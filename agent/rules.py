"""Deterministic verdict rules and Loop E consistency checks (brief sections 4, 7).

The brief lists four verdict rules, but they overlap (a self-serve app can also
need app review) and they are not exhaustive (nothing covers a self-serve app
whose only interface is a local CLI). So this module fixes an explicit precedence
order and adds a fallback that marks the case as *uncovered* rather than guessing.

Decisions taken for the gaps are recorded in docs/DECISIONS.md:
  D10  api_type == [cli_or_library] -> not_viable, blocker local_only_tool.
       The brief asked us to "say which"; a local tool is viable as a local skill
       but not as a hosted toolkit, and blocker_notes carries that nuance.
  D11  blocker == app_review outranks self-serve access -> ready_with_friction.

apply_rules() is pure and total: it never mutates the record and always returns a
valid Verdict. The caller applies the result, which keeps this trivially testable.
"""

from __future__ import annotations

from typing import NamedTuple, Optional

from agent.schema import Access, ApiType, AppRecord, Blocker, ExistingMcp, Verdict

RULES_VERSION = "1.0"

_API_OK = {ApiType.REST, ApiType.GRAPHQL}
_SELF_SERVE = {Access.SELF_SERVE_FREE, Access.SELF_SERVE_TRIAL}
_FRICTION_ACCESS = {Access.PAID_PLAN, Access.ADMIN_APPROVAL}
_NO_HOSTED_API = ({ApiType.NONE}, {ApiType.CLI_OR_LIBRARY})


class RuleResult(NamedTuple):
    """Outcome of applying the rules. Immutable; _asdict() goes into verify_log."""

    verdict: Verdict   # authoritative -- the rule always wins over the LLM
    rule_id: str       # "R1".."R6", shown on the page and in the log
    covered: bool      # False => the brief was silent here; escalate to a human
    disagrees: bool    # True => the LLM answered, and answered differently
    reason: str        # one human-readable sentence


def _value(enum_or_none) -> str:
    return getattr(enum_or_none, "value", str(enum_or_none))


def apply_rules(record: AppRecord) -> RuleResult:
    """Return the deterministic verdict for a record. Never mutates it."""
    api = {ApiType(_value(a)) for a in (record.api_type or [])}
    access = Access(_value(record.access)) if record.access is not None else None
    blocker = Blocker(_value(record.blocker)) if record.blocker is not None else None

    if access == Access.NO_PUBLIC_API:
        verdict, rule_id, covered = Verdict.NOT_VIABLE, "R1", True
        reason = "access=no_public_api"

    elif not api or api in _NO_HOSTED_API:
        verdict, rule_id, covered = Verdict.NOT_VIABLE, "R2", True
        listed = sorted(a.value for a in api) or "[]"
        reason = f"api_type={listed} exposes no hosted API"

    elif access == Access.PARTNER_GATED:
        verdict, rule_id, covered = Verdict.NEEDS_OUTREACH, "R3", True
        reason = "access=partner_gated"

    elif access in _FRICTION_ACCESS or blocker == Blocker.APP_REVIEW:
        verdict, rule_id, covered = Verdict.READY_WITH_FRICTION, "R4", True
        reason = f"access={_value(access)}, blocker={_value(blocker)}"

    elif access in _SELF_SERVE and api & _API_OK:
        verdict, rule_id, covered = Verdict.READY, "R5", True
        reason = "self-serve access and a documented REST/GraphQL API"

    else:
        # The brief is silent here. Default to the honest middle and always
        # escalate -- never silently call an unknown shape "ready".
        verdict, rule_id, covered = Verdict.READY_WITH_FRICTION, "R6", False
        reason = (
            f"no rule covers access={_value(access)} "
            f"api_type={sorted(a.value for a in api)}; defaulted, needs human"
        )

    # Compare by value: model_copy(update=...) skips validation, so a caller
    # (e.g. verify.py applying a correction) can hand us a raw string here.
    disagrees = record.verdict is not None and _value(record.verdict) != verdict.value
    if disagrees:
        reason += f" (LLM said {_value(record.verdict)}, rule keeps {verdict.value})"

    return RuleResult(verdict, rule_id, covered, disagrees, reason)


def rule_needs_human(result: RuleResult) -> tuple[bool, Optional[str]]:
    """Map a RuleResult to (needs_human, reason). Applied by research.py."""
    if not result.covered:
        return True, f"verdict_rule_uncovered ({result.rule_id}): {result.reason}"
    if result.disagrees:
        return True, f"rule_llm_disagreement ({result.rule_id}): {result.reason}"
    return False, None


# --------------------------------------------------------------------------
# Loop E -- deterministic consistency checks (brief section 7)
# This module only *detects*. verify.py decides what to do with each severity.
# --------------------------------------------------------------------------

class Violation(NamedTuple):
    name: str       # stable id, used in verify_log.json and on the page
    severity: str   # "error" -> re-research + needs_human; "warn" -> log only
    message: str


def check_consistency(record: AppRecord) -> list[Violation]:
    """Return every internal contradiction found in a record."""
    out: list[Violation] = []
    api = {ApiType(_value(a)) for a in (record.api_type or [])}

    def add(name: str, severity: str, message: str) -> None:
        out.append(Violation(name, severity, message))

    if _value(record.access) == "no_public_api" and _value(record.api_breadth) == "broad":
        add("no_api_but_broad", "error",
            "access=no_public_api but api_breadth=broad")

    if _value(record.existing_mcp) in ("official", "community") and not record.mcp_url:
        add("mcp_without_url", "error",
            f"existing_mcp={_value(record.existing_mcp)} but mcp_url is empty")

    if record.mcp_url and _value(record.existing_mcp) == "none_found":
        add("mcp_url_without_mcp", "warn",
            "mcp_url is set but existing_mcp=none_found")

    if _value(record.verdict) == "ready" and _value(record.blocker) not in ("None", "none"):
        add("ready_with_blocker", "error",
            f"verdict=ready but blocker={_value(record.blocker)}")

    if _value(record.verdict) == "not_viable" and api & _API_OK:
        add("not_viable_with_api", "error",
            "verdict=not_viable but api_type includes rest/graphql")

    if record.primary_auth and _value(record.primary_auth) not in [
            _value(a) for a in record.auth_methods]:
        add("primary_auth_not_in_list", "error",
            f"primary_auth={_value(record.primary_auth)} not in auth_methods")

    if ApiType.NONE in api and len(api) > 1:
        add("api_type_none_mixed", "error",
            "api_type contains 'none' alongside other values")

    if _value(record.verdict) == "needs_outreach" and _value(record.access) != "partner_gated":
        add("outreach_without_gate", "error",
            f"verdict=needs_outreach but access={_value(record.access)}")

    for item in record.evidence:
        if not item.url.startswith(("http://", "https://")):
            add("evidence_url_not_http", "error",
                f"evidence url is not a URL: {item.url!r}")
            break

    if record.docs_url is None and record.confidence >= 0.7:
        add("no_docs_url_but_confident", "warn",
            f"confidence={record.confidence} with no docs_url")

    if record.missing_evidence_for:
        add("missing_required_evidence", "warn",
            "no evidence for: " + ",".join(record.missing_evidence_for))

    # E15: after research.py applies the rules this must never fire on stored
    # data. If it does, the JSON was hand-edited.
    if record.verdict is not None and _value(record.verdict) != apply_rules(record).verdict.value:
        add("verdict_not_rule_verdict", "error",
            f"stored verdict={_value(record.verdict)} != rule verdict")

    return out
