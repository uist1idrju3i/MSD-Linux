#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd -P)"
OUTPUT_DIR="${OUTPUT_DIR:-${REPO_ROOT}/output}"
IMAGES_DIR="${OUTPUT_DIR}/images"
LOG_ROOT="${QEMU_LOG_DIR:-${REPO_ROOT}/output/qemu-logs/watchdog}"
WORK_ROOT="${LOG_ROOT}/work"
BASE_IMAGE="${IMAGES_DIR}/sdcard.img"
ROOTFS="${IMAGES_DIR}/rootfs.squashfs"
KERNEL="${KERNEL_IMAGE:-${IMAGES_DIR}/Image}"
QEMU_MACHINE="${QEMU_MACHINE:-raspi3ap}"
CSV_FILE="${QEMU_WATCHDOG_CSV:-${LOG_ROOT}/watchdog.csv}"
CURRENT_PID=""
LOGGER_PID=""
TEST_TEMPLATE=""
SMOKE=0
RUNS=5
MODE=""
CSV_OVERRIDE=""
PROTOCOL_VERSION=v2

case "$QEMU_MACHINE" in
	raspi3b)
		default_dtb=bcm2710-rpi-3-b.dtb
		;;
	raspi3ap)
		default_dtb=bcm2710-rpi-cm0.dtb
		;;
	*)
		printf 'Unsupported QEMU_MACHINE: %s\n' "$QEMU_MACHINE" >&2
		exit 2
		;;
esac
BASE_DTB="${DTB_IMAGE:-${IMAGES_DIR}/${default_dtb}}"

usage() {
	printf 'Usage: %s [--smoke | --experiment | --mode MODE [--runs N]] [--csv PATH]\n' "$0" >&2
}

# shellcheck disable=SC2329
terminate_current() {
	if [[ -n "$CURRENT_PID" ]]; then
		if kill -0 "$CURRENT_PID" 2>/dev/null; then
			kill -KILL "$CURRENT_PID" 2>/dev/null || true
		fi
		wait "$CURRENT_PID" 2>/dev/null || true
		CURRENT_PID=""
	fi
	if [[ -n "$LOGGER_PID" ]]; then
		wait "$LOGGER_PID" 2>/dev/null || true
		LOGGER_PID=""
	fi
}

trap 'terminate_current' EXIT
trap 'terminate_current; exit 130' INT
trap 'terminate_current; exit 143' TERM

if [[ "${QEMU_WATCHDOG:-0}" != 1 ]]; then
	printf 'QEMU_WATCHDOG=1 is required for this test.\n' >&2
	exit 2
fi

