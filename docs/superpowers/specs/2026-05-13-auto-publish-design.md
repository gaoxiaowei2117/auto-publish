# auto-publish 设计文档

- **状态**：草案，待 review
- **日期**：2026-05-13
- **作者**：gaoxiaowei2117 + Claude（brainstorming）
- **目标版本**：v1.0

---

## 1. 项目定位

`auto-publish` 是一个**多平台内容发布编排器**。用户给一个主题（可能附带素材），工具：

1. 用模型按用户的人设生成平台原生的标题 / 正文 / 话题 / 封面建议
2. 把整稿亮给用户确认（默认）或直接发布（可选）
3. 调用平台执行层把图文交付出去

**v1.0 只覆盖小红书图文发布**，但架构从一开始就为多平台扩展预留。

### 用户场景

- 主要用户：作者本人 + 少数朋友/团队成员（每人在自己电脑跑）
- 不是 SaaS，不做注册/账户/权限/计费
- 不是矩阵号工具，是"个人创作者效率工具"

### 核心差异化

我们的差异化**不在**"打开浏览器填表点发布"——那是商品化的脏活，外包给开源社区。

我们的差异化**在**：
- 内容生成（持有用户人设，输出贴近用户口吻的稿子）
- 整稿确认流程（默认 B 流程：一次性出整稿、用户拍板才发）
- 跨平台编排（一份主题，未来按各平台特性生成不同版本）
- 多模态集成（v1.1 起接 MiniMax 生图）

---

## 2. 三层架构

```
┌─────────────────────────────────────────────────────────────┐
│  编排层 — auto-publish skill                                │
│  - 意图理解、人设加载、模型生成、B-流程确认                │
│  - --draft / --auto / --gen-image / --persona / --account   │
│  - 平台无关。决定"发什么"。                                 │
└─────────────────────────────────────────────────────────────┘
                          │ 路由
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ 适配层:XHS   │ │ 适配层:X (v2)│ │ 适配层:WeChat│
│ (v1.0)       │ │              │ │ (v2)         │
│ 通用草稿     │ │              │ │              │
│ → 平台参数   │ │              │ │              │
└──────────────┘ └──────────────┘ └──────────────┘
        │
        ▼
┌────────────────────────────────────────┐
│ 执行层 — fork 自 xiaohongshu-skills    │
│ python scripts/cli.py publish ...      │
│ + Chrome 扩展                          │
└────────────────────────────────────────┘
```

**分层规则**：

- **编排层是模型 + Markdown + 少量 Python**。所有 AI 价值都集中在这里。
- **适配层是几十行 Python**。每个平台一份，负责把"通用草稿"翻译成执行层吃的参数。
- **执行层是 fork 的代码**。我们尽量不动，必要时打补丁；新平台到来时，引入新的执行层即可。

---

## 3. Fork 策略与仓库结构

### 3.1 Fork 形态

**Hard fork 整个 `autoclaw-cc/xiaohongshu-skills` 仓库**到 `gaoxiaowei2117/auto-publish`。

理由：
- 它的 `SKILL.md` / `scripts/cli.py` / `extension/` 是绑死的整体，硬拆破坏内部约束
- 保留 `upstream` remote，未来上游更新可拉合并
- 单 `git clone` 即可分发给朋友，安装路径与原项目一致

### 3.2 改造后目录

