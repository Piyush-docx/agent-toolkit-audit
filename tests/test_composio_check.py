"""The 'already on Composio?' check.

Uses a fixture copy of the real index format so tests never hit the network.
"""
from unittest.mock import MagicMock, patch

import pytest

from agent.composio_check import (
    fetch_toolkits,
    is_composio_mcp_toolkit,
    lookup,
    parse_toolkits,
)

INDEX = """# Toolkits

| Toolkit | Slug | Tools | Triggers | Auth | Managed App |
|---------|------|-------|----------|------|-------------|
| [Stripe](/toolkits/stripe.md) | `STRIPE` | 432 | 40 | API_KEY | Yes |
| [Google Ads](/toolkits/googleads.md) | `GOOGLEADS` | 20 | 0 | OAUTH2 | Yes |
| [Clay MCP](/toolkits/claymcp.md) | `CLAY_MCP` | 5 | 0 | API_KEY | — |
| [Highlevel](/toolkits/highlevel.md) | `HIGHLEVEL` | 12 | 0 | OAUTH2 | — |
| [Gladia](/toolkits/gladia.md) | `GLADIA` | 3 | 0 | API_KEY | — |
| [Square](/toolkits/square.md) | `SQUARE` | 9 | 0 | OAUTH2 | — |
"""


@pytest.fixture(scope="module")
def toolkits():
    return parse_toolkits(INDEX)


def test_parses_every_row(toolkits):
    assert len(toolkits) == 6
    assert toolkits["stripe"] == "STRIPE"


def test_exact_name_match(toolkits):
    assert lookup("Stripe", toolkits) == ("yes", "STRIPE")


def test_match_is_case_and_space_insensitive(toolkits):
    """Composio's slug is not derivable from the name: 'Google Ads' -> googleads."""
    assert lookup("Google Ads", toolkits)[0] == "yes"


def test_mcp_suffix_is_matched(toolkits):
    """Clay is listed only as 'Clay MCP'; without this it was a false negative."""
    assert lookup("Clay", toolkits) == ("yes", "CLAY_MCP")


def test_alias_match(toolkits):
    assert lookup("GoHighLevel", toolkits) == ("yes", "HIGHLEVEL")


@pytest.mark.parametrize("app", ["Gladly", "Squarespace", "PitchBook", "Sherlock"])
def test_similar_but_different_products_are_not_matched(toolkits, app):
    """Gladly != Gladia, Squarespace != Square. A false 'yes' is worse than a 'no'."""
    assert lookup(app, toolkits) == ("no", None)


def test_absence_is_meaningful():
    """The index is complete, so 'no' is evidence, not ignorance (supersedes D8)."""
    assert lookup("Totally Made Up App", parse_toolkits(INDEX)) == ("no", None)


@pytest.mark.parametrize(
    "slug,expected", [("CLAY_MCP", True), ("STRIPE", False), (None, False)]
)
def test_mcp_toolkit_detection(slug, expected):
    assert is_composio_mcp_toolkit(slug) is expected


# --- SDK path (mocked -- never hits the network or needs a real key) -------

def _fake_toolkit(name, slug):
    item = MagicMock()
    item.name = name
    item.slug = slug
    return item


def _fake_client(pages):
    """pages: list of (items, next_cursor) tuples simulating cursor pagination."""
    client = MagicMock()
    responses = []
    for items, next_cursor in pages:
        resp = MagicMock()
        resp.items = items
        resp.next_cursor = next_cursor
        responses.append(resp)
    client.client.toolkits.list.side_effect = responses
    return client


def test_fetch_toolkits_via_sdk_paginates_until_no_next_cursor(monkeypatch):
    from agent import composio_check

    page1 = ([_fake_toolkit("Stripe", "stripe")], "cursor2")
    page2 = ([_fake_toolkit("Gmail", "gmail")], None)
    fake = _fake_client([page1, page2])

    with patch("composio.Composio", return_value=fake):
        result = composio_check.fetch_toolkits_via_sdk()

    assert result == {"stripe": "stripe", "gmail": "gmail"}
    assert fake.client.toolkits.list.call_count == 2


def test_fetch_toolkits_prefers_sdk_when_key_present(monkeypatch):
    from agent import composio_check

    monkeypatch.setenv("COMPOSIO_API_KEY", "ck_test_key")
    monkeypatch.setattr(composio_check, "fetch_toolkits_via_sdk",
                        lambda: {"stripe": "stripe"})

    def _should_not_be_called(*a, **kw):
        raise AssertionError("keyless fallback should not run when SDK succeeds")
    monkeypatch.setattr(composio_check, "fetch_index", _should_not_be_called)

    assert fetch_toolkits() == {"stripe": "stripe"}


def test_fetch_toolkits_falls_back_when_sdk_raises(monkeypatch):
    from agent import composio_check

    monkeypatch.setenv("COMPOSIO_API_KEY", "ck_test_key")

    def _raise():
        raise RuntimeError("network down")
    monkeypatch.setattr(composio_check, "fetch_toolkits_via_sdk", _raise)
    monkeypatch.setattr(composio_check, "fetch_index", lambda **kw: INDEX)

    result = fetch_toolkits()
    assert result["stripe"] == "STRIPE"  # came from the keyless INDEX fixture


def test_fetch_toolkits_uses_keyless_index_when_no_key(monkeypatch):
    from agent import composio_check

    monkeypatch.delenv("COMPOSIO_API_KEY", raising=False)
    monkeypatch.setattr(composio_check, "fetch_index", lambda **kw: INDEX)

    result = fetch_toolkits()
    assert result["stripe"] == "STRIPE"
