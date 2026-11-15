#!/bin/sh
# E1: /data 初回起動書き込みの帰属実験用 variant 入力を生成する。
# output-dwcause/input-<variant>/ に run.py --output が要求する構成を作る。
# 実行はリポジトリ最上位から（既存の入力は上書きしない）。
set -eu

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="${E1_OUTPUT_DIR:-$REPO/output-openssl-lts}"
WORK="${E1_WORK_DIR:-$REPO/output-dwcause}"
mkdir -p "$WORK"
IMGS="$OUT/images"
E2FS="$OUT/host/sbin"

BASE_IMG="$IMGS/sdcard.img"
[ -f "$BASE_IMG" ] || { echo "missing $BASE_IMG" >&2; exit 1; }

for variant in grown-fs64 pregrown pregrown-nolazy; do
    d="$WORK/input-$variant"
    if [ -e "$d" ] || [ -L "$d" ]; then
        echo "refusing to overwrite existing evidence: $d" >&2
        exit 1
    fi
done
TMP="$(mktemp -d "$WORK/prepare.XXXXXXXX")"
echo "intermediate evidence: $TMP"

mk_input() { # $1=variant名 $2=sdcard.imgのパス
    d="$WORK/input-$1"
    mkdir "$d"
    mkdir "$d/images"
    cp "$2" "$d/images/sdcard.img"
    for n in Image rootfs.squashfs bcm2710-rpi-cm0.dtb; do
        ln -s "$(realpath --relative-to="$d/images" "$IMGS/$n")" "$d/images/$n"
    done
    ln -s "$(realpath --relative-to="$d" "$OUT/.config")" "$d/.config"
    ln -s "$(realpath --relative-to="$d" "$OUT/host")" "$d/host"
    (cd "$d" && sha256sum images/sdcard.img images/Image images/rootfs.squashfs \
        images/bcm2710-rpi-cm0.dtb .config > inputs.sha256)
    echo "prepared $d"
}

IMG_SIZE="$(stat -c %s "$BASE_IMG")"
GROWN=1
while [ "$GROWN" -lt "$IMG_SIZE" ]; do GROWN=$((GROWN * 2)); done
GROWN_SEC=$((GROWN / 512))
echo "image=$IMG_SIZE grown=$GROWN sectors=$GROWN_SEC"

layout="$(sfdisk --json "$BASE_IMG" | python3 -c '
import json, sys
t = json.load(sys.stdin)["partitiontable"]
p4, p7 = (next(p for p in t["partitions"] if p["node"].endswith(str(n))) for n in (4, 7))
if (t["label"] != "dos" or t["sectorsize"] != 512 or
        p4["type"].lower() not in ("5", "f", "0f") or p7["type"].lower() != "83" or
        p7["size"] != 131072 or not 0 < p4["start"] < p7["start"] or
        p7["start"] + p7["size"] > p4["start"] + p4["size"]):
    sys.exit("unsupported E1 input layout (expected DOS/512, extended p4, 64 MiB p7)")
print(p4["start"], p7["start"], p7["size"])
')"
read -r P4_START P7_START P7_SIZE <<EOF
$layout
EOF
[ "$((P7_START + P7_SIZE))" -le "$((IMG_SIZE / 512))" ] || exit 1
[ "$P7_START" -lt "$GROWN_SEC" ] || exit 1
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
f="$TMP/grown-fs64.img"
cp "$BASE_IMG" "$f"
grow_partitions "$f"
mk_input grown-fs64 "$f"

# --- v-pregrown: 拡張 + host resize2fs 済み（新規グループは INODE_UNINIT のまま）
f="$TMP/pregrown.img"
cp "$BASE_IMG" "$f"
grow_partitions "$f"
dd if="$f" of="$TMP/p7.ext4" bs=512 skip="$P7_START" count="$NEW_P7_SIZE" status=none
"$E2FS/resize2fs" "$TMP/p7.ext4"
dd if="$TMP/p7.ext4" of="$f" bs=512 seek="$P7_START" conv=notrunc status=none
mk_input pregrown "$f"

# --- v-pregrown-nolazy: 拡張 + grown サイズで lazy-off mkfs（全グループ初期化済み）
f="$TMP/pregrown-nolazy.img"
cp "$BASE_IMG" "$f"
grow_partitions "$f"
"$E2FS/mke2fs" -t ext4 -F -b 4096 -L data \
    -E lazy_itable_init=0,lazy_journal_init=0 \
    "$TMP/data-grown-nolazy.ext4" "$((NEW_P7_SIZE * 512 / 1024))K"
dd if="$TMP/data-grown-nolazy.ext4" of="$f" bs=512 seek="$P7_START" conv=notrunc status=none
mk_input pregrown-nolazy "$f"

echo "done. mature variant は base 実測後に post-boot 画像から作る。"
