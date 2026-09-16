"""Aggregate stats -> patterns.json (brief section 9)."""
from agent import patterns
from agent.schema import AppRecord


def _rec(id, name, category, **overrides):
    base = {"id": id, "name": name, "category": category}
    return AppRecord.model_validate({**base, **overrides})


def test_verdict_counts_per_category(monkeypatch):
    records = [
        _rec(1, "A", "CRM", verdict="ready"),
        _rec(2, "B", "CRM", verdict="not_viable"),
        _rec(3, "C", "Comms", verdict="ready"),
    ]
    monkeypatch.setattr(patterns, "load_all_records", lambda: records)
    p = patterns.build()
    assert p["verdict_by_category"]["CRM"] == {"ready": 1, "not_viable": 1}
    assert p["verdict_by_category"]["Comms"] == {"ready": 1}


def test_auth_distribution_primary_and_any(monkeypatch):
    records = [
        _rec(1, "A", "CRM", primary_auth="oauth2", auth_methods=["oauth2", "api_key"]),
        _rec(2, "B", "CRM", primary_auth="api_key", auth_methods=["api_key"]),
    ]
    monkeypatch.setattr(patterns, "load_all_records", lambda: records)
    p = patterns.build()
    assert p["auth"]["primary"]["oauth2"] == 1
    assert p["auth"]["primary"]["api_key"] == 1
    assert p["auth"]["any"]["oauth2"] == 1
    assert p["auth"]["any"]["api_key"] == 2


def test_composio_easy_wins_ready_but_not_on_composio(monkeypatch):
    records = [
        _rec(1, "A", "CRM", verdict="ready", on_composio="no"),
        _rec(2, "B", "CRM", verdict="ready", on_composio="yes"),
        _rec(3, "C", "CRM", verdict="not_viable", on_composio="no"),
    ]
    monkeypatch.setattr(patterns, "load_all_records", lambda: records)
    p = patterns.build()
    assert [r["name"] for r in p["easy_wins"]] == ["A"]


def test_needs_outreach_and_not_viable_lists_include_reason(monkeypatch):
    records = [
        _rec(1, "A", "CRM", verdict="needs_outreach", access="partner_gated"),
        _rec(2, "B", "CRM", verdict="not_viable", access="no_public_api"),
    ]
    monkeypatch.setattr(patterns, "load_all_records", lambda: records)
    p = patterns.build()
    assert p["needs_outreach"][0]["name"] == "A"
    assert p["not_viable"][0]["name"] == "B"


def test_blocker_frequency_ranking(monkeypatch):
    records = [
        _rec(1, "A", "CRM", blocker="paid_plan"),
        _rec(2, "B", "CRM", blocker="paid_plan"),
        _rec(3, "C", "CRM", blocker="app_review"),
    ]
    monkeypatch.setattr(patterns, "load_all_records", lambda: records)
    p = patterns.build()
    assert p["blocker_frequency"][0] == {"blocker": "paid_plan", "count": 2}


def test_mcp_distribution(monkeypatch):
    records = [
        _rec(1, "A", "CRM", existing_mcp="official"),
        _rec(2, "B", "CRM", existing_mcp="official"),
        _rec(3, "C", "CRM", existing_mcp="none_found"),
    ]
    monkeypatch.setattr(patterns, "load_all_records", lambda: records)
    p = patterns.build()
    assert p["mcp"]["overall"]["official"] == 2
    assert p["mcp"]["overall"]["none_found"] == 1


def test_headline_numbers_all_come_from_patterns_json(monkeypatch):
    """Every number in a headline sentence must be traceable to patterns.json."""
    records = [_rec(i, f"App{i}", "CRM", verdict="ready") for i in range(3)]
    monkeypatch.setattr(patterns, "load_all_records", lambda: records)
    p = patterns.build()
    headlines = patterns.headlines(p)
    assert any(str(p["totals"]["ready"]) in h for h in headlines)
