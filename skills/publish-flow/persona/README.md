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
