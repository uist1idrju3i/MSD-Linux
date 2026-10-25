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
# The running version is the version of the real bundle; T8-T13 vary it.
V=$(sed -n '1s/^version \([1-9][0-9]*\)$/\1/p' "$W/good/manifest")
[ -n "$V" ] || { echo "the real bundle has no version line" >&2; exit 1; }
printf '%s\n' "$V" > "$W/version"
mk() { # name dir -> tar
	tar -cf "$W/$1.tar" -C "$2" rootfs.squashfs boot.vfat manifest manifest.sig; }
sign() { openssl pkeyutl -sign -rawin -inkey "$1" -in "$2/manifest" -out "$2/manifest.sig"; }
cp "$IMG/msd-update-bundle.tar" "$W/T0-valid.tar"
mkdir "$W/u"; cp "$W/good/"* "$W/u/"; : > "$W/u/manifest.sig"; mk T1-unsigned "$W/u"
mkdir "$W/k"; cp "$W/good/"* "$W/k/"; sign "$W/other.pem" "$W/k"; mk T2-wrongkey "$W/k"
mkdir "$W/r"; cp "$W/good/"* "$W/r/"; printf 'X' | dd of="$W/r/rootfs.squashfs" bs=1 seek=4096 conv=notrunc 2>/dev/null; mk T3-tampered-rootfs "$W/r"
mkdir "$W/m"; cp "$W/good/"* "$W/m/"
awk 'NR == 2 { c = substr($0, 1, 1); $0 = (c == "0" ? "1" : "0") substr($0, 2) } 1' "$W/good/manifest" > "$W/m/manifest"
if cmp -s "$W/good/manifest" "$W/m/manifest"; then echo "T4 tampering did not change the manifest" >&2; exit 1; fi
mk T4-tampered-manifest "$W/m"
sz=$(stat -c %s "$W/T0-valid.tar"); head -c $((sz/2)) "$W/T0-valid.tar" > "$W/T5-truncated-half.tar"
head -c $((sz-1024)) "$W/T0-valid.tar" > "$W/T6-truncated-tail.tar"
head -c $((sz-1024-65536)) "$W/T0-valid.tar" > "$W/T6b-truncated-member.tar"
# T7: validly signed bundle with different (older) content: boot.vfat of this build, rootfs from a 1-byte-changed copy, re-signed with the real dev key.
mkdir "$W/o"; cp "$W/good/"* "$W/o/"; printf 'O' | dd of="$W/o/rootfs.squashfs" bs=1 seek=8192 conv=notrunc 2>/dev/null
# resign DIR VERSION: rewrite the manifest with VERSION verbatim (empty omits the line) and sign it.
resign() {
	( cd "$1" && { [ -z "$2" ] || printf 'version %s\n' "$2"; sha256sum rootfs.squashfs boot.vfat; } > manifest )
	sign "$KEY" "$1"
}
resign "$W/o" "$V"; mk T7-other-signed "$W/o"
for d in older nover newer bad; do mkdir "$W/$d"; cp "$W/good/"* "$W/$d/"; done
resign "$W/older" "$((V - 1))"; mk T8-older "$W/older"; cp "$W/T8-older.tar" "$W/T9-older-allow.tar"
resign "$W/nover" ""; mk T10-unversioned "$W/nover"; cp "$W/T10-unversioned.tar" "$W/T11-unversioned-allow.tar"
resign "$W/newer" "$((V + 1))"; mk T12-newer "$W/newer"
resign "$W/bad" "0$V"; mk T13-malformed-allow "$W/bad"
[ -f "$CSV" ] || echo "rep,case,exit,inactive_root_changed,inactive_boot_changed,installed_state,message" > "$CSV"
for rep in $(seq 1 "$REPS"); do
 for t in T0-valid T1-unsigned T2-wrongkey T3-tampered-rootfs T4-tampered-manifest T5-truncated-half T6-truncated-tail T6b-truncated-member T7-other-signed T8-older T9-older-allow T10-unversioned T11-unversioned-allow T12-newer T13-malformed-allow; do
	R="$W/run"; rm -rf "$R"; mkdir -p "$R/dt" "$R/state" "$R/p1" "$R/bin"
	printf '#!/bin/sh\nexit 0\n' > "$R/bin/fsync"; chmod +x "$R/bin/fsync"
	printf '\000\000\000\002' > "$R/dt/partition"; printf '\000\000\000\000' > "$R/dt/tryboot"
	printf 'old-rootfs\n' > "$R/part6"; printf 'old-boot\n' > "$R/part3"
	opt=; case "$t" in *-allow) opt=--allow-downgrade ;; esac
	set +e
	PATH="$R/bin:$PATH" MSD_UPDATE_DT_DIR="$R/dt" MSD_UPDATE_P1_DIR="$R/p1" MSD_UPDATE_STATE_DIR="$R/state" \
	MSD_UPDATE_PARTITION_PREFIX="$R/part" MSD_UPDATE_KEY_PATH="$W/pub.pem" MSD_UPDATE_VERSION_PATH="$W/version" \
	/bin/sh "$UPDATER" install ${opt:+"$opt"} "$W/$t.tar" > "$R/out" 2>&1; ec=$?
	set -e
	rc=1; [ "$(cat "$R/part6")" = old-rootfs ] && rc=0
	bc=1; [ "$(cat "$R/part3")" = old-boot ] && bc=0
	st=$(cat "$R/state/installed" 2>/dev/null || echo none)
	msg=$(grep -E 'msd-update|error|failed|verif' "$R/out" | tail -1 | tr ',\n' ';  ')
	echo "$rep,$t,$ec,$rc,$bc,$st,$msg" >> "$CSV"
 done
done
