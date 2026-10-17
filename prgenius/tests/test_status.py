"""Tests for PR Genius status classifier.

Locks down priority rules to prevent regressions.
"""
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

from prgenius.status import (
    PRStatus, PRInfo, classify_pr, _resolve_stale_days, _compute_transitions,
    enrich_pr_flags, format_transitions, format_step_summary,
    format_step_summary_analyze, format_issue_body, notify_webhook,
    DEFAULT_ABANDON_DAYS,
)


def _make_pr(**overrides) -> PRInfo:
    """Create a PRInfo with sensible defaults."""
    now = datetime.now(timezone.utc)
    defaults = {
        "repo": "org/repo",
        "number": 1,
        "title": "test PR",
        "url": "https://github.com/org/repo/pull/1",
        "author": "testuser",
        "created_at": (now - timedelta(days=5)).isoformat(),
        "updated_at": (now - timedelta(days=1)).isoformat(),
        "mergeable": "MERGEABLE",
        "merge_state": "CLEAN",
        "review_decision": "",
        "checks_status": "",
        "last_commit_at": (now - timedelta(days=3)).isoformat(),
        "last_review_at": "",
        "is_own_repo": False,
    }
    defaults.update(overrides)
    return PRInfo(**defaults)


class TestNeedsRebase(unittest.TestCase):
    """NEEDS_REBASE: CONFLICTING, DIRTY, BEHIND."""

    def test_conflicting(self):
        pr = _make_pr(mergeable="CONFLICTING")
        result = classify_pr(pr)
        self.assertEqual(result.status, PRStatus.NEEDS_REBASE)

    def test_dirty(self):
        pr = _make_pr(merge_state="DIRTY")
        result = classify_pr(pr)
        self.assertEqual(result.status, PRStatus.NEEDS_REBASE)

    def test_behind(self):
        pr = _make_pr(merge_state="BEHIND")
        result = classify_pr(pr)
        self.assertEqual(result.status, PRStatus.NEEDS_REBASE)

    def test_mergeable_clean_not_rebase(self):
        pr = _make_pr(mergeable="MERGEABLE", merge_state="CLEAN")
        result = classify_pr(pr)
        self.assertNotEqual(result.status, PRStatus.NEEDS_REBASE)


class TestCiFailing(unittest.TestCase):
    """CI_FAILING: UNSTABLE, check failure."""

    def test_unstable(self):
        pr = _make_pr(merge_state="UNSTABLE")
        result = classify_pr(pr)
        self.assertEqual(result.status, PRStatus.CI_FAILING)

    def test_check_failure(self):
        pr = _make_pr(checks_status="failure")
        result = classify_pr(pr)
        self.assertEqual(result.status, PRStatus.CI_FAILING)

    def test_pending_not_ci_failing(self):
        """PENDING checks should be BLOCKED, not CI_FAILING."""
        pr = _make_pr(checks_status="pending")
        result = classify_pr(pr)
        self.assertEqual(result.status, PRStatus.BLOCKED)
        self.assertNotEqual(result.status, PRStatus.CI_FAILING)


class TestStaleReviewVsChangesRequested(unittest.TestCase):
    """STALE_REVIEW must not swallow CHANGES_REQUESTED.

    STALE_REVIEW (priority 3): last_commit_at > last_review_at AND stale AND last_review_at != null
    CHANGES_REQUESTED (priority 4): reviewDecision=CHANGES_REQUESTED (and not STALE_REVIEW)
    """

    def test_stale_review_when_commit_after_review(self):
        """Pushed fix but no re-review → STALE_REVIEW."""
        now = datetime.now(timezone.utc)
        pr = _make_pr(
            review_decision="CHANGES_REQUESTED",
            last_commit_at=(now - timedelta(days=20)).isoformat(),
            last_review_at=(now - timedelta(days=25)).isoformat(),
            updated_at=(now - timedelta(days=1)).isoformat(),
        )
        result = classify_pr(pr, stale_days=14)
        self.assertEqual(result.status, PRStatus.STALE_REVIEW)

    def test_changes_requested_when_no_commit_after_review(self):
        """Review requested but no fix pushed → CHANGES_REQUESTED."""
        now = datetime.now(timezone.utc)
        pr = _make_pr(
            review_decision="CHANGES_REQUESTED",
            last_commit_at=(now - timedelta(days=25)).isoformat(),
            last_review_at=(now - timedelta(days=20)).isoformat(),
        )
        result = classify_pr(pr, stale_days=14)
        self.assertEqual(result.status, PRStatus.CHANGES_REQUESTED)

    def test_changes_requested_when_not_stale_yet(self):
        """Review requested, fix pushed, but not yet stale → CHANGES_REQUESTED."""
        now = datetime.now(timezone.utc)
        pr = _make_pr(
            review_decision="CHANGES_REQUESTED",
            last_commit_at=(now - timedelta(days=5)).isoformat(),
            last_review_at=(now - timedelta(days=10)).isoformat(),
        )
        result = classify_pr(pr, stale_days=14)
        self.assertEqual(result.status, PRStatus.CHANGES_REQUESTED)

    def test_changes_requested_when_no_review_at_all(self):
        """CHANGES_REQUESTED but last_review_at is null → CHANGES_REQUESTED."""
        pr = _make_pr(
            review_decision="CHANGES_REQUESTED",
            last_review_at="",
        )
        result = classify_pr(pr, stale_days=14)
        self.assertEqual(result.status, PRStatus.CHANGES_REQUESTED)


