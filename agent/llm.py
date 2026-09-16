"""Pluggable LLM backends (brief section 3).

  claude_code   (default) -- `claude -p` via subprocess, using the developer's
                existing Claude Code login. No API key needed.
  anthropic_api (optional) -- only used when ANTHROPIC_API_KEY is set.

Both expose the same call: complete(prompt, schema, tools) -> LLMResult.

Claude Code specifics verified on this machine in P0 (docs/DECISIONS.md D1-D5):
  - `--json-schema` enforces structured output, so prompts must NOT also say
    "reply with JSON only" -- that double-encodes the answer (D3).
  - usage.server_tool_use counters stay 0 for the local WebSearch/WebFetch
    tools, so cost/turns/wall-time are the usable usage signals (D4).
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any, Optional

DEFAULT_MODEL = "sonnet"          # bulk extraction
JUDGE_MODEL = "opus"              # verification judgments (D6)


class LLMError(RuntimeError):
    """Backend failed. `usage_limited` distinguishes 'retry later' from 'broken'."""

    def __init__(self, message: str, *, usage_limited: bool = False):
        super().__init__(message)
        self.usage_limited = usage_limited


@dataclass
class LLMResult:
    data: Optional[dict]        # parsed structured output, None if unparseable
    raw: str                    # raw result text, always kept for cache/audit
    cost_usd: float = 0.0
    duration_s: float = 0.0
    num_turns: int = 0
    model: str = ""
    session_id: str = ""
    meta: dict[str, Any] = field(default_factory=dict)


# Phrases Claude Code prints when a Pro window is exhausted. Matched loosely
# because the exact wording is not a stable contract.
_LIMIT_MARKERS = (
    "usage limit",
    "rate limit",
    "limit reached",
    "resets at",
    "out of usage",
)


def _looks_usage_limited(text: str) -> bool:
    lowered = (text or "").lower()
    return any(marker in lowered for marker in _LIMIT_MARKERS)


def complete_claude_code(
    prompt: str,
    *,
    schema: Optional[dict] = None,
    tools: tuple[str, ...] = ("WebSearch", "WebFetch"),
    model: str = DEFAULT_MODEL,
    max_turns: int = 20,
    timeout: int = 600,
) -> LLMResult:
    """Run one headless Claude Code turn and return its structured output."""
    cmd = [
        "claude", "-p", prompt,
        "--output-format", "json",
        "--model", model,
        "--max-turns", str(max_turns),
    ]
    if tools:
        cmd += ["--allowedTools", *tools]
    if schema:
        cmd += ["--json-schema", json.dumps(schema)]

    started = time.monotonic()
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False
        )
    except subprocess.TimeoutExpired as exc:
        raise LLMError(f"claude timed out after {timeout}s") from exc
    elapsed = time.monotonic() - started

    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()[:500]
        raise LLMError(
            f"claude exited {proc.returncode}: {detail}",
            usage_limited=_looks_usage_limited(detail),
        )

    try:
        envelope = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise LLMError(f"claude output was not JSON: {proc.stdout[:300]}") from exc

    if envelope.get("is_error"):
        detail = str(envelope.get("result") or envelope.get("subtype") or "")[:500]
        raise LLMError(
            f"claude reported an error: {detail}",
            usage_limited=_looks_usage_limited(detail),
        )

    raw = envelope.get("result") or ""
    data = envelope.get("structured_output")
    if data is None and raw:
        data = _loads_or_none(raw)

    return LLMResult(
        data=data if isinstance(data, dict) else None,
        raw=raw if isinstance(raw, str) else json.dumps(raw),
        cost_usd=float(envelope.get("total_cost_usd") or 0.0),
        duration_s=elapsed,
        num_turns=int(envelope.get("num_turns") or 0),
        model=model,
        session_id=str(envelope.get("session_id") or ""),
        meta={"subtype": envelope.get("subtype"),
              "permission_denials": envelope.get("permission_denials")},
    )


def _loads_or_none(text: str) -> Optional[dict]:
    """Best-effort JSON recovery from prose (fenced blocks, leading chatter)."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1] if "```" in text[3:] else text
        text = text.removeprefix("json").strip()
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            return None
        try:
            value = json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return None
    return value if isinstance(value, dict) else None


def complete_anthropic_api(
    prompt: str,
    *,
    schema: Optional[dict] = None,
    tools: tuple[str, ...] = (),
    model: str = "claude-sonnet-5",
    max_turns: int = 1,
    timeout: int = 600,
) -> LLMResult:
    """Direct API backend. Only reachable when ANTHROPIC_API_KEY is set.

    Deliberately has no web tools: server-side search would be a different
    evidence path than the Claude Code backend, and the brief's evidence rules
    require quotes from pages actually fetched. Used for offline judging only.
    """
    try:
        import anthropic
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise LLMError("anthropic package not installed") from exc

    client = anthropic.Anthropic(timeout=timeout)
    instruction = prompt
    if schema:
        instruction += (
            "\n\nReturn a single JSON object matching this schema, no prose:\n"
            + json.dumps(schema)
        )
    started = time.monotonic()
    try:
        message = client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[{"role": "user", "content": instruction}],
        )
    except Exception as exc:  # pragma: no cover - network path
        raise LLMError(f"anthropic api call failed: {exc}",
                       usage_limited=_looks_usage_limited(str(exc))) from exc
    elapsed = time.monotonic() - started
    raw = "".join(block.text for block in message.content if hasattr(block, "text"))
    return LLMResult(data=_loads_or_none(raw), raw=raw, duration_s=elapsed,
                     num_turns=1, model=model)


def get_backend(name: Optional[str] = None):
    """Resolve the backend. Env LLM_BACKEND wins; falls back to claude_code."""
    name = name or os.environ.get("LLM_BACKEND") or "claude_code"
    if name == "anthropic_api":
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise LLMError("LLM_BACKEND=anthropic_api but ANTHROPIC_API_KEY is unset")
        return complete_anthropic_api
    if name == "claude_code":
        return complete_claude_code
    raise LLMError(f"unknown backend {name!r}")


def complete(prompt: str, **kwargs) -> LLMResult:
    """Call the configured backend."""
    return get_backend()(prompt, **kwargs)
