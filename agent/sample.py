"""Stratified sample -> blind ground-truth template (brief section 8).

`make sample` writes data/ground_truth_template.csv: one row per (app, field),
pre-filled only with the docs link the human should check. No values, no
agent answers -- the human labels blind from real docs.
"""

from __future__ import annotations

import csv
from pathlib import Path

from agent.research import load_apps, load_cached_record, select_apps

TEMPLATE_PATH = Path("data/ground_truth_template.csv")

# The fields section 8 scores. Order matches the brief.
SCORED_FIELDS: tuple[str, ...] = (
    "auth_methods", "access", "api_type", "existing_mcp", "webhooks", "verdict",
)

# Brief section 8's default stratified sample: 2 per category (one
# easy/well-known, one hard/obscure), fixed rather than randomised so the
# same 20 apps are used every run.
_DEFAULT_NAMES: tuple[str, ...] = (
    "HubSpot", "DealCloud", "Zendesk", "Gladly", "Slack", "WhatsApp Business",
    "Meta Ads", "systeme.io", "Shopify", "fanbasis", "Firecrawl", "Sherlock",
    "GitHub", "Neo4j", "Notion", "Harvest", "Stripe", "Paygent Connect",
    "Otter AI", "NotebookLM",
)


def _default_sample() -> list[dict]:
    return select_apps(load_apps(), only=_DEFAULT_NAMES)


DEFAULT_SAMPLE: list[dict] = _default_sample()


def build_rows(apps: list[dict]) -> list[dict]:
    """One row per (app, scored field). truth_value is always blank."""
    rows = []
    for app in apps:
        record = load_cached_record(app["id"])
        source_url = record.docs_url if record and record.docs_url else ""
        for field in SCORED_FIELDS:
            rows.append({
                "id": app["id"], "name": app["name"], "field": field,
                "truth_value": "", "source_url": source_url, "notes": "",
            })
    return rows


def write_template(apps: list[dict], path: Path = TEMPLATE_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = build_rows(apps)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["id", "name", "field", "truth_value",
                                "source_url", "notes"])
        writer.writeheader()
        writer.writerows(rows)
    return path
