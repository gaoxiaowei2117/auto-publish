# auto-publish v1.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship v1.0 of auto-publish — a Skill that takes a topic + user-provided images, generates a 小红书 post via Claude using the user's persona, presents it for confirmation (B-flow), and publishes through the forked `xiaohongshu-skills` CLI.

**Architecture:** Three-layer (Orchestrator skill / per-platform adapter / fork's executor). We fork `autoclaw-cc/xiaohongshu-skills` into `gaoxiaowei2117/auto-publish`, add a new `skills/publish-flow/` sub-skill containing persona config + generation + validation + adapter, and replace the root `SKILL.md` to route the "publish" intent through our orchestrator before reaching the fork's executor.

**Tech Stack:** Python 3.11+, uv, anthropic SDK (Claude API, prompt caching), pyyaml, pytest. Fork's existing Chrome extension + bridge_server for browser automation (we don't touch it).

**Spec reference:** `docs/superpowers/specs/2026-05-13-auto-publish-design.md`

**Concrete upstream contracts (verified):**
- `python scripts/cli.py check-login` — exit 0 if logged in, 1 if not
- `python scripts/cli.py publish --title-file <p> --content-file <p> --images <p1> <p2> ... [--tags <t1> <t2>]` — publishes (JSON output on stdout)
- `python scripts/cli.py fill-publish ...` — fills form but does NOT submit (our `--draft` maps to this)
- `python scripts/cli.py get-qrcode`, `wait-login` — login flow

**Model:** `claude-sonnet-4-6` (good writing, cheaper than Opus). Prompt-cache the persona-derived system prompt; user message (topic + image names) is per-call.

---

## Task 1: Fork repo & bootstrap local workspace

**Goal:** Create the GitHub fork, clone it into the working directory while preserving the existing `docs/` we already wrote, set up `upstream` remote, make initial commit.

**Files:**
- Create on GitHub: `gaoxiaowei2117/auto-publish` (fork of `autoclaw-cc/xiaohongshu-skills`)
- Modify locally: working dir `/home/xgao/workspace/auto-publish/`

- [ ] **Step 1: Verify docs to preserve**

```bash
ls /home/xgao/workspace/auto-publish/docs/superpowers/{specs,plans}/
```
Expected: two markdown files (design + this plan).

- [ ] **Step 2: Move docs and .claude out temporarily**

```bash
mv /home/xgao/workspace/auto-publish/docs /tmp/ap-docs-bak
mv /home/xgao/workspace/auto-publish/.claude /tmp/ap-claude-bak
rmdir /home/xgao/workspace/auto-publish
ls /home/xgao/workspace/auto-publish/ 2>&1
```
Expected: dir no longer exists; the `ls` reports "No such file or directory".

- [ ] **Step 3: Create the fork on GitHub**

```bash
gh repo fork autoclaw-cc/xiaohongshu-skills \
  --fork-name auto-publish \
  --clone=false
```
Expected: fork created at `https://github.com/gaoxiaowei2117/auto-publish`. If the fork already exists, the command is idempotent and prints a notice.

- [ ] **Step 4: Clone the fork into the workspace**

```bash
cd /home/xgao/workspace
gh repo clone gaoxiaowei2117/auto-publish auto-publish
ls /home/xgao/workspace/auto-publish/ | head
```
Expected: `auto-publish/` now contains the cloned fork (SKILL.md, scripts/, extension/, etc.).

- [ ] **Step 5: Restore docs and .claude into the fork**

```bash
mv /tmp/ap-docs-bak /home/xgao/workspace/auto-publish/docs
mv /tmp/ap-claude-bak /home/xgao/workspace/auto-publish/.claude
ls /home/xgao/workspace/auto-publish/docs/superpowers/{specs,plans}/
```
Expected: both spec + plan markdown files visible.

- [ ] **Step 6: Add upstream remote**

```bash
cd /home/xgao/workspace/auto-publish
git remote add upstream https://github.com/autoclaw-cc/xiaohongshu-skills.git
git remote -v
```
Expected output contains `origin` (your fork) and `upstream` (autoclaw-cc).

- [ ] **Step 7: Commit the design + plan docs**

```bash
git add docs/
git commit -m "$(cat <<'EOF'
docs: add auto-publish v1.0 design and implementation plan

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
git push origin main
```

- [ ] **Step 8: Verify uv environment installs**

```bash
cd /home/xgao/workspace/auto-publish
uv sync
```
Expected: dependencies install cleanly. (We're not adding our own deps yet — that's Task 2.)

---

## Task 2: Add Python dependencies and create publish-flow skeleton

**Goal:** Add `anthropic` and `pyyaml` to `pyproject.toml`, create the empty `skills/publish-flow/` tree with placeholder files so subsequent tasks have somewhere to write code.

**Files:**
- Modify: `pyproject.toml`
- Create: `skills/publish-flow/{persona,platforms,scripts}/`
- Create: `tests/publish_flow/`

- [ ] **Step 1: Add dependencies to pyproject.toml**

Edit `pyproject.toml`, replace the `dependencies = [...]` block with:

```toml
dependencies = [
    "python-socks>=2.8.1",
    "requests>=2.28.0",
    "websockets>=12.0",
    "anthropic>=0.40.0",
    "pyyaml>=6.0",
]
```

- [ ] **Step 2: Run uv sync to install**

```bash
uv sync
uv run python -c "import anthropic, yaml; print(anthropic.__version__, yaml.__version__)"
```
Expected: prints both versions, no errors.

- [ ] **Step 3: Create publish-flow directory tree**

```bash
cd /home/xgao/workspace/auto-publish
mkdir -p skills/publish-flow/{persona,platforms,scripts}
mkdir -p tests/publish_flow
touch skills/publish-flow/scripts/__init__.py
touch tests/publish_flow/__init__.py
```

- [ ] **Step 4: Verify pytest still runs**

```bash
uv run pytest tests/ -q
```
Expected: existing tests pass (or are no-ops); no errors about our new empty `__init__.py`.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock skills/publish-flow tests/publish_flow
git commit -m "$(cat <<'EOF'
chore: add anthropic + pyyaml deps; scaffold publish-flow skill

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Persona schema, sample file, and loader

**Goal:** Define `persona/default.yaml` with the full v1.0 schema; write `scripts/persona.py` that loads it into a dataclass with defaults and validation. TDD.

**Files:**
- Create: `skills/publish-flow/persona/default.yaml`
- Create: `skills/publish-flow/persona/README.md`
- Create: `skills/publish-flow/scripts/persona.py`
- Create: `tests/publish_flow/test_persona.py`

- [ ] **Step 1: Write the failing test**

`tests/publish_flow/test_persona.py`:

