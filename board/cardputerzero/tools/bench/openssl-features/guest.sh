#!/bin/sh
set -eu

base=/run/openssl-features
mkdir -p "$base/logs"
cd "$base"
export HOME="$base" TMPDIR="$base"
unset OPENSSL_CONF OPENSSL_MODULES
server=
cleanup()
{
	if [ -n "$server" ]; then
		kill "$server" 2>/dev/null || :
		wait "$server" 2>/dev/null || :
	fi
}
trap cleanup EXIT

bounded()
{
	"$@" &
	child=$!
	(sleep 30; kill -KILL "$child" 2>/dev/null) >/dev/null 2>&1 &
	watchdog=$!
	status=0
	wait "$child" || status=$?
	kill "$watchdog" 2>/dev/null || :
	wait "$watchdog" 2>/dev/null || :
	return "$status"
}

check()
{
	name=$1
	shift
	rc=0
	"$@" >"logs/$name.log" 2>&1 || rc=$?
	printf 'FEATURE_RESULT case=%s rc=%s\n' "$name" "$rc"
	test "$rc" -eq 0
}

reject()
{
	name=$1
	pattern=$2
	shift 2
	rc=0
	"$@" >"logs/$name.log" 2>&1 || rc=$?
	test "$rc" -ne 0
	test "$rc" -lt 124
	grep -qi "$pattern" "logs/$name.log"
	printf 'rejected_exit=%s\n' "$rc" >>"logs/$name.log"
	printf 'FEATURE_RESULT case=%s rc=0\n' "$name"
}

