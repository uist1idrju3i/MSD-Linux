#!/usr/bin/env python3
"""Check build trigger failure modes and bounded host-test scheduling."""

import csv
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = (ROOT / ".github/workflows/build.yml").read_text()
FAKE_GIT = r'''#!/usr/bin/env python3
import os, pathlib, sys
args = sys.argv[1:]
with open(os.environ["GIT_CALLS"], "a") as stream:
    stream.write(" ".join(args) + "\n")
if args[0] == "cat-file":
    missing = os.environ["MISSING_BASE"] if args[-1].startswith("b" * 40) else os.environ["MISSING_HEAD"]
    sys.exit(int(bool(missing) and not pathlib.Path(os.environ["FETCHED"]).exists()))
if args[0] == "fetch":
    if os.environ["FETCH_FAIL"]: sys.exit(1)
    pathlib.Path(os.environ["FETCHED"]).touch()
    sys.exit(0)
if args[0] == "diff":
    assert args == ["diff", "--no-renames", "--name-only", "-z", "b" * 40 + "..." + "a" * 40], args
    if os.environ["DIFF_FAIL"]: sys.exit(1)
    sys.stdout.buffer.write(bytes.fromhex(os.environ["CHANGED_HEX"]))
    sys.exit(0)
raise AssertionError(args)
'''


def filter_script(workflow: str) -> str:
    block = workflow.split("name: Check whether the build is needed\n", 1)[1]
    block = block.split("        run: |\n", 1)[1].split("\n  msd-update-tests:", 1)[0]
    return textwrap.dedent(block)


def classify(paths: list[str], event: str = "pull_request", *, workflow: str = WORKFLOW,
             **flags: str) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        git = root / "git"
        git.write_text(FAKE_GIT)
        git.chmod(0o755)
        output, calls = root / "output", root / "calls"
        env = {**os.environ, "PATH": f'{root}:{os.environ["PATH"]}',
               "RUNNER_TEMP": directory, "GITHUB_OUTPUT": str(output),
               "EVENT_NAME": event, "BASE_SHA": "b" * 40, "HEAD_SHA": "a" * 40,
               "PR_NUMBER": "123", "GIT_CALLS": str(calls), "FETCHED": str(root / "fetched"),
               "MISSING_BASE": "", "MISSING_HEAD": "", "FETCH_FAIL": "", "DIFF_FAIL": "",
               "CHANGED_HEX": b"".join(path.encode() + b"\0" for path in paths).hex(), **flags}
        subprocess.run(["bash", "-euo", "pipefail", "-c", filter_script(workflow)],
                       env=env, check=True, capture_output=True, timeout=15)
        value = output.read_text().strip()
        assert value in {"build=true", "build=false"}, value
        return value == "build=true", calls.read_text() if calls.exists() else ""