```python
"""Tests for persona loading."""
from pathlib import Path

import pytest

import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills" / "publish-flow" / "scripts"))

import persona as persona_mod


SAMPLE_YAML = """
name: test
display_name: "Test"
description: "A test persona"
voice:
  tone: "casual"
  style_keywords: ["真实", "短"]
  avoid_tones: ["种草"]
length:
  title_chars: [10, 20]
  body_chars: [200, 500]
emoji:
  usage: light
  preferred: ["🌿"]
  avoid: ["💕"]
hashtags:
  count: [3, 4]
  style: mix
  preferred_categories: ["生活"]
  avoid_categories: ["美妆"]
content_rules:
  forbid_phrases: ["种草", "yyds"]
  prefer_first_person: true
  cta_style: subtle
  format: "短段落"
examples:
  - title: "示例标题"
    body: "示例正文。"
    tags: ["#示例"]
    note: "test example"
"""


def test_load_persona_from_file(tmp_path: Path) -> None:
    p = tmp_path / "p.yaml"
    p.write_text(SAMPLE_YAML, encoding="utf-8")
    persona = persona_mod.load_persona(p)
    assert persona.name == "test"
    assert persona.voice.tone == "casual"
    assert persona.length.title_chars == (10, 20)
    assert persona.length.body_chars == (200, 500)
    assert persona.emoji.usage == "light"
    assert "种草" in persona.content_rules.forbid_phrases
    assert len(persona.examples) == 1
    assert persona.examples[0].title == "示例标题"


def test_load_persona_missing_required_raises(tmp_path: Path) -> None:
    p = tmp_path / "p.yaml"
    p.write_text("name: x", encoding="utf-8")
    with pytest.raises(persona_mod.PersonaError):
        persona_mod.load_persona(p)


def test_load_default_persona_succeeds() -> None:
    default = ROOT / "skills" / "publish-flow" / "persona" / "default.yaml"
    persona = persona_mod.load_persona(default)
    assert persona.name
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/publish_flow/test_persona.py -v
```
Expected: `ModuleNotFoundError: No module named 'persona'`.

- [ ] **Step 3: Write the persona loader**

`skills/publish-flow/scripts/persona.py`:

```python
"""Persona loader.

Loads a persona YAML file into typed dataclasses with validation.
Used by generate.py to build the system prompt for content generation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


class PersonaError(ValueError):
    pass


@dataclass(frozen=True)
class Voice:
    tone: str
    style_keywords: list[str]
    avoid_tones: list[str]


@dataclass(frozen=True)
class Length:
    title_chars: tuple[int, int]
    body_chars: tuple[int, int]


@dataclass(frozen=True)
class Emoji:
    usage: str  # none | light | heavy
    preferred: list[str]
    avoid: list[str]


@dataclass(frozen=True)
class Hashtags:
    count: tuple[int, int]
    style: str  # specific | broad | mix
    preferred_categories: list[str]
    avoid_categories: list[str]


@dataclass(frozen=True)
class ContentRules:
    forbid_phrases: list[str]
    prefer_first_person: bool
    cta_style: str  # none | subtle | explicit
    format: str


@dataclass(frozen=True)
class Example:
    title: str
    body: str
    tags: list[str]
    note: str = ""


@dataclass(frozen=True)
class Persona:
    name: str
    display_name: str
    description: str
    voice: Voice
    length: Length
    emoji: Emoji
    hashtags: Hashtags
    content_rules: ContentRules
    examples: list[Example] = field(default_factory=list)


def _require(d: dict, key: str, where: str) -> object:
    if key not in d:
        raise PersonaError(f"missing '{key}' in {where}")
    return d[key]


def _pair(v, where: str) -> tuple[int, int]:
    if not isinstance(v, list) or len(v) != 2:
        raise PersonaError(f"expected [min, max] in {where}, got {v!r}")
    return (int(v[0]), int(v[1]))


def load_persona(path: Path) -> Persona:
    path = Path(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise PersonaError(f"persona file must be a YAML mapping: {path}")

    voice_d = _require(raw, "voice", path.name)
    length_d = _require(raw, "length", path.name)
    emoji_d = _require(raw, "emoji", path.name)
    hashtags_d = _require(raw, "hashtags", path.name)
    rules_d = _require(raw, "content_rules", path.name)

    examples = [
        Example(
            title=str(_require(e, "title", "example")),
            body=str(_require(e, "body", "example")),
            tags=list(_require(e, "tags", "example")),
            note=str(e.get("note", "")),
        )
        for e in raw.get("examples", []) or []
    ]

    return Persona(
        name=str(_require(raw, "name", path.name)),
        display_name=str(raw.get("display_name", raw["name"])),
        description=str(raw.get("description", "")),
        voice=Voice(
            tone=str(_require(voice_d, "tone", "voice")),
            style_keywords=list(voice_d.get("style_keywords", [])),
            avoid_tones=list(voice_d.get("avoid_tones", [])),
        ),
        length=Length(
            title_chars=_pair(_require(length_d, "title_chars", "length"), "length.title_chars"),
            body_chars=_pair(_require(length_d, "body_chars", "length"), "length.body_chars"),
        ),
        emoji=Emoji(
            usage=str(_require(emoji_d, "usage", "emoji")),
            preferred=list(emoji_d.get("preferred", [])),
            avoid=list(emoji_d.get("avoid", [])),
        ),
        hashtags=Hashtags(
            count=_pair(_require(hashtags_d, "count", "hashtags"), "hashtags.count"),
            style=str(_require(hashtags_d, "style", "hashtags")),
            preferred_categories=list(hashtags_d.get("preferred_categories", [])),
            avoid_categories=list(hashtags_d.get("avoid_categories", [])),
        ),
        content_rules=ContentRules(
            forbid_phrases=list(rules_d.get("forbid_phrases", [])),
            prefer_first_person=bool(rules_d.get("prefer_first_person", True)),
            cta_style=str(rules_d.get("cta_style", "subtle")),
            format=str(rules_d.get("format", "")),
        ),
        examples=examples,
    )
```

- [ ] **Step 4: Create the sample default.yaml**

`skills/publish-flow/persona/default.yaml`:

```yaml
# 编辑这份配置以匹配你的小红书人设。
# 修改后无需重启任何东西，下次发布即生效。
# 字段说明见同目录 README.md。

name: default
display_name: "我的小红书"
description: "默认人设。请按你自己的口吻修改后再用。"

voice:
  tone: "亲切但不假，像跟朋友分享周末发现"
  style_keywords: ["真实", "有信息密度", "不卖弄", "偶尔自嘲"]
  avoid_tones: ["种草文", "微商口吻", "鸡汤", "标题党"]

length:
  title_chars: [12, 20]
  body_chars: [300, 800]

emoji:
  usage: light
  preferred: ["🌿", "📷", "✨", "🍵"]
  avoid: ["💕", "😍", "🥺"]

hashtags:
  count: [3, 5]
  style: mix
  preferred_categories: ["生活方式", "城市", "周末"]
  avoid_categories: ["美妆", "穿搭"]

content_rules:
  forbid_phrases: ["种草", "宝藏", "yyds", "绝绝子", "巨好吃"]
  prefer_first_person: true
  cta_style: subtle
  format: "短段落 + 适度分行"

# 1-3 篇你认可的过往笔记 —— 模型从这里学你的语气。
# 强烈建议至少填 1 篇，否则生成质量会显著下降。
examples:
  - title: "（替换成你自己的标题）"
    body: |
      （替换成你自己的过往笔记原文。
      多写几行让模型学到你的节奏、句式、收尾方式。
      暂时没有也可以先用 placeholder，但越早换上越好。）
    tags: ["#示例", "#请替换"]
    note: "首次使用时请替换为你的真实笔记"
```

