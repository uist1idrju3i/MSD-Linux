#!/usr/bin/env python3
"""SHA-256と実際のFEC復号をveritysetupで対照検査する。"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    dest = args.destination.resolve()
    dest.mkdir()
    tool = dest / "verityfmt"
    subprocess.run(["cc", "-O2", "-Wall", "-Wextra", "-o", str(tool),
                    str(ROOT / "board/cardputerzero/tools/dm-verity/verityfmt.c")], check=True)
    image = dest / "sha256.img"
    image.write_bytes(bytes(range(256)) * (4096 * 732 // 256))
    params = dest / "params.env"
    with (dest / "format.log").open("w") as log:
        subprocess.run([str(tool), "--hash", "sha256", "--fec-roots", "8", "--salt", "00" * 32,
                        "--no-superblock", "--params-file", str(params), str(image)],
                       check=True, stdout=log, stderr=subprocess.STDOUT)
    p = dict(line.split("=", 1) for line in params.read_text().splitlines())
    cmd = ["veritysetup", "verify", "--no-superblock", "--hash=sha256",
           "--data-blocks=" + p["data_blocks"], "--hash-offset=" + p["hash_offset"],
           "--salt=" + p["salt"]]
    results = []
    for name, fec, expected in [("clean", False, 0), ("corrupt-without-fec", False, 1),
                                ("corrupt-with-fec", True, 0)]:
        if name == "corrupt-without-fec":
            with image.open("r+b") as f:
                f.seek(123)
                value = f.read(1)[0]
                f.seek(123)
                f.write(bytes([value ^ 255]))
        invocation = cmd + (["--fec-device=" + str(image), "--fec-roots=8",
                             "--fec-offset=" + p["fec_area_offset"]] if fec else [])
        invocation += [str(image), str(image), p["root_hash"]]
        with (dest / (name + ".log")).open("w") as log:
            status = subprocess.run(invocation, stdout=log, stderr=subprocess.STDOUT).returncode
        results.append(dict(name=name, command=invocation, status=status))
        if (status == 0) != (expected == 0):
            raise RuntimeError("unexpected verification result: " + name)
    results.append(dict(formatter_sha256=hashlib.file_digest(tool.open("rb"), "sha256").hexdigest(),
                        version=subprocess.check_output(["veritysetup", "--version"], text=True).strip()))
    (dest / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    print("ok - veritysetup: SHA-256 clean accepted, corrupt rejected without FEC, decoded with FEC")


if __name__ == "__main__":
    main()