class BuildScope(unittest.TestCase):
    def test_document_and_gate_only_paths(self) -> None:
        for path in ("README.md", "RESEARCH.md", str(Path("docs") / "new note\nsecond line.md"),
                     str(Path("docs") / "experiments/raw.csv"), "docs/logo/tools/generate.py", "public_html/index.html",
                     ".agents/skills/vendor-update/SKILL.md", ".claude/skills/yomiyasu", "vendor/yomiyasu",
                     ".devin/wiki.json", "LICENSE", "tests/check-ci-cache/run.py",
                     "tests/release-signing-key/run.py", ".github/dependabot.yml"):
            with self.subTest(path=path):
                self.assertFalse(classify([path])[0])

    def test_product_inputs_override_markdown_exemption(self) -> None:
        for path in ("board/cardputerzero/firmware.txt", "board/README.md", "configs/README.md",
                     "package/example/input.md", "docker/README.md", "patches/README.md",
                     "vendor/buildroot", "vendor/kernel/README.md", "external.mk", "Config.in",
                     "Makefile", ".gitmodules", "unknown file\nsecond line", "tests/msd-update/run.sh",
                     str(Path("docs") / "product.config"), str(Path("docs") / "input.dts"),
                     str(Path("docs") / "unknown-input.py"),
                     ".github/workflows/build.yml", ".github/workflows/lint.yml", ".github/workflows/new.yml",
                     ".github/actions/setup-dev-image/action.yml",
                     ".github/scripts/dev-image-cache.py", "tests/release-signing-key/new-file.py"):
            with self.subTest(path=path):
                self.assertTrue(classify(["README.md", path])[0])

    def test_all_events_and_fail_closed(self) -> None:
        for event in ("push", "pull_request"):
            result, calls = classify(["README.md"], event)
            self.assertFalse(result)
            self.assertIn("--no-renames --name-only -z " + "b" * 40 + "..." + "a" * 40, calls)
        for event in ("workflow_dispatch", "schedule", "unrecognized"):
            result, calls = classify(["README.md"], event)
            self.assertTrue(result)
            self.assertEqual(calls, "")
        for flags in ({"MISSING_BASE": "1"}, {"BASE_SHA": "0" * 40},
                      {"MISSING_HEAD": "1", "FETCH_FAIL": "1"}, {"DIFF_FAIL": "1"},
                      {"MISSING_HEAD": "1", "EVENT_NAME": "push"}):
            with self.subTest(flags=flags):
                self.assertTrue(classify(["README.md"], **flags)[0])
        result, calls = classify(["README.md"], MISSING_HEAD="1")
        self.assertFalse(result)
        self.assertIn("refs/pull/123/head:refs/remotes/pull/123/head", calls)

    def test_real_git_rename_delete_and_cumulative_diff(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def git(*args: str) -> str:
                fixture_env = {**os.environ, "GIT_AUTHOR_NAME": "CI fixture", "GIT_COMMITTER_NAME": "CI fixture",
                               "GIT_AUTHOR_EMAIL": "ci-fixture@example.invalid",
                               "GIT_COMMITTER_EMAIL": "ci-fixture@example.invalid"}
                return subprocess.check_output(["git", *args], cwd=root, env=fixture_env, text=True).strip()
            git("init", "--quiet", "--initial-branch=main")
            (root / "board").mkdir()
            (root / "docs").mkdir()
            (root / "board/input.md").write_text("product input\n")
            git("add", ".")
            git("commit", "--quiet", "-m", "fixture base")
            base = git("rev-parse", "HEAD")
            git("mv", "board/input.md", str(Path("docs") / "renamed.md"))
            git("commit", "--quiet", "-am", "fixture rename")
            (root / "docs" / "latest.md").write_text("documentation only at tip\n")
            git("add", ".")
            git("commit", "--quiet", "-m", "fixture documentation tip")
            head = git("rev-parse", "HEAD")
            output = root / "result"
            env = {**os.environ, "EVENT_NAME": "pull_request", "BASE_SHA": base,
                   "HEAD_SHA": head, "PR_NUMBER": "123", "RUNNER_TEMP": directory,
                   "GITHUB_OUTPUT": str(output)}
            subprocess.run(["bash", "-euo", "pipefail", "-c", filter_script(WORKFLOW)],
                           cwd=root, env=env, check=True, capture_output=True, timeout=15)
            self.assertEqual(output.read_text().strip(), "build=true")
            self.assertIn("board/input.md", (root / "changed-files").read_bytes().decode())
            output.write_text("")
            subprocess.run(["bash", "-euo", "pipefail", "-c", filter_script(WORKFLOW.replace("--no-renames ", ""))],
                           cwd=root, env=env, check=True, capture_output=True, timeout=15)
            self.assertEqual(output.read_text().strip(), "build=false")
            doc_base = head
            git("rm", str(Path("docs") / "renamed.md"))
            git("commit", "--quiet", "-m", "fixture document removal")
            output.write_text("")
            subprocess.run(["bash", "-euo", "pipefail", "-c", filter_script(WORKFLOW)],
                           cwd=root, env={**env, "BASE_SHA": doc_base, "HEAD_SHA": git("rev-parse", "HEAD")},
                           check=True, capture_output=True, timeout=15)
            self.assertEqual(output.read_text().strip(), "build=false")

    def test_required_jobs_and_negative_controls(self) -> None:
        job = WORKFLOW.split("\n  msd-update-tests:", 1)[1].split("\n  build:", 1)[0]
        self.assertNotRegex(job, r"(?m)^    (if|needs):")
        self.assertIn("if: needs.changes.outputs.build == 'true'", WORKFLOW)
        self.assertNotIn("paths-ignore:", WORKFLOW)
        self.assertIn("tests/check-ci-scope/run.py", job)
        # A broadened exemption must wrongly exclude product inputs.
        mutated = WORKFLOW.replace("tests/check-*/*", "tests/*")
        self.assertNotEqual(mutated, WORKFLOW)
        self.assertFalse(classify(["tests/msd-update/run.sh"], workflow=mutated)[0])
        no_workflow_rule = WORKFLOW.replace(".github/workflows/*|", "")
        self.assertNotEqual(no_workflow_rule, WORKFLOW)
        self.assertFalse(classify([".github/workflows/build.yml"], workflow=no_workflow_rule)[0])
        no_product_priority = WORKFLOW.replace("board/*|", "")
        self.assertFalse(classify(["board/input.md"], workflow=no_product_priority)[0])


spec = importlib.util.spec_from_file_location("host_test_runner", ROOT / ".github/scripts/run-host-tests.py")
assert spec and spec.loader
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class ParallelRunner(unittest.TestCase):
    def test_suites_are_preserved_and_outputs_do_not_overlap(self) -> None:
        self.assertEqual(set(runner.SUITES), {"msd-update", "init-scripts", "msd-hwinfo", "msd-data-grow",
                                             "qemu-log-check", "powerfail-log", "msd-dev"})
        self.assertIn("--jobs 2 --output-dir", WORKFLOW)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            # Both processes must start before either can finish. A serial runner times out.
            code = ("import pathlib,time,sys; p=pathlib.Path('.'); "
                    "(p/sys.argv[1]).touch(); start=time.monotonic(); "
                    "exec('while not (p/sys.argv[2]).exists():\\n time.sleep(0.01)'); print('paired')")
            suites = [("one", [sys.executable, "-c", code, "one.ready", "two.ready"]),
                      ("two", [sys.executable, "-c", code, "two.ready", "one.ready"])]
            results = runner.run(suites, root / "logs", 2, 3, cwd=root)
            self.assertEqual([row["status"] for row in results], ["passed", "passed"])
            self.assertIn("paired", (root / "logs/one.log").read_text())
            with self.assertRaises(FileExistsError):
                runner.run(suites, root / "logs", 2, 3, cwd=root)

    def test_failure_timeout_and_late_failure_do_not_hide_other_results(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            suites = [("late-failure", [sys.executable, "-c", "print('success marker'); raise SystemExit(17)"]),
                      ("pass", [sys.executable, "-c", "print('finished')"]),
                      ("timeout", [sys.executable, "-c", "import time; time.sleep(10)"]),
                      ("missing", [str(root / "no-such-command")])]
            results = runner.run(suites, root / "logs", 2, 0.3, cwd=root)
            self.assertEqual([row["status"] for row in results], ["failed", "passed", "timeout", "error"])
            self.assertEqual([row["exit_code"] for row in results], [17, 0, 124, 127])
            with (root / "logs/results.csv").open() as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 4)
            self.assertTrue(all(float(row["seconds"]) >= 0 for row in rows))


if __name__ == "__main__":
    unittest.main(verbosity=2)
