from pathlib import Path
import sys
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills" / "publish-flow" / "scripts"))

import llm as llm_mod


def _make_mock_client(text: str) -> MagicMock:
    client = MagicMock()
    response = MagicMock()
    response.content = [MagicMock(text=text)]
    client.messages.create.return_value = response
    return client


def test_call_claude_parses_clean_json() -> None:
    client = _make_mock_client(
        '{"title": "T", "body": "B", "tags": ["#a"], '
        '"cover_pick": "x.jpg", "image_order": ["x.jpg"]}'
    )
    out = llm_mod.call_claude(
        system="sys", user="usr", client=client, model="claude-sonnet-4-6"
    )
    assert out == {
        "title": "T",
        "body": "B",
        "tags": ["#a"],
        "cover_pick": "x.jpg",
        "image_order": ["x.jpg"],
    }


def test_call_claude_strips_code_fence() -> None:
    client = _make_mock_client(
        'Sure! Here is the draft:\n```json\n{"title": "T", "body": "B", "tags": [], "cover_pick": "x", "image_order": []}\n```'
    )
    out = llm_mod.call_claude(system="s", user="u", client=client)
    assert out["title"] == "T"


def test_call_claude_raises_on_unparseable() -> None:
    client = _make_mock_client("not json at all")
    import pytest
    with pytest.raises(llm_mod.LLMOutputError):
        llm_mod.call_claude(system="s", user="u", client=client)


def test_call_claude_uses_cache_control_on_system() -> None:
    client = _make_mock_client('{"title": "T", "body": "B", "tags": [], "cover_pick": "x", "image_order": []}')
    llm_mod.call_claude(system="long-system-prompt", user="u", client=client)
    args = client.messages.create.call_args.kwargs
    # System should be a structured list with cache_control on the persona block
    assert isinstance(args["system"], list)
    assert args["system"][0]["type"] == "text"
    assert args["system"][0]["cache_control"] == {"type": "ephemeral"}
