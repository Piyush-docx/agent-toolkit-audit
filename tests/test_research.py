"""Research orchestration: caching, repair, rule application, resumability."""
import json

import pytest

from agent import research
from agent.llm import LLMError, LLMResult
from agent.schema import AppRecord, Verdict

APP = {"id": 81, "name": "Stripe", "category": "Finance & Fintech",
       "hint": "stripe.com/docs/api"}

GOOD = {
    "one_liner": "Payments infrastructure for the internet",
    "docs_url": "https://docs.stripe.com/api",
    "auth_methods": ["api_key", "basic"], "primary_auth": "api_key",
    "access": "self_serve_free", "access_notes": "Test keys on signup",
    "api_type": ["rest"], "api_breadth": "broad", "existing_mcp": "official",
    "mcp_url": "https://mcp.stripe.com", "confidence": 0.9,
    "evidence": [{"field": f, "url": "https://docs.stripe.com/api", "quote": "q"}
                 for f in ("auth_methods", "access", "api_type",
                           "existing_mcp", "verdict")],
}


@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    """Redirect every cache path so tests never touch the real cache."""
    monkeypatch.setattr(research, "RECORDS_DIR", tmp_path / "records")
    monkeypatch.setattr(research, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(research, "attach_composio", lambda records: None)
    return tmp_path


def fake_llm(payloads):
    """Return a complete_claude_code stub yielding each payload in turn."""
    calls = {"n": 0, "prompts": []}

    def _call(prompt, **kwargs):
        calls["prompts"].append(prompt)
        data = payloads[min(calls["n"], len(payloads) - 1)]
        calls["n"] += 1
        if isinstance(data, Exception):
            raise data
        return LLMResult(data=data, raw=json.dumps(data), cost_usd=0.25,
                         num_turns=4, model="sonnet")

    return _call, calls


def test_happy_path_builds_a_record(monkeypatch):
    call, _ = fake_llm([GOOD])
    monkeypatch.setattr(research, "complete_claude_code", call)
    record = research.research_app(APP)
    assert record.name == "Stripe"
    assert record.verdict is Verdict.READY      # rules, not the model
    assert record.rule_id == "R5"
    assert record.needs_human is False


def test_identity_fields_come_from_csv_not_the_model(monkeypatch):
    """The model must never be able to rename or recategorise an app."""
    call, _ = fake_llm([{**GOOD, "id": 999, "name": "Hacked", "category": "X"}])
    monkeypatch.setattr(research, "complete_claude_code", call)
    record = research.research_app(APP)
    assert (record.id, record.name, record.category) == (
        81, "Stripe", "Finance & Fintech")


def test_invalid_output_triggers_one_repair(monkeypatch):
    call, calls = fake_llm([{**GOOD, "access": "freemium"}, GOOD])
    monkeypatch.setattr(research, "complete_claude_code", call)
    stats = research.RunStats()
    record = research.research_app(APP, stats=stats)
    assert calls["n"] == 2
    assert "did not match the required schema" in calls["prompts"][1]
    assert stats.repairs_succeeded == 1
    assert record.verdict is Verdict.READY


def test_failed_repair_yields_a_flagged_record_not_a_crash(monkeypatch):
    call, _ = fake_llm([{"access": "bogus"}, {"access": "still_bogus"}])
    monkeypatch.setattr(research, "complete_claude_code", call)
    record = research.research_app(APP)
    assert record.needs_human is True
    assert "schema invalid after repair" in record.needs_human_reason
    # A repair-exhausted record must never get a rule-derived verdict: there
    # is no real data behind it, and apply_rules() would mechanically read
    # the empty api_type/access as not_viable/R2 -- a fabricated finding.
    assert record.verdict is Verdict.NOT_RESEARCHED
    assert record.rule_id is None


def test_rule_overrides_model_verdict_and_flags(monkeypatch):
    """PitchBook-shaped: model says ready, partner gate says otherwise."""
    call, _ = fake_llm([{**GOOD, "access": "partner_gated", "verdict": "ready"}])
    monkeypatch.setattr(research, "complete_claude_code", call)
    record = research.research_app(APP)
    assert record.verdict is Verdict.NEEDS_OUTREACH
    assert record.needs_human is True
    assert "disagreement" in record.needs_human_reason


def test_raw_output_is_cached_before_parsing(monkeypatch, isolate):
    call, _ = fake_llm([GOOD])
    monkeypatch.setattr(research, "complete_claude_code", call)
    research.research_app(APP)
    assert (isolate / "raw" / "81.json").exists()


# --- resumability ----------------------------------------------------------

def test_run_skips_cached_apps(monkeypatch):
    call, calls = fake_llm([GOOD])
    monkeypatch.setattr(research, "complete_claude_code", call)
    research.run([APP])
    assert calls["n"] == 1
    research.run([APP])                 # second run must not call the model
    assert calls["n"] == 1


def test_refresh_forces_reresearch(monkeypatch):
    call, calls = fake_llm([GOOD])
    monkeypatch.setattr(research, "complete_claude_code", call)
    research.run([APP])
    research.run([APP], refresh=True)
    assert calls["n"] == 2


def test_usage_limit_stops_the_run_and_keeps_progress(monkeypatch):
    call, _ = fake_llm([LLMError("usage limit reached", usage_limited=True)])
    monkeypatch.setattr(research, "complete_claude_code", call)
    records, stats = research.run([APP], concurrency=1)
    assert stats.stopped_early and "usage limit" in stats.stopped_early
    assert records == []                # nothing invented


def test_ordinary_llm_error_produces_a_flagged_record(monkeypatch):
    call, _ = fake_llm([LLMError("network down")])
    monkeypatch.setattr(research, "complete_claude_code", call)
    records, stats = research.run([APP], concurrency=1)
    assert len(records) == 1
    assert records[0].needs_human is True
    assert stats.errors and stats.errors[0]["name"] == "Stripe"
    # Regression: an LLM-error record used to fall through to apply_rules(),
    # which read the empty api_type/access as a genuine not_viable/R2 finding
    # (batch 1/2 postmortem: 26/40 apps got a false not_viable this way).
    assert records[0].verdict is Verdict.NOT_RESEARCHED
    assert records[0].rule_id is None


def test_llm_error_envelope_is_saved_for_audit(monkeypatch, isolate):
    """error_max_structured_output_retries (batch 2) left no raw cache entry at
    all, so a fabricated not_viable verdict had no audit trail to diagnose it
    from. The envelope must now be persisted whenever the backend supplies one.
    """
    envelope = {"is_error": True, "subtype": "error_max_structured_output_retries",
                "num_turns": 12, "total_cost_usd": 0.41}
    call, _ = fake_llm([LLMError("claude reported an error: "
                                 "error_max_structured_output_retries",
                                 envelope=envelope)])
    monkeypatch.setattr(research, "complete_claude_code", call)
    research.run([APP], concurrency=1)
    saved = json.loads((isolate / "raw" / "81.json").read_text())
    assert saved["envelope"]["subtype"] == "error_max_structured_output_retries"


# --- app selection ---------------------------------------------------------

def test_select_by_name_is_case_insensitive():
    apps = research.load_apps()
    assert research.select_apps(apps, only=["stripe"])[0]["id"] == 81


def test_select_unknown_name_fails_loudly():
    with pytest.raises(SystemExit, match="unknown app"):
        research.select_apps(research.load_apps(), only=["Nonexistent App"])


def test_select_by_ids():
    chosen = research.select_apps(research.load_apps(), ids=[1, 58, 81])
    assert [a["id"] for a in chosen] == [1, 58, 81]


def test_consistency_errors_are_flagged_at_write_time(monkeypatch):
    """Stripe v1 really produced primary_auth=api_key with api_key absent."""
    call, _ = fake_llm([{**GOOD, "auth_methods": ["basic", "oauth2"],
                         "primary_auth": "api_key"}])
    monkeypatch.setattr(research, "complete_claude_code", call)
    record = research.research_app(APP)
    assert record.needs_human is True
    assert "primary_auth_not_in_list" in record.needs_human_reason
    assert record.verification["consistency"]


def test_clean_record_records_no_consistency_problems(monkeypatch):
    call, _ = fake_llm([GOOD])
    monkeypatch.setattr(research, "complete_claude_code", call)
    assert "consistency" not in research.research_app(APP).verification
