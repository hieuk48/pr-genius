"""Smoke tests for prgenius parser + CLI.

These tests deliberately avoid framework/fixture infrastructure
(per ponytail "lazy code ≠ no check" rule). Each test creates
minimal temp inputs and asserts the public API behavior.

Run from repo root:

    cd prgenius
    PYTHONPATH=src python3 -m pytest tests/ -v
    # or
    PYTHONPATH=src python3 tests/test_parser_smoke.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Allow running without pytest installed (stdlib unittest)
try:
    import pytest  # noqa: F401
    HAS_PYTEST = True
except ImportError:
    HAS_PYTEST = False

from prgenius.parser import (
    iter_profiles,
    iter_case_studies,
    load,
    parse_frontmatter,
    profile_get,
    schema_info,
    extract_frontmatter_text,
    FrontmatterTooLarge,
    MAX_FRONTMATTER_BYTES,
)
from prgenius import __version__


class TestVersion(unittest.TestCase):
    def test_version_is_string(self):
        self.assertIsInstance(__version__, str)
        # semver-ish: X.Y.Z
        parts = __version__.split(".")
        self.assertEqual(len(parts), 3, f"version not semver: {__version__}")
        for p in parts:
            self.assertTrue(p.isdigit(), f"non-numeric version part: {p}")


class TestParseFrontmatter(unittest.TestCase):
    def test_basic_yaml(self):
        text = """---
