import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import run


class RunnerTests(unittest.TestCase):
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
