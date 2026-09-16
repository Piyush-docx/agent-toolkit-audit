"""Aggregate stats across all researched apps -> patterns.json (brief section 9).

Only v1 exists in this submission (verify.py / v2 was scoped out under time
pressure), so this computes from data/results_v1.json rather than v2.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from agent.research import load_apps, load_cached_record
from agent.schema import AppRecord

PATTERNS_PATH = Path("data/patterns.json")


def load_all_records() -> list[AppRecord]:
    return [r for r in (load_cached_record(a["id"]) for a in load_apps())
            if r is not None]


def _value(v) -> str:
    return getattr(v, "value", v) if v is not None else "unknown"


def build() -> dict[str, Any]:
    records = load_all_records()

    verdict_by_category: dict[str, dict[str, int]] = defaultdict(dict)
    access_by_category: dict[str, dict[str, int]] = defaultdict(dict)
    primary_auth = Counter()
    any_auth = Counter()
    mcp_overall = Counter()
    mcp_by_category: dict[str, Counter] = defaultdict(Counter)
    on_composio = Counter()
    blocker_counts = Counter()
    webhooks_counts = Counter()
    sandbox_counts = Counter()
    totals = Counter()
    easy_wins, needs_outreach, not_viable = [], [], []

    for r in records:
        cat = r.category
        verdict = _value(r.verdict)
        totals[verdict] += 1
        verdict_by_category[cat][verdict] = verdict_by_category[cat].get(verdict, 0) + 1

        access = _value(r.access)
        access_by_category[cat][access] = access_by_category[cat].get(access, 0) + 1

        if r.primary_auth is not None:
            primary_auth[_value(r.primary_auth)] += 1
        for a in r.auth_methods or []:
            any_auth[_value(a)] += 1

        mcp = _value(r.existing_mcp)
        mcp_overall[mcp] += 1
        mcp_by_category[cat][mcp] += 1

        on_composio[_value(r.on_composio)] += 1

        if r.blocker is not None and _value(r.blocker) != "none":
            blocker_counts[_value(r.blocker)] += 1

        webhooks_counts[_value(r.webhooks)] += 1
        sandbox_counts[_value(r.sandbox_or_test_mode)] += 1

        if verdict == "ready" and _value(r.on_composio) == "no":
            easy_wins.append({"id": r.id, "name": r.name, "category": cat})
        if verdict == "needs_outreach":
            needs_outreach.append({"id": r.id, "name": r.name, "category": cat,
                                    "access": access,
                                    "reason": r.access_notes or r.blocker_notes or ""})
        if verdict == "not_viable":
            not_viable.append({"id": r.id, "name": r.name, "category": cat,
                               "access": access,
                               "reason": r.access_notes or r.blocker_notes or ""})

    return {
        "totals": dict(totals),
        "verdict_by_category": dict(verdict_by_category),
        "access_by_category": dict(access_by_category),
        "auth": {"primary": dict(primary_auth), "any": dict(any_auth)},
        "mcp": {"overall": dict(mcp_overall),
                "by_category": {k: dict(v) for k, v in mcp_by_category.items()}},
        "on_composio": dict(on_composio),
        "blocker_frequency": [{"blocker": b, "count": c}
                              for b, c in blocker_counts.most_common()],
        "webhooks": dict(webhooks_counts),
        "sandbox_or_test_mode": dict(sandbox_counts),
        "easy_wins": easy_wins,
        "needs_outreach": needs_outreach,
        "not_viable": not_viable,
        "apps_total": len(records),
    }


def headlines(p: dict[str, Any]) -> list[str]:
    """4-6 sentences, every number taken directly from `p` (brief section 9)."""
    total = p["apps_total"]
    ready = p["totals"].get("ready", 0)
    friction = p["totals"].get("ready_with_friction", 0)
    any_auth = p["auth"]["any"]
    top_auth = max(any_auth, key=any_auth.get) if any_auth else "unknown"
    top_auth_pct = round(100 * any_auth.get(top_auth, 0) / total) if total else 0
    on_composio_yes = p["on_composio"].get("yes", 0)
    easy_wins = len(p["easy_wins"])
    official_mcp = p["mcp"]["overall"].get("official", 0)

    return [
        f"{ready} of {total} apps are ready to use as an agent toolkit today, "
        f"no negotiation or waiting required.",
        f"Counting ready-with-friction apps too, {ready + friction} of {total} "
        f"are usable with some setup cost (a paid plan or admin approval).",
        f"{top_auth} is the most common auth method, appearing in {top_auth_pct}% "
        f"of researched apps.",
        f"{official_mcp} apps already publish an official MCP server.",
        f"{on_composio_yes} of {total} apps are already available as a Composio "
        f"toolkit; {easy_wins} ready apps are not yet on Composio -- an easy-wins list.",
    ]


def write_patterns(path: Path = PATTERNS_PATH) -> Path:
    p = build()
    p["headlines"] = headlines(p)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(p, indent=2), encoding="utf-8")
    return path
