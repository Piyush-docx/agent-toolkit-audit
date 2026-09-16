"""Deterministic page fetching + text extraction, with an on-disk cache.

Used by verification Loop A, which must check that an evidence quote really
appears on the page the model cited. That check has to be plain Python, not an
LLM: asking a model "is this quote on the page?" would reintroduce exactly the
error we are trying to detect.

Fallback ladder (brief section 3): httpx -> Claude Code WebFetch -> Playwright.
Which method succeeded is recorded, because JS-rendered docs (Stoplight,
Readme.io, Notion-hosted) return empty text over plain httpx.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import httpx

CACHE_DIR = Path("cache/pages")
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) composio-readiness-research/1.0"
)
MIN_USEFUL_CHARS = 200          # below this, treat as JS-rendered and escalate


@dataclass
class FetchResult:
    url: str
    text: str
    method: str                 # httpx | webfetch | playwright | cache
    ok: bool
    status: Optional[int] = None
    error: Optional[str] = None


def _cache_path(url: str) -> Path:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]
    return CACHE_DIR / f"{digest}.json"


def _read_cache(url: str) -> Optional[FetchResult]:
    path = _cache_path(url)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return FetchResult(url=url, text=payload.get("text", ""),
                       method=payload.get("method", "cache"),
                       ok=payload.get("ok", False), status=payload.get("status"))


def _write_cache(result: FetchResult) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _cache_path(result.url).write_text(
        json.dumps({"url": result.url, "text": result.text, "method": result.method,
                    "ok": result.ok, "status": result.status}),
        encoding="utf-8",
    )


_TAG_SOUP = re.compile(r"<(script|style|noscript|svg)[^>]*>.*?</\1>",
                       re.S | re.I)
_TAGS = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


def extract_text(html: str) -> str:
    """HTML -> visible text. selectolax when available, regex otherwise."""
    try:
        from selectolax.parser import HTMLParser
    except ImportError:
        cleaned = _TAG_SOUP.sub(" ", html)
        return normalise_whitespace(_TAGS.sub(" ", cleaned))
    tree = HTMLParser(html)
    for tag in tree.css("script, style, noscript, svg"):
        tag.decompose()
    body = tree.body or tree
    return normalise_whitespace(body.text(separator=" "))


def normalise_whitespace(text: str) -> str:
    """Collapse all runs of whitespace. Applied to BOTH sides of a quote match."""
    return _WS.sub(" ", (text or "").replace(" ", " ")).strip()


def fetch_httpx(url: str, *, timeout: float = 20.0) -> FetchResult:
    try:
        response = httpx.get(url, timeout=timeout, follow_redirects=True,
                             headers={"User-Agent": USER_AGENT})
    except httpx.HTTPError as exc:
        return FetchResult(url, "", "httpx", False, error=str(exc)[:200])
    if response.status_code >= 400:
        return FetchResult(url, "", "httpx", False, status=response.status_code,
                           error=f"HTTP {response.status_code}")
    text = extract_text(response.text)
    ok = len(text) >= MIN_USEFUL_CHARS
    return FetchResult(url, text, "httpx", ok, status=response.status_code,
                       error=None if ok else "too little text (JS-rendered?)")


def fetch_webfetch(url: str) -> FetchResult:
    """Escalation for JS-rendered pages, via Claude Code's own WebFetch."""
    from agent.llm import LLMError, complete_claude_code
    try:
        result = complete_claude_code(
            f"Fetch {url} and reproduce its main textual content verbatim. "
            "Do not summarise, do not add commentary.",
            tools=("WebFetch",), max_turns=4, timeout=180,
        )
    except LLMError as exc:
        return FetchResult(url, "", "webfetch", False, error=str(exc)[:200])
    text = normalise_whitespace(result.raw)
    ok = len(text) >= MIN_USEFUL_CHARS
    return FetchResult(url, text, "webfetch", ok,
                       error=None if ok else "webfetch returned little text")


def fetch_playwright(url: str, *, timeout: int = 30000) -> FetchResult:
    """Last resort. Optional dependency: absent Playwright is not an error."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return FetchResult(url, "", "playwright", False,
                           error="playwright not installed")
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(user_agent=USER_AGENT)
            page.goto(url, timeout=timeout, wait_until="domcontentloaded")
            html = page.content()
            browser.close()
    except Exception as exc:  # pragma: no cover - browser path
        return FetchResult(url, "", "playwright", False, error=str(exc)[:200])
    text = extract_text(html)
    return FetchResult(url, text, "playwright", len(text) >= MIN_USEFUL_CHARS)


def fetch(url: str, *, use_cache: bool = True, allow_llm: bool = True,
          allow_browser: bool = False) -> FetchResult:
    """Fetch a page, escalating only as far as needed. Caches successes."""
    if use_cache:
        cached = _read_cache(url)
        if cached and cached.ok:
            return cached

    result = fetch_httpx(url)
    if not result.ok and allow_llm:
        escalated = fetch_webfetch(url)
        if escalated.ok:
            result = escalated
    if not result.ok and allow_browser:
        escalated = fetch_playwright(url)
        if escalated.ok:
            result = escalated

    if result.ok and use_cache:
        _write_cache(result)
    return result


def quote_supported(quote: str, page_text: str, *, threshold: int = 90
                    ) -> tuple[bool, float]:
    """Is `quote` present in `page_text`? Exact first, then fuzzy.

    Both sides are whitespace-normalised and lowercased. rapidfuzz's
    partial_ratio finds the best matching window, which is what we want: the
    quote is a fragment of a much longer page.
    """
    needle = normalise_whitespace(quote).lower()
    haystack = normalise_whitespace(page_text).lower()
    if not needle or not haystack:
        return False, 0.0
    if needle in haystack:
        return True, 100.0
    try:
        from rapidfuzz import fuzz
    except ImportError:
        return False, 0.0
    score = fuzz.partial_ratio(needle, haystack)
    return score >= threshold, float(score)
