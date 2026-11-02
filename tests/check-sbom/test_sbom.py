import copy
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("kernel_version", ROOT / ".github/scripts/set-kernel-version.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
SHA = "a" * 40
MAKEFILE = "VERSION = 6\nPATCHLEVEL = 18\nSUBLEVEL = 59\n"


class SbomTest(unittest.TestCase):
    def setUp(self):
        self.info = {
            "linux": {"name": "linux", "version": "custom", "type": "target", "virtual": False,
                      "dependencies": ["host-tool"]},
            "host-tool": {"name": "tool", "version": "1.0", "type": "host", "virtual": False},
            "virtual": {"type": "target", "virtual": True},
            "rootfs": {"type": "rootfs", "virtual": False},
        }
        self.sbom = {
            "bomFormat": "CycloneDX",
            "metadata": {"component": {"bom-ref": "msd-linux", "version": SHA}},
            "components": [
                {"bom-ref": "linux", "name": "linux", "version": "custom",
                 "cpe": "cpe:2.3:o:linux:linux_kernel:custom:-:*:*:*:*:*:*",
                 "licenses": [{"license": {"name": "unknown"}}],
                 "properties": [{"name": "BR_TYPE", "value": "target"}]},
                {"bom-ref": "host-tool", "name": "tool", "version": "1.0",
                 "properties": [{"name": "BR_TYPE", "value": "host"}]},
            ],
            "dependencies": [{"ref": "msd-linux", "dependsOn": ["linux"]},
                             {"ref": "linux", "dependsOn": ["host-tool"]},
                             {"ref": "host-tool", "dependsOn": []}],
        }

    def run_tool(self, local=True, sbom=None, makefile=MAKEFILE, extra=(), checked=True):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sbom.json"
            path.write_text(json.dumps(self.sbom if sbom is None else sbom))
            info = Path(tmp) / "info.json"
            info.write_text(json.dumps(self.info))
            kernel = Path(tmp) / "Makefile"
            kernel.write_text(makefile)
            original = path.read_text()
            argv = ["set-kernel-version.py", str(path)]
            if checked:
                argv += ["--show-info", str(info), "--project-version", SHA]
            if local:
                argv += ["--kernel-makefile", str(kernel)]
            argv += list(extra)
            with patch.object(sys, "argv", argv), patch.object(
                MODULE.urllib.request, "urlopen", return_value=io.BytesIO(makefile.encode())
            ) as urlopen:
                try:
                    MODULE.main()
                except SystemExit:
                    self.assertEqual(original, path.read_text())
                    raise
                self.assertEqual(0 if local else 1, urlopen.call_count)
            return json.loads(path.read_text())

    def test_local_and_pinned_remote_match(self):
        local = self.run_tool()
        self.assertEqual(local, self.run_tool(local=False))
        kernel = local["components"][0]
        self.assertEqual("6.18.59", kernel["version"])
        self.assertIn(":6.18.59:", kernel["cpe"])
        self.assertEqual(self.sbom["components"][0]["licenses"], kernel["licenses"])
        self.assertEqual(self.sbom["components"][1], local["components"][1])

    def test_idempotent_and_preserves_other_metadata(self):
        first = self.run_tool()
        self.assertEqual(first, self.run_tool(sbom=first))

    def test_rejects_duplicate_missing_extra_and_wrong_version(self):
        cases = []
        for change in ("duplicate", "missing", "extra", "version", "host-target", "name"):
            sbom = copy.deepcopy(self.sbom)
            if change == "duplicate":
                sbom["components"].append(copy.deepcopy(sbom["components"][1]))
            elif change == "missing":
                sbom["components"].pop()
            elif change == "extra":
                sbom["components"].append({"bom-ref": "extra"})
            elif change == "version":
                sbom["components"][1]["version"] = "old"
            elif change == "name":
                sbom["components"][1]["name"] = "other"
            else:
                sbom["components"][1]["properties"][0]["value"] = "target"
            cases.append((change, sbom))
        for change, sbom in cases:
            with self.subTest(change=change), self.assertRaises(SystemExit):
                self.run_tool(sbom=sbom)

    def test_rejects_stale_project_and_malformed_graph(self):
        for change in ("project", "graph-missing", "graph-extra", "graph-duplicate", "graph-unknown", "graph-wrong"):
            sbom = copy.deepcopy(self.sbom)
            if change == "project":
                sbom["metadata"]["component"]["version"] = "b" * 40
            elif change == "graph-missing":
                sbom["dependencies"].pop()
            elif change == "graph-extra":
                sbom["dependencies"].append({"ref": "extra"})
            elif change == "graph-duplicate":
                sbom["dependencies"].append(sbom["dependencies"][0])
            elif change == "graph-unknown":
                sbom["dependencies"][0]["dependsOn"] = ["not-in-bom"]
            else:
                sbom["dependencies"][1]["dependsOn"] = []
            with self.subTest(change=change), self.assertRaises(SystemExit):
                self.run_tool(sbom=sbom)

    def test_rejects_invalid_cpe_and_kernel(self):
        for value in (None, "bad", "cpe:2.3:a:other:kernel:custom:-:*:*:*:*:*:*"):
            sbom = copy.deepcopy(self.sbom)
            sbom["components"][0]["cpe"] = value
            with self.subTest(cpe=value), self.assertRaises(SystemExit):
                self.run_tool(sbom=sbom)
        for value in ("", "VERSION = 6\nPATCHLEVEL = 18\n"):
            with self.subTest(makefile=value), self.assertRaises(SystemExit):
                self.run_tool(makefile=value)

    def test_rejects_argument_mismatch(self):
        for extra in (("--project-version", "bad"), ("--show-info", "missing.json")):
            with self.subTest(extra=extra), self.assertRaises(SystemExit):
                self.run_tool(checked=False, extra=extra)

    def test_legacy_invocation_still_normalizes(self):
        self.assertEqual("6.18.59", self.run_tool(checked=False)["components"][0]["version"])

    def test_virtual_dependency_resolves_to_provider(self):
        self.info["linux"]["dependencies"] = ["virtual"]
        self.info["host-tool"]["provides"] = ["virtual"]
        self.run_tool()

    def test_rejects_non_cyclonedx(self):
        self.sbom["bomFormat"] = "SPDX"
        with self.assertRaisesRegex(SystemExit, "CycloneDX"):
            self.run_tool()

    def test_rejects_missing_and_multiple_kernel_components(self):
        for count in (0, 2):
            sbom = copy.deepcopy(self.sbom)
            kernel = sbom["components"].pop(0)
            sbom["components"] += [kernel] * count
            with self.subTest(count=count), self.assertRaisesRegex(SystemExit, "one kernel"):
                self.run_tool(sbom=sbom)

    def test_rejects_short_checkout_hash(self):
        with self.assertRaises(SystemExit):
            self.run_tool(extra=("--project-version", "abcdef0"))


if __name__ == "__main__":
    unittest.main()
