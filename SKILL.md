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
