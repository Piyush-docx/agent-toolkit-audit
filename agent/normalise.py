"""Canonicalisation shared by scoring (section 8) and consistency checks (Loop E).

Human ground-truth labels are free text -- "OAuth 2.0", "OAuth2", "oauth_2" all
mean the same thing. Both sides are reduced to a single canonical token before
being compared.

Canonical forms are *exactly* the enum values in schema.py. There is deliberately
no second vocabulary; test_every_alias_target_is_a_real_enum_value keeps it honest.
"""

from __future__ import annotations

import re

from agent.schema import (
    Access,
    ApiBreadth,
    ApiType,
    AuthMethod,
    Blocker,
    ExistingMcp,
    Verdict,
    YesNoUnknown,
)

# Which enum is legal for each field. Used to short-circuit the alias table so a
# token that is already valid for its field is never rewritten.
VALID_VALUES: dict[str, set[str]] = {
    "auth_methods": {e.value for e in AuthMethod},
    "primary_auth": {e.value for e in AuthMethod},
    "access": {e.value for e in Access},
    "api_type": {e.value for e in ApiType},
    "api_breadth": {e.value for e in ApiBreadth},
    "existing_mcp": {e.value for e in ExistingMcp},
    "verdict": {e.value for e in Verdict},
    "blocker": {e.value for e in Blocker},
    "webhooks": {e.value for e in YesNoUnknown},
    "openapi_spec": {e.value for e in YesNoUnknown},
    "sandbox_or_test_mode": {e.value for e in YesNoUnknown},
    "rate_limits_documented": {e.value for e in YesNoUnknown},
    "on_composio": {e.value for e in YesNoUnknown},
}

LIST_FIELDS = {"auth_methods", "api_type"}

# Small and hand-written on purpose: every entry is defensible in an interview.
ALIASES: dict[str, str] = {
    # auth
    "oauth": "oauth2", "oauth_2": "oauth2", "oauth_2_0": "oauth2",
    "oauth2_0": "oauth2", "o_auth2": "oauth2",
    "apikey": "api_key", "api_keys": "api_key", "key": "api_key",
    "bearer": "bearer_token", "token": "bearer_token",
    "personal_access_token": "bearer_token", "pat": "bearer_token",
    "basic_auth": "basic", "http_basic": "basic",
    "hmac": "hmac_signature", "signature": "hmac_signature",
    "json_web_token": "jwt",
    # api type
    "restful": "rest", "rest_api": "rest", "http": "rest", "json_rest": "rest",
    "graph_ql": "graphql", "gql": "graphql",
    "ws": "websocket", "web_socket": "websocket",
    "sdk": "sdk_only", "library_only": "sdk_only",
    "cli": "cli_or_library", "local_cli": "cli_or_library",
    "library": "cli_or_library",
    # access
    "free": "self_serve_free", "free_tier": "self_serve_free",
    "trial": "self_serve_trial", "free_trial": "self_serve_trial",
    "paid": "paid_plan", "enterprise": "paid_plan", "paid_tier": "paid_plan",
    "sales_gated": "partner_gated", "contact_sales": "partner_gated",
    "partner": "partner_gated", "partnership": "partner_gated",
    "no_api": "no_public_api", "none_public": "no_public_api",
    # mcp -- note these are only reached when the field is not api_type,
    # because norm_field short-circuits on already-valid values.
    "not_found": "none_found", "no_mcp": "none_found",
    # yes/no
    "true": "yes", "y": "yes", "false": "no", "n": "no",
    "unk": "unknown", "": "unknown",
}

_SEPARATORS = re.compile(r"[\s\-\./]+")
_UNDERSCORES = re.compile(r"_+")


def norm_token(value) -> str:
    """'OAuth 2.0' -> 'oauth2'. Lowercase, collapse separators, then alias-map."""
    text = _SEPARATORS.sub("_", str(value).strip().lower())
    text = _UNDERSCORES.sub("_", text).strip("_")
    return ALIASES.get(text, text or "unknown")


def norm_list(values) -> tuple[str, ...]:
    """Accept a list or a 'a; b, c' string; return a sorted, de-duped tuple."""
    if isinstance(values, str):
        values = re.split(r"[;,|]", values)
    return tuple(sorted({norm_token(v) for v in values if str(v).strip()}))


def _norm_for_field(field: str, value) -> str:
    """Alias-map, but never rewrite a token that is already valid for this field.

    This is what keeps `none` meaning `none` for api_type while still mapping to
    `none_found` for existing_mcp.
    """
    raw = _UNDERSCORES.sub("_", _SEPARATORS.sub("_", str(value).strip().lower())).strip("_")
    if raw in VALID_VALUES.get(field, set()):
        return raw
    if field == "existing_mcp" and raw in {"none", "no"}:
        return "none_found"
    return norm_token(value)


def norm_field(field: str, value):
    """Dispatch: list fields -> sorted tuple, everything else -> single token."""
    if field in LIST_FIELDS:
        if isinstance(value, str):
            value = re.split(r"[;,|]", value)
        return tuple(sorted({
            _norm_for_field(field, v) for v in value if str(v).strip()
        }))
    return _norm_for_field(field, value)
