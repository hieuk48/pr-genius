"""Tests for the PR comment renderers (issue #111 — `comment_format` input).

`post_comment.py` lives outside the package on purpose: the composite action
installs the published `prgenius-core` wheel from PyPI rather than this
checkout, so the comment renderer has to stay a self-contained stdlib script.
These tests therefore load it by path.

Two contracts are frozen here:

1. **verbose is byte-identical to the pre-`comment_format` output** — that is
   the regression boundary. `render_comment` must not drift.
2. **compact is far shorter** — it is the whole point of the input.

Unknown `comment_format` values fall back to `compact` and raise a warning
rather than hard-failing: every failure path in the comment step of
`action.yml` is already advisory-only (`::warning::`, never a failed job), and
a typo must never be the reason a 200-line comment gets posted.
"""

from __future__ import annotations

import importlib.util
import os
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
POST_COMMENT_PATH = (
    REPO_ROOT / ".github" / "actions" / "pr-genius-check" / "post_comment.py"
)


def _load_post_comment():
    spec = importlib.util.spec_from_file_location(
        "prgenius_post_comment_under_test", POST_COMMENT_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pc = _load_post_comment()


def _sample_result() -> dict:
    """A result shaped like a real high-risk analyze output."""
    return {
        "tier": "high_risk",
        "repo": "org/repo",
        "summary": "\U0001F534 1 blocking issue(s) — fix before submitting",
        "signals": {
            "negative": [
                {
                    "description": "Missing tests",
                    "severity": "high",
                    "fix_action": "Add tests",
                    "source_pr": "org/repo#12",
                },
                {
                    "description": "Big PR",
                    "severity": "medium",
                    "fix_action": "Split it",
                },
            ],
            "positive": [
                {"description": "Good commit message"},
                {"description": "Focused change"},
            ],
            "neutral": [{"description": "Touches 3 files"}],
        },
        "checklist": [
            {"hint": "Add tests", "priority": "P1", "done": False},
            {"hint": "Update docs", "priority": "P2", "done": True},
        ],
        "anti_patterns_detail": [
            {
                "key": "mega-pr",
                "description": "Mega PR",
                "severity": "high",
                "fix_action": "Split into smaller PRs",
            },
        ],
        "anti_patterns_hit": [],
        "repo_context": {"star_count": 4521, "repo_size": "L", "merge_rate": 0.42},
    }


def _large_sample_result() -> dict:
    """A high-volume result at the scale issue #111 complains about.

    Mirrors a high-risk analysis with many signals/checklist/anti-patterns —
    the shape that used to render to >100 lines of Markdown.
    """
    return {
        "tier": "high_risk",
        "repo": "org/repo",
        "summary": "\U0001F534 3 blocking issue(s) — fix before submitting",
        "signals": {
            "negative": [
                {
                    "description": f"Negative signal {i} describing a concrete problem",
                    "severity": ("critical", "high", "medium", "low")[i % 4],
                    "fix_action": f"Concrete fix action number {i}",
                    "source_pr": f"org/repo#{100 + i}",
                }
                for i in range(12)
            ],
            "positive": [{"description": f"Positive signal {i}"} for i in range(6)],
            "neutral": [{"description": f"Neutral note {i}"} for i in range(4)],
        },
        "checklist": [
            {"hint": f"Checklist hint {i} with enough words to look real",
             "priority": "P1" if i % 3 == 0 else "P2", "done": i % 2 == 0}
            for i in range(14)
        ],
        "anti_patterns_detail": [
            {"key": f"pattern-{i}", "description": f"Anti-pattern {i} description",
             "severity": ("high", "medium", "low")[i % 3],
             "fix_action": f"Remediation step {i}"}
            for i in range(8)
        ],
        "anti_patterns_hit": [],
        "repo_context": {"star_count": 4521, "repo_size": "L", "merge_rate": 0.42},
    }


# Frozen golden: exact `render_comment` output for `_sample_result()` as
# produced BEFORE the `comment_format` input existed. Any edit to the verbose
# renderer must fail `test_verbose_is_byte_identical_to_pre_change_output`.
GOLDEN_VERBOSE = (
    "## \U0001F9EC PR Genius Analysis\n"
    "\n"
    "**\U0001F534 Risk tier: High Risk** (2 positive / 2 negative)\n"
    "*org/repo*\n"
    "\n"
    "### ⚠️ Issues\n"
    "\n"
    "- ⚠️ **Missing tests**\n"
    "  - → Add tests\n"
    "  - (case: org/repo#12)\n"
    "- \U0001F4CB **Big PR**\n"
    "  - → Split it\n"
    "\n"
    "### ✅ Positive\n"
    "\n"
    "- Good commit message\n"
    "- Focused change\n"
    "\n"
    "### ℹ️ Info\n"
    "\n"
    "- Touches 3 files\n"
    "\n"
    "### \U0001F4CB Checklist\n"
    "\n"
    "- [☐] **[P1]** Add tests\n"
    "- [✅] **[P2]** Update docs\n"
    "\n"
    "### \U0001F50E Anti-Patterns\n"
    "\n"
    "- ⚠️ **Mega PR**\n"
    "  - → Split into smaller PRs\n"
    "\n"
    "*Repo: 4,521⭐ | L | merge rate 42%*\n"
    "\n"
    "*This is a non-blocking advisory from PR Genius. It does not request "
    "changes or block merge.*\n"
    "\n"
    "<!-- pr-genius:report -->"
)


class TestVerboseRendererRegression(unittest.TestCase):
    """`comment_format: verbose` is the old behavior, byte for byte."""

    def test_verbose_is_byte_identical_to_pre_change_output(self):
        out = pc.render_comment(_sample_result())
        self.assertEqual(out, GOLDEN_VERBOSE)

    def test_verbose_keeps_marker_and_disclaimer(self):
        out = pc.render_comment(_sample_result())
        self.assertTrue(out.endswith(pc.MARKER))
        self.assertIn("non-blocking advisory", out)

    def test_verbose_empty_result_still_renders_marker(self):
        out = pc.render_comment({})
        self.assertIn(pc.MARKER, out)
        self.assertIn("Risk tier:", out)


class TestCompactRenderer(unittest.TestCase):
    """`comment_format: compact` — a short bullet summary (issue #111)."""

    def test_compact_is_far_shorter_than_verbose(self):
        result = _sample_result()
        verbose = pc.render_comment(result)
        compact = pc.render_comment_compact(
            result, "https://github.com/org/repo/actions/runs/1"
        )
        v_lines = verbose.count("\n") + 1
        c_lines = compact.count("\n") + 1
        self.assertLessEqual(c_lines, 8, "compact must stay under 8 lines")
        self.assertLess(
            c_lines * 3,
            v_lines,
            "compact must be at least 3x fewer lines than verbose",
        )

    def test_compact_dramatically_smaller_at_issue_scale(self):
        """At the scale issue #111 describes (~160-line high_risk comments),
        compact must be roughly an order of magnitude smaller."""
        result = _large_sample_result()
        verbose = pc.render_comment(result)
        compact = pc.render_comment_compact(
            result, "https://github.com/org/repo/actions/runs/1"
        )
        v_bytes = len(verbose.encode("utf-8"))
        c_bytes = len(compact.encode("utf-8"))
        v_lines = verbose.count("\n") + 1
        c_lines = compact.count("\n") + 1
        self.assertGreater(v_lines, 80, "fixture must be large enough to matter")
        self.assertLessEqual(c_lines, 8)
        self.assertGreater(
            v_bytes / c_bytes,
            8.0,
            f"expected >8x byte reduction, got {v_bytes}/{c_bytes}",
        )
        self.assertGreater(
            v_lines / c_lines,
            10.0,
            f"expected >10x line reduction, got {v_lines}/{c_lines}",
        )

    def test_compact_reports_tier_counts_summary_and_run_link(self):
        out = pc.render_comment_compact(
            _sample_result(), "https://github.com/org/repo/actions/runs/99"
        )
        self.assertIn("\U0001F534", out)          # high_risk icon
        self.assertIn("High Risk", out)
        self.assertIn("1 anti-pattern", out)
        self.assertIn("2 issues", out)
        self.assertIn("2 checklist items", out)
        self.assertIn("2 positive signals", out)
        self.assertIn("1 blocking issue(s)", out)  # analyzer one-line summary
        self.assertIn("https://github.com/org/repo/actions/runs/99", out)
        self.assertTrue(out.endswith(pc.MARKER))

    def test_compact_without_run_url_still_renders(self):
        out = pc.render_comment_compact(_sample_result(), "")
        self.assertIn("action run", out)
        self.assertNotIn("]()", out)
        self.assertTrue(out.endswith(pc.MARKER))

    def test_compact_falls_back_to_anti_patterns_hit_keys(self):
        result = {
            "tier": "medium_risk",
            "signals": {"negative": [], "positive": [], "neutral": []},
            "checklist": [],
            "anti_patterns_hit": ["mega-pr", "drive-by-refactor"],
            "anti_patterns_detail": [],
        }
        out = pc.render_comment_compact(result)
        self.assertIn("2 anti-patterns", out)

    def test_compact_omits_summary_line_when_absent(self):
        result = {"tier": "low_risk", "signals": {}, "checklist": []}
        out = pc.render_comment_compact(result)
        self.assertIn("Low Risk", out)
        self.assertIn("no findings", out)
        self.assertNotIn("blocking issue", out)
        # one bullet only — no summary row when the analyzer gave none
        self.assertEqual(out.count("\n- "), 0)
        self.assertTrue(out.startswith("- "))

    def test_compact_drops_zero_counts(self):
        result = {
            "tier": "medium_risk",
            "signals": {"negative": [{"description": "One thing"}], "positive": [], "neutral": []},
            "checklist": [],
            "anti_patterns_detail": [],
            "anti_patterns_hit": [],
        }
        out = pc.render_comment_compact(result)
        self.assertIn("1 issue", out)
        self.assertNotIn("0 anti-pattern", out)
        self.assertNotIn("0 checklist", out)
        self.assertNotIn("0 positive", out)

    def test_compact_keeps_marker_for_comment_upsert(self):
        out = pc.render_comment_compact(_sample_result())
        self.assertIn(pc.MARKER, out)


class TestResolveCommentFormat(unittest.TestCase):
    """Input normalization: unknown values fall back to compact + warn."""

    def test_default_is_compact(self):
        self.assertEqual(pc.resolve_comment_format(None), ("compact", False))
        self.assertEqual(pc.resolve_comment_format(""), ("compact", False))

    def test_known_values_are_accepted(self):
        self.assertEqual(pc.resolve_comment_format("compact"), ("compact", False))
        self.assertEqual(pc.resolve_comment_format("verbose"), ("verbose", False))

    def test_values_are_normalized(self):
        self.assertEqual(pc.resolve_comment_format(" Compact "), ("compact", False))
        self.assertEqual(pc.resolve_comment_format("VERBOSE"), ("verbose", False))

    def test_unknown_value_falls_back_to_compact_and_warns(self):
        fmt, warned = pc.resolve_comment_format("banana")
        self.assertEqual(fmt, "compact")
        self.assertTrue(warned)

    def test_near_miss_also_falls_back(self):
        fmt, warned = pc.resolve_comment_format("compakt")
        self.assertEqual(fmt, "compact")
        self.assertTrue(warned)


class TestResolveRunUrl(unittest.TestCase):
    def test_cli_value_wins(self):
        self.assertEqual(
            pc.resolve_run_url("https://example/run/1"), "https://example/run/1"
        )

    def test_env_fallback_builds_actions_run_url(self):
        saved = {
            k: os.environ.get(k)
            for k in ("GITHUB_SERVER_URL", "GITHUB_REPOSITORY", "GITHUB_RUN_ID")
        }
        try:
            os.environ["GITHUB_SERVER_URL"] = "https://github.com"
            os.environ["GITHUB_REPOSITORY"] = "o/r"
            os.environ["GITHUB_RUN_ID"] = "42"
            self.assertEqual(
                pc.resolve_run_url(), "https://github.com/o/r/actions/runs/42"
            )
        finally:
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_missing_env_returns_empty(self):
        saved = {
            k: os.environ.get(k)
            for k in ("GITHUB_SERVER_URL", "GITHUB_REPOSITORY", "GITHUB_RUN_ID")
        }
        try:
            for key in saved:
                os.environ.pop(key, None)
            self.assertEqual(pc.resolve_run_url(), "")
        finally:
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


class TestMainDispatch(unittest.TestCase):
    """`main()` routes to the right renderer and never hard-fails."""

    def _run_main(self, comment_format, argv_extra=()):
        import io
        import json
        import sys as _sys

        posted = {}
        original = pc.post_or_update
        pc.post_or_update = lambda repo, number, token, body, marker=pc.MARKER: posted.update(
            body=body
        )
        old_argv, old_stdin = _sys.argv, _sys.stdin
        old_stdout, old_stderr = _sys.stdout, _sys.stderr
        out, err = io.StringIO(), io.StringIO()
        try:
            _sys.argv = [
                "post_comment.py",
                "--repo",
                "org/repo",
                "--pr-number",
                "1",
                "--token",
                "t",
                "--comment-format",
                comment_format,
                *argv_extra,
            ]
            _sys.stdin = io.StringIO(json.dumps(_sample_result()))
            _sys.stdout, _sys.stderr = out, err
            code = pc.main()
        finally:
            _sys.argv, _sys.stdin = old_argv, old_stdin
            _sys.stdout, _sys.stderr = old_stdout, old_stderr
            pc.post_or_update = original
        return code, posted.get("body", ""), out.getvalue(), err.getvalue()

    def test_verbose_dispatch_renders_full_body(self):
        code, body, stdout, _ = self._run_main("verbose")
        self.assertEqual(code, 0)
        self.assertEqual(body, GOLDEN_VERBOSE)
        self.assertNotIn("::warning::", stdout)

    def test_compact_dispatch_renders_short_body(self):
        code, body, stdout, _ = self._run_main(
            "compact", ("--run-url", "https://github.com/o/r/actions/runs/7")
        )
        self.assertEqual(code, 0)
        self.assertNotEqual(body, GOLDEN_VERBOSE)
        self.assertIn("https://github.com/o/r/actions/runs/7", body)
        self.assertLessEqual(body.count("\n") + 1, 8)
        self.assertNotIn("::warning::", stdout)

    def test_unknown_format_warns_and_posts_compact(self):
        code, body, stdout, _ = self._run_main("banana")
        self.assertEqual(code, 0, "must not fail the workflow on a bad input")
        self.assertLessEqual(body.count("\n") + 1, 8)
        self.assertIn("1 anti-pattern", body)
        self.assertIn("::warning::", stdout)
        self.assertIn("banana", stdout)


class TestDefaultIsLocked(unittest.TestCase):
    """The compact default must be pinned in every place that can flip it.

    `resolve_comment_format(None)` being compact is not enough: the argparse
    default and `action.yml`'s `inputs.comment_format.default` are what real
    runs actually see. If either drifts back to verbose, existing users get
    100-line comments again and nothing would catch it.
    """

    def test_action_yml_declares_compact_default(self):
        import re

        text = (Path(__file__).resolve().parents[2] / "action.yml").read_text(
            encoding="utf-8"
        )
        # action.yml's inputs block: `  comment_format:` at 2 spaces, its keys
        # at 4. The input ends at the next 2-space key.
        block = re.search(
            r"^  comment_format:\n(?P<body>(?:^    .+\n|^      .+\n)+)",
            text,
            re.M,
        )
        self.assertIsNotNone(block, "action.yml must declare a comment_format input")
        default = re.search(r"^    default:\s*(.+)$", block.group("body"), re.M)
        self.assertIsNotNone(default, "comment_format must declare a default")
        self.assertEqual(default.group(1).strip().strip("'\""), "compact")

    def test_argparse_default_is_compact_when_flag_omitted(self):
        import io
        import json
        import sys as _sys

        posted = {}
        original = pc.post_or_update
        pc.post_or_update = lambda repo, number, token, body, marker=pc.MARKER: posted.update(
            body=body
        )
        old_argv, old_stdin = _sys.argv, _sys.stdin
        old_stdout, old_stderr = _sys.stdout, _sys.stderr
        out, err = io.StringIO(), io.StringIO()
        try:
            # NOTE: no --comment-format at all — this is the real default path
            _sys.argv = [
                "post_comment.py",
                "--repo",
                "org/repo",
                "--pr-number",
                "1",
                "--token",
                "t",
            ]
            _sys.stdin = io.StringIO(json.dumps(_sample_result()))
            _sys.stdout, _sys.stderr = out, err
            code = pc.main()
        finally:
            _sys.argv, _sys.stdin = old_argv, old_stdin
            _sys.stdout, _sys.stderr = old_stdout, old_stderr
            pc.post_or_update = original

        body = posted.get("body", "")
        self.assertEqual(code, 0)
        self.assertNotEqual(body, GOLDEN_VERBOSE, "default must not be verbose")
        self.assertLessEqual(body.count("\n") + 1, 8, "default output is compact-sized")
        self.assertIn(pc.MARKER, body)


if __name__ == "__main__":
    unittest.main()
