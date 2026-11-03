#!/usr/bin/env python3
"""Test dev-image path classification and its workflow trigger contract."""

import importlib.util
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / ".github/scripts/dev-image-scope.py"
WORKFLOW = ROOT / ".github/workflows/publish-dev-image.yml"
SPEC = importlib.util.spec_from_file_location("dev_image_scope", SCRIPT)
assert SPEC and SPEC.loader
scope = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scope)


def trigger_block(workflow: str, trigger: str) -> list[str]:
    lines = workflow.splitlines()
    start = lines.index(f"  {trigger}:")
    end = next(
        (
            index
            for index in range(start + 1, len(lines))
            if re.fullmatch(r"  [A-Za-z][A-Za-z0-9_-]*:", lines[index])
        ),
        len(lines),
    )
    return lines[start:end]


def trigger_paths(workflow: str, trigger: str) -> list[str] | None:
    block = trigger_block(workflow, trigger)
    try:
        start = block.index("    paths:") + 1
    except ValueError:
        return None

    paths = []
    for line in block[start:]:
        if line.startswith("      - "):
            paths.append(line[8:])
        elif line and not line.startswith("      "):
            break
    return paths


def git(root: Path, *args: str) -> str:
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "CI fixture",
        "GIT_COMMITTER_NAME": "CI fixture",
        "GIT_AUTHOR_EMAIL": "ci-fixture@example.invalid",
        "GIT_COMMITTER_EMAIL": "ci-fixture@example.invalid",
    }
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        env=env,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


def init_repository(root: Path, path: str) -> str:
    git(root, "init", "--quiet", "--initial-branch=main")
    git(root, "config", "user.name", "CI fixture")
    git(root, "config", "user.email", "ci-fixture@example.invalid")
    file_path = root / path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("fixture\n", encoding="utf-8")
    git(root, "add", "--", path)
    git(root, "commit", "--quiet", "-m", "fixture base")
    return git(root, "rev-parse", "HEAD")


class DevImageScope(unittest.TestCase):
    def test_documentation_only_changes_are_out_of_scope(self) -> None:
        self.assertFalse(scope.requires_build(["README.md", "docs/CI.md"]))

    def test_dockerfile_qemu_patch_and_workflow_changes_are_in_scope(self) -> None:
        for path in (
            "docker/msd-dev.Dockerfile",
            "docker/qemu-patches/nested/arm64/fix.patch",
            ".github/workflows/publish-dev-image.yml",
        ):
            with self.subTest(path=path):
                self.assertTrue(scope.requires_build([path]))

    def test_workflow_path_filters_match_the_single_scope_list(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertEqual(trigger_paths(workflow, "push"), list(scope.PATH_PATTERNS))
        self.assertIsNone(trigger_paths(workflow, "pull_request"))

    def test_empty_diff_is_out_of_scope(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            commit = init_repository(root, "README.md")
            self.assertFalse(scope.needs_development_image(commit, commit, cwd=str(root)))

    def test_matching_source_or_destination_of_rename_is_in_scope(self) -> None:
        for source, destination in (
            ("docker/msd-dev.Dockerfile", "docs/CI.md"),
            ("docs/CI.md", "docker/msd-dev.Dockerfile"),
        ):
            with self.subTest(source=source, destination=destination):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    base = init_repository(root, source)
                    old_path, new_path = root / source, root / destination
                    new_path.parent.mkdir(parents=True, exist_ok=True)
                    old_path.rename(new_path)
                    git(root, "add", "--", source, destination)
                    git(root, "commit", "--quiet", "-m", "fixture rename")
                    head = git(root, "rev-parse", "HEAD")
                    self.assertTrue(scope.needs_development_image(base, head, cwd=str(root)))

    def test_git_diff_failure_exits_without_reporting_false(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake_git = root / "git"
            fake_git.write_text(
                "#!/bin/sh\nprintf 'intentional diff failure\\n' >&2\nexit 23\n",
                encoding="utf-8",
            )
            fake_git.chmod(0o700)
            process = subprocess.run(
                [sys.executable, str(SCRIPT), "a" * 40, "b" * 40],
                env={**os.environ, "PATH": f"{root}{os.pathsep}{os.environ['PATH']}"},
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(process.returncode, 0)
            self.assertNotEqual(process.stdout.strip(), "false")
            self.assertIn("git diff failed", process.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
