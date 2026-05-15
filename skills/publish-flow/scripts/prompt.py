"""Prompt assembly.

build_messages(persona, topic, image_filenames) -> {"system": str, "user": str}

The persona-derived portion goes into `system` so it can be prompt-cached
across regeneration retries within a single publish session. The user portion
(topic + images) is per-call and not cached.
"""
from __future__ import annotations

from persona import Persona


PLATFORM_HARD_LIMITS = """\
HARD PLATFORM LIMITS (must not be exceeded):
- title: ≤ 20 chars
- body: ≤ 1000 chars
- images: ≤ 9
- tags (hashtags): not enforced by platform; use persona setting
"""


def build_messages(
    persona: Persona,
    topic: str,
    image_filenames: list[str],
    user_feedback: str | None = None,
) -> dict[str, str]:
    """Build (system, user) messages for the Claude generation call.

    Args:
        persona: Loaded persona configuration.
        topic: User-provided topic / brief.
        image_filenames: Just the basenames; the model uses them as hints
            for cover selection and ordering, not for actual visual analysis.
        user_feedback: If this is a regeneration, the user's revision request.
    """
    system = _build_system(persona)
    user = _build_user(topic, image_filenames, user_feedback)
    return {"system": system, "user": user}


def _build_system(p: Persona) -> str:
    lines: list[str] = []
    lines.append("You are writing a 小红书 (Xiaohongshu) post in the user's voice.")
    lines.append("")
    lines.append("VOICE:")
    lines.append(f"  tone: {p.voice.tone}")
    lines.append(f"  style_keywords: {', '.join(p.voice.style_keywords)}")
    lines.append(f"  avoid_tones: {', '.join(p.voice.avoid_tones)}")
    lines.append("")
    lines.append("LENGTH:")
    lines.append(
        f"  title: target {p.length.title_chars[0]}-{p.length.title_chars[1]} chars "
        f"(platform hard limit 20)"
    )
    lines.append(
        f"  body: target {p.length.body_chars[0]}-{p.length.body_chars[1]} chars "
        f"(platform hard limit 1000)"
    )
    lines.append("")
    lines.append("EMOJI:")
    lines.append(f"  usage: {p.emoji.usage}")
    lines.append(f"  preferred: {' '.join(p.emoji.preferred) or '(none)'}")
    lines.append(f"  avoid: {' '.join(p.emoji.avoid) or '(none)'}")
    lines.append("")
    lines.append("HASHTAGS:")
    lines.append(
        f"  count: {p.hashtags.count[0]}-{p.hashtags.count[1]}"
    )
    lines.append(f"  style: {p.hashtags.style}")
    lines.append(f"  preferred_categories: {', '.join(p.hashtags.preferred_categories) or '(none)'}")
    lines.append(f"  avoid_categories: {', '.join(p.hashtags.avoid_categories) or '(none)'}")
    lines.append("")
    lines.append("CONTENT RULES:")
    lines.append(
        f"  forbid_phrases (MUST NOT appear): {', '.join(p.content_rules.forbid_phrases) or '(none)'}"
    )
    lines.append(f"  prefer_first_person: {p.content_rules.prefer_first_person}")
    lines.append(f"  cta_style: {p.content_rules.cta_style}")
    lines.append(f"  format: {p.content_rules.format}")
    lines.append("")

    if p.examples:
        lines.append("EXAMPLES OF THE USER'S OWN STYLE (learn from these):")
        for i, ex in enumerate(p.examples, 1):
            lines.append(f"  Example {i}:")
            lines.append(f"    title: {ex.title}")
            lines.append(f"    body: {ex.body}")
            lines.append(f"    tags: {' '.join(ex.tags)}")
            if ex.note:
                lines.append(f"    (author's note: {ex.note})")
            lines.append("")
    else:
        lines.append("EXAMPLES: (no examples provided — quality will suffer)")
        lines.append("")

    lines.append(PLATFORM_HARD_LIMITS)
    lines.append("")
    lines.append(
        "OUTPUT: Respond with ONLY a JSON object (no prose around it), matching:"
    )
    lines.append('  {')
    lines.append('    "title": "string, <=20 chars",')
    lines.append('    "body": "string, <=1000 chars",')
    lines.append('    "tags": ["#tag1", "#tag2", ...],')
    lines.append('    "cover_pick": "<exact filename from available images>",')
    lines.append('    "image_order": ["<filename>", ...]   // permutation of available')
    lines.append('  }')
    return "\n".join(lines)


def _build_user(topic: str, image_filenames: list[str], user_feedback: str | None) -> str:
    parts: list[str] = []
    parts.append(f"Topic: {topic}")
    parts.append("")
    parts.append("Available images (filenames only):")
    for fn in image_filenames:
        parts.append(f"  - {fn}")
    if user_feedback:
        parts.append("")
        parts.append("Revision feedback from a previous draft:")
        parts.append(user_feedback)
    parts.append("")
    parts.append(
        "Pick one image as cover (likely the most representative) and order the rest "
        "so the first 3 are the strongest hook."
    )
    return "\n".join(parts)
