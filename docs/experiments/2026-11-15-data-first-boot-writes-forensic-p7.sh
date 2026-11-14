#!/bin/sh
# E1 forensic: p7 領域の byte 差分を 3 者で比較する。
#   A = pristine   (output-openssl-lts/images/sdcard.img, 64MiB)
#   B = host-resize (input-pregrown の p7, 352MiB, INODE_UNINIT 残り)
#   C = post-boot  (runs/base-rN/sdcard.img の p7, guest が grow+resize+lazyinit 済み)
# 差分領域を dumpe2fs のグループ情報と突き合わせて帰属する。
set -eu
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="$REPO/output-openssl-lts"
WORK="$REPO/output-dwcause"
E2FS="$OUT/host/sbin"
P7_START=1376256
P7_SIZE=131072          # 64MiB
GROWN_P7_SIZE=720896    # 352MiB

run="$(cd "$(dirname "${1:-$WORK/runs/base-r1}")" && pwd)/$(basename "${1:-$WORK/runs/base-r1}")"
[ -f "$run/sdcard.img" ] || { echo "no post-boot image at $run" >&2; exit 1; }

mkdir -p "$WORK/forensic"
cd "$WORK/forensic"

dd if="$OUT/images/sdcard.img" of=p7-pristine.raw bs=512 \
    skip=$P7_START count=$P7_SIZE status=none
dd if="$WORK/input-pregrown/images/sdcard.img" of=p7-hostresized.raw bs=512 \
    skip=$P7_START count=$GROWN_P7_SIZE status=none
dd if="$run/sdcard.img" of=p7-postboot.raw bs=512 \
    skip=$P7_START count=$GROWN_P7_SIZE status=none

for f in p7-pristine p7-hostresized p7-postboot; do
    "$E2FS/e2image" -r "$f.raw" "$f.raw"
    "$E2FS/dumpe2fs" "$f.raw" > "$f.dumpe2fs" 2>/dev/null || true
done

# 先頭 64MiB 部分の比較: pristine vs postboot / hostresized vs postboot
for pair in "p7-pristine p7-postboot" "p7-hostresized p7-postboot"; do
    # shellcheck disable=SC2086  # intentional word splitting of "NAME1 NAME2"
    set -- $pair
    echo "=== cmp $1 vs $2 (first 64MiB) ==="
    cmp -l -n $((P7_SIZE * 512)) "$1.raw" "$2.raw" 2>/dev/null |
        awk '{print $1}' | python3 -c '
import sys
# 差分 byte offset を連続区間にまとめる
prev=-2; start=-1; total=0
for line in sys.stdin:
    n=int(line)
    if n!=prev+1:
        if start>=0: print(f"  range {start}-{prev} ({prev-start+1} bytes)")
        start=n
    prev=n; total+=1
if start>=0: print(f"  range {start}-{prev} ({prev-start+1} bytes)")
print(f"  total diff bytes: {total}")
'
done

# postboot 全体 vs hostresized 全体（grown 全域）
echo "=== cmp p7-hostresized vs p7-postboot (full 352MiB) ==="
cmp -l p7-hostresized.raw p7-postboot.raw 2>/dev/null | wc -l

echo "=== group flags after boot ==="
grep -E 'Group|UNINIT|ZEROED' p7-postboot.dumpe2fs | head -8
echo "=== done ==="
