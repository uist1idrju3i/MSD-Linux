import os
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import run


class RunnerTests(unittest.TestCase):
    def test_record_paths_inside_and_outside_repository(self):
        self.assertEqual(run.record_path(run.ROOT / "runs/image"), "runs/image")
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "image"
            self.assertEqual(run.record_path(image), str(image.resolve()))

    def test_path_validation_precedes_image_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(run, "record_path", side_effect=ValueError("invalid path")):
                with patch.object(run, "command") as command:
                    with self.assertRaisesRegex(ValueError, "invalid path"):
                        run.prepare(root, root / "runs")
                    command.assert_not_called()
                    self.assertFalse((root / "runs").exists())

    def test_prepare_outside_repository_records_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "output"
            (output / "images").mkdir(parents=True)
            for name in ["sdcard.img", "bcm2710-rpi-3-b.dtb"]:
                (output / "images" / name).write_bytes(b"input")

            def command(args, log):
                if Path(args[0]).name == "unsquashfs":
                    (Path(args[-2]) / "etc/init.d").mkdir(parents=True)
                elif Path(args[0]).name == "mksquashfs":
                    Path(args[2]).write_bytes(b"squash")
                elif args[0] == "cp":
                    shutil.copyfile(args[-2], args[-1])
                else:
                    self.assertEqual(args[0], "dd")

            table = {"partitiontable": {"partitions": [{"start": 1, "size": 100}] * 7}}
            runs = root / "new/runs"
            with patch.object(run, "command", side_effect=command):
                with patch.object(run.subprocess, "check_output", return_value=json.dumps(table)):
                    run.prepare(output, runs)
            inputs = json.loads((runs / "prepared/inputs.json").read_text())
            image = runs / "prepared/sdcard.img"
            self.assertEqual(inputs[str(image.resolve())], run.sha(image))
            self.assertEqual(len(inputs), 5)

    def test_prepare_creates_missing_parents_and_rejects_existing_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runs = root / "new" / "runs"
            with patch.object(run, "command", side_effect=RuntimeError("stop before tools")) as command:
                with self.assertRaisesRegex(RuntimeError, "stop before tools"):
                    run.prepare(root, runs)
                self.assertTrue((runs / "prepared").is_dir())
                command.assert_called_once()
                with self.assertRaises(FileExistsError):
                    run.prepare(root, runs)
                command.assert_called_once()

    def test_inherited_drive_override_is_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.dict(os.environ, {"QEMU_DRIVE_FILE": "/unrelated/image"}):
                with patch.object(run.subprocess, "Popen", side_effect=RuntimeError("captured")) as launch:
                    with self.assertRaisesRegex(RuntimeError, "captured"):
                        run.boot(root, root, "A", "boot")
            env = launch.call_args.kwargs["env"]
            self.assertNotIn("QEMU_DRIVE_FILE", env)
            self.assertEqual(env["QEMU_COPY_IMAGE"], "1")
            self.assertEqual(launch.call_args.args[0][-1], str(root / "prepared/sdcard.img"))


if __name__ == "__main__":
    unittest.main()
