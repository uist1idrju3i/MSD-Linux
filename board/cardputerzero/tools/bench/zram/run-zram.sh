#!/bin/bash
# Usage (inside docker/msd-dev): run-zram.sh VARIANT_DIR LOG ALGORITHM|none [TIMEOUT]
# One QEMU boot of a test-only image; the guest hook prints =zram= lines.
set -uo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../../../.." && pwd)"
OUTPUT_DIR="${OUTPUT_DIR:-${REPO_ROOT}/output}"
export OUTPUT_DIR
vdir="$1"; log="$2"; alg="$3"; timeout_s="${4:-1800}"
img="$(mktemp -p "$vdir" run-XXXX.img)"
cp --sparse=always "$vdir/sdcard.img" "$img"
append=
[[ "$alg" == none ]] || append="msd.zram=${alg}${ZRAM_EXTRA_APPEND:+ ${ZRAM_EXTRA_APPEND}}"
QEMU_COPY_IMAGE=0 QEMU_EXTRA_APPEND="$append" \
	DTB_IMAGE="${OUTPUT_DIR}/images/bcm2710-rpi-cm0.dtb" \
	"${REPO_ROOT}/board/cardputerzero/qemu/run-qemu.sh" "$img" </dev/null >"$log" 2>&1 &
pid=$!
start=$(date +%s)
result=timeout
while kill -0 "$pid" 2>/dev/null; do
	if grep -aEq '=zram= (finished|skipped)' "$log"; then result=finished; break; fi
	(( $(date +%s) - start > timeout_s )) && break
	sleep 2
done
sleep 1
kill "$pid" 2>/dev/null; wait "$pid" 2>/dev/null
rm -f "$img"
echo "$(basename "$log") alg=$alg icount=${QEMU_ICOUNT:-none} result=$result elapsed=$(( $(date +%s) - start ))"