```
auto-publish/                                ← fork 自 xiaohongshu-skills
├── SKILL.md                                 ← 🔄 替换为多平台路由 + 创作意图
├── README.md                                ← 🔄 重写
├── CLAUDE.md                                ← 🔄 添加项目规范
├── pyproject.toml                           ← ➕ 加入 anthropic, pyyaml, pillow 等依赖
├── uv.lock
│
├── skills/
│   ├── publish-flow/                        ← ➕ 编排核心（v1.0 新增）
│   │   ├── SKILL.md                         ←   创作+确认+发布流程
│   │   ├── persona/
│   │   │   ├── default.yaml                 ←   用户的人设配置
│   │   │   └── README.md                    ←   字段说明
│   │   ├── platforms/
│   │   │   └── xhs.py                       ←   适配层：通用草稿 → xhs CLI 参数
│   │   └── scripts/
│   │       ├── orchestrate.py               ←   整个流程的 entry point
│   │       ├── generate.py                  ←   调模型生成内容
│   │       ├── validate.py                  ←   硬校验（字数、禁用词、emoji 数）
│   │       └── audit.py                     ←   写审计日志
│   │
│   ├── xhs-auth/                            ←   原封不动（来自 fork）
│   ├── xhs-publish/                         ←   原封不动（执行层）
│   ├── xhs-explore/                         ←   保留，v1 不路由进去
│   ├── xhs-interact/                        ←   保留，v1 不路由进去
│   └── xhs-content-ops/                     ←   保留，v1 不路由进去
│
├── scripts/cli.py                           ← 不动（执行层 entry）
├── extension/                               ← 不动（Chrome 扩展）
├── tests/                                   ← 不动（原项目测试），新加 publish-flow 测试
└── docs/superpowers/specs/                  ← ➕ 设计文档
```

「🔄」替换，「➕」新增，其余原状。

### 3.3 根 SKILL.md 新路由

```
意图判断（按优先级）：
1. 「创作 / 发布 / 写一篇关于X / 帮我发」     → publish-flow（编排层）
2. 「登录 / 检查登录 / 切换账号」              → xhs-auth（fork 原有）
3. 「搜索 / 看详情 / 看推荐」                  → xhs-explore（fork 原有）
4. 「评论 / 点赞 / 收藏」                      → xhs-interact（fork 原有）
5. 「复合运营」                                → xhs-content-ops（fork 原有）
```

关键差异：用户说"发一篇 XX"时不再直接走 xhs-publish，而是先进 publish-flow 做生成 + 确认，确认后才调 `xhs-publish` 的 CLI 完成发布。

### 3.4 Upstream 跟踪

```bash
git remote add upstream https://github.com/autoclaw-cc/xiaohongshu-skills.git
git fetch upstream
git merge upstream/main             # 或 cherry-pick
```

我们的改动集中在「🔄/➕」标记的文件，merge upstream 大概率无冲突。

### 3.5 分发给朋友

```bash
git clone https://github.com/gaoxiaowei2117/auto-publish.git
cd auto-publish
uv sync
# 安装 Chrome 扩展（README 写步骤）
# 配置 ANTHROPIC_API_KEY（v1.0）、MINIMAX_API_KEY（v1.1）
# 编辑 skills/publish-flow/persona/default.yaml
```

---

## 4. v1.0 范围

### 4.1 In Scope

| 项 | v1.0 |
|----|------|
| 平台 | 小红书 only |
| 内容类型 | 图文（图 + 标题 + 正文 + 话题），不含视频 |
| 图片来源 | 用户提供本地路径（目录或具体文件） |
| 内容生成 | 模型生成标题/正文/话题；从用户图里挑封面 |
| 确认流程 | B 流程（整稿一次确认） |
| Flags | `--draft`（存草稿）、`--auto`（跳过确认）、`--regen-budget N`（默认 5） |
| 账号 | 单账号，复用本机 Chrome 登录态 |
| 触发方式 | Claude Code 对话内自然语言 |

### 4.2 Out of Scope（v1.0 明确不做）

- 视频发布 → v1.2
- AI 生图 → v1.1
- 多账号切换 → v1.1
- 定时发布 → v1.2
- 多平台 → v2
- 搜索/评论/点赞 → 路由到 fork 原有 skill，但不在 publish-flow 编排

---

## 5. 端到端流程

### 5.1 B 流程（默认）

