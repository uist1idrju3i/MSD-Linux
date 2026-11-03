from __future__ import annotations

import csv
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
CHECKER = ROOT / ".github/scripts/check-releases.py"
HEADER = [
    "tag",
    "semver",
    "prerelease",
    "commit",
    "update_number",
    "signing_key",
    "release_url",
    "assets_sha256",
    "note",
]
BASE_DATE = "2026-11-01T00:00:00+00:00"
NEXT_DATE = "2026-11-01T00:01:00+00:00"


class ReleaseCheckerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "docs/releases").mkdir(parents=True)
        (self.root / "test.sha256").write_text(
            "a" * 64 + "  sdcard.img.xz\n", encoding="utf-8"
        )
        (self.root / "CHANGELOG.md").write_text(
            "## [0.1.0]\n## [0.1.0-rc.1]\n## [0.2.0]\n", encoding="utf-8"
        )
        self.env = os.environ.copy()
        self.env.update(
            {
                "GIT_AUTHOR_NAME": "Release Test",
                "GIT_AUTHOR_EMAIL": "release-test@example.invalid",
                "GIT_COMMITTER_NAME": "Release Test",
                "GIT_COMMITTER_EMAIL": "release-test@example.invalid",
                "GIT_AUTHOR_DATE": BASE_DATE,
                "GIT_COMMITTER_DATE": BASE_DATE,
            }
        )
        self.git("init", "-q")
        self.commit_one = self.commit("initial")
        self.time_one = self.git("show", "-s", "--format=%ct", self.commit_one)
        self.git("tag", "v0.1.0")
        self.row = self.make_row("v0.1.0", "0.1.0", "false", self.commit_one, self.time_one)
        self.write_rows([self.row])

    def tearDown(self) -> None:
        self.temp.cleanup()

    def git(self, *args: str, env: dict[str, str] | None = None) -> str:
        result = subprocess.run(
            ["git", "-C", str(self.root), *args],
            check=True,
            capture_output=True,
            text=True,
            env=env or self.env,
        )
        return result.stdout.strip()

    def commit(self, text: str, date: str = BASE_DATE) -> str:
        file = self.root / "fixture.txt"
        with file.open("a", encoding="utf-8") as handle:
            handle.write(text + "\n")
        self.git("add", "fixture.txt")
        env = self.env.copy()
        env["GIT_AUTHOR_DATE"] = date
        env["GIT_COMMITTER_DATE"] = date
        self.git("commit", "-q", "-m", text, env=env)
        return self.git("rev-parse", "HEAD")

    def make_row(
        self, tag: str, semver: str, prerelease: str, commit: str, number: str
    ) -> dict[str, str]:
        return {
            "tag": tag,
            "semver": semver,
            "prerelease": prerelease,
            "commit": commit,
            "update_number": number,
            "signing_key": "development",
            "release_url": "https://example.invalid/release",
            "assets_sha256": "test.sha256",
            "note": "test",
        }

    def write_rows(self, rows: list[dict[str, str]], header: list[str] = HEADER) -> None:
        with (self.root / "docs/releases/releases.csv").open(
            "w", newline="", encoding="utf-8"
        ) as handle:
            writer = csv.DictWriter(handle, fieldnames=header)
            writer.writeheader()
            writer.writerows(rows)

    def run_checker(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(CHECKER), "--root", str(self.root), *args],
            check=False,
            capture_output=True,
            text=True,
        )

    def assert_failure_contains(self, phrase: str, *args: str) -> None:
        result = self.run_checker(*args)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(phrase, result.stdout)
        self.assertIn("Summary:", result.stdout)

    def test_valid_ledger(self) -> None:
        result = self.run_checker("--require-tags")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Summary: errors=0 warnings=0", result.stdout)

    def test_decreasing_update_number(self) -> None:
        later = self.commit("second", NEXT_DATE)
        later_time = self.git("show", "-s", "--format=%ct", later)
        self.git("tag", "v0.2.0", later)
        second = self.make_row("v0.2.0", "0.2.0", "false", later, str(int(self.time_one) - 1))
        first = self.make_row("v0.1.0", "0.1.0", "false", self.commit_one, later_time)
        self.write_rows([first, second])
        self.assert_failure_contains("not strictly increasing")

    def test_equal_update_number(self) -> None:
        second = self.make_row("v0.2.0", "0.2.0", "false", self.commit_one, self.time_one)
        self.git("tag", "v0.2.0")
        self.write_rows([self.row, second])
        self.assert_failure_contains("not strictly increasing")

    def test_nineteen_digit_update_number(self) -> None:
        self.row["update_number"] = "1234567890123456789"
        self.write_rows([self.row])
        self.assert_failure_contains("at most 18 digits")

    def test_leading_zero_update_number(self) -> None:
        self.row["update_number"] = "01"
        self.write_rows([self.row])
        self.assert_failure_contains("without leading zero")

    def test_non_integer_update_number(self) -> None:
        self.row["update_number"] = "one"
        self.write_rows([self.row])
        self.assert_failure_contains("without leading zero")

    def test_bad_tag(self) -> None:
        self.row["tag"] = "v0.1"
        self.write_rows([self.row])
        self.assert_failure_contains("invalid tag")

    def test_rc_must_be_prerelease(self) -> None:
        self.row.update(tag="v0.1.0-rc.1", semver="0.1.0-rc.1", prerelease="false")
        self.write_rows([self.row])
        self.assert_failure_contains("rc tag cannot have prerelease=false")

    def test_tag_pointing_to_another_commit(self) -> None:
        other = self.commit("other", NEXT_DATE)
        self.git("tag", "-f", "v0.1.0", other)
        self.assert_failure_contains("points to a different commit")

    def test_commit_time_mismatch(self) -> None:
        self.row["update_number"] = str(int(self.time_one) + 1)
        self.write_rows([self.row])
        self.assert_failure_contains("does not match commit %ct")

    def test_missing_tag_warns_without_require_tags(self) -> None:
        self.git("tag", "-d", "v0.1.0")
        result = self.run_checker()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("warning:", result.stdout)

    def test_missing_tag_errors_with_require_tags(self) -> None:
        self.git("tag", "-d", "v0.1.0")
        self.assert_failure_contains("tag v0.1.0 is missing locally", "--require-tags")

    def test_missing_commit_object_warns_or_errors(self) -> None:
        self.git("tag", "-d", "v0.1.0")
        self.row["commit"] = "f" * 40
        self.write_rows([self.row])
        result = self.run_checker()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("commit object", result.stdout)
        self.assert_failure_contains("commit object", "--require-tags")

    def test_unrecorded_tag_errors_with_require_tags(self) -> None:
        self.git("tag", "v0.2.0")
        self.assert_failure_contains("unrecorded local tag", "--require-tags")

    def test_header_must_match_exactly(self) -> None:
        (self.root / "docs/releases/releases.csv").write_text(
            "tag,semver\nv0.1.0,0.1.0\n", encoding="utf-8"
        )
        self.assert_failure_contains("header mismatch")

    def test_missing_changelog_heading(self) -> None:
        (self.root / "CHANGELOG.md").write_text("## [Unreleased]\n", encoding="utf-8")
        self.assert_failure_contains("has no ## [0.1.0] heading")

    def test_missing_digest_file(self) -> None:
        self.row["assets_sha256"] = "missing.sha256"
        self.write_rows([self.row])
        self.assert_failure_contains("cannot read asset checksum file")

    def test_malformed_digest_file(self) -> None:
        (self.root / "test.sha256").write_text("not a digest\n", encoding="utf-8")
        self.assert_failure_contains("malformed checksum line")

    def test_duplicate_tag(self) -> None:
        self.write_rows([self.row, self.row.copy()])
        self.assert_failure_contains("duplicate tag")

    def test_rc_precedes_final_release(self) -> None:
        rc_commit = self.commit("candidate", NEXT_DATE)
        rc_time = self.git("show", "-s", "--format=%ct", rc_commit)
        final_commit = self.commit("final", "2026-11-01T00:02:00+00:00")
        final_time = self.git("show", "-s", "--format=%ct", final_commit)
        self.git("tag", "v0.1.0-rc.1", rc_commit)
        self.git("tag", "-f", "v0.1.0", final_commit)
        rc = self.make_row("v0.1.0-rc.1", "0.1.0-rc.1", "true", rc_commit, rc_time)
        final = self.make_row("v0.1.0", "0.1.0", "false", final_commit, final_time)
        self.write_rows([rc, final])
        result = self.run_checker("--require-tags")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Summary: errors=0 warnings=0", result.stdout)


if __name__ == "__main__":
    unittest.main()
