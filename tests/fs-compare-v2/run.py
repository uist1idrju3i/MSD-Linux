#!/usr/bin/env python3
"""Host tests for the v2 judge, supervisor and matrix; no QEMU or network."""

import csv
import errno
import fcntl
import gzip
import io
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import tarfile
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
S = P.storage


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
    def test_boot_serial_fragments(self):
        first = "Re-reading the partition table failed."
        kernel = "[   16.000491] mmc1: Timeout waiting for hardware interrupt."
        continuation = ": Device or resource busy"
        self.assertEqual(list(M.boot_serial_lines([], lambda: True)), [])
        self.assertEqual(list(M.boot_serial_lines([first + kernel, continuation], lambda: True)),
                         [(1, kernel), (1, first + continuation)])
        self.assertEqual(list(M.boot_serial_lines([first + kernel, continuation], lambda: False)),
                         [(1, first + kernel), (2, continuation)])
        self.assertEqual(list(M.boot_serial_lines([first + kernel], lambda: True)),
                         [(1, kernel), (1, first)])
        self.assertEqual(list(M.boot_serial_lines(
            [first + kernel, "msd.fscmp: finished"], lambda: True)),
            [(1, kernel), (1, first), (2, "msd.fscmp: finished")])

    def test_real_inline_boot_fragments_are_judged_independently(self):
        text = "\n".join(gzip.decompress(
            (ROOT / "tests/fs-compare-v2/fixtures/raspi3b-first-run.log.gz").read_bytes()
        ).decode().splitlines())
        grow = "msd-data-grow: extending partition 7 to the end of /dev/mmcblk0\n"
        warning = "Re-reading the partition table failed.: Device or resource busy"
        kernel = "[   16.000491] mmc1: Timeout waiting for hardware interrupt."
        split = "Re-reading the partition table failed." + kernel + "\n: Device or resource busy"
        self.assertIn(grow + warning, text)
        modified = text.replace(grow + warning, grow + split)
        records = self.boot_scan(modified)
        self.assertEqual(sum(r["expected"] for r in records), 19)
        self.assertEqual(sum(not r["expected"] for r in records), 5)
        self.assertEqual(self.boot_scan(kernel), [])
        for fragment in ("unknown driver: failed", "Kernel panic", "Oops:", "BUG:", "EIO", "ENOSPC"):
            changed = modified.replace(kernel, "[   16.000491] " + fragment)
            self.assertTrue(any(not r["expected"] and fragment in r["text"]
                                for r in self.boot_scan(changed)))
        for changed in (modified.replace(": Device or resource busy", ": Input/output error"),
                        modified.replace(grow, "unrelated userspace operation\n"),
                        modified.replace("msd-data: setup synchronized / 初期設定の同期が完了しました。",
                                         "setup incomplete")):
            self.assertTrue(any(not r["expected"] and "Re-reading" in r["text"]
                                for r in self.boot_scan(changed)))
        self.assertTrue(any(not r["expected"] and "Re-reading" in r["text"]
                            for r in self.boot_scan(modified, "host")))
        self.assertTrue(any(not r["expected"] and "Re-reading" in r["text"]
                            for r in self.boot_scan(text + "\n" + split)))

    def boot_scan(self, text, phase="run"):
        # fixtureの起動logはQEMU 11.1.2・kernel 6.18.59-v8で記録した実測値。
        # 版条件は記録時の版を注入して照合する（生の記録を新版に書き換えない）。
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / f"qemu-{phase}.log"
            path.write_text(text)
            rules = M.load_json(V2 / "boot-diagnostics.json")
            rules["qemu"] = "QEMU emulator version 11.1.2"
            rules["kernel"] = "6.18.59-v8"
            with mock.patch.object(M, "load_json", return_value=rules):
                return M.aggregate_errors([(phase, path)], "smoke")

    def test_actual_boot_diagnostics_keep_camera_eio_and_unresolved_uart_fatal(self):
        text = gzip.decompress((ROOT / "tests/fs-compare-v2/fixtures/raspi3b-first-run.log.gz").read_bytes()).decode()
        for phase in ("run", "verify"):
            records = self.boot_scan(text, phase)
            self.assertEqual(len(records), 24)
            expected = [r for r in records if r["expected"]]
            self.assertEqual(len(expected), 19)
            self.assertTrue(all(r.get("source") and r.get("reason") for r in expected))
            fatal = [r for r in records if not r["expected"]]
            self.assertEqual(len(fatal), 5)
            self.assertTrue(all("cam1_regulator" in r["text"] or "bcm2835-aux-uart" in r["text"]
                                for r in fatal))

    def test_known_boot_entries_reject_near_misses_and_wrong_scope(self):
        text = gzip.decompress((ROOT / "tests/fs-compare-v2/fixtures/raspi3b-first-run.log.gz").read_bytes()).decode()
        records = self.boot_scan(text)
        expected = [r for r in records if r["expected"]]
        for row in expected:
            with self.subTest(line=row["text"]):
                changed = text.replace(row["text"], row["text"] + " unexpected", 1)
                self.assertTrue(any(not r["expected"] and r["text"].endswith(" unexpected")
                                    for r in self.boot_scan(changed)))
                self.assertFalse(self.boot_scan(row["text"])[0]["expected"])
                self.assertFalse(self.boot_scan(row["text"], "host")[0]["expected"])
        for prefix in ("run-qemu: machine=raspi3b", "run-qemu: version=QEMU emulator version 11.1.2",
                       "Linux version 6.18.59-v8", "Machine model: Raspberry Pi 3 Model B",
                       "msd.fscmp: SMOKE_PROFILE"):
            self.assertFalse(any(r["expected"] for r in self.boot_scan(text.replace(prefix, "unknown"))))
        line = next(r["text"] for r in expected if r["known_boot"] == "no-uefi")
        self.assertFalse(self.boot_scan(text + "\n" + line)[-1]["expected"])
        for suffix in (" EIO", " ENOSPC", " BUG: fatal", " Kernel panic", " Oops:"):
            self.assertFalse(self.boot_scan(text.replace(line, line + suffix, 1))[0]["expected"])

    def test_reread_busy_requires_known_grow_step_and_success(self):
        text = gzip.decompress((ROOT / "tests/fs-compare-v2/fixtures/raspi3b-first-run.log.gz").read_bytes()).decode()
        for modified in (
                text.replace("msd-data-grow: extending partition ", "unrelated: extending partition "),
                text.replace("msd-data: setup synchronized / 初期設定の同期が完了しました。", "setup incomplete"),
                text.replace("Device or resource busy", "Input/output error")):
            records = self.boot_scan(modified)
            self.assertTrue(any(not r["expected"] and "Re-reading" in r["text"] for r in records))
        records = self.boot_scan(text.replace("mmc1: Failed", "mmc0: Failed"))
        self.assertTrue(any(not r["expected"] and "mmc0: Failed" in r["text"] for r in records))
        self.assertEqual(self.boot_scan(""), [])

    def test_grow_reread_allows_kernel_interleaving_not_unknown_errors_or_userspace(self):
        text = gzip.decompress((ROOT / "tests/fs-compare-v2/fixtures/raspi3b-first-run.log.gz").read_bytes()).decode()
        grow = "msd-data-grow: extending partition 7 to the end of /dev/mmcblk0"
        led = "[   16.238832] platform leds: deferred probe pending: leds-gpio: Failed to get GPIO '/leds/led-act'"
        records = self.boot_scan(text.replace(grow, grow + "\n" + led))
        self.assertTrue(all(r["expected"] for r in records if "Re-reading" in r["text"]))
        for message in ("unrelated userspace operation", "[   16.238832] unknown driver: failed"):
            records = self.boot_scan(text.replace(grow, grow + "\n" + message))
            self.assertTrue(any(not r["expected"] and (
                "Re-reading" in r["text"] if "userspace" in message else r["text"] == message)
                                for r in records))

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


