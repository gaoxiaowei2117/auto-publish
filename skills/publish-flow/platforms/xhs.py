"""XHS adapter: converts our generic draft into a cli.py invocation.

publish_draft(draft, images_dir, save_as_draft=False) -> {"ok": bool, "url"?, "error"?}

`draft` is the dict produced by generate.py:
  { title, body, tags, cover_pick, image_order }
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def publish_draft(
    draft: dict,
    images_dir: Path,
    save_as_draft: bool = False,
    repo_root: Path | None = None,
) -> dict:
    images_dir = Path(images_dir).resolve()
    repo_root = Path(repo_root).resolve() if repo_root else _detect_repo_root()

    # Resolve image_order to absolute paths.
    image_paths = [str((images_dir / name).resolve()) for name in draft["image_order"]]

    # cli.py wants title and content as files.
    with tempfile.NamedTemporaryFile(
        "w", suffix=".txt", delete=False, encoding="utf-8"
    ) as tf:
        tf.write(draft["title"])
        title_file = tf.name
    with tempfile.NamedTemporaryFile(
        "w", suffix=".txt", delete=False, encoding="utf-8"
    ) as cf:
        cf.write(draft["body"])
        content_file = cf.name

    subcmd = "fill-publish" if save_as_draft else "publish"
    cli_path = repo_root / "scripts" / "cli.py"
    args = [
        sys.executable,
        str(cli_path),
        subcmd,
        "--title-file", title_file,
        "--content-file", content_file,
        "--images", *image_paths,
    ]
    if draft.get("tags"):
        args.append("--tags")
        # Strip leading '#' — cli.py expects bare tag names.
        args.extend(t.lstrip("#") for t in draft["tags"])

    proc = subprocess.run(args, capture_output=True, text=True)
    raw_out = proc.stdout.strip()
    try:
        parsed = json.loads(raw_out) if raw_out else {}
    except json.JSONDecodeError:
        parsed = {"raw": raw_out}

    if proc.returncode != 0 or not parsed.get("success", False):
        return {
            "ok": False,
            "error": parsed.get("error") or proc.stderr.strip() or raw_out,
            "exit_code": proc.returncode,
            "raw": parsed,
        }
    return {"ok": True, "result": parsed}


def _detect_repo_root() -> Path:
    """Walk up from this file to find scripts/cli.py."""
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        if (parent / "scripts" / "cli.py").is_file():
            return parent
    raise RuntimeError("could not locate repo root with scripts/cli.py")