type: Profile
title: Test
tags: [a, b]
---
# Body here
"""
        fm = parse_frontmatter(text)
        self.assertEqual(fm.get("type"), "Profile")
        self.assertEqual(fm.get("title"), "Test")
        # tags normalized to list
        self.assertEqual(fm.get("tags"), ["a", "b"])

    def test_empty_frontmatter(self):
        text = "# Body only, no frontmatter\n"
        fm = parse_frontmatter(text)
        # Should not raise — returns empty dict or default
        self.assertIsInstance(fm, dict)


class TestLoadAndIter(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = Path(self.tmp)
        # Create one profile + one case study
        (self.root / "fake-org-fake-repo").mkdir()
        (self.root / "fake-org-fake-repo" / "index.md").write_text(
            "---\n"
            "type: Repo Profile\n"
            "title: fake-org/fake-repo\n"
            "agent_guidelines:\n"
            "  default_branch: main\n"
            "---\n"
            "# Profile body\n",
            encoding="utf-8",
        )
        (self.root / "fake-org-fake-repo" / "pr-1-test.md").write_text(
            "---\n"
            "type: PR Case Study\n"
            "title: Test case\n"
            "rounds:\n"
            "  - action: open\n"
            "    at: 2026-01-01\n"
            "---\n"
            "# Case body\n",
            encoding="utf-8",
        )

    def test_load_single_file(self):
        profile_md = self.root / "fake-org-fake-repo" / "index.md"
        result = load(profile_md)
        self.assertEqual(result["frontmatter"]["title"], "fake-org/fake-repo")
        self.assertIn("Profile body", result["body"])

    def test_iter_profiles_finds_one(self):
        profiles = list(iter_profiles(self.root))
        self.assertEqual(len(profiles), 1)
        self.assertEqual(profiles[0]["frontmatter"]["type"], "Repo Profile")

    def test_iter_case_studies_finds_one(self):
        cases = list(iter_case_studies(self.root))
        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0]["frontmatter"]["type"], "PR Case Study")

    def test_profile_get_hit(self):
        prof = profile_get(self.root, "fake-org/fake-repo")
        self.assertIsNotNone(prof)
        self.assertEqual(prof["frontmatter"]["title"], "fake-org/fake-repo")

    def test_profile_get_miss(self):
        prof = profile_get(self.root, "nonexistent/repo")
        self.assertIsNone(prof)


class TestSchemaInfo(unittest.TestCase):
    def test_returns_dict(self):
        info = schema_info()
        self.assertIsInstance(info, dict)
        # Should advertise at least one OKF version
        self.assertTrue(any("okf" in str(k).lower() for k in info.keys())
                        or "version" in info
                        or len(info) >= 1)


class TestCliSmoke(unittest.TestCase):
    """Verify the CLI entry point actually launches."""

    def test_cli_version(self):
        repo_root = Path(__file__).resolve().parents[2]  # up to pr-genius/
        env_python = sys.executable
        # Use `python -m prgenius` with PYTHONPATH pointing at src/
        env_add = str(repo_root / "prgenius" / "src")
        import os
        env = os.environ.copy()
        env["PYTHONPATH"] = (
            env_add + os.pathsep + env.get("PYTHONPATH", "")
        )
        result = subprocess.run(
            [env_python, "-m", "prgenius", "--version"],
            capture_output=True, text=True, env=env, timeout=15,
        )
        self.assertEqual(result.returncode, 0,
                         f"stderr={result.stderr!r}")
        self.assertIn(__version__, result.stdout)

    def test_frontmatter_size_limit(self):
        # Audit C.1 #3: a hostile 10 MB frontmatter (YAML bomb) used to be
        # held in memory by `read_text` + the regex. Now bounded at
        # MAX_FRONTMATTER_BYTES, raising FrontmatterTooLarge loudly.
        # 1. just under the limit — works.
        ok = "---\n" + ("x" * (MAX_FRONTMATTER_BYTES - 1)) + "\n---\n"
        out = extract_frontmatter_text(ok)
        self.assertIsNotNone(out)
        self.assertEqual(len(out), MAX_FRONTMATTER_BYTES - 1)
        # 2. just over the limit — raises, not silently truncates.
        big = "---\n" + ("x" * (MAX_FRONTMATTER_BYTES + 1)) + "\n---\n"
        with self.assertRaises(FrontmatterTooLarge) as ctx:
            extract_frontmatter_text(big)
        self.assertIn(str(MAX_FRONTMATTER_BYTES), str(ctx.exception))
        # 3. real frontmatter in this repo is well under the limit
        #    (anti-patterns/ai-generated-content.md is the largest at ~620 B).
        real_text = (Path(__file__).resolve().parents[2] /
                     "anti-patterns" / "ai-generated-content.md").read_text()
        self.assertIsNotNone(extract_frontmatter_text(real_text))

    def test_load_enforces_frontmatter_size_limit(self):
        # Regression: the first cut of this cap only guarded
        # `extract_frontmatter_text()`. `load()` — the public entry point
        # used by evaluator.py and re-exported from `prgenius` — walked
        # `_FM_RE` itself and handed an oversized block straight to
        # `parse_frontmatter`, so the YAML-bomb defense had a hole. Both
        # paths must raise FrontmatterTooLarge.
        tmp = Path(tempfile.mkdtemp())
        bomb = tmp / "bomb.md"
        bomb.write_text(
            "---\n" + ("k: " + "v" * (MAX_FRONTMATTER_BYTES)) + "\n---\nbody\n",
            encoding="utf-8",
        )
        with self.assertRaises(FrontmatterTooLarge):
            load(bomb)

        # under the limit — load() still works end to end
        ok = tmp / "ok.md"
        ok.write_text("---\ntitle: small\n---\nbody text\n", encoding="utf-8")
        result = load(ok)
        self.assertEqual(result["frontmatter"].get("title"), "small")
        self.assertIn("body text", result["body"])

        # the exception message must quote the limit in bytes, and must not
        # call a byte count "chars" (non-ASCII frontmatter makes them differ).
        bomb.write_text(
            "---\n" + ("字" * (MAX_FRONTMATTER_BYTES)) + "\n---\nbody\n",
            encoding="utf-8",
        )
        with self.assertRaises(FrontmatterTooLarge) as ctx:
            load(bomb)
        msg = str(ctx.exception)
        self.assertIn(str(MAX_FRONTMATTER_BYTES), msg)
        self.assertIn("bytes", msg)
        self.assertNotIn("chars, exceeds", msg)


if __name__ == "__main__":
    if HAS_PYTEST:
        sys.exit(pytest.main([__file__, "-v"]))  # noqa
    else:
        unittest.main(verbosity=2)