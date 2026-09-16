"""Command line entry point: `python -m agent.cli <command>`."""

from __future__ import annotations

import argparse
import sys

from agent.llm import DEFAULT_MODEL


def cmd_research(args: argparse.Namespace) -> int:
    from agent.research import load_apps, run, save_stats, select_apps

    apps = select_apps(load_apps(), only=[args.app] if args.app else None,
                       ids=args.ids)
    if args.limit:
        apps = apps[: args.limit]
    print(f"researching {len(apps)} app(s) with model={args.model}, "
          f"concurrency={args.concurrency}")

    records, stats = run(apps, concurrency=args.concurrency, model=args.model,
                         refresh=args.refresh)
    save_stats(stats)

    print(f"\ndone: {len(records)} record(s) in {stats.wall_time_s}s | "
          f"{stats.llm_calls} llm calls | ${stats.total_cost_usd:.2f} | "
          f"{stats.needs_human} need a human")
    if stats.stopped_early:
        print(f"STOPPED EARLY: {stats.stopped_early}\n"
              "Progress is cached; rerun the same command to continue.")
        return 2
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    """Print cached records as a readable table (used at the P2 human gate)."""
    from agent.research import load_apps, load_cached_record, select_apps

    apps = select_apps(load_apps(), only=args.apps or None, ids=args.ids)
    records = [r for r in (load_cached_record(a["id"]) for a in apps) if r]
    if not records:
        print("no cached records found; run `make research-one APP=...` first")
        return 1

    for record in records:
        print("=" * 78)
        print(f"#{record.id}  {record.name}  ({record.category})")
        print(f"  {record.one_liner}")
        print(f"  verdict     : {record.verdict.value}  [rule {record.rule_id}]"
              f"   confidence {record.confidence}")
        print(f"  auth        : {[a.value for a in record.auth_methods]} "
              f"(primary: {getattr(record.primary_auth, 'value', None)})")
        print(f"  access      : {getattr(record.access, 'value', None)} "
              f"- {record.access_notes}")
        print(f"  api         : {[a.value for a in record.api_type]} "
              f"breadth={record.api_breadth.value} "
              f"openapi={record.openapi_spec.value}")
        print(f"  mcp         : {record.existing_mcp.value} {record.mcp_url or ''}")
        print(f"  extras      : webhooks={record.webhooks.value} "
              f"sandbox={record.sandbox_or_test_mode.value} "
              f"rate_limits={record.rate_limits_documented.value} "
              f"on_composio={record.on_composio.value}")
        print(f"  blocker     : {getattr(record.blocker, 'value', None)} "
              f"- {record.blocker_notes or ''}")
        if record.needs_human:
            print(f"  NEEDS HUMAN : {record.needs_human_reason}")
        print(f"  docs        : {record.docs_url}")
        print(f"  evidence ({len(record.evidence)}):")
        for item in record.evidence:
            print(f"    - [{item.field}] {item.url}")
            print(f"      \"{item.quote}\"")
    print("=" * 78)
    return 0


def cmd_freeze_v1(args: argparse.Namespace) -> int:
    """Collect every cached record into data/results_v1.json and hash it.

    Refuses to freeze a partial run: the brief's v1 is "100 records (errors
    allowed, flagged)" -- a record existing and being flagged needs_human is
    fine, a record missing entirely is not, since freeze-v1 is a one-way door
    (v1 is never edited after this).
    """
    import hashlib
    import json
    from pathlib import Path

    from agent.research import load_apps, load_cached_record
    from agent.schema import dump_record

    apps = load_apps()
    records = []
    missing = []
    for app in apps:
        record = load_cached_record(app["id"])
        if record is None:
            missing.append(app["id"])
        else:
            records.append(dump_record(record))

    if missing:
        print(f"refusing to freeze: {len(missing)} app(s) not yet researched: "
              f"{missing}")
        return 1

    out_path = Path("data/results_v1.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(records, indent=2)
    out_path.write_text(payload, encoding="utf-8")

    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    sha_path = Path("data/results_v1.sha256")
    sha_path.write_text(f"{digest}  results_v1.json\n", encoding="utf-8")

    not_researched = sum(1 for r in records if r["verdict"] == "not_researched")
    needs_human = sum(1 for r in records if r["needs_human"])
    print(f"froze {len(records)} records -> {out_path}")
    print(f"sha256 -> {sha_path}  ({digest})")
    print(f"needs_human: {needs_human}  not_researched: {not_researched}")
    return 0


def _not_yet(phase: str):
    def handler(args: argparse.Namespace) -> int:
        print(f"not implemented yet ({phase})")
        return 1
    return handler


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    research = sub.add_parser("research", help="research pass 1")
    research.add_argument("--app", help="single app by name, e.g. Stripe")
    research.add_argument("--ids", type=int, nargs="*", help="app ids")
    research.add_argument("--limit", type=int)
    research.add_argument("--concurrency", type=int, default=3)
    research.add_argument("--model", default=DEFAULT_MODEL)
    research.add_argument("--refresh", action="store_true",
                          help="ignore cached records")
    research.set_defaults(func=cmd_research)

    show = sub.add_parser("show", help="print cached records")
    show.add_argument("apps", nargs="*")
    show.add_argument("--ids", type=int, nargs="*")
    show.set_defaults(func=cmd_show)

    freeze = sub.add_parser("freeze-v1", help="freeze results_v1.json + sha256")
    freeze.set_defaults(func=cmd_freeze_v1)

    for name, phase in [("verify", "P5"), ("sample", "P4"),
                        ("score", "P7"), ("patterns", "P7"), ("review", "P6")]:
        placeholder = sub.add_parser(name)
        placeholder.set_defaults(func=_not_yet(phase))

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
