---
type: PR Case Study
title: fastmcp PR #282 - testWithOllama() for local LLM testing
description: zsxh1990 在 fastmcp 提的 Ollama 测试工具 PR，首次外部贡献等待 CI
pr_number: 282
pr_url: https://github.com/punkpeye/fastmcp/pull/282
repo: punkpeye/fastmcp
author: zsxh1990
status: closed-not-merged
opened_at: 2026-06-28
closed_at: 2026-07-24
last_activity: 2026-07-24
tags:
  - pr-case-study
  - closed
  - mcp
  - ollama
  - first-time-contributor
  - lesson:split-pr
related:
  - ../index.md
verified_at: "2026-07-05T04:12:46Z"
evidence_urls:
  - https://github.com/punkpeye/fastmcp/pull/282
  - https://api.github.com/repos/punkpeye/fastmcp/pulls/282
  - https://api.github.com/repos/punkpeye/fastmcp/pulls/282/files
  - https://api.github.com/repos/punkpeye/fastmcp/issues/282/comments
  - https://api.github.com/repos/punkpeye/fastmcp/pulls/282/reviews
  - https://api.github.com/repos/punkpeye/fastmcp/pulls/282/commits
confidence: high
rounds:
  - round: 1
    action: open
    delta:
      kind: code_change
      value: "+271 / -16 / 1 file"
      verified_at: "2026-06-28T08:13:56Z"
      evidence_urls:
        - https://github.com/punkpeye/fastmcp/pull/282/files
        - https://github.com/punkpeye/fastmcp/pull/282
        - https://api.github.com/repos/punkpeye/fastmcp/pulls/282/commits
      confidence: high  # PR created_at from GH API; commits at 2606984d
    response_time_h: null  # 首次贡献，CI 未跑
    maintainer_action: null
    bot_review: []
    blocker: "CI 未跑（首次贡献需 maintainer 授权）"
    timestamp: "2026-06-28T08:13:00Z"
  - round: 2
    action: amend
    delta:
      kind: no_code_change
      value: "格式调整"
      verified_at: "2026-06-28T09:39:00Z"
      evidence_urls:
        - https://github.com/punkpeye/fastmcp/pull/282
        - https://api.github.com/repos/punkpeye/fastmcp/pulls/282/files
      confidence: low  # round-level timestamp from case body (not GH API cross-ref)
      verified_at: "2026-06-28T09:39:00Z"
      evidence_urls:
        - https://github.com/punkpeye/fastmcp/pull/282
        - https://api.github.com/repos/punkpeye/fastmcp/pulls/282/files
      confidence: low  # round-level timestamp from case body (not GH API cross-ref)
    response_time_h: 1.5
    maintainer_action: null
    bot_review: []
    blocker: "Prettier formatting issue"
    resolution: "Fixed prettier formatting"
    timestamp: "2026-06-28T09:39:00Z"
  - round: 3
    action: decision
    delta:
      kind: no_code_change
      value: "PR 已关闭（未合并），无代码变更"
      verified_at: "2026-07-24T09:33:50Z"
      evidence_urls:
        - https://github.com/punkpeye/fastmcp/pull/282
        - https://api.github.com/repos/punkpeye/fastmcp/pulls/282
      confidence: high
    response_time_h: 0
    maintainer_action: "maintainer closed the PR"
    bot_review: []
    blocker: null
    resolution: "GitHub API 复核：state=closed, merged=false"
    timestamp: "2026-07-24T09:33:50Z"
close_decision:
  status: close
  reason: "PR 已由维护者关闭（未合并），GitHub API 复核确认"
  decided_at: "2026-07-24T09:33:50Z"
  actor: zsxh1990
final_status: closed-not-merged
opened_at: "2026-06-28T08:13:00Z"
last_activity: "2026-07-24T09:33:50Z"
next_action: "已结案（2026-07-24 维护者关闭，未合并）"
---

# fastmcp PR #282: feat: add testWithOllama() for local LLM testing

> zsxh1990 在 [punkpeye/fastmcp#282](https://github.com/punkpeye/fastmcp/pull/282) 的 Ollama 测试 PR。  
> **状态**：⚫ closed（closed-not-merged，2026-07-24）  
> **特殊**：首次外部贡献，等待 maintainer 授权 CI。

---

## PR 内容

**问题**：MCP server 测试需要真实 LLM，但用 OpenAI/Anthropic 太贵  
**方案**：`testWithOllama()` helper - 自动起本地 Ollama + 跑 prompt  
**规模**：+271 / -16 / 1 file

---

## 关键反馈

- 2026-06-28 09:39 zsxh1990 自报："Fixed the Prettier formatting issue. CI may need maintainer approval for first-time contributors."

**含义**：GitHub 对首次贡献者会阻止 CI 自动跑，需要 maintainer 点 "Approve and run"。

---

## 下一步

- ⚠️ 等 punkpeye 授权 CI
- ⚠️ 等真实 review
- 风险：fastmcp 后续可能加 Ollama 测试标准 → 我们的实现要主动兼容

---

## 关联文档

- [fastmcp 仓 Profile](../index.md)
- [OKF bundle 根入口](../index.md)

## Related Anti-Patterns

- `punkpeye-fastmcp-282-too-large`
- `punkpeye-awesome-mcp-devtools-248-pending`
