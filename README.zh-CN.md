---
type: Knowledge Bundle
title: PR Genius — 提交前改进顾问
description: 大型开源项目 PR 知识库 + 提交前改进顾问，Agent 可读结构化数据
version: 2.1.5
created: 2026-07-01
updated: 2026-07-22
author: zsxh1990
---

# PR Genius — 知道什么 PR 会被关的顾问

> **550+ 真实案例，帮你找到合并概率最大的提 PR 路径。**

[English](README.md) | 中文

---

## 与 PR-Agent / CodeRabbit 的区别

pr-genius 是**纯规则的提交前顾问**：无 LLM、无 API key、分析过程零网络调用。
`analyze` / `coach` / `triage` / `contributor` / `maintainer` 只读本仓库的本地知识库
（仓画像、anti-patterns、case studies），不会把你的代码发到任何地方。
（会访问 GitHub API 的命令是
`status` / `auto-ping` / `auto-rebase` / `update-issue` / `harvest` —— 它们读写的是
PR *元数据*，不用模型分析代码。）

PR-Agent（[qodo-ai/pr-agent](https://github.com/qodo-ai/pr-agent)）是
**AI 代码审查 agent**：需要 LLM API key，在*已经打开的* PR 上执行
`/review`、`/improve`、`/describe` 等命令。CodeRabbit、Greptile 是同类商业工具
—— 具体能力以它们的官网为准。

**pr-genius 不读你的 diff 正文。** `analyze_pr` / `coach_pr` 只接收 title、body、
repo、labels 和可选的 `diff_stat` 摘要（`git diff --stat` 的输出）。PR 大小判定
只来自该摘要的行数/文件数（没有 `diff_stat` 时退化为标题关键词），diff 正文
（hunks）从不解析。想要可复现、可审计、不上云的提交前建议 → 用 pr-genius；
想要对已打开 PR 的 diff 给自然语言评论 → 用 PR-Agent（或同类工具）。

| 使用场景 | PR-Agent / CodeRabbit（LLM 审查 bot） | pr-genius |
|---|---|---|
| "我该不该向 org/repo 提这个 PR？" | 不干这个 —— 它们作用于已打开的 PR | ✅ `analyze` / `coach` |
| "审查这个已打开 PR 的 diff hunks" | ✅ 这是它们的本职 | ❌ 从不分析 diff 正文 |
| "我有个停滞的出向 PR，该怎么办？" | 不覆盖 —— 见它们的文档 | ✅ `status` / `status_prs` |
| "我要 LLM 自然语言审查" | ✅（需要 LLM API key） | ❌ 无 LLM、无 API key |
| "合规环境禁止调用 LLM API" | 需要 LLM API key | ✅ 分析只读本地文件 |

---

## 🛡️ 为什么用 pr-genius

**pr-genius 不是"会写 PR 的 AI"，而是"知道什么 PR 会被关的顾问"。**

| 能力 | 大模型直接提 PR | 爬虫 Agent | pr-genius |
|------|----------------|-----------|-----------|
| 知识来源 | 训练数据 | 实时爬取 | 550+ 结构化 case studies |
| 仓库理解 | 通用知识 | stars/issues | 17 字段 agent_guidelines |
| 失败模式 | 不知道 | 不知道 | 68 anti-patterns |
| 维护者偏好 | 猜 | 看最近 PR | 结构化 policy |
| 合并概率 | 无法估算 | 无法估算 | 基于仓库合并率 |

**真实教训（只有被关过才知道）：**
- MisakaNet 不接受"破坏性 README 重写"（#491, #496）
- huggingface 要"内部处理"tokenizers 版本（#47434）
- encode/httpx 不接受外部贡献者（restricted interactions）
- Glama badge 是 awesome-mcp-servers 的必须项（#10393）

## 🚀 Quick Start

```bash
pip install prgenius-core

# 分析 PR
python3 -m prgenius analyze "feat: add feature" --repo org/repo --body "Fixes #123"

# Coach (pass/fail)
python3 -m prgenius coach "feat: add feature" --repo org/repo

# Triage (policy check)
python3 -m prgenius triage "docs: typo" --repo org/repo --diff-stat "docs/faq.md | 3 ++-"
```

## 🤖 MCP 配置

```json
{
  "mcpServers": {
    "pr-genius": {
      "command": "python",
      "args": ["-m", "prgenius", "mcp", "serve"]
    }
  }
}
```

### 14 个 MCP Tools

| Tool | 用途 |
|------|------|
| `analyze_pr` | 合并概率 + 优化路径 + 三档风险 |
| `coach_pr` | go/no-go 决策（pass/fail） |
| `triage_pr` | 维护者政策检查（9 条规则） |
| `get_repo_profile` | 仓库画像（17 字段） |
| `list_open_prs` | 本地 open case-study 记录（非实时 GitHub PR） |
| `get_case_study` | PR 案例详情 |
| `search_patterns` | 反模式/成功模式搜索 |
| `schema_info` | OKF schema 版本 |
| `status_prs` | 出向 PR 状态心跳（9 状态分类） |
| `profile_writeback_suggestions` | 画像回写建议（dry-run） |
| `maintainer_view` | 维护者侧决策（5 action） |
| `contributor_view` | 贡献者就绪决策（5 action） |
| `review_queue` | 优先级 review 队列 |
| `prgenius_doctor` | 安装/数据/MCP 自检 |

## 📊 数据规模

| 维度 | 数量 |
|------|------|
| Repo profiles | 58 |
| Case studies | 50+ |
| Anti-patterns | 68 |
| Coach accuracy | 87% (257 cases) |
| 已覆盖仓库 | 35+ |

## 📖 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md)

## 引用

```bibtex
@misc{pr-genius-2026,
  title  = {PR Genius — Evidence-backed PR Contribution Advisor},
  author = {zsxh1990},
  year   = {2026},
  url    = {https://github.com/zsxh1990/pr-genius}
}
```
