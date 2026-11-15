#!/bin/sh
# mksquashfs compression matrix: block_size x level for zstd, plus codec baselines.
# Usage: run-mksquashfs-matrix.sh <srcdir> <outdir>
set -eu
SRC=$1; OUT=$2
mkdir -p "$OUT"
CSV="$OUT/matrix.csv"
echo "codec,block,level,image_bytes,build_ms" > "$CSV"
for bs in 16K 32K 64K 128K 256K 512K 1M; do
  for lvl in 1 3 9 15 19 22; do
    img="$OUT/zstd-b${bs}-l${lvl}.sqfs"
    t0=$(date +%s%N)
    mksquashfs "$SRC" "$img" -noappend -quiet -comp zstd -b "$bs" -Xcompression-level "$lvl" -all-root -no-progress
    t1=$(date +%s%N)
    sz=$(stat -c %s "$img")
    echo "zstd,$bs,$lvl,$sz,$(( (t1-t0)/1000000 ))" >> "$CSV"
  done
done
# codec baselines at default block 128K
for spec in "xz:-Xbcj arm" "lz4:" "gzip:" "zstd:"; do
  codec=${spec%%:*}; extra=${spec#*:}
  img="$OUT/${codec}-b128K-default.sqfs"
  t0=$(date +%s%N)
  # shellcheck disable=SC2086
  mksquashfs "$SRC" "$img" -noappend -quiet -comp "$codec" -b 128K $extra -all-root -no-progress
  t1=$(date +%s%N)
  sz=$(stat -c %s "$img")
  echo "$codec,128K,default,$sz,$(( (t1-t0)/1000000 ))" >> "$CSV"
done
