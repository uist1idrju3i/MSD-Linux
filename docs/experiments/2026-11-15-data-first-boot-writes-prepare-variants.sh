#!/bin/sh
# E1: /data 初回起動書き込みの帰属実験用 variant 入力を生成する。
# output-dwcause/input-<variant>/ に run.py --output が要求する構成を作る。
# 実行はリポジトリ最上位から: sh output-dwcause/prepare-variants.sh
set -eu

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="$REPO/output-openssl-lts"
WORK="$REPO/output-dwcause"
IMGS="$OUT/images"
E2FS="$OUT/host/sbin"

BASE_IMG="$IMGS/sdcard.img"
[ -f "$BASE_IMG" ] || { echo "missing $BASE_IMG" >&2; exit 1; }

mk_input() { # $1=variant名 $2=sdcard.imgのパス
    d="$WORK/input-$1"
    rm -rf "$d"
    mkdir -p "$d/images"
    cp "$2" "$d/images/sdcard.img"
    ln -sf "$IMGS/Image" "$d/images/Image"
    ln -sf "$IMGS/rootfs.squashfs" "$d/images/rootfs.squashfs"
    ln -sf "$IMGS/bcm2710-rpi-cm0.dtb" "$d/images/bcm2710-rpi-cm0.dtb"
    ln -sf "$OUT/.config" "$d/.config"
    ln -sf "$OUT/host" "$d/host"
    echo "prepared $d"
}

IMG_SIZE="$(stat -c %s "$BASE_IMG")"
GROWN=1
while [ "$GROWN" -lt "$IMG_SIZE" ]; do GROWN=$((GROWN * 2)); done
GROWN_SEC=$((GROWN / 512))
echo "image=$IMG_SIZE grown=$GROWN sectors=$GROWN_SEC"

# genimage レイアウト (sfdisk -J で確認済み): p4 ext start=303104 type=f, p7 start=1376256 type=83
P4_START=303104
P7_START=1376256
NEW_P4_SIZE=$((GROWN_SEC - P4_START))
NEW_P7_SIZE=$((GROWN_SEC - P7_START))
echo "new p4 size=$NEW_P4_SIZE new p7 size=$NEW_P7_SIZE"

grow_partitions() { # msd-data-grow と同じ手順: p4 を先に末尾まで、その後 p7
    truncate -s "$GROWN" "$1"
    printf 'start=%s, size=%s, type=f\n' "$P4_START" "$NEW_P4_SIZE" |
        sfdisk --no-reread -N 4 "$1" >/dev/null
    printf 'start=%s, size=%s, type=83\n' "$P7_START" "$NEW_P7_SIZE" |
        sfdisk --no-reread -N 7 "$1" >/dev/null
}

# --- v-grown-fs64: パーティションだけ拡張（FS は 64M のまま → guest が resize2fs）
f="$WORK/tmp-grown-fs64.img"
cp "$BASE_IMG" "$f"
grow_partitions "$f"
mk_input grown-fs64 "$f"

# --- v-pregrown: 拡張 + host resize2fs 済み（新規グループは INODE_UNINIT のまま）
f="$WORK/tmp-pregrown.img"
cp "$BASE_IMG" "$f"
grow_partitions "$f"
dd if="$f" of="$WORK/tmp-p7.ext4" bs=512 skip="$P7_START" count="$NEW_P7_SIZE" status=none
"$E2FS/resize2fs" "$WORK/tmp-p7.ext4"
dd if="$WORK/tmp-p7.ext4" of="$f" bs=512 seek="$P7_START" conv=notrunc status=none
mk_input pregrown "$f"

# --- v-pregrown-nolazy: 拡張 + grown サイズで lazy-off mkfs（全グループ初期化済み）
f="$WORK/tmp-pregrown-nolazy.img"
cp "$BASE_IMG" "$f"
grow_partitions "$f"
"$E2FS/mke2fs" -t ext4 -F -b 4096 -L data \
    -E lazy_itable_init=0,lazy_journal_init=0 \
    "$WORK/tmp-data-grown-nolazy.ext4" "$((NEW_P7_SIZE * 512 / 1024))K"
dd if="$WORK/tmp-data-grown-nolazy.ext4" of="$f" bs=512 seek="$P7_START" conv=notrunc status=none
mk_input pregrown-nolazy "$f"

rm -f "$WORK"/tmp-*.img "$WORK"/tmp-*.ext4
echo "done. mature variant は base 実測後に post-boot 画像から作る。"