class TestCleanNotSwallowedByWaiting(unittest.TestCase):
    """CLEAN must be detected before WAITING (residual fallback)."""

    def test_clean_detected(self):
        pr = _make_pr(
            mergeable="MERGEABLE",
            merge_state="CLEAN",
            review_decision="APPROVED",
        )
        result = classify_pr(pr)
        self.assertEqual(result.status, PRStatus.CLEAN)

    def test_waiting_is_residual(self):
        """When nothing matches, fall through to WAITING."""
        pr = _make_pr(
            mergeable="MERGEABLE",
            merge_state="CLEAN",
            review_decision="",
        )
        result = classify_pr(pr)
        self.assertEqual(result.status, PRStatus.WAITING)


class TestBlocked(unittest.TestCase):
    """BLOCKED: HAS_HOOKS, PENDING checks."""

    def test_has_hooks(self):
        pr = _make_pr(merge_state="HAS_HOOKS")
        result = classify_pr(pr)
        self.assertEqual(result.status, PRStatus.BLOCKED)

    def test_blocked_state(self):
        pr = _make_pr(merge_state="BLOCKED")
        result = classify_pr(pr)
        self.assertEqual(result.status, PRStatus.BLOCKED)

    def test_pending_checks(self):
        pr = _make_pr(checks_status="pending")
        result = classify_pr(pr)
        self.assertEqual(result.status, PRStatus.BLOCKED)


class TestUnknown(unittest.TestCase):
    """UNKNOWN: mergeable=UNKNOWN."""

    def test_unknown_mergeable(self):
        pr = _make_pr(mergeable="UNKNOWN", merge_state="UNKNOWN")
        result = classify_pr(pr)
        self.assertEqual(result.status, PRStatus.UNKNOWN)


class TestStaleNoReview(unittest.TestCase):
    """STALE_NO_REVIEW: no reviews and stale."""

    def test_no_review_stale(self):
        now = datetime.now(timezone.utc)
        pr = _make_pr(
            last_review_at="",
            updated_at=(now - timedelta(days=20)).isoformat(),
        )
        result = classify_pr(pr, stale_days=14)
        self.assertEqual(result.status, PRStatus.STALE_NO_REVIEW)

    def test_no_review_not_stale(self):
        now = datetime.now(timezone.utc)
        pr = _make_pr(
            last_review_at="",
            updated_at=(now - timedelta(days=5)).isoformat(),
        )
        result = classify_pr(pr, stale_days=14)
        self.assertNotEqual(result.status, PRStatus.STALE_NO_REVIEW)


class TestOwnRepo(unittest.TestCase):
    """OWN_REPO PRs are ignored."""

    def test_own_repo_ignored(self):
        pr = _make_pr(is_own_repo=True)
        result = classify_pr(pr)
        self.assertEqual(result.ignored_reason, "OWN_REPO")


class TestPriorityOrder(unittest.TestCase):
    """Verify priority ordering when multiple conditions match."""

    def test_needs_rebase_beats_ci_failing(self):
        """CONFLICTING + UNSTABLE → NEEDS_REBASE (priority 1 > 2)."""
        pr = _make_pr(mergeable="CONFLICTING", merge_state="UNSTABLE")
        result = classify_pr(pr)
        self.assertEqual(result.status, PRStatus.NEEDS_REBASE)

    def test_ci_failing_beats_changes_requested(self):
        """UNSTABLE + CHANGES_REQUESTED → CI_FAILING (priority 2 > 4)."""
        pr = _make_pr(merge_state="UNSTABLE", review_decision="CHANGES_REQUESTED")
        result = classify_pr(pr)
        self.assertEqual(result.status, PRStatus.CI_FAILING)


class TestSnapshotDiscovery(unittest.TestCase):
    """Snapshot file discovery must be strict to avoid picking test fixtures."""

    def _write(self, d, name, content):
        from pathlib import Path
        p = Path(d) / name
        p.write_text(content, encoding="utf-8")
        return p

    def test_strict_date_match_skips_fixtures(self, tmp_path=None):
        import tempfile
        from pathlib import Path
        from prgenius.status import _find_latest_snapshot, _SNAPSHOT_NAME
        with tempfile.TemporaryDirectory() as td:
            # Real snapshot for today
            self._write(td, "2026-08-02.json", '{"prs": []}')
            # Test fixture that shares the date prefix — must NOT be selected
            self._write(td, "2026-08-02-graphql.json", '{"fixture": true}')
            # Older real snapshot
            self._write(td, "2026-08-01.json", '{"prs": []}')
            # Non-date filename — must NOT be selected
            self._write(td, "README.json", '{"readme": true}')

            latest = _find_latest_snapshot(Path(td))
            self.assertIsNotNone(latest)
            self.assertEqual(latest.name, "2026-08-02.json")

    def test_empty_dir_returns_none(self):
        import tempfile
        from pathlib import Path
        from prgenius.status import _find_latest_snapshot
        with tempfile.TemporaryDirectory() as td:
            self.assertIsNone(_find_latest_snapshot(Path(td)))

    def test_snapshot_name_regex_shape(self):
        from prgenius.status import _SNAPSHOT_NAME
        # Strict YYYY-MM-DD.json only
        self.assertIsNotNone(_SNAPSHOT_NAME.match("2026-08-02.json"))
        self.assertIsNone(_SNAPSHOT_NAME.match("2026-08-02-graphql.json"))
        self.assertIsNone(_SNAPSHOT_NAME.match("2026-8-2.json"))  # zero-pad required
        self.assertIsNone(_SNAPSHOT_NAME.match("2026-08-02.JSON"))  # case-sensitive
        self.assertIsNone(_SNAPSHOT_NAME.match("README.json"))


