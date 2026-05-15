import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills" / "publish-flow"))

from platforms import xhs as xhs_mod

DRAFT = {
    "title": "今天去逛了城市市集",
    "body": "周末的市集很有意思。" * 5,
    "tags": ["#周末", "#市集", "#City walk"],
    "cover_pick": "a.jpg",
    "image_order": ["a.jpg", "b.jpg"],
}


def test_publish_draft_invokes_cli_publish(tmp_path: Path) -> None:
    images_dir = tmp_path / "imgs"
    images_dir.mkdir()
    for n in ["a.jpg", "b.jpg"]:
        (images_dir / n).write_bytes(b"x")

    completed = MagicMock(
        returncode=0,
        stdout=json.dumps({"success": True, "title": DRAFT["title"]}),
        stderr="",
    )
    with patch.object(xhs_mod.subprocess, "run", return_value=completed) as mock_run:
        result = xhs_mod.publish_draft(
            draft=DRAFT,
            images_dir=images_dir,
            save_as_draft=False,
        )
    assert result["ok"] is True
    # Verify cli.py invocation shape
    args = mock_run.call_args.args[0]
    assert args[0] in ("uv", "python") or args[0].endswith("python")
    joined = " ".join(args)
    assert "scripts/cli.py" in joined
    assert "publish" in args
    assert "fill-publish" not in args
    # Image order matters: cover first
    images_arg_idx = args.index("--images")
    image_args = args[images_arg_idx + 1 : images_arg_idx + 3]
    assert image_args[0].endswith("a.jpg")
    assert image_args[1].endswith("b.jpg")


def test_publish_draft_save_as_draft_uses_fill_publish(tmp_path: Path) -> None:
    images_dir = tmp_path / "imgs"
    images_dir.mkdir()
    for n in ["a.jpg", "b.jpg"]:
        (images_dir / n).write_bytes(b"x")

    completed = MagicMock(
        returncode=0,
        stdout=json.dumps({"success": True}),
        stderr="",
    )
    with patch.object(xhs_mod.subprocess, "run", return_value=completed) as mock_run:
        xhs_mod.publish_draft(
            draft=DRAFT,
            images_dir=images_dir,
            save_as_draft=True,
        )
    args = mock_run.call_args.args[0]
    assert "fill-publish" in args
    assert "publish" not in [a for a in args if a == "publish"]


def test_publish_draft_propagates_cli_failure(tmp_path: Path) -> None:
    images_dir = tmp_path / "imgs"
    images_dir.mkdir()
    (images_dir / "a.jpg").write_bytes(b"x")
    (images_dir / "b.jpg").write_bytes(b"x")

    completed = MagicMock(
        returncode=2,
        stdout=json.dumps({"success": False, "error": "no images"}),
        stderr="",
    )
    with patch.object(xhs_mod.subprocess, "run", return_value=completed):
        result = xhs_mod.publish_draft(
            draft=DRAFT,
            images_dir=images_dir,
            save_as_draft=False,
        )
    assert result["ok"] is False
    assert "no images" in result["error"]
