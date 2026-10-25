#!/usr/bin/env bash
# S15: boot the same image five times under QEMU icount with each QEMU
# binary, machine model and optional TCG plugin, and record boot markers.
# Run inside docker/msd-dev with OUTPUT_DIR set on the host side.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
OUTPUT_DIR="${OUTPUT_DIR:?set OUTPUT_DIR}"
LOG_ROOT="${S15_LOG_DIR:-${OUTPUT_DIR}/s15}"
RUNS="${S15_RUNS:-5}"
BOOT_CSV="${LOG_ROOT}/s15-boot.csv"
PLUGIN_CSV="${LOG_ROOT}/s15-plugin.csv"
# name:qemu-binary:machine:plugin (plugin empty for none)
CONDITIONS="${S15_CONDITIONS:?set S15_CONDITIONS}"

for f in "$BOOT_CSV" "$PLUGIN_CSV"; do
	[[ -e "$f" ]] && { printf 'Refusing to overwrite %s\n' "$f" >&2; exit 1; }
done
mkdir -p "$LOG_ROOT"
printf 'variant,repeat,metric,value,unit,valid,note\n' >"$PLUGIN_CSV"

for spec in $CONDITIONS; do
	IFS=: read -r name qemu machine plugin <<<"$spec"
	[[ -x "$qemu" ]] || { printf 'QEMU binary not found: %s\n' "$qemu" >&2; exit 1; }
	[[ -z "$plugin" || -r "$plugin" ]] || { printf 'Plugin not found: %s\n' "$plugin" >&2; exit 1; }
	{
		printf '%s qemu=%s sha256=%s machine=%s plugin=%s\n' "$name" "$qemu" \
			"$(sha256sum "$qemu" | cut -d ' ' -f 1)" "$machine" "${plugin:-none}"
		"$qemu" --version | head -n 1
		[[ -z "$plugin" ]] || printf 'plugin_sha256=%s\n' "$(sha256sum "$plugin" | cut -d ' ' -f 1)"
	} >>"${LOG_ROOT}/conditions.log"
	status=0
	S15_QEMU="$qemu" S15_PLUGIN="$plugin" QEMU_MACHINE="$machine" \
		QEMU_SYSTEM_AARCH64="${SCRIPT_DIR}/s15/qemu-wrap.sh" \
		"${SCRIPT_DIR}/boottime/run-boottime.sh" --variant "$name" --runs "$RUNS" \
		--csv "$BOOT_CSV" --log-dir "${LOG_ROOT}/${name}" --mode icount || status=$?
	printf '%s exit=%s\n' "$name" "$status" >>"${LOG_ROOT}/conditions.log"
	[[ -n "$plugin" ]] || continue
	for boot in "${LOG_ROOT}/${name}"/boot*/; do
		boot="${boot%/}"
		insns="$(sed -n 's/^total insns: \([0-9][0-9]*\)$/\1/p' "${boot}/plugin.log" 2>/dev/null || true)"
		valid=1
		[[ "$insns" =~ ^[0-9]+$ ]] || { insns=; valid=0; }
		printf '%s,%s,plugin_total_insns,%s,insn,%s,plugin=%s\n' "$name" "${boot##*/boot}" \
			"$insns" "$valid" "${plugin##*/}" >>"$PLUGIN_CSV"
	done
done
printf 'boot CSV: %s\nplugin CSV: %s\n' "$BOOT_CSV" "$PLUGIN_CSV"
