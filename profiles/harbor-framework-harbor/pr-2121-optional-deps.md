---
type: PR Case Study
title: harbor PR #2121 - make litellm and datasets optional dependencies
description: zsxh1990 在 harbor 提的 litellm/datasets 可选依赖 PR，Vercel + Devin 反馈
pr_number: 2121
pr_url: https://github.com/harbor-framework/harbor/pull/2121
repo: harbor-framework/harbor
author: zsxh1990
status: open
opened_at: 2026-06-28
last_activity: 2026-09-06
tags:
  - pr-case-study
  - open
  - optional-deps
  - vercel-preview
  - devin-reviewed
related:
  - ../index.md
verified_at: "2026-09-06T08:14:11Z"
evidence_urls:
  - https://github.com/harbor-framework/harbor/pull/2121
  - https://api.github.com/repos/harbor-framework/harbor/pulls/2121
  - https://api.github.com/repos/harbor-framework/harbor/pulls/2121/files
  - https://api.github.com/repos/harbor-framework/harbor/issues/2121/comments
  - https://api.github.com/repos/harbor-framework/harbor/pulls/2121/reviews
  - https://api.github.com/repos/harbor-framework/harbor/pulls/2121/commits
confidence: high
rounds:
  - round: 1
    action: open
    delta:
      kind: code_change
      value: "+57 / -23 / 6 files"
      verified_at: "2026-06-28T09:14:50Z"
      evidence_urls:
        - https://github.com/harbor-framework/harbor/pull/2121/files
        - https://github.com/harbor-framework/harbor/pull/2121
        - https://api.github.com/repos/harbor-framework/harbor/pulls/2121/commits
      confidence: high  # PR created_at from GH API; commits at c240a2b2
    response_time_h: 0.1
    maintainer_action: null
    bot_review:
      - "vercel[bot]: 部署预览需 maintainer 授权"
      - "github-actions[bot]: diff viewer"
      - "devin-ai-integration[bot]: 2 findings (待修)"
    timestamp: "2026-06-28T09:14:00Z"
  - round: 2
    action: check_in
    delta:
      kind: no_code_change
      value: null
      verified_at: "2026-07-07T13:16:00Z"
      evidence_urls:
        - https://github.com/harbor-framework/harbor/pull/2121
        - https://api.github.com/repos/harbor-framework/harbor/issues/2121/comments
      confidence: high
    response_time_h: 220
    maintainer_action: null
    bot_review: []
    blocker: "maintainer 未回应"
    resolution: "zsxh1990 第 1 次 friendly check-in: 'CI is all green. Happy to adjust if needed.'"
    timestamp: "2026-07-07T13:16:00Z"
  - round: 3
    action: bump
    delta:
      kind: no_code_change
      value: null
      verified_at: "2026-08-04T03:09:23Z"
      evidence_urls:
        - https://api.github.com/repos/harbor-framework/harbor/issues/2121/comments
      confidence: high
    response_time_h: 673
    maintainer_action: null
    bot_review:
      - "devin-ai-integration[bot]: 8/2 3 new + 8/2 2 new findings"
    blocker: "maintainer 未回应"
    resolution: "zsxh1990 第 2 次 friendly ping: 强调 base install 544MB → 39MB (93% reduction)"
    timestamp: "2026-08-04T03:09:23Z"
  - round: 4
    action: bump
    delta:
      kind: no_code_change
      value: null
      verified_at: "2026-08-16T09:53:03Z"
      evidence_urls:
        - https://api.github.com/repos/harbor-framework/harbor/issues/2121/comments
        - https://api.github.com/repos/harbor-framework/harbor/pulls/2121/reviews
      confidence: medium
    response_time_h: 1005
    maintainer_action: "human review received (findings 一一回应)"
    bot_review:
      - "devin-ai-integration[bot]: 8/10 1 new issue"
    blocker: null
    resolution: "zsxh1990 第 3 次 ping + 逐条回应 reviewer findings（lock file / 其余项已解决）"
    timestamp: "2026-08-16T09:53:03Z"
  - round: 5
    action: decision
    delta:
      kind: no_code_change
      value: "保持 open：CI 全绿，reviewer findings 已回应，等待最终 review"
      verified_at: "2026-09-06T08:14:11Z"
      evidence_urls:
        - https://api.github.com/repos/harbor-framework/harbor/pulls/2121
        - https://api.github.com/repos/harbor-framework/harbor/pulls/2121/reviews
      confidence: high
    response_time_h: 496
    maintainer_action: null
    bot_review:
      - "devin-ai-integration[bot]: 9/3 + 9/5 findings"
      - "codecov-commenter[bot]: 9/6 coverage 提醒"
    blocker: "PR 仍 open，无 maintainer 合并/关闭信号"
    resolution: "GitHub API 复核：state=open, merged=false, updated_at=2026-09-06"
    timestamp: "2026-09-06T08:14:11Z"