- [ ] **Step 5: Create persona README**

`skills/publish-flow/persona/README.md`:

```markdown
# Persona 配置说明

`default.yaml` 是 v1.0 唯一使用的人设。v1.1 起支持目录下多份 yaml，命令传 `--persona <name>` 切换。

## 字段速查

| 字段 | 类型 | 说明 |
|------|------|------|
| `voice.tone` | str | 一句话描述你的语气 |
| `voice.style_keywords` | list[str] | 想要的风格关键词 |
| `voice.avoid_tones` | list[str] | 想避免的口吻 |
| `length.title_chars` | [min, max] | 标题字数范围（平台硬限 20） |
| `length.body_chars` | [min, max] | 正文字数范围（平台硬限 1000） |
| `emoji.usage` | none / light / heavy | emoji 用量 |
| `emoji.preferred` | list[str] | 偏好的 emoji |
| `emoji.avoid` | list[str] | 避免的 emoji |
| `hashtags.count` | [min, max] | 话题数范围 |
| `hashtags.style` | specific / broad / mix | 话题风格 |
| `content_rules.forbid_phrases` | list[str] | 硬性禁用词，违反则模型重写 |
| `content_rules.cta_style` | none / subtle / explicit | 呼吁行为的强度 |
| `examples` | list | 1-3 篇过往笔记，最影响风格迁移 |

## examples 为什么最重要

模型对"风格描述"（tone、keywords）的遵循度只有 70-90%。但你给它 1-3 篇你认可的过往笔记当 few-shot example，遵循度能再上一个台阶。强烈建议至少填 1 篇。
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
uv run pytest tests/publish_flow/test_persona.py -v
```
Expected: 3 passing.

- [ ] **Step 7: Commit**

```bash
git add skills/publish-flow/persona skills/publish-flow/scripts/persona.py tests/publish_flow/test_persona.py
git commit -m "$(cat <<'EOF'
feat(publish-flow): add persona schema, sample default.yaml, and loader

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Prompt assembly

**Goal:** Pure function `build_messages(persona, topic, image_filenames)` returning the (system, user) message pair for Claude. Persona-derived portion goes into `system` so it caches across regen retries.

**Files:**
- Create: `skills/publish-flow/scripts/prompt.py`
- Create: `tests/publish_flow/test_prompt.py`

- [ ] **Step 1: Write the failing test**

`tests/publish_flow/test_prompt.py`:

```python
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills" / "publish-flow" / "scripts"))

import persona as persona_mod
import prompt as prompt_mod


def _sample_persona() -> persona_mod.Persona:
    yaml_text = """
name: test
display_name: "Test"
description: ""
voice:
  tone: "casual"
  style_keywords: ["k1", "k2"]
  avoid_tones: ["AVOID1"]
length:
  title_chars: [10, 20]
  body_chars: [200, 500]
emoji:
  usage: light
  preferred: ["🌿"]
  avoid: ["💕"]
hashtags:
  count: [3, 4]
  style: mix
  preferred_categories: ["a"]
  avoid_categories: ["b"]
content_rules:
  forbid_phrases: ["FORBID1"]
  prefer_first_person: true
  cta_style: subtle
  format: "short"
examples:
  - title: "EX_TITLE"
    body: "EX_BODY"
    tags: ["#x"]
"""
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as f:
        f.write(yaml_text)
        path = f.name
    return persona_mod.load_persona(Path(path))


def test_build_messages_contains_persona_fields() -> None:
    persona = _sample_persona()
    msgs = prompt_mod.build_messages(
        persona, topic="topic-X", image_filenames=["a.jpg", "b.jpg"]
    )
    system = msgs["system"]
    user = msgs["user"]

    # persona fields are in system (so they cache)
    assert "casual" in system
    assert "k1" in system and "k2" in system
    assert "AVOID1" in system
    assert "FORBID1" in system
    assert "EX_TITLE" in system and "EX_BODY" in system

    # topic + images are in user (the per-call part)
    assert "topic-X" in user
    assert "a.jpg" in user and "b.jpg" in user

    # constraints surfaced
    assert "20" in system and "500" in system   # hard length limits


def test_build_messages_no_examples() -> None:
    # Same but strip examples — should still work
    persona = _sample_persona()
    from dataclasses import replace
    persona = replace(persona, examples=[])
    msgs = prompt_mod.build_messages(persona, topic="t", image_filenames=["x.jpg"])
    assert "EXAMPLES" not in msgs["system"] or "no examples" in msgs["system"].lower()
```

- [ ] **Step 2: Run test, verify it fails**

```bash
uv run pytest tests/publish_flow/test_prompt.py -v
```
Expected: `ModuleNotFoundError: No module named 'prompt'`.

- [ ] **Step 3: Write prompt.py**

`skills/publish-flow/scripts/prompt.py`:

```python
"""Prompt assembly.

build_messages(persona, topic, image_filenames) -> {"system": str, "user": str}

The persona-derived portion goes into `system` so it can be prompt-cached
across regeneration retries within a single publish session. The user portion
(topic + images) is per-call and not cached.
"""
from __future__ import annotations

from persona import Persona


PLATFORM_HARD_LIMITS = """\
HARD PLATFORM LIMITS (must not be exceeded):
- title: ≤ 20 chars
- body: ≤ 1000 chars
- images: ≤ 9
- tags (hashtags): not enforced by platform; use persona setting
"""


def build_messages(
    persona: Persona,
    topic: str,
    image_filenames: list[str],
    user_feedback: str | None = None,
) -> dict[str, str]:
    """Build (system, user) messages for the Claude generation call.

    Args:
        persona: Loaded persona configuration.
        topic: User-provided topic / brief.
        image_filenames: Just the basenames; the model uses them as hints
            for cover selection and ordering, not for actual visual analysis.
        user_feedback: If this is a regeneration, the user's revision request.
    """
    system = _build_system(persona)
    user = _build_user(topic, image_filenames, user_feedback)
    return {"system": system, "user": user}


