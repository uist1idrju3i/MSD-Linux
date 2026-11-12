#!/usr/bin/env python3
"""Run independent host suites in one development container with bounded concurrency."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import os
from pathlib import Path
import signal
import subprocess
import time


ROOT = Path(__file__).resolve().parents[2]
SUITES = (
    "msd-update", "version-info", "init-scripts", "msd-hwinfo", "msd-data-grow",
    "qemu-log-check", "powerfail-log", "msd-dev", "release-signing",
)


def run_suite(name: str, command: list[str], directory: Path, timeout: float,
              cwd: Path = ROOT) -> dict[str, str | int | float]:
    start = time.monotonic()
    with (directory / f"{name}.log").open("w") as log:
        try:
            process = subprocess.Popen(command, cwd=cwd, stdout=log,
                                       stderr=subprocess.STDOUT, start_new_session=True)
            code = process.wait(timeout=timeout)
            status = "passed" if code == 0 else "failed"
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
            code, status = 124, "timeout"
            log.write("\nHost test suite timed out.\n")
        except OSError as error:
            code, status = 127, "error"
            log.write(f"\nCould not start suite: {error}\n")
    return {"suite": name, "status": status, "exit_code": code,
            "seconds": round(time.monotonic() - start, 6)}


def run(suites: list[tuple[str, list[str]]], directory: Path, jobs: int,
        timeout: float, cwd: Path = ROOT) -> list[dict[str, str | int | float]]:
    directory.mkdir(parents=True, exist_ok=False)
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        futures = [pool.submit(run_suite, name, command, directory, timeout, cwd)
                   for name, command in suites]
        results = [future.result() for future in futures]
    with (directory / "results.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=("suite", "status", "exit_code", "seconds"))
        writer.writeheader()
        writer.writerows(results)
    for result in results:
        print(f'::group::{result["suite"]}: {result["status"]}', flush=True)
        print((directory / f'{result["suite"]}.log').read_text(errors="replace"), end="", flush=True)
        print("::endgroup::", flush=True)
        print("=host-test=\t" + "\t".join(str(value) for value in result.values()), flush=True)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--timeout", type=float, default=180)
    args = parser.parse_args()
    if not 1 <= args.jobs <= len(SUITES) or not 0 < args.timeout <= 300:
        parser.error("Invalid concurrency or timeout")
    results = run([(name, [f"tests/{name}/run.sh"]) for name in SUITES],
                  args.output_dir, args.jobs, args.timeout)
    return int(any(result["status"] != "passed" for result in results))


if __name__ == "__main__":
    raise SystemExit(main())
