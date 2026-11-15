#!/bin/sh
# E1 driver: variant x 3 repeat の write-inventory 測定を逐次実行する。
# mature は直前の base run の post-boot sdcard.img を入力にする。
# 実行: docker/msd-dev sh output-dwcause/run-e1.sh  (リポジトリ最上位から)
set -eu

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
WORK="${E1_WORK_DIR:-$REPO/output-dwcause}"
OUTPUT="${E1_OUTPUT_DIR:-$REPO/output-openssl-lts}"
RUNS="$WORK/runs"
RUNPY="board/cardputerzero/tools/bench/write-inventory/run.py"
CHECK="$REPO/docs/experiments/2026-11-15-data-first-boot-writes-aggregate.py"
WINDOW_SECONDS="${WINDOW_SECONDS:-120}"
WINDOWS="${WINDOWS:-3}"
REPEATS="${REPEATS:-3}"
for count in "$WINDOW_SECONDS" "$WINDOWS" "$REPEATS"; do
    case "$count" in ''|*[!0-9]*|0) echo "positive count required" >&2; exit 2 ;; esac
done
mkdir -p "$RUNS"

run_one() { # $1=variant $2=output-dir $3=repeat
    rd="$RUNS/$1-r$3"
    if python3 "$CHECK" "$rd" --validate --windows "$WINDOWS" --seconds "$WINDOW_SECONDS"; then
        echo "skip $1 r$3 (verified completion record)"
        return 0
    fi
    if [ -e "$rd" ] || [ -L "$rd" ]; then
        saved="$(mktemp -d "$RUNS/$1-r$3.failed-XXXXXXXX")" || return 1
        mv "$rd" "$saved/attempt" || return 1
    fi
    echo "=== run $1 r$3 $(date -Is) ==="
    if python3 "$RUNPY" --output "$2" --run-dir "$rd" \
        --variant "$1" --seconds "$WINDOW_SECONDS" --windows "$WINDOWS"; then
        python3 "$CHECK" "$rd" --complete --windows "$WINDOWS" --seconds "$WINDOW_SECONDS"
    else
        return 1
    fi
}

mk_mature_input() { # $1=base run の run-dir
    d="$(mktemp -d "$WORK/input-mature-r$2.XXXXXXXX")" || return 1
    mkdir "$d/images" || return 1
    cp "$1/sdcard.img" "$d/images/sdcard.img" || return 1
    for n in Image rootfs.squashfs bcm2710-rpi-cm0.dtb; do
        ln -s "$(realpath --relative-to="$d/images" "$OUTPUT/images/$n")" "$d/images/$n" || return 1
    done
    ln -s "$(realpath --relative-to="$d" "$OUTPUT/.config")" "$d/.config" || return 1
    ln -s "$(realpath --relative-to="$d" "$OUTPUT/host")" "$d/host" || return 1
}

failed=0
for rep in $(seq 1 "$REPEATS"); do
    if ! run_one base "$OUTPUT" "$rep"; then failed=1; continue; fi
    run_one grown-fs64 "$WORK/input-grown-fs64" "$rep" || failed=1
    run_one pregrown "$WORK/input-pregrown" "$rep" || failed=1
    run_one pregrown-nolazy "$WORK/input-pregrown-nolazy" "$rep" || failed=1
    if [ -f "$RUNS/base-r$rep/sdcard.img" ]; then
        mk_mature_input "$RUNS/base-r$rep" "$rep"
        run_one mature "$d" "$rep" || failed=1
    else
        failed=1
    fi
done
echo "ALL DONE $(date -Is)"
exit "$failed"
