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
