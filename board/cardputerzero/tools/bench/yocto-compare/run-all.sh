#!/bin/bash
# Full matrix for docs/experiments/2026-11-02-buildroot-yocto-boottime.md.
# Usage (inside docker/msd-dev): run-all.sh INPUT_DIR OUT_DIR [RUNS]
# INPUT_DIR holds br-Image, br-cm0.dtb, br-sdcard.img, yocto-e-Image, yocto-b2-Image, yocto-cmp.wic.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
in="$1" out="$2" runs="${3:-5}"
br=(--root-dev /dev/mmcblk0p5 --root-fstype squashfs --ready-marker 'MSD/Linux ready' --image "$in/br-sdcard.img")
yo=(--root-dev /dev/mmcblk0p2 --root-fstype ext4 --ready-marker 'msd-compare: ready' --image "$in/yocto-cmp.wic")
for mode in icount tcg; do
	"$SCRIPT_DIR/run-compare.sh" --condition C1-br --kernel "$in/br-Image" --dtb "$in/br-cm0.dtb" "${br[@]}" --mode "$mode" --runs "$runs" --out "$out"
	"$SCRIPT_DIR/run-compare.sh" --condition C2-yocto-e --kernel "$in/yocto-e-Image" --dtb "$in/br-cm0.dtb" "${yo[@]}" --mode "$mode" --runs "$runs" --out "$out"
	"$SCRIPT_DIR/run-compare.sh" --condition C3-yocto-b2k --kernel "$in/yocto-b2-Image" --dtb "$in/br-cm0.dtb" "${yo[@]}" --mode "$mode" --runs "$runs" --out "$out"
	"$SCRIPT_DIR/run-compare.sh" --condition C4-brk-yroot --kernel "$in/br-Image" --dtb "$in/br-cm0.dtb" "${yo[@]}" --mode "$mode" --runs "$runs" --out "$out"
	if [[ "$mode" == icount ]]; then
		"$SCRIPT_DIR/run-compare.sh" --condition C1-br-aa --kernel "$in/br-Image" --dtb "$in/br-cm0.dtb" "${br[@]}" --mode "$mode" --runs "$runs" --out "$out"
	fi
done
