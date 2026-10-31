#!/bin/bash
# git bisect run 用の判定スクリプト。QEMU ツリーの各コミットを
# 製品条件（docker/qemu-patches 適用・run-qemu.sh と同じ起動）でビルドし、
# `MSD/Linux ready` までの実時間がしきい値以内かで判定する。
#
# 戻り値: 0=good（しきい値内に ready 到達）, 1=bad（超過またはタイムアウト）,
#         125=skip（ビルド失敗・バイナリなし）
#
# 前提の環境変数（run-bisect.sh が設定する）:
#   QEMU_SRC       QEMU の git ツリー
#   QEMU_BUILD     ビルドディレクトリ（configure 済み）
#   BISECT_WORK    ログ・作業ディレクトリ
#   REPO_ROOT      MSD-Linux リポジトリ（コンテナ内のパス）
# 任意:
#   BISECT_GOOD_LIMIT  ready までの実時間の上限秒（既定 45。超えた時点で打ち切り）
#   BISECT_TIMEOUT     上限の上限（既定 420）
#   PATCHES_DIR        パッチ群（既定 $REPO_ROOT/docker/qemu-patches）
set -u

SRC=${QEMU_SRC:?QEMU_SRC is required}
BUILD=${QEMU_BUILD:?QEMU_BUILD is required}
WORK=${BISECT_WORK:?BISECT_WORK is required}
REPO=${REPO_ROOT:?REPO_ROOT is required}
PATCHES_DIR=${PATCHES_DIR:-"$REPO/docker/qemu-patches"}
TIMEOUT=${BISECT_TIMEOUT:-420}
GOOD_LIMIT=${BISECT_GOOD_LIMIT:-45}
RUN_QEMU="$REPO/board/cardputerzero/qemu/run-qemu.sh"
LOG="$WORK/step-serial.log"

cd "$SRC" || exit 125
# 前ステップのパッチ残りを戻す（bisect が次コミットへ checkout するため必須）
git checkout -- . 2>/dev/null || git checkout -f HEAD 2>/dev/null
cleanup() { git checkout -- . 2>/dev/null; }
commit=$(git rev-parse --short HEAD)

# 製品ビルドと同じカスタムパッチを適用する。
# パッチ未適用の QEMU は起動がゲスト時刻 0.74s 付近で停滞する（bcm2835_pm
# 経由の deferred probe）ため必須。適用できないパッチは省略して継続する
# （0003 watchdog は 11.0.x ではコンテキストがずれて適用できない）。
skipped_patches=""
for p in "$PATCHES_DIR"/0*.patch; do
	if ! git apply "$p" 2>/dev/null; then
		if ! patch -p1 --batch --fuzz=3 --no-backup-if-mismatch -i "$p" >/dev/null 2>&1; then
			skipped_patches="$skipped_patches $(basename "$p")"
		fi
	fi
done

if ! ninja -C "$BUILD" qemu-system-aarch64 >"$WORK/step-build.log" 2>&1; then
	cleanup
	echo "step: $commit build failed -> skip"
	exit 125
fi
QEMU="$BUILD/qemu-system-aarch64"
if [ ! -x "$QEMU" ]; then
	cleanup
	echo "step: $commit no binary -> skip"
	exit 125
fi

: > "$LOG"
# run-qemu.sh が製品と同じ条件を組み立てる（イメージのコピーと 2 冪 padding、
# DTB の Bluetooth 無効化、machine/memory/DTB の既定値）
QEMU_SYSTEM_AARCH64="$QEMU" \
	QEMU_ICOUNT='shift=0,sleep=off' \
	QEMU_EXTRA_APPEND='initcall_debug printk.time=1 msd.sweep=1' \
	"$RUN_QEMU" >"$LOG" 2>&1 &
qpid=$!

result=bad
elapsed=0
while [ "$elapsed" -lt "$TIMEOUT" ]; do
	if ! kill -0 "$qpid" 2>/dev/null; then
		break
	fi
	if grep -q 'MSD/Linux ready' "$LOG" 2>/dev/null; then
		result=good
		break
	fi
	sleep 3
	elapsed=$((elapsed + 3))
	if [ "$elapsed" -gt "$GOOD_LIMIT" ]; then
		break
	fi
done
kill "$qpid" 2>/dev/null
wait "$qpid" 2>/dev/null

stamp=$(grep -oE '^\[[[:space:]]*[0-9.]+\]' "$LOG" 2>/dev/null | tail -1)
cleanup
if [ "$result" = good ]; then
	echo "step: $commit ready in ~${elapsed}s real ($stamp guest)${skipped_patches:+ [skip-patch:$skipped_patches]} -> good (limit ${GOOD_LIMIT}s)"
	exit 0
fi
echo "step: $commit over ${GOOD_LIMIT}s limit (${elapsed}s real, last $stamp)${skipped_patches:+ [skip-patch:$skipped_patches]} -> bad"
exit 1
