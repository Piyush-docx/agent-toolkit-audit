""""Already on Composio?" check (PROJECT_BRIEF.md section 3, decisions D7/D8).

Queries the Composio toolkits API by app name. With COMPOSIO_API_KEY set this can
say yes/no/unknown; without a key it falls back to the keyless public page, which
can only prove presence (yes/unknown), never absence -- see D8.
"""

from __future__ import annotations

import os
from functools import lru_cache

import httpx

API_BASE = "https://backend.composio.dev/api/v3.1"
PUBLIC_TOOLKITS_URL = "https://composio.dev/toolkits"
TIMEOUT = 10.0


def _normalise(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum())


@lru_cache(maxsize=1)
def _api_key() -> str | None:
    return os.environ.get("COMPOSIO_API_KEY") or None


def check_on_composio(app_name: str) -> dict:
    """Return {"on_composio": "yes"|"no"|"unknown", "method": str, "slug": str|None}."""
    key = _api_key()
    if key:
        return _check_with_api(app_name, key)
    return _check_keyless(app_name)


def _check_with_api(app_name: str, key: str) -> dict:
    try:
        resp = httpx.get(
            f"{API_BASE}/toolkits",
            params={"search": app_name, "limit": 20},
            headers={"x-api-key": key},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
    except httpx.HTTPError:
        return {"on_composio": "unknown", "method": "api_error", "slug": None}

    target = _normalise(app_name)
    for item in items:
        if _normalise(item.get("name", "")) == target or _normalise(item.get("slug", "")) == target:
            return {"on_composio": "yes", "method": "api", "slug": item.get("slug")}
    # A partial/substring match still counts as found (e.g. "Zoho CRM" vs slug "zohocrm").
    for item in items:
        if target in _normalise(item.get("name", "")) or target in _normalise(item.get("slug", "")):
            return {"on_composio": "yes", "method": "api", "slug": item.get("slug")}

    return {"on_composio": "no", "method": "api", "slug": None}


def _check_keyless(app_name: str) -> dict:
    """No key: page is client-paginated, so absence can't be proven (D8)."""
    try:
        resp = httpx.get(PUBLIC_TOOLKITS_URL, timeout=TIMEOUT)
        resp.raise_for_status()
    except httpx.HTTPError:
        return {"on_composio": "unknown", "method": "keyless_error", "slug": None}

    target = _normalise(app_name)
    if target in _normalise(resp.text):
        return {"on_composio": "yes", "method": "keyless_page", "slug": None}
    return {"on_composio": "unknown", "method": "keyless_page", "slug": None}
