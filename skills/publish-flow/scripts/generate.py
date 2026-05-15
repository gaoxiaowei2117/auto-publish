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

from llm import call_claude
from persona import Persona
from prompt import build_messages
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

    for _ in range(max_retries + 1):
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


def main() -> None:
    """CLI entry. Produces a draft JSON from a topic + images directory."""
    import argparse
    import json
    import sys
    from pathlib import Path

    from persona import load_persona

    parser = argparse.ArgumentParser(
        description="Generate an XHS draft via Claude from topic + images.",
    )
    parser.add_argument("--topic", required=True, help="Topic / brief from the user.")
    parser.add_argument(
        "--images-dir",
        required=True,
        help="Directory containing the image files to use.",
    )
    parser.add_argument(
        "--persona",
        default="skills/publish-flow/persona/default.yaml",
        help="Path to persona YAML.",
    )
    parser.add_argument(
        "--feedback",
        default=None,
        help="Optional user revision feedback from a previous iteration.",
    )
    parser.add_argument(
        "--regen-budget",
        type=int,
        default=2,
        help="Max hard-validation retries (NOT user revisions).",
    )
    args = parser.parse_args()

    persona = load_persona(Path(args.persona))
    images_dir = Path(args.images_dir).expanduser()
    if not images_dir.is_dir():
        print(json.dumps({"ok": False, "error": f"images-dir not found: {images_dir}"},
                         ensure_ascii=False), flush=True)
        sys.exit(2)

    image_exts = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
    image_files = sorted(
        [p.name for p in images_dir.iterdir() if p.suffix.lower() in image_exts]
    )
    if not image_files:
        print(json.dumps({"ok": False, "error": "no images in images-dir"},
                         ensure_ascii=False), flush=True)
        sys.exit(2)

    if len(image_files) > 9:
        image_files = image_files[:9]
        truncated = True
    else:
        truncated = False

    try:
        draft, history = generate_with_retry(
            persona=persona,
            topic=args.topic,
            image_filenames=image_files,
            max_retries=args.regen_budget,
            user_feedback=args.feedback,
        )
    except Exception as e:
        print(json.dumps({"ok": False, "error": f"generation failed: {e}"},
                         ensure_ascii=False), flush=True)
        sys.exit(2)

    final_violations = history[-1] if history else []
    out = {
        "ok": True,
        "draft": draft,
        "violations": final_violations,
        "history": history,
        "images_dir": str(images_dir.resolve()),
        "image_files": image_files,
        "truncated_to_9": truncated,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