```
用户输入（Claude Code 对话内）：
  「帮我发一篇小红书，主题是上海周末复古市集，图在 ~/Pictures/2026-05-13/shanghai/」
        │
        ▼
[1] 意图解析（根 SKILL.md 路由）
    命中"发布"→ publish-flow
    提取 topic / images path
        │
        ▼
[2] 前置检查（orchestrate.py）
    - 调 cli.py auth check-login，未登录则路由 xhs-auth 引导扫码
    - 校验 images：≥1 张、格式合法、≤9 张（超出截断并告知）
    - 加载 persona/default.yaml
        │
        ▼
[3] 内容生成（generate.py）
    模型输入：persona + topic + image 文件名 + 平台约束
    模型输出 JSON：{ title, body, tags, cover_pick, image_order }
        │
        ▼
[4] 硬校验（validate.py）
    - 标题 ≤20 字、正文 ≤1000 字
    - 禁用词不在 forbid_phrases
    - emoji 个数在 persona 设定范围内
    - cover_pick 与 image_order 在用户提供的图集中
    校验失败：让模型重写，最多 2 次；仍失败将"裸版"亮给用户手改
        │
        ▼
[5] 整稿亮给用户
    📝 标题、📄 正文 preview、🏷️ 话题、🖼️ 封面 + 排序
    选项：[发布] [改 X] [重新生成] [存草稿 = --draft] [取消]
    --regen-budget 默认 5
        │
        ├── 用户选"改/重新生成" → 带 feedback 回 [3]
        ▼ 用户选"发布"（或 --auto 直跳到此）
[6] 适配层（platforms/xhs.py）
    通用草稿 → xhs CLI 参数
    调 `python scripts/cli.py publish image \
        --title "..." --content "..." \
        --tags "..." --images "/abs/p1,/abs/p2,..."`
        │
        ▼
[7] 执行层（fork 自带，不动）
    Chrome 扩展打开创作中心 → 填表 → 上传 → 提交
    返回 JSON：{ ok, url, error? }
        │
        ▼
[8] 回传结果 + 写审计日志
    ✅ 已发布 → https://www.xiaohongshu.com/explore/...
```

### 5.2 Flag 变体

- **`--draft`**：步骤 [6] 改成"存草稿"。若 fork 不支持小红书原生草稿，回退到本地草稿（写本地 yaml + 拷贝图）
- **`--auto`**：跳过 [5]，[4] 完直接进 [6]。日志仍记录草稿，事后可追溯
- **`--regen-budget N`**：限制重新生成轮数，默认 5

### 5.3 错误路径（v1.0 必须处理）

| 触发 | 行为 |
|------|------|
| 未登录 | 自动调 xhs-auth 引导扫码，成功后回主流程 |
| 图片 0 张 | 阻塞，提示必须给图 |
| 图片 >9 张 | 模型按相关性挑前 9 张，告知截断 |
| 标题 / 正文超长 | 模型重写一次，再超则报错 |
| 模型 API 报错 | 重试 1 次，仍失败则保留已生成内容 + 错误信息 |
| 发布接口报错 | 输出错误，**不**自动重试（避免重复发布） |
| 硬校验失败超 2 次 | 把裸版亮给用户手改 |

### 5.4 审计日志

每次发布写一份 JSON 到 `~/.auto-publish/runs/YYYY-MM-DD-HHMM.json`：

```json
{
  "platform": "xhs",
  "topic": "...",
  "persona": "default",
  "iterations": [
    { "draft": {...}, "user_feedback": "改短一点"  },
    ...
  ],
  "final_draft": { "title": "...", "body": "...", "tags": [...] },
  "user_choice": "publish",
  "result": { "ok": true, "url": "https://..." }
}
```

用途：(a) 失败复盘素材；(b) v1.1 persona auto-distill 的语料库。

---

## 6. Persona 配置

### 6.1 存储

```
skills/publish-flow/persona/
├── default.yaml           ← v1.0 唯一一份
└── README.md              ← 字段说明 + 填写示范
```

v1.1 起支持目录下多份 yaml，命令传 `--persona <name>` 切换。

### 6.2 Schema