def _build_system(p: Persona) -> str:
    lines: list[str] = []
    lines.append("You are writing a 小红书 (Xiaohongshu) post in the user's voice.")
    lines.append("")
    lines.append("VOICE:")
    lines.append(f"  tone: {p.voice.tone}")
    lines.append(f"  style_keywords: {', '.join(p.voice.style_keywords)}")
    lines.append(f"  avoid_tones: {', '.join(p.voice.avoid_tones)}")
    lines.append("")
    lines.append("LENGTH:")
    lines.append(
        f"  title: target {p.length.title_chars[0]}-{p.length.title_chars[1]} chars "
        f"(platform hard limit 20)"
    )
    lines.append(
        f"  body: target {p.length.body_chars[0]}-{p.length.body_chars[1]} chars "
        f"(platform hard limit 1000)"
    )
    lines.append("")
    lines.append("EMOJI:")
    lines.append(f"  usage: {p.emoji.usage}")
    lines.append(f"  preferred: {' '.join(p.emoji.preferred) or '(none)'}")
    lines.append(f"  avoid: {' '.join(p.emoji.avoid) or '(none)'}")
    lines.append("")
    lines.append("HASHTAGS:")
    lines.append(
        f"  count: {p.hashtags.count[0]}-{p.hashtags.count[1]}"
    )
    lines.append(f"  style: {p.hashtags.style}")
    lines.append(f"  preferred_categories: {', '.join(p.hashtags.preferred_categories) or '(none)'}")
    lines.append(f"  avoid_categories: {', '.join(p.hashtags.avoid_categories) or '(none)'}")
    lines.append("")
    lines.append("CONTENT RULES:")
    lines.append(
        f"  forbid_phrases (MUST NOT appear): {', '.join(p.content_rules.forbid_phrases) or '(none)'}"
    )
    lines.append(f"  prefer_first_person: {p.content_rules.prefer_first_person}")
    lines.append(f"  cta_style: {p.content_rules.cta_style}")
    lines.append(f"  format: {p.content_rules.format}")
    lines.append("")

    if p.examples:
        lines.append("EXAMPLES OF THE USER'S OWN STYLE (learn from these):")
        for i, ex in enumerate(p.examples, 1):
            lines.append(f"  Example {i}:")
            lines.append(f"    title: {ex.title}")
            lines.append(f"    body: {ex.body}")
            lines.append(f"    tags: {' '.join(ex.tags)}")
            if ex.note:
                lines.append(f"    (author's note: {ex.note})")
            lines.append("")
    else:
        lines.append("EXAMPLES: (no examples provided — quality will suffer)")
        lines.append("")

    lines.append(PLATFORM_HARD_LIMITS)
    lines.append("")
    lines.append(
        "OUTPUT: Respond with ONLY a JSON object (no prose around it), matching:"
    )
    lines.append('  {')
    lines.append('    "title": "string, <=20 chars",')
    lines.append('    "body": "string, <=1000 chars",')
    lines.append('    "tags": ["#tag1", "#tag2", ...],')
    lines.append('    "cover_pick": "<exact filename from available images>",')
    lines.append('    "image_order": ["<filename>", ...]   // permutation of available')
    lines.append('  }')
    return "\n".join(lines)


def _build_user(topic: str, image_filenames: list[str], user_feedback: str | None) -> str:
    parts: list[str] = []
    parts.append(f"Topic: {topic}")
    parts.append("")
    parts.append("Available images (filenames only):")
    for fn in image_filenames:
        parts.append(f"  - {fn}")
    if user_feedback:
        parts.append("")
        parts.append("Revision feedback from a previous draft:")
        parts.append(user_feedback)
    parts.append("")
    parts.append(
        "Pick one image as cover (likely the most representative) and order the rest "
        "so the first 3 are the strongest hook."
    )
    return "\n".join(parts)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/publish_flow/test_prompt.py -v
```
Expected: 2 passing.

- [ ] **Step 5: Commit**

```bash
git add skills/publish-flow/scripts/prompt.py tests/publish_flow/test_prompt.py
git commit -m "$(cat <<'EOF'
feat(publish-flow): assemble Claude prompts with cacheable persona block

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Anthropic API caller (with prompt caching)

**Goal:** `call_claude(messages, client=None) -> dict` — sends the messages to Claude, applies prompt caching to the system block, parses JSON from the response. Tests mock the SDK client so they run offline.

**Files:**
- Create: `skills/publish-flow/scripts/llm.py`
- Create: `tests/publish_flow/test_llm.py`

- [ ] **Step 1: Write the failing test**

`tests/publish_flow/test_llm.py`:

```python
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
```

- [ ] **Step 2: Run test, verify it fails**

```bash
uv run pytest tests/publish_flow/test_llm.py -v
```
Expected: `ModuleNotFoundError: No module named 'llm'`.

- [ ] **Step 3: Write llm.py**

`skills/publish-flow/scripts/llm.py`:

```python
"""Claude API caller with prompt caching.

call_claude(system, user, client=None, model=...) -> dict

The `system` string is wrapped in a content block with cache_control="ephemeral"
so the persona-derived prefix caches across regen retries within a session
(5-minute TTL).
"""
from __future__ import annotations

import json
import re

DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_MAX_TOKENS = 2048


class LLMOutputError(ValueError):
    pass


def call_claude(
    system: str,
    user: str,
    client=None,
    model: str = DEFAULT_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> dict:
    """Send messages to Claude, parse JSON output, return dict."""
    if client is None:
        import anthropic
        client = anthropic.Anthropic()

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=[
            {
                "type": "text",
                "text": system,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {"role": "user", "content": user},
        ],
    )

    # response.content is a list of content blocks; first is usually text
    text = response.content[0].text if response.content else ""
    return _parse_json(text)


def _parse_json(text: str) -> dict:
    """Extract JSON from a model response. Tolerates code fences and prose."""
    # Try direct parse first.
    candidate = text.strip()
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    # Strip ```json ... ``` fences.
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if fence:
        try:
            return json.loads(fence.group(1))
        except json.JSONDecodeError:
            pass

    # Greedy {...} match.
    brace = re.search(r"\{.*\}", text, re.S)
    if brace:
        try:
            return json.loads(brace.group(0))
        except json.JSONDecodeError:
            pass

    raise LLMOutputError(f"could not parse JSON from model output: {text!r}")
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/publish_flow/test_llm.py -v
```
Expected: 4 passing.

- [ ] **Step 5: Commit**

```bash
git add skills/publish-flow/scripts/llm.py tests/publish_flow/test_llm.py
git commit -m "$(cat <<'EOF'
feat(publish-flow): Anthropic SDK wrapper with prompt caching and JSON parsing

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Hard validation rules

**Goal:** `validate_draft(draft, persona, available_images) -> list[str]` returning a list of human-readable violations (empty = pass). Checks title/body lengths, forbidden phrases, emoji counts, cover_pick + image_order against the available set.

**Files:**
- Create: `skills/publish-flow/scripts/validate.py`
- Create: `tests/publish_flow/test_validate.py`

- [ ] **Step 1: Write the failing test**

`tests/publish_flow/test_validate.py`:

```python
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
    d = {**GOOD, "title": "这个标题非常非常非常非常非常非常非常的长"}
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
```

- [ ] **Step 2: Run test, verify it fails**

```bash
uv run pytest tests/publish_flow/test_validate.py -v
```
Expected: `ModuleNotFoundError: No module named 'validate'`.

- [ ] **Step 3: Write validate.py**

`skills/publish-flow/scripts/validate.py`:

```python
"""Hard validation rules for generated drafts.

validate_draft(draft, persona, available_images) -> list[str]

Empty list = valid. Non-empty list = violations to feed back to the model
for a regeneration attempt.
"""
from __future__ import annotations

from persona import Persona

PLATFORM_TITLE_MAX = 20
PLATFORM_BODY_MAX = 1000


