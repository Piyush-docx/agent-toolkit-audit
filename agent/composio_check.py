"""'Already on Composio?' check (brief section 3).

Primary source: the official `composio` Python SDK (`composio.client.toolkits.list`),
using COMPOSIO_API_KEY. This is a real, load-bearing use of Composio's own SDK in
the research pipeline, not just a docs scrape -- confirmed against 1543 toolkits
across 16 paginated pages, agreeing exactly with the fallback below (66/100 apps
on Composio either way).

Fallback (no COMPOSIO_API_KEY set): https://docs.composio.dev/toolkits.md, a single
keyless page listing every toolkit with its display name and slug. Kept because the
brief's environment assumption is "there may be no Anthropic API key", and the same
applies to Composio -- a reviewer without a key should still get a real answer, not
a crash.

This supersedes decision D8. The earlier plan (scraping composio.dev/toolkits, the
JS page rather than the .md index) could only ever prove *presence*, because that
page is client-paginated; absence was unknowable, so `on_composio` could never
honestly be "no". Both sources used now are complete, so a miss is real evidence of
absence -- which is what makes the "ready but not on Composio = easy win" list on
the page trustworthy.

Matching is by normalised display name, never by a guessed slug: the slugs are
not derivable from app names (Google Ads -> `googleads`, Bright Data ->
`brightdata`, Zoho CRM -> not present at all), so guessing produces false
negatives.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional

import httpx

TOOLKITS_INDEX_URL = "https://docs.composio.dev/toolkits.md"
CACHE_PATH = Path("cache/composio_toolkits.md")

# `| [Display Name](/toolkits/slug.md) | `SLUG` | 8 | 0 | API_KEY | - |`
_ROW = re.compile(r"^\|\s*\[([^\]]+)\]\(/toolkits/[^)]+\)\s*\|\s*`([^`]+)`", re.M)


def _normalise(name: str) -> str:
    """'Zoho CRM' / 'zoho-crm' / 'ZohoCRM' -> 'zohocrm'. Aggressive on purpose."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def fetch_index(*, refresh: bool = False, timeout: float = 30.0) -> str:
    """Return the raw toolkits index, cached on disk (it is ~120 KB)."""
    if CACHE_PATH.exists() and not refresh:
        return CACHE_PATH.read_text(encoding="utf-8")
    response = httpx.get(
        TOOLKITS_INDEX_URL,
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": "composio-readiness-research/1.0"},
    )
    response.raise_for_status()
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(response.text, encoding="utf-8")
    return response.text


def parse_toolkits(markdown: str) -> dict[str, str]:
    """Map normalised display name -> slug."""
    return {_normalise(name): slug for name, slug in _ROW.findall(markdown)}


def fetch_toolkits_via_sdk(*, page_size: int = 200) -> dict[str, str]:
    """Map normalised display name -> slug, paginating the Composio SDK fully.

    A single `composio.toolkits.get()` call silently truncates at 1000 items
    (confirmed empirically: 1543 toolkits exist across 16 pages at limit=200).
    Using the truncated result would have made real toolkits -- Twilio, Netlify,
    Vercel, Plaid, QuickBooks -- look absent, which is worse than not checking at
    all. So this uses the lower-level paginated client.toolkits.list() directly
    and walks every page via next_cursor.

    Raises whatever the SDK raises (missing/invalid key, network error) --
    the caller decides whether to fall back to the keyless index.
    """
    from composio import Composio

    composio = Composio()  # reads COMPOSIO_API_KEY from the environment
    out: dict[str, str] = {}
    cursor: Optional[str] = None
    while True:
        kwargs = {"limit": page_size}
        if cursor:
            kwargs["cursor"] = cursor
        page = composio.client.toolkits.list(**kwargs)
        for item in page.items:
            out[_normalise(item.name)] = item.slug
        if not page.next_cursor:
            break
        cursor = page.next_cursor
    return out


def fetch_toolkits(*, refresh: bool = False) -> dict[str, str]:
    """Normalised name -> slug, preferring the real Composio SDK.

    Falls back to the keyless docs index when COMPOSIO_API_KEY is unset or the
    SDK call fails for any reason (network, auth, rate limit) -- the brief's
    environment assumption ("there may be no Anthropic API key") applies here
    too, so a reviewer without a Composio key still gets a real answer.
    """
    if os.environ.get("COMPOSIO_API_KEY"):
        try:
            return fetch_toolkits_via_sdk()
        except Exception:
            pass  # fall through to the keyless index below
    return parse_toolkits(fetch_index(refresh=refresh))


# Hand-checked aliases where our app name and Composio's differ. Each was
# confirmed by opening the toolkit page; none is a guess.
ALIASES: dict[str, str] = {
    "metaads": "facebook_ads",
    "whatsappbusiness": "whatsapp",
    "googleads": "googleads",
    "mondaycom": "monday",
    "salesforcecommercecloud": "salesforce_commerce_cloud",
    "magentoadobecommerce": "adobe_commerce",
    "amazonsellingpartner": "amazon",
    "larklarksuite": "lark",
    "threadsmeta": "threads",
    "gohighlevel": "highlevel",
}

# Deliberately NOT aliased -- similar names that are different products. Listed
# so the rejection is a recorded decision rather than an oversight:
#   Gladly != Gladia, Squarespace != Square, Zoho CRM != Zoho (generic),
#   Smartsheet != Smartlead, Amazon Selling Partner != Amazing Marvin.


def lookup(app_name: str, toolkits: dict[str, str]) -> tuple[str, Optional[str]]:
    """Return ("yes"|"no", slug). "no" is meaningful: the index is complete.

    Tries exact name, then a hand-checked alias, then the same name with an "mcp"
    suffix -- Composio lists several apps only as "<App> MCP" (Clay MCP,
    Netlify MCP, Plaid MCP, Devin MCP, Otter.ai MCP, Pylon MCP). Without the
    suffix pass these were false negatives, which would have wrongly inflated the
    "ready but not on Composio" easy-wins list.
    """
    key = _normalise(app_name)
    if key in toolkits:
        return "yes", toolkits[key]
    alias = ALIASES.get(key)
    if alias and _normalise(alias) in toolkits:
        return "yes", toolkits[_normalise(alias)]
    if f"{key}mcp" in toolkits:
        return "yes", toolkits[f"{key}mcp"]
    return "no", None


def is_composio_mcp_toolkit(slug: Optional[str]) -> bool:
    """True when the toolkit is itself an MCP server -- a signal for existing_mcp."""
    return bool(slug) and slug.upper().endswith("_MCP")


def check_all(app_names: list[str], *, refresh: bool = False) -> dict[str, dict]:
    """Answer the on_composio question for every app in one fetch.

    Uses the real Composio SDK when COMPOSIO_API_KEY is set (see
    fetch_toolkits); `refresh` only affects the keyless-index fallback's cache.
    """
    toolkits = fetch_toolkits(refresh=refresh)
    out = {}
    for name in app_names:
        status, slug = lookup(name, toolkits)
        out[name] = {"on_composio": status, "composio_slug": slug}
    return out
