#!/usr/bin/env python3
"""Host tests for the v2 judge, supervisor and matrix; no QEMU or network."""

import csv
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
V2 = ROOT / "board/cardputerzero/tools/bench/fs-compare-v2"
SPEC = importlib.util.spec_from_file_location("supervisor", V2 / "supervisor.py")
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)
sys.path.insert(0, str(V2))
PREFLIGHT_SPEC = importlib.util.spec_from_file_location("preflight", V2 / "preflight.py")
P = importlib.util.module_from_spec(PREFLIGHT_SPEC)
PREFLIGHT_SPEC.loader.exec_module(P)


def phase_result(test="smoke", phase="run", **overrides):
    result = dict(schema=M.SCHEMA, phase=phase, test=test, reaped=True,
                  returncode=0, mode="normal", qmp_quit=True, fallback=[],
                  cut_intent=False, cut_sent=False, marker=True, error=None)
    result.update(overrides)
    return result


def fixture(directory, test="smoke", text=None, **overrides):
    directory.mkdir(exist_ok=True)
    (directory / "host.log").write_text("")
    phases = ["run", "verify"] if test in M.CUT_MARKERS else ["run"]
    for phase in phases:
        content = text if text is not None else M.MARKERS[phase] + "\n"
        if phase == "run" and test in M.CUT_MARKERS:
            content = M.CUT_MARKERS[test] + "\n"
        path = directory / f"qemu-{phase}.log"
        path.write_text(content)
        result = phase_result(test, phase)
        if phase == "run" and test in M.CUT_MARKERS:
            result.update(mode="cut", returncode=-9, qmp_quit=False,
                          cut_intent=True, cut_sent=True, marker=False)
            M.write_json(directory / "cut-intent.json", dict(test=test, phase=phase,
                         marker=M.CUT_MARKERS[test], schema=M.SCHEMA))
        result.update(overrides)
        result["log_sha256"] = M.hashlib.sha256(path.read_bytes()).hexdigest()
        M.write_json(directory / f"phase-{phase}.json", result)
    header = next(line.split("=", 1)[1].strip("'") for line in
                  (V2 / "fs-compare-matrix.sh").read_text().splitlines()
                  if line.startswith("SUMMARY_HEADER="))
    values = {key: "" for key in header.split(",")}
    values.update(run_id=directory.name, config="E1", test=test, status="ok", wall_seconds="1")
    with (directory / "summary.pending.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=values, lineterminator="\n")
        writer.writeheader()
        writer.writerow(values)


class Judge(unittest.TestCase):
    def test_only_complete_reaped_normal_phase_passes(self):
        self.assertTrue(M.phase_ok(phase_result(), "smoke", "run"))
        for overrides in [dict(returncode=-9), dict(returncode=1), dict(returncode=None),
                          dict(marker=False), dict(reaped=False), dict(qmp_quit=False),
                          dict(fallback=["SIGTERM"]), dict(fallback=["SIGKILL"]),
                          dict(mode=None), dict(error="timeout"), dict(schema="old")]:
            with self.subTest(overrides=overrides):
                self.assertFalse(M.phase_ok(phase_result(**overrides), "smoke", "run"))
        self.assertFalse(M.phase_ok({}, "smoke", "run"))
        self.assertFalse(M.phase_ok(None, "smoke", "run"))

    def test_cut_is_not_recovery_success(self):
        cut = phase_result("T2", mode="cut", returncode=-9, qmp_quit=False,
                           cut_intent=True, cut_sent=True, marker=False)
        self.assertTrue(M.phase_ok(cut, "T2", "run"))
        for change in [dict(cut_intent=False), dict(cut_sent=False), dict(returncode=0)]:
            self.assertFalse(M.phase_ok(dict(cut, **change), "T2", "run"))
        self.assertFalse(M.phase_ok(cut, "T2", "verify"))
        self.assertFalse(M.phase_ok(dict(cut, test="smoke"), "smoke", "run"))

    def test_atomic_replace_failure_preserves_previous_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "result.json"
            path.write_bytes(b"old")
            with mock.patch.object(M.os, "replace", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    M.atomic_write(path, b"new")
            self.assertEqual(path.read_bytes(), b"old")
            self.assertEqual(list(path.parent.iterdir()), [path])

    def test_final_publication_and_matrix_gate(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "run"
            fixture(directory)
            self.assertFalse(M.matrix_ok(directory / "summary.csv", 0))
            result = M.finalize(directory, "smoke", 0)
            self.assertEqual(result["status"], "ok")
            self.assertEqual((directory / "errors.jsonl").read_text(), "")
            M.write_json(directory / "matrix-child.json", {"status": 0})
            self.assertTrue(M.matrix_ok(directory / "summary.csv", 0))
            for status in [1, 137, -9, None]:
                self.assertFalse(M.matrix_ok(directory / "summary.csv", status))
            M.write_json(directory / "matrix-child.json", {"status": 7})
            self.assertFalse(M.matrix_ok(directory / "summary.csv", 0))
            with self.assertRaises(FileExistsError):
                M.finalize(directory, "smoke", 0)

    def test_missing_invalid_changed_and_old_evidence_fail(self):
        for mutation in ("missing-phase", "bad-json", "changed-log", "empty-log", "missing-summary",
                         "missing-marker", "driver-nonzero", "old-schema", "wrong-run"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary) / "run"
                fixture(directory)
                phase = directory / "phase-run.json"
                if mutation == "missing-phase":
                    phase.unlink()
                elif mutation == "bad-json":
                    phase.write_text("[")
                elif mutation == "changed-log":
                    (directory / "qemu-run.log").write_text("changed")
                elif mutation == "empty-log":
                    fixture(directory, text="")
                elif mutation == "missing-summary":
                    (directory / "summary.pending.csv").unlink()
                elif mutation == "missing-marker":
                    value = M.load_json(phase)
                    value["marker"] = False
                    M.write_json(phase, value)
                elif mutation == "old-schema":
                    value = M.load_json(phase)
                    value["schema"] = "old"
                    M.write_json(phase, value)
                elif mutation == "wrong-run":
                    path = directory / "summary.pending.csv"
                    path.write_text(path.read_text().replace("run,E1", "other,E1"))
                result = M.finalize(directory, "smoke", 1 if mutation == "driver-nonzero" else 0)
                self.assertNotEqual(result["status"], "ok")
                self.assertFalse(M.matrix_ok(directory / "summary.csv", 0))

    def test_planned_cut_needs_intent_and_normal_recovery(self):
        for test in ("T2", "T3"):
            for mutation in ("none", "missing-intent", "recovery-killed"):
                with self.subTest(test=test, mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                    directory = Path(temporary) / "run"
                    fixture(directory, test)
                    if mutation == "missing-intent":
                        (directory / "cut-intent.json").unlink()
                    elif mutation == "recovery-killed":
                        path = directory / "phase-verify.json"
                        value = M.load_json(path)
                        value["returncode"] = -9
                        M.write_json(path, value)
                    result = M.finalize(directory, test, 0)
                    self.assertEqual(result["status"] == "ok", mutation == "none")

    def test_post_marker_errors_are_rescanned_with_location(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "run"
            fixture(directory)
            log = directory / "qemu-run.log"
            self.assertEqual(M.aggregate_errors([("run", log)], "smoke"), [])
            log.write_text(log.read_text() + "msd.fscmp: error=late\n")
            path = directory / "phase-run.json"
            value = M.load_json(path)
            value["log_sha256"] = M.hashlib.sha256(log.read_bytes()).hexdigest()
            M.write_json(path, value)
            self.assertNotEqual(M.finalize(directory, "smoke", 0)["status"], "ok")
            error = json.loads((directory / "errors.jsonl").read_text().splitlines()[0])
            self.assertEqual((error["file"], error["line"], error["phase"]), ("qemu-run.log", 2, "run"))
            self.assertIn("error=late", (directory / "errors.txt").read_text())

    def test_error_publication_failure_never_commits_success(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "run"
            fixture(directory)
            with mock.patch.object(M, "atomic_write", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    M.finalize(directory, "smoke", 0)
            self.assertFalse((directory / "result.json").exists())
            self.assertFalse(M.matrix_ok(directory / "summary.csv", 0))

    def test_final_commit_follows_errors_and_summary(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "run"
            fixture(directory)
            original = M.atomic_write
            order = []

            def observe(path, content):
                order.append(Path(path).name)
                if Path(path).name == "result.json":
                    self.assertTrue((directory / "errors.jsonl").exists())
                    self.assertTrue((directory / "errors.txt").exists())
                    self.assertTrue((directory / "summary.csv").exists())
                return original(path, content)

            with mock.patch.object(M, "atomic_write", side_effect=observe):
                self.assertEqual(M.finalize(directory, "smoke", 0)["status"], "ok")
            self.assertEqual(order[-1], "result.json")

    def test_summary_tampering_and_missing_final_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "run"
            fixture(directory)
            M.finalize(directory, "smoke", 0)
            path = directory / "summary.csv"
            path.write_text(path.read_text() + "extra\n")
            self.assertFalse(M.matrix_ok(path, 0))
            (directory / "result.json").unlink()
            self.assertFalse(M.matrix_ok(path, 0))


class Errors(unittest.TestCase):
    def test_real_launcher_provenance_is_not_a_qemu_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            fake = directory / "qemu-system-aarch64"
            fake.write_text(f"#!{sys.executable}\nimport sys\n"
                            "if '--version' in sys.argv: print('QEMU emulator version fixture')\n"
                            "elif 'fatal' in __import__('os').environ.get('FIXTURE_MODE', ''):\n"
                            " print('qemu-system-aarch64: fatal: fixture', file=sys.stderr)\n"
                            " sys.exit(1)\n")
            fake.chmod(0o755)
            image, kernel, dtb = [directory / name for name in ("sd.img", "Image", "board.dtb")]
            for path in (image, kernel, dtb):
                path.write_bytes(b"fixture")
            environment = dict(os.environ, QEMU_SYSTEM_AARCH64=str(fake), QEMU_COPY_IMAGE="0",
                               QEMU_DTB_BLUETOOTH="1", KERNEL_IMAGE=str(kernel), DTB_IMAGE=str(dtb))
            log = directory / "qemu-run.log"
            for mode in ("normal", "fatal"):
                result = subprocess.run([str(ROOT / "board/cardputerzero/qemu/run-qemu.sh"), str(image)],
                                        env=dict(environment, FIXTURE_MODE=mode), capture_output=True)
                log.write_bytes(result.stdout + result.stderr)
                self.assertIn(b"run-qemu: version=", log.read_bytes())
                self.assertIn(b"run-qemu: sha256 ", log.read_bytes())
                errors = M.aggregate_errors([("run", log)], "smoke")
                self.assertEqual(len(errors), 0 if mode == "normal" else 1)
                self.assertEqual(result.returncode, 0 if mode == "normal" else 1)

    def scan(self, text, test="smoke", phase="run"):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "test.log"
            path.write_text(text)
            return M.aggregate_errors([(phase, path)], test)

    def test_empty_normal_and_multiple_errors(self):
        self.assertEqual(self.scan(""), [])
        self.assertEqual(self.scan("msd.fscmp: finished\n"), [])
        errors = self.scan("Kernel panic - not syncing\nqemu-system-aarch64: fatal\nI/O error, dev mmcblk0\n")
        self.assertEqual(len(errors), 3)
        self.assertFalse(any(item["expected"] for item in errors))

    def test_multiple_logs_keep_each_occurrence_without_combined_log_duplicates(self):
        with tempfile.TemporaryDirectory() as temporary:
            first, second = Path(temporary) / "host.log", Path(temporary) / "qemu-run.log"
            first.write_text("build failed\nbuild failed\nRequired file not found: missing\n")
            second.write_text("msd.fscmp: error=bad\n")
            errors = M.aggregate_errors([("host", first), ("run", second)], "smoke")
            self.assertEqual([(item["file"], item["line"]) for item in errors],
                             [("host.log", 1), ("host.log", 2), ("host.log", 3), ("qemu-run.log", 1)])

    def test_expected_errors_are_retained_and_scoped(self):
        text = ("msd.fscmp: expected_errors_begin kind=T6_corruption\n"
                "I/O error, dev dm-1\nmsd.fscmp: T6_READCHECK exit=3\n"
                "msd.fscmp: expected_errors_end kind=T6_corruption\n")
        self.assertTrue(all(item["expected"] for item in self.scan(text, "T6")))
        for test, phase in [("T6", "verify"), ("smoke", "run")]:
            self.assertTrue(any(not item["expected"] for item in self.scan(text, test, phase)))
        for line in ["Kernel panic", "msd.fscmp: error=bad", "I/O error, dev mmcblk0"]:
            errors = self.scan(text.replace("I/O error, dev dm-1", line), "T6")
            self.assertTrue(any(not item["expected"] for item in errors))
        self.assertTrue(any(not item["expected"] for item in self.scan(text + "I/O error, dev dm-1", "T6")))
        self.assertTrue(any(not item["expected"] for item in self.scan(text.split("msd.fscmp: expected_errors_end")[0], "T6")))

    def test_t1_negative_manifest_is_an_expected_measurement(self):
        errors = self.scan("msd.fscmp: expected_errors_begin kind=T1_replay\n"
                           "msd.fscmp: T1_MANIFEST_FAIL entry=1\n"
                           "msd.fscmp: expected_errors_end kind=T1_replay\n", "T1-negative")
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0]["expected"])

    def test_t1_printed_mount_and_fsck_diagnostics_are_scoped(self):
        text = ("msd.fscmp: expected_errors_begin kind=T1_replay\n"
                "msd.fscmp: T1_MOUNT_ERR entry=1 mount: wrong fs type\n"
                "msd.fscmp: T1_FSCK_ERR entry=1 unexpected filesystem error\n"
                "msd.fscmp: expected_errors_end kind=T1_replay\n")
        self.assertTrue(all(item["expected"] for item in self.scan(text, "T1-negative")))
        self.assertTrue(any(not item["expected"] for item in self.scan(text, "smoke")))
        errors = self.scan(text.replace("mount: wrong fs type", "I/O error, dev mmcblk0"), "T1-negative")
        self.assertTrue(any(not item["expected"] for item in errors))


class Processes(unittest.TestCase):
    def exercise(self, mode, stop="normal", test="smoke"):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            command = [sys.executable, str(V2 / "supervisor.py"), "run", "--grace", "0.15",
                       "--timeout", "3", str(directory), "run", test, sys.executable,
                       str(Path(__file__).with_name("fake-vm.py")), mode]
            with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
                try:
                    deadline = time.monotonic() + 5
                    while time.monotonic() < deadline:
                        path = directory / "qemu-run.log"
                        if path.exists() and "fake-ready" in path.read_text():
                            break
                        if process.poll() is not None:
                            break
                        time.sleep(0.01)
                    M.write_json(directory / "request-run.json", {"mode": stop})
                    stdout, stderr = process.communicate(timeout=6)
                finally:
                    if process.poll() is None:
                        process.kill()
                        process.wait()
                result = M.load_json(directory / "phase-run.json")
                return process.returncode, result, stdout + stderr + (directory / "qemu-run.log").read_bytes()

    def test_qmp_quit_reaps_normal_process_and_ignores_events(self):
        code, result, output = self.exercise("normal")
        self.assertEqual(code, 0, output)
        self.assertTrue(result["reaped"])
        self.assertTrue(result["qmp_quit"])
        self.assertEqual(result["fallback"], [])

    def test_nonzero_missing_marker_early_exit_and_fallback_fail(self):
        for mode in ("nonzero", "no-marker", "early", "hang", "reject"):
            with self.subTest(mode=mode):
                code, result, output = self.exercise(mode)
                self.assertNotEqual(code, 0, output)
                self.assertTrue(result["reaped"])
                if mode == "hang":
                    self.assertEqual(result["fallback"], ["SIGTERM", "SIGKILL"])

    def test_cut_allowed_only_in_planned_t2_phase(self):
        code, result, output = self.exercise("cut", "cut", "T2")
        self.assertEqual(code, 0, output)
        self.assertTrue(result["cut_intent"])
        self.assertEqual(result["returncode"], -signal.SIGKILL)
        self.assertNotEqual(self.exercise("normal", "cut")[0], 0)

    def test_late_log_error_survives_process_reaping(self):
        code, result, output = self.exercise("late-error")
        self.assertEqual(code, 0, output)
        self.assertTrue(result["marker"])
        self.assertIn(b"msd.fscmp: error=after_marker", output)
        self.assertFalse(M.phase_ok(dict(result, returncode=-9), "smoke", "run"))


class Matrix(unittest.TestCase):
    def test_result_without_saved_child_exit_is_incomplete(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "run"
            fixture(directory)
            M.finalize(directory, "smoke", 0)
            self.assertFalse(M.matrix_ok(directory / "summary.csv", 0))
            for payload in ("", "{", "{}", '{"status": null}', '{"status": 7}'):
                (directory / "matrix-child.json").write_text(payload)
                self.assertFalse(M.matrix_ok(directory / "summary.csv", 0))
            M.write_json(directory / "matrix-child.json", {"status": 0})
            self.assertTrue(M.matrix_ok(directory / "summary.csv", 0))

    def test_resume_reruns_published_result_without_saved_child_exit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runs = root / "runs"
            runs.mkdir()
            matrix = runs / "host-test"
            matrix.mkdir()
            (matrix / ".v2").write_text(M.SCHEMA + "\n")
            incomplete = runs / "host-test-smoke-E1-r1-123456"
            fixture(incomplete)
            M.finalize(incomplete, "smoke", 0)
            fake = root / "driver"
            fake.write_text(f"#!{sys.executable}\nimport os,runpy,sys\nfrom pathlib import Path\n"
                            f"suite=runpy.run_path({str(Path(__file__).resolve())!r})\n"
                            "d=Path(os.environ['QEMU_LOG_DIR'])/sys.argv[3]\n"
                            "suite['fixture'](d);suite['M'].finalize(d,sys.argv[2],0)\n")
            fake.chmod(0o755)
            plan = root / "plan.tsv"
            plan.write_text("E1\tsmoke\t1\n")
            result = subprocess.run([str(V2 / "fs-compare-matrix.sh"), "--matrix-id", "host-test",
                                     "--runs-dir", str(runs), "-j", "1", str(plan)],
                                    env=dict(os.environ, FS_COMPARE_V2_DRIVER=str(fake)),
                                    capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            with (matrix / "matrix-summary.csv").open() as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 1)
            self.assertNotEqual(rows[0]["run_id"], incomplete.name)
            self.assertTrue((incomplete / "result.json").exists())

    def test_child_nonzero_beats_ok_summary_and_cannot_pass_on_resume(self):
        for child_status in (0, 7):
            with self.subTest(child_status=child_status), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                fake = root / "driver"
                fake.write_text(f"#!{sys.executable}\n"
                                "import sys,os,importlib.util\nfrom pathlib import Path\n"
                                f"spec=importlib.util.spec_from_file_location('suite', {str(Path(__file__).resolve())!r})\n"
                                "suite=importlib.util.module_from_spec(spec);spec.loader.exec_module(suite)\n"
                                "d=Path(os.environ['QEMU_LOG_DIR'])/sys.argv[3]\n"
                                "suite.fixture(d);suite.M.finalize(d,sys.argv[2],0)\n"
                                f"sys.exit({child_status})\n")
                fake.chmod(0o755)
                plan = root / "plan.tsv"
                plan.write_text("E1\tsmoke\t1\n")
                command = [str(V2 / "fs-compare-matrix.sh"), "--matrix-id", "host-test",
                           "--runs-dir", str(root / "runs"), "-j", "1", str(plan)]
                environment = dict(os.environ, FS_COMPARE_V2_DRIVER=str(fake))
                for _attempt in range(2):
                    result = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=15)
                    self.assertEqual(result.returncode == 0, child_status == 0, result.stdout + result.stderr)
                with (root / "runs/host-test/matrix-summary.csv").open() as stream:
                    rows = list(csv.DictReader(stream))
                self.assertEqual(len(rows), 1 if child_status == 0 else 2)
                self.assertTrue(all(row["status"] == ("ok" if child_status == 0 else "fail:child_exit_7") for row in rows))


class Preflight(unittest.TestCase):
    def test_registry_covers_dispatch_recovery_selection_and_planned_pairs(self):
        paths, configs, variants = P.registry()
        self.assertEqual(len(configs), 20)
        for config, test, _ in P.generated("all", 1):
            P.validate(config, test)
        for invalid in (("E99", "T1"), ("P999", "T3"), ("E1", "not-a-path")):
            with self.assertRaises(ValueError):
                P.validate(*invalid)
        required = P.requirements([("P001", "T1", "7")])
        keys = {(config, row["path"]) for config, row in required}
        self.assertTrue(all((config, row["path"]) in keys for config in configs for row in paths))
        self.assertIn(("P001", "T1"), keys)
        self.assertIn(("E1", "T1-sample-selected"), keys)
        self.assertTrue(all(row["phases"] == "run,verify" for _, row in required
                            if row["test"] in ("T2", "T3")))
        for config, variant in variants.items():
            self.assertEqual((config, "T6") in keys, variant["tests"] == "std+T6")
        self.assertTrue(all((config, "smoke") in keys for config in variants))

    def test_repetitions_and_legacy_plan_are_distinct_from_attempts(self):
        rows = P.generated("phase2", 3)
        self.assertNotIn("smoke", {row[1] for row in P.generated("all", 3)})
        self.assertEqual([row for row in rows if row[:2] == ("P001", "T3")],
                         [("P001", "T3", str(number)) for number in (1, 2, 3)])
        for count in (0, -1):
            with self.assertRaises(ValueError):
                P.generated("all", count)
        with tempfile.TemporaryDirectory() as temporary:
            plan = Path(temporary) / "plan"
            original = "# fixed repetitions\nE1\tT1-sample\t7\nE1\tT1-sample\t42\n"
            plan.write_text(original)
            self.assertEqual(P.read_plan(plan), [("E1", "T1-sample", "7"), ("E1", "T1-sample", "42")])
            self.assertEqual(plan.read_text(), original)
            for bad in ("", "E1\tT1\n", "E1\tT1\t0\n", "E1\tT1\t1\nE1\tT1\t1\n"):
                plan.write_text(bad)
                with self.assertRaises(ValueError):
                    P.read_plan(plan)
        result = subprocess.run([str(V2 / "fs-compare-matrix.sh"), "--generate-plan"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual({line.split("\t")[2] for line in result.stdout.splitlines()}, {"1", "2", "3"})

    def environment_fixture(self, directory):
        files = {
            ".config": (V2 / "fs-compare.buildroot.fragment").read_text(),
            "build/linux-custom/.config": (V2 / "fs-compare.fragment").read_text(),
            "build/linux-custom/include/config/kernel.release": "6.12-fixture\n",
            "build/busybox-1/.config": "CONFIG_CHATTR=y\nCONFIG_BB_SYSCTL=y\n",
            **{f"images/{name}": "fixture" for name in
               ("Image", "bcm2710-rpi-3-b.dtb", "rootfs.squashfs", "sdcard.img")},
            **{f"fs-compare/{name}": "fixture" for name in
               ("replay-log", "replay-log.provenance", "fs-compare-workload")},
            **{name: "#!/bin/sh\nexit 0\n" for name in
               ("host/bin/unsquashfs", "host/bin/mksquashfs", "host/sbin/sfdisk", "fake-tool")},
        }
        for name, content in files.items():
            target = directory / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
            target.chmod(0o755)

    def test_environment_uses_real_configs_hashes_versions_and_fails_before_image(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.environment_fixture(directory)
            runner = mock.Mock(return_value=subprocess.CompletedProcess([], 0, "fixture version\n", ""))
            with mock.patch.object(P.shutil, "which", return_value=str(directory / "fake-tool")), \
                    mock.patch.dict(os.environ, {}, clear=True):
                env = P.environment(directory, runner)
                self.assertEqual(env["kernel_release"], "6.12-fixture")
                self.assertIn(str(directory / "build/linux-custom/.config"), env["files"])
                self.assertIn("version", env["tools"]["qemu"])
                with mock.patch.object(P.shutil, "which", return_value=None):
                    with self.assertRaisesRegex(ValueError, "host tool missing"):
                        P.environment(directory, runner)
                runner.return_value = subprocess.CompletedProcess([], 1, "", "bad version")
                with self.assertRaisesRegex(ValueError, "version probe failed"):
                    P.environment(directory, runner)
                runner.side_effect = subprocess.TimeoutExpired("tool", 15)
                with self.assertRaises(subprocess.TimeoutExpired):
                    P.environment(directory, runner)
                for relative in ("build/linux-custom/.config", "build/busybox-1/.config", ".config"):
                    original = (directory / relative).read_text()
                    (directory / relative).write_text("CONFIG_BLK_DEV_LOOP=m\n")
                    with self.assertRaisesRegex(ValueError, "built-in config missing"):
                        P.environment(directory, runner)
                    (directory / relative).write_text(original)
                (directory / "images/Image").unlink()
                runner.side_effect = None
                runner.return_value = subprocess.CompletedProcess([], 0, "version\n", "")
                with self.assertRaises(FileNotFoundError):
                    P.environment(directory, runner)
            self.assertFalse((directory / "run").exists())

    def test_exact_unsupported_only_and_negative_controls(self):
        signatures = {
            "P012": "EXT4-fs (loop0): can't mount with journal_async_commit in data=ordered mode",
            "P085": "mkfs.btrfs: unrecognized option '--enable-simple-quota'",
            "P101": "BTRFS error (device loop0): cannot disable free-space-tree",
            "P133": "cryptsetup: Option --iv-large-sectors is not allowed with luksFormat action.",
        }
        for config, line in signatures.items():
            records = [{"text": line, "expected": False}]
            self.assertEqual(P.unsupported(config, records, line, 1), [line])
            self.assertIsNone(P.unsupported("P001", records, line, 1))
            self.assertIsNone(P.unsupported(config, records, line, 137))
            for error in ("timeout", "ENOSPC", "No space left on device", "EIO", "I/O error",
                          "Kernel panic", "environment_error", "tool_version_error"):
                self.assertIsNone(P.unsupported(config, records, line + "\n" + error, 1))
            self.assertIsNone(P.unsupported(config, records + [{"text": "unrelated failure"}], line, 1))
            self.assertIsNone(P.unsupported(config, [{"text": line, "expected": True}], line, 1))
            self.assertIsNone(P.unsupported(config, [], "", 1))

    def test_gate_coverage_reuse_hash_changes_errors_and_all_excluded(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            path = {"path": "T3", "test": "T3", "phases": "run,verify", "points": "none"}
            required = [("E1", path)]
            env = {"kernel_release": "fixture", "files": {"kernel": "first"}}
            calls = []

            def probe(attempt, config, selected, _env, _output):
                calls.append(config)
                evidence = attempt / "evidence"
                evidence.write_text("raw fixture")
                return dict(config=config, path=selected["path"], test=selected["test"],
                            phases=["run", "verify"], ok=True, child_status=0, run=str(attempt),
                            evidence={str(evidence): P.digest(evidence)}, unsupported=None)

            inspect = lambda _output: env
            rows = [("E1", "T3", "7")]
            with mock.patch.object(P, "requirements", return_value=required):
                P.gate(rows, directory, directory, probe, inspect)
                P.gate(rows, directory, directory, probe, inspect)
                self.assertEqual(len(calls), 1)
                approved = directory / "approved.json"
                P.write_json(approved, env)
                P.gate(rows, directory, directory, probe, inspect, expected_environment=approved)
                with self.assertRaisesRegex(ValueError, "approved manifest"):
                    P.gate(rows, directory, directory, probe,
                           lambda _output: dict(env, tools={"qemu": {"version": "changed"}}),
                           expected_environment=approved)
                self.assertEqual(len(calls), 1)
                self.assertEqual((directory / "effective-plan.tsv").read_bytes(), P.plan_bytes(rows))
                cert = P.load_json(directory / "smoke-coverage.json")
                fingerprint = cert["identity"]
                self.assertFalse(P.covered({**cert, "probes": []}, fingerprint, required))
                cert["probes"][0]["phases"] = ["run"]
                self.assertFalse(P.covered(cert, fingerprint, required))
                env["files"]["kernel"] = "changed"
                P.gate(rows, directory, directory, probe, inspect)
                self.assertEqual(len(calls), 2)
                cert = P.load_json(directory / "smoke-coverage.json")
                Path(next(iter(cert["probes"][0]["evidence"]))).write_text("changed raw log")
                P.gate(rows, directory, directory, probe, inspect)
                self.assertEqual(len(calls), 3)
                P.gate([("E1", "T3", "8")], directory, directory, probe, inspect)
                self.assertEqual(len(calls), 4)

                def fail_probe(*args):
                    return dict(probe(*args), ok=False)

                with self.assertRaisesRegex(ValueError, "main run not started"):
                    P.gate(rows, directory / "failed", directory, fail_probe, inspect)
                with self.assertRaisesRegex(ValueError, "environment missing"):
                    P.gate(rows, directory / "missing", directory, probe,
                           mock.Mock(side_effect=ValueError("environment missing")))

                def exclude(*args):
                    return dict(probe(*args), ok=False, unsupported=["known unsupported"])

                with self.assertRaisesRegex(ValueError, "nothing to run"):
                    P.gate(rows, directory / "excluded", directory, exclude, inspect)
                self.assertEqual((directory / "excluded/effective-plan.tsv").read_bytes(), b"")
                self.assertEqual(len(P.load_json(directory / "excluded/excluded-options.json")["options"]), 1)

    def test_probe_provenance_and_late_error_are_not_confused(self):
        with tempfile.TemporaryDirectory() as temporary:
            log = Path(temporary) / "qemu-run.log"
            log.write_text("msd.fscmp: environment_dm_target=error            v1.5.0\n"
                           "msd.fscmp: environment_ok kernel=fixture\n"
                           "msd.fscmp: finished\nKernel panic: fixture\n")
            records = M.aggregate_errors([("run", log)], "smoke")
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["category"], "kernel-fatal")

    def test_known_unsupported_allows_only_evidenced_abort_sigterm(self):
        line = "mkfs.btrfs: unrecognized option '--enable-simple-quota'"
        phase = dict(reaped=True, mode="abort", error=None, returncode=0,
                     fallback=["SIGTERM"], stop_pid=123)
        diagnostic = "qemu-system-aarch64: terminating on signal 15 from pid 123 (python3)"

        def records(state, message=diagnostic):
            return [{"category": "diagnostic", "phase": "run", "text": line},
                    {"category": "process", "phase": "run",
                     "text": "phase status: " + json.dumps(state)},
                    {"category": "qemu", "phase": "run", "text": message}]

        self.assertEqual(P.unsupported("P085", records(phase), line + "\n" + diagnostic, 1), [line])
        for changes in ({"error": "timeout"}, {"fallback": ["SIGTERM", "SIGKILL"]},
                        {"stop_pid": 999}, {"reaped": False}, {"mode": "normal"},
                        {"returncode": -9}):
            self.assertIsNone(P.unsupported("P085", records(dict(phase, **changes)), line, 1))
        self.assertIsNone(P.unsupported("P085", records(phase, diagnostic.replace("15", "9")), line, 1))

    def test_guest_environment_probe_normal_missing_module_kernel_tool_and_empty_cases(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            binaries = root / "bin"
            binaries.mkdir()
            proc = root / "proc"
            proc.mkdir()
            filesystems = "ext4\nf2fs\nbtrfs\n"
            (proc / "filesystems").write_text(filesystems)
            tools = ("uname", "dmsetup", "mkfs.ext4", "mkfs.f2fs", "mkfs.btrfs", "btrfs",
                     "cryptsetup", "integritysetup", "e2fsck", "fsck.f2fs", "fscryptctl")
            for name in tools:
                script = binaries / name
                script.write_text(
                    f"#!{sys.executable}\nimport os,sys\n"
                    f"name={name!r}\n"
                    "if os.environ.get('FAIL_TOOL') == name: sys.exit(1)\n"
                    "if os.environ.get('EMPTY_TOOL') == name: sys.exit(0)\n"
                    "if name == 'uname': print(os.environ.get('KERNEL','fixture'))\n"
                    "elif name == 'dmsetup' and sys.argv[1] == 'targets':\n"
                    " print(os.environ.get('TARGETS','log-writes v1.0.0\\nsnapshot v1.0.0\\n"
                    "crypt v1.0.0\\nintegrity v1.0.0\\nerror v1.5.0'))\n"
                    "else: print('fixture version 1')\n")
                script.chmod(0o755)
            environment = dict(os.environ, PATH=str(binaries) + os.pathsep + os.environ["PATH"])
            command = ["sh", str(V2 / "fs-compare-probe"), "fixture", str(proc)]
            result = subprocess.run(command, env=environment, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("environment_ok kernel=fixture", result.stdout)
            for changes, reason in (({"KERNEL": "wrong"}, "kernel="),
                                    ({"TARGETS": "log-writes v1.0.0"}, "dm_target=snapshot"),
                                    ({"TARGETS": ""}, "dm_target="),
                                    ({"FAIL_TOOL": "mkfs.f2fs"}, "version=f2fs-mkfs"),
                                    ({"EMPTY_TOOL": "mkfs.f2fs"}, "version=f2fs-mkfs"),
                                    ({"FAIL_TOOL": "dmsetup"}, "dm_targets")):
                result = subprocess.run(command, env=dict(environment, **changes),
                                        capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("environment_error_" + reason, result.stdout)
                self.assertNotIn("environment_ok", result.stdout)
            for content in ("ext4\nbtrfs\n", ""):
                (proc / "filesystems").write_text(content)
                result = subprocess.run(command, env=environment, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("environment_error_filesystem=", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