def validate_draft(draft: dict, persona: Persona, available_images: list[str]) -> list[str]:
    violations: list[str] = []

    title = draft.get("title", "")
    body = draft.get("body", "")
    tags = draft.get("tags", []) or []
    cover = draft.get("cover_pick", "")
    image_order = draft.get("image_order", []) or []

    # Title length
    t_min, t_max_pers = persona.length.title_chars
    if len(title) > PLATFORM_TITLE_MAX:
        violations.append(
            f"title exceeds platform hard limit 20 chars (got {len(title)})"
        )
    elif len(title) > t_max_pers:
        violations.append(
            f"title exceeds persona max {t_max_pers} (got {len(title)})"
        )
    if len(title) < t_min:
        violations.append(
            f"title shorter than persona min {t_min} (got {len(title)})"
        )

    # Body length
    b_min, b_max_pers = persona.length.body_chars
    if len(body) > PLATFORM_BODY_MAX:
        violations.append(
            f"body exceeds platform hard limit 1000 chars (got {len(body)})"
        )
    elif len(body) > b_max_pers:
        violations.append(
            f"body exceeds persona max {b_max_pers} (got {len(body)})"
        )
    if len(body) < b_min:
        violations.append(
            f"body shorter than persona min {b_min} (got {len(body)})"
        )

    # Forbidden phrases
    for phrase in persona.content_rules.forbid_phrases:
        if phrase and phrase in (title + " " + body):
            violations.append(
                f"contains forbidden phrase '{phrase}'"
            )

    # Tags count
    tag_min, tag_max = persona.hashtags.count
    if not (tag_min <= len(tags) <= tag_max):
        violations.append(
            f"tags count {len(tags)} out of range [{tag_min}, {tag_max}]"
        )

    # Cover pick must be in available set
    if cover and cover not in available_images:
        violations.append(
            f"cover_pick '{cover}' not in available images {available_images}"
        )
    if not cover:
        violations.append("cover_pick is empty")

    # image_order entries must all be in available
    unknown = [f for f in image_order if f not in available_images]
    if unknown:
        violations.append(f"image_order contains unknown filenames: {unknown}")

    return violations
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/publish_flow/test_validate.py -v
```
Expected: 8 passing.

- [ ] **Step 5: Commit**

```bash
git add skills/publish-flow/scripts/validate.py tests/publish_flow/test_validate.py
git commit -m "$(cat <<'EOF'
feat(publish-flow): hard validation for length, forbidden phrases, image refs

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Generate-with-retry loop

**Goal:** `generate_with_retry(persona, topic, images, client, max_retries=2)` — generates, validates, on failure feeds violations back as feedback and retries up to `max_retries` more times. Returns `(draft, violations_history)`; the violations list is empty if final draft is clean.

**Files:**
- Create: `skills/publish-flow/scripts/generate.py`
- Create: `tests/publish_flow/test_generate.py`

- [ ] **Step 1: Write the failing test**

`tests/publish_flow/test_generate.py`:

```python
from pathlib import Path
import sys
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills" / "publish-flow" / "scripts"))

import persona as persona_mod
import generate as gen_mod


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
    assert history == []
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
    assert len(history) == 1
    assert any("种草" in v for v in history[0])
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
    assert client.messages.create.call_count == 3
```

- [ ] **Step 2: Run test, verify it fails**

```bash
uv run pytest tests/publish_flow/test_generate.py -v
```
Expected: ModuleNotFoundError.

- [ ] **Step 3: Write generate.py**

`skills/publish-flow/scripts/generate.py`:

```python
"""Generation orchestrator: build prompt, call Claude, validate, retry.

generate_with_retry(persona, topic, image_filenames, client=None, max_retries=2)
  -> (final_draft: dict, violations_history: list[list[str]])

`violations_history[i]` is the validation result of attempt i (empty if pass).
The returned draft is whichever attempt was last; check
`violations_history[-1]` to know whether it's clean.

`user_feedback` parameter allows external (non-validation) revision requests
— e.g., the user said "make it shorter".
"""
from __future__ import annotations

from persona import Persona
from prompt import build_messages
from llm import call_claude
from validate import validate_draft


def generate_once(
    persona: Persona,
    topic: str,
    image_filenames: list[str],
    client=None,
    user_feedback: str | None = None,
) -> dict:
    """Single generation attempt without retry."""
    msgs = build_messages(persona, topic, image_filenames, user_feedback=user_feedback)
    return call_claude(system=msgs["system"], user=msgs["user"], client=client)


def generate_with_retry(
    persona: Persona,
    topic: str,
    image_filenames: list[str],
    client=None,
    max_retries: int = 2,
    user_feedback: str | None = None,
) -> tuple[dict, list[list[str]]]:
    """Generate; if validation fails, retry up to `max_retries` more times with
    violations fed back as feedback. Returns (last_draft, list_of_violation_lists).
    """
    violations_history: list[list[str]] = []
    draft: dict = {}
    feedback = user_feedback

    for attempt in range(max_retries + 1):
        draft = generate_once(
            persona, topic, image_filenames, client=client, user_feedback=feedback
        )
        violations = validate_draft(draft, persona, image_filenames)
        violations_history.append(violations)
        if not violations:
            return draft, violations_history
        # Build feedback for next iteration.
        feedback = (
            "The previous draft had these validation problems. Fix all of them:\n  - "
            + "\n  - ".join(violations)
        )

    return draft, violations_history
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/publish_flow/test_generate.py -v
```
Expected: 3 passing.

- [ ] **Step 5: Commit**

