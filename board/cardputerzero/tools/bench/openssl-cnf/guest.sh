#!/bin/sh
set -eu

base=/run/cnf
variant=$1
mkdir -p "$base/logs"
cd "$base"
server=
cleanup()
{
	if [ -n "$server" ]; then
		kill "$server" 2>/dev/null || :
		wait "$server" 2>/dev/null || :
	fi
}
trap cleanup EXIT
export TMPDIR="$base" HOME="$base"
unset OPENSSL_CONF OPENSSL_MODULES

stats()
{
	awk '{ print $5, $7 }' /sys/class/block/mmcblk0p7/stat
}

begin()
{
	case_name=$1
	read -r before_ios before_sectors <<EOF
$(stats)
EOF
	echo "CNF_BEGIN case=$case_name uptime=$(cut -d ' ' -f1 /proc/uptime)"
}

end()
{
	read -r after_ios after_sectors <<EOF
$(stats)
EOF
	echo "CNF_RESULT case=$case_name rc=$1 pass=$2 writes=$((after_ios - before_ios)) sectors=$((after_sectors - before_sectors))"
}

check()
{
	name=$1
	shift
	begin "$name"
	rc=0
	"$@" >"logs/$name.log" 2>&1 || rc=$?
	pass=0
	[ "$rc" -ne 0 ] || pass=1
	end "$rc" "$pass"
	[ "$pass" -eq 1 ]
}

data_hash()
{
	find /data -xdev -type f -exec sha256sum {} \; | sort
}

uname -a >logs/kernel.log
cat /proc/mounts >logs/mounts.log
cat /proc/cmdline >logs/cmdline.log
openssl version -a >logs/openssl.log
cryptsetup --version >logs/cryptsetup.log
ls -l /sbin/modprobe >logs/module.log
sha256sum /etc/ssl/openssl.cnf /usr/bin/openssl /usr/lib/libcrypto.so.3 \
	/usr/lib/libssl.so.3 /usr/lib/ossl-modules/legacy.so /usr/sbin/msd-update >logs/binaries.log
data_hash >logs/data-before.log
sync
sleep 10
check idle-before sleep 3
check providers openssl list -providers
check ciphers openssl ciphers -s -v
check module /run/kmod-probe
test -r /proc/config.gz
zcat /proc/config.gz | sed -n '/^CONFIG_MODULE_SIG/p' >logs/module-config.log

printf 'openssl_conf = init\nconfig_diagnostics = 1\n[init]\nssl_conf = absent\n' >bad.cnf
begin bad-config
rc=0
OPENSSL_CONF="$base/bad.cnf" openssl ciphers >logs/bad-config.log 2>&1 || rc=$?
pass=0
if [ "$rc" -ne 0 ] && grep -qi 'configuration\|error' logs/bad-config.log; then pass=1; fi
end "$rc" "$pass"
test "$pass" -eq 1

openssl genpkey -algorithm Ed25519 -out update.key >logs/keygen.log 2>&1
openssl pkey -in update.key -pubout -out update.pub
mkdir -p bundle dt state
printf '\000\000\000\002' >dt/partition
printf '\000\000\000\000' >dt/tryboot
printf '100\n' >version
printf 'test root payload\n' >bundle/rootfs.squashfs
printf 'test boot payload\n' >bundle/boot.vfat
(cd bundle; printf 'version 100\n'; sha256sum rootfs.squashfs boot.vfat) >bundle/manifest
openssl pkeyutl -sign -rawin -inkey update.key -in bundle/manifest -out bundle/manifest.sig
tar -cf valid.tar -C bundle rootfs.squashfs boot.vfat manifest manifest.sig
printf 'bad signature\n' >bundle/manifest.sig
tar -cf invalid.tar -C bundle rootfs.squashfs boot.vfat manifest manifest.sig
export MSD_UPDATE_DT_DIR="$base/dt" MSD_UPDATE_STATE_DIR="$base/state"
export MSD_UPDATE_PARTITION_PREFIX="$base/slot" MSD_UPDATE_KEY_PATH="$base/update.pub"
export MSD_UPDATE_VERSION_PATH="$base/version"
: >slot3
: >slot6
check update-valid msd-update install "$base/valid.tar"
cmp bundle/rootfs.squashfs slot6
cmp bundle/boot.vfat slot3
test "$(cat state/installed)" = 3
sha256sum slot3 slot6 state/installed >before-invalid
begin update-invalid
rc=0
msd-update install "$base/invalid.tar" >logs/update-invalid.log 2>&1 || rc=$?
sha256sum slot3 slot6 state/installed >after-invalid
pass=0
if [ "$rc" -ne 0 ] && grep -q 'signature verification failed' logs/update-invalid.log &&
	cmp -s before-invalid after-invalid; then pass=1; fi
end "$rc" "$pass"
test "$pass" -eq 1

