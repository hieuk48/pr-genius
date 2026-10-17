---
type: Knowledge Bundle
title: PR Genius — 你发出去的那些 PR 的看板
description: 面向 OSS 贡献者的外发贡献项目管理，不是代码审查工具。知道今天该动哪个 PR，以及具体怎么做。
version: 2.2.3
created: 2026-07-01
updated: 2026-10-17
author: zsxh1990
---

# PR Genius

> 你的 GitHub 里，有一些 PR 你已经不再点开了。
>
> 有一个需要 rebase，你一直说等会儿弄。有一个红了四天，没人告诉你。
> 有三个摆了三周没人看。还有一个你干脆绕着走——因为点开它，就意味着确认它死了。

**PR Genius 是这些活儿的看板。** 你往别人的仓库发出去的贡献——没有看板、没有站会、没人在替你记着。

它**不是**代码审查工具。它从不读你的 diff，也不会告诉你「代码没问题」。那是另一类工具的活儿，而且有做得很好的。

它回答的是一个真的在干活的人，周二早上会问的问题：**我发出去的这些东西，今天该动哪个——具体怎么做？**

[English](README.md) | 中文

---

## 为什么会有这个东西

GitHub 记得住那条 PR。

它记不住你为什么关掉了在某个仓库的第三次尝试。什么有效、什么无效。哪个 reviewer 真的会回，哪个评论过一次就消失了。上次把你弹回来的到底是体量、缺 issue 链接，还是语气。

那些东西在你脑子里。会话一结束就没了。

PR Genius 是它们该去的地方。

> 仓库画像记下这个项目**要什么**。
> 案例记下一次贡献**怎么落地或怎么死的**。
> 你自己的状态历史记下**后来怎样**——等了多久、什么变了、有没有回来。

第三样，代码审查工具和大模型都不可能有。它们只在别人的仓库里看见你的 PR 一次。这个看见的是你几个月的组合。

---

## 它知道什么

| 它知道 | 对你意味着 |
|---|---|
| **67 个大项目的实际做派** —— merge 率、review 节奏、什么会被关 | 你不用再猜 `encode/httpx` 想要什么 |
| **真实 PR 为什么被拒** —— 写下来了，带证据 | 你不用再重蹈别人已经赔进去三周的覆辙 |
| **你自己的 PR 后来怎样** —— 每个状态停了多久 | 你在它**正在死的时候**就知道，而不是三周后 |
| **你瞄准的那个仓库的政策** | 正文里一个 `Fixes #N`，仍然是第一条 PR 被弹回来的头号原因 |

给怀疑者看的数字：753 条模式、190 条失败 PR 观察、68 个仓库画像、302 个审过的案例。这些是上面那几句话的**收据**，不是重点——每次发布都会由 `scripts/verify_claims.py` 对着真实目录核一遍。

其中一个语料要说清楚：`success-patterns/` **只作检索/参考，不参与评分**。它是可以翻的背景，不是正反馈系统，从来没有改变过任何一次结论。真正推动风险档位的是那 61 条 anti-patterns。

---

## 九个状态，是九个决定

看板上的数字告诉你「有事」。**状态**告诉你「怎么办」。

| 状态 | 今天对你意味着 |
|---|---|
| `NEEDS_REBASE` | 花二十分钟，这条 PR 就还活着。 |
| `CI_FAILING` | 红了好几天，本来不会有人告诉你。 |
| `STALE_REVIEW` | 有人看过，然后停住了。现在动，或者它就凉了。 |
| `STALE_NO_REVIEW` | 没人看过。等、催、还是体面地撤——但要**决定**。 |
| `CLEAN` | 别管它。这同样是一句值得被告知的话。 |
| `WAITING` | 还在正常响应窗口内。去做别的。 |

看板一半的价值，在于告诉你**今天不该把时间花在什么上**。

---

## 它出现的两个时刻

**在你提之前。** 这个 ready 了吗，还是我准备浪费维护者的注意力？

```bash
python3 -m prgenius coach "fix: timeout in connection pool" \
  --repo encode/httpx --body "Fixes #4821"
```

五个答案，每个都带下一步——`READY_TO_SUBMIT`、`FIX_BEFORE_SUBMIT`、`NEEDS_DISCUSSION`、`IMPROVE_CHANCE`、`ASK_MAINTAINER`。只读、只建议：不评论、不打标签、不关闭、不合并。

**在它已经出去之后。** 这些里面哪个需要我？

```bash
python3 -m prgenius status --author your-handle
```

九个状态、陈旧检测、每条给一个建议——修 CI、rebase、催、等、或者放弃。挂到 cron 上，它就变成你真的会看的那一行。

而且它**会记住**：`STALE_NO_REVIEW for 5d, was NEEDS_REBASE`。不是「有事」，是**怎么走到这一步的**。

---

## 安装

```bash
pip install "prgenius-core[mcp]"     # 引擎 + MCP server
```

装完就能用——决策相关的语料（anti-patterns / profiles / pr-observations / policies）**在 wheel 里**，不用 clone。

```bash
prgenius-core doctor          # 它找到了什么、缺什么，照实说
python3 -m prgenius status --author your-handle
python3 -m prgenius profile get owner/name   # 这个项目到底要什么？
```

> 一条诚实的边界：`success-patterns/`（约 2.7 MB，只作检索参考、不参与评分）**不进 wheel**。
> `doctor` 会说 `success-patterns: not installed`，而不是含混地报 0。想要它，clone 本仓并
> `export PRGENIUS_REPO_ROOT=<clone>`。

---

## 它永远不会做的事

明说，因为这一页的其余部分如果这些含糊，就一文不值：

- **它不会告诉你代码是对的。** 它不读 diff。
- **它不会替你发任何东西**，除非你显式加 `--confirm`。所有会改动状态的命令默认 dry-run。
- **它不外联。** 分析是本地的：无 LLM、无 API key、无网络调用。碰 GitHub 的那几个命令用的是**你自己的** token，而且只读 PR 元数据。没有遥测——见 [docs/ADOPTION_DATA.md](docs/ADOPTION_DATA.md)。
- **它不装。** 没验证过的事实就写没验证。这一页错过，更正在 [CHANGELOG.md](CHANGELOG.md) 里。

---

## 中文文档与延伸

- [README.md](README.md) —— 英文主文档
- [docs/BLOG.md](docs/BLOG.md) —— 上面那段故事的长文版
- [README.zh.md](README.zh.md) —— 知识库中文导航

## Contributing

仓库画像、案例、anti-patterns 都欢迎——见 [CONTRIBUTING.md](CONTRIBUTING.md)。瓶颈是每个上游的整理工时，不是基建：一个仓库画像大约 30 分钟调研，再加上在上游落地一个支撑性 PR 的功夫。

## 引用

```bibtex
@software{pr_genius,
  title  = {PR Genius — the board for your outbound open-source contributions},
  author = {zsxh1990},
  year   = {2026},
  url    = {https://github.com/zsxh1990/pr-genius}
}
```
