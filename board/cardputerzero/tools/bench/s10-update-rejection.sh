#!/usr/bin/env bash
# S10: give unsigned, wrongly signed, tampered, truncated and re-signed
# bundles to msd-update inside the QEMU guest and record whether the inactive
# slot and the install state changed. Cases T8-T13 check the signed manifest
# version against the running version, with and without --allow-downgrade
# (case names ending in -allow). Writes one CSV row per case and boot.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../../.." && pwd -P)"
OUTPUT_DIR="${OUTPUT_DIR:-${REPO_ROOT}/output}"
IMAGES_DIR="${OUTPUT_DIR}/images"
SIGNING_KEY="${MSD_UPDATE_SIGNING_KEY:-${OUTPUT_DIR}/msd-update-dev-key.pem}"
LOG_ROOT="${S10_LOG_DIR:-${OUTPUT_DIR}/qemu-logs/s10}"
RUNS="${S10_RUNS:-5}"
CSV="${S10_CSV:-${LOG_ROOT}/s10.csv}"
TIMEOUT="${S10_TIMEOUT:-900}"
CASES="T0-valid T1-unsigned T2-wrongkey T3-tampered-rootfs T4-tampered-manifest T5-truncated-half T6-truncated-tail T6b-truncated-member T7-other-signed T8-older T9-older-allow T10-unversioned T11-unversioned-allow T12-newer T13-malformed-allow"

[[ -e "$CSV" ]] && { printf 'Refusing to overwrite %s\n' "$CSV" >&2; exit 1; }
mkdir -p "$LOG_ROOT"
build="${LOG_ROOT}/build-$(date -u +%Y%m%dT%H%M%S)"
mkdir "$build"
unsquashfs="${OUTPUT_DIR}/host/bin/unsquashfs"
mksquashfs="${OUTPUT_DIR}/host/bin/mksquashfs"
sfdisk="${OUTPUT_DIR}/host/sbin/sfdisk"

# Flip the first hex digit of the rootfs hash (line 2, after the version line).
tamper_hash_line() {
	awk 'NR == 2 { c = substr($0, 1, 1); $0 = (c == "0" ? "1" : "0") substr($0, 2) } 1' "$1" >"$1.new"
	if cmp -s "$1" "$1.new"; then printf 'Tampering did not change %s\n' "$1" >&2; exit 1; fi
	mv "$1.new" "$1"
}
sign() { openssl pkeyutl -sign -rawin -inkey "$1" -in "$2/manifest" -out "$2/manifest.sig"; }
pack() { tar -cf "$1" -C "$2" rootfs.squashfs boot.vfat manifest manifest.sig; }
# payload_dir DIR VERSION: VERSION is written verbatim; an empty one omits the line.
payload_dir() {
	mkdir -p "$1"
	head -c 1048576 /dev/urandom >"$1/rootfs.squashfs"
	head -c 1048576 /dev/urandom >"$1/boot.vfat"
	(
		cd "$1"
		if [[ -n "$2" ]]; then printf 'version %s\n' "$2"; fi
		sha256sum rootfs.squashfs boot.vfat
	) >"$1/manifest"
	sign "$SIGNING_KEY" "$1"
}

bundles="${build}/target/usr/share/msd-s10"
"$unsquashfs" -no-progress -no-xattrs -d "${build}/target" "${IMAGES_DIR}/rootfs.squashfs" \
	>"${build}/unsquashfs.log" 2>&1 || grep -Fq 'failed to change uid and gids' "${build}/unsquashfs.log"
mkdir -p "$bundles"
running_version="$(cat "${build}/target/etc/msd-update/version")"
[[ "$running_version" =~ ^[1-9][0-9]{0,17}$ ]] ||
	{ printf 'Invalid running version in rootfs: %s\n' "$running_version" >&2; exit 1; }