```bash
git add skills/publish-flow/scripts/generate.py tests/publish_flow/test_generate.py
git commit -m "$(cat <<'EOF'
feat(publish-flow): generate-with-retry pipes validation back as feedback

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: `generate.py` CLI entry — produce a draft JSON from topic + images

**Goal:** Command-line interface so the orchestrator skill can invoke it via `uv run python skills/publish-flow/scripts/generate.py --topic ... --images-dir ...`. Outputs JSON to stdout: `{"ok": true, "draft": {...}, "violations": [...]}`.

**Files:**
- Modify: `skills/publish-flow/scripts/generate.py` (add CLI)
- Create: `tests/publish_flow/test_generate_cli.py`

- [ ] **Step 1: Write the failing test**

`tests/publish_flow/test_generate_cli.py`:

```python
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
```

> **NOTE for the implementer:** This integration test uses a Python stub to inject a mock SDK before importing `generate`. If the test proves flaky on your system, you may convert it to a pure unit test of `main()` by calling it in-process with `monkeypatch` instead.

- [ ] **Step 2: Run test, verify it fails**

```bash
uv run pytest tests/publish_flow/test_generate_cli.py -v
```
Expected: AttributeError or similar — `generate.main` does not yet exist.

- [ ] **Step 3: Add CLI to generate.py**

Append to `skills/publish-flow/scripts/generate.py`:

```python
def main() -> None:
    """CLI entry. Produces a draft JSON from a topic + images directory."""
    import argparse
    import json
    import sys
    from pathlib import Path
    from persona import load_persona

    parser = argparse.ArgumentParser(
        description="Generate an XHS draft via Claude from topic + images.",
    )
    parser.add_argument("--topic", required=True, help="Topic / brief from the user.")
    parser.add_argument(
        "--images-dir",
        required=True,
        help="Directory containing the image files to use.",
    )
    parser.add_argument(
        "--persona",
        default="skills/publish-flow/persona/default.yaml",
        help="Path to persona YAML.",
    )
    parser.add_argument(
        "--feedback",
        default=None,
        help="Optional user revision feedback from a previous iteration.",
    )
    parser.add_argument(
        "--regen-budget",
        type=int,
        default=2,
        help="Max hard-validation retries (NOT user revisions).",
    )
    args = parser.parse_args()

    persona = load_persona(Path(args.persona))
    images_dir = Path(args.images_dir).expanduser()
    if not images_dir.is_dir():
        print(json.dumps({"ok": False, "error": f"images-dir not found: {images_dir}"},
                         ensure_ascii=False), flush=True)
        sys.exit(2)

    image_exts = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
    image_files = sorted(
        [p.name for p in images_dir.iterdir() if p.suffix.lower() in image_exts]
    )
    if not image_files:
        print(json.dumps({"ok": False, "error": "no images in images-dir"},
                         ensure_ascii=False), flush=True)
        sys.exit(2)

    if len(image_files) > 9:
        image_files = image_files[:9]
        truncated = True
    else:
        truncated = False

    try:
        draft, history = generate_with_retry(
            persona=persona,
            topic=args.topic,
            image_filenames=image_files,
            max_retries=args.regen_budget,
            user_feedback=args.feedback,
        )
    except Exception as e:
        print(json.dumps({"ok": False, "error": f"generation failed: {e}"},
                         ensure_ascii=False), flush=True)
        sys.exit(2)

    final_violations = history[-1] if history else []
    out = {
        "ok": True,
        "draft": draft,
        "violations": final_violations,
        "history": history,
        "images_dir": str(images_dir.resolve()),
        "image_files": image_files,
        "truncated_to_9": truncated,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/publish_flow/test_generate_cli.py -v
```
Expected: 1 passing.

- [ ] **Step 5: Commit**

```bash
git add skills/publish-flow/scripts/generate.py tests/publish_flow/test_generate_cli.py
git commit -m "$(cat <<'EOF'
feat(publish-flow): generate.py CLI entry — topic + images dir to draft JSON

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: Audit log writer

**Goal:** `write_audit(record, path=None) -> Path` — writes a JSON record to `~/.auto-publish/runs/YYYY-MM-DD-HHMMSS.json` (or a caller-provided path). Creates the directory if missing.

**Files:**
- Create: `skills/publish-flow/scripts/audit.py`
- Create: `tests/publish_flow/test_audit.py`

- [ ] **Step 1: Write the failing test**

`tests/publish_flow/test_audit.py`:

```python
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
```

- [ ] **Step 2: Run test, verify it fails**

```bash
uv run pytest tests/publish_flow/test_audit.py -v
```
Expected: ModuleNotFoundError.

- [ ] **Step 3: Write audit.py**

`skills/publish-flow/scripts/audit.py`:

```python
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
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/publish_flow/test_audit.py -v
```
Expected: 2 passing.

- [ ] **Step 5: Commit**

```bash
git add skills/publish-flow/scripts/audit.py tests/publish_flow/test_audit.py
git commit -m "$(cat <<'EOF'
feat(publish-flow): audit log writer for per-run JSON records

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: XHS adapter & publish_xhs.py CLI

**Goal:** `platforms/xhs.py` exposes `publish_draft(draft, images_dir, dry_run, save_as_draft)` that:
1. Writes `title` to a temp file, `body` to another (cli.py wants `--title-file` / `--content-file`)
2. Maps `image_order` to absolute paths under `images_dir`
3. Invokes `python scripts/cli.py {publish|fill-publish}` with the right args
4. Parses the JSON output from cli.py and returns `{ok, url|error}`

Plus `publish_xhs.py` CLI for the orchestrator to call.

**Files:**
- Create: `skills/publish-flow/platforms/__init__.py`
- Create: `skills/publish-flow/platforms/xhs.py`
- Create: `skills/publish-flow/scripts/publish_xhs.py`
- Create: `tests/publish_flow/test_xhs_adapter.py`

- [ ] **Step 1: Write the failing test**

`tests/publish_flow/test_xhs_adapter.py`:

```python
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

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
```

- [ ] **Step 2: Run test, verify it fails**

```bash
uv run pytest tests/publish_flow/test_xhs_adapter.py -v
```
Expected: ModuleNotFoundError or AttributeError.

- [ ] **Step 3: Write platforms/__init__.py (empty) and xhs.py**

`skills/publish-flow/platforms/__init__.py`: empty.

`skills/publish-flow/platforms/xhs.py`:

```python
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
```

- [ ] **Step 4: Run adapter tests**

```bash
uv run pytest tests/publish_flow/test_xhs_adapter.py -v
```
Expected: 3 passing.

- [ ] **Step 5: Write publish_xhs.py CLI**

`skills/publish-flow/scripts/publish_xhs.py`:

```python
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
```

- [ ] **Step 6: Commit**

```bash
git add skills/publish-flow/platforms skills/publish-flow/scripts/publish_xhs.py tests/publish_flow/test_xhs_adapter.py
git commit -m "$(cat <<'EOF'
feat(publish-flow): XHS adapter + publish_xhs.py CLI; map draft to cli.py args

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 11: Replace root SKILL.md with multi-platform router

**Goal:** Replace the upstream root `SKILL.md` so its name reflects our project and so the "publish/create" intent routes through `publish-flow` instead of directly through `xhs-publish`.

**Files:**
- Modify (full overwrite): `SKILL.md` at repo root

- [ ] **Step 1: Back up the upstream root SKILL.md**

```bash
cp SKILL.md SKILL.md.upstream.bak
```
(This file is .gitignored after this task — see Step 3.)

- [ ] **Step 2: Overwrite root SKILL.md**

`SKILL.md`:

```markdown
---
name: auto-publish
description: |
  多平台内容发布编排器。当用户要求"发布 / 发帖 / 创作 / 帮我发一篇 / 写一篇关于X的小红书"时触发；
  也覆盖小红书登录、搜索、评论、点赞、收藏等附加操作（路由到 fork 原有子技能）。
  v1.0 只支持小红书图文，未来扩展 X / 微信公众号 / 抖音 / B站。
version: 1.0.0
metadata:
  openclaw:
    requires:
      bins:
        - python3
        - uv
    emoji: "📣"
    homepage: https://github.com/gaoxiaowei2117/auto-publish
    os:
      - darwin
      - linux
---

# auto-publish

你是「多平台发布编排助手」。本仓库 fork 自 `autoclaw-cc/xiaohongshu-skills`，
在其上加了一层 `publish-flow` 子技能负责创作与确认；其余子技能保持上游原样。

## 🔒 技能边界

**所有小红书底层操作只能通过本项目的 `python scripts/cli.py` 完成，**
**不得使用任何外部项目（xiaohongshu-mcp、其他 MCP 服务器、Go 工具）。**
**完成任务后直接报告结果，等待用户下一步。**

## 输入判断（按优先级路由）

1. **创作 / 发布**（"发一篇 / 写一篇关于X / 帮我发 / 发布"） → 执行 **publish-flow** 子技能
2. **认证**（"登录 / 检查登录 / 切换账号"） → 执行 **xhs-auth** 子技能
3. **搜索发现**（"搜索 / 看详情 / 浏览首页 / 看用户"） → 执行 **xhs-explore** 子技能
4. **社交互动**（"评论 / 回复 / 点赞 / 收藏"） → 执行 **xhs-interact** 子技能
5. **复合运营**（"竞品分析 / 热点 / 批量互动"） → 执行 **xhs-content-ops** 子技能

子技能各自的 `SKILL.md` 在 `skills/<name>/SKILL.md`。

## 全局约束

- 所有操作前先 `python scripts/cli.py check-login`，未登录则路由 xhs-auth
- 发布前必须经过 publish-flow 的整稿确认（除非用户传 `--auto`）
- 文件路径一律绝对路径
- CLI 的 stdout 是 JSON，按结构呈现给用户
- 操作频率请克制，避免触发风控

## v1.0 范围（与 v1.1+ 区分）

- ✅ 小红书图文发布、单账号、用户提供图片
- ❌ 视频发布 / AI 生图 / 多账号 / 定时 / 跨平台 → v1.1+，按上方路由也尚未接入
```

- [ ] **Step 3: Gitignore the backup**

Append to `.gitignore`:

```
SKILL.md.upstream.bak
```

- [ ] **Step 4: Commit**

```bash
git add SKILL.md .gitignore
git commit -m "$(cat <<'EOF'
feat(skill): replace root SKILL.md to route publish through publish-flow

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 12: Write `publish-flow/SKILL.md`

**Goal:** The instructions Claude follows when the root SKILL.md routes a "publish" intent to publish-flow. It describes the B-flow loop, the flags, and the concrete commands to run.

**Files:**
- Create: `skills/publish-flow/SKILL.md`

- [ ] **Step 1: Write the SKILL.md**

`skills/publish-flow/SKILL.md`:

````markdown
---
name: publish-flow
description: |
  小红书图文创作 + 确认 + 发布编排。当根 SKILL.md 路由"发布/创作/写一篇"意图进来时执行。
  生成内容、亮稿给用户确认、发布或存草稿。v1.0 仅图文，仅小红书。
---

# publish-flow

## 输入

用户的自然语言里需要至少提取：

| 项 | 必需 | 默认 |
|----|------|------|
| `topic` | ✅ | 无 |
| `images-dir` | ✅ | 无 |
| `persona` | ❌ | `skills/publish-flow/persona/default.yaml` |
| 模式 | ❌ | B 流程（亮稿确认） |
| `regen-budget` | ❌ | 2（硬校验内部重试） |

模式 flag：
- `--draft`：生成完不发，调 `fill-publish` 把表单填进去等用户在浏览器里手动发
- `--auto`：跳过亮稿确认，直接发
- 都不传：B 流程，亮稿给用户，等用户说"发"或反馈修改

## 流程（B 流程默认）

### 步骤 1：前置检查

```bash
uv run python scripts/cli.py check-login
```
若 exit code = 1，告诉用户"先扫码登录"，引导执行：

```bash
uv run python scripts/cli.py get-qrcode --output /tmp/xhs-qr.png
# 在终端里告诉用户去看 /tmp/xhs-qr.png 扫码
uv run python scripts/cli.py wait-login
```

### 步骤 2：生成草稿

```bash
uv run python skills/publish-flow/scripts/generate.py \
  --topic "<用户提供>" \
  --images-dir "<用户提供，绝对路径>" \
  [--persona /abs/path/to/persona.yaml] \
  [--regen-budget 2]
```

stdout 是一个 JSON：
```json
{
  "ok": true,
  "draft": { "title": "...", "body": "...", "tags": [...],
             "cover_pick": "...", "image_order": [...] },
  "violations": [],
  "history": [...],
  "images_dir": "/abs/path/to/imgs",
  "image_files": ["a.jpg", "b.jpg", ...],
  "truncated_to_9": false
}
```

把 `draft` 完整渲染给用户：

> 📝 标题：…
> 📄 正文：…（如太长可 preview 前 200 字 + 可展开）
> 🏷️  话题：…
> 🖼️  封面：cover_pick，其余按 image_order
>
> ❓ 这样发吗？[发布] [改 X] [重新生成] [存草稿] [取消]

### 步骤 3：用户回应

- **"发"/"OK"/"发布"** → 进步骤 4（发布）
- **"改 X"**（例如"标题太长"、"少 emoji"、"加一个 City walk 话题"） → 把用户的话作为 `--feedback` 重新生成：
  ```bash
  uv run python skills/publish-flow/scripts/generate.py \
    --topic "..." --images-dir "..." \
    --feedback "用户的修改意见原文"
  ```
  回步骤 2 亮稿。
- **"重新生成"** → 同上，但 `--feedback` 为空，让模型自由再来一稿。
- **"存草稿"** → 步骤 4 时加 `--save-as-draft`
- **"取消"** → 中止，不写审计日志的发布字段

最多重生 **5 轮**（用户层面）。超过提示用户"我已经改了 5 次了，要不你直接告诉我标题/正文/话题应该写啥？"

### 步骤 4：发布（或存草稿）

把当前 draft 写到临时 JSON 文件，调：

```bash
uv run python skills/publish-flow/scripts/publish_xhs.py \
  --draft-file /tmp/draft.json \
  --images-dir "<图片目录>" \
  --topic "<原 topic>" \
  [--save-as-draft]
```

stdout JSON：
```json
{ "ok": true, "result": {...}, "audit_log": "/abs/path/to/log.json" }
```

向用户报告：
- 成功：✅ 已发布。审计日志：`<audit_log>`
- 失败：❌ 发布失败：`<error>`。审计日志：`<audit_log>`

## `--auto` 模式

跳过步骤 3 用户确认。生成完直接发。

## 边界情况

- `images-dir` 不存在 → 拒绝，让用户给个真实路径
- 目录里没有图片 → 拒绝
- 目录里 >9 张图 → 用 `truncated_to_9=true` 告诉用户被截断，但仍然继续
- `violations` 非空 → 最终草稿仍未通过硬校验。告知用户具体违规，让用户决定继续发还是手改
- check-login 返回 1 → 必须先跑登录流程，不要尝试直接发

## 不做（v1.0）

- 视频发布 / 视频混排
- AI 生图
- `--account` 多账号
- 定时发布
- 跨平台并发

````

- [ ] **Step 2: Commit**

```bash
git add skills/publish-flow/SKILL.md
git commit -m "$(cat <<'EOF'
feat(publish-flow): SKILL.md describing B-flow generation + confirmation + publish

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 13: Update README

**Goal:** Replace the inherited README with one that explains what `auto-publish` is, how it differs from upstream, and how to set it up.

**Files:**
- Modify (overwrite): `README.md`

- [ ] **Step 1: Overwrite README.md**

`README.md`:

```markdown
# auto-publish

多平台内容发布编排器。基于 [`autoclaw-cc/xiaohongshu-skills`](https://github.com/autoclaw-cc/xiaohongshu-skills) fork，加了一层 AI 创作 + 整稿确认编排。

**v1.0 范围：** 小红书图文，单账号，用户提供图片，模型按你的人设生成标题+正文+话题，整稿确认后发布。

## 与上游的差别

上游 `xiaohongshu-skills` 是"打开浏览器，按参数填表"的执行器；`auto-publish` 在它之上加了"按你的人设生成内容、整稿亮给你看、你拍板才发"的编排层。两者各管一段：

| 层 | 项目 |
|----|------|
| 编排（创作 + 确认） | 本仓库 `skills/publish-flow/` |
| 平台适配 | 本仓库 `skills/publish-flow/platforms/xhs.py` |
| 浏览器执行 | 上游 `scripts/cli.py` + `extension/` |

## 安装

### 前置

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- Chrome 浏览器
- Anthropic API key（环境变量 `ANTHROPIC_API_KEY`）

### 步骤

```bash
git clone https://github.com/gaoxiaowei2117/auto-publish.git
cd auto-publish
uv sync
```

装上游的 Chrome 扩展（这一步无法跳过）：
1. Chrome 地址栏输入 `chrome://extensions/`
2. 右上角开启「开发者模式」
3. 「加载已解压的扩展程序」选择本仓库 `extension/` 目录
4. 确认扩展「XHS Bridge」启用

配置 API key：

```bash
export ANTHROPIC_API_KEY=sk-ant-...
# 或写进 .env / shell profile
```

编辑你的人设：

```bash
$EDITOR skills/publish-flow/persona/default.yaml
```

人设里至少把 1 篇 examples 换成你真实的过往笔记，否则生成质量会显著下降。

## 使用

在 Claude Code 里：

> 帮我发一篇小红书，主题是上海周末复古市集的逛展笔记，图在 ~/Pictures/2026-05-13/shanghai/

Claude 会：
1. 调 `python scripts/cli.py check-login` 检查登录，未登录引导扫码
2. 调 `python skills/publish-flow/scripts/generate.py` 生成草稿
3. 把生成的标题/正文/话题/封面整稿亮给你看
4. 你说"发"/反馈修改/"重新生成"/"存草稿"/"取消"
5. 拍板后调 `python skills/publish-flow/scripts/publish_xhs.py` 发布

flag 也能直接在自然语言里传达，比如「直接发，不要确认」对应 `--auto`，「先存草稿」对应 `--save-as-draft`。

## 项目结构

```
auto-publish/
├── SKILL.md                      # 多平台路由（我们替换）
├── skills/
│   ├── publish-flow/             # 编排层（我们新增）
│   │   ├── SKILL.md
│   │   ├── persona/default.yaml  # ← 编辑这里把人设换成你的
│   │   ├── platforms/xhs.py      # XHS 适配
│   │   └── scripts/
│   │       ├── generate.py       # 生成草稿
│   │       ├── publish_xhs.py    # 发布
│   │       ├── prompt.py / persona.py / llm.py / validate.py / audit.py
│   └── xhs-*                     # 上游原有子技能（认证/搜索/互动 等）
├── scripts/cli.py                # 上游执行层 entry
├── extension/                    # 上游 Chrome 扩展
└── docs/superpowers/             # 设计文档和实施计划
```

## 审计日志

每次发布会写一份 JSON 到 `~/.auto-publish/runs/YYYY-MM-DD-HHMMSS.json`，记录主题、最终草稿、用户选择、发布结果。用于失败复盘 + v1.1 persona auto-distill 的语料库。

## 路线图

- v1.1：MiniMax 生图、多人设、persona auto-distill、多账号、本地草稿
- v1.2：视频发布、定时发布
- v2：X / 微信公众号（架构已预留）

详见 `docs/superpowers/specs/2026-05-13-auto-publish-design.md`。

## License

MIT，与上游一致。
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "$(cat <<'EOF'
docs: rewrite README for auto-publish

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 14: Run full test suite

**Goal:** Verify nothing regressed across the whole repo.

- [ ] **Step 1: Run all tests**

```bash
cd /home/xgao/workspace/auto-publish
uv run pytest -v
```
Expected: all our new tests pass; upstream tests still pass (or skip cleanly).

- [ ] **Step 2: Lint check**

```bash
uv run ruff check skills/publish-flow tests/publish_flow
```
Expected: no lint errors. Fix any reported issues, then re-run.

- [ ] **Step 3: Push so far**

```bash
git push origin main
```

---

## Task 15: Manual end-to-end smoke test

**Goal:** Run a real publish against a real XHS account. This task is **NOT** TDD — it's an integration sanity check that proves v1.0 works.

**Files:** (no edits — manual verification)

- [ ] **Step 1: Set up test materials**

```bash
mkdir -p ~/test-xhs-imgs
# Drop 2-3 real images into this directory.
ls ~/test-xhs-imgs
```

- [ ] **Step 2: Edit persona with at least 1 real example**

Open `skills/publish-flow/persona/default.yaml`, replace the placeholder `examples[0]` with one of your actual past XHS posts (title, body, tags). Save.

- [ ] **Step 3: Verify login works**

```bash
uv run python scripts/cli.py check-login
```
Expected: `{"success": true, ...}` and exit 0. If exit 1, follow the login flow:

```bash
uv run python scripts/cli.py get-qrcode --output /tmp/xhs-qr.png
xdg-open /tmp/xhs-qr.png   # or your platform's equivalent
uv run python scripts/cli.py wait-login
```

- [ ] **Step 4: Dry run — generate only**

```bash
uv run python skills/publish-flow/scripts/generate.py \
  --topic "测试：今天试一下 auto-publish 的发布流程" \
  --images-dir ~/test-xhs-imgs
```
Expected: prints JSON with `"ok": true`, a draft, and `violations: []` (or short list).

- [ ] **Step 5: Fill-publish (draft mode, doesn't post)**

Save the draft from Step 4:

```bash
uv run python skills/publish-flow/scripts/generate.py \
  --topic "..." --images-dir ~/test-xhs-imgs > /tmp/draft-out.json

# Extract the draft node:
uv run python -c "
import json
d = json.load(open('/tmp/draft-out.json'))
json.dump(d['draft'], open('/tmp/draft.json', 'w'), ensure_ascii=False, indent=2)
"

uv run python skills/publish-flow/scripts/publish_xhs.py \
  --draft-file /tmp/draft.json \
  --images-dir ~/test-xhs-imgs \
  --topic "smoke test" \
  --save-as-draft
```
Expected:
- Chrome opens, creator center fills in title/body/tags/images
- Form is NOT submitted (because `--save-as-draft`)
- stdout has `{"ok": true, ...}`
- Audit log written to `~/.auto-publish/runs/`

Manually inspect the form in Chrome: do the fields match the draft?

- [ ] **Step 6: Full publish (real post)**

Only when Step 5 looks right:

```bash
uv run python skills/publish-flow/scripts/publish_xhs.py \
  --draft-file /tmp/draft.json \
  --images-dir ~/test-xhs-imgs \
  --topic "smoke test"
```
Expected:
- Form submits
- stdout has `{"ok": true, "result": {...}}`
- The post is live on XHS within ~30s

Verify on xiaohongshu.com that the post appeared with the expected content.

- [ ] **Step 7: Document any issues found**

Open a GitHub issue or jot down notes for v1.0.1 follow-ups. Common things that may surface:
- Selector drift in the fork (file a PR upstream or patch locally)
- Image upload timeout (increase fork's wait time)
- Tag format quirks (commit a fix in `xhs.py` adapter)

- [ ] **Step 8: Final commit + tag**

If anything needed fixing during this smoke test, commit those fixes. Then tag v1.0:

```bash
git tag -a v1.0.0 -m "auto-publish v1.0: XHS image post with B-flow confirmation"
git push origin main --tags
```

---

## Done condition for v1.0

All checkboxes above ticked, including the live publish in Task 15. Ready to start v1.1 (MiniMax generation, multi-persona, persona auto-distill).
