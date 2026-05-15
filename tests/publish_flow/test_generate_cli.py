import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_generate_cli_invokes_and_outputs_json(tmp_path: Path) -> None:
    # Create fake images dir
    images_dir = tmp_path / "imgs"
    images_dir.mkdir()
    (images_dir / "a.jpg").write_bytes(b"x")
    (images_dir / "b.jpg").write_bytes(b"x")

    # Build a stub that monkey-patches anthropic.Anthropic before importing generate
    stub = tmp_path / "stub_runner.py"
    valid = {
        "title": "今天去逛了城市市集",
        "body": "周末的市集很有意思，淘到不少小东西。" * 3,
        "tags": ["#周末", "#市集", "#City walk"],
        "cover_pick": "a.jpg",
        "image_order": ["a.jpg", "b.jpg"],
    }
    stub.write_text(f"""
import json, sys
from unittest.mock import MagicMock
import anthropic

VALID = {valid!r}
ROOT = {str(ROOT)!r}
IMAGES_DIR = {str(images_dir)!r}

def _fake(*a, **kw):
    c = MagicMock()
    r = MagicMock()
    r.content = [MagicMock(text=json.dumps(VALID, ensure_ascii=False))]
    c.messages.create.return_value = r
    return c
anthropic.Anthropic = _fake

sys.argv = [
    "generate",
    "--topic", "test",
    "--images-dir", IMAGES_DIR,
    "--persona", ROOT + "/skills/publish-flow/persona/default.yaml",
]
sys.path.insert(0, ROOT + "/skills/publish-flow/scripts")
import generate
generate.main()
""", encoding="utf-8")

    env = os.environ.copy()
    env["ANTHROPIC_API_KEY"] = "fake"
    result = subprocess.run(
        ["uv", "run", "python", str(stub)],
        capture_output=True, text=True, env=env, cwd=ROOT, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    out = json.loads(result.stdout)
    assert out["ok"] is True
    assert out["draft"]["title"] == valid["title"]