printf '%s\n' "$running_version" >"${build}/running-version"
install -m 0755 "${SCRIPT_DIR}/S97zz-s10test" "${build}/target/etc/init.d/S97zz-s10test"
openssl genpkey -algorithm Ed25519 -out "${build}/other-key.pem"
w="${build}/bundles"
payload_dir "$w/good" "$running_version"
pack "$bundles/T0-valid.tar" "$w/good"
cp -r "$w/good" "$w/u"; : >"$w/u/manifest.sig"; pack "$bundles/T1-unsigned.tar" "$w/u"
cp -r "$w/good" "$w/k"; sign "${build}/other-key.pem" "$w/k"; pack "$bundles/T2-wrongkey.tar" "$w/k"
cp -r "$w/good" "$w/r"; printf 'X' | dd of="$w/r/rootfs.squashfs" bs=1 seek=4096 conv=notrunc status=none
pack "$bundles/T3-tampered-rootfs.tar" "$w/r"
cp -r "$w/good" "$w/m"; tamper_hash_line "$w/m/manifest"; pack "$bundles/T4-tampered-manifest.tar" "$w/m"
size="$(stat -c %s "$bundles/T0-valid.tar")"
head -c $((size / 2)) "$bundles/T0-valid.tar" >"$bundles/T5-truncated-half.tar"
head -c $((size - 1024)) "$bundles/T0-valid.tar" >"$bundles/T6-truncated-tail.tar"
head -c $((size - 1024 - 262144)) "$bundles/T0-valid.tar" >"$bundles/T6b-truncated-member.tar"
payload_dir "$w/other" "$running_version"; pack "$bundles/T7-other-signed.tar" "$w/other"
payload_dir "$w/older" "$((running_version - 1))"; pack "$bundles/T8-older.tar" "$w/older"
cp "$bundles/T8-older.tar" "$bundles/T9-older-allow.tar"
payload_dir "$w/nover" ""; pack "$bundles/T10-unversioned.tar" "$w/nover"
cp "$bundles/T10-unversioned.tar" "$bundles/T11-unversioned-allow.tar"
payload_dir "$w/newer" "$((running_version + 1))"; pack "$bundles/T12-newer.tar" "$w/newer"
payload_dir "$w/bad" "0${running_version}"; pack "$bundles/T13-malformed-allow.tar" "$w/bad"
(cd "$bundles" && sha256sum T*.tar) >"${build}/bundles.sha256"

info="$("$unsquashfs" -s "${IMAGES_DIR}/rootfs.squashfs")"
comp="$(awk '$1 == "Compression" { print $2; exit }' <<<"$info")"
bsize="$(awk '$1 == "Block" && $2 == "size" { print $3; exit }' <<<"$info")"
"$mksquashfs" "${build}/target" "${build}/rootfs-s10.squashfs" -noappend -all-root \
	-no-xattrs -no-progress -comp "$comp" -b "$bsize" >"${build}/mksquashfs.log" 2>&1
template="${build}/sdcard-s10.img"
cp --sparse=always "${IMAGES_DIR}/sdcard.img" "$template"
padded=1; while ((padded < $(stat -c %s "$template"))); do padded=$((padded * 2)); done
truncate -s "$padded" "$template"
read -r a_start a_size b_start <<<"$("$sfdisk" --json "$template" | python3 -c '
import json, sys
p = json.load(sys.stdin)["partitiontable"]["partitions"]
assert len(p) == 7, len(p)
print(p[4]["start"], p[4]["size"], p[5]["start"])')"
(($(stat -c %s "${build}/rootfs-s10.squashfs") <= a_size * 512)) || { echo 'test rootfs too large' >&2; exit 1; }
dd if="${build}/rootfs-s10.squashfs" of="$template" bs=512 seek="$a_start" conv=notrunc status=none
sha256sum "${IMAGES_DIR}/sdcard.img" "${IMAGES_DIR}/rootfs.squashfs" "${IMAGES_DIR}/Image" \
	"${build}/rootfs-s10.squashfs" "$SCRIPT_DIR/S97zz-s10test" "${BASH_SOURCE[0]}" >"${build}/inputs.sha256"
: "$b_start"

printf 'run,case,exit,root_changed,boot_changed,state,message,valid,note\n' >"$CSV"
for run in $(seq 1 "$RUNS"); do
	disk="${build}/run${run}.img"; log="${build}/run${run}.log"
	cp --sparse=always "$template" "$disk"
	QEMU_EXTRA_APPEND="msd.s10test=1" QEMU_COPY_IMAGE=0 OUTPUT_DIR="$OUTPUT_DIR" \
		"${REPO_ROOT}/board/cardputerzero/qemu/run-qemu.sh" "$disk" >"$log" 2>&1 &
	pid=$!
	deadline=$((SECONDS + TIMEOUT)); note=""
	until grep -aq 'msd-s10: finished' "$log"; do
		if ((SECONDS > deadline)) || ! kill -0 "$pid" 2>/dev/null; then note=timeout; break; fi
		sleep 2
	done
	kill -KILL "$pid" 2>/dev/null || true; wait "$pid" 2>/dev/null || true
	rm -f "$disk"
	for c in $CASES; do
		line="$(tr -d '\r' <"$log" | grep -aF "msd-s10: case=$c " | tail -n 1 || true)"
		if [[ -z "$line" ]]; then
			printf '%s,%s,,,,,,0,%s\n' "$run" "$c" "${note:-missing}" >>"$CSV"; continue
		fi
		val() { sed -n "s/.* $1=\([^ ]*\).*/\1/p" <<<"$line"; }
		msg="$(sed -n 's/.* message=//p' <<<"$line")"
		printf '%s,%s,%s,%s,%s,%s,%s,1,%s\n' "$run" "$c" "$(val exit)" "$(val root_changed)" \
			"$(val boot_changed)" "$(val state)" "$msg" "$note" >>"$CSV"
	done
	sha256sum "$log" >>"${build}/logs.sha256"
done
printf 'CSV: %s\n' "$CSV"
