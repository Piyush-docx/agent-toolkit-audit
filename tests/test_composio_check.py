"""composio_check.py -- name matching and fallback behaviour, no network calls."""

import httpx
import pytest

from agent import composio_check


@pytest.fixture(autouse=True)
def _clear_key_cache():
    composio_check._api_key.cache_clear()
    yield
    composio_check._api_key.cache_clear()


def test_api_exact_match(monkeypatch):
    monkeypatch.setenv("COMPOSIO_API_KEY", "fake_key")

    def fake_get(url, params=None, headers=None, timeout=None):
        assert headers["x-api-key"] == "fake_key"
        return httpx.Response(
            200,
            json={"items": [{"name": "Stripe", "slug": "stripe"}]},
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(composio_check.httpx, "get", fake_get)
    result = composio_check.check_on_composio("Stripe")
    assert result == {"on_composio": "yes", "method": "api", "slug": "stripe"}


def test_api_no_match_means_no(monkeypatch):
    monkeypatch.setenv("COMPOSIO_API_KEY", "fake_key")

    def fake_get(url, params=None, headers=None, timeout=None):
        return httpx.Response(200, json={"items": []}, request=httpx.Request("GET", url))

    monkeypatch.setattr(composio_check.httpx, "get", fake_get)
    result = composio_check.check_on_composio("SomeObscureApp")
    assert result["on_composio"] == "no"


def test_api_error_is_unknown_not_crash(monkeypatch):
    monkeypatch.setenv("COMPOSIO_API_KEY", "fake_key")

    def fake_get(url, params=None, headers=None, timeout=None):
        raise httpx.ConnectTimeout("timeout")

    monkeypatch.setattr(composio_check.httpx, "get", fake_get)
    result = composio_check.check_on_composio("Stripe")
    assert result["on_composio"] == "unknown"


def test_keyless_fallback_cannot_prove_absence(monkeypatch):
    monkeypatch.delenv("COMPOSIO_API_KEY", raising=False)

    def fake_get(url, timeout=None):
        return httpx.Response(200, text="no matches here", request=httpx.Request("GET", url))

    monkeypatch.setattr(composio_check.httpx, "get", fake_get)
    result = composio_check.check_on_composio("SomeObscureApp")
    assert result["on_composio"] == "unknown"
    assert result["method"] == "keyless_page"


def test_keyless_fallback_can_prove_presence(monkeypatch):
    monkeypatch.delenv("COMPOSIO_API_KEY", raising=False)

    def fake_get(url, timeout=None):
        return httpx.Response(200, text="...stripe...", request=httpx.Request("GET", url))

    monkeypatch.setattr(composio_check.httpx, "get", fake_get)
    result = composio_check.check_on_composio("Stripe")
    assert result["on_composio"] == "yes"
