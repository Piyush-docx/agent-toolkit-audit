"""Deterministic verdict rules and Loop E consistency checks.

The brief's four rules overlap and are not exhaustive. These tests pin the
precedence order and the decisions taken for the gaps (D10-D11 in DECISIONS.md).
"""
import itertools

import pytest

from agent.rules import apply_rules, check_consistency, rule_needs_human
from agent.schema import Access, ApiType, Blocker, Verdict, AppRecord


# --- one test per rule -----------------------------------------------------

def test_r1_no_public_api(make_record):
    r = apply_rules(make_record(access="no_public_api", api_type=["rest"]))
    assert (r.verdict, r.rule_id, r.covered) == (Verdict.NOT_VIABLE, "R1", True)


def test_r2_api_type_none(make_record):
    r = apply_rules(make_record(access="self_serve_free", api_type=["none"]))
    assert (r.verdict, r.rule_id) == (Verdict.NOT_VIABLE, "R2")


def test_r2_empty_api_type_is_covered(make_record):
    """G4: an empty list is treated as [none], not as an uncovered gap."""
    r = apply_rules(make_record(access="self_serve_free", api_type=[]))
    assert (r.verdict, r.rule_id, r.covered) == (Verdict.NOT_VIABLE, "R2", True)


@pytest.mark.parametrize("app", ["Sherlock", "Mermaid CLI"])
def test_cli_only_tools_are_not_viable(make_record, app):
    """D10: local-only tools are not viable as *hosted* toolkits."""
    r = apply_rules(make_record(name=app, access="self_serve_free",
                                api_type=["cli_or_library"]))
    assert (r.verdict, r.rule_id, r.covered) == (Verdict.NOT_VIABLE, "R2", True)


def test_r3_partner_gated_beats_a_working_rest_api(make_record):
    r = apply_rules(make_record(access="partner_gated", api_type=["rest"]))
    assert (r.verdict, r.rule_id) == (Verdict.NEEDS_OUTREACH, "R3")


def test_r3_beats_app_review(make_record):
    """G10: a partner gate cannot be bought past; it outranks app review."""
    r = apply_rules(make_record(access="partner_gated", api_type=["rest"],
                                blocker="app_review"))
    assert r.verdict is Verdict.NEEDS_OUTREACH


@pytest.mark.parametrize("access", ["paid_plan", "admin_approval"])
def test_r4_friction_access(make_record, access):
    r = apply_rules(make_record(access=access, api_type=["rest"]))
    assert (r.verdict, r.rule_id) == (Verdict.READY_WITH_FRICTION, "R4")


def test_r4_app_review_beats_self_serve(make_record):
    """D11, the Meta case: app review is real friction even on a free tier."""
    r = apply_rules(make_record(access="self_serve_free", api_type=["rest"],
                                blocker="app_review"))
    assert (r.verdict, r.rule_id, r.covered) == (Verdict.READY_WITH_FRICTION, "R4", True)


@pytest.mark.parametrize("api", ["rest", "graphql"])
@pytest.mark.parametrize("access", ["self_serve_free", "self_serve_trial"])
def test_r5_ready(make_record, access, api):
    r = apply_rules(make_record(access=access, api_type=[api]))
    assert (r.verdict, r.rule_id) == (Verdict.READY, "R5")


# --- the uncovered gaps must be visible, never silently "ready" ------------

@pytest.mark.parametrize("api_type", [["sdk_only"], ["websocket"], ["soap"]])
def test_r6_uncovered_shapes_flag_for_human(make_record, api_type):
    r = apply_rules(make_record(access="self_serve_free", api_type=api_type))
    assert r.rule_id == "R6"
    assert r.covered is False
    assert r.verdict is Verdict.READY_WITH_FRICTION
    assert rule_needs_human(r)[0] is True


def test_r6_missing_access_is_uncovered(make_record):
    """G8: a partial LLM response must not be scored as ready."""
    r = apply_rules(make_record(api_type=["rest"]))
    assert r.covered is False


# --- rule vs LLM disagreement ---------------------------------------------