class TestSnapshotSaveTimestamp(unittest.TestCase):
    """Snapshot save should include HHMM so multiple runs per day are kept."""

    def test_save_snapshot_filename_has_hhmm(self):
        import tempfile
        from pathlib import Path
        from prgenius.status import _save_snapshot
        with tempfile.TemporaryDirectory() as td:
            p = _save_snapshot({"prs": []}, Path(td))
            # Pattern: YYYY-MM-DD-HHMM.json
            self.assertRegex(p.name, r"^\d{4}-\d{2}-\d{2}-\d{4}\.json$")

    def test_save_snapshot_distinct_files_across_runs(self):
        """Two save calls produce different filenames (HHMM keeps collisions
        to within 1 minute, which cron never hits)."""
        import tempfile
        from pathlib import Path
        from prgenius.status import _save_snapshot
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            p1 = _save_snapshot({"prs": [], "n": 1}, d)
            # Force a different minute by renaming the first file
            stem = p1.name[:-5]  # strip .json
            new_first = d / (stem[:-4] + "0000.json")  # rewrite HHMM to 0000
            p1.rename(new_first)
            p2 = _save_snapshot({"prs": [], "n": 2}, d)
            self.assertNotEqual(new_first.name, p2.name)


class TestSnapshotRoundTrip(unittest.TestCase):
    """A snapshot written by _save_snapshot must be found by _find_latest_snapshot.

    The writer names files `YYYY-MM-DD-HHMM.json`. A reader that only accepts
    `YYYY-MM-DD.json` writes snapshots it can never read back, and every run
    then diffs against a stale file forever — this test is the regression lock
    for that bug.
    """

    def test_save_then_find(self):
        import tempfile
        from pathlib import Path
        from prgenius.status import _save_snapshot, _find_latest_snapshot
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            written = _save_snapshot({"prs": []}, d)
            found = _find_latest_snapshot(d)
            self.assertIsNotNone(found)
            self.assertEqual(found.name, written.name)

    def test_timestamped_beats_same_day_legacy_name(self):
        import tempfile
        from pathlib import Path
        from prgenius.status import _find_latest_snapshot
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "2026-08-02.json").write_text('{"legacy": true}', encoding="utf-8")
            (d / "2026-08-02-1430.json").write_text('{"newer": true}', encoding="utf-8")
            (d / "2026-08-02-graphql.json").write_text('{"fixture": true}', encoding="utf-8")
            latest = _find_latest_snapshot(d)
            self.assertEqual(latest.name, "2026-08-02-1430.json")

    def test_newer_date_beats_older_timestamped(self):
        import tempfile
        from pathlib import Path
        from prgenius.status import _find_latest_snapshot
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "2026-08-02-2359.json").write_text("{}", encoding="utf-8")
            (d / "2026-08-03.json").write_text("{}", encoding="utf-8")
            self.assertEqual(_find_latest_snapshot(d).name, "2026-08-03.json")

    def test_snapshot_name_accepts_hhmm_rejects_fixtures(self):
        from prgenius.status import _SNAPSHOT_NAME
        self.assertIsNotNone(_SNAPSHOT_NAME.match("2026-10-16-1704.json"))
        self.assertIsNone(_SNAPSHOT_NAME.match("2026-08-02-graphql.json"))
        self.assertIsNone(_SNAPSHOT_NAME.match("2026-08-02-17.json"))  # HHMM is 4 digits
        self.assertIsNone(_SNAPSHOT_NAME.match("2026-08-02-170459.json"))  # not HHMMSS


class TestStaleDaysSourceReporting(unittest.TestCase):
    """check_status must report the actual stale_days_source per run."""

    def _run_with_empty_fetch(self, **kwargs):
        from prgenius import status as st_mod
        original = st_mod.fetch_open_prs
        st_mod.fetch_open_prs = lambda **kw: []
        try:
            from prgenius.status import check_status
            return check_status(save_snapshot=False, **kwargs)
        finally:
            st_mod.fetch_open_prs = original

    def test_cli_source(self):
        r = self._run_with_empty_fetch(author="zsxh1990", stale_days=7, repo_root=None)
        self.assertEqual(r["stale_days_source"], "cli")
        self.assertEqual(r["stale_days"], 7)

    def test_default_source_when_no_profile(self):
        r = self._run_with_empty_fetch(author="zsxh1990", repo_root=None)
        self.assertEqual(r["stale_days_source"], "default")
        self.assertEqual(r["stale_days"], 14)


class TestStaleDaysResolution(unittest.TestCase):
    """Priority: CLI > profile > default 14."""

    def test_cli_overrides_all(self):
        stale, source = _resolve_stale_days("org/repo", cli_stale_days=7)
        self.assertEqual(stale, 7)
        self.assertEqual(source, "cli")

    def test_default_when_no_profile(self):
        stale, source = _resolve_stale_days("org/repo", cli_stale_days=None, repo_root=None)
        self.assertEqual(stale, 14)
        self.assertEqual(source, "default")

    def test_default_when_profile_not_found(self):
        """When repo_root is given but no profile exists, use default."""
        from pathlib import Path
        stale, source = _resolve_stale_days(
            "nonexistent/repo", cli_stale_days=None,
            repo_root=Path(__file__).resolve().parents[2],
        )
        self.assertEqual(stale, 14)
        self.assertEqual(source, "default")


