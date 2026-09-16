"""Canonicalisation shared by scoring (section 8) and consistency checks (Loop E)."""
import pytest

from agent.normalise import ALIASES, VALID_VALUES, norm_field, norm_list, norm_token


@pytest.mark.parametrize(
    "raw", ["OAuth2", "oauth 2.0", "OAuth 2", "oauth_2", "OAUTH2", " oauth2 "]
)
def test_auth_aliases_collapse_to_oauth2(raw):
    assert norm_token(raw) == "oauth2"


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("API Key", "api_key"),
        ("Personal Access Token", "bearer_token"),
        ("HTTP Basic", "basic"),
        ("REST API", "rest"),
        ("GraphQL", "graphql"),
        ("Contact Sales", "partner_gated"),
        ("Free Trial", "self_serve_trial"),
    ],
)
def test_common_human_labels(raw, expected):
    assert norm_token(raw) == expected


def test_list_is_order_independent():
    assert norm_list(["rest", "graphql"]) == norm_list(["graphql", "rest"])


def test_list_dedupes():
    assert norm_list(["rest", "REST", "rest_api"]) == ("rest",)


def test_list_from_delimited_string():
    assert norm_list("oauth2; api_key") == ("api_key", "oauth2")


def test_empty_values_dropped():
    assert norm_list(["rest", "", "  "]) == ("rest",)


@pytest.mark.parametrize("raw", ["", "   ", "unk"])
def test_blank_becomes_unknown(raw):
    assert norm_token(raw) == "unknown"


def test_none_resolves_per_field():
    """`none` is a real api_type value but means none_found for existing_mcp."""
    assert norm_field("api_type", "none") == ("none",)
    assert norm_field("existing_mcp", "none") == "none_found"


def test_norm_field_dispatches_lists():
    assert norm_field("auth_methods", "OAuth2, API Key") == ("api_key", "oauth2")
    assert norm_field("access", "Contact Sales") == "partner_gated"


def test_every_alias_target_is_a_real_enum_value():
    """Guards the alias table against drifting from schema.py."""
    known = set().union(*VALID_VALUES.values())
    unknown = {t for t in ALIASES.values() if t not in known}
    assert not unknown, f"alias targets not in any enum: {unknown}"
