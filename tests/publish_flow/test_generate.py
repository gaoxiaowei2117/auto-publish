import sys
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills" / "publish-flow" / "scripts"))

import generate as gen_mod
import persona as persona_mod


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
  forbid_phrases: ["种草"]
  prefer_first_person: true
  cta_style: subtle
  format: ""
"""
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as f:
        f.write(yaml_text)
        f.flush()
        return persona_mod.load_persona(Path(f.name))


VALID = {
    "title": "今天去逛了城市市集",
    "body": "周末的市集很有意思，淘到不少小东西。" * 3,
    "tags": ["#周末", "#市集", "#City walk"],
    "cover_pick": "a.jpg",
    "image_order": ["a.jpg", "b.jpg"],
}
INVALID = {**VALID, "body": VALID["body"] + " 真宝藏种草。"}  # forbidden phrase


def _client_returning(*responses: dict) -> MagicMock:
    """Mock client that returns each response in order on successive calls."""
    client = MagicMock()
    texts = [
        __import__("json").dumps(r, ensure_ascii=False)
        for r in responses
    ]
    msgs = [MagicMock(content=[MagicMock(text=t)]) for t in texts]
    client.messages.create.side_effect = msgs
    return client


def test_first_call_valid_no_retry() -> None:
    client = _client_returning(VALID)
    draft, history = gen_mod.generate_with_retry(
        persona=_persona(),
        topic="t",
        image_filenames=["a.jpg", "b.jpg"],
        client=client,
        max_retries=2,
    )
    assert draft == VALID
    assert history == [[]]
    assert client.messages.create.call_count == 1


def test_invalid_then_valid_retries_once() -> None:
    client = _client_returning(INVALID, VALID)
    draft, history = gen_mod.generate_with_retry(
        persona=_persona(),
        topic="t",
        image_filenames=["a.jpg", "b.jpg"],
        client=client,
        max_retries=2,
    )
    assert draft == VALID
    assert len(history) == 2   # attempt 1 (invalid) + attempt 2 (valid)
    assert any("种草" in v for v in history[0])
    assert history[1] == []
    assert client.messages.create.call_count == 2


def test_all_invalid_returns_last_with_history() -> None:
    client = _client_returning(INVALID, INVALID, INVALID)
    draft, history = gen_mod.generate_with_retry(
        persona=_persona(),
        topic="t",
        image_filenames=["a.jpg", "b.jpg"],
        client=client,
        max_retries=2,
    )
    assert draft == INVALID
    assert len(history) == 3   # initial attempt + 2 retries
    assert all(v for v in history)  # every entry non-empty
    assert client.messages.create.call_count == 3
