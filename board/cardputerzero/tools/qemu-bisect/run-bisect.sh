#!/bin/bash
# QEMU の icount 起動時間回帰を git bisect するドライバー。
# debian:trixie-slim コンテナ内で QEMU をビルドし、step.sh で各コミットを判定する。
#
# 使い方:
#   board/cardputerzero/tools/qemu-bisect/run-bisect.sh <bad-ref> <good-ref>
# 例: board/cardputerzero/tools/qemu-bisect/run-bisect.sh v11.1.2 v11.0.2
#
# 任意の環境変数:
#   BISECT_GOOD_LIMIT  判定しきい値（秒、既定 45。step.sh に引き継ぐ）
#   QEMU_BISECT_WORK   作業ディレクトリ（既定 output/qemu-bisect）
set -euo pipefail

BAD_REF=${1:?usage: run-bisect.sh <bad-ref> <good-ref>}
GOOD_REF=${2:?usage: run-bisect.sh <bad-ref> <good-ref>}
REPO_ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
WORK="${QEMU_BISECT_WORK:-$REPO_ROOT/output/qemu-bisect}"
GOOD_LIMIT=${BISECT_GOOD_LIMIT:-45}
TOOLS_DIR=board/cardputerzero/tools/qemu-bisect

mkdir -p "$WORK"

# コンテナ内で実行するセットアップ＋bisect 本体。リポジトリは /work にマウントする
read -r -d '' inner <<EOS || true
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq >/dev/null
apt-get install -y -qq --no-install-recommends \
	git build-essential ninja-build meson pkg-config \
	libglib2.0-dev libpixman-1-dev libslirp-dev libfdt-dev libzstd-dev \
	python3-venv python3-setuptools ca-certificates \
	device-tree-compiler patch >/dev/null
git config --global --add safe.directory '*'
SRC=/bisect/qemu-src
BUILD=/bisect/build
if [ ! -d "\$SRC/.git" ]; then
	git clone --filter=blob:none https://gitlab.com/qemu-project/qemu.git "\$SRC"
fi
mkdir -p "\$BUILD"
if [ ! -f "\$BUILD/build.ninja" ]; then
	( cd "\$BUILD" && "\$SRC/configure" \
		--target-list=aarch64-softmmu \
		--enable-slirp --enable-fdt=system \
		--disable-docs --disable-user --disable-gtk --disable-sdl --disable-vnc )
fi
cd "\$SRC"
git checkout -f -q "$BAD_REF"
git bisect reset >/dev/null 2>&1 || true
git bisect start "$BAD_REF" "$GOOD_REF"
export QEMU_SRC="\$SRC" QEMU_BUILD="\$BUILD" BISECT_WORK=/bisect \
	REPO_ROOT=/work BISECT_GOOD_LIMIT="$GOOD_LIMIT"
git bisect run /work/$TOOLS_DIR/step.sh
git bisect log
EOS

exec docker run --rm \
	-v "$REPO_ROOT:/work" \
	-v "$WORK:/bisect" \
	-e "BISECT_WORK=/bisect" \
	debian:trixie-slim bash -c "$inner"
