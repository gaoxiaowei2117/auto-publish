"""Audit log: write a JSON record per publish run."""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path


def _default_base() -> Path:
    return Path(os.path.expanduser("~/.auto-publish/runs"))


def write_audit(record: dict, base_dir: Path | None = None) -> Path:
    base = Path(base_dir) if base_dir else _default_base()
    base.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    path = base / f"{ts}.json"
    # Avoid overwriting if invoked twice in the same second
    n = 1
    while path.exists():
        path = base / f"{ts}-{n}.json"
        n += 1
    path.write_text(
        json.dumps(record, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path
