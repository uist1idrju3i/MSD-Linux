#!/bin/bash
set -euo pipefail

# B3: dm-verity(crc32c)+FEC 破損注入 case の一括実行。
# 各 case を run-boots.sh で runs+1 回 boot させ、case ごとの csv に記録する。
#
# Usage: run-all.sh OUTPUT_DIR BASE_DIR RESULTS_DIR [RUNS] [TIMEOUT_SEC]
#   OUTPUT_DIR  host tools（unsquashfs, mksquashfs, sfdisk）と qemu 環境の build output
#   BASE_DIR    V0/ T0/ F0-A2/ を持つ case 基盤（make-case.sh の BASE_DIR）
#   RESULTS_DIR log と csv の出力先
#   RUNS        repeat の最大値（boot 回数 = RUNS+1、既定 4 = 5 boot）
#   TIMEOUT_SEC 1 boot あたりの上限秒（既定 180）

if (($# < 3)); then
	printf 'Usage: %s OUTPUT_DIR BASE_DIR RESULTS_DIR [RUNS] [TIMEOUT_SEC]\n' "$0" >&2
	exit 2
fi

output_dir="$1"
base_dir="$2"
results_dir="$3"
runs="${4:-4}"
timeout="${5:-180}"
script_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
run_boots="${script_dir}/../dm-verity/run-boots.sh"

if [[ ! -x "$run_boots" || ! -d "$base_dir" ]]; then
	printf 'missing runner or base dir: %s %s\n' "$run_boots" "$base_dir" >&2
	exit 2
fi
mkdir -p "$results_dir"

# case -> 期待する結果（ready = 起動成功、verity-error = 検出して停止）
case_expected=(
	"F0-A2 ready"
	"F1-A2 ready"
	"F2-A2 verity-error"
	"F3-A2 ready"
	"F4-A2 verity-error"
	"F5-A2 verity-error"
	"F6-A2 verity-error"
)

failed=0
for entry in "${case_expected[@]}"; do
	read -r case_name expected <<<"$entry"
	case_dir="${base_dir}/${case_name}"
	if [[ ! -f "${case_dir}/images/sdcard.img" ||
		! -f "${case_dir}/qemu-extra-append.txt" ]]; then
		printf 'case %s is not generated: %s\n' "$case_name" "$case_dir" >&2
		failed=1
		continue
	fi
	printf '=== %s (expected=%s) ===\n' "$case_name" "$expected"
	OUTPUT_DIR="$output_dir" \
		"$run_boots" --case "$case_name" \
		--image "${case_dir}/images/sdcard.img" \
		--runs "$runs" --timeout "$timeout" \
		--csv "${results_dir}/${case_name}.csv" \
		--log-dir "${results_dir}/${case_name}" \
		--expected "$expected" || failed=1
done
exit "$failed"