class TestTransitions(unittest.TestCase):
    """Transition tracking: compare current vs previous snapshot."""

    def _make_result(self, prs):
        """Helper to build a minimal result dict."""
        return {"prs": prs}

    def test_no_previous_snapshot(self):
        """First run: no transitions."""
        current = self._make_result([
            {"repo": "org/repo", "number": 1, "title": "PR1", "status": "WAITING"},
        ])
        transitions = _compute_transitions(current, previous=None)
        self.assertEqual(transitions, [])

    def test_unchanged_status(self):
        """Same status: changed=False."""
        pr = {"repo": "org/repo", "number": 1, "title": "PR1", "status": "WAITING"}
        current = self._make_result([pr])
        previous = self._make_result([pr])
        transitions = _compute_transitions(current, previous)
        self.assertEqual(len(transitions), 1)
        self.assertFalse(transitions[0]["changed"])

    def test_changed_status(self):
        """Status changed: changed=True."""
        current = self._make_result([
            {"repo": "org/repo", "number": 1, "title": "PR1", "status": "NEEDS_REBASE"},
        ])
        previous = self._make_result([
            {"repo": "org/repo", "number": 1, "title": "PR1", "status": "WAITING"},
        ])
        transitions = _compute_transitions(current, previous)
        self.assertEqual(len(transitions), 1)
        self.assertTrue(transitions[0]["changed"])
        self.assertEqual(transitions[0]["previous_status"], "WAITING")
        self.assertEqual(transitions[0]["current_status"], "NEEDS_REBASE")

    def test_alert_escalation(self):
        """WAITING → NEEDS_REBASE triggers alert."""
        current = self._make_result([
            {"repo": "org/repo", "number": 1, "title": "PR1", "status": "NEEDS_REBASE"},
        ])
        previous = self._make_result([
            {"repo": "org/repo", "number": 1, "title": "PR1", "status": "WAITING"},
        ])
        transitions = _compute_transitions(current, previous)
        self.assertTrue(transitions[0]["alert"])

    def test_alert_deescalation(self):
        """STALE_REVIEW → CLEAN triggers alert."""
        current = self._make_result([
            {"repo": "org/repo", "number": 1, "title": "PR1", "status": "CLEAN"},
        ])
        previous = self._make_result([
            {"repo": "org/repo", "number": 1, "title": "PR1", "status": "STALE_REVIEW"},
        ])
        transitions = _compute_transitions(current, previous)
        self.assertTrue(transitions[0]["alert"])

    def test_no_alert_for_minor_change(self):
        """WAITING → BLOCKED: no alert (not in alert set)."""
        current = self._make_result([
            {"repo": "org/repo", "number": 1, "title": "PR1", "status": "BLOCKED"},
        ])
        previous = self._make_result([
            {"repo": "org/repo", "number": 1, "title": "PR1", "status": "WAITING"},
        ])
        transitions = _compute_transitions(current, previous)
        self.assertFalse(transitions[0]["alert"])

    def test_disappeared_pr(self):
        """PR in previous but not current → CLOSED_OR_MERGED."""
        current = self._make_result([])
        previous = self._make_result([
            {"repo": "org/repo", "number": 1, "title": "PR1", "status": "WAITING"},
        ])
        transitions = _compute_transitions(current, previous)
        self.assertEqual(len(transitions), 1)
        self.assertEqual(transitions[0]["current_status"], "CLOSED_OR_MERGED")
        self.assertTrue(transitions[0]["changed"])

    def test_new_pr(self):
        """PR in current but not previous → NEW."""
        current = self._make_result([
            {"repo": "org/repo", "number": 1, "title": "PR1", "status": "WAITING"},
        ])
        previous = self._make_result([])
        transitions = _compute_transitions(current, previous)
        self.assertEqual(len(transitions), 1)
        self.assertIsNone(transitions[0]["previous_status"])
        self.assertTrue(transitions[0]["changed"])

    def test_severity_critical(self):
        """WAITING → NEEDS_REBASE has severity=critical."""
        current = self._make_result([
            {"repo": "org/repo", "number": 1, "title": "PR1", "status": "NEEDS_REBASE"},
        ])
        previous = self._make_result([
            {"repo": "org/repo", "number": 1, "title": "PR1", "status": "WAITING"},
        ])
        transitions = _compute_transitions(current, previous)
        self.assertTrue(transitions[0]["alert"])
        self.assertEqual(transitions[0]["severity"], "critical")

    def test_severity_info(self):
        """STALE_REVIEW → CLEAN has severity=info."""
        current = self._make_result([
            {"repo": "org/repo", "number": 1, "title": "PR1", "status": "CLEAN"},
        ])
        previous = self._make_result([
            {"repo": "org/repo", "number": 1, "title": "PR1", "status": "STALE_REVIEW"},
        ])
        transitions = _compute_transitions(current, previous)
        self.assertTrue(transitions[0]["alert"])
        self.assertEqual(transitions[0]["severity"], "info")

    def test_no_severity_for_non_alert(self):
        """WAITING → BLOCKED has no severity (not an alert)."""
        current = self._make_result([
            {"repo": "org/repo", "number": 1, "title": "PR1", "status": "BLOCKED"},
        ])
        previous = self._make_result([
            {"repo": "org/repo", "number": 1, "title": "PR1", "status": "WAITING"},
        ])
        transitions = _compute_transitions(current, previous)
        self.assertFalse(transitions[0]["alert"])
        self.assertNotIn("severity", transitions[0])


