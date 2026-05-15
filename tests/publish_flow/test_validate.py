from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills" / "publish-flow" / "scripts"))

import persona as persona_mod
import validate as validate_mod


def _persona() -> persona_mod.Persona:
    import tempfile
    yaml_text = """
name: t
display_name: t
description: t
voice:
  tone: casual
  style_keywords: []
  avoid_tones: []
length:
  title_chars: [5, 20]
  body_chars: [50, 200]
emoji:
  usage: light
  preferred: []
  avoid: []
hashtags:
  count: [2, 4]
  style: mix
  preferred_categories: []
  avoid_categories: []
content_rules:
  forbid_phrases: ["种草", "yyds"]
  prefer_first_person: true
  cta_style: subtle
  format: ""
"""
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as f:
        f.write(yaml_text)
        f.flush()
        return persona_mod.load_persona(Path(f.name))


GOOD = {
    "title": "今天去逛了城市市集",
    "body": "周末的市集很有意思，淘到不少小东西。" * 3,
    "tags": ["#周末", "#市集", "#City walk"],
    "cover_pick": "a.jpg",
    "image_order": ["a.jpg", "b.jpg"],
}
AVAILABLE = ["a.jpg", "b.jpg"]


def test_good_draft_has_no_violations() -> None:
    v = validate_mod.validate_draft(GOOD, _persona(), AVAILABLE)
    assert v == []


def test_title_too_long() -> None:
    d = {**GOOD, "title": "标题" * 13}   # 26 chars, well over the 20 platform limit
    v = validate_mod.validate_draft(d, _persona(), AVAILABLE)
    assert any("title" in s and "20" in s for s in v)


def test_title_too_short() -> None:
    d = {**GOOD, "title": "短"}
    v = validate_mod.validate_draft(d, _persona(), AVAILABLE)
    assert any("title" in s for s in v)


def test_body_over_platform_hard_limit() -> None:
    d = {**GOOD, "body": "x" * 1500}
    v = validate_mod.validate_draft(d, _persona(), AVAILABLE)
    assert any("body" in s and "1000" in s for s in v)


def test_forbidden_phrase() -> None:
    d = {**GOOD, "body": GOOD["body"] + " 真的是宝藏种草。"}
    v = validate_mod.validate_draft(d, _persona(), AVAILABLE)
    assert any("种草" in s for s in v)


def test_tags_count_out_of_range() -> None:
    d = {**GOOD, "tags": ["#only-one"]}
    v = validate_mod.validate_draft(d, _persona(), AVAILABLE)
    assert any("tags" in s.lower() for s in v)


def test_cover_pick_not_in_available() -> None:
    d = {**GOOD, "cover_pick": "ghost.jpg"}
    v = validate_mod.validate_draft(d, _persona(), AVAILABLE)
    assert any("cover_pick" in s for s in v)


def test_image_order_has_unknown() -> None:
    d = {**GOOD, "image_order": ["a.jpg", "ghost.jpg"]}
    v = validate_mod.validate_draft(d, _persona(), AVAILABLE)
    assert any("image_order" in s for s in v)