close_decision:
  status: keep_open
  reason: "reviewer findings 已回应，CI 全绿，PR 仍 open 无合并信号 → keep open"
  decided_at: "2026-09-06T08:14:11Z"
  actor: zsxh1990
final_status: open
opened_at: "2026-06-28T09:14:00Z"
last_activity: "2026-09-06T08:14:11Z"
next_action: "等 maintainer 最终 review；Devin findings 持续跟进"
---

# harbor PR #2121: feat: make litellm and datasets optional dependencies

> zsxh1990 在 [harbor-framework/harbor#2121](https://github.com/harbor-framework/harbor/pull/2121) 的可选依赖 PR。  
> **状态**：🟢 open（99 天，reviewer findings 已回应，等待最终 review）  
> **核心价值**：建立 harbor 可选依赖模式（litellm/datasets → extras_require）。

---

## PR 内容

**问题**：harbor 默认安装 `litellm`（~150MB）+ `datasets`（~500MB），但很多场景只用其一  
**方案**：
- `pip install harbor` - 最小安装
- `pip install harbor[llm]` - 加 litellm
- `pip install harbor[data]` - 加 datasets
- `pip install harbor[all]` - 全装

**规模**：+57 / -23 / 6 files（小而精）

---

## 反馈时间线

| 时间 | 事件 |
|---|---|
| 2026-06-28 09:14 | PR 创建 + Vercel bot 通知（需 maintainer 授权） |
| 2026-06-28 09:15 | github-actions bot diff viewer 链接 |
| 2026-06-28 09:20 | @devin-ai-integration[bot] 自动 review，2 findings |
| 2026-07-07 13:16 | zsxh1990 第 1 次 friendly check-in |
| 2026-08-04 03:09 | zsxh1990 第 2 次 friendly ping（强调 93% 体积缩减） |
| 2026-08-02 → 08-10 | Devin 多轮 findings（3+2+1） |
| 2026-08-16 09:53 | zsxh1990 第 3 次 ping + **逐条回应 reviewer findings** |
| 2026-09-03 / 09-05 | Devin 新 findings（PR 仍 open） |
| 2026-09-06 08:14 | codecov-commenter 提醒；GitHub API 复核 state=open |

---

## Devin AI 反馈（待深读）

Devin 找到 2 个 potential issues（细节未读，zsxh1990 未提 amend）。  
**特征**：Devin 是 harbor 官方接入的 AI review = **他们的反馈大概率需要处理**。

---

## 下一步

- ✅ Vercel 预览等授权（maintainer 操作）
- ✅ reviewer findings 已于 8/16 逐条回应
- ⚠️ Devin findings 持续新增（9/3、9/5）
- 🟡 maintainer 尚未合并/关闭，PR 仍 open

---

## 关联文档

- [harbor 仓 Profile](../index.md)
- [OKF bundle 根入口](../index.md)