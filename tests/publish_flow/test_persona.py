"""Tests for persona loading."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills" / "publish-flow" / "scripts"))

import persona as persona_mod

SAMPLE_YAML = """
name: test
display_name: "Test"
description: "A test persona"
voice:
  tone: "casual"
  style_keywords: ["真实", "短"]
  avoid_tones: ["种草"]
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
  preferred_categories: ["生活"]
  avoid_categories: ["美妆"]
content_rules:
  forbid_phrases: ["种草", "yyds"]
  prefer_first_person: true
  cta_style: subtle
  format: "短段落"
examples:
  - title: "示例标题"
    body: "示例正文。"
    tags: ["#示例"]
    note: "test example"
"""


def test_load_persona_from_file(tmp_path: Path) -> None:
    p = tmp_path / "p.yaml"
    p.write_text(SAMPLE_YAML, encoding="utf-8")
    persona = persona_mod.load_persona(p)
    assert persona.name == "test"
    assert persona.voice.tone == "casual"
    assert persona.length.title_chars == (10, 20)
    assert persona.length.body_chars == (200, 500)
    assert persona.emoji.usage == "light"
    assert "种草" in persona.content_rules.forbid_phrases
    assert len(persona.examples) == 1
    assert persona.examples[0].title == "示例标题"


def test_load_persona_missing_required_raises(tmp_path: Path) -> None:
    p = tmp_path / "p.yaml"
    p.write_text("name: x", encoding="utf-8")
    with pytest.raises(persona_mod.PersonaError):
        persona_mod.load_persona(p)


def test_load_default_persona_succeeds() -> None:
    default = ROOT / "skills" / "publish-flow" / "persona" / "default.yaml"
    persona = persona_mod.load_persona(default)
    assert persona.name


BASE_YAML = """
name: test
voice:
  tone: "casual"
length:
  title_chars: [10, 20]
  body_chars: [200, 500]
emoji:
  usage: light
hashtags:
  count: [3, 4]
  style: mix
content_rules:
  format: "短段落"
"""


def test_examples_must_be_list_not_string(tmp_path: Path) -> None:
    p = tmp_path / "p.yaml"
    p.write_text(BASE_YAML + '\nexamples: "oops"\n', encoding="utf-8")
    with pytest.raises(persona_mod.PersonaError) as exc_info:
        persona_mod.load_persona(p)
    assert "examples" in str(exc_info.value)


def test_example_missing_field_reports_index(tmp_path: Path) -> None:
    p = tmp_path / "p.yaml"
    yaml_text = BASE_YAML + """
examples:
  - title: "first"
    body: "first body"
    tags: ["#a"]
  - title: "second"
    tags: ["#b"]
"""
    p.write_text(yaml_text, encoding="utf-8")
    with pytest.raises(persona_mod.PersonaError) as exc_info:
        persona_mod.load_persona(p)
    assert "examples[1]" in str(exc_info.value)


def test_pair_with_non_numeric_raises_persona_error(tmp_path: Path) -> None:
    p = tmp_path / "p.yaml"
    yaml_text = """
name: test
voice:
  tone: "casual"
length:
  title_chars: [foo, 20]
  body_chars: [200, 500]
emoji:
  usage: light
hashtags:
  count: [3, 4]
  style: mix
content_rules:
  format: "短段落"
"""
    p.write_text(yaml_text, encoding="utf-8")
    with pytest.raises(persona_mod.PersonaError) as exc_info:
        persona_mod.load_persona(p)
    assert "length.title_chars" in str(exc_info.value)
