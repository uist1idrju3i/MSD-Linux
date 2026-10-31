#!/bin/bash
# 指定した QEMU バージョンを製品条件（docker/qemu-patches 適用）でビルドする。
# 成果物: $QEMU_BISECT_WORK/build/qemu-system-aarch64
#
# 使い方:
#   board/cardputerzero/tools/qemu-bisect/build-qemu.sh v11.0.2
# ビルド済みバイナリは QEMU_SYSTEM_AARCH64 で run-qemu.sh / kernel-variant-sweep.sh から使う。
#
# 任意の環境変数:
#   QEMU_BISECT_WORK  作業ディレクトリ（既定 output/qemu-bisect）
set -euo pipefail

REF=${1:?usage: build-qemu.sh <qemu-ref>}
REPO_ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
WORK="${QEMU_BISECT_WORK:-$REPO_ROOT/output/qemu-bisect}"

mkdir -p "$WORK"

read -r -d '' inner <<EOS || true
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq >/dev/null
apt-get install -y -qq --no-install-recommends \
	git build-essential ninja-build meson pkg-config \
	libglib2.0-dev libpixman-1-dev libslirp-dev libfdt-dev libzstd-dev \
	python3-venv python3-setuptools ca-certificates patch >/dev/null
git config --global --add safe.directory '*'
SRC=/bisect/qemu-src
BUILD=/bisect/build
if [ ! -d "\$SRC/.git" ]; then
	git clone --filter=blob:none https://gitlab.com/qemu-project/qemu.git "\$SRC"
fi
cd "\$SRC"
git checkout -f -q "$REF"
mkdir -p "\$BUILD"
if [ ! -f "\$BUILD/build.ninja" ]; then
	( cd "\$BUILD" && "\$SRC/configure" \
		--target-list=aarch64-softmmu \
		--enable-slirp --enable-fdt=system \
		--disable-docs --disable-user --disable-gtk --disable-sdl --disable-vnc )
fi
for p in /work/docker/qemu-patches/0*.patch; do
	if ! git apply "\$p" 2>/dev/null; then
		patch -p1 --batch --fuzz=3 --no-backup-if-mismatch -i "\$p" >/dev/null 2>&1 \
			|| echo "skip patch (does not apply on $REF): \$(basename "\$p")"
	fi
done
ninja -C "\$BUILD" qemu-system-aarch64
"\$BUILD/qemu-system-aarch64" --version | head -1
EOS

exec docker run --rm \
	-v "$REPO_ROOT:/work" \
	-v "$WORK:/bisect" \
	debian:trixie-slim bash -c "$inner"
