#!/usr/bin/env python3
"""Append one result row to the preregistered S21 CSV."""

import csv
import sys
from pathlib import Path


HEADER = (
    "run_id",
    "condition",
    "trial",
    "image_variant",
    "rootfs_sha256",
    "sdcard_sha256",
    "sdcard_after_sha256",
    "dtb_sha256",
    "cmdline",
    "qemu_watchdog",
    "ready",
    "ready_seconds",
    "sysctl_readbacks",
    "running_sysctl",
    "serial_check_exit",
    "ab_exit_status",
    "powerfail_exit_status",
    "powerfail_status",
    "powerfail_target_delay_seconds",
    "powerfail_gpio_low_to_kill_seconds",
    "powerfail_event",
    "powerfail_sysrq_u_remount",
    "powerfail_remount_from_event_seconds",
    "powerfail_marker_after_reboot",
    "powerfail_fsck_exit_status",
    "powerfail_fs_recovery",
    "powerfail_firstboot_wall_seconds",
    "powerfail_reboot_verify_wall_seconds",
    "powerfail_total_wall_seconds",
    "panic_triggered",
    "panic_message",
    "reboot_message",
    "marker_to_reset_seconds",
    "reset_source",
    "second_boot_ready",
    "ramoops_registration",
    "pstore_mount_status",
    "pstore_files",
    "ramoops_record_sysrq",
    "ramoops_record_panic",
    "valid",
    "criteria_result",
    "log_sha256",
    "note",
)


def main() -> int:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} CSV [column=value ...]", file=sys.stderr)
        return 2
    csv_path = Path(sys.argv[1])
    row = dict.fromkeys(HEADER, "")
    for argument in sys.argv[2:]:
        if "=" not in argument:
            print(f"Expected column=value: {argument}", file=sys.stderr)
            return 2
        key, value = argument.split("=", 1)
        if key not in row:
            print(f"Unknown CSV column: {key}", file=sys.stderr)
            return 2
        row[key] = value
    if not row["run_id"] or not row["condition"]:
        print("run_id and condition are required", file=sys.stderr)
        return 2

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    exists = csv_path.exists() and csv_path.stat().st_size > 0
    with csv_path.open("a", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=HEADER, lineterminator="\n")
        if exists:
            with csv_path.open("r", encoding="utf-8", newline="") as source:
                actual_header = next(csv.reader(source), [])
            if tuple(actual_header) != HEADER:
                print(f"Unexpected CSV header in {csv_path}", file=sys.stderr)
                return 1
        else:
            writer.writeheader()
        writer.writerow(row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