head -c 32 /dev/urandom >luks.key
for pbkdf in argon2id pbkdf2; do
	truncate -s 64M luks.img
	set -- --pbkdf-force-iterations 1000
	if [ "$pbkdf" = argon2id ]; then
		set -- --pbkdf-force-iterations 4 --pbkdf-memory 65536 --pbkdf-parallel 1
	fi
	check "$pbkdf-format" cryptsetup --debug luksFormat --type luks2 --batch-mode \
		--key-file luks.key --pbkdf "$pbkdf" "$@" luks.img
	cryptsetup luksDump luks.img >"logs/$pbkdf-dump.log"
	check "$pbkdf-open" cryptsetup --debug open --key-file luks.key luks.img cnf-test
	cryptsetup status cnf-test >"logs/$pbkdf-status.log"
	cryptsetup close cnf-test
	rm luks.img
done

openssl req -x509 -newkey rsa:2048 -noenc -subj /CN=localhost \
	-keyout tls.key -out cert.pem -days 1 >logs/cert.log 2>&1
printf 'GET / HTTP/1.0\r\n\r\n' >request

tls()
{
	direction=$1
	protocol=$2
	cipher=$3
	expected=$4
	begin "tls-$direction-$protocol-$cipher"
	log="logs/$case_name.log"
	server_cnf=/etc/ssl/openssl.cnf
	client_cnf=/etc/ssl/openssl.cnf
	if [ "$direction" = server ]; then client_cnf="$base/peer.cnf"; fi
	if [ "$direction" = client ]; then server_cnf="$base/peer.cnf"; fi
	if [ "$direction" = control ]; then
		client_cnf="$base/peer.cnf"
		server_cnf="$base/peer.cnf"
	fi
	OPENSSL_CONF="$server_cnf" openssl s_server -accept 127.0.0.1:44330 \
		-cert cert.pem -key tls.key -www >"$log.server" 2>&1 &
	server=$!
	sleep 1
	kill -0 "$server"
	set --
	if [ "$direction" = server ] || [ "$direction" = control ]; then
		set -- "-$protocol"
	fi
	if [ "$cipher" = cbc ] && [ "$direction" != client ]; then
		set -- "$@" -cipher ECDHE-RSA-AES128-SHA256
	elif [ "$protocol" = tls1_2 ] && [ "$direction" != client ]; then
		set -- "$@" -cipher ECDHE-RSA-AES128-GCM-SHA256
	fi
	if [ "$direction" = client ]; then
		cleanup
		set --
		if [ "$cipher" = cbc ]; then set -- -cipher ECDHE-RSA-AES128-SHA256; fi
		OPENSSL_CONF="$server_cnf" openssl s_server -accept 127.0.0.1:44330 \
			-cert cert.pem -key tls.key -www "-$protocol" "$@" >"$log.server" 2>&1 &
		server=$!
		sleep 1
		kill -0 "$server"
		set --
	fi
	rc=0
	OPENSSL_CONF="$client_cnf" openssl s_client -connect 127.0.0.1:44330 \
		-servername localhost -CAfile cert.pem -verify_hostname localhost \
		-verify_return_error -brief "$@" <request >"$log" 2>&1 &
	client=$!
	(sleep 15; kill -KILL "$client" 2>/dev/null) &
	watchdog=$!
	wait "$client" || rc=$?
	kill "$watchdog" 2>/dev/null || :
	wait "$watchdog" 2>/dev/null || :
	cleanup
	server=
	pass=0
	if [ "$expected" = accept ]; then
		if [ "$rc" -eq 0 ] && grep -q 'CONNECTION ESTABLISHED' "$log" &&
			grep -q 'Verification: OK' "$log"; then pass=1; fi
	else
		if [ "$rc" -ne 0 ] && [ "$rc" -ne 137 ] &&
			! grep -q 'CONNECTION ESTABLISHED' "$log" &&
			grep -qi 'unsupported protocol\|alert protocol version\|no protocols available\|no shared cipher\|handshake failure' "$log" "$log.server"; then pass=1; fi
	fi
	end "$rc" "$pass"
	test "$pass" -eq 1
}

printf 'openssl_conf = init\n[init]\nssl_conf = ssl\n[ssl]\nsystem_default = policy\n[policy]\nMinProtocol = TLSv1\nCipherString = ALL:@SECLEVEL=0\n' >peer.cnf
for protocol in tls1 tls1_1; do tls control "$protocol" aead accept; done
for direction in server client; do
	for protocol in tls1 tls1_1; do tls "$direction" "$protocol" aead reject; done
	for protocol in tls1_2 tls1_3; do tls "$direction" "$protocol" aead accept; done
	expected=accept
	if [ "$variant" = C2 ]; then expected=reject; fi
	tls "$direction" tls1_2 cbc "$expected"
done
check idle-after sleep 3
data_hash >logs/data-after.log
check data-content cmp logs/data-before.log logs/data-after.log
tar -cf /run/cnf-logs.tar logs
echo CNF_LOGS_BEGIN
base64 /run/cnf-logs.tar
echo CNF_LOGS_END
echo CNF_DONE
