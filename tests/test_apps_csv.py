"""Integrity of data/apps.csv.

The 100 rows were transcribed from PROJECT_BRIEF.md section 2. Transcription is the
kind of step that silently drops or duplicates a row, so these tests pin the shape
and spot-check the ids that later phases depend on.
"""
import csv
from pathlib import Path

import pytest

APPS_CSV = Path(__file__).resolve().parents[1] / "data" / "apps.csv"


@pytest.fixture(scope="module")
def rows():
    with APPS_CSV.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_header_is_id_name_category_hint():
    with APPS_CSV.open(encoding="utf-8") as f:
        assert next(csv.reader(f)) == ["id", "name", "category", "hint"]


def test_exactly_100_rows(rows):
    assert len(rows) == 100


def test_ids_are_1_to_100_unique(rows):
    assert sorted(int(r["id"]) for r in rows) == list(range(1, 101))


def test_exactly_10_categories_of_10(rows):
    counts = {}
    for r in rows:
        counts[r["category"]] = counts.get(r["category"], 0) + 1
    assert len(counts) == 10
    assert set(counts.values()) == {10}, counts


def test_names_unique_and_fields_non_empty(rows):
    names = [r["name"] for r in rows]
    assert len(set(names)) == 100
    for r in rows:
        assert r["name"].strip(), r
        assert r["category"].strip(), r
        assert r["hint"].strip(), r


@pytest.mark.parametrize(
    "app_id,name",
    [
        (1, "Salesforce"),     # P2 slice
        (50, "fanbasis"),      # thin docs
        (58, "Sherlock"),      # local-only tool -> not_viable (D10)
        (81, "Stripe"),        # P2 slice
        (90, "PitchBook"),     # partner gated
        (98, "Mermaid CLI"),   # local-only tool (D10)
        (100, "Grain"),
    ],
)
def test_known_hard_cases_at_expected_id(rows, app_id, name):
    """Guards against an off-by-one slip in the 100-row transcription."""
    by_id = {int(r["id"]): r["name"] for r in rows}
    assert by_id[app_id] == name


def test_section_8_sample_apps_all_exist(rows):
    """The 20 stratified sample apps (brief section 8) must resolve by name."""
    sample = [
        "HubSpot", "DealCloud", "Zendesk", "Gladly", "Slack", "WhatsApp Business",
        "Meta Ads", "systeme.io", "Shopify", "fanbasis", "Firecrawl", "Sherlock",
        "GitHub", "Neo4j", "Notion", "Harvest", "Stripe", "Paygent Connect",
        "Otter AI", "NotebookLM",
    ]
    names = {r["name"] for r in rows}
    assert not (set(sample) - names)