class TestEnrichHistory(unittest.TestCase):
    """History fields come from the previous local snapshot only."""

    def _result(self, prs, checked_at="2026-10-16T12:00:00+00:00"):
        return {"checked_at": checked_at, "prs": prs}

    def test_unchanged_inherits_status_since(self):
        from prgenius.status import _enrich_history
        current = self._result([{"repo": "o/r", "number": 1, "title": "P", "status": "STALE_NO_REVIEW"}])
        previous = self._result(
            [{"repo": "o/r", "number": 1, "title": "P", "status": "STALE_NO_REVIEW",
              "status_since": "2026-10-11", "status_before": "NEEDS_REBASE"}],
            checked_at="2026-10-12T12:00:00+00:00",
        )
        _enrich_history(current, previous)
        pr = current["prs"][0]
        self.assertEqual(pr["status_since"], "2026-10-11")
        self.assertEqual(pr["days_in_status"], 5)
        self.assertEqual(pr["status_before"], "NEEDS_REBASE")
        self.assertEqual(pr["previous_status"], "STALE_NO_REVIEW")

    def test_changed_resets_status_since_and_records_status_before(self):
        from prgenius.status import _enrich_history
        current = self._result([{"repo": "o/r", "number": 1, "title": "P", "status": "STALE_NO_REVIEW"}])
        previous = self._result(
            [{"repo": "o/r", "number": 1, "title": "P", "status": "NEEDS_REBASE",
              "status_since": "2026-08-02", "status_before": None}],
            checked_at="2026-10-15T12:00:00+00:00",
        )
        _enrich_history(current, previous)
        pr = current["prs"][0]
        self.assertEqual(pr["status_since"], "2026-10-16")
        self.assertEqual(pr["days_in_status"], 0)
        self.assertEqual(pr["status_before"], "NEEDS_REBASE")

    def test_legacy_previous_without_status_since_uses_its_checked_at(self):
        """A legacy snapshot proves the status held since its own date — and
        nothing earlier."""
        from prgenius.status import _enrich_history
        current = self._result([{"repo": "o/r", "number": 1, "title": "P", "status": "NEEDS_REBASE"}])
        previous = self._result(
            [{"repo": "o/r", "number": 1, "title": "P", "status": "NEEDS_REBASE"}],
            checked_at="2026-08-02T10:09:50+00:00",
        )
        _enrich_history(current, previous)
        pr = current["prs"][0]
        self.assertEqual(pr["status_since"], "2026-08-02")
        self.assertIsNone(pr["status_before"])  # no claim about what came before

    def test_no_previous_snapshot_is_honest(self):
        """First run: no duration, no previous status — a baseline, not a story."""
        from prgenius.status import _enrich_history
        current = self._result([{"repo": "o/r", "number": 1, "title": "P", "status": "NEEDS_REBASE"}])
        _enrich_history(current, None)
        pr = current["prs"][0]
        self.assertEqual(pr["status_since"], "2026-10-16")
        self.assertEqual(pr["days_in_status"], 0)
        self.assertIsNone(pr["previous_status"])
        self.assertIsNone(pr["status_before"])


class TestDescribeHistory(unittest.TestCase):
    """The one-line history a user reads off the status table."""

    def test_transition_narrative(self):
        """'STALE_NO_REVIEW for 5d, was NEEDS_REBASE' — the product sentence."""
        from prgenius.status import describe_history
        text = describe_history({
            "status": "STALE_NO_REVIEW", "status_since": "2026-10-11",
            "days_in_status": 5, "previous_status": "STALE_NO_REVIEW",
            "status_before": "NEEDS_REBASE",
        })
        self.assertEqual(text, "STALE_NO_REVIEW for 5d, was NEEDS_REBASE")

    def test_changed_today(self):
        from prgenius.status import describe_history
        text = describe_history({
            "status": "NEEDS_REBASE", "status_since": "2026-10-16",
            "days_in_status": 0, "previous_status": "WAITING",
            "status_before": "WAITING",
        })
        self.assertEqual(text, "NEEDS_REBASE (changed today), was WAITING")

    def test_unchanged_without_prior_status(self):
        from prgenius.status import describe_history
        text = describe_history({
            "status": "STALE_NO_REVIEW", "status_since": "2026-10-11",
            "days_in_status": 5, "previous_status": "STALE_NO_REVIEW",
            "status_before": None,
        })
        self.assertEqual(text, "STALE_NO_REVIEW for 5d")

    def test_unchanged_since_today_does_not_claim_a_change(self):
        """days_in_status==0 is not proof of a transition — no 'was X' claim."""
        from prgenius.status import describe_history
        text = describe_history({
            "status": "NEEDS_REBASE", "status_since": "2026-10-16",
            "days_in_status": 0, "previous_status": "NEEDS_REBASE",
            "status_before": None,
        })
        self.assertEqual(text, "NEEDS_REBASE since today")
        self.assertNotIn("was", text)

    def test_first_record_on_baseline(self):
        from prgenius.status import describe_history
        text = describe_history(
            {"status": "NEEDS_REBASE", "status_since": "2026-10-16",
             "days_in_status": 0, "previous_status": None},
            baseline=True,
        )
        self.assertEqual(text, "first record")

    def test_unenriched_entry_says_nothing(self):
        from prgenius.status import describe_history
        self.assertEqual(describe_history({"status": "CLEAN"}), "")