while (($#)); do
	case "$1" in
		--smoke)
			SMOKE=1
			shift
			;;
		--experiment)
			MODE=all
			RUNS=5
			shift
			;;
		--mode)
			(($# >= 2)) || { usage; exit 2; }
			MODE="$2"
			shift 2
			;;
		--runs)
			(($# >= 2)) || { usage; exit 2; }
			RUNS="$2"
			shift 2
			;;
		--csv)
			(($# >= 2)) || { usage; exit 2; }
			CSV_OVERRIDE="$2"
			shift 2
			;;
		-h|--help)
			usage
			exit 0
			;;
		*)
			usage
			exit 2
			;;
	esac
done

if ((SMOKE)); then
	MODE=stop
	RUNS=1
fi
if [[ -z "$MODE" ]]; then
	MODE=all
fi
if [[ "$MODE" != all && "$MODE" != none && "$MODE" != stop &&
	"$MODE" != kill9 && "$MODE" != term && "$MODE" != reboot &&
	"$MODE" != poweroff ]]; then
	printf 'Unsupported watchdog mode: %s\n' "$MODE" >&2
	exit 2
fi
if [[ ! "$RUNS" =~ ^[1-9][0-9]*$ ]]; then
	printf 'Run count must be a positive integer: %s\n' "$RUNS" >&2
	exit 2
fi
if [[ -n "$CSV_OVERRIDE" ]]; then
	CSV_FILE="$CSV_OVERRIDE"
fi
if [[ "$MODE" == all && "$RUNS" != 5 ]]; then
	printf 'The registered experiment uses exactly five runs per mode.\n' >&2
	exit 2
fi

mkdir -p "$LOG_ROOT" "$WORK_ROOT" "$(dirname -- "$CSV_FILE")"
for required in "$BASE_IMAGE" "$ROOTFS" "$KERNEL" "$BASE_DTB"; do
	if [[ ! -f "$required" ]]; then
		printf 'Required file not found: %s\n' "$required" >&2
		exit 1
	fi
done

prepare_test_image() {
	local build_dir target_dir rootfs_test image_template
	local unsquashfs mksquashfs sfdisk
	local unsquash_status=0 squashfs_info compression block_size partition_info
	local root_a_start root_a_size root_b_start root_b_size rootfs_bytes
	local image_size padded_size

	unsquashfs="${OUTPUT_DIR}/host/bin/unsquashfs"
	mksquashfs="${OUTPUT_DIR}/host/bin/mksquashfs"
	sfdisk="${OUTPUT_DIR}/host/sbin/sfdisk"
	build_dir="${WORK_ROOT}/image-$(date -u +%Y%m%dT%H%M%S)-${BASHPID}"
	target_dir="${build_dir}/target"
	rootfs_test="${build_dir}/rootfs-wdtest.squashfs"
	image_template="${build_dir}/sdcard-wdtest.img"
	for required in "$unsquashfs" "$mksquashfs" "$sfdisk"; do
		if [[ ! -x "$required" ]]; then
			printf 'Required test-image tool not found: %s\n' "$required" >&2
			return 1
		fi
	done

	mkdir -p "$build_dir"
	"$unsquashfs" -no-progress -no-xattrs -d "$target_dir" "$ROOTFS" \
		>"${build_dir}/unsquashfs.log" 2>&1 || unsquash_status=$?
	if ((unsquash_status != 0)); then
		if ((unsquash_status != 2)) ||
			! grep -Fq 'failed to change uid and gids' \
				"${build_dir}/unsquashfs.log"; then
			cat "${build_dir}/unsquashfs.log" >&2
			return 1
		fi
	fi
	install -D -m 0755 "${SCRIPT_DIR}/S97zz-wdtest" \
		"${target_dir}/etc/init.d/S97zz-wdtest"

	squashfs_info="$("$unsquashfs" -s "$ROOTFS")"
	compression="$(awk '$1 == "Compression" { print $2; exit }' \
		<<<"$squashfs_info")"
	block_size="$(awk '$1 == "Block" && $2 == "size" { print $3; exit }' \
		<<<"$squashfs_info")"
	if [[ -z "$compression" || -z "$block_size" ]]; then
		printf 'Could not read SquashFS options from %s\n' "$ROOTFS" >&2
		return 1
	fi
	"$mksquashfs" "$target_dir" "$rootfs_test" -noappend -all-root \
		-no-xattrs -no-progress -comp "$compression" -b "$block_size" \
		>"${build_dir}/mksquashfs.log" 2>&1

	cp --reflink=auto --sparse=always "$BASE_IMAGE" "$image_template"
	image_size="$(stat -c '%s' "$image_template")"
	padded_size=1
	while ((padded_size < image_size)); do
		padded_size=$((padded_size * 2))
	done
	truncate -s "$padded_size" "$image_template"
	partition_info="$("$sfdisk" --json "$image_template" | python3 -c '
import json
import sys

partitions = json.load(sys.stdin)["partitiontable"]["partitions"]
if len(partitions) != 7:
    raise SystemExit(f"expected 7 partitions, found {len(partitions)}")
for number in (5, 6):
    partition = partitions[number - 1]
    print(partition["start"], partition["size"], end=" ")
')"
	read -r root_a_start root_a_size root_b_start root_b_size \
		<<<"$partition_info"
	rootfs_bytes="$(stat -c '%s' "$rootfs_test")"
	if ((rootfs_bytes > root_a_size * 512 || rootfs_bytes > root_b_size * 512)); then
		printf 'Test SquashFS does not fit in rootfs A/B partitions.\n' >&2
		return 1
	fi
	dd if="$rootfs_test" of="$image_template" bs=512 \
		seek="$root_a_start" conv=notrunc status=none
	dd if="$rootfs_test" of="$image_template" bs=512 \
		seek="$root_b_start" conv=notrunc status=none

	TEST_TEMPLATE="$image_template"
	printf 'Test-only S97zz hook installed in %s\n' "$TEST_TEMPLATE"
}

wait_for_text() {
	local log="$1"
	local text="$2"
	local timeout="$3"
	local deadline=$((SECONDS + timeout))

	while ((SECONDS <= deadline)); do
		if [[ -f "$log" ]] && grep -Fq -- "$text" "$log"; then
			return 0
		fi
		if [[ -n "$LOGGER_PID" ]] && ! kill -0 "$LOGGER_PID" 2>/dev/null; then
			return 1
		fi
		sleep 0.1
	done
	return 1
}

wait_after_marker() {
	local timeout="$1"
	local deadline=$((SECONDS + timeout))

	while ((SECONDS < deadline)); do
		if [[ -n "$LOGGER_PID" ]] && ! kill -0 "$LOGGER_PID" 2>/dev/null; then
			return 0
		fi
		sleep 0.1
	done
}

wait_for_reset_and_ready() {
	local log="$1"

	python3 - "$log" <<'PY'
import sys
import time
from pathlib import Path

log_path = Path(sys.argv[1])
started = time.monotonic()

def read_log():
    try:
        return log_path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""

def after_marker(text):
    marker = text.find("msd-wdtest: wdt state=")
    return text[marker:] if marker >= 0 else ""

while time.monotonic() - started < 30:
    text = read_log()
    marker_log = after_marker(text)
    if "[host] serial EOF" in text:
        raise SystemExit(0)
    reset = marker_log.find("Booting Linux")
    if reset >= 0:
        reset_seen = time.monotonic()
        while time.monotonic() - reset_seen < 120:
            text = read_log()
            marker_log = after_marker(text)
            if "[host] serial EOF" in text:
                raise SystemExit(0)
            reset = marker_log.find("Booting Linux")
            if reset >= 0:
                second_boot = marker_log.find("msd-wdtest: second boot", reset)
                if second_boot >= 0 and "MSD/Linux ready" in marker_log[second_boot:]:
                    raise SystemExit(0)
            time.sleep(0.1)
        raise SystemExit(0)
    time.sleep(0.1)

raise SystemExit(0)
PY
}

analyze_log() {
	local log="$1"
	python3 - "$log" <<'PY'
import re
import sys

lines = []
with open(sys.argv[1], encoding="utf-8", errors="replace") as stream:
    for raw in stream:
        match = re.match(r"^([0-9]+\.[0-9]+) (.*)$", raw.rstrip("\n"))
        if match:
            lines.append((float(match.group(1)), match.group(2)))

marker = next(
    ((time, line) for time, line in lines if "msd-wdtest: wdt state=" in line),
    None,
)
eof = next(
    (time for time, line in reversed(lines) if line == "[host] serial EOF"),
    None,
)
if marker is None:
    print("missing\tmissing\tmissing\tno\tno\tmissing\tmissing\tno\tmissing")
    raise SystemExit(0)

marker_time, marker_line = marker
reset = next(
    (time for time, line in lines
     if time > marker_time and "Booting Linux" in line),
    None,
)
restart = any(
    "reboot: Restarting system" in line
    and time > marker_time
    and (reset is None or time < reset)
    for time, line in lines
)
second_lines = [
    line for time, line in lines if reset is not None and time > reset
]
second_ready = (
    any("MSD/Linux ready" in line for line in second_lines)
    and any("msd-wdtest: second boot" in line for line in second_lines)
)
state_match = re.search(r"wdt state=(\S+) timeout=(\S+)", marker_line)
state, timeout = state_match.groups() if state_match else ("missing", "missing")
cmdline = next(
    (line for _, line in lines if "msd-wdtest: cmdline=" in line),
    "",
)
cmdline_ok = bool(cmdline) and "initcall_blacklist=bcm2835_wdt_driver_init" not in cmdline
delta = reset - marker_time if reset is not None else None
values = (
    f"{marker_time:.9f}",
    f"{reset:.9f}" if reset is not None else "missing",
    f"{delta:.9f}" if delta is not None else "missing",
    "yes" if restart else "no",
    "yes" if second_ready else "no",
    state,
    timeout,
    "yes" if cmdline_ok else "no",
    f"{eof:.9f}" if eof is not None else "missing",
)
print("\t".join(values))
PY
}

append_csv_row() {
	local version="$1" run_id="$2" mode="$3" repeat="$4" marker_s="$5"
	local reset_s="$6" delta_s="$7" restart_line="$8" second_ready="$9"
	local qemu_exit="${10}" valid="${11}" note="${12//,/;}"
	local header='version,run_id,mode,repeat,marker_s,reset_s,delta_s,restart_line,second_ready,qemu_exit,valid,note'

	if [[ ! -s "$CSV_FILE" ]]; then
		printf '%s\n' "$header" >"$CSV_FILE"
	elif [[ "$(head -n 1 "$CSV_FILE")" != "$header" ]]; then
		printf 'Unexpected CSV header in %s\n' "$CSV_FILE" >&2
		return 1
	fi
	printf '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n' \
		"$version" "$run_id" "$mode" "$repeat" "$marker_s" "$reset_s" \
		"$delta_s" "$restart_line" "$second_ready" "$qemu_exit" "$valid" "$note" \
		>>"$CSV_FILE"
}

run_trial() {
	local run_id="$1" mode="$2" repeat="$3"
	local run_dir="${LOG_ROOT}/${run_id}"
	local disk="${run_dir}/sdcard.img"
	local fifo="${run_dir}/serial.fifo"
	local log="${run_dir}/serial.log"
	local timeout=40 qemu_exit=missing exit_status=0 naturally_exited=no
	local marker_s reset_s delta_s restart_line second_ready state watchdog_timeout
	local cmdline_ok eof_s valid=1 note=""

	if [[ "$mode" == none || "$mode" == term ]]; then
		timeout=60
	fi
	mkdir -p "$run_dir"
	cp --reflink=auto --sparse=always "$TEST_TEMPLATE" "$disk"
	mkfifo "$fifo"
	python3 "${SCRIPT_DIR}/timestamp-serial.py" "$fifo" "$log" &
	LOGGER_PID=$!
	env -u QEMU_ICOUNT QEMU_WATCHDOG=1 \
		QEMU_EXTRA_APPEND="msd.wdtest=${mode}" \
		QEMU_COPY_IMAGE=0 QEMU_MACHINE="$QEMU_MACHINE" \
		DTB_IMAGE="$BASE_DTB" OUTPUT_DIR="$OUTPUT_DIR" \
		"$SCRIPT_DIR/run-qemu.sh" "$disk" >"$fifo" 2>&1 &
	CURRENT_PID=$!

	if ! wait_for_text "$log" "msd-wdtest: wdt state=" 180; then
		note="marker-timeout"
		valid=0
	elif [[ "$mode" == stop || "$mode" == kill9 ]]; then
		wait_for_reset_and_ready "$log"
	else
		wait_after_marker "$timeout"
	fi

	if [[ -n "$CURRENT_PID" ]]; then
		if [[ -n "$LOGGER_PID" ]] && kill -0 "$LOGGER_PID" 2>/dev/null; then
			kill -KILL "$CURRENT_PID" 2>/dev/null || true
		else
			naturally_exited=yes
		fi
		if wait "$CURRENT_PID"; then
			exit_status=0
		else
			exit_status=$?
		fi
		CURRENT_PID=""
		wait "$LOGGER_PID" 2>/dev/null || true
		LOGGER_PID=""
	fi

	IFS=$'\t' read -r marker_s reset_s delta_s restart_line second_ready \
		state watchdog_timeout cmdline_ok eof_s <<<"$(analyze_log "$log")"
	if [[ "$marker_s" == missing ]]; then
		valid=0
		note="${note:+${note};}marker-missing"
	fi
	if [[ "$cmdline_ok" != yes ]]; then
		valid=0
		note="${note:+${note};}watchdog-cmdline-not-enabled"
	fi
	if [[ "$state" != active || "$watchdog_timeout" != 15 ]]; then
		note="${note:+${note};}state=${state};timeout=${watchdog_timeout}"
	fi
	if [[ "$naturally_exited" == yes ]]; then
		qemu_exit="${exit_status}@${eof_s}"
	else
		qemu_exit="killed@${eof_s}"
	fi

	case "$mode" in
		none)
			if [[ "$reset_s" != missing || "$naturally_exited" == yes ||
				"$state" != active || "$watchdog_timeout" != 15 ]]; then
				note="${note:+${note};}criteria-failed"
			fi
			;;
		stop|kill9)
			if [[ "$reset_s" == missing || "$delta_s" == missing ]] ||
				! awk -v delta="$delta_s" \
					'BEGIN { exit !(delta >= 8 && delta <= 30) }' ||
				[[ "$restart_line" != no || "$second_ready" != yes ]]; then
				note="${note:+${note};}criteria-failed"
			fi
			;;
		reboot)
			if [[ "$reset_s" == missing || "$delta_s" == missing ]] ||
				! awk -v delta="$delta_s" \
					'BEGIN { exit !(delta <= 10) }' ||
				[[ "$restart_line" != yes || "$second_ready" != yes ]]; then
				note="${note:+${note};}criteria-failed"
			fi
			;;
		poweroff)
			if [[ "$naturally_exited" != yes || "$exit_status" != 0 ||
				"$reset_s" != missing || "$eof_s" == missing ||
				"$marker_s" == missing ]] ||
				! awk -v marker="$marker_s" -v exit_time="$eof_s" \
					'BEGIN { exit !(exit_time - marker <= 30) }'; then
				note="${note:+${note};}criteria-failed"
			fi
			;;
		term)
			;;
	esac

	append_csv_row "$PROTOCOL_VERSION" "$run_id" "$mode" "$repeat" "$marker_s" \
		"$reset_s" "$delta_s" "$restart_line" "$second_ready" "$qemu_exit" \
		"$valid" "$note"
	printf 'mode=%s repeat=%s marker=%s reset=%s delta=%s restart=%s second_ready=%s qemu_exit=%s valid=%s log=%s\n' \
		"$mode" "$repeat" "$marker_s" "$reset_s" "$delta_s" \
		"$restart_line" "$second_ready" "$qemu_exit" "$valid" "$log"
	if [[ "$note" == *criteria-failed* || "$valid" != 1 ]]; then
		return 1
	fi
}

prepare_test_image
run_timestamp="$(date -u +%Y%m%dT%H%M%SZ)-${BASHPID}"
if [[ "$MODE" == all ]]; then
	modes=(none stop kill9 term reboot poweroff)
else
	modes=("$MODE")
fi

failed=0
for mode in "${modes[@]}"; do
	for ((repeat = 1; repeat <= RUNS; repeat++)); do
		run_id="s11-${PROTOCOL_VERSION}-${run_timestamp}-${mode}-${repeat}"
		if [[ "$SMOKE" == 1 ]]; then
			run_id="s11-smoke-${PROTOCOL_VERSION}-${run_timestamp}-${mode}-${repeat}"
		fi
		if ! run_trial "$run_id" "$mode" "$repeat"; then
			failed=1
		fi
	done
done

printf 'Raw CSV: %s\n' "$CSV_FILE"
exit "$failed"
