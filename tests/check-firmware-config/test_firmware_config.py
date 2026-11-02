import configparser
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class FirmwareConfigTests(unittest.TestCase):
    def test_default_selects_cut_down_firmware_automatically(self):
        config = configparser.ConfigParser(
            interpolation=None, inline_comment_prefixes=("#",), strict=False
        )
        with (ROOT / "board/cardputerzero/config.txt").open(encoding="utf-8") as source:
            config.read_file(source)

        self.assertEqual(config.get("all", "gpu_mem", fallback=None), "16")
        for section in config.sections():
            for option, value in config.items(section):
                with self.subTest(section=section, option=option):
                    self.assertNotIn(option, ("start_file", "fixup_file"))
                    if option.startswith("gpu_mem"):
                        self.assertEqual((section, option, value), ("all", "gpu_mem", "16"))


if __name__ == "__main__":
    unittest.main()
