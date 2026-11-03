#!/usr/bin/env python3
"""Capture repeatable CI regressions without overwriting evidence or benchmarking CI."""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import time


ROOT = Path(__file__).resolve().parents[2]
INPUTS = (".github/actions/setup-dev-image/action.yml", ".github/actionlint.yaml",
          ".github/scripts/dev-image-cache.py", ".github/scripts/run-host-tests.py",
          ".github/workflows/build.yml", ".github/workflows/lint.yml",
          ".github/workflows/agent-docs.yml", "docker/msd-dev",
          "tests/check-ci-cache/run.py", "tests/check-ci-scope/run.py", "tests/check-ci-cache/record.py")


def hashes() -> dict[str, str]:
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in INPUTS}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--check-docker-archive", action="store_true")
    args = parser.parse_args()
    if args.repetitions < 5:
        parser.error("At least five repetitions are required")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    before = hashes()
    metadata = {"base_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
                "inputs": before, "host": platform.platform(), "repetitions": args.repetitions,
                "image": subprocess.check_output(["docker", "image", "inspect", "msd-dev:local",
                                                   "--format", "{{.Id}} {{.Os}}/{{.Architecture}}"], text=True).strip()}
    (args.output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    rows = []
    def capture(name: str, command: list[str]) -> None:
        start = time.monotonic()
        log = args.output_dir / f"{name}.log"
        with log.open("w") as stream:
            process = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, cwd=ROOT)
        rows.append({"run_id": name, "status": "passed" if process.returncode == 0 else "failed",
                     "exit_code": process.returncode, "seconds": round(time.monotonic() - start, 6),
                     "log_sha256": hashlib.sha256(log.read_bytes()).hexdigest(),
                     "command": json.dumps(command)})
        print(name, process.returncode, flush=True)
    for repeat in range(1, args.repetitions + 1):
        for suite in ("check-ci-cache", "check-ci-scope"):
            capture(f"{suite}-{repeat}", ["docker/msd-dev", "python3", f"tests/{suite}/run.py"])
    capture("tools", ["docker/msd-dev", "bash", "-c",
                      'python3 --version; actionlint -version; shellcheck --version; zizmor --version; '
                      'git --version; for tool in python3 actionlint shellcheck zizmor; do '
                      'sha256sum "$(command -v "$tool")"; done'])
    if args.check_docker_archive:
        tag = subprocess.check_output(["docker/msd-dev", "tag"], text=True).strip()
        for operation in ("save", "load"):
            capture(f"docker-{operation}", ["python3", ".github/scripts/dev-image-cache.py", operation,
                                            "--directory", str(args.output_dir / "archive"), "--tag", tag])
    if hashes() != before:
        raise RuntimeError("Inputs changed during trials; preserve this attempt and rerun separately")
    with (args.output_dir / "results.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return int(any(row["status"] != "passed" for row in rows))


if __name__ == "__main__":
    raise SystemExit(main())