class TestCheckStatusRecording(unittest.TestCase):
    """Recording is the default and never invents history."""

    def _pr(self, status="STALE_NO_REVIEW", number=1):
        """Build a PRInfo whose fields make classify_pr() land on `status`."""
        now = datetime.now(timezone.utc)
        fields = {
            "repo": "org/repo", "number": number, "title": f"PR{number}",
            "url": "https://example.invalid/pr", "author": "someone",
            "created_at": (now - timedelta(days=40)).isoformat(),
            "updated_at": (now - timedelta(days=20)).isoformat(),
            "mergeable": "MERGEABLE", "merge_state": "CLEAN", "review_decision": "",
            "checks_status": "success", "last_commit_at": "", "last_review_at": "",
            "is_own_repo": False,
        }
        if status == "NEEDS_REBASE":
            fields["merge_state"] = "BEHIND"
        elif status == "WAITING":
            fields["updated_at"] = (now - timedelta(days=1)).isoformat()
        elif status == "STALE_NO_REVIEW":
            fields["last_review_at"] = ""
            fields["updated_at"] = (now - timedelta(days=20)).isoformat()
        return PRInfo(**fields)

    def _run(self, snapshot_dir, prs=None, **kwargs):
        from prgenius import status as st_mod
        original = st_mod.fetch_open_prs
        st_mod.fetch_open_prs = lambda **kw: prs if prs is not None else [self._pr()]
        try:
            from prgenius.status import check_status
            return check_status(author="someone", snapshot_dir=Path(snapshot_dir), **kwargs)
        finally:
            st_mod.fetch_open_prs = original

    def test_default_writes_snapshot_and_reports_baseline(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            result = self._run(td)
            files = list(Path(td).glob("*.json"))
            self.assertEqual(len(files), 1)
            self.assertTrue(result["transition_summary"]["baseline"])
            self.assertEqual(result["transitions"], [])
            pr = result["prs"][0]
            self.assertEqual(pr["days_in_status"], 0)
            self.assertIsNone(pr["previous_status"])

    def test_second_run_records_transition_from_real_previous(self):
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            self._run(td, prs=[self._pr(status="NEEDS_REBASE")])
            result = self._run(td, prs=[self._pr(status="STALE_NO_REVIEW")])
            pr = result["prs"][0]
            self.assertEqual(pr["status_before"], "NEEDS_REBASE")
            self.assertEqual(pr["previous_status"], "NEEDS_REBASE")
            self.assertEqual(pr["days_in_status"], 0)
            changed = [t for t in result["transitions"] if t["changed"]]
            self.assertEqual(len(changed), 1)
            self.assertEqual(changed[0]["previous_status"], "NEEDS_REBASE")
            self.assertEqual(changed[0]["current_status"], "STALE_NO_REVIEW")
            self.assertFalse(result["transition_summary"]["baseline"])
            # and the transition is persisted for the run after this one
            saved = json.loads((Path(td) / result["transition_summary"]["saved_to"]).read_text())
            self.assertEqual(saved["prs"][0]["status_before"], "NEEDS_REBASE")

    def test_unchanged_state_skips_rewrite(self):
        """Same state, recent snapshot → no new file (polling must not flood)."""
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            self._run(td)
            self._run(td)
            self.assertEqual(len(list(Path(td).glob("*.json"))), 1)

    def test_save_snapshot_false_writes_nothing(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            self._run(td, prs=[self._pr(status="NEEDS_REBASE")])
            result = self._run(td, prs=[self._pr(status="STALE_NO_REVIEW")],
                               save_snapshot=False)
            # read-only run: no new snapshot, but history is still reported
            self.assertEqual(len(list(Path(td).glob("*.json"))), 1)
            self.assertIsNone(result["transition_summary"]["saved_to"])
            self.assertEqual(
                result["transition_summary"]["skipped_write"], "recording disabled"
            )
            pr = result["prs"][0]
            self.assertEqual(pr["status_before"], "NEEDS_REBASE")
            self.assertEqual(pr["previous_status"], "NEEDS_REBASE")

    def test_format_table_first_record_is_honest(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            result = self._run(td)
            from prgenius.status import format_table
            text = format_table(result)
            self.assertIn("first record", text)
            self.assertIn("baseline established", text)
            self.assertNotIn("was NEEDS_REBASE", text)  # no invented prior status

    def test_format_table_shows_history_sentence(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            self._run(td, prs=[self._pr(status="NEEDS_REBASE")])
            result = self._run(td, prs=[self._pr(status="STALE_NO_REVIEW")])
            from prgenius.status import format_table
            text = format_table(result)
            self.assertIn("STALE_NO_REVIEW (changed today), was NEEDS_REBASE", text)

    def test_json_output_stays_parseable_when_recording(self):
        """--format json must remain pure JSON even while a snapshot is written."""
        import io
        import json
        import tempfile
        from contextlib import redirect_stdout
        from prgenius.cli import main
        from prgenius import status as st_mod
        original = st_mod.fetch_open_prs
        st_mod.fetch_open_prs = lambda **kw: [self._pr()]
        try:
            with tempfile.TemporaryDirectory() as td:
                buf = io.StringIO()
                with redirect_stdout(buf):
                    rc = main([
                        "status", "--author", "someone", "--format", "json",
                        "--snapshot-dir", td,
                    ])
                self.assertEqual(rc, 0)
                data = json.loads(buf.getvalue())  # would raise if stdout were dirty
                self.assertTrue(data["transition_summary"]["baseline"])
                self.assertTrue(list(Path(td).glob("*.json")))
        finally:
            st_mod.fetch_open_prs = original


class TestProfileWriteback(unittest.TestCase):
    """Profile writeback suggestions."""

    def test_stale_no_review_suggests_threshold(self):
        """STALE_NO_REVIEW with >21d suggests stale_days_threshold."""
        from prgenius.status import suggest_profile_writeback
        result = {
            "prs": [{
                "repo": "org/repo",
                "number": 1,
                "title": "old PR",
                "status": "STALE_NO_REVIEW",
                "days_since_update": 30,
            }],
        }
        suggestions = suggest_profile_writeback(result, mode="suggest")
        self.assertTrue(any(s["field"] == "stale_days_threshold" for s in suggestions))

    def test_auto_mode_filters_low_confidence(self):
        """auto mode only returns suggestions with confidence >= 0.8."""
        from prgenius.status import suggest_profile_writeback
        result = {
            "prs": [{
                "repo": "org/repo",
                "number": 1,
                "title": "old PR",
                "status": "STALE_NO_REVIEW",
                "days_since_update": 30,
            }],
        }
        suggestions = suggest_profile_writeback(result, mode="auto")
        for s in suggestions:
            self.assertGreaterEqual(s["confidence"], 0.8)

    def test_no_suggestions_for_healthy_prs(self):
        """No writeback suggestions for WAITING/BLOCKED PRs."""
        from prgenius.status import suggest_profile_writeback
        result = {
            "prs": [{
                "repo": "org/repo",
                "number": 1,
                "title": "healthy PR",
                "status": "WAITING",
                "days_since_update": 3,
            }],
        }
        suggestions = suggest_profile_writeback(result, mode="suggest")
        self.assertEqual(len(suggestions), 0)


class TestEnrichPrFlags(unittest.TestCase):
    """Phase 4: enrich_pr_flags adds abandon/ping/rebase flags."""

    def test_stale_no_review_becomes_ping(self):
        now = datetime.now(timezone.utc)
        pr = _make_pr(
            last_review_at="",
            updated_at=(now - timedelta(days=20)).isoformat(),
        )
        result = classify_pr(pr, stale_days=14)
        result = enrich_pr_flags(result)
        self.assertTrue(result.ping_suggested)
        self.assertFalse(result.abandon_candidate)
        self.assertFalse(result.rebase_suggested)

    def test_stale_no_review_becomes_abandon(self):
        now = datetime.now(timezone.utc)
        pr = _make_pr(
            last_review_at="",
            updated_at=(now - timedelta(days=60)).isoformat(),
        )
        result = classify_pr(pr, stale_days=14)
        result = enrich_pr_flags(result)
        self.assertTrue(result.abandon_candidate)
        self.assertFalse(result.ping_suggested)  # abandon overrides ping

    def test_stale_review_becomes_ping(self):
        now = datetime.now(timezone.utc)
        pr = _make_pr(
            review_decision="CHANGES_REQUESTED",
            last_commit_at=(now - timedelta(days=20)).isoformat(),
            last_review_at=(now - timedelta(days=25)).isoformat(),
            updated_at=(now - timedelta(days=1)).isoformat(),
        )
        result = classify_pr(pr, stale_days=14)
        result = enrich_pr_flags(result)
        self.assertTrue(result.ping_suggested)
        self.assertFalse(result.abandon_candidate)

    def test_needs_rebase_becomes_rebase(self):
        pr = _make_pr(mergeable="CONFLICTING")
        result = classify_pr(pr)
        result = enrich_pr_flags(result)
        self.assertTrue(result.rebase_suggested)
        self.assertFalse(result.ping_suggested)
        self.assertFalse(result.abandon_candidate)

    def test_ci_failing_becomes_abandon_after_threshold(self):
        now = datetime.now(timezone.utc)
        pr = _make_pr(
            checks_status="failure",
            updated_at=(now - timedelta(days=60)).isoformat(),
        )
        result = classify_pr(pr, stale_days=14)
        result = enrich_pr_flags(result)
        self.assertTrue(result.abandon_candidate)

    def test_changes_requested_becomes_abandon_after_threshold(self):
        now = datetime.now(timezone.utc)
        pr = _make_pr(
            review_decision="CHANGES_REQUESTED",
            # last_commit < last_review → classify_pr picks CHANGES_REQUESTED (not STALE_REVIEW)
            last_commit_at=(now - timedelta(days=70)).isoformat(),
            last_review_at=(now - timedelta(days=60)).isoformat(),
            updated_at=(now - timedelta(days=60)).isoformat(),
        )
        result = classify_pr(pr, stale_days=14)
        self.assertEqual(result.status, PRStatus.CHANGES_REQUESTED)
        result = enrich_pr_flags(result)
        self.assertTrue(result.abandon_candidate)

    def test_waiting_no_flags(self):
        pr = _make_pr()
        result = classify_pr(pr)
        result = enrich_pr_flags(result)
        self.assertFalse(result.abandon_candidate)
        self.assertFalse(result.ping_suggested)
        self.assertFalse(result.rebase_suggested)

    def test_clean_no_flags(self):
        pr = _make_pr(
            mergeable="MERGEABLE", merge_state="CLEAN", review_decision="APPROVED",
        )
        result = classify_pr(pr)
        result = enrich_pr_flags(result)
        self.assertFalse(result.abandon_candidate)
        self.assertFalse(result.ping_suggested)
        self.assertFalse(result.rebase_suggested)

    def test_custom_abandon_days(self):
        now = datetime.now(timezone.utc)
        pr = _make_pr(
            last_review_at="",
            updated_at=(now - timedelta(days=30)).isoformat(),
        )
        result = classify_pr(pr, stale_days=14)
        # With default threshold (56d), 30d is not abandon
        result_no_abandon = enrich_pr_flags(result)
        self.assertFalse(result_no_abandon.abandon_candidate)
        self.assertTrue(result_no_abandon.ping_suggested)

        # With custom threshold (21d), 30d is abandon
        result_abandon = enrich_pr_flags(result, abandon_days=21)
        self.assertTrue(result_abandon.abandon_candidate)


class TestFormatTransitions(unittest.TestCase):
    """Phase 2: format_transitions with recommended actions."""

    def test_critical_alert_has_action(self):
        transitions = [{
            "repo": "org/repo", "number": 1, "title": "PR",
            "previous_status": "WAITING", "current_status": "CI_FAILING",
            "changed": True, "alert": True, "severity": "critical",
        }]
        text = format_transitions(transitions)
        self.assertIn("🚨", text)
        self.assertIn("investigate CI failure", text)

    def test_info_alert_has_action(self):
        transitions = [{
            "repo": "org/repo", "number": 1, "title": "PR",
            "previous_status": "STALE_REVIEW", "current_status": "CLEAN",
            "changed": True, "alert": True, "severity": "info",
        }]
        text = format_transitions(transitions)
        self.assertIn("ℹ️", text)
        self.assertIn("ready for merge", text)

    def test_non_alert_no_action(self):
        transitions = [{
            "repo": "org/repo", "number": 1, "title": "PR",
            "previous_status": None, "current_status": "WAITING",
            "changed": True, "alert": False,
        }]
        text = format_transitions(transitions)
        self.assertIn("NEW", text)
        self.assertNotIn("🚨", text)

    def test_empty_transitions(self):
        text = format_transitions([])
        self.assertEqual(text, "")


class TestFormatStepSummary(unittest.TestCase):
    """Phase 3: GitHub Step Summary formatting."""

    def _make_result(self):
        return {
            "author": "testuser",
            "checked_at": "2026-08-03T12:00:00+00:00",
            "stale_days": 14,
            "stale_days_source": "default",
            "prs": [
                {"status": "CI_FAILING", "repo": "org/repo", "number": 1,
                 "title": "fix CI", "days_since_update": 3},
            ],
            "ignored": [],
            "summary": {"ci_failing": 1},
            "transitions": [],
            "actions": ["fix CI org/repo#1"],
        }

    def test_contains_header(self):
        text = format_step_summary(self._make_result())
        self.assertIn("PR Genius Status", text)
        self.assertIn("testuser", text)

    def test_contains_pr_table(self):
        text = format_step_summary(self._make_result())
        self.assertIn("org/repo#1", text)
        self.assertIn("CI_FAILING", text)

    def test_contains_actions(self):
        text = format_step_summary(self._make_result())
        self.assertIn("fix CI org/repo#1", text)

    def test_transition_table_with_action(self):
        result = self._make_result()
        result["transitions"] = [{
            "repo": "org/repo", "number": 1, "title": "fix CI",
            "previous_status": "WAITING", "current_status": "CI_FAILING",
            "changed": True, "alert": True, "severity": "critical",
        }]
        text = format_step_summary(result)
        self.assertIn("Transition Alerts", text)
        self.assertIn("investigate CI failure", text)


class TestFormatStepSummaryAnalyze(unittest.TestCase):
    """Phase 3: analyze Step Summary formatting."""

    def test_high_risk_shows_issues(self):
        result = {
            "tier": "high_risk",
            "repo": "org/repo",
            "signals": {
                "negative": [{"description": "Missing tests", "severity": "high", "fix_action": "Add tests"}],
                "positive": [{"description": "Good message"}],
                "neutral": [],
            },
            "checklist": [{"hint": "Add tests", "priority": "P1", "done": False}],
        }
        text = format_step_summary_analyze(result)
        self.assertIn("High Risk", text)
        self.assertIn("Missing tests", text)
        self.assertIn("Add tests", text)
        self.assertIn("Good message", text)


class TestFormatIssueBody(unittest.TestCase):
    """Phase 3: issue body formatting."""

    def test_contains_title_and_table(self):
        result = {
            "author": "testuser",
            "checked_at": "2026-08-03T12:00:00+00:00",
            "summary": {"waiting": 1},
            "prs": [
                {"status": "WAITING", "repo": "org/repo", "number": 1,
                 "title": "feat", "days_since_update": 3},
            ],
            "ignored": [],
            "transitions": [],
            "actions": [],
        }
        text = format_issue_body(result)
        self.assertIn("PR Genius Heartbeat", text)
        self.assertIn("org/repo#1", text)
        self.assertIn("Auto-updated", text)

    def test_alerts_section_present(self):
        result = {
            "author": "testuser",
            "checked_at": "2026-08-03T12:00:00+00:00",
            "summary": {},
            "prs": [],
            "ignored": [],
            "transitions": [{
                "repo": "org/repo", "number": 1, "title": "PR",
                "previous_status": "WAITING", "current_status": "CI_FAILING",
                "changed": True, "alert": True, "severity": "critical",
            }],
            "actions": [],
        }
        text = format_issue_body(result)
        self.assertIn("Needs Attention", text)
        self.assertIn("investigate CI failure", text)


class TestNotifyWebhook(unittest.TestCase):
    """Phase 3: webhook notification (dry-run)."""

    def _make_result(self):
        return {
            "author": "testuser",
            "checked_at": "2026-08-03T12:00:00Z",
            "summary": {"ci_failing": 1},
            "transitions": [{
                "repo": "org/repo", "number": 1, "title": "PR",
                "previous_status": "WAITING", "current_status": "CI_FAILING",
                "changed": True, "alert": True, "severity": "critical",
            }],
            "prs": [],
            "ignored": [],
        }

    def test_feishu_dry_run(self):
        r = notify_webhook(self._make_result(), "https://open.feishu.cn/open-apis/bot/v2/hook/xxx", dry_run=True)
        self.assertTrue(r["ok"])
        self.assertTrue(r["dry_run"])
        self.assertIn("card", r["payload"])

    def test_slack_dry_run(self):
        r = notify_webhook(self._make_result(), "https://hooks.slack.com/services/xxx", dry_run=True)
        self.assertTrue(r["ok"])
        self.assertIn("blocks", r["payload"])

    def test_generic_dry_run(self):
        r = notify_webhook(self._make_result(), "https://example.com/webhook", dry_run=True)
        self.assertTrue(r["ok"])
        self.assertEqual(len(r["payload"]["alerts"]), 1)

    def test_no_alerts_generic(self):
        result = {
            "author": "testuser",
            "checked_at": "2026-08-03T12:00:00Z",
            "summary": {},
            "transitions": [],
            "prs": [],
            "ignored": [],
        }
        r = notify_webhook(result, "https://example.com/hook", dry_run=True)
        self.assertTrue(r["ok"])
        self.assertEqual(len(r["payload"]["alerts"]), 0)


if __name__ == "__main__":
    unittest.main()
