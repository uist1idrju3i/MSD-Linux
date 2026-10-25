#!/usr/bin/env bash
# S12: rebuild the rootfs with each SquashFS compressor and block size, boot
# each image five times under QEMU icount, and record image size and host
# decode time. Run inside docker/msd-dev with OUTPUT_DIR set on the host side.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
OUTPUT_DIR="${OUTPUT_DIR:?set OUTPUT_DIR}"
LOG_ROOT="${S12_LOG_DIR:-${OUTPUT_DIR}/s12}"
RUNS="${S12_RUNS:-5}"
HOST_RUNS="${S12_HOST_RUNS:-5}"
BOOT_CSV="${LOG_ROOT}/s12-boot.csv"
HOST_CSV="${LOG_ROOT}/s12-host.csv"
VARIANTS="${S12_VARIANTS:-zstd128a:zstd:131072 gzip128:gzip:131072 xz128:xz:131072 lz4128:lz4:131072 lzo128:lzo:131072 zstd256:zstd:262144 zstd1m:zstd:1048576 zstd128b:zstd:131072}"
unsquashfs="${OUTPUT_DIR}/host/bin/unsquashfs"

for f in "$BOOT_CSV" "$HOST_CSV"; do
	[[ -e "$f" ]] && { printf 'Refusing to overwrite %s\n' "$f" >&2; exit 1; }
done
mkdir -p "$LOG_ROOT"
printf 'run_id,variant,repeat,metric,value,unit,valid,note\n' >"$HOST_CSV"

for spec in $VARIANTS; do
	IFS=: read -r name comp block <<<"$spec"
	status=0
	"${SCRIPT_DIR}/boottime/run-boottime.sh" --variant "$name" --runs "$RUNS" \
		--csv "$BOOT_CSV" --log-dir "${LOG_ROOT}/${name}" --mode icount \
		--squashfs-comp "$comp" --squashfs-block "$block" || status=$?
	printf '%s exit=%s\n' "$name" "$status" >>"${LOG_ROOT}/variants.log"
	rootfs="$(find "${LOG_ROOT}/${name}" -name rootfs-boottime.squashfs | head -n 1)"
	[[ -n "$rootfs" ]] || continue
	run_id="$(date -u +%Y%m%dT%H%M%SZ)-${name}-host"
	printf '%s,%s,0,rootfs_bytes,%s,B,1,comp=%s;block=%s\n' "$run_id" "$name" \
		"$(stat -c %s "$rootfs")" "$comp" "$block" >>"$HOST_CSV"
	for repeat in $(seq 1 "$HOST_RUNS"); do
		out="${LOG_ROOT}/${name}/unsquash"
		rm -rf "$out"
		start_ns="$(date +%s%N)"
		ok=1
		"$unsquashfs" -no-progress -no-xattrs -processors 1 -d "$out" "$rootfs" \
			>"${LOG_ROOT}/${name}/unsquash${repeat}.log" 2>&1 ||
			grep -Fq 'failed to change uid and gids' "${LOG_ROOT}/${name}/unsquash${repeat}.log" || ok=0
		end_ns="$(date +%s%N)"
		ns=$((end_ns - start_ns))
		printf '%s,%s,%s,host_unsquashfs_1cpu,%d.%06d,s,%s,comp=%s;block=%s\n' "$run_id" "$name" \
			"$repeat" "$((ns / 1000000000))" "$(((ns % 1000000000) / 1000))" "$ok" "$comp" "$block" >>"$HOST_CSV"
		rm -rf "$out"
	done
done
printf 'boot CSV: %s\nhost CSV: %s\n' "$BOOT_CSV" "$HOST_CSV"
