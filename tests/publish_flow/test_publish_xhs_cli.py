"""Test publish_xhs.py audit record assembly."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills" / "publish-flow" / "scripts"))
sys.path.insert(0, str(ROOT / "skills" / "publish-flow"))

import publish_xhs as pub_mod


def test_audit_record_includes_iterations(tmp_path: Path, monkeypatch) -> None:
    draft = {
        "title": "T",
        "body": "B",
        "tags": ["#x"],
        "cover_pick": "a.jpg",
        "image_order": ["a.jpg"],
    }
    draft_file = tmp_path / "draft.json"
    draft_file.write_text(json.dumps(draft, ensure_ascii=False), encoding="utf-8")

    history = [["violation 1"], []]
    history_file = tmp_path / "history.json"
    history_file.write_text(json.dumps(history), encoding="utf-8")

    images_dir = tmp_path / "imgs"
    images_dir.mkdir()
    (images_dir / "a.jpg").write_bytes(b"x")

    captured = {}

    def fake_publish(draft, images_dir, save_as_draft, **kw):
        return {"ok": True, "result": {"url": "https://example.com"}}

    def fake_audit(record, base_dir=None):
        captured["record"] = record
        p = tmp_path / "audit.json"
        p.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        return p

    monkeypatch.setattr(pub_mod.xhs_adapter, "publish_draft", fake_publish)
    monkeypatch.setattr(pub_mod.audit_mod, "write_audit", fake_audit)
    monkeypatch.setattr(
        sys, "argv",
        ["publish_xhs",
         "--draft-file", str(draft_file),
         "--images-dir", str(images_dir),
         "--topic", "smoke",
         "--history-file", str(history_file)],
    )

    try:
        pub_mod.main()
    except SystemExit as e:
        assert e.code == 0

    assert "iterations" in captured["record"]
    assert captured["record"]["iterations"] == history


def test_audit_record_omits_iterations_when_no_history_file(tmp_path: Path, monkeypatch) -> None:
    draft = {
        "title": "T", "body": "B", "tags": [],
        "cover_pick": "a.jpg", "image_order": ["a.jpg"],
    }
    draft_file = tmp_path / "draft.json"
    draft_file.write_text(json.dumps(draft, ensure_ascii=False), encoding="utf-8")

    images_dir = tmp_path / "imgs"
    images_dir.mkdir()
    (images_dir / "a.jpg").write_bytes(b"x")

    captured = {}
    monkeypatch.setattr(pub_mod.xhs_adapter, "publish_draft",
                        lambda **kw: {"ok": True, "result": {}})
    monkeypatch.setattr(pub_mod.audit_mod, "write_audit",
                        lambda record, base_dir=None: (captured.update({"record": record}),
                                                       tmp_path / "a.json")[1])
    monkeypatch.setattr(sys, "argv",
                        ["publish_xhs",
                         "--draft-file", str(draft_file),
                         "--images-dir", str(images_dir),
                         "--topic", "smoke"])

    try:
        pub_mod.main()
    except SystemExit as e:
        assert e.code == 0

    assert "iterations" not in captured["record"]
