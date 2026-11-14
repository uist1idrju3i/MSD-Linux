#!/bin/sh
# E1 driver: variant x 3 repeat の write-inventory 測定を逐次実行する。
# mature は直前の base run の post-boot sdcard.img を入力にする。
# 実行: docker/msd-dev sh output-dwcause/run-e1.sh  (リポジトリ最上位から)
set -u

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
WORK="$REPO/output-dwcause"
RUNS="$WORK/runs"
RUNPY="board/cardputerzero/tools/bench/write-inventory/run.py"
WINDOW_SECONDS="${WINDOW_SECONDS:-120}"
WINDOWS="${WINDOWS:-3}"
REPEATS="${REPEATS:-3}"
mkdir -p "$RUNS"

run_one() { # $1=variant $2=output-dir $3=repeat
    rd="$RUNS/$1-r$3"
    # 完全なrunのみskip。失敗したrun（raw.csvなし）はやり直す
    if [ -f "$rd/raw.csv" ]; then echo "skip $1 r$3 (raw.csv exists)"; return 0; fi
    if [ -d "$rd" ]; then echo "warn: $rd 存在するがraw.csvがない。消去して再実行" >&2; rm -rf "$rd"; fi
    echo "=== run $1 r$3 $(date -Is) ==="
    python3 "$RUNPY" --output "$2" --run-dir "$rd" \
        --variant "$1" --seconds "$WINDOW_SECONDS" --windows "$WINDOWS"
    rc=$?
    echo "=== done $1 r$3 rc=$rc $(date -Is) ==="
    return $rc
}

mk_mature_input() { # $1=base run の run-dir
    d="$WORK/input-mature"
    rm -rf "$d"
    mkdir -p "$d/images"
    cp "$1/sdcard.img" "$d/images/sdcard.img"
    for n in Image rootfs.squashfs bcm2710-rpi-cm0.dtb; do
        ln -sf "$REPO/output-openssl-lts/images/$n" "$d/images/$n"
    done
    ln -sf "$REPO/output-openssl-lts/.config" "$d/.config"
    ln -sf "$REPO/output-openssl-lts/host" "$d/host"
}

for rep in $(seq 1 "$REPEATS"); do
    run_one base "$REPO/output-openssl-lts" "$rep" || continue
    run_one grown-fs64 "$WORK/input-grown-fs64" "$rep" || true
    run_one pregrown "$WORK/input-pregrown" "$rep" || true
    run_one pregrown-nolazy "$WORK/input-pregrown-nolazy" "$rep" || true
    if [ -f "$RUNS/base-r$rep/sdcard.img" ]; then
        mk_mature_input "$RUNS/base-r$rep"
        run_one mature "$WORK/input-mature" "$rep" || true
    fi
done
echo "ALL DONE $(date -Is)"
