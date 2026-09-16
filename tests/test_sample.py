"""Stratified sample -> blind ground-truth template (brief section 8)."""
import csv

import pytest

from agent import sample
from agent.schema import AppRecord

FIELDS = ["auth_methods", "access", "api_type", "existing_mcp", "webhooks", "verdict"]


def _rec(id, name, category, docs_url=None):
    return AppRecord.model_validate(
        {"id": id, "name": name, "category": category, "docs_url": docs_url,
         "auth_methods": ["oauth2"], "access": "self_serve_free",
         "verdict": "ready", "confidence": 0.9})


def test_default_sample_is_20_apps_two_per_category():
    apps = sample.DEFAULT_SAMPLE
    assert len(apps) == 20
    from collections import Counter
    counts = Counter(a["category"] for a in apps)
    assert len(counts) == 10
    assert all(n == 2 for n in counts.values())


def test_default_sample_names_match_the_brief():
    names = {a["name"] for a in sample.DEFAULT_SAMPLE}
    expected = {
        "HubSpot", "DealCloud", "Zendesk", "Gladly", "Slack",
        "WhatsApp Business", "Meta Ads", "systeme.io", "Shopify", "fanbasis",
        "Firecrawl", "Sherlock", "GitHub", "Neo4j", "Notion", "Harvest",
        "Stripe", "Paygent Connect", "Otter AI", "NotebookLM",
    }
    assert names == expected


def test_build_rows_one_row_per_field_per_app(monkeypatch):
    records = {
        1: _rec(1, "Stripe", "Finance & Fintech", "https://docs.stripe.com/api"),
        2: _rec(2, "Sherlock", "Data, SEO & Scraping", None),
    }
    monkeypatch.setattr(sample, "load_cached_record", lambda i: records.get(i))
    apps = [{"id": 1, "name": "Stripe", "category": "Finance & Fintech"},
            {"id": 2, "name": "Sherlock", "category": "Data, SEO & Scraping"}]
    rows = sample.build_rows(apps)
    assert len(rows) == 2 * len(FIELDS)
    assert {r["field"] for r in rows} == set(FIELDS)


def test_rows_never_carry_agent_answers_or_truth(monkeypatch):
    """Blind labelling: the template must not leak what the agent found."""
    records = {1: _rec(1, "Stripe", "Finance & Fintech", "https://docs.stripe.com/api")}
    monkeypatch.setattr(sample, "load_cached_record", lambda i: records.get(1))
    apps = [{"id": 1, "name": "Stripe", "category": "Finance & Fintech"}]
    rows = sample.build_rows(apps)
    for row in rows:
        assert row["truth_value"] == ""
        assert set(row.keys()) == {"id", "name", "field", "truth_value",
                                    "source_url", "notes"}


def test_source_url_comes_from_the_cached_record(monkeypatch):
    records = {1: _rec(1, "Stripe", "Finance & Fintech", "https://docs.stripe.com/api")}
    monkeypatch.setattr(sample, "load_cached_record", lambda i: records.get(1))
    apps = [{"id": 1, "name": "Stripe", "category": "Finance & Fintech"}]
    rows = sample.build_rows(apps)
    assert all(r["source_url"] == "https://docs.stripe.com/api" for r in rows)


def test_source_url_blank_when_no_cached_docs_url(monkeypatch):
    records = {1: _rec(1, "HubSpot", "CRM & Sales", None)}
    monkeypatch.setattr(sample, "load_cached_record", lambda i: records.get(1))
    apps = [{"id": 1, "name": "HubSpot", "category": "CRM & Sales"}]
    rows = sample.build_rows(apps)
    assert all(r["source_url"] == "" for r in rows)


def test_missing_record_still_produces_rows(monkeypatch):
    """An app that somehow has no cached record yet must not crash the build."""
    monkeypatch.setattr(sample, "load_cached_record", lambda i: None)
    apps = [{"id": 999, "name": "Ghost App", "category": "Nowhere"}]
    rows = sample.build_rows(apps)
    assert len(rows) == len(FIELDS)
    assert all(r["source_url"] == "" for r in rows)


def test_write_template_produces_the_exact_csv_header(tmp_path, monkeypatch):
    records = {1: _rec(1, "Stripe", "Finance & Fintech", "https://docs.stripe.com/api")}
    monkeypatch.setattr(sample, "load_cached_record", lambda i: records.get(1))
    out = tmp_path / "ground_truth_template.csv"
    apps = [{"id": 1, "name": "Stripe", "category": "Finance & Fintech"}]
    sample.write_template(apps, out)
    with out.open() as fh:
        reader = csv.DictReader(fh)
        assert reader.fieldnames == ["id", "name", "field", "truth_value",
                                      "source_url", "notes"]
        rows = list(reader)
    assert len(rows) == len(FIELDS)


def test_write_template_default_uses_default_sample(tmp_path, monkeypatch):
    monkeypatch.setattr(sample, "load_cached_record", lambda i: None)
    out = tmp_path / "ground_truth_template.csv"
    sample.write_template(sample.DEFAULT_SAMPLE, out)
    with out.open() as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 20 * len(FIELDS)
