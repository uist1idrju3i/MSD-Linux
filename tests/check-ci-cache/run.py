#!/usr/bin/env python3
"""Exercise the real CI shell fragments and image-cache helper without a daemon."""

from collections.abc import Callable
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
ACTION = ROOT / ".github/actions/setup-dev-image/action.yml"
HELPER = ROOT / ".github/scripts/dev-image-cache.py"
BUILD = ROOT / ".github/workflows/build.yml"
TAG = "inputs-0123456789abcdef"
IMAGE_ID = "sha256:" + "a" * 64

FAKE_DOCKER = r'''#!/usr/bin/env python3
import json, os, pathlib, sys
args = sys.argv[1:]
config = json.loads(pathlib.Path(os.environ["FAKE_CONFIG"]).read_text())
with pathlib.Path(os.environ["FAKE_LOG"]).open("a") as stream:
    stream.write(json.dumps(args) + "\n")
if args[:2] == ["manifest", "inspect"]:
    print(config.get("manifest_output", "manifest unknown"), file=sys.stderr)
    sys.exit(config.get("manifest_status", 1))
if args[:1] == ["version"]:
    print(config.get("platform", "linux/amd64"))
elif args[:2] == ["image", "inspect"]:
    print(json.dumps({"id": config.get("image_id", "sha256:" + "a" * 64),
                      "os": "linux", "arch": config.get("arch", "amd64")}))
elif args[:1] == ["save"]:
    if config.get("save_status", 0): sys.exit(config["save_status"])
    pathlib.Path(args[args.index("--output") + 1]).write_bytes(b"fixture-image-archive\n")
elif args[:1] == ["load"]:
    if config.get("load_status", 0): sys.exit(config["load_status"])
elif args[:1] == ["build"]:
    sys.exit(config.get("build_status", 0))
elif args[:1] == ["pull"]:
    sys.exit(config.get("pull_status", 0))
'''

FAKE_GH = r'''#!/usr/bin/env python3
import json, os, pathlib, sys
config = json.loads(pathlib.Path(os.environ["FAKE_CONFIG"]).read_text())
with pathlib.Path(os.environ["FAKE_LOG"]).open("a") as stream:
    stream.write(json.dumps(["gh", *sys.argv[1:]]) + "\n")
sys.exit(config.get("auth_status" if sys.argv[1:3] == ["auth", "status"] else "attestation_status", 0))
'''


def step(text: str, name: str) -> str:
    match = re.search(rf"^(\s*)- id: {re.escape(name)}\s*$", text, re.M)
    assert match, f"Missing step {name}"
    following = text[match.end():]
    end = re.search(rf"^{match[1]}- ", following, re.M)
    return following[:end.start()] if end else following


def script(text: str, name: str) -> str:
    body = step(text, name)
    match = re.search(r"^(\s*)run: \|\n((?:\1  .*\n|\n)+)", body, re.M)
    assert match, f"Missing run body for {name}"
    return "\n".join(line[len(match[1]) + 2:] for line in match[2].splitlines())


def field(body: str, name: str) -> str:
    match = re.search(rf"^\s*{re.escape(name)}: (.+)$", body, re.M)
    assert match, f"Missing {name}"
    return match[1]


def guards(action: str, build: str) -> None:
    cache = step(action, "cache")
    prepare = step(action, "prepare")
    assert "if: steps.probe.outputs.published == 'false'" in cache
    assert "restore-keys:" not in cache
    assert "runner.os" in field(cache, "key") and "runner.arch" in field(cache, "key")
    assert "steps.probe.outputs.tag" in field(cache, "key")
    assert "MSD_DEV_REQUIRE_ATTESTATION: '1'" in prepare
    assert '[[ "$CACHE_HIT" == true ]]' in prepare
    assert "docker/msd-dev pull" in prepare
    assert 'steps.prepare.outputs.cacheable == \'true\'' in action
    assert "key: ${{ steps.cache.outputs.cache-primary-key }}" in action
    assert "github.run_attempt" in field(step(build, "ccache-restore"), "key")
    assert "steps.cache-generation.outputs.ccache-prefix" in field(
        step(build, "ccache-restore"), "restore-keys")
    assert "restore-keys: buildroot-ccache-" not in build
    assert "steps.ccache-restore.outputs.cache-primary-key" in build
    assert "steps.dl-restore.outputs.cache-primary-key" in build
    assert "steps.buildroot-build.outcome == 'success'" in build
    assert "CCACHE_MAXSIZE: 3G" in build


class CacheTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="msd-ci-cache-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        for name, content in (("docker", FAKE_DOCKER), ("gh", FAKE_GH)):
            path = self.bin / name
            path.write_text(content)
            path.chmod(0o755)
        self.config = self.root / "config.json"
        self.config.write_text("{}")
        self.log = self.root / "commands.jsonl"
        self.output = self.root / "output"
        self.output.touch()
        self.summary = self.root / "summary"
        self.cache = self.root / "msd-dev-image-cache"
        self.env = {**os.environ, "PATH": f"{self.bin}:{os.environ['PATH']}",
                    "FAKE_CONFIG": str(self.config), "FAKE_LOG": str(self.log),
                    "GITHUB_OUTPUT": str(self.output),
                    "GITHUB_STEP_SUMMARY": str(self.summary),
                    "RUNNER_TEMP": str(self.root), "INPUT_TAG": TAG,
                    "PUBLISHED": "false", "CACHE_HIT": "false"}
        self.env.pop("MSD_DEV_IMAGE", None)
        self.env["MSD_DEV_REQUIRE_ATTESTATION"] = "1"

    def configure(self, **values: object) -> None:
        self.config.write_text(json.dumps(values))

    def run_command(self, command: list[str], **extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(command, env={**self.env, **extra}, cwd=ROOT,
                              capture_output=True, text=True, timeout=30)

    def helper(self, operation: str, *extra: str) -> subprocess.CompletedProcess[str]:
        return self.run_command([sys.executable, str(HELPER), operation,
                                 "--directory", str(self.cache), "--tag", TAG, *extra])

    def prepare(self, **extra: str) -> subprocess.CompletedProcess[str]:
        return self.run_command(["bash", "-euo", "pipefail", "-c",
                                 script(ACTION.read_text(), "prepare")], **extra)

    def commands(self) -> list[list[str]]:
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def assert_no(self, *prefix: str) -> None:
        self.assertFalse(any(command[:len(prefix)] == list(prefix) for command in self.commands()),
                         self.commands())

    def seed(self) -> None:
        result = self.helper("save")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.output.write_text("")
        self.log.write_text("")

    def test_published_probe(self) -> None:
        for status, message, expected in (
            (0, '{"schemaVersion":2}', "true"),
            (1, "manifest unknown", "false"),
            (1, "no such manifest", "false"),
            (1, "image: not found", "false"),
        ):
            with self.subTest(message=message):
                self.configure(manifest_status=status, manifest_output=message)
                result = self.run_command([str(ROOT / "docker/msd-dev"), "available"])
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), expected)
                self.assert_no("pull")
                self.assert_no("build")

    def test_registry_errors_fail_without_fallback(self) -> None:
        for error in ("denied: authentication required", "TLS handshake timeout", "HTTP 429", ""):
            self.configure(manifest_status=1, manifest_output=error)
            result = self.run_command(["bash", "-euo", "pipefail", "-c",
                                       script(ACTION.read_text(), "probe")])
            self.assertNotEqual(result.returncode, 0)
            self.assert_no("load")
            self.assert_no("build")

    def test_published_always_pulls_and_verifies(self) -> None:
        result = self.prepare(PUBLISHED="true", CACHE_HIT="true")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(any(cmd[:3] == ["gh", "attestation", "verify"] for cmd in self.commands()))
        self.assertIn("source=published", self.output.read_text())
        self.assert_no("load")
        self.assert_no("build")
        self.assert_no("save")

    def test_published_failures_do_not_fall_back_to_cache(self) -> None:
        for setting in ("pull_status", "auth_status", "attestation_status"):
            with self.subTest(setting=setting):
                self.configure(**{setting: 1})
                result = self.prepare(PUBLISHED="true", CACHE_HIT="true")
                self.assertNotEqual(result.returncode, 0)
                self.assert_no("load")
                self.assert_no("build")
                self.assertNotIn("source=published", self.output.read_text())

    def test_cold_build_and_partial_hit_are_not_cache_hits(self) -> None:
        for hit in ("false", "", "true-but-not-exact"):
            with self.subTest(hit=hit):
                result = self.prepare(CACHE_HIT=hit)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("source=local-build", self.output.read_text())
                self.assertIn("cacheable=true", self.output.read_text())
                self.assertTrue(any(cmd[:1] == ["build"] for cmd in self.commands()))
                self.assert_no("load")

    def test_warm_load_preserves_identity(self) -> None:
        self.seed()
        result = self.prepare(CACHE_HIT="true")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("source=local-cache", self.output.read_text())
        self.assertTrue(any(cmd[:1] == ["load"] for cmd in self.commands()))
        self.assert_no("build")
        self.assert_no("pull")
        self.assert_no("save")
        self.assert_no("gh")

    def test_corrupt_archive_is_rejected_before_loading(self) -> None:
        self.seed()
        path = self.cache / "image.tar"
        original = path.read_bytes()
        path.write_bytes(b"X" + original[1:])
        result = self.prepare(CACHE_HIT="true")
        self.assertNotEqual(result.returncode, 0)
        self.assert_no("load")
        self.assert_no("build")
        self.assertNotIn("source=local-cache", self.output.read_text())

    def test_metadata_mismatches_are_rejected(self) -> None:
        self.seed()
        path = self.cache / "image.json"
        original = json.loads(path.read_text())
        for key, value in (("format", True), ("format", 2), ("tag", TAG + "0"),
                           ("image", "other-image"), ("os", "windows"), ("arch", "arm64"),
                           ("bytes", True), ("bytes", 999), ("id", "invalid")):
            with self.subTest(key=key, value=value):
                path.write_text(json.dumps({**original, key: value}))
                result = self.helper("load")
                self.assertNotEqual(result.returncode, 0)
                self.assert_no("load")

    def test_loaded_identity_and_docker_failures_are_rejected(self) -> None:
        self.seed()
        for config in ({"image_id": "sha256:" + "b" * 64}, {"load_status": 19},
                       {"arch": "arm64"}):
            with self.subTest(config=config):
                self.configure(**config)
                result = self.prepare(CACHE_HIT="true")
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("source=local-cache", self.output.read_text())
                self.assert_no("build")

    def test_missing_symlink_and_oversized_metadata_are_rejected(self) -> None:
        self.seed()
        metadata = self.cache / "image.json"
        contents = metadata.read_bytes()
        metadata.unlink()
        self.assertNotEqual(self.helper("load").returncode, 0)
        original = self.root / "original.json"
        original.write_bytes(contents)
        metadata.symlink_to(original)
        self.assertNotEqual(self.helper("load").returncode, 0)
        metadata.unlink()
        metadata.write_bytes(b" " * 4097)
        self.assertNotEqual(self.helper("load").returncode, 0)
        self.assert_no("load")

    def test_size_limit_and_empty_archive(self) -> None:
        result = self.helper("save", "--max-bytes", "1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("cacheable=false", self.output.read_text())
        self.assertIn("Cache save skipped: archive exceeds", self.summary.read_text())
        self.assertFalse((self.cache / "image.tar").exists())
        self.assertFalse((self.cache / "image.json").exists())
        self.seed()
        self.assertNotEqual(self.helper("load", "--max-bytes", "1").returncode, 0)
        (self.cache / "image.tar").write_bytes(b"")
        self.assertNotEqual(self.helper("load").returncode, 0)
        self.assert_no("load")

    def test_build_and_export_failures_do_not_report_success(self) -> None:
        for setting in ("build_status", "save_status"):
            with self.subTest(setting=setting):
                self.configure(**{setting: 18})
                result = self.prepare()
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("source=local-build", self.output.read_text())
                self.assertFalse((self.cache / "image.json").exists())

    def test_cli_rejects_invalid_tags_and_limits(self) -> None:
        self.assertNotEqual(self.helper("save", "--tag", "inputs-invalid").returncode, 0)
        self.assertNotEqual(self.helper("save", "--max-bytes", "0").returncode, 0)
        result = self.run_command([str(ROOT / "docker/msd-dev"), "available", "extra"])
        self.assertNotEqual(result.returncode, 0)
        self.assert_no("build")

    def test_generation_script_and_rerun_namespace(self) -> None:
        work = self.root / "work"
        (work / "docker").mkdir(parents=True)
        wrapper = work / "docker/msd-dev"
        wrapper.write_text('#!/usr/bin/env bash\nprintf "%s\\n" "$TEST_TAG"\n')
        wrapper.chmod(0o755)
        git = self.bin / "git"
        git.write_text('#!/usr/bin/env bash\nprintf "%s\\n" "$TEST_REVISION"\n')
        git.chmod(0o755)
        common = {**self.env, "RUNNER_OS": "Linux", "RUNNER_ARCH": "X64",
                  "TEST_TAG": TAG, "TEST_REVISION": "b" * 40, "DEFCONFIG_HASH": "c" * 64}
        prefixes = []
        for change in ({}, {}, {"RUNNER_ARCH": "ARM64"}, {"TEST_REVISION": "d" * 40},
                       {"TEST_TAG": "inputs-fedcba9876543210"}, {"DEFCONFIG_HASH": "e" * 64}):
            self.output.write_text("")
            result = subprocess.run(["bash", "-euo", "pipefail", "-c",
                                     script(BUILD.read_text(), "cache-generation")],
                                    cwd=work, env={**common, **change},
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            fields = dict(line.split("=", 1) for line in self.output.read_text().splitlines())
            prefixes.append(fields["ccache-prefix"])
        self.assertEqual(prefixes[0], prefixes[1])
        self.assertEqual(len(set(prefixes)), 5)
        self.assertIn("-cardputerzero-", prefixes[0])
        key = field(step(BUILD.read_text(), "ccache-restore"), "key")
        def render(attempt: str) -> str:
            values = {"steps.cache-generation.outputs.ccache-prefix": prefixes[0],
                      "github.run_id": "123", "github.run_attempt": attempt}
            return re.sub(r"\$\{\{\s*(.*?)\s*\}\}", lambda m: values[m[1]], key)
        self.assertNotEqual(render("1"), render("2"))

    def test_workflow_boundaries_and_mutation_controls(self) -> None:
        action = ACTION.read_text()
        build = BUILD.read_text()
        guards(action, build)
        mutations: list[Callable[[], None]] = [
            lambda: guards(action.replace("if: steps.probe.outputs.published == 'false'", "if: always()"), build),
            lambda: guards(action.replace("        key: msd-dev-image", "        restore-keys: broad-prefix\n        key: msd-dev-image"), build),
            lambda: guards(action.replace("MSD_DEV_REQUIRE_ATTESTATION: '1'", "MSD_DEV_REQUIRE_ATTESTATION: '0'"), build),
            lambda: guards(action.replace('[[ "$CACHE_HIT" == true ]]', '[[ -n "$CACHE_HIT" ]]'), build),
            lambda: guards(action.replace("&& steps.prepare.outputs.cacheable == 'true'", ""), build),
            lambda: guards(action, build.replace("-${{ github.run_attempt }}", "")),
            lambda: guards(action, build.replace("CCACHE_MAXSIZE: 3G", "CCACHE_MAXSIZE: 30G")),
        ]
        for mutation in mutations:
            with self.assertRaises(AssertionError):
                mutation()
        for name in ("lint", "agent-docs"):
            workflow = (ROOT / f".github/workflows/{name}.yml").read_text()
            self.assertIn("github.event.pull_request.number || github.run_id", workflow)
            self.assertIn("cancel-in-progress: ${{ github.event_name == 'pull_request' }}", workflow)
        lint = (ROOT / ".github/workflows/lint.yml").read_text()
        local_action = "uses: ./.github/actions/setup-dev-image # zizmor: ignore[self-repository] -- source archives cannot resolve vendor-backed skill symlinks; use the checkout"
        self.assertEqual(build.count(local_action), 2)
        self.assertEqual(lint.count(local_action), 2)
        for workflow in (build, lint):
            self.assertEqual(workflow.count("ignore[self-repository]"), 2)
            self.assertNotIn("ignore[unpinned-uses]", workflow)
        self.assertIn("docker/msd-dev python3 tests/check-ci-cache/run.py", build)
        self.assertIn("docker/msd-dev python3 .github/scripts/run-host-tests.py", build)
        self.assertIn("docker/msd-dev bash -c", script(build, "buildroot-build"))
        self.assertIn("make -C output", script(build, "buildroot-build"))
        self.assertIn("docker/msd-dev board/cardputerzero/qemu/test-boot.sh", build)
        self.assertIn("docker/msd-dev zizmor --offline", lint)
        publish = (ROOT / ".github/workflows/publish-dev-image.yml").read_text()
        self.assertLess(publish.index("trivy-gate.py gate"), publish.index("name: Push architecture image"))
        self.assertIn("Generate SPDX SBOM", publish)
        self.assertIn("uses: actions/attest-sbom@", publish)
        config = (ROOT / ".github/actionlint.yaml").read_text()
        self.assertNotIn("specifying action", config)
        self.assertIn("ARG ACTIONLINT_VERSION=1.7.12", (ROOT / "docker/msd-dev.Dockerfile").read_text())


if __name__ == "__main__":
    unittest.main(verbosity=2)
