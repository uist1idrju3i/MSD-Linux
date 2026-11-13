#!/bin/sh
set -eu
dmesg -n 1
uname -a
cat /proc/cmdline
modprobe usb-storage
sleep 2
mkdir -p /run/pqc
mount -t vfat -o ro /dev/sda /run/pqc
export LD_LIBRARY_PATH=/run/pqc/default/usr/lib
cli=/run/pqc/default/usr/bin/openssl
"$cli" genpkey -algorithm ED25519 -out /run/ed.key
"$cli" pkey -in /run/ed.key -pubout -out /run/ed.pub
"$cli" req -x509 -newkey rsa:2048 -noenc -subj /CN=pqc-local-test -keyout /run/rsa.key -out /run/cert.pem -days 1
printf 'public test payload\n' > /run/payload
printf 'tampered payload\n' > /run/tampered
for variant in default no-ml-kem no-ml-dsa no-slh-dsa all-three; do
	echo "VARIANT $variant"
	export LD_LIBRARY_PATH="/run/pqc/$variant/usr/lib"
	cli="/run/pqc/$variant/usr/bin/openssl"
	sha256sum "$cli" "$LD_LIBRARY_PATH/libcrypto.so.3" "$LD_LIBRARY_PATH/libssl.so.3"
	"$cli" version -a
	"$cli" list -disabled
	"$cli" list -kem-algorithms
	"$cli" list -signature-algorithms
	"$cli" list -tls1_3 -tls-groups
	"$cli" pkeyutl -sign -rawin -inkey /run/ed.key -in /run/payload -out /run/sig
	"$cli" pkeyutl -verify -rawin -pubin -inkey /run/ed.pub -in /run/payload -sigfile /run/sig
	if "$cli" pkeyutl -verify -rawin -pubin -inkey /run/ed.pub -in /run/tampered -sigfile /run/sig; then
		exit 1
	fi
	"$cli" cms -sign -binary -in /run/payload -signer /run/cert.pem -inkey /run/rsa.key -outform DER -out /run/cms
	"$cli" cms -verify -binary -inform DER -in /run/cms -content /run/payload -CAfile /run/cert.pem -out /run/verified
	cmp /run/payload /run/verified
	echo "FUNCTIONAL_OK $variant"
done
export LD_LIBRARY_PATH=/run/pqc/default/usr/lib
cli=/run/pqc/default/usr/bin/openssl
for invalid in '' invalid-PQC-group; do
	if /run/pqc/hello "$invalid"; then
		exit 1
	fi
done
for groups in DEFAULT X25519 X25519MLKEM768 '?X25519MLKEM768:DEFAULT'; do
	/run/pqc/hello "$groups"
done
for repeat in 1 2 3 4 5; do
	echo "SPEED_REPEAT $repeat"
	"$cli" speed -seconds 1 -mr X25519 X25519MLKEM768
done
echo PQC_DONE
