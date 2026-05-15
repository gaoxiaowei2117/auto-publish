"""Claude API caller with prompt caching.

call_claude(system, user, client=None, model=...) -> dict

The `system` string is wrapped in a content block with cache_control="ephemeral"
so the persona-derived prefix caches across regen retries within a session
(5-minute TTL).
"""
from __future__ import annotations

import json
import re

DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_MAX_TOKENS = 2048


class LLMOutputError(ValueError):
    pass


def call_claude(
    system: str,
    user: str,
    client=None,
    model: str = DEFAULT_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> dict:
    """Send messages to Claude, parse JSON output, return dict."""
    if client is None:
        import anthropic
        client = anthropic.Anthropic()

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=[
            {
                "type": "text",
                "text": system,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {"role": "user", "content": user},
        ],
    )

    # response.content is a list of content blocks; first is usually text
    text = response.content[0].text if response.content else ""
    return _parse_json(text)


def _parse_json(text: str) -> dict:
    """Extract JSON from a model response. Tolerates code fences and prose."""
    # Try direct parse first.
    candidate = text.strip()
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    # Strip ```json ... ``` fences.
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if fence:
        try:
            return json.loads(fence.group(1))
        except json.JSONDecodeError:
            pass

    # Greedy {...} match.
    brace = re.search(r"\{.*\}", text, re.S)
    if brace:
        try:
            return json.loads(brace.group(0))
        except json.JSONDecodeError:
            pass

    raise LLMOutputError(f"could not parse JSON from model output: {text!r}")
