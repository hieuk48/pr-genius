---
type: PR Case Study
title: sourcebot PR #1383 - detect and surface ctags indexing failures
description: zsxh1990 在 sourcebot 提的 ctags 失败检测 PR，CodeRabbit 已审
pr_number: 1383
pr_url: https://github.com/sourcebot-dev/sourcebot/pull/1383
repo: sourcebot-dev/sourcebot
author: zsxh1990
status: closed-not-merged
opened_at: 2026-06-28
last_activity: 2026-08-02
tags:
  - pr-case-study
  - ctags
  - observability
  - small-pr
related:
  - ../index.md
verified_at: "2026-07-05T04:12:46Z"
evidence_urls:
  - https://github.com/sourcebot-dev/sourcebot/pull/1383
  - https://api.github.com/repos/sourcebot-dev/sourcebot/pulls/1383
  - https://api.github.com/repos/sourcebot-dev/sourcebot/pulls/1383/files
  - https://api.github.com/repos/sourcebot-dev/sourcebot/issues/1383/comments
  - https://api.github.com/repos/sourcebot-dev/sourcebot/pulls/1383/reviews
  - https://api.github.com/repos/sourcebot-dev/sourcebot/pulls/1383/commits
confidence: high
rounds:
  - round: 1
    action: open
    delta:
      kind: code_change
      value: "+60 / -6 / 2 files"  # 极小 PR - OpenClaw §6.1 #2 ideal
      verified_at: "2026-06-28T09:23:26Z"
      evidence_urls:
        - https://github.com/sourcebot-dev/sourcebot/pull/1383/files
        - https://github.com/sourcebot-dev/sourcebot/pull/1383
        - https://api.github.com/repos/sourcebot-dev/sourcebot/pulls/1383/commits
      confidence: high  # PR created_at from GH API; commits at 1ec1917d
    response_time_h: 0.5
    maintainer_action: null
    bot_review:
      - "coderabbit: 1 actionable finding (未修)"
    timestamp: "2026-06-28T09:23:00Z"
  - round: 2
    action: decision
    delta:
      kind: no_code_change
      value: "PR 已关闭（未合并），无代码变更"
      verified_at: "2026-08-02T05:41:08Z"
      evidence_urls:
        - https://github.com/sourcebot-dev/sourcebot/pull/1383
        - https://api.github.com/repos/sourcebot-dev/sourcebot/pulls/1383
      confidence: high
    response_time_h: 0
    maintainer_action: "maintainer closed the PR"
    bot_review: []
    blocker: null
    resolution: "GitHub API 复核：state=closed, merged=false"
    timestamp: "2026-08-02T05:41:08Z"
close_decision:
  status: close
  reason: "PR 已由维护者关闭（未合并），GitHub API 复核确认"
  decided_at: "2026-08-02T05:41:08Z"
  actor: zsxh1990
final_status: closed-not-merged
closed_at: "2026-08-02T05:41:08Z"
opened_at: "2026-06-28T09:23:00Z"
last_activity: "2026-08-02T05:41:08Z"
next_action: "已结案（2026-08-02 维护者关闭，未合并）"
---

# sourcebot PR #1383: feat: detect and surface ctags indexing failures

> zsxh1990 在 [sourcebot-dev/sourcebot#1383](https://github.com/sourcebot-dev/sourcebot/pull/1383) 的 ctags 失败检测 PR。  
> **状态**：⚫ closed（closed-not-merged，2026-08-02）  
> **特征**：极小 PR（+60/-6，2 files）= 理想 size（学 OpenClaw §6.1 #2）。

---

## PR 内容

**问题**：ctags 索引失败时静默（用户看不到，搜索结果空）  
**方案**：捕获 ctags 失败 → 暴露到连接状态 UI  
**规模**：+60 / -6 / 2 files

---

## CodeRabbit 反馈

- 1 actionable finding（细节未读）
- zsxh1990 未提 amend

---

## 关联文档

- [sourcebot 仓 Profile](../index.md)
- [OpenClaw 守则 §6.1 #2 XS/S size](../../../MEMORY.md)