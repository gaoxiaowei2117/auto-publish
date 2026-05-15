"""CLI: publish a previously-generated draft via the XHS adapter.

Usage:
  uv run python skills/publish-flow/scripts/publish_xhs.py \
      --draft-file /path/to/draft.json \
      --images-dir /path/to/images/ \
      [--save-as-draft]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Make platforms/ importable.
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))   # skills/publish-flow/
from platforms import xhs as xhs_adapter   # noqa: E402

# Also make audit.py available.
sys.path.insert(0, str(HERE))
import audit as audit_mod   # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description="Publish a draft to XHS via the adapter.")
    p.add_argument("--draft-file", required=True)
    p.add_argument("--images-dir", required=True)
    p.add_argument("--save-as-draft", action="store_true",
                   help="Fill the form but don't submit.")
    p.add_argument("--topic", default="",
                   help="Original topic, for audit log only.")
    args = p.parse_args()

    draft = json.loads(Path(args.draft_file).read_text(encoding="utf-8"))
    result = xhs_adapter.publish_draft(
        draft=draft,
        images_dir=Path(args.images_dir),
        save_as_draft=args.save_as_draft,
    )

    record = {
        "platform": "xhs",
        "topic": args.topic,
        "final_draft": draft,
        "user_choice": "draft" if args.save_as_draft else "publish",
        "result": result,
    }
    audit_path = audit_mod.write_audit(record)
    result["audit_log"] = str(audit_path)

    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    sys.exit(0 if result["ok"] else 2)


if __name__ == "__main__":
    main()
