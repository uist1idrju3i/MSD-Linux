#!/bin/sh
set -eu

repo_root="$(CDPATH='' cd "$(dirname "$0")/../.." && pwd)"
hwinfo="$repo_root/board/cardputerzero/rootfs-overlay/usr/sbin/msd-hwinfo"
test_root="$(mktemp -d)"

cleanup() {
	rm -rf "$test_root"
}
trap cleanup 0
trap 'exit 1' HUP INT TERM

fail() {
	printf 'not ok - %s\n' "$*" >&2
	exit 1
}

expect_result() {
	expected="$1"
	root="$2"
	actual="$(MSD_HWINFO_SYSFS="$root" "$hwinfo")"
	[ "$actual" = "$expected" ] || fail "expected $expected, got $actual"
}

standard="$test_root/standard"
mkdir -p "$standard/bus/i2c/devices/1-0068" "$standard/bus/i2c/devices/1-004f"
: > "$standard/bus/i2c/devices/1-0068/driver"
expect_result 'model=standard imu=present' "$standard"
printf 'ok - a bound IMU identifies the standard model\n'

iio_standard="$test_root/iio-standard"
mkdir -p "$iio_standard/bus/i2c/devices/1-004f" "$iio_standard/bus/iio/devices/iio:device0"
: > "$iio_standard/bus/i2c/devices/1-004f/driver"
printf '%s\n' BMI270 > "$iio_standard/bus/iio/devices/iio:device0/name"
expect_result 'model=standard imu=present' "$iio_standard"
printf 'ok - a BMI270 IIO device identifies the standard model\n'

lite="$test_root/lite"
mkdir -p "$lite/bus/i2c/devices/1-004f" "$lite/bus/i2c/devices/1-0068"
: > "$lite/bus/i2c/devices/1-004f/driver"
expect_result 'model=lite imu=absent' "$lite"
printf 'ok - a bound M5IOE1 with no IMU identifies the Lite model\n'

unknown="$test_root/unknown"
mkdir -p "$unknown/bus/i2c/devices/1-0068"
expect_result 'model=unknown imu=unknown' "$unknown"
printf 'ok - an unprobed bus reports unknown hardware\n'

printf 'All msd-hwinfo host tests passed.\n'
