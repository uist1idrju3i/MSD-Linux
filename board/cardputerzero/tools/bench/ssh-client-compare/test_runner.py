#!/usr/bin/env python3
"""Host-only checks; no build or VM is started."""

import gzip
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import build

from build import overrides
from inventory import encode_multiline
from runtime import initramfs, parse_serial
from summarize import putty_protocol_ids


class Runner(unittest.TestCase):
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
