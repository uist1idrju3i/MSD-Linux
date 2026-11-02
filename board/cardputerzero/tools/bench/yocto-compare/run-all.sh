#!/bin/bash
# Full matrix for docs/experiments/2026-11-02-buildroot-yocto-boottime.md.
# Usage (inside docker/msd-dev): run-all.sh INPUT_DIR OUT_DIR [RUNS]
# INPUT_DIR holds br-Image, br-cm0.dtb, br-sdcard.img, yocto-e-Image, yocto-b2-Image, yocto-cmp.wic.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
if (($# < 2 || $# > 3)); then
	printf 'Usage: %s INPUT_DIR NEW_OUT_DIR [RUNS]\n' "$0" >&2
	exit 2
fi
in="$1" out="$2" runs="${3:-5}"
[[ "$runs" =~ ^[1-9][0-9]{0,8}$ ]] || exit 2
for input in br-Image br-cm0.dtb br-sdcard.img yocto-e-Image yocto-b2-Image yocto-cmp.wic; do
	[[ -s "$in/$input" && -f "$in/$input" && -r "$in/$input" ]] || { printf 'Missing input: %s\n' "$input" >&2; exit 2; }
done
mkdir -- "$out" || { printf 'Output directory already exists or parent is missing: %s\n' "$out" >&2; exit 2; }
br=(--root-dev /dev/mmcblk0p5 --root-fstype squashfs --ready-marker 'MSD/Linux ready' --image "$in/br-sdcard.img")
yo=(--root-dev /dev/mmcblk0p2 --root-fstype ext4 --ready-marker 'msd-compare: ready' --image "$in/yocto-cmp.wic")
for mode in icount tcg; do
	"$SCRIPT_DIR/run-compare.sh" --condition C1-br --kernel "$in/br-Image" --dtb "$in/br-cm0.dtb" "${br[@]}" --mode "$mode" --runs "$runs" --out "$out/C1-br-$mode"
	"$SCRIPT_DIR/run-compare.sh" --condition C2-yocto-e --kernel "$in/yocto-e-Image" --dtb "$in/br-cm0.dtb" "${yo[@]}" --mode "$mode" --runs "$runs" --out "$out/C2-yocto-e-$mode"
	"$SCRIPT_DIR/run-compare.sh" --condition C3-yocto-b2k --kernel "$in/yocto-b2-Image" --dtb "$in/br-cm0.dtb" "${yo[@]}" --mode "$mode" --runs "$runs" --out "$out/C3-yocto-b2k-$mode"
	"$SCRIPT_DIR/run-compare.sh" --condition C4-brk-yroot --kernel "$in/br-Image" --dtb "$in/br-cm0.dtb" "${yo[@]}" --mode "$mode" --runs "$runs" --out "$out/C4-brk-yroot-$mode"
	if [[ "$mode" == icount ]]; then
		"$SCRIPT_DIR/run-compare.sh" --condition C1-br-aa --kernel "$in/br-Image" --dtb "$in/br-cm0.dtb" "${br[@]}" --mode "$mode" --runs "$runs" --out "$out/C1-br-aa-$mode"
	fi
done
python3 - "$out" <<'PY'
import csv
from pathlib import Path
import sys

out = Path(sys.argv[1])
with (out / "results.csv").open("x", newline="") as target:
    writer = csv.writer(target, lineterminator="\n")
    for index, path in enumerate(sorted(out.glob("*/results.csv"))):
        with path.open(newline="") as source:
            reader = csv.reader(source)
            header = next(reader)
            if index == 0:
                writer.writerow(header)
            writer.writerows(reader)
PY
python3 "$SCRIPT_DIR/summarize.py" "$out/results.csv" --min-runs "$runs" >"$out/summary.csv"
