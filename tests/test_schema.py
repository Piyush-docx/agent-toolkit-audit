"""Schema behaviour (PROJECT_BRIEF.md section 4).

Focus: the edge cases that decide whether a real pipeline run survives imperfect
LLM output. Trivial field access is not tested.
"""
import pytest
from pydantic import ValidationError

from agent.schema import (
    Access,
    AppRecord,
    ApiBreadth,
    ApiType,
    AuthMethod,
    Evidence,
    PassName,
    Verdict,
    dump_record,
)

MINIMAL = {"id": 1, "name": "Salesforce", "category": "CRM & Sales"}


# --- the `pass` reserved-keyword alias -------------------------------------

def test_pass_alias_parses_from_json():
    rec = AppRecord.model_validate({**MINIMAL, "pass": "v2"})
    assert rec.pass_ is PassName.V2


def test_pass_alias_round_trips():
    dumped = dump_record(AppRecord.model_validate(MINIMAL))
    assert dumped["pass"] == "v1"
    assert "pass_" not in dumped


def test_populate_by_name_accepts_python_attr():
    assert AppRecord(**MINIMAL, pass_="v2").pass_ is PassName.V2


# --- tolerance of partial / messy LLM output -------------------------------

def test_minimal_record_parses_with_honest_defaults():
    rec = AppRecord.model_validate(MINIMAL)
    assert rec.verdict is None          # None = the LLM did not answer; rules fill it
    assert rec.access is None
    assert rec.auth_methods == []
    assert rec.api_type == []
    assert rec.api_breadth is ApiBreadth.UNKNOWN
    assert rec.confidence == 0.0


def test_partial_llm_response_parses():
    rec = AppRecord.model_validate({
        **MINIMAL,
        "auth_methods": ["oauth2"],
        "access": "self_serve_trial",
        "confidence": 0.5,
    })
    assert rec.auth_methods == [AuthMethod.OAUTH2]
    assert rec.access is Access.SELF_SERVE_TRIAL


def test_unknown_extra_key_is_ignored():
    rec = AppRecord.model_validate({**MINIMAL, "notes": "model added this"})
    assert not hasattr(rec, "notes")


def test_verification_default_is_not_shared():
    a, b = AppRecord.model_validate(MINIMAL), AppRecord.model_validate(MINIMAL)
    a.verification["auth_methods"] = {"status": "supported"}
    assert b.verification == {}


# --- word limits are hard errors (length is the model's job) ---------------

def test_one_liner_15_words_ok():
    text = " ".join(["word"] * 15)
    assert AppRecord.model_validate({**MINIMAL, "one_liner": text}).one_liner == text


def test_one_liner_16_words_rejected():
    with pytest.raises(ValidationError, match="15 words"):
        AppRecord.model_validate({**MINIMAL, "one_liner": " ".join(["word"] * 16)})


def test_one_liner_whitespace_normalised_before_counting():
    rec = AppRecord.model_validate({**MINIMAL, "one_liner": "  CRM   platform \n"})
    assert rec.one_liner == "CRM platform"


def test_quote_40_words_ok():
    Evidence(field="access", url="https://x.dev", quote=" ".join(["w"] * 40))


def test_quote_41_words_rejected():
    with pytest.raises(ValidationError, match="40 words"):
        Evidence(field="access", url="https://x.dev", quote=" ".join(["w"] * 41))


# --- strictness where it belongs -------------------------------------------

def test_invalid_enum_value_rejected():
    with pytest.raises(ValidationError):
        AppRecord.model_validate({**MINIMAL, "access": "freemium"})


@pytest.mark.parametrize("bad", [1.5, -0.1])
def test_confidence_out_of_bounds_rejected(bad):
    with pytest.raises(ValidationError):
        AppRecord.model_validate({**MINIMAL, "confidence": bad})


def test_evidence_field_name_must_be_known():
    """A typo'd field name would otherwise look like missing evidence."""
    with pytest.raises(ValidationError):
        Evidence(field="auth", url="https://x.dev", quote="q")


# --- evidence coverage is a SOFT flag (decision D13) -----------------------

def _evidence_for_all_required():
    return [
        {"field": f, "url": "https://docs.example.com", "quote": "q"}
        for f in ("auth_methods", "access", "api_type", "existing_mcp", "verdict")
    ]


def test_missing_evidence_flags_instead_of_raising():
    rec = AppRecord.model_validate(MINIMAL)          # must NOT raise
    assert set(rec.missing_evidence_for) == {
        "auth_methods", "access", "api_type", "existing_mcp", "verdict"
    }
    assert rec.needs_human is True
    assert "missing_evidence" in rec.needs_human_reason


def test_full_evidence_sets_no_flag():
    rec = AppRecord.model_validate({**MINIMAL, "evidence": _evidence_for_all_required()})
    assert rec.missing_evidence_for == []
    assert rec.needs_human is False


def test_existing_needs_human_reason_not_overwritten():
    rec = AppRecord.model_validate({
        **MINIMAL, "needs_human": True, "needs_human_reason": "ambiguous identity",
    })
    assert rec.needs_human_reason == "ambiguous identity"


# --- the schema is embedded in the P2 prompt -------------------------------

def test_json_schema_generates():
    schema = AppRecord.model_json_schema()
    assert "pass" in schema["properties"]
    assert "pass_" not in schema["properties"]


@pytest.mark.parametrize("raw,expected", [
    ("Checkout &amp; payments", "Checkout & payments"),
    ("A &lt;b&gt; tag", "A <b> tag"),
    ("plain text", "plain text"),
])
def test_html_entities_are_unescaped(raw, expected):
    """fanbasis v1 really produced 'Creator/seller checkout &amp; payments'."""
    assert AppRecord.model_validate({**MINIMAL, "one_liner": raw}).one_liner == expected
