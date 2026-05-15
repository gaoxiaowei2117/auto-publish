"""Generation orchestrator: build prompt, call Claude, validate, retry.

generate_with_retry(persona, topic, image_filenames, client=None, max_retries=2)
  -> (final_draft: dict, violations_history: list[list[str]])

`violations_history[i]` is the validation result of attempt i (empty if pass).
The returned draft is whichever attempt was last; check
`violations_history[-1]` to know whether it's clean.

`user_feedback` parameter allows external (non-validation) revision requests
— e.g., the user said "make it shorter".
"""
from __future__ import annotations

from persona import Persona
from prompt import build_messages
from llm import call_claude
from validate import validate_draft


def generate_once(
    persona: Persona,
    topic: str,
    image_filenames: list[str],
    client=None,
    user_feedback: str | None = None,
) -> dict:
    """Single generation attempt without retry."""
    msgs = build_messages(persona, topic, image_filenames, user_feedback=user_feedback)
    return call_claude(system=msgs["system"], user=msgs["user"], client=client)


def generate_with_retry(
    persona: Persona,
    topic: str,
    image_filenames: list[str],
    client=None,
    max_retries: int = 2,
    user_feedback: str | None = None,
) -> tuple[dict, list[list[str]]]:
    """Generate; if validation fails, retry up to `max_retries` more times with
    violations fed back as feedback. Returns (last_draft, list_of_violation_lists).
    """
    violations_history: list[list[str]] = []
    draft: dict = {}
    feedback = user_feedback

    for attempt in range(max_retries + 1):
        draft = generate_once(
            persona, topic, image_filenames, client=client, user_feedback=feedback
        )
        violations = validate_draft(draft, persona, image_filenames)
        violations_history.append(violations)
        if not violations:
            return draft, violations_history
        # Build feedback for next iteration.
        feedback = (
            "The previous draft had these validation problems. Fix all of them:\n  - "
            + "\n  - ".join(violations)
        )

    return draft, violations_history