def test_disagreement_keeps_the_rule_verdict(make_record):
    r = apply_rules(make_record(access="partner_gated", api_type=["rest"],
                                verdict="ready"))
    assert r.verdict is Verdict.NEEDS_OUTREACH     # rule wins
    assert r.disagrees is True
    assert "ready" in r.reason and "needs_outreach" in r.reason
    assert rule_needs_human(r)[0] is True


def test_no_disagreement_when_llm_gave_no_verdict(make_record):
    assert apply_rules(make_record(access="partner_gated")).disagrees is False


def test_agreement_does_not_flag_a_human(make_record):
    r = apply_rules(make_record(access="self_serve_free", api_type=["rest"],
                                verdict="ready"))
    assert (r.disagrees, rule_needs_human(r)[0]) == (False, False)


# --- purity and totality ---------------------------------------------------

def test_apply_rules_does_not_mutate_the_record(make_record):
    rec = make_record(access="partner_gated", api_type=["rest"], verdict="ready")
    before = rec.model_dump()
    apply_rules(rec)
    assert rec.model_dump() == before


def test_apply_rules_is_total(make_record):
    """Every reachable input shape yields a valid Verdict and never raises."""
    accesses = [None] + [a.value for a in Access]
    blockers = [None] + [b.value for b in Blocker]
    api_types = [[], ["none"], ["rest"], ["graphql"], ["cli_or_library"],
                 ["sdk_only"], ["websocket"], ["rest", "graphql"]]
    for access, blocker, api in itertools.product(accesses, blockers, api_types):
        r = apply_rules(make_record(access=access, blocker=blocker, api_type=api))
        assert isinstance(r.verdict, Verdict)
        assert r.rule_id in {"R1", "R2", "R3", "R4", "R5", "R6"}
        # NOT_RESEARCHED is reserved for research.py's failure path -- a rule
        # must never assign it, or a crash could masquerade as a real finding.
        assert r.verdict is not Verdict.NOT_RESEARCHED


# --- Loop E consistency checks --------------------------------------------

def _clean(make_record) -> AppRecord:
    rec = make_record(
        access="self_serve_free", api_type=["rest"], api_breadth="broad",
        auth_methods=["oauth2"], primary_auth="oauth2", verdict="ready",
        blocker="none", docs_url="https://docs.example.com", confidence=0.9,
        evidence=[{"field": f, "url": "https://docs.example.com", "quote": "q"}
                  for f in ("auth_methods", "access", "api_type",
                            "existing_mcp", "verdict")],
    )
    return rec


def test_clean_record_has_no_violations(make_record):
    assert check_consistency(_clean(make_record)) == []


@pytest.mark.parametrize(
    "name,overrides",
    [
        ("no_api_but_broad", {"access": "no_public_api", "api_breadth": "broad"}),
        ("mcp_without_url", {"existing_mcp": "official", "mcp_url": None}),
        ("ready_with_blocker", {"verdict": "ready", "blocker": "paid_plan"}),
        ("not_viable_with_api", {"verdict": "not_viable", "api_type": ["rest"]}),
        ("primary_auth_not_in_list", {"auth_methods": ["oauth2"],
                                      "primary_auth": "api_key"}),
        ("api_type_none_mixed", {"api_type": ["rest", "none"]}),
        ("outreach_without_gate", {"verdict": "needs_outreach",
                                   "access": "self_serve_free"}),
        ("mcp_url_without_mcp", {"existing_mcp": "none_found",
                                 "mcp_url": "https://x.dev/mcp"}),
    ],
)
def test_each_consistency_check_fires(make_record, name, overrides):
    rec = _clean(make_record).model_copy(update=overrides)
    assert name in {v.name for v in check_consistency(rec)}


def test_evidence_url_must_be_http(make_record):
    rec = _clean(make_record)
    rec.evidence[0].url = "docs.example.com"
    assert "evidence_url_not_http" in {v.name for v in check_consistency(rec)}


def test_verdict_must_match_the_rules(make_record):
    """E15: guards against hand-edited JSON."""
    rec = _clean(make_record).model_copy(update={"verdict": Verdict.NOT_VIABLE})
    assert "verdict_not_rule_verdict" in {v.name for v in check_consistency(rec)}