class Storage(unittest.TestCase):
    def test_resume_reserves_only_unfinished_verified_matrix_rows(self):
        with tempfile.TemporaryDirectory() as temporary, mock.patch.dict(os.environ, {}, clear=True):
            root = Path(temporary)
            matrix = root / "matrix"
            matrix.mkdir()
            source = root / "matrix-smoke-E1-r1-123"
            fixture(source)
            M.write_json(source / "matrix-child.json", dict(status=0))
            M.finalize(source, "smoke", 0)
            with mock.patch.object(S, "archive_root", return_value=root / "archives"):
                S.finish(source, "smoke", 0)
            rows = [("E1", "smoke", "1"), ("E1", "smoke", "2")]
            with mock.patch.object(P, "requirements", return_value=[]), \
                    mock.patch.object(S, "unpacked_size", return_value=1), \
                    mock.patch.object(S, "archive_root", return_value=root / "archives"), \
                    mock.patch.object(S, "filesystem", return_value=("same", 50 * S.GIB)), \
                    mock.patch.dict(os.environ, {"FSCMP_MATRIX_DIR": str(matrix),
                                                "FSCMP_MAX_ATTEMPTS": "2"}):
                P.gate(rows, root / "gate", root, inspect=lambda _: {})
            model = S.load_json(root / "gate/capacity.json")
            self.assertEqual(model["remaining_attempts"], 2)
            self.assertEqual(S.remaining_attempts(rows[:1], matrix, 2), 0)
            (source / S.STATE).write_text('{"complete": false}')
            self.assertEqual(S.remaining_attempts(rows, matrix, 2), 4)
            (matrix / "matrix-summary.csv").write_text(
                "repetition,run_id,config,test,status\n2,failed,E1,smoke,fail:final_judge\n")
            self.assertEqual(S.remaining_attempts(rows, matrix, 2), 3)
            groups = S.estimate(dict(output=root, temp=root, archive=root), 1, 0, 1, 1,
                                lambda _path: ("same", 5 * S.GIB))
            self.assertEqual(groups["same"]["estimate"], 0)
            self.assertEqual(groups["same"]["required"], 5 * S.GIB)

    def test_smoke_reuse_repetitions_and_maximum_attempts_feed_capacity(self):
        with tempfile.TemporaryDirectory() as temporary, mock.patch.dict(os.environ, {}, clear=True):
            root = Path(temporary)
            path = dict(path="smoke", test="smoke", phases="run", points="none")
            rows = [("E1", "smoke", "1"), ("E1", "smoke", "2")]

            def probe(attempt, config, selected, _env, _output):
                evidence = attempt / "raw"
                evidence.write_text("fixture")
                return dict(config=config, path=selected["path"], phases=["run"], ok=True,
                            unsupported=None, evidence={str(evidence): P.digest(evidence)})

            with mock.patch.object(P, "run_probe", probe), \
                    mock.patch.object(P, "requirements", return_value=[("E1", path)]), \
                    mock.patch.object(S, "prepare") as prepare, \
                    mock.patch.dict(os.environ, {"FSCMP_MAX_ATTEMPTS": "3"}):
                P.gate(rows, root, root, probe, lambda _: {})
                self.assertEqual(prepare.call_args.args[2], 7)
                self.assertEqual(prepare.call_args.kwargs["counts"]["smoke_probes"], 1)
                P.gate(rows, root, root, probe, lambda _: {})
                self.assertEqual(prepare.call_args.args[2], 6)
                self.assertEqual(prepare.call_args.kwargs["counts"]["smoke_probes"], 0)

    def test_context_archives_sources_generated_configs_command_and_environment(self):
        with tempfile.TemporaryDirectory() as temporary, mock.patch.dict(os.environ, {}, clear=True):
            root = Path(temporary)
            output = root / "output"
            Preflight().environment_fixture(output)
            runner = mock.Mock(return_value=subprocess.CompletedProcess([], 0, "version\n", ""))
            with mock.patch.object(P.shutil, "which", return_value=str(output / "fake-tool")):
                environment = P.environment(output, runner)
            env_file = root / "environment.json"
            S.write_json(env_file, environment)
            source = root / "run"
            source.mkdir()
            with mock.patch.dict(os.environ, {"FSCMP_ENVIRONMENT_FILE": str(env_file)}), \
                    mock.patch.object(S, "archive_root", return_value=root / "archives"):
                S.context(source, "E1", "T1-sample", "run", "7")
            self.assertTrue((source / "evidence/harness/run-qemu.sh").is_file())
            self.assertTrue((source / "evidence/harness/fs-compare-workload.c").is_file())
            self.assertEqual(len(list((source / "evidence/configs").iterdir())), 4)
            self.assertEqual(S.load_json(source / "evidence/command.json")["command"][-2:],
                             ["--points", "7"])
            self.assertEqual(S.load_json(source / "evidence/environment.json"), environment)

    def test_capacity_same_and_separate_filesystems_parallel_repetitions_retry_and_smoke(self):
        paths = dict(output="/out", temp="/temp", archive="/archive")
        separate = S.estimate(paths, 4, 2 * 3 * 2 + 5, 100, 200,
                              lambda path: (path, 1000 * S.GIB))
        shared = S.estimate(paths, 4, 17, 100, 200, lambda _path: ("same", 1000 * S.GIB))
        self.assertEqual(shared["same"]["estimate"], sum(row["estimate"] for row in separate.values()))
        self.assertEqual(shared["same"]["required"],
                         max((shared["same"]["estimate"] * 6 + 4) // 5, 5 * S.GIB))
        one = S.estimate(paths, 1, 17, 100, 200, lambda path: (path, 1000 * S.GIB))
        self.assertGreater(separate["/out"]["estimate"], one["/out"]["estimate"])
        self.assertEqual(separate["/archive"]["estimate"], one["/archive"]["estimate"])
        self.assertGreater(S.estimate(paths, 4, 18, 100, 200,
                           lambda path: (path, 1000 * S.GIB))["/archive"]["estimate"],
                           separate["/archive"]["estimate"])
        for key, value in (("jobs", 0), ("attempts", -1), ("rootfs", 0), ("limit", 0)):
            options = dict(jobs=1, attempts=1, rootfs=1, limit=1)
            options[key] = value
            with self.assertRaises(ValueError):
                S.estimate(paths, **options)

    def test_capacity_records_deficits_rechecks_and_credits_idempotently(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "capacity.json"
            model = dict(paths=dict(output=temporary, temp=temporary, archive=temporary),
                         jobs=2, attempts=10, rootfs=100, log_limit=200, completed=[])
            free = 1000 * S.GIB
            with mock.patch.object(S, "filesystem", side_effect=lambda _path: ("same", free)):
                S.capacity(path, model)
                free = 1
                with self.assertRaises(OSError) as raised:
                    S.capacity(path)
                self.assertEqual(raised.exception.errno, errno.ENOSPC)
                self.assertEqual(S.load_json(path)["filesystems"]["same"]["free"], 1)
                self.assertFalse((Path(temporary) / "deleted.log").exists())
                with mock.patch.dict(os.environ, {"FSCMP_CAPACITY_FILE": str(path)}):
                    S.credit(Path(temporary) / "run")
                    S.credit(Path(temporary) / "run")
                free = 1000 * S.GIB
                self.assertEqual(S.capacity(path)["remaining_attempts"], 9)
            for value in ("relative", "/tmp/archive", "/dev/shm/archive"):
                with self.assertRaises(ValueError):
                    S.persistent(value)

    def test_rootfs_listing_size_includes_metadata_and_rejects_empty_listing(self):
        runner = mock.Mock(return_value=subprocess.CompletedProcess([], 0,
            "drwxr-xr-x 0/0 0 2026-01-01 root\n-rwxr-xr-x 0/0 123 2026-01-01 root/tool\n", ""))
        self.assertEqual(S.unpacked_size(Path("/output"), runner), 123 + 2 * 65536)
        runner.return_value.stdout = ""
        with self.assertRaises(ValueError):
            S.unpacked_size(Path("/output"), runner)

    def archive_fixture(self, root):
        source = root / "run"
        (source / "build/rootfs").mkdir(parents=True)
        for name, data in {"host.log": b"raw\n", "empty.log": b"",
                           "build/tool.log": b"build raw\n", "build/events.jsonl": b"{}\n",
                           "build/rootfs/payload": b"unpacked",
                           "sdcard.img": b"image"}.items():
            (source / name).write_bytes(data)
            os.utime(source / name, ns=(1320000000123456789, 1320000000123456789))
        (source / "link").symlink_to("host.log")
        os.link(source / "host.log", source / "hardlink")
        os.mkfifo(source / "fifo")
        return source

    def test_archive_roundtrip_all_members_hash_size_mtime_type_and_cleanup(self):
        with tempfile.TemporaryDirectory() as temporary, mock.patch.dict(os.environ, {}, clear=True):
            root = Path(temporary)
            source = self.archive_fixture(root)
            original = S.inventory(source)
            receipt = S.archive_attempt(source, root / "archives")
            self.assertEqual(S.verify_archive(receipt["archive"], receipt["manifest_sha256"]), original)
            self.assertEqual((source / "host.log").read_bytes(), b"raw\n")
            self.assertEqual((source / "empty.log").stat().st_size, 0)
            self.assertEqual((source / "host.log").stat().st_mtime_ns, 1320000000123456789)
            self.assertEqual((source / "build/tool.log").read_bytes(), b"build raw\n")
            self.assertEqual((source / "build/events.jsonl").read_bytes(), b"{}\n")
            self.assertFalse((source / "sdcard.img").exists())
            self.assertFalse((source / "build/rootfs/payload").exists())
            S.archive_attempt(source, root / "archives")
            self.assertTrue(S.load_json(source / S.STATE)["cleaned"])

    def test_archive_preserves_and_verifies_hardlink_relations(self):
        with tempfile.TemporaryDirectory() as temporary, mock.patch.dict(os.environ, {}, clear=True):
            root = Path(temporary)
            source = self.archive_fixture(root)
            os.link(source / "empty.log", source / "empty-twin")
            receipt = S.archive_attempt(source, root / "archives")
            manifest = S.verify_archive(receipt["archive"], receipt["manifest_sha256"])
            rows = {row["path"]: row for row in manifest["entries"]}
            self.assertEqual(rows["host.log"]["type"], "hardlink")
            self.assertEqual(rows["host.log"]["link"], "hardlink")
            with tarfile.open(receipt["archive"]) as archive:
                self.assertTrue(archive.getmember("host.log").islnk())
                self.assertEqual(archive.extractfile("host.log").read(), b"raw\n")
                self.assertTrue(archive.getmember("empty.log").islnk())
                self.assertEqual(archive.extractfile("empty.log").read(), b"")
                archive.extractall(root / "restored", members=[
                    archive.getmember("hardlink"), archive.getmember("host.log")], filter="data")
            self.assertEqual((root / "restored/host.log").stat().st_ino,
                             (root / "restored/hardlink").stat().st_ino)
            (source / "host.log").unlink()
            (source / "host.log").write_bytes(b"raw\n")
            os.utime(source / "host.log", ns=(1320000000123456789, 1320000000123456789))
            with self.assertRaisesRegex(ValueError, "source changed"):
                S.archive_attempt(source, root / "archives")

    def test_hardlink_cleanup_can_remove_canonical_payload_but_preserves_log(self):
        with tempfile.TemporaryDirectory() as temporary, mock.patch.dict(os.environ, {}, clear=True):
            root = Path(temporary)
            source = self.archive_fixture(root)
            os.link(source / "build/rootfs/payload", source / "build/rootfs/z.log")
            S.archive_attempt(source, root / "archives")
            self.assertEqual((source / "build/rootfs/z.log").read_bytes(), b"unpacked")
            S.archive_attempt(source, root / "archives")

    def test_hardlink_canonical_order_is_shared_for_nested_and_sibling_paths(self):
        with tempfile.TemporaryDirectory() as temporary, mock.patch.dict(os.environ, {}, clear=True):
            root = Path(temporary)
            source = self.archive_fixture(root)
            (source / "build/a").mkdir()
            (source / "build/a/item.log").write_bytes(b"linked log\n")
            os.link(source / "build/a/item.log", source / "build/a.log")
            manifest = S.inventory(source)
            S.verify_source(source, manifest, cleaned=True)
            receipt = S.archive_attempt(source, root / "archives")
            S.verify_source(source, S.verify_archive(receipt["archive"]), cleaned=True)
            S.archive_attempt(source, root / "archives")
            self.assertEqual((source / "build/a.log").stat().st_ino,
                             (source / "build/a/item.log").stat().st_ino)

    def test_archive_verification_failure_enospc_and_resume_preserve_sources_and_partials(self):
        for error in (ValueError("corrupt"), OSError(errno.ENOSPC, "full"), KeyboardInterrupt()):
            with self.subTest(error=error), tempfile.TemporaryDirectory() as temporary, \
                    mock.patch.dict(os.environ, {}, clear=True):
                root = Path(temporary)
                source = self.archive_fixture(root)
                original = S.inventory(source)
                with mock.patch.object(S, "verify_archive", side_effect=error):
                    with self.assertRaises(type(error)):
                        S.archive_attempt(source, root / "archives")
                self.assertEqual(S.inventory(source), original)
                self.assertFalse(S.load_json(source / S.STATE)["complete"])
                partials = list((root / "archives").glob("*.partial"))
                self.assertEqual(len(partials), 1)
                S.archive_attempt(source, root / "archives")
                self.assertTrue(partials[0].exists())

    def test_archive_creation_enospc_and_changed_source_never_cleanup(self):
        with tempfile.TemporaryDirectory() as temporary, mock.patch.dict(os.environ, {}, clear=True):
            root = Path(temporary)
            source = self.archive_fixture(root)
            with mock.patch.object(S.tarfile, "open", side_effect=OSError(errno.ENOSPC, "full")):
                with self.assertRaises(OSError):
                    S.archive_attempt(source, root / "archives")
            self.assertTrue((source / "sdcard.img").exists())
            original_verify = S.verify_archive

            def change(*args):
                result = original_verify(*args)
                (source / "host.log").write_text("changed")
                return result

            with mock.patch.object(S, "verify_archive", side_effect=change):
                with self.assertRaisesRegex(ValueError, "source changed"):
                    S.archive_attempt(source, root / "archives")
            with self.assertRaisesRegex(ValueError, "source changed"):
                S.archive_attempt(source, root / "archives")
            self.assertTrue((source / "build/rootfs/payload").exists())
            with self.assertRaises(ValueError):
                S.archive_attempt(source, source / "nested")

    def test_corrupted_payload_and_member_set_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary, mock.patch.dict(os.environ, {}, clear=True):
            root = Path(temporary)
            source = self.archive_fixture(root)
            receipt = S.archive_attempt(source, root / "archives")
            path = receipt["archive"]
            with tarfile.open(path, "r:gz") as archive:
                members = [(member, archive.extractfile(member).read() if member.isfile() else None)
                           for member in archive.getmembers()]
            with tarfile.open(path, "w:gz") as archive:
                for member, data in members:
                    if member.name == "hardlink":
                        data = b"bad\n"
                    archive.addfile(member, io.BytesIO(data) if data is not None else None)
            with self.assertRaisesRegex(ValueError, "payload mismatch"):
                S.verify_archive(path, receipt["manifest_sha256"])
            with self.assertRaises(ValueError):
                S.archive_attempt(source, root / "archives")
            self.assertEqual((source / "host.log").read_bytes(), b"raw\n")

    def test_log_limit_watcher_fails_without_truncation(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary)
            self.assertIsNone(S.logs_over_limit(source, 4))
            (source / "host.log").write_bytes(b"0123456789")
            parent = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(20)"])
            try:
                result = subprocess.run([sys.executable, str(V2 / "storage.py"), "watch",
                                         str(source), str(parent.pid)],
                                        env=dict(os.environ, FSCMP_LOG_LIMIT_BYTES="4"),
                                        capture_output=True, text=True, timeout=5)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(parent.wait(timeout=5), -signal.SIGTERM)
            finally:
                if parent.poll() is None:
                    parent.terminate()
                    parent.wait()
            self.assertEqual((source / "host.log").read_bytes(), b"0123456789")
            self.assertEqual(S.load_json(source / "log-limit.json")["total"], 10)

    def test_every_attempt_is_archived_and_late_scan_and_unreaped_guards(self):
        with tempfile.TemporaryDirectory() as temporary, mock.patch.dict(os.environ, {}, clear=True):
            root = Path(temporary)
            for label, status, test in (("success", 0, "smoke"), ("failed", 1, "T1"),
                                        ("abort", 143, "smoke"), ("smoke", 0, "smoke"),
                                        ("excluded", 1, "smoke"), ("cut", 0, "T3")):
                source = root / label
                fixture(source, test)
                M.finalize(source, test, status)
                with mock.patch.object(S, "archive_root", return_value=root / "archives"):
                    self.assertTrue(S.finish(source, test, status)["complete"])
            source = root / "late"
            fixture(source)
            M.finalize(source, "smoke", 0)
            launcher = root / "launcher"
            launcher.write_text("qemu-system-aarch64: fatal after marker\n")
            with mock.patch.object(S, "archive_root", return_value=root / "archives"):
                S.finish(source, "smoke", 0, launcher)
            self.assertNotEqual(M.published(source / "summary.csv")["status"], "ok")
            self.assertIn("fatal after marker", (source / "errors.txt").read_text())
            source = root / "unreaped"
            fixture(source, reaped=False)
            with self.assertRaisesRegex(ValueError, "not proven reaped"):
                S.finish(source, "smoke", 1)
            self.assertFalse((source / S.STATE).exists())

    def test_cap_exceeded_and_incomplete_archive_cannot_publish_success(self):
        with tempfile.TemporaryDirectory() as temporary, mock.patch.dict(os.environ, {}, clear=True):
            root = Path(temporary)
            source = root / "limit"
            fixture(source)
            M.finalize(source, "smoke", 0)
            original = (source / "qemu-run.log").read_bytes()
            with mock.patch.object(S, "archive_root", return_value=root / "archives"), \
                    mock.patch.dict(os.environ, {"FSCMP_LOG_LIMIT_BYTES": "1"}):
                S.finish(source, "smoke", 0)
            self.assertNotEqual(M.published(source / "summary.csv")["status"], "ok")
            self.assertEqual((source / "qemu-run.log").read_bytes(), original)
            self.assertIn("log size cap", (source / "errors.txt").read_text())
            S.write_json(source / S.STATE, dict(complete=False))
            self.assertIsNone(M.published(source / "summary.csv"))
            self.assertTrue((source / "qemu-run.log").exists())


class Preflight(unittest.TestCase):
    def test_matrix_locks_before_shared_preflight_or_plan_read(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            matrix = root / "runs/same"
            matrix.mkdir(parents=True)
            (matrix / ".v2").write_text("fs-compare-v2/1\n")
            plan = root / "plan.tsv"
            plan.write_text("E1\tsmoke\t1\n")
            binary = root / "python3"
            marker = root / "gate-called"
            binary.write_text(
                f"#!{sys.executable}\nimport os,sys\nfrom pathlib import Path\n"
                f"if sys.argv[2] == 'gate': Path({str(marker)!r}).touch(); sys.exit(1)\n"
                f"os.execv({sys.executable!r}, [{sys.executable!r}, *sys.argv[1:]])\n")
            binary.chmod(0o755)
            environment = dict(os.environ, PATH=str(root) + os.pathsep + os.environ["PATH"])
            environment.pop("FS_COMPARE_V2_DRIVER", None)
            with (matrix / ".driver.lock").open("w") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                result = subprocess.run(
                    [str(V2 / "fs-compare-matrix.sh"), "--matrix-id", "same",
                     "--runs-dir", str(root / "runs"), str(plan)],
                    env=environment, capture_output=True, text=True, timeout=15)
            self.assertFalse(marker.exists(), "competing run reached the shared preflight")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("already running", result.stderr)

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

    def test_launcher_tools_and_boot_environment_invalidate_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.environment_fixture(directory)
            fdtput = directory / "host/bin/fdtput"
            fdtput.write_text("first")
            fdtput.chmod(0o755)
            runner = mock.Mock(return_value=subprocess.CompletedProcess([], 0, "version\n", ""))
            with mock.patch.object(P.shutil, "which", return_value=str(directory / "fake-tool")), \
                    mock.patch.dict(os.environ, {}, clear=True):
                baseline = P.identity(P.environment(directory, runner), [])
                for key in ("ROOT_DEVICE", "ROOT_FSTYPE", "TMPDIR", "BASH_ENV", "LD_PRELOAD"):
                    with mock.patch.dict(os.environ, {key: "changed"}):
                        self.assertNotEqual(P.identity(P.environment(directory, runner), []),
                                            baseline, key)
                fdtput.write_text("changed")
                self.assertNotEqual(P.identity(P.environment(directory, runner), []), baseline)
                self.assertIn("fdtput", P.environment(directory, runner)["tools"])
                fdtput.unlink()
                self.assertEqual(P.environment(directory, runner)["tools"]["fdtput"]["path"],
                                 str(directory / "fake-tool"))
                with mock.patch.object(P.shutil, "which", return_value=None):
                    with self.assertRaisesRegex(ValueError, "host tool missing"):
                        P.environment(directory, runner)

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


class LightSmoke(unittest.TestCase):
    def test_t1_replay_checks_full_profile_tail_not_last_fsync_marker(self):
        guest = (V2 / "fs-compare-guest").read_text()

        def function(name):
            return name + "()\n{\n" + guest.split("\n" + name + "()\n{\n", 1)[1].split("\n}\n", 1)[0] + "\n}\n"

        replay = function("replay_t1").split("\n\texpected_ack_count=", 1)[0] + "\n}\n"
        script = (function("prepare_w3_expected_file") + function("validate_w3_file") + replay
                  + '\nconsole() { :; }\ncreate_mark_map() { :; }\nwait_for_t1_log_end() { :; }\n'
                  + 'WORKLOAD=profile_query\nprofile_query() { echo "$COUNT"; }\nworkload_profile() { echo fixture; }\n'
                  + 'RUN_PATH=$1\nCOUNT=$3\nW3_RECORD_SIZE=128\nW3_SYNC_INTERVAL=50\nTEST=T1\n'
                  + 'replay_t1\n'
                  + 'prefix=$(printf "%s\\n" "$2" | awk -F - \'{ print ($4 + 0) * 128 }\')\n'
                  + 'hash=$(head -c "$prefix" "$W3_EXPECTED_FILE" | sha256sum | awk \'{ print $1 }\')\n'
                  + 'if validate_w3_file "$RUN_PATH/data.bin" "$hash" "$2"; then echo ok; '
                  + 'else echo "$w3_validation_detail"; fi\n')

        def records(count):
            return b"".join(f"{0:010d} {n:010d}\n".encode() + b"\0" + b" " * 105
                            for n in range(1, count + 1))

        cases = [
            (51, 50, records(51), "ok"),
            (51, 50, records(50), "ok"),
            (51, 50, b"", "file_shorter_than_prefix"),
            (51, 50, records(51)[:-1], "partial_record_tail"),
            (51, 50, records(51)[:-1] + b"x", "invalid_deterministic_tail"),
            (51, 50, records(52), "tail_exceeds_final_record"),
            (1000, 1000, records(1000), "ok"),
            (250, 250, records(250), "ok"),
            (250, 250, records(251), "tail_exceeds_final_record"),
        ]
        for count, synced, data, expected in cases:
            with self.subTest(count=count, expected=expected), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary)
                marker = f"w3-record-000-{synced:04d}"
                (directory / "T1-markers.tsv").write_text(f"1\tW3/append.log\thash\t1\t1\t{marker}\n")
                (directory / "data.bin").write_bytes(data)
                result = subprocess.run(["sh", "-eu", "-c", script, "fixture", temporary,
                                         marker, str(count)], text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), expected)

    def test_probe_space_normal_zero_negative_and_error(self):
        with mock.patch.object(S, "filesystem", return_value=("device", 90)):
            self.assertEqual(P.probe_space(Path("."), ("device", 100))["used_delta_bytes"], 10)
            self.assertEqual(P.probe_space(Path("."), ("device", 90))["used_delta_bytes"], 0)
            self.assertEqual(P.probe_space(Path("."), ("device", 80))["used_delta_bytes"], -10)
            with self.assertRaisesRegex(ValueError, "filesystem changed"):
                P.probe_space(Path("."), ("other", 100))
        with mock.patch.object(S, "filesystem", side_effect=OSError("unavailable")):
            with self.assertRaises(OSError):
                P.probe_space(Path("."), ("device", 100))

    def test_profile_normal_empty_invalid_and_environment_isolation(self):
        profile = P.smoke_profile
        data = profile.load()
        self.assertEqual(profile.logical_bytes(data), 84352)
        self.assertIn("SMOKE_W3_RECORDS=51", profile.render("shell"))
        self.assertIn("#define SMOKE_W4_BYTES 65536U", profile.render("header"))
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "profile.json"
            for content in ("", "{}", json.dumps(dict(data, w3_records=50)),
                            json.dumps(dict(data, w1_files=True)),
                            json.dumps(dict(data, unknown=1)),
                            json.dumps(dict(data, archive_mode="full"))):
                path.write_text(content)
                with self.assertRaises(ValueError):
                    profile.load(path)
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                with profile.context():
                    self.assertEqual(S.log_limit(), 8388608)
                    raise RuntimeError("failed probe")
            self.assertNotIn("FSCMP_SMOKE", os.environ)
            self.assertEqual(S.log_limit(), 268435456)

    def test_private_workload_preserves_sync_rename_tail_and_exact_small_w4(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "smoke-profile.h").write_text(P.smoke_profile.render("header"))
            binary = root / "workload"
            subprocess.run(["cc", "-O2", "-Wall", "-Wextra", "-Werror", "-std=c11",
                            f"-I{root}", str(V2 / "fs-compare-workload.c"), "-lcrypto", "-o", str(binary)],
                           capture_output=True, text=True, check=True)
            for size, files, updates, records, large in (("smoke", 2, 2, 51, 65536),
                                                        ("t1-reduced", 50, 25, 250, 8388608),
                                                        ("full", 200, 100, 1000, 33554432)):
                work = root / size
                work.mkdir()
                manifest = root / f"{size}.tsv"
                result = subprocess.run([str(binary), "workload", str(work), str(manifest), "-",
                                         "--workload-size", size], capture_output=True, text=True,
                                        timeout=30, check=True)
                self.assertIn(f"W3_records={records}", result.stdout)
                query = subprocess.run([str(binary), "w3-records", size],
                                       capture_output=True, text=True, check=True)
                self.assertEqual(query.stdout.strip(), str(records))
                self.assertEqual(len(list((work / "W1").iterdir())), files)
                self.assertEqual((work / "W2/target.dat").stat().st_size, 2048)
                self.assertEqual((work / "W3/append.log").stat().st_size, records * 128)
                self.assertEqual((work / "W4/large.bin").stat().st_size, large)
                with manifest.open() as stream:
                    rows = list(csv.DictReader(stream, delimiter="\t"))
                self.assertEqual(sum(row["event"] == "atomic_update" for row in rows), updates)
                self.assertEqual(sum(row["event"] == "batch_fsync" for row in rows), records // 50)
            for arguments in ([], ["workload", str(root / "bad"), str(root / "bad.tsv"), "-",
                                    "--workload-size", "unknown"]):
                self.assertNotEqual(subprocess.run([str(binary), *arguments], capture_output=True).returncode, 0)

    def test_shared_evidence_images_hash_only_metadata_dedup_and_corruption(self):
        with tempfile.TemporaryDirectory() as temporary, mock.patch.dict(os.environ, {}, clear=True):
            root = Path(temporary)
            source = Storage().archive_fixture(root)
            image = P.digest(source / "sdcard.img")
            with P.smoke_profile.context():
                state = S.archive_attempt(source, root / "archives")
            manifest = S.verify_archive(state["archive"], state["manifest_sha256"])
            entries = {row["path"]: row for row in manifest["entries"]}
            self.assertEqual(entries["sdcard.img"]["sha256"], image)
            self.assertEqual(entries["host.log"]["type"], "hardlink")
            self.assertEqual(entries["link"]["link"], "host.log")
            self.assertEqual(entries["fifo"]["type"], "fifo")
            self.assertFalse((root / "archives/objects" / image).exists())
            with tarfile.open(state["archive"]) as archive:
                self.assertEqual(archive.getnames(), [S.MANIFEST])
            S.verify_source(source, manifest, cleaned=True)
            self.assertFalse((source / "sdcard.img").exists())
            self.assertTrue((source / "host.log").exists())
            count = len(list((root / "archives/objects").iterdir()))
            second = Storage().archive_fixture(root / "second")
            with P.smoke_profile.context():
                S.archive_attempt(second, root / "archives")
            self.assertEqual(len(list((root / "archives/objects").iterdir())), count)
            payload = root / "archives/objects" / entries["build/rootfs/payload"]["sha256"]
            original = payload.read_bytes()
            payload.write_bytes(b"tampered")
            with self.assertRaises(ValueError):
                S.verify_archive(state["archive"], state["manifest_sha256"])
            payload.write_bytes(original)
            payload.unlink()
            with self.assertRaises(ValueError):
                S.archive_attempt(source, root / "archives")

    def test_shared_archive_failure_and_cleanup_resume_fail_closed(self):
        import smoke_storage
        with tempfile.TemporaryDirectory() as temporary, mock.patch.dict(os.environ, {}, clear=True):
            root = Path(temporary)
            source = Storage().archive_fixture(root)
            with P.smoke_profile.context(), mock.patch.object(smoke_storage, "store", side_effect=OSError(errno.ENOSPC, "full")):
                with self.assertRaises(OSError):
                    S.archive_attempt(source, root / "archives")
            self.assertTrue((source / "sdcard.img").exists())
            self.assertFalse(S.load_json(source / S.STATE)["complete"])
            with mock.patch.object(S, "cleanup_payload", side_effect=OSError("cleanup interrupted")):
                with self.assertRaises(OSError):
                    S.archive_attempt(source, root / "archives")
            self.assertTrue(S.load_json(source / S.STATE)["complete"])
            self.assertTrue((source / "sdcard.img").exists())
            S.archive_attempt(source, root / "archives")
            self.assertTrue(S.load_json(source / S.STATE)["cleaned"])

    def test_capacity_light_mixed_and_credit_preserves_normal_reservations(self):
        paths = dict(output="/out", temp="/temp", archive="/archive")
        probe = lambda _: ("same", 100000 * S.GIB)
        normal = S.estimate(paths, 1, 851, S.GIB, 268435456, probe)["same"]["required"]
        light = S.estimate(paths, 1, 851, S.GIB, 268435456, probe, smoke=851)["same"]["required"]
        mixed = S.estimate(paths, 1, 852, S.GIB, 268435456, probe, smoke=851)["same"]["required"]
        self.assertLess(light, 100 * S.GIB)
        self.assertGreater(normal, 8000 * S.GIB)
        self.assertGreater(mixed, light + 8 * S.GIB)
        with self.assertRaises(ValueError):
            S.estimate(paths, 1, 1, 1, 1, probe, smoke=2)

    def test_profile_missing_wrong_phase_and_stale_logical_count_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            marker = f"msd.fscmp: SMOKE_PROFILE sha256={P.smoke_profile.fingerprint()}\n"
            for phase in ("run", "verify"):
                (root / f"qemu-{phase}.log").write_text(marker)
            self.assertTrue(P.profile_evidence("smoke", root, ["run", "verify"], marker))
            self.assertFalse(P.profile_evidence("T5", root, ["run"], marker))
            self.assertFalse(P.profile_evidence("T7", root, ["run"], marker + "T7_FINISHED filesystem=ext4 bytes=4294967296"))
            (root / "qemu-verify.log").write_text("")
            self.assertFalse(P.profile_evidence("smoke", root, ["run", "verify"], marker))

    def test_partial_coverage_resume_and_smoke_only_does_not_reserve_main(self):
        with tempfile.TemporaryDirectory() as temporary, mock.patch.dict(os.environ, {}, clear=True):
            root = Path(temporary)
            path = dict(path="smoke", test="smoke", phases="run", points="none")
            calls = []
            fail = True

            def probe(attempt, config, selected, _env, _output):
                calls.append(config)
                evidence = attempt / config
                evidence.write_text(config)
                return dict(config=config, path=selected["path"], phases=["run"],
                            ok=not (fail and config == "E2"), unsupported=None,
                            evidence={str(evidence): P.digest(evidence)})

            with mock.patch.object(P, "requirements", return_value=[("E1", path), ("E2", path)]), \
                    mock.patch.object(P, "run_probe", probe), mock.patch.object(S, "prepare") as prepare:
                rows = [("E1", "smoke", "1")]
                with self.assertRaisesRegex(ValueError, "smoke failed"):
                    P.gate(rows, root, root, probe, lambda _: {}, parameters={"smoke_only": True})
                self.assertEqual(prepare.call_args.kwargs["counts"]["remaining_main_attempts"], 0)
                fail = False
                P.gate(rows, root, root, probe, lambda _: {}, parameters={"smoke_only": True})
                self.assertEqual(calls, ["E1", "E2", "E2"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
