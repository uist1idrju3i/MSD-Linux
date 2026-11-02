"""Test evidence conversion independently of the product build."""

import argparse
import contextlib
import csv
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path


SPEC = importlib.util.spec_from_file_location("collector", Path(__file__).with_name("collect.py"))
COLLECTOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COLLECTOR)


class CollectorTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        repo = self.root / "repo"
        recipe = repo / "vendor/buildroot/package/example"
        recipe.mkdir(parents=True)
        (recipe / "example.mk").write_text("EXAMPLE_VERSION = 1\n")
        (recipe / "Config.in").write_text("config BR2_EXAMPLE\nconfig BR2_ABSENT\n")
        (repo / "vendor/buildroot/Config.in").write_text(
            "config BR2_ENABLED\nconfig BR2_DISABLED\nconfig BR2_TEST_PASSWORD\n")
        external = repo / "package/external"
        external.mkdir(parents=True)
        (external / "external.mk").write_text("EXTERNAL_VERSION = 2\n")
        (external / "Config.in").write_text("menuconfig BR2_EXTERNAL\n")
        info = {
            "example": {"type": "target", "version": "1", "package_dir": "package/example"},
            "host-example": {"type": "host", "version": "1", "package_dir": "package/example"},
            "external": {"type": "target", "version": "2", "package_dir": "/work/package/external"},
            "rootfs": {"type": "rootfs", "version": "0"},
            "virtual": {"type": "target", "virtual": True},
        }
        self.sbom = {"components": [
            {"bom-ref": key, "name": "example" if key == "host-example" else key,
             "version": info[key]["version"]}
            for key in ("example", "host-example", "external")
        ]}
        variables = {name: {"raw": "", "expanded": ""} for name in (
            "TARGET_CFLAGS", "TARGET_CXXFLAGS", "TARGET_LDFLAGS", "HOST_CFLAGS",
            "HOST_LDFLAGS", "TOOLCHAIN_WRAPPER_ARGS", "TOOLCHAIN_WRAPPER_OPTS")}
        variables["EXAMPLE_CONF_OPTS"] = {"raw": "$(EXAMPLE_PATH)", "expanded": "/work/input"}
        variables["HOST_EXAMPLE_CONF_OPTS"] = {"raw": "--host", "expanded": "--host"}
        for name, data in (("info.json", info), ("sbom.json", self.sbom), ("vars.json", variables)):
            (self.root / name).write_text(json.dumps(data))
        (self.root / "config").write_text(
            "BR2_ENABLED=y\n# BR2_DISABLED is not set\nBR2_TEST_PASSWORD=\"fixture-only\"\n")
        (self.root / "kernel").write_text("CONFIG_ONE=m\n# CONFIG_TWO is not set\n")
        gcc = self.root / "gcc"
        gcc.mkdir()
        for category in ("common", "warnings", "params", "optimizers", "target"):
            (gcc / f"component-sdk-gcc-{category}-Os-a53.txt").write_text(
                "  -fexample  [enabled]\n  -fblank  \n  -o  <file>  /output/fixture.s\n")
        help_dir = self.root / "help"
        help_dir.mkdir()
        (help_dir / "status.json").write_text(json.dumps([
            {"source_directory": "example", "returncode": 0},
            {"source_directory": "failed", "returncode": 1}]))
        (help_dir / "example.txt").write_text("  --first  First option\n     Wrapped detail\n")
        (help_dir / "example.stderr").write_text("  --second  Second option\n")
        self.args = argparse.Namespace(
            repository=repo, output=self.root / "out", package_info=self.root / "info.json",
            sbom=self.root / "sbom.json", variables=self.root / "vars.json",
            configuration=self.root / "config", kernel_config=self.root / "kernel",
            gcc_help_dir=gcc, configure_help_dir=help_dir, path_map=["/work=@EXTERNAL@"])

    def run_collector(self):
        with contextlib.redirect_stdout(io.StringIO()):
            COLLECTOR.collect(self.args)

    def rows(self, name):
        with (self.args.output / name).open() as stream:
            return list(csv.DictReader(stream))

    def test_host_target_and_external_population(self):
        self.run_collector()
        rows = {r["component"]: r for r in self.rows("packages.csv")}
        self.assertEqual(set(rows), {"example", "host-example", "external"})
        self.assertEqual(rows["host-example"]["role"], "host")
        self.assertEqual(rows["external"]["recipes"], "package/external/external.mk")

    def test_duplicate_component_reference_fails(self):
        self.sbom["components"].append(self.sbom["components"][0])
        self.args.sbom.write_text(json.dumps(self.sbom))
        with self.assertRaisesRegex(ValueError, "duplicate SBOM"):
            self.run_collector()

    def test_missing_component_fails(self):
        self.sbom["components"].pop()
        self.args.sbom.write_text(json.dumps(self.sbom))
        with self.assertRaisesRegex(ValueError, "populations differ"):
            self.run_collector()

    def test_absence_disabled_and_withheld_are_distinct(self):
        self.run_collector()
        values = {r["symbol"]: r["normalized_value"] for r in self.rows("buildroot-symbols.csv")}
        self.assertEqual(values["BR2_ENABLED"], "y")
        self.assertEqual(values["BR2_DISABLED"], "n")
        self.assertEqual(values["BR2_ABSENT"], "not-recorded")
        self.assertEqual(values["BR2_TEST_PASSWORD"], "withheld")

    def test_paths_and_package_namespaces(self):
        self.run_collector()
        data = json.loads((self.args.output / "package-variables.json").read_text())
        self.assertEqual(data["example"]["EXAMPLE_CONF_OPTS"]["expanded"], "@EXTERNAL@/input")
        self.assertNotIn("HOST_EXAMPLE_CONF_OPTS", data["example"])
        self.assertIn("HOST_EXAMPLE_CONF_OPTS", data["host-example"])

    def test_help_streams_query_categories_and_kernel(self):
        self.run_collector()
        self.assertEqual({r["option"] for r in self.rows("configure-options.csv")},
                         {"--first", "--second"})
        gcc = self.rows("gcc-options.csv")
        self.assertEqual(len(gcc), 15)
        self.assertEqual(len({r["category"] for r in gcc}), 5)
        self.assertEqual([r["query_result"] for r in gcc if r["option"] == "-fblank"], [""] * 5)
        self.assertEqual([r["query_result"] for r in gcc if r["option"] == "-o"],
                         ["<file>  @GCC_OUTPUT@"] * 5)
        self.assertEqual({r["symbol"]: r["artifact_value"] for r in self.rows("kernel-config.csv")},
                         {"CONFIG_ONE": "m", "CONFIG_TWO": "n"})

    def test_identical_inputs_produce_identical_files(self):
        self.run_collector()
        before = {p.name: p.read_bytes() for p in self.args.output.iterdir()}
        self.run_collector()
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.args.output.iterdir()})


if __name__ == "__main__":
    unittest.main()
