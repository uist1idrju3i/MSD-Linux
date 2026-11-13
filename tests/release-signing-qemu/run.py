#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "acceptance", ROOT / "board/cardputerzero/tools/bench/release-signing-qemu/run.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class EvidenceParser(unittest.TestCase):
    def fixture(self):
        text = "ec181b24375d93e884e05888d8348900fd1bc6405e225696716dc9feeb7f1f42\n1794526865\n"
        for part in [3, 6]:
            for label in ["before", "tampered", "unsigned", "signed"]:
                text += f"SNAP {label} p{part} " + "a" * 64 + "\n"
                count = 10 if label == "signed" else 0
                text += f"STAT {label} p{part} 0 0 0 0 0 0 {count} 0 0 0 0\n"
        text += "RESULT tampered 1\nRESULT unsigned 1\nRESULT signed 0\n"
        text += "STATE before absent\nSTATE tampered absent\nSTATE unsigned absent\nSTATE signed 3\n"
        text += "PAYLOAD rootfs 1eaa81c3cd3dfb1c6c458122f8d0cfa504f76725055bd60cf46f4fd51ead0d4a\n"
        text += "PAYLOAD boot 1d00199d1b9977efc739a26fab9a92ae39af4af595bf963c205ff6eb6154c234\n"
        return text + "ACCEPTANCE_DONE a\n"

    def test_normal(self):
        probe.validate(self.fixture(), "a")

    def test_empty_and_missing(self):
        for text in ["", self.fixture().replace("ACCEPTANCE_DONE a", ""),
                     self.fixture().replace("STATE signed 3", "")]:
            with self.assertRaises(ValueError):
                probe.validate(text, "a")

    def test_negative_mutations(self):
        for text in [self.fixture().replace("RESULT signed 0", "RESULT signed 1"),
                     self.fixture().replace("SNAP tampered p6 a", "SNAP tampered p6 b"),
                     self.fixture().replace("STAT unsigned p3 0 0 0 0 0 0 0", "STAT unsigned p3 0 0 0 0 0 0 1")]:
            with self.assertRaises(ValueError):
                probe.validate(text, "a")

    def test_b_identity(self):
        text = "ec181b24375d93e884e05888d8348900fd1bc6405e225696716dc9feeb7f1f42\n1794526865\n"
        with self.assertRaises(ValueError):
            probe.validate(text + "ACCEPTANCE_DONE b", "b")
        probe.validate(text + "slot=B partition=3 tryboot=1\nACCEPTANCE_DONE b", "b")


if __name__ == "__main__":
    unittest.main()
