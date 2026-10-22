#!/usr/bin/env bash
set -euo pipefail

if (($# != 2)); then
	printf 'Usage: %s BASE_DTB OUTPUT_DTB\n' "$0" >&2
	exit 2
fi

base_dtb="$1"
output_dtb="$2"
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
dtc="${OUTPUT_DIR:?set OUTPUT_DIR}/host/bin/dtc"

[[ -f "$base_dtb" && -x "$dtc" ]]
[[ ! -e "$output_dtb" ]] || {
	printf 'Refusing to overwrite %s\n' "$output_dtb" >&2
	exit 1
}

mkdir -p "$(dirname "$output_dtb")"
work_dir="${output_dtb}.work"
mkdir "$work_dir"
"$dtc" -I dtb -O dts "$base_dtb" -o "$work_dir/base.dts" \
	>"$work_dir/decompile.log" 2>&1
python3 "$script_dir/add-ramoops.py" "$work_dir/base.dts" \
	"$work_dir/ramoops.dts"
"$dtc" -I dts -O dtb "$work_dir/ramoops.dts" -o "$output_dtb" \
	>"$work_dir/compile.log" 2>&1
"$dtc" -I dtb -O dts "$output_dtb" -o "$work_dir/roundtrip.dts" \
	>>"$work_dir/compile.log" 2>&1
grep -Fq 'compatible = "ramoops";' "$work_dir/roundtrip.dts"
grep -Fq 'record-size = <0x20000>;' "$work_dir/roundtrip.dts"
grep -Fq 'console-size = <0x20000>;' "$work_dir/roundtrip.dts"
sha256sum "$base_dtb" "$output_dtb" >"${output_dtb}.sha256"
