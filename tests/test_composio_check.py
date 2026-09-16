"""The 'already on Composio?' check.

Uses a fixture copy of the real index format so tests never hit the network.
"""
import pytest

from agent.composio_check import (
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
