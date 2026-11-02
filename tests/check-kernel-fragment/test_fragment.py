import subprocess
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
CHECK = ROOT / "board/cardputerzero/tools/check-kernel-fragment.sh"


class FragmentTest(unittest.TestCase):
    def run_check(self, fragment, config, code=0):
        with tempfile.TemporaryDirectory() as tmp:
            f, c = Path(tmp) / "fragment", Path(tmp) / ".config"
            f.write_text(fragment)
            c.write_text(config)
            result = subprocess.run([str(CHECK), str(f), str(c)], capture_output=True, text=True)
            self.assertEqual(code, result.returncode, result.stderr)
            return result.stderr

    def test_types_and_disabled_default(self):
        config = 'CONFIG_Y=y\nCONFIG_M=m\nCONFIG_S="words with spaces"\nCONFIG_H=0x10\n'
        self.run_check(config + "# CONFIG_N is not set", config)

    def test_mismatch_and_missing_enabled(self):
        self.run_check("CONFIG_X=y\nCONFIG_M=m\n", "CONFIG_X=m\n", 1)

    def test_conflicting_duplicate(self):
        error = self.run_check("CONFIG_X=y\n# CONFIG_X is not set\n", "# CONFIG_X is not set\n", 1)
        self.assertIn("duplicate CONFIG_X=n (line 1 requested y)", error)

    def test_redundant_duplicate(self):
        self.run_check("CONFIG_X=y\nCONFIG_X=y\n", "CONFIG_X=y\n", 1)

    def test_usage_and_unreadable_input(self):
        for args in ([], ["/missing/fragment", "/missing/config"]):
            self.assertEqual(2, subprocess.run([str(CHECK), *args], capture_output=True).returncode)

    def test_repository_fragment_is_unambiguous(self):
        fragment = ROOT / "board/cardputerzero/linux.fragment"
        result = subprocess.run([str(CHECK), str(fragment), str(fragment)], capture_output=True)
        self.assertEqual(0, result.returncode, result.stderr)


if __name__ == "__main__":
    unittest.main()