printf '\n'
echo MODULE_INVENTORY_BEGIN
cat /proc/modules
echo MODULE_INVENTORY_END
if [ "$1" = A ]; then
	openssl version -a >logs/version.log
	sha256sum /usr/bin/openssl /usr/lib/libcrypto.so.3 /usr/lib/libssl.so.3 \
		/usr/lib/ossl-modules/legacy.so /etc/ssl/openssl.cnf >logs/binaries.log
	check providers openssl list -providers
	if grep -q legacy logs/providers.log; then exit 1; fi
	openssl list -providers -provider default -provider legacy >logs/explicit-providers.log
	grep -q legacy logs/explicit-providers.log
	grep -q default logs/explicit-providers.log
	for type in cipher digest public-key kdf kem signature mac asymcipher key-exchange; do
		openssl list "-$type-algorithms" -provider default -provider legacy >"logs/$type-algorithms.log"
	done
	check c1-minimum grep -q '^MinProtocol = TLSv1.2$' /etc/ssl/openssl.cnf
	check c1-security grep -q '^CipherString = DEFAULT:@SECLEVEL=2$' /etc/ssl/openssl.cnf
	openssl genpkey -algorithm Ed25519 -out update.key >logs/keygen.log 2>&1
	openssl pkey -in update.key -pubout -out update.pub
	printf 'signed payload\n' >payload
	openssl pkeyutl -sign -rawin -inkey update.key -in payload -out payload.sig
	check ed25519 openssl pkeyutl -verify -rawin -pubin -inkey update.pub -in payload -sigfile payload.sig
	printf 'tampered payload\n' >tampered
	reject ed25519-reject 'signature verification failure' openssl pkeyutl -verify -rawin \
		-pubin -inkey update.pub -in tampered -sigfile payload.sig
	mkdir -p bundle dt state
	printf '\000\000\000\002' >dt/partition
	printf '\000\000\000\000' >dt/tryboot
	printf '100\n' >version
	cp payload bundle/rootfs.squashfs
	cp payload bundle/boot.vfat
	(cd bundle; printf 'version 100\n'; sha256sum rootfs.squashfs boot.vfat) >bundle/manifest
	openssl pkeyutl -sign -rawin -inkey update.key -in bundle/manifest -out bundle/manifest.sig
	tar -cf valid.tar -C bundle rootfs.squashfs boot.vfat manifest manifest.sig
	printf 'invalid signature\n' >bundle/manifest.sig
	tar -cf invalid.tar -C bundle rootfs.squashfs boot.vfat manifest manifest.sig
	export MSD_UPDATE_DT_DIR="$base/dt" MSD_UPDATE_STATE_DIR="$base/state"
	export MSD_UPDATE_PARTITION_PREFIX="$base/slot" MSD_UPDATE_KEY_PATH="$base/update.pub"
	export MSD_UPDATE_VERSION_PATH="$base/version"
	: >slot3
	: >slot6
	check update-valid msd-update install "$base/valid.tar"
	cmp bundle/rootfs.squashfs slot6
	cmp bundle/boot.vfat slot3
	sha256sum slot3 slot6 state/installed >before-invalid
	reject update-invalid 'signature verification failed' msd-update install "$base/invalid.tar"
	sha256sum slot3 slot6 state/installed >after-invalid
	check update-unchanged cmp before-invalid after-invalid
	head -c 32 /dev/urandom >luks.key
	truncate -s 64M luks.img
	check argon2id-format cryptsetup --debug luksFormat --type luks2 --batch-mode --key-file luks.key \
		--pbkdf argon2id --pbkdf-force-iterations 4 --pbkdf-memory 8192 --pbkdf-parallel 1 luks.img
	cryptsetup luksDump luks.img >logs/luks-dump.log
	check argon2id-metadata grep -q argon2id logs/luks-dump.log
	check argon2id-open cryptsetup --debug open --key-file luks.key luks.img features-test
	cryptsetup status features-test >logs/luks-status.log
	check argon2id-close cryptsetup close features-test
	rm luks.img
	openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:P-256 -noenc -subj /CN=localhost \
		-addext subjectAltName=DNS:localhost -keyout tls.key -out cert.pem -days 1 >logs/cert.log 2>&1
	check x509 openssl verify -CAfile cert.pem cert.pem
	openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:P-256 -noenc -subj /CN=untrusted \
		-keyout other.key -out other.pem -days 1 >logs/other-cert.log 2>&1
	reject x509-reject 'self-signed certificate' openssl verify -CAfile cert.pem other.pem
	check cms-sign openssl cms -sign -binary -in payload -signer cert.pem -inkey tls.key -outform DER -out payload.cms
	check cms-verify openssl cms -verify -binary -inform DER -in payload.cms -content payload \
		-CAfile cert.pem -purpose any -out verified
	cmp payload verified
	reject cms-reject 'CMS Verification failure' openssl cms -verify -binary -inform DER \
		-in payload.cms -content tampered -CAfile cert.pem -purpose any -out rejected
	for protocol in tls1_2 tls1_3; do
		openssl s_server -accept 127.0.0.1:44330 -cert cert.pem -key tls.key -www "-$protocol" \
			>"logs/$protocol-server.log" 2>&1 &
		server=$!
		sleep 1
		kill -0 "$server"
		printf 'GET / HTTP/1.0\r\n\r\n' >request
		check "$protocol" bounded openssl s_client -connect 127.0.0.1:44330 -servername localhost \
			-CAfile cert.pem -verify_hostname localhost -verify_return_error -brief -msg "-$protocol" <request
		grep -q 'Verification: OK' "logs/$protocol.log"
		version=TLSv1.2
		if [ "$protocol" = tls1_3 ]; then version=TLSv1.3; fi
		grep -q "Protocol version: $version" "logs/$protocol.log"
		reject "$protocol-hostname" 'hostname mismatch' bounded openssl s_client \
			-connect 127.0.0.1:44330 -servername localhost -CAfile cert.pem -verify_hostname mismatch.invalid \
			-verify_return_error -brief "-$protocol" <request
		cleanup
		server=
	done
fi
tar -cf logs.tar logs
echo FEATURE_LOGS_BEGIN
base64 logs.tar
echo FEATURE_LOGS_END
echo FEATURE_DONE
