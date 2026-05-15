from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills" / "publish-flow" / "scripts"))

import persona as persona_mod
import prompt as prompt_mod


def _sample_persona() -> persona_mod.Persona:
    yaml_text = """
name: test
display_name: "Test"
description: ""
voice:
  tone: "casual"
  style_keywords: ["k1", "k2"]
  avoid_tones: ["AVOID1"]
length:
  title_chars: [10, 20]
  body_chars: [200, 500]
emoji:
  usage: light
  preferred: ["🌿"]
  avoid: ["💕"]
hashtags:
  count: [3, 4]
  style: mix
  preferred_categories: ["a"]
  avoid_categories: ["b"]
content_rules:
  forbid_phrases: ["FORBID1"]
  prefer_first_person: true
  cta_style: subtle
  format: "short"
examples:
  - title: "EX_TITLE"
    body: "EX_BODY"
    tags: ["#x"]
"""
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as f:
        f.write(yaml_text)
        path = f.name
    return persona_mod.load_persona(Path(path))


def test_build_messages_contains_persona_fields() -> None:
    persona = _sample_persona()
    msgs = prompt_mod.build_messages(
        persona, topic="topic-X", image_filenames=["a.jpg", "b.jpg"]
    )
    system = msgs["system"]
    user = msgs["user"]

    # persona fields are in system (so they cache)
    assert "casual" in system
    assert "k1" in system and "k2" in system
    assert "AVOID1" in system
    assert "FORBID1" in system
    assert "EX_TITLE" in system and "EX_BODY" in system

    # topic + images are in user (the per-call part)
    assert "topic-X" in user
    assert "a.jpg" in user and "b.jpg" in user

    # constraints surfaced
    assert "20" in system and "500" in system   # hard length limits


def test_build_messages_no_examples() -> None:
    # Same but strip examples — should still work
    persona = _sample_persona()
    from dataclasses import replace
    persona = replace(persona, examples=[])
    msgs = prompt_mod.build_messages(persona, topic="t", image_filenames=["x.jpg"])
    assert "EXAMPLES" not in msgs["system"] or "no examples" in msgs["system"].lower()
