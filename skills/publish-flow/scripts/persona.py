"""Persona loader.

Loads a persona YAML file into typed dataclasses with validation.
Used by generate.py to build the system prompt for content generation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


class PersonaError(ValueError):
    pass


@dataclass(frozen=True)
class Voice:
    tone: str
    style_keywords: list[str]
    avoid_tones: list[str]


@dataclass(frozen=True)
class Length:
    title_chars: tuple[int, int]
    body_chars: tuple[int, int]


@dataclass(frozen=True)
class Emoji:
    usage: str  # none | light | heavy
    preferred: list[str]
    avoid: list[str]


@dataclass(frozen=True)
class Hashtags:
    count: tuple[int, int]
    style: str  # specific | broad | mix
    preferred_categories: list[str]
    avoid_categories: list[str]


@dataclass(frozen=True)
class ContentRules:
    forbid_phrases: list[str]
    prefer_first_person: bool
    cta_style: str  # none | subtle | explicit
    format: str


@dataclass(frozen=True)
class Example:
    title: str
    body: str
    tags: list[str]
    note: str = ""


@dataclass(frozen=True)
class Persona:
    name: str
    display_name: str
    description: str
    voice: Voice
    length: Length
    emoji: Emoji
    hashtags: Hashtags
    content_rules: ContentRules
    examples: list[Example] = field(default_factory=list)


def _require(d: dict, key: str, where: str) -> object:
    if key not in d:
        raise PersonaError(f"missing '{key}' in {where}")
    return d[key]


def _pair(v, where: str) -> tuple[int, int]:
    if not isinstance(v, list) or len(v) != 2:
        raise PersonaError(f"expected [min, max] in {where}, got {v!r}")
    try:
        return (int(v[0]), int(v[1]))
    except (TypeError, ValueError) as exc:
        raise PersonaError(f"expected [int, int] in {where}, got {v!r}") from exc


def load_persona(path: Path) -> Persona:
    path = Path(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise PersonaError(f"persona file must be a YAML mapping: {path}")

    voice_d = _require(raw, "voice", path.name)
    length_d = _require(raw, "length", path.name)
    emoji_d = _require(raw, "emoji", path.name)
    hashtags_d = _require(raw, "hashtags", path.name)
    rules_d = _require(raw, "content_rules", path.name)

    raw_examples = raw.get("examples", []) or []
    if not isinstance(raw_examples, list):
        raise PersonaError(f"'examples' must be a list, got {type(raw_examples).__name__}")
    examples = []
    for i, e in enumerate(raw_examples):
        where = f"examples[{i}]"
        if not isinstance(e, dict):
            raise PersonaError(f"{where} must be a mapping, got {type(e).__name__}")
        examples.append(
            Example(
                title=str(_require(e, "title", where)),
                body=str(_require(e, "body", where)),
                tags=list(_require(e, "tags", where)),
                note=str(e.get("note", "")),
            )
        )

    return Persona(
        name=str(_require(raw, "name", path.name)),
        display_name=str(raw.get("display_name", raw["name"])),
        description=str(raw.get("description", "")),
        voice=Voice(
            tone=str(_require(voice_d, "tone", "voice")),
            style_keywords=list(voice_d.get("style_keywords", [])),
            avoid_tones=list(voice_d.get("avoid_tones", [])),
        ),
        length=Length(
            title_chars=_pair(_require(length_d, "title_chars", "length"), "length.title_chars"),
            body_chars=_pair(_require(length_d, "body_chars", "length"), "length.body_chars"),
        ),
        emoji=Emoji(
            usage=str(_require(emoji_d, "usage", "emoji")),
            preferred=list(emoji_d.get("preferred", [])),
            avoid=list(emoji_d.get("avoid", [])),
        ),
        hashtags=Hashtags(
            count=_pair(_require(hashtags_d, "count", "hashtags"), "hashtags.count"),
            style=str(_require(hashtags_d, "style", "hashtags")),
            preferred_categories=list(hashtags_d.get("preferred_categories", [])),
            avoid_categories=list(hashtags_d.get("avoid_categories", [])),
        ),
        content_rules=ContentRules(
            forbid_phrases=list(rules_d.get("forbid_phrases", [])),
            prefer_first_person=bool(rules_d.get("prefer_first_person", True)),
            cta_style=str(rules_d.get("cta_style", "subtle")),
            format=str(rules_d.get("format", "")),
        ),
        examples=examples,
    )
