#!/bin/bash
# Usage (inside docker/msd-dev): run-tty-count.sh LOG_DIR CSV [RUNS]
# Boots the unmodified image with the stock DTB ("stock") and with the
# Bluetooth serdev child of the PL011 disabled ("bt-off"), logs in on the
# serial console, and counts the kernel tty->count warnings. "default" boots
# the stock DTB without QEMU_DTB_BLUETOOTH=1, so run-qemu.sh disables the node.
set -uo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../../../.." && pwd)"
OUTPUT_DIR="${OUTPUT_DIR:-${REPO_ROOT}/output}"
export OUTPUT_DIR
log_dir="$1"; csv="$2"; runs="${3:-5}"
stock_dtb="${OUTPUT_DIR}/images/bcm2710-rpi-cm0.dtb"
bt_node=/soc/serial@7e201000/bluetooth
[[ -e "$csv" ]] && { printf 'Refusing to overwrite %s\n' "$csv" >&2; exit 1; }
mkdir -p "$log_dir"
bt_off_dtb="${log_dir}/bcm2710-rpi-cm0-bt-off.dtb"
cp "$stock_dtb" "$bt_off_dtb"
"${OUTPUT_DIR}/host/bin/fdtput" -t s "$bt_off_dtb" "$bt_node" status disabled
[[ "$("${OUTPUT_DIR}/host/bin/fdtget" "$bt_off_dtb" "$bt_node" status)" == disabled ]] || exit 1
printf 'run_id,variant,repeat,metric,value,unit,valid,note\n' >"$csv"

wait_for() { # log pattern pid timeout
	local deadline=$((SECONDS + $4))
	while ((SECONDS < deadline)); do
		tr -d '\r' <"$1" | grep -aEq -- "$2" && return 0
		kill -0 "$3" 2>/dev/null || return 1
		sleep 0.5
	done
	return 1
}

for variant in ${TTY_VARIANTS:-stock bt-off default}; do
	dtb="$stock_dtb"; [[ "$variant" == bt-off ]] && dtb="$bt_off_dtb"
	keep_bt=1; [[ "$variant" == default ]] && keep_bt=0
	for repeat in $(seq 1 "$runs"); do
		run_id="$(date -u +%Y%m%dT%H%M%SZ)-${variant}-${repeat}"
		log="${log_dir}/${run_id}.log"
		fifo="${log_dir}/${run_id}.in"
		mkfifo "$fifo"
		QEMU_DTB_BLUETOOTH="$keep_bt" DTB_IMAGE="$dtb" "${REPO_ROOT}/board/cardputerzero/qemu/run-qemu.sh" \
			<"$fifo" >"$log" 2>&1 &
		pid=$!
		exec 3>"$fifo"
		ok=1
		wait_for "$log" 'login:' "$pid" 240 || ok=0
		before_login="$(tr -d '\r' <"$log" | grep -ac 'tty->count')"
		if ((ok)); then
			sleep 2; printf 'root\r' >&3
			wait_for "$log" '^# |~ # ' "$pid" 60 || ok=0
		fi
		if ((ok)); then
			# shellcheck disable=SC2016 # Expanded by the guest shell.
			printf 'echo TTYPROBE-$((6*7)); grep -c hci_uart /proc/modules; ls /sys/bus/serial/devices | tr "\\n" " "; echo; echo PROBE-END\r' >&3
			wait_for "$log" '^PROBE-END' "$pid" 60 || ok=0
		fi
		sleep 1
		exec 3>&-
		kill "$pid" 2>/dev/null; wait "$pid" 2>/dev/null
		rm -f "$fifo"
		clean="$(tr -d '\r\000' <"$log")"
		total="$(grep -ac 'tty->count' <<<"$clean")"
		probe=no; grep -aq '^TTYPROBE-42$' <<<"$clean" && probe=yes
		hci="$(grep -aA1 '^TTYPROBE-42$' <<<"$clean" | sed -n 2p)"
		serdev="$(grep -ac 'tty port ttyAMA1 registered' <<<"$clean")"
		{
			printf '%s,%s,%s,warnings_total,%s,lines,%s,\n' "$run_id" "$variant" "$repeat" "$total" "$ok"
			printf '%s,%s,%s,warnings_before_login,%s,lines,%s,\n' "$run_id" "$variant" "$repeat" "$before_login" "$ok"
			printf '%s,%s,%s,serdev_registered,%s,lines,%s,\n' "$run_id" "$variant" "$repeat" "$serdev" "$ok"
			printf '%s,%s,%s,hci_uart_loaded,%s,count,%s,\n' "$run_id" "$variant" "$repeat" "${hci:-none}" "$ok"
			printf '%s,%s,%s,shell_probe,%s,bool,%s,\n' "$run_id" "$variant" "$repeat" "$probe" "$ok"
			printf '%s,%s,%s,log_sha256,%s,sha256,%s,\n' "$run_id" "$variant" "$repeat" "$(sha256sum "$log" | cut -d' ' -f1)" "$ok"
		} >>"$csv"
		printf '%s ok=%s warnings=%s before_login=%s serdev=%s hci=%s probe=%s\n' \
			"$run_id" "$ok" "$total" "$before_login" "$serdev" "${hci:-none}" "$probe"
	done
done
