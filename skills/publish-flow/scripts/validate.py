"""Hard validation rules for generated drafts.

validate_draft(draft, persona, available_images) -> list[str]

Empty list = valid. Non-empty list = violations to feed back to the model
for a regeneration attempt.
"""
from __future__ import annotations

from persona import Persona

PLATFORM_TITLE_MAX = 20
PLATFORM_BODY_MAX = 1000


def validate_draft(draft: dict, persona: Persona, available_images: list[str]) -> list[str]:
    violations: list[str] = []

    title = draft.get("title", "")
    body = draft.get("body", "")
    tags = draft.get("tags", []) or []
    cover = draft.get("cover_pick", "")
    image_order = draft.get("image_order", []) or []

    # Title length
    t_min, t_max_pers = persona.length.title_chars
    if len(title) >= PLATFORM_TITLE_MAX:
        violations.append(
            f"title exceeds platform hard limit 20 chars (got {len(title)})"
        )
    elif len(title) > t_max_pers:
        violations.append(
            f"title exceeds persona max {t_max_pers} (got {len(title)})"
        )
    if len(title) < t_min:
        violations.append(
            f"title shorter than persona min {t_min} (got {len(title)})"
        )

    # Body length
    b_min, b_max_pers = persona.length.body_chars
    if len(body) > PLATFORM_BODY_MAX:
        violations.append(
            f"body exceeds platform hard limit 1000 chars (got {len(body)})"
        )
    elif len(body) > b_max_pers:
        violations.append(
            f"body exceeds persona max {b_max_pers} (got {len(body)})"
        )
    if len(body) < b_min:
        violations.append(
            f"body shorter than persona min {b_min} (got {len(body)})"
        )

    # Forbidden phrases
    for phrase in persona.content_rules.forbid_phrases:
        if phrase and phrase in (title + " " + body):
            violations.append(
                f"contains forbidden phrase '{phrase}'"
            )

    # Tags count
    tag_min, tag_max = persona.hashtags.count
    if not (tag_min <= len(tags) <= tag_max):
        violations.append(
            f"tags count {len(tags)} out of range [{tag_min}, {tag_max}]"
        )

    # Cover pick must be in available set
    if cover and cover not in available_images:
        violations.append(
            f"cover_pick '{cover}' not in available images {available_images}"
        )
    if not cover:
        violations.append("cover_pick is empty")

    # image_order entries must all be in available
    unknown = [f for f in image_order if f not in available_images]
    if unknown:
        violations.append(f"image_order contains unknown filenames: {unknown}")

    return violations
