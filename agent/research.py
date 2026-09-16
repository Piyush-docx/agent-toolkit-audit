"""Research pass 1: one AppRecord per app (brief section 6).

Per app: prompt -> Claude Code (WebSearch/WebFetch) -> validate -> one repair
attempt -> apply deterministic rules -> attach the Composio check -> cache.

Three properties that matter on Claude Pro:
  resumable  a cached record is never re-researched, so an interrupted run
             continues where it stopped
  bounded    concurrency is small (2-3) and a usage-limit error stops the run
             cleanly with progress saved, rather than burning the window
  auditable  the raw model output is written to cache/llm/v1/{id}.json before
             any parsing, so a bad record can always be traced to its source
"""

from __future__ import annotations

import csv
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Optional

from pydantic import ValidationError

from agent import prompts
from agent.composio_check import check_all, is_composio_mcp_toolkit
from agent.llm import DEFAULT_MODEL, LLMError, complete_claude_code
from agent.rules import apply_rules, check_consistency, rule_needs_human
from agent.schema import AppRecord, YesNoUnknown, dump_record

APPS_CSV = Path("data/apps.csv")
RAW_DIR = Path("cache/llm/v1")
RECORDS_DIR = Path("cache/records/v1")
STATS_PATH = Path("data/run_stats.json")

# Obscure apps legitimately need many search/fetch turns before they can answer.
# fanbasis exhausted 20 turns in the slice run and lost ~$0.86 of work, so the
# budget is generous and exhaustion is now salvaged rather than discarded.
MAX_TURNS = 40

_STATS_LOCK = threading.Lock()


def _record_usage(stats: Optional["RunStats"], result) -> None:
    """Accumulate usage under a lock -- research runs on a thread pool."""
    if stats is None:
        return
    with _STATS_LOCK:
        stats.llm_calls += 1
        stats.total_cost_usd += result.cost_usd


@dataclass
class RunStats:
    apps_attempted: int = 0
    apps_succeeded: int = 0
    apps_failed: int = 0
    repairs_attempted: int = 0
    repairs_succeeded: int = 0
    llm_calls: int = 0
    total_cost_usd: float = 0.0
    wall_time_s: float = 0.0
    needs_human: int = 0
    prompt_version: str = prompts.PROMPT_VERSION
    model: str = DEFAULT_MODEL
    errors: list[dict] = field(default_factory=list)
    stopped_early: Optional[str] = None


def load_apps(path: Path = APPS_CSV) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [
            {"id": int(row["id"]), "name": row["name"],
             "category": row["category"], "hint": row["hint"]}
            for row in csv.DictReader(handle)
        ]


def select_apps(apps: list[dict], *, only: Optional[Iterable[str]] = None,
                ids: Optional[Iterable[int]] = None) -> list[dict]:
    """Filter by name (case-insensitive) or id. Unknown names raise loudly."""
    if ids:
        wanted_ids = set(ids)
        return [a for a in apps if a["id"] in wanted_ids]
    if only:
        wanted = {name.strip().lower() for name in only}
        chosen = [a for a in apps if a["name"].lower() in wanted]
        missing = wanted - {a["name"].lower() for a in chosen}
        if missing:
            raise SystemExit(f"unknown app name(s): {sorted(missing)}")
        return chosen
    return apps


def _record_path(app_id: int) -> Path:
    return RECORDS_DIR / f"{app_id}.json"


def load_cached_record(app_id: int) -> Optional[AppRecord]:
    path = _record_path(app_id)
    if not path.exists():
        return None
    try:
        return AppRecord.model_validate_json(path.read_text(encoding="utf-8"))
    except (ValidationError, OSError):
        return None      # a corrupt cache entry simply means "re-research it"


def save_record(record: AppRecord) -> None:
    RECORDS_DIR.mkdir(parents=True, exist_ok=True)
    _record_path(record.id).write_text(
        json.dumps(dump_record(record), indent=2), encoding="utf-8")


def _save_raw(app_id: int, payload: dict) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_DIR / f"{app_id}.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8")


def research_app(app: dict, *, model: str = DEFAULT_MODEL,
                 stats: Optional[RunStats] = None) -> AppRecord:
    """Research one app. Raises LLMError; every other failure yields a record."""
    schema = AppRecord.model_json_schema()
    prompt = prompts.RESEARCH.format(**app)

    result = complete_claude_code(prompt, schema=schema, model=model,
                                  max_turns=MAX_TURNS)
    _record_usage(stats, result)

    _save_raw(app["id"], {"app": app, "prompt_version": prompts.PROMPT_VERSION,
                          "model": model, "cost_usd": result.cost_usd,
                          "num_turns": result.num_turns, "raw": result.raw,
                          "data": result.data})

    record, error = _to_record(app, result.data)

    # One repair attempt, quoting the validation error back to the model.
    if record is None:
        if stats:
            stats.repairs_attempted += 1
        repair = complete_claude_code(
            prompt + "\n\n" + prompts.REPAIR.format(name=app["name"], error=error),
            schema=schema, model=model, max_turns=MAX_TURNS,
        )
        _record_usage(stats, repair)
        _save_raw(app["id"], {"app": app, "repair": True, "raw": repair.raw,
                              "data": repair.data})
        record, error2 = _to_record(app, repair.data)
        if record is not None and stats:
            stats.repairs_succeeded += 1
        if record is None:
            record = _fallback_record(app, f"schema invalid after repair: {error2}")

    return finalise(record)