```yaml
name: default
display_name: "我的小红书"
description: "随手写一句你的人设定位"

voice:
  tone: "亲切但不假，像跟朋友分享周末发现"
  style_keywords: ["真实", "有信息密度", "不卖弄"]
  avoid_tones: ["种草文", "微商口吻", "鸡汤"]

length:
  title_chars: [12, 20]
  body_chars: [300, 800]

emoji:
  usage: light             # none | light | heavy
  preferred: ["🌿", "📷", "✨"]
  avoid: ["💕", "😍"]

hashtags:
  count: [3, 5]
  style: mix               # specific | broad | mix
  preferred_categories: ["生活方式", "城市", "周末"]
  avoid_categories: ["美妆", "穿搭"]

content_rules:
  forbid_phrases: ["种草", "宝藏", "yyds"]
  prefer_first_person: true
  cta_style: subtle        # none | subtle | explicit
  format: "短段落 + 适度分行"

examples:                  # 1-3 篇你认可的过往笔记（最重要）
  - title: "..."
    body: |
      ...
    tags: ["#...", "#..."]
    note: "我为什么觉得这篇风格好"
```

### 6.3 注入 Prompt

`generate.py` 把 YAML 渲染成 system prompt 的固定结构：

```
You are writing a 小红书 post in the user's voice.

VOICE:
  tone: <persona.voice.tone>
  keywords: <persona.voice.style_keywords>
  avoid: <persona.voice.avoid_tones>

LENGTH CONSTRAINTS:
  title: <a>-<b> chars (HARD limit 20)
  body: <a>-<b> chars (HARD limit 1000)

EMOJI: <usage>, preferred=<...>, avoid=<...>
HASHTAGS: count=<a>-<b>, style=<...>
CONTENT RULES:
  forbid_phrases: <...>
  prefer_first_person: <bool>
  cta_style: <...>

EXAMPLES OF THE USER'S OWN STYLE:
  <example 1: title + body + tags>
  <example 2: ...>

TASK:
  topic: <user input>
  available images: <filenames>

Output ONE candidate as JSON:
{ "title": "...", "body": "...", "tags": [...],
  "cover_pick": "<filename>", "image_order": [...] }
```

### 6.4 模型遵循度与硬校验

| 字段类型 | 遵循度 | 兜底 |
|----------|--------|------|
| 数值约束 | 100% | Python 校验 + 重写 |
| 列表约束（禁用词） | 100% | regex 兜底 + 重写 |
| 风格描述 | 70-90% | 用户人工 review |
| examples 迁移 | 60-80% | 用户人工 review |

硬校验最多重试 **2 次**；仍失败则把裸版亮给用户手改。

---

## 7. v1.1+ 路线图

### v1.1（v1.0 之后立刻做）

| 项 | 价值 | 改动 |
|----|------|------|
| MiniMax 生图（可选） | 没图时自动出封面/配图 | 新增 `images/minimax.py` 在生成阶段插一步；`--gen-image` flag |
| 多人设 | 主号/副号/不同栏目 | `persona/` 多 yaml + `--persona name` |
| persona auto-distill | 从用户过往笔记蒸馏 persona | 抓 N 篇主页笔记 → 模型蒸馏 → 输出 yaml 草稿 |
| 多账号 | 主号 + 副号 | fork 已有，加 `--account name` |
| 本地草稿 | "攒一周再发"的用法 | `--draft` 写本地 yaml + 图，`auto-publish drafts list/publish` |

**v1.1 口号**：把 v1.0 的最小可用打磨成"我每周用三四次都顺手"。

### v1.2（加视频与定时）

| 项 | 价值 | 改动 |
|----|------|------|
| 视频发布 | 图文之外的形态 | fork 已支持；适配层加 `publish_video` 分支 |
| 定时发布 | 不在电脑前也能按时发 | (a) 本地 cron 包工具，或 (b) 平台原生定时（待确认 fork 是否暴露） |
| 视频自动选封面 | 模型挑视频帧当封面 | ffmpeg 抽帧 + 多模态打分（可选） |

### v2（多平台扩展）

**第二平台候选锁定 X / 微信公众号**。

