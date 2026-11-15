#!/bin/bash
set -euo pipefail

# B2: SquashFS compression option の一括測定。
# make-case.sh で各 variant の sdcard.img を生成し、run-boots.sh で
# runs+1 回 boot させる。全 case が ready 期待。
#
# Usage: run-all.sh OUTPUT_DIR BASE_DIR CASES_DIR RESULTS_DIR [RUNS] [TIMEOUT_SEC]
#   CASES_DIR  case 生成先（既存のものは skip して再利用しない: 存在すると失敗）
#   RUNS       repeat の最大値（boot 回数 = RUNS+1、既定 4 = 5 boot）

if (($# < 4)); then
	printf 'Usage: %s OUTPUT_DIR BASE_DIR CASES_DIR RESULTS_DIR [RUNS] [TIMEOUT_SEC]\n' "$0" >&2
	exit 2
fi

output_dir="$1"
base_dir="$2"
cases_dir="$3"
results_dir="$4"
runs="${5:-4}"
timeout="${6:-180}"
script_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
make_case="${script_dir}/make-case.sh"
run_boots="${script_dir}/../dm-verity/run-boots.sh"

if [[ ! -x "$make_case" || ! -x "$run_boots" || ! -d "$base_dir" ]]; then
	printf 'missing tools or base dir\n' >&2
	exit 2
fi
mkdir -p "$cases_dir" "$results_dir"

# variant と mksquashfs args（B1 matrix の代表値。現行 128K/l19、
# B1 最小の zstd 1M/l19、中間 512K/l19、既定 level、codec 対照）
variants=(
	"S-z128-l19|-comp zstd -b 128K -Xcompression-level 19"
	"S-z1M-l19|-comp zstd -b 1M -Xcompression-level 19"
	"S-z512k-l19|-comp zstd -b 512K -Xcompression-level 19"
	"S-z128-def|-comp zstd -b 128K"
	"S-xz128-bcja|-comp xz -b 128K -Xbcj arm"
	"S-gzip128|-comp gzip -b 128K"
	"S-lz4-128|-comp lz4 -b 128K"
)

failed=0
for entry in "${variants[@]}"; do
	case_name="${entry%%|*}"
	args_str="${entry#*|}"
	read -r -a mkfs_args <<<"$args_str"
	case_dir="${cases_dir}/${case_name}"
	if [[ -e "$case_dir" ]]; then
		printf 'skip existing case dir %s\n' "$case_dir"
	else
		printf '=== generate %s ===\n' "$case_name"
		if ! "$make_case" "$case_name" "$output_dir" "$base_dir" \
			"$case_dir" -- "${mkfs_args[@]}"; then
			failed=1
			continue
		fi
	fi
	printf '=== boot %s ===\n' "$case_name"
	OUTPUT_DIR="$output_dir" \
		ROOT_DEVICE_OVERRIDE=/dev/mmcblk0p5 \
		"$run_boots" --case "$case_name" \
		--image "${case_dir}/images/sdcard.img" \
		--runs "$runs" --timeout "$timeout" \
		--csv "${results_dir}/${case_name}.csv" \
		--log-dir "${results_dir}/${case_name}" \
		--expected ready || failed=1
done
exit "$failed"