def _to_record(app: dict, data: Optional[dict]) -> tuple[Optional[AppRecord], str]:
    """Validate model output, forcing the CSV-derived identity fields."""
    if not isinstance(data, dict):
        return None, "model returned no JSON object"
    payload = {**data, "id": app["id"], "name": app["name"],
               "category": app["category"], "pass": "v1"}
    try:
        return AppRecord.model_validate(payload), ""
    except ValidationError as exc:
        return None, str(exc)[:1500]


def _fallback_record(app: dict, reason: str) -> AppRecord:
    """A record that says 'we failed', rather than a missing row."""
    return AppRecord.model_validate({
        "id": app["id"], "name": app["name"], "category": app["category"],
        "pass": "v1", "needs_human": True, "needs_human_reason": reason,
        "confidence": 0.0,
    })


def _flag(record: AppRecord, reason: str) -> None:
    """Set needs_human, appending to any existing reason rather than clobbering."""
    record.needs_human = True
    record.needs_human_reason = (
        f"{record.needs_human_reason}; {reason}"
        if record.needs_human_reason else reason
    )


def finalise(record: AppRecord) -> AppRecord:
    """Apply the deterministic rules. The rule always wins over the LLM (D14).

    Also runs the error-level consistency checks now rather than waiting for
    Loop E: a self-contradictory record (e.g. primary_auth absent from
    auth_methods) is cheap to spot and should not sit unflagged in v1.
    """
    result = apply_rules(record)
    record.verdict = result.verdict
    record.rule_id = result.rule_id
    escalate, reason = rule_needs_human(result)
    if escalate:
        _flag(record, reason)

    errors = [v for v in check_consistency(record) if v.severity == "error"]
    if errors:
        record.verification.setdefault("consistency", []).extend(
            [{"name": v.name, "message": v.message} for v in errors])
        _flag(record, "consistency: " + "; ".join(v.name for v in errors))
    return record


def attach_composio(records: list[AppRecord]) -> None:
    """Fill on_composio for every record from one cached index fetch."""
    if not records:
        return
    try:
        lookup = check_all([r.name for r in records])
    except Exception as exc:                      # network hiccup is not fatal
        print(f"  composio check unavailable ({exc}); leaving on_composio=unknown")
        return
    for record in records:
        entry = lookup.get(record.name, {})
        record.on_composio = YesNoUnknown(entry.get("on_composio", "unknown"))
        slug = entry.get("composio_slug")
        if slug:
            record.verification.setdefault("composio", {})["slug"] = slug
            if is_composio_mcp_toolkit(slug):
                record.verification["composio"]["is_mcp_toolkit"] = True


def run(apps: list[dict], *, concurrency: int = 3, model: str = DEFAULT_MODEL,
        refresh: bool = False) -> tuple[list[AppRecord], RunStats]:
    """Research every app, skipping those already cached unless refresh=True."""
    stats = RunStats(apps_attempted=len(apps), model=model)
    started = time.monotonic()
    records: dict[int, AppRecord] = {}
    todo: list[dict] = []

    for app in apps:
        cached = None if refresh else load_cached_record(app["id"])
        if cached is not None:
            records[app["id"]] = cached
        else:
            todo.append(app)

    if records:
        print(f"  resuming: {len(records)} cached, {len(todo)} to research")

    if todo:
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = {pool.submit(research_app, app, model=model, stats=stats): app
                       for app in todo}
            try:
                for future in as_completed(futures):
                    app = futures[future]
                    try:
                        record = future.result()
                    except LLMError as exc:
                        if exc.usage_limited:
                            # Stop cleanly: progress is already on disk.
                            stats.stopped_early = str(exc)
                            for pending in futures:
                                pending.cancel()
                            break
                        record = _fallback_record(app, f"llm error: {exc}")
                        record = finalise(record)
                        stats.errors.append({"id": app["id"], "name": app["name"],
                                             "error": str(exc)[:300]})
                    records[app["id"]] = record
                    save_record(record)
                    flag = " [needs_human]" if record.needs_human else ""
                    print(f"  [{len(records)}/{len(apps)}] {app['name']} "
                          f"-> {record.verdict.value}{flag}")
            except KeyboardInterrupt:
                stats.stopped_early = "interrupted by user"

    ordered = [records[a["id"]] for a in apps if a["id"] in records]
    attach_composio(ordered)
    for record in ordered:
        save_record(record)

    stats.apps_succeeded = sum(1 for r in ordered if not r.needs_human)
    stats.apps_failed = len(ordered) - stats.apps_succeeded
    stats.needs_human = stats.apps_failed
    stats.wall_time_s = round(time.monotonic() - started, 1)
    return ordered, stats


def save_stats(stats: RunStats, path: Path = STATS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(stats), indent=2), encoding="utf-8")
