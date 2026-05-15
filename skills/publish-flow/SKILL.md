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

若 exit code = 1，stdout JSON 里会包含 `qrcode_path` 字段指向二维码 PNG。告诉用户去看那个文件扫码，然后等待登录完成：

```bash
uv run python scripts/cli.py wait-login
```

成功后回到本步骤复查一次 check-login。

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

在调用 publish_xhs.py 之前，把 generate.py 输出中的 `history` 字段写到 /tmp/history.json，便于审计日志记录所有迭代尝试。

把当前 draft 写到临时 JSON 文件，调：

```bash
uv run python skills/publish-flow/scripts/publish_xhs.py \
  --draft-file /tmp/draft.json \
  --images-dir "<图片目录>" \
  --topic "<原 topic>" \
  --history-file /tmp/history.json \
  [--save-as-draft]
```

stdout JSON：
```json
{ "ok": true, "result": {...}, "audit_log": "/abs/path/to/log.json" }
```

向用户报告：
- 成功：✅ 已发布。审计日志：`<audit_log>`
- 失败：❌ 发布失败：`<error>`。审计日志：`<audit_log>`

## `--draft` 模式

跳过最终提交。流程同 B 流程，但步骤 4 的 publish_xhs.py 调用加 `--save-as-draft`：

```bash
uv run python skills/publish-flow/scripts/publish_xhs.py \
  --draft-file /tmp/draft.json \
  --images-dir "<图片目录>" \
  --topic "<原 topic>" \
  --history-file /tmp/history.json \
  --save-as-draft
```

底层调 `scripts/cli.py fill-publish`：把标题/正文/话题/图片填到创作中心表单里，但不点"发布"。用户事后在浏览器里手动确认发出（或丢弃）。返回成功时向用户报告"✅ 已填入草稿，请到创作中心检查并手动发布"。

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
