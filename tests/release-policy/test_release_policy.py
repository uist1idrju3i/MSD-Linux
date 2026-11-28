import json
import os
from pathlib import Path
import runpy
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch


POLICY = runpy.run_path(str(Path(__file__).resolve().parents[2] /
                            ".github/scripts/check-release-policy.py"))


class ProductionPolicyTest(unittest.TestCase):
    def test_requires_exact_production_policy(self):
        good_environment = {
            "can_admins_bypass": False,
            "deployment_branch_policy": {
                "protected_branches": False, "custom_branch_policies": True,
            },
            "protection_rules": [{"type": "required_reviewers", "reviewers": [{}]}],
        }
        good_policy = {"total_count": 1, "branch_policies": [{"type": "tag", "name": "v*"}]}

        def check(environment, policies):
            def fetch(endpoint):
                if endpoint.endswith("/environments/production"):
                    return environment
                self.assertTrue(endpoint.endswith("/deployment-branch-policies?per_page=100"))
                return policies
            with patch.dict(os.environ, {"GITHUB_REPOSITORY": "owner/repo"}):
                POLICY["check_production"](fetch)

        check(good_environment, good_policy)
        for environment, policies in (
            (good_environment | {"can_admins_bypass": True}, good_policy),
            (good_environment | {"protection_rules": []}, good_policy),
            (good_environment, good_policy | {"total_count": 2}),
            (good_environment, good_policy | {"branch_policies": [{"type": "branch", "name": "v*"}]}),
        ):
            with self.subTest(environment=environment, policies=policies):
                with self.assertRaises(ValueError):
                    check(environment, policies)

    def test_tag_push_must_match_checkout_and_main(self):
        original = Path.cwd()
        with TemporaryDirectory() as tmp:
            os.chdir(tmp)
            def git(*args):
                return subprocess.check_output(
                    ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args],
                    text=True,
                ).strip()

            try:
                git("init", "-q")
                git("commit", "--allow-empty", "-qm", "main")
                head = git("rev-parse", "HEAD")
                git("update-ref", "refs/remotes/origin/main", head)
                git("-c", "tag.gpgSign=false", "tag", "v1.2.3")
                event = Path("event.json")
                event.write_text(json.dumps({"deleted": False}), encoding="utf-8")
                env = {
                    "GITHUB_EVENT_NAME": "push", "GITHUB_EVENT_PATH": str(event),
                    "GITHUB_REF": "refs/tags/v1.2.3", "GITHUB_REF_NAME": "v1.2.3",
                    "GITHUB_SHA": head,
                }
                with patch.dict(os.environ, env):
                    self.assertEqual(POLICY["check_tag"](), "v1.2.3")
                    git("commit", "--allow-empty", "-qm", "unmerged")
                    with self.assertRaises(ValueError):
                        POLICY["check_tag"]()
                    git("-c", "tag.gpgSign=false", "tag", "--force", "v1.2.3")
                    with patch.dict(os.environ, {"GITHUB_SHA": git("rev-parse", "HEAD")}):
                        with self.assertRaises(subprocess.CalledProcessError):
                            POLICY["check_tag"]()
            finally:
                os.chdir(original)

    def test_rc_tag_requires_unrecorded_version_with_increasing_commit_time(self):
        original = Path.cwd()
        with TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                subprocess.run(["git", "init", "-q"], check=True)
                def git(*args):
                    return subprocess.check_output(
                        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args],
                        text=True,
                        env=os.environ | {"GIT_COMMITTER_DATE": "2026-11-28T00:00:00Z"},
                    ).strip()
                Path("CHANGELOG.md").write_text("## [1.2.3-rc.1] - 2026-11-28\n", encoding="utf-8")
                Path("docs/releases").mkdir(parents=True)
                ledger = Path("docs/releases/releases.csv")
                header = "tag,semver,prerelease,commit,update_number,signing_key,release_url,assets_sha256,note\n"
                ledger.write_text(header + "v1.2.2,1.2.2,false,old,100,,,,\n", encoding="utf-8")
                git("add", "CHANGELOG.md", str(ledger))
                git("commit", "-qm", "release")
                candidate = git("rev-parse", "HEAD")
                git("update-ref", "refs/remotes/origin/main", candidate)
                POLICY["check_version"]("v1.2.3-rc.1")
                for tag in ("v1.2.3-rc.01", "v1.2.3+test", "v1.2.3"):
                    with self.subTest(tag=tag), self.assertRaises(ValueError):
                        POLICY["check_version"](tag)
                ledger.write_text(header + "v1.2.2,1.2.2,false,old,1999999999,,,,\n", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "commit time"):
                    POLICY["check_version"]("v1.2.3-rc.1")
                git("commit", "-qam", "new ledger entry")
                git("update-ref", "refs/remotes/origin/main", git("rev-parse", "HEAD"))
                git("switch", "--detach", candidate)
                with self.assertRaisesRegex(ValueError, "origin/main release ledger"):
                    POLICY["check_version"]("v1.2.3-rc.1")
            finally:
                os.chdir(original)
