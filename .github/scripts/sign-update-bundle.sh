#!/bin/bash
set -euo pipefail
umask 077

if [[ $# != 6 ]]; then
	printf 'Usage: %s unsigned.tar private.pem public.pem fingerprint tar-sha256 signed.tar\n' "$0" >&2
	exit 2
fi
unsigned="$(realpath -- "$1")"
private="$(realpath -- "$2")"
public="$(realpath -- "$3")"
fingerprint="$4"
tar_hash="$5"
output="$(realpath -m -- "$6")"
[[ "$fingerprint" =~ ^[0-9a-f]{64}$ && "$tar_hash" =~ ^[0-9a-f]{64}$ ]]
[[ -f "$private" && -r "$private" && ! -e "$output" ]]
actual="$(sha256sum -- "$unsigned")"
[[ "${actual%% *}" == "$tar_hash" ]]

stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT
python3 - "$unsigned" "$stage" <<'PY'
import hashlib
from pathlib import Path
import re
import shutil
import sys
import tarfile

archive, destination = sys.argv[1], Path(sys.argv[2])
expected = {"rootfs.squashfs", "boot.vfat", "manifest"}
with tarfile.open(archive, mode="r:") as source:
    members = source.getmembers()
    if (len(members) != 3 or {m.name for m in members} != expected
            or any(not m.isfile() or m.issparse() or m.size > 1024**3 for m in members)
            or any(m.name == "manifest" and m.size > 1024 for m in members)):
        raise SystemExit("Unexpected unsigned bundle members")
    for member in members:
        with source.extractfile(member) as data, (destination / member.name).open("xb") as out:
            shutil.copyfileobj(data, out)
manifest = (destination / "manifest").read_bytes()
pattern = (rb"version (0|[1-9][0-9]*)\n"
           rb"([0-9a-f]{64})  rootfs\.squashfs\n"
           rb"([0-9a-f]{64})  boot\.vfat\n")
match = re.fullmatch(pattern, manifest)
if match is None or len(match.group(1)) > 18:
    raise SystemExit("Invalid manifest format")
for name, digest in zip(("rootfs.squashfs", "boot.vfat"), match.groups()[1:]):
    with (destination / name).open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest().encode()
    if actual != digest:
        raise SystemExit("Manifest image hash mismatch")
PY

[[ "$(sed -n '1p' "$public")" == '-----BEGIN PUBLIC KEY-----' ]]
if grep -q 'PRIVATE KEY' "$public"; then
	printf '%s\n' 'Public-key input must not contain a private key.' >&2
	exit 1
fi
openssl pkey -pubin -in "$public" -text -noout | grep -q '^ED25519 Public-Key:'
openssl pkey -pubin -in "$public" -outform DER -out "$stage/public.der"
actual="$(sha256sum "$stage/public.der")"
[[ "${actual%% *}" == "$fingerprint" ]]
openssl pkey -in "$private" -passin pass: -check -noout >/dev/null
openssl pkey -in "$private" -passin pass: -pubout -outform DER -out "$stage/derived.der"
cmp "$stage/public.der" "$stage/derived.der"
openssl pkeyutl -sign -rawin -inkey "$private" -passin pass: \
	-in "$stage/manifest" -out "$stage/manifest.sig"
openssl pkeyutl -verify -rawin -pubin -inkey "$public" \
	-in "$stage/manifest" -sigfile "$stage/manifest.sig"
tar -C "$stage" -cf "$stage/signed.tar" rootfs.squashfs boot.vfat manifest manifest.sig
mv -- "$stage/signed.tar" "$output"
