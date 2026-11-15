#!/usr/bin/env python3
"""機能判定をboottimeの妥当性と分離する。"""
import argparse
import hashlib
import json
from pathlib import Path
import re


def verdict(serial, harness, expected, status, monitor):
    ready = "MSD/Linux ready" in serial
    corruption = bool(re.search(r"device-mapper:\s*verity:[^\n]*(?:is corrupted|verification failed)|"
                                r"dm-verity device corrupted", serial))
    panic = "Kernel panic" in serial
    verity_panic = bool(re.search(r"Kernel panic[^\n]*dm-verity", serial))
    restart = bool(re.search(r"reboot: Restarting system", serial))
    new_boot = len(re.findall(r"(?:^|\n)(?:\[\s*[\d.]+\]\s*)?Linux version ", serial)) > 1
    signal = bool(re.search(r"terminating on signal|terminated-after", serial + harness))
    natural_exit = "QEMU exited before the boot marker and login prompt" in harness
    passed = False
    if expected == "ready":
        passed = ready and not (corruption or panic or restart or new_boot) and status == 0 and monitor == "none"
    elif expected == "verity-panic":
        passed = (corruption and verity_panic and not ready and not restart and not new_boot
                  and monitor == "panic-observed" and status in (1, 143))
    elif expected == "verity-restart":
        passed = (corruption and (restart or new_boot) and not ready and not panic
                  and monitor == "none" and not signal and status in (0, 1)
                  and natural_exit)
    else:
        raise ValueError("unknown expected mode: " + expected)
    return dict(version=2, functional_pass=bool(passed), expected=expected,
                exit_status=status, monitor=monitor, ready=ready, corruption=corruption,
                panic=panic, verity_panic=verity_panic, restart=restart, new_boot=new_boot,
                host_signal=signal, natural_exit=natural_exit)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--serial", type=Path, required=True)
    parser.add_argument("--harness", type=Path, required=True)
    parser.add_argument("--expected", choices=["ready", "verity-panic", "verity-restart"], required=True)
    parser.add_argument("--exit-status", type=int, required=True)
    parser.add_argument("--monitor", required=True)
    args = parser.parse_args()
    serial = args.serial.read_bytes() if args.serial.exists() else b""
    harness = args.harness.read_bytes()
    result = verdict(serial.decode(errors="replace"), harness.decode(errors="replace"),
                     args.expected, args.exit_status, args.monitor)
    result.update(serial_sha256=hashlib.sha256(serial).hexdigest(),
                  harness_sha256=hashlib.sha256(harness).hexdigest())
    print(json.dumps(result, sort_keys=True))
    return 0 if result["functional_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
