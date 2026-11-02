#!/bin/bash
# Boot-time comparison of Buildroot and Yocto images under QEMU.
# Run inside docker/msd-dev: docker/msd-dev board/cardputerzero/tools/bench/yocto-compare/run-compare.sh ...
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../../../../" && pwd)"
RUN_QEMU="${REPO_ROOT}/board/cardputerzero/qemu/run-qemu.sh"

usage() {
	printf 'Usage: %s --condition NAME --kernel Image --dtb DTB --image IMG --root-dev DEV --root-fstype FS --ready-marker TEXT --mode icount|tcg --runs N --out DIR [--timeout SEC]\n' "$0" >&2
}

condition='' kernel='' dtb='' image='' root_dev='' root_fstype='' ready_marker='' mode='' runs='' out='' timeout=600
while (($#)); do
	(($# >= 2)) || { usage; exit 2; }
	case "$1" in
		--condition) condition="$2" ;;
		--kernel) kernel="$2" ;;
		--dtb) dtb="$2" ;;
		--image) image="$2" ;;
		--root-dev) root_dev="$2" ;;
		--root-fstype) root_fstype="$2" ;;
		--ready-marker) ready_marker="$2" ;;
		--mode) mode="$2" ;;
		--runs) runs="$2" ;;
		--out) out="$2" ;;
		--timeout) timeout="$2" ;;
		*) usage; exit 2 ;;
	esac
	shift 2
done
for v in condition kernel dtb image root_dev root_fstype ready_marker mode runs out; do
	[[ -n "${!v}" ]] || { usage; exit 2; }
done
case "$mode" in
	icount) icount='shift=0,sleep=off' ;;
	tcg) icount= ;;
	*) usage; exit 2 ;;
esac

mkdir -p -- "$out"
csv="${out}/results.csv"
[[ -f "$csv" ]] || printf 'condition,mode,boot,first_boot,t_root,t_init,t_ready,login,wall_login_s,result\n' >"$csv"

work_image="${out}/${condition}-${mode}.img"
cp --sparse=always -- "$image" "$work_image"
size="$(stat -c '%s' "$work_image")"
padded=1
while ((padded < size)); do padded=$((padded * 2)); done
truncate -s "$padded" "$work_image"
{
	printf 'condition=%s mode=%s icount=%s\n' "$condition" "$mode" "${icount:-off}"
	sha256sum -- "$kernel" "$dtb" "$image"
	"${QEMU_SYSTEM_AARCH64:-qemu-system-aarch64}" --version | head -n 1
} >"${out}/${condition}-${mode}.provenance"

for ((boot = 0; boot <= runs; boot++)); do
	log="${out}/${condition}-${mode}-boot${boot}.log"
	: >"$log"
	start_ns="$(date +%s%N)"
	env KERNEL_IMAGE="$kernel" DTB_IMAGE="$dtb" ROOT_DEVICE="$root_dev" \
		ROOT_FSTYPE="$root_fstype" QEMU_COPY_IMAGE=0 QEMU_HASH_IMAGE=0 \
		QEMU_EXTRA_APPEND='printk.time=1 msd.sweep=1' QEMU_ICOUNT="$icount" \
		"$RUN_QEMU" "$work_image" </dev/null >"$log" 2>&1 &
	pid=$!
	result=timeout login=0 wall=
	deadline=$((SECONDS + timeout))
	while ((SECONDS < deadline)); do
		sleep 0.2
		if grep -aFq -- "$ready_marker" "$log" && grep -aEq '(^|[[:space:]])[^[:space:]]* ?login:' "$log"; then
			end_ns="$(date +%s%N)"
			wall="$(awk -v a="$end_ns" -v b="$start_ns" 'BEGIN { printf "%.1f", (a - b) / 1e9 }')"
			login=1 result=pass
			break
		fi
		if ! kill -0 "$pid" 2>/dev/null; then
			result=exited
			break
		fi
	done
	kill "$pid" 2>/dev/null || true
	wait "$pid" 2>/dev/null || true
	python3 - "$log" "$ready_marker" "$csv" "$condition" "$mode" "$boot" "$login" "$wall" "$result" <<'PY'
import re, sys
log, marker, csv, cond, mode, boot, login, wall, result = sys.argv[1:]
ts = re.compile(r"^\[\s*(\d+\.\d+)\]\s?(.*)$")
found = {}
for line in open(log, errors="replace"):
    m = ts.match(line.rstrip("\r\n"))
    if not m:
        continue
    t, msg = m.group(1), m.group(2)
    if "t_root" not in found and msg.startswith("VFS: Mounted root"):
        found["t_root"] = t
    if "t_init" not in found and "Run /sbin/init as init process" in msg:
        found["t_init"] = t
    if "t_ready" not in found and msg.strip() == marker:
        found["t_ready"] = t
if result == "pass" and "t_ready" not in found:
    result = "missing_t_ready"
row = [cond, mode, boot, "1" if boot == "0" else "0", found.get("t_root", ""),
       found.get("t_init", ""), found.get("t_ready", ""), login, wall, result]
with open(csv, "a") as f:
    f.write(",".join(row) + "\n")
print(",".join(row))
PY
done
rm -f -- "$work_image"