| 平台 | 难点 | 执行层候选 |
|------|------|-----------|
| X (Twitter) | API 收费但稳定；280 字硬限 | tweepy / x-api |
| 微信公众号 | 草稿 API 公开，需订阅号/服务号 + 备案；长文 + 富文本 + 封面 + 摘要 | wechatpy / 官方 SDK |
| 抖音 / 头条 | 创作中心 UI 复杂 | 暂无成熟 OSS；自写 Playwright |
| B 站 | 动态简单，专栏复杂 | bili-api-py |
| 微博 | API 限严，多 web 自动化 | weibo-spider 类 |

v2 启动前必做：定义跨平台通用草稿 schema，让一份主题可以衍生出各平台原生表达。建议 v1.0 完成后立即起草此 schema 当 v2 准入条件。

### v2.5（智能调度层；只在真在用了之后做）

- 批量草稿池
- 跨平台改写（XHS 重图 / X 重短文 / 公众号重长文）
- 发布节奏控制（一天 ≤N 篇，避开风控密集时段）
- 效果回流（抓回笔记互动数据，feed 回 persona）

### 明确不做

- ❌ 小红书私信 / 关注 / 拉黑
- ❌ 数据分析 dashboard
- ❌ AI 模特图 / 换装图（v1.1 MiniMax 已覆盖基本生图）
- ❌ 小红书直播 / 商城 / 蒲公英
- ❌ 多用户 SaaS（注册、账户、权限、计费）

### 时间线（粗估）

| 版本 | 预期耗时 | 启动条件 |
|------|---------|---------|
| v1.0 | 2-4 天 | spec 批准后即动手 |
| v1.1 | 1-2 周 | v1.0 自用 5+ 次后 |
| v1.2 | 1-2 周 | 用户提出视频/定时需求后 |
| v2 启动 | 视情况 | XHS 稳定输出 + 第二平台需求明确 |
| v2.5 | 不预估 | v2 真在用之后 |

启动条件都是"**有人在用**"——不被使用就不前进。

---

## 8. 开放问题（待 v1.0 实现阶段确认）

- 图片上限以 9 还是 18 张为准（小红书近期放宽到 18，但 fork 行为待验）
- `--draft` 是否能映射到小红书原生草稿（如果 fork 不支持，回退本地草稿）
- 视频混排（图集内含 1 个视频）在 v1.0 是否值得提早支持
- 模型选型：默认 Claude（用户已有 ANTHROPIC_API_KEY）；是否需要支持其它供应商作为可替换 backend

---

## 9. 决策摘要（brainstorming 阶段已敲定）

| # | 决策 | 取舍 |
|---|------|------|
| 1 | 形态：Skill，不是 MCP | 用户自己 + 朋友用；与已有 wishlist-enroll 范式一致 |
| 2 | 模型介入程度：半自主创作 + 发布 | 用户给主题/素材，模型生成内容 |
| 3 | 确认模式：B 流程（整稿一次确认）+ `--draft` / `--auto` flag | 既能体验 AI 价值又安全 |
| 4 | 图片来源：v1.0 用户提供，v1.1 加 MiniMax 生图 | 先把发布管线打通 |
| 5 | 浏览器自动化：用 fork（`autoclaw-cc/xiaohongshu-skills`）的 Chrome 扩展方案 | 不重造轮子 |
| 6 | Fork 形态：hard fork 整个仓库到 `gaoxiaowei2117/auto-publish` | 保留 upstream 合并能力 |
| 7 | 项目定位：多平台编排器，XHS 是第一个 | 架构从 v1 起为多平台预留 |
| 8 | 第二平台候选：X 或 微信公众号 | 风格与 XHS 差异大，是好的 schema 压力测试 |
| 9 | Persona 用 YAML，单文件 v1.0，多文件 v1.1 | 人写人改、低门槛 |

---

## 10. 下一步

1. 用户 review 本文档，确认或要求修改
2. 通过后转入 `writing-plans` skill，产出 v1.0 的可执行实现计划
3. 按实现计划逐步执行
