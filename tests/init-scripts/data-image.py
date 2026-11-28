#!/usr/bin/env python3
"""Exercise sparse generation and the complete p7 image check."""

import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("data_image", ROOT / "board/cardputerzero/data-image.py")
IMAGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(IMAGE)


class DataImage(unittest.TestCase):
    def test_layout_and_failure_boundaries(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            IMAGE.prepare(directory)
            data = directory / "data.zero"
            self.assertEqual(data.stat().st_size, 536870912)
            self.assertLess(data.stat().st_blocks * 512, data.stat().st_size)
            config = (directory / "genimage.cfg").read_text()
            self.assertNotIn("@MSD_DATA_INITIAL_BYTES@", config)
            self.assertNotIn("ext4", config)
            self.assertIn("size = 536870912", config)
            disk = directory / "sdcard.img"
            end = 2424832 * 512
            with disk.open("wb") as stream:
                stream.truncate(end)
            table = ("label: dos\nunit: sectors\n\n"
                     "start=8192, size=32768, type=c\n"
                     "start=40960, size=131072, type=c\n"
                     "start=172032, size=131072, type=c\n"
                     "start=303104, size=2121728, type=5\n"
                     "start=311296, size=524288, type=83\n"
                     "start=843776, size=524288, type=83\n"
                     "start=1376256, size=1048576, type=83\n")
            subprocess.run(["sfdisk", str(disk)], input=table.encode(), check=True,
                           stdout=subprocess.DEVNULL)
            IMAGE.check(disk)
            for offset in (1376256 * 512, end - 1):
                with disk.open("r+b") as stream:
                    stream.seek(offset)
                    stream.write(b"x")
                with self.assertRaisesRegex(ValueError, "nonzero"):
                    IMAGE.check(disk)
                with disk.open("r+b") as stream:
                    stream.seek(offset)
                    stream.write(b"\0")
            with disk.open("r+b") as stream:
                stream.truncate(end - 1)
            with self.assertRaisesRegex(ValueError, "ends before"):
                IMAGE.check(disk)
            with self.assertRaises(subprocess.CalledProcessError):
                IMAGE.check(directory / "missing.img")


if __name__ == "__main__":
    unittest.main()
