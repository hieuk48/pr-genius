"""Tests for knowledge-root resolution and doctor's honesty about the corpus.

issue #116: the wheel used to ship code only, so a fresh `pip install
prgenius-core` resolved to `repo_root_source == "none"` and every corpus count
was 0. These tests pin the two halves of the fix: the package-local corpus is
a first-class resolution candidate, and the reference-only corpus that is
deliberately left out of the wheel is reported as *not installed* rather than
as a bare 0.
"""

from pathlib import Path

from prgenius.utils import (
    _is_kb_root,
    _iter_kb_candidates,
    _npm_bundle_roots,
    find_reference_bundles,
)


def _make_kb_root(path: Path, with_success: bool = False) -> Path:
    (path / "anti-patterns").mkdir(parents=True, exist_ok=True)
    (path / "profiles").mkdir(parents=True, exist_ok=True)
    if with_success:
        (path / "success-patterns").mkdir(parents=True, exist_ok=True)
    return path


class TestIsKbRoot:
    def test_requires_both_markers(self, tmp_path):
        (tmp_path / "anti-patterns").mkdir()
        assert not _is_kb_root(tmp_path)
        (tmp_path / "profiles").mkdir()
        assert _is_kb_root(tmp_path)

    def test_success_patterns_is_not_a_marker(self, tmp_path):
        # The wheel ships the decision subset without it (issue #116); a root
        # without it must still resolve, or a wheel install is amnesiac again.
        _make_kb_root(tmp_path)
        assert _is_kb_root(tmp_path)

    def test_rejects_plain_dir(self, tmp_path):
        assert not _is_kb_root(tmp_path)
        assert not _is_kb_root(tmp_path / "nope")


class TestKbCandidates:
    def test_package_data_candidate(self, tmp_path):
        """A wheel install: <pkg>/data carries the corpus and must resolve."""
        here = tmp_path / "site-packages" / "prgenius" / "utils.py"
        here.parent.mkdir(parents=True)
        here.write_text("# stub\n")
        _make_kb_root(here.parent / "data")

        found = _iter_kb_candidates(here=here, cwd=tmp_path)
        assert found, "bundled corpus must be a resolution candidate"
        path, source = found[0]
        assert source == "package-data"
        assert path == here.parent / "data"

    def test_full_checkout_wins_over_package_data(self, tmp_path):
        """A real checkout above the package outranks the bundled snapshot."""
        checkout = _make_kb_root(tmp_path / "pr-genius")
        here = checkout / "prgenius" / "src" / "prgenius" / "utils.py"
        here.parent.mkdir(parents=True)
        here.write_text("# stub\n")
        _make_kb_root(here.parent / "data")

        path, source = _iter_kb_candidates(here=here, cwd=tmp_path)[0]
        assert source == "found"
        assert path == checkout

    def test_npm_bundle_is_found_from_cwd(self, tmp_path):
        """DSH installs keep the corpus in node_modules/pr-genius (issue #116)."""
        here = tmp_path / "site-packages" / "prgenius" / "utils.py"
        here.parent.mkdir(parents=True)
        here.write_text("# stub\n")
        npm_root = _make_kb_root(tmp_path / "project" / "node_modules" / "pr-genius")
        cwd = tmp_path / "project"

        bundles = _npm_bundle_roots(here=here, cwd=cwd)
        assert npm_root in bundles
        sources = {src for _p, src in _iter_kb_candidates(here=here, cwd=cwd)}
        assert "npm-node_modules" in sources

    def test_no_markers_no_candidates(self, tmp_path):
        here = tmp_path / "site-packages" / "prgenius" / "utils.py"
        here.parent.mkdir(parents=True)
        here.write_text("# stub\n")
        assert _iter_kb_candidates(here=here, cwd=tmp_path) == []


class TestFindReferenceBundles:
    def test_names_the_bundle_that_has_success_patterns(self, tmp_path):
        here = tmp_path / "site-packages" / "prgenius" / "utils.py"
        here.parent.mkdir(parents=True)
        here.write_text("# stub\n")
        _make_kb_root(here.parent / "data")  # decision subset only
        fuller = _make_kb_root(tmp_path / "project" / "node_modules" / "pr-genius", with_success=True)

        bundles = find_reference_bundles(here=here, cwd=tmp_path / "project")
        assert fuller in bundles
        assert here.parent / "data" not in bundles, "decision-only bundle is not a reference bundle"


class TestDoctorCorpusHonesty:
    def test_reports_success_patterns_not_installed(self, tmp_path, capsys):
        from prgenius.doctor import format_doctor_text, run_doctor

        root = _make_kb_root(tmp_path)
        report = run_doctor(root)
        kb = report["knowledge_base"]
        assert kb["readable"] is True
        assert kb["success_patterns"] == 0
        assert kb["success_patterns_installed"] is False
        assert any("success-patterns: not installed" in w for w in report["warnings"])

        text = format_doctor_text(report)
        assert "success-patterns: not installed" in text

    def test_installed_corpus_is_not_flagged_missing(self, tmp_path):
        from prgenius.doctor import run_doctor

        root = _make_kb_root(tmp_path, with_success=True)
        (root / "success-patterns" / "sample.md").write_text(
            "---\ntitle: sample\n---\nbody\n", encoding="utf-8"
        )
        report = run_doctor(root)
        kb = report["knowledge_base"]
        assert kb["success_patterns_installed"] is True
        assert not any("success-patterns: not installed" in w for w in report["warnings"])
