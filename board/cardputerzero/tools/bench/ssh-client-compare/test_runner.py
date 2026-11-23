#!/usr/bin/env python3
"""Host-only checks; no build or VM is started."""

import gzip
import csv
import json
import os
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

import build
import inventory

from build import VARIANTS, overrides
from inventory import configure_tokens, encode_multiline, unix_cache_value
from runtime import execute, initramfs, parse_config, parse_serial, prepare
from summarize import putty_protocol_ids
from summarize import summarize


class Runner(unittest.TestCase):
    def test_prepare_keeps_key_copies_and_archive_private_under_permissive_umask(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            out, reference = root / "out", root / "reference"
            out.mkdir(mode=0o755)
            (reference / "target/dev").mkdir(parents=True)
            (reference / "images").mkdir()
            (reference / "images/bcm2710-rpi-cm0.dtb").write_bytes(b"dtb")
            for name in ("client", "settings", "known-good", "known-wrong"):
                (out / name).write_bytes(b"test fixture")
            args = SimpleNamespace(out=out, reference=reference, build=root, variants=[], strace=None)
            previous = os.umask(0)
            try:
                with mock.patch("runtime.subprocess.run"):
                    prepare(args)
            finally:
                os.umask(previous)
            for path in (out, out / "root", out / "root/fixtures"):
                self.assertEqual(path.stat().st_mode & 0o777, 0o700)
            for name in ("client", "settings", "known-good", "known-wrong"):
                path = out / "root/fixtures" / name
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
                self.assertEqual(path.read_bytes(), b"test fixture")
            self.assertEqual((out / "initrd.gz").stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                prepare(args)

    def test_execute_keeps_generated_keys_and_settings_private_before_prepare_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            def run(command, **kwargs):
                if command[0] == "ssh-keygen":
                    path = Path(command[-1])
                    path.write_bytes(b"test private key")
                    path.with_suffix(".pub").write_text("ssh-ed25519 fixture\n")
                else:
                    raise RuntimeError("prepare failed")
            args = SimpleNamespace(out=out, reference=out, build=out, variants=[], repetitions=1, strace=None)
            previous = os.umask(0)
            try:
                with mock.patch("runtime.ROOT", Path("/")), mock.patch("runtime.subprocess.run", side_effect=run), \
                        mock.patch("runtime.subprocess.check_output", return_value="256 SHA256:fixture comment"):
                    with self.assertRaisesRegex(RuntimeError, "prepare failed"):
                        execute(args)
            finally:
                os.umask(previous)
            self.assertEqual(out.stat().st_mode & 0o777, 0o700)
            for name in ("client", "host", "wrong", "settings", "sshd.conf"):
                self.assertEqual((out / name).stat().st_mode & 0o777, 0o600)

    def test_sha_without_python311_file_digest_handles_empty_large_and_missing_files(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "payload"
            for data in (b"", b"abc", b"x" * (1024 * 1024 + 1)):
                path.write_bytes(data)
                with mock.patch.object(build.hashlib, "file_digest", None, create=True):
                    self.assertEqual(build.sha(path), build.hashlib.sha256(data).hexdigest())
            with self.assertRaises(FileNotFoundError):
                build.sha(Path(directory) / "missing")

    def test_dropbear_small_is_an_unchanged_default_not_an_explicit_override(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            recipe = root / "vendor/buildroot/package/dropbear"
            recipe.mkdir(parents=True)
            (recipe / "Config.in").write_text("config BR2_PACKAGE_DROPBEAR\n\tbool\n"
                                             "config BR2_PACKAGE_DROPBEAR_SMALL\n\tbool\n\tdefault y\n")
            (recipe / "dropbear.mk").write_text("")
            source = root / "build/dropbear/buildroot/build/dropbear-fixture"
            (source / "src").mkdir(parents=True)
            for name in ("configure", "src/default_options.h", "src/cli-runopts.c"):
                (source / name).write_text("")
            with mock.patch.object(inventory, "ROOT", root), mock.patch.object(inventory, "VARIANTS", ("dropbear",)), \
                    mock.patch.object(inventory.subprocess, "check_output", return_value=""):
                rows, _ = inventory.collect(root / "build", None)
            rows = {row["option"]: row for row in rows}
            self.assertEqual(rows["BR2_PACKAGE_DROPBEAR_SMALL"]["upstream_default"], "y")
            self.assertEqual(rows["BR2_PACKAGE_DROPBEAR_SMALL"]["decision"], "不採用（明示変更せず）")
            self.assertEqual(rows["BR2_PACKAGE_DROPBEAR"]["decision"], "採用（比較条件の明示指定）")

    def test_unix_cache_does_not_supply_windows_declarations(self):
        cache = {"PUTTY_GSSAPI": "OFF"}
        self.assertEqual(unix_cache_value(Path("cmake/platforms/unix.cmake"), cache, "PUTTY_GSSAPI"), "OFF")
        self.assertEqual(unix_cache_value(Path("cmake/platforms/windows.cmake"), cache, "PUTTY_GSSAPI"),
                         "非対象platform（Unix build）")
        self.assertEqual(unix_cache_value(Path("cmake/setup.cmake"), {}, "missing"), "非対象platform")

    def test_config_preserves_repeated_values_and_ignores_incomplete_lines(self):
        result = parse_config("identityfile first\nidentityfile second\nport 22\nidentityfile\n")
        self.assertEqual(result, dict(identityfile=["first", "second"], port="22"))
        self.assertEqual(json.loads(encode_multiline("\n".join(result["identityfile"]))[5:]), "first\nsecond")
        self.assertEqual(parse_config(""), {})
        self.assertEqual(parse_config("identityfile\n"), {})
        with tempfile.TemporaryDirectory() as directory:
            build, measure, final = self.summary_fixture(Path(directory))
            with mock.patch("summarize.needed", return_value=[]):
                _, report = summarize(build, measure, [final], final)
            self.assertEqual(report["openssh_effective_config"]["identityfile"], ["first", "second"])

    def test_configure_tokens_preserve_case_and_complete_names(self):
        self.assertEqual(configure_tokens("  --with-Werror  --enable-FEATURE[=ARG]  --without-X"),
                         ["--with-Werror", "--enable-FEATURE", "--without-X"])
        self.assertEqual(configure_tokens(""), [])
        self.assertEqual(configure_tokens("text--not-an-option -h --"), [])
        with self.assertRaises(TypeError):
            configure_tokens(None)

    def summary_fixture(self, root, traced=True):
        build, measure, final = (root / name for name in ("build", "measure", "final"))
        for path in (build, measure, final):
            path.mkdir()
        with (measure / "results.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=("run_id", "variant", "repeat", "metric", "value", "unit", "valid", "note"))
            writer.writeheader()
            for variant in ("baseline", *VARIANTS):
                for repeat in range(1, 6):
                    writer.writerow(dict(run_id=f"{variant}-{repeat}", variant=variant,
                                         repeat=repeat, metric="squashfs", value=100,
                                         unit="byte", valid=1, note="sha256=fixture"))
        serial = []
        for variant in VARIANTS:
            work = build / variant
            (work / "root/usr/bin").mkdir(parents=True)
            name = {"openssh": "ssh", "dropbear": "dbclient", "putty": "plink"}[variant]
            (work / "root/usr/bin" / name).write_bytes(b"client")
            (work / "files.json").write_text(json.dumps([dict(path=f"usr/bin/{name}", bytes=6)]))
            (work / "dependencies.json").write_text('{}')
            shutil.copytree(work, measure / variant)
            for condition in ("good", "wrong"):
                for repeat in range(1, 6):
                    serial.extend((f"SSH_BEGIN {variant} {condition} {repeat}", "SSH_HOME_BEFORE",
                                   "0" * 64 + "  /root/key", "SSH_REMOTE_OK" if condition == "good" else
                                   "REMOTE HOST IDENTIFICATION HAS CHANGED", "SSH_HOME_AFTER",
                                   "0" * 64 + "  /root/key"))
                    if traced:
                        serial.extend(("SSH_TRACE_BEGIN", "SSH_TRACE_END"))
                    serial.append(f"SSH_RESULT {variant} {condition} {repeat} {0 if condition == 'good' else 1} 0")
        serial.extend(("SSH_CONFIG_BEGIN", "identityfile first", "identityfile second",
                       "SSH_CONFIG_END", "SSH_COMPARE_DONE"))
        (final / "serial.log").write_text("\n".join(serial))
        (final / "inputs.json").write_text('{}')
        (final / "process.json").write_text(json.dumps(dict(qmp_quit=True, returncode=0, fallback=[], error=None)))
        return build, measure, final

    def test_summary_uses_measured_payload_even_when_new_baseline_contains_files(self):
        for already_installed in (False, True):
            with self.subTest(already_installed=already_installed), tempfile.TemporaryDirectory() as directory:
                built, measure, final = self.summary_fixture(Path(directory))
                for tree, content in ((built, b"ssh-rsa\0"), (measure, b"ssh-ed25519\0")):
                    (tree / "putty/root/usr/bin/plink").write_bytes(content)
                    (tree / "putty/files.json").write_text(json.dumps([
                        dict(path="usr/bin/plink", bytes=len(content))]))
                path = built / "dropbear/files.json"
                original = json.loads(path.read_text())
                path.write_text(json.dumps([*original, dict(path="usr/lib/libcrypt.so.2", bytes=7)]))
                for tree in (built / "dropbear/root", measure / "dropbear/root"):
                    (tree / "usr/lib").mkdir()
                    (tree / "usr/lib/libcrypt.so.2").write_bytes(b"library")
                if already_installed:
                    (measure / "dropbear/files.json").write_text('[]')
                (measure / "dropbear/dependencies.json").write_text('{"libcrypt.so.2":"usr/lib/libcrypt.so.2"}')
                with (measure / "results.csv").open(newline="") as stream:
                    rows = list(csv.DictReader(stream))
                for row in rows:
                    if row["variant"] == "dropbear":
                        row["value"] = 104
                with (measure / "results.csv").open("w", newline="") as stream:
                    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                    writer.writeheader()
                    writer.writerows(rows)
                with mock.patch("summarize.needed", return_value=[]) as needed:
                    _, report = summarize(built, measure, [final], final)
                result = report["candidates"]["dropbear"]
                self.assertEqual(result["installed_added"], 0 if already_installed else 6)
                self.assertEqual(result["squashfs_delta"], 4)
                self.assertEqual(result["dependency_closure"], {"libcrypt.so.2": "usr/lib/libcrypt.so.2"})
                self.assertTrue(all(call.args[0].is_relative_to(measure) for call in needed.call_args_list))
                self.assertEqual(report["putty_binary_protocol_ids"]["hostkey"], ["ssh-ed25519"])

    def test_summary_rejects_failed_final_process_despite_complete_serial(self):
        with tempfile.TemporaryDirectory() as directory:
            build, measure, final = self.summary_fixture(Path(directory))
            for override in ({"returncode":7}, {"returncode":-9}, {"qmp_quit":False},
                             {"fallback":["TERM"]}, {"error":"late failure"}, {}):
                process = dict(qmp_quit=True, returncode=0, fallback=[], error=None)
                process.update(override)
                if not override:
                    process = {}
                (final / "process.json").write_text(json.dumps(process))
                with self.subTest(process=process), self.assertRaisesRegex(ValueError, "final runtime"):
                    summarize(build, measure, [final], final)

    def test_summary_retains_preparation_failure_and_rejects_missing_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            build, measure, final = self.summary_fixture(root)
            failed = root / "prepare-failed"
            failed.mkdir()
            evidence = '{"error":"FileNotFoundError: fixture"}'
            (failed / "failure.json").write_text(evidence)
            with mock.patch("summarize.needed", return_value=[]):
                rows, report = summarize(build, measure, [failed, final], final)
            row = next(row for row in rows if row["run_id"] == "prepare-failed/attempt")
            self.assertEqual((row["value"], row["valid"]), (0, 0))
            self.assertIn("FileNotFoundError: fixture", row["note"])
            self.assertEqual((failed / "failure.json").read_text(), evidence)
            self.assertEqual(report["final_process"]["returncode"], 0)
            (failed / "failure.json").unlink()
            with self.assertRaisesRegex(ValueError, "missing process/failure"):
                summarize(build, measure, [failed, final], final)

    def test_summary_distinguishes_missing_empty_and_incomplete_trace(self):
        for traced in (False, True):
            with self.subTest(traced=traced), tempfile.TemporaryDirectory() as directory:
                build, measure, final = self.summary_fixture(Path(directory), traced=traced)
                with mock.patch("summarize.needed", return_value=[]):
                    _, report = summarize(build, measure, [final], final)
                for variant in VARIANTS:
                    self.assertEqual(report["writable_opens"][variant], [] if traced else None)
                    self.assertEqual(report["trace_available"][variant]["observed"], 10 if traced else 0)
                if traced:
                    path = final / "serial.log"
                    path.write_text(path.read_text().replace("SSH_TRACE_END", "", 1))
                    with mock.patch("summarize.needed", return_value=[]), self.assertRaisesRegex(ValueError, "incomplete trace"):
                        summarize(build, measure, [final], final)

    def test_measure_from_rebases_payload_on_current_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reference, source, out = root / "reference", root / "source", root / "out"
            (reference / "target/usr/bin").mkdir(parents=True)
            (reference / "target/current").write_text("new baseline")
            (source / "openssh/root/usr/bin").mkdir(parents=True)
            (source / "openssh/root/obsolete").write_text("old baseline")
            (source / "openssh/root/usr/bin/ssh").write_bytes(b"ssh")
            (source / "openssh/files.json").write_text('[{"path":"usr/bin/ssh","bytes":3}]')
            (source / "openssh/dependencies.json").write_text('{}')

            def fake_run(command, *args, **kwargs):
                if Path(command[0]).name == "mksquashfs":
                    Path(command[2]).write_bytes(b"image")

            arguments = ["build.py", "--reference", str(reference), "--out", str(out),
                         "--measure-from", str(source), "--variants", "openssh", "--repetitions", "1"]
            with mock.patch("sys.argv", arguments), mock.patch.object(build, "ROOT", root), \
                    mock.patch.object(build.os, "nice"), mock.patch.object(build, "run", side_effect=fake_run), \
                    mock.patch.object(build, "needed", return_value=[]), \
                    mock.patch.object(build, "sha", return_value="0" * 64), \
                    mock.patch.object(build.subprocess, "check_output", return_value="commit"):
                build.main()
            self.assertTrue((out / "openssh/root/current").is_file())
            self.assertFalse((out / "openssh/root/obsolete").exists())
            self.assertEqual((out / "openssh/root/usr/bin/ssh").read_bytes(), b"ssh")
            self.assertEqual(json.loads((out / "openssh/files.json").read_text())[0]["bytes"], 3)

    def test_multiline_source_values_round_trip_without_losing_whitespace(self):
        value = "before\n  \n  after\n"
        self.assertEqual(json.loads(encode_multiline(value)[5:]), value)
        self.assertEqual(encode_multiline(""), "")
        self.assertEqual(encode_multiline("default"), "default")
        with self.assertRaises(TypeError):
            encode_multiline(None)

    def test_protocol_ids_handle_pooled_strings_and_empty_input(self):
        result = putty_protocol_ids(b"message ssh-ed25519\0aes128-ctr\0mlkem_decaps\0arcfour_setkey\0")
        self.assertEqual(result["hostkey"], ["ssh-ed25519"])
        self.assertEqual(result["cipher"], ["aes128-ctr"])
        self.assertEqual(result["kex"], [])
        self.assertTrue(all(not values for values in putty_protocol_ids(b"").values()))
        with self.assertRaises(TypeError):
            putty_protocol_ids(None)

    def serial(self):
        return ("SSH_BEGIN openssh good 1\nSSH_REMOTE_OK\nSSH_RESULT openssh good 1 0 0\n"
                "SSH_BEGIN openssh wrong 1\nREMOTE HOST IDENTIFICATION HAS CHANGED\n"
                "SSH_RESULT openssh wrong 1 255 0\nSSH_COMPARE_DONE\n")

    def test_normal_and_negative_control(self):
        self.assertEqual(parse_serial(self.serial(), ["openssh"], 1),
                         {("openssh", "good", 1): 0, ("openssh", "wrong", 1): 255})

    def test_missing_duplicate_or_unexpected_results(self):
        for text in ("", self.serial().replace("SSH_COMPARE_DONE", ""),
                     self.serial() + "SSH_RESULT openssh wrong 1 255 0\n",
                     self.serial().replace("SSH_RESULT openssh wrong 1 255 0", "")):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_serial(text, ["openssh"], 1)
        with self.assertRaises(ValueError):
            parse_serial(self.serial(), ["openssh"], 2)

    def test_error_status_late_panic_and_key_writes(self):
        for old, new in (("good 1 0 0", "good 1 7 0"),
                         ("wrong 1 255 0", "wrong 1 0 0"),
                         ("wrong 1 255 0", "wrong 1 124 0"),
                         ("good 1 0 0", "good 1 0 1"),
                         ("SSH_COMPARE_DONE", "SSH_COMPARE_DONE\nKernel panic"),
                         ("REMOTE HOST IDENTIFICATION HAS CHANGED", "network failure"),
                         ("SSH_REMOTE_OK", "debug: Sending command: echo SSH_REMOTE_OK")):
            with self.subTest(new=new), self.assertRaises(ValueError):
                parse_serial(self.serial().replace(old, new), ["openssh"], 1)

    def test_putty_explicit_host_key_rejection(self):
        text = self.serial().replace("openssh", "putty").replace("wrong 1 255 0", "wrong 1 1 0")
        text = text.replace("REMOTE HOST IDENTIFICATION HAS CHANGED", "FATAL ERROR: Host key not in manually configured list")
        self.assertEqual(parse_serial(text, ["putty"], 1)[("putty", "wrong", 1)], 1)

    def test_client_only_recipe_overrides(self):
        for variant, name in (("openssh", "ssh"), ("dropbear", "dbclient"), ("putty", "plink")):
            values = overrides(variant)
            self.assertIn(f"{variant.upper()}_INSTALL_INIT_SYSV=", values)
            self.assertTrue(values[0].endswith(f"/usr/bin/{name}"))
            self.assertNotIn("/usr/sbin/sshd", values[0])
        self.assertIn("OPENSSH_MAKE_OPTS=ssh", overrides("openssh"))
        self.assertIn("DROPBEAR_PROGRAMS=dbclient", overrides("dropbear"))
        self.assertIn("$(@D)/plink ", overrides("putty")[0])

    def test_initramfs_is_deterministic_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tree = root / "root"
            tree.mkdir()
            (tree / "dev").mkdir()
            (tree / "init").write_text("fixture\n")
            (tree / "link").symlink_to("init")
            for index in (1, 2):
                initramfs(tree, root / f"{index}.gz")
            self.assertEqual((root / "1.gz").read_bytes(), (root / "2.gz").read_bytes())
            with gzip.open(root / "1.gz") as stream:
                data = stream.read()
            self.assertTrue(data.startswith(b"070701"))
            for token in (b"dev/console\0", b"dev/null\0", b"TRAILER!!!\0", b"fixture\n"):
                self.assertIn(token, data)
            with self.assertRaises(FileExistsError):
                initramfs(tree, root / "1.gz")


if __name__ == "__main__":
    unittest.main()
