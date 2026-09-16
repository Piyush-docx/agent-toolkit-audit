"""Text extraction and quote matching (verification Loop A)."""
import pytest

from agent.fetch import extract_text, normalise_whitespace, quote_supported

HTML = """<html><head><style>.x{color:red}</style>
<script>var a = "invisible";</script></head>
<body><h1>Stripe API</h1>
<p>Authentication to the API is performed via HTTP Basic Auth.</p>
<p>Provide your API key as the basic auth username value.</p></body></html>"""


def test_extract_drops_script_and_style():
    text = extract_text(HTML)
    assert "invisible" not in text
    assert "color:red" not in text


def test_extract_keeps_visible_text():
    assert "HTTP Basic Auth" in extract_text(HTML)


def test_normalise_collapses_all_whitespace():
    assert normalise_whitespace("a \n\t  b c") == "a b c"


# --- quote matching --------------------------------------------------------

def test_exact_quote_is_supported():
    ok, score = quote_supported(
        "performed via HTTP Basic Auth", extract_text(HTML))
    assert ok and score == 100.0


def test_whitespace_differences_still_match():
    """The model's quote often re-wraps the page's line breaks."""
    ok, _ = quote_supported(
        "Authentication to the API\n  is performed   via HTTP Basic Auth",
        extract_text(HTML))
    assert ok


def test_case_differences_still_match():
    ok, _ = quote_supported("HTTP BASIC AUTH", extract_text(HTML))
    assert ok


def test_absent_quote_is_not_supported():
    """A fabricated quote must fail -- this is the check's whole purpose."""
    ok, _ = quote_supported(
        "Stripe uses OAuth2 device flow for all requests", extract_text(HTML))
    assert not ok


def test_near_miss_passes_fuzzy_threshold():
    ok, score = quote_supported(
        "Provide your API key as the basic auth username",
        extract_text(HTML))
    assert ok and score >= 90


@pytest.mark.parametrize("quote,page", [("", "something"), ("something", "")])
def test_empty_inputs_are_unsupported(quote, page):
    assert quote_supported(quote, page) == (False, 0.0)
