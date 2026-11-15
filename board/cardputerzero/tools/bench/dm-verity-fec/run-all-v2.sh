#!/bin/bash
set -euo pipefail

if (($# < 3 || $# > 5)); then
	printf 'Usage: %s OUTPUT_DIR BASE_DIR RESULTS_DIR [RUNS] [TIMEOUT_SEC]\n' "$0" >&2
	exit 2
fi
output_dir="$1"
base_dir="$2"
results_dir="$3"
runs="${4:-4}"
timeout="${5:-180}"
script_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
if [[ -e "$results_dir" || -L "$results_dir" ]]; then
	printf 'refusing to overwrite existing evidence: %s\n' "$results_dir" >&2
	exit 1
fi
while read -r case_name expected; do
	[[ -f "${base_dir}/${case_name}/images/sdcard.img" ]]
	if [[ "$expected" == verity-panic ]]; then
		grep -Fq panic_on_corruption "${base_dir}/${case_name}/qemu-extra-append.txt"
	elif [[ "$expected" == verity-restart ]]; then
		grep -Fq restart_on_corruption "${base_dir}/${case_name}/qemu-extra-append.txt"
	fi
done <"${script_dir}/expectations-v2.tsv"
mkdir -p "$(dirname "$results_dir")"
mkdir "$results_dir"
cp "${script_dir}/expectations-v2.tsv" "$results_dir/expectations.tsv"
sha256sum "${script_dir}/../dm-verity/run-boots.sh" \
	"${script_dir}/../dm-verity/verdict.py" \
	"${script_dir}/expectations-v2.tsv" >"$results_dir/harness.sha256"
failed=0
while read -r case_name expected; do
	OUTPUT_DIR="$output_dir" bash "${script_dir}/../dm-verity/run-boots.sh" \
		--case "$case_name" --image "${base_dir}/${case_name}/images/sdcard.img" \
		--runs "$runs" --timeout "$timeout" --csv "${results_dir}/${case_name}.csv" \
		--log-dir "${results_dir}/${case_name}" --expected "$expected" || failed=1
done <"${script_dir}/expectations-v2.tsv"
exit "$failed"
