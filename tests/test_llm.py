"""LLM backend plumbing. subprocess is mocked, so these never hit the network."""
import json
import subprocess

import pytest

from agent import llm


def _envelope(**overrides):
    base = {
        "is_error": False, "result": '{"ok": true}',
        "structured_output": {"ok": True}, "total_cost_usd": 0.12,
        "num_turns": 3, "session_id": "abc", "subtype": "success",
        "permission_denials": [],
    }
    return json.dumps({**base, **overrides})


@pytest.fixture
def fake_run(monkeypatch):
    calls = {}

    def _install(stdout="", returncode=0, stderr="", exc=None):
        def fake(cmd, **kwargs):
            calls["cmd"] = cmd
            if exc:
                raise exc
            return subprocess.CompletedProcess(cmd, returncode, stdout, stderr)
        monkeypatch.setattr(llm.subprocess, "run", fake)
        return calls

    return _install


def test_builds_the_verified_flag_set(fake_run):
    calls = fake_run(stdout=_envelope())
    llm.complete_claude_code("hi", schema={"type": "object"}, model="sonnet")
    cmd = calls["cmd"]
    assert cmd[:2] == ["claude", "-p"]
    for flag in ("--output-format", "--model", "--max-turns",
                 "--allowedTools", "--json-schema"):
        assert flag in cmd
    assert "WebSearch" in cmd and "WebFetch" in cmd


def test_omits_schema_flag_when_no_schema(fake_run):
    calls = fake_run(stdout=_envelope())
    llm.complete_claude_code("hi", schema=None)
    assert "--json-schema" not in calls["cmd"]


def test_prefers_structured_output(fake_run):
    fake_run(stdout=_envelope())
    assert llm.complete_claude_code("hi").data == {"ok": True}


def test_records_usage(fake_run):
    fake_run(stdout=_envelope())
    result = llm.complete_claude_code("hi")
    assert result.cost_usd == 0.12
    assert result.num_turns == 3


def test_falls_back_to_parsing_raw_result(fake_run):
    fake_run(stdout=_envelope(structured_output=None, result='{"a": 1}'))
    assert llm.complete_claude_code("hi").data == {"a": 1}


def test_recovers_json_from_a_fenced_block(fake_run):
    fake_run(stdout=_envelope(structured_output=None,
                              result='```json\n{"a": 2}\n```'))
    assert llm.complete_claude_code("hi").data == {"a": 2}


def test_recovers_json_after_leading_prose(fake_run):
    fake_run(stdout=_envelope(structured_output=None,
                              result='Here you go:\n{"a": 3}'))
    assert llm.complete_claude_code("hi").data == {"a": 3}


def test_unparseable_output_gives_none_but_keeps_raw(fake_run):
    fake_run(stdout=_envelope(structured_output=None, result="no json here"))
    result = llm.complete_claude_code("hi")
    assert result.data is None
    assert result.raw == "no json here"      # kept for the cache / audit trail


def test_nonzero_exit_raises(fake_run):
    fake_run(stdout="", returncode=1, stderr="boom")
    with pytest.raises(llm.LLMError, match="exited 1"):
        llm.complete_claude_code("hi")


def test_usage_limit_is_flagged_for_resume(fake_run):
    """P3 must be able to tell 'retry later' from 'broken' and save progress."""
    fake_run(stdout="", returncode=1, stderr="Claude usage limit reached; resets at 5pm")
    with pytest.raises(llm.LLMError) as excinfo:
        llm.complete_claude_code("hi")
    assert excinfo.value.usage_limited is True


def test_ordinary_failure_is_not_usage_limited(fake_run):
    fake_run(stdout="", returncode=1, stderr="segfault")
    with pytest.raises(llm.LLMError) as excinfo:
        llm.complete_claude_code("hi")
    assert excinfo.value.usage_limited is False


def test_is_error_envelope_raises(fake_run):
    fake_run(stdout=_envelope(is_error=True, result="model overloaded"))
    with pytest.raises(llm.LLMError, match="overloaded"):
        llm.complete_claude_code("hi")


def test_non_json_stdout_raises(fake_run):
    fake_run(stdout="totally not json")
    with pytest.raises(llm.LLMError, match="not JSON"):
        llm.complete_claude_code("hi")


def test_timeout_raises(fake_run):
    fake_run(exc=subprocess.TimeoutExpired("claude", 600))
    with pytest.raises(llm.LLMError, match="timed out"):
        llm.complete_claude_code("hi")


# --- backend resolution ----------------------------------------------------

def test_default_backend_is_claude_code(monkeypatch):
    monkeypatch.delenv("LLM_BACKEND", raising=False)
    assert llm.get_backend() is llm.complete_claude_code


def test_anthropic_backend_requires_a_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(llm.LLMError, match="ANTHROPIC_API_KEY"):
        llm.get_backend("anthropic_api")


def test_unknown_backend_raises(monkeypatch):
    monkeypatch.delenv("LLM_BACKEND", raising=False)
    with pytest.raises(llm.LLMError, match="unknown backend"):
        llm.get_backend("gpt")
