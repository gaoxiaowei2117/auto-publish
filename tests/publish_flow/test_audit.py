import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills" / "publish-flow" / "scripts"))

import audit as audit_mod


def test_write_audit_creates_dir_and_file(tmp_path: Path) -> None:
    base = tmp_path / "runs"
    record = {
        "platform": "xhs",
        "topic": "t",
        "final_draft": {"title": "T"},
        "user_choice": "publish",
        "result": {"ok": True},
    }
    p = audit_mod.write_audit(record, base_dir=base)
    assert p.exists()
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["platform"] == "xhs"
    assert data["topic"] == "t"


def test_write_audit_filename_pattern(tmp_path: Path) -> None:
    p = audit_mod.write_audit({"x": 1}, base_dir=tmp_path)
    name = p.name
    # YYYY-MM-DD-HHMMSS.json
    assert len(name) >= len("2026-05-13-180000.json")
    assert name.endswith(".json")
