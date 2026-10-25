#!/bin/sh
# S10: msd-update bundle rejection with real build artifacts (host run).
# usage: s10-host.sh <repo> <images-dir> <dev-private-key> <reps> <csv>
set -eu
REPO=$1 IMG=$2 KEY=$3 REPS=$4 CSV=$5
UPDATER="$REPO/board/cardputerzero/rootfs-overlay/usr/sbin/msd-update"
W="$(mktemp -d)"; trap 'rm -rf "$W"' 0
openssl pkey -in "$KEY" -pubout -out "$W/pub.pem"
openssl genpkey -algorithm Ed25519 -out "$W/other.pem"
mkdir "$W/good"; tar -xf "$IMG/msd-update-bundle.tar" -C "$W/good"
mk() { # name dir -> tar
	tar -cf "$W/$1.tar" -C "$2" rootfs.squashfs boot.vfat manifest manifest.sig; }
sign() { openssl pkeyutl -sign -rawin -inkey "$1" -in "$2/manifest" -out "$2/manifest.sig"; }
cp "$IMG/msd-update-bundle.tar" "$W/T0-valid.tar"
mkdir "$W/u"; cp "$W/good/"* "$W/u/"; : > "$W/u/manifest.sig"; mk T1-unsigned "$W/u"
mkdir "$W/k"; cp "$W/good/"* "$W/k/"; sign "$W/other.pem" "$W/k"; mk T2-wrongkey "$W/k"
mkdir "$W/r"; cp "$W/good/"* "$W/r/"; printf 'X' | dd of="$W/r/rootfs.squashfs" bs=1 seek=4096 conv=notrunc 2>/dev/null; mk T3-tampered-rootfs "$W/r"
mkdir "$W/m"; cp "$W/good/"* "$W/m/"; sed -i '1s/^./0/' "$W/m/manifest"; mk T4-tampered-manifest "$W/m"
sz=$(stat -c %s "$W/T0-valid.tar"); head -c $((sz/2)) "$W/T0-valid.tar" > "$W/T5-truncated-half.tar"
head -c $((sz-1024)) "$W/T0-valid.tar" > "$W/T6-truncated-tail.tar"
head -c $((sz-1024-65536)) "$W/T0-valid.tar" > "$W/T6b-truncated-member.tar"
# T7: validly signed bundle with different (older) content: boot.vfat of this build, rootfs from a 1-byte-changed copy, re-signed with the real dev key.
mkdir "$W/o"; cp "$W/good/"* "$W/o/"; printf 'O' | dd of="$W/o/rootfs.squashfs" bs=1 seek=8192 conv=notrunc 2>/dev/null
( cd "$W/o" && sha256sum rootfs.squashfs boot.vfat > manifest ); sign "$KEY" "$W/o"; mk T7-other-signed "$W/o"
[ -f "$CSV" ] || echo "rep,case,exit,inactive_root_changed,inactive_boot_changed,installed_state,message" > "$CSV"
for rep in $(seq 1 "$REPS"); do
 for t in T0-valid T1-unsigned T2-wrongkey T3-tampered-rootfs T4-tampered-manifest T5-truncated-half T6-truncated-tail T6b-truncated-member T7-other-signed; do
	R="$W/run"; rm -rf "$R"; mkdir -p "$R/dt" "$R/state" "$R/p1" "$R/bin"
	printf '#!/bin/sh\nexit 0\n' > "$R/bin/fsync"; chmod +x "$R/bin/fsync"
	printf '\000\000\000\002' > "$R/dt/partition"; printf '\000\000\000\000' > "$R/dt/tryboot"
	printf 'old-rootfs\n' > "$R/part6"; printf 'old-boot\n' > "$R/part3"
	set +e
	PATH="$R/bin:$PATH" MSD_UPDATE_DT_DIR="$R/dt" MSD_UPDATE_P1_DIR="$R/p1" MSD_UPDATE_STATE_DIR="$R/state" \
	MSD_UPDATE_PARTITION_PREFIX="$R/part" MSD_UPDATE_KEY_PATH="$W/pub.pem" \
	/bin/sh "$UPDATER" install "$W/$t.tar" > "$R/out" 2>&1; ec=$?
	set -e
	rc=1; [ "$(cat "$R/part6")" = old-rootfs ] && rc=0
	bc=1; [ "$(cat "$R/part3")" = old-boot ] && bc=0
	st=$(cat "$R/state/installed" 2>/dev/null || echo none)
	msg=$(grep -E 'msd-update|error|failed|verif' "$R/out" | tail -1 | tr ',\n' ';  ')
	echo "$rep,$t,$ec,$rc,$bc,$st,$msg" >> "$CSV"
 done
done
