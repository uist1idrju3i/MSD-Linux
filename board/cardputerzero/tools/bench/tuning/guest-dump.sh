#!/bin/sh
# Prints every tunable visible in the guest, one "KIND|path|mode|value" line each.
# Read-only: it never writes to /proc/sys or /sys.
emit() {
	kind="$1"
	path="$2"
	# The image has no stat(1); keep the column for images that do.
	mode="$(stat -c %a "$path" 2>/dev/null)"
	value="$(cat "$path" 2>&1 | tr '\t\n' '  ' | sed 's/ *$//')"
	printf '%s|%s|%s|%s\n' "$kind" "$path" "$mode" "$value"
}
find /proc/sys -type f | sort | while read -r f; do emit SYSCTL "$f"; done
for f in /sys/block/*/queue/* /sys/block/*/queue/iosched/* /sys/block/*/bdi/*; do
	[ -f "$f" ] && emit BLOCK "$f"
done
for f in /sys/devices/system/cpu/cpufreq/policy*/* /sys/devices/system/cpu/cpu*/cpuidle/state*/* \
	/sys/devices/system/cpu/cpuidle/* /sys/devices/system/cpu/online /sys/devices/system/cpu/possible \
	/sys/devices/system/cpu/smt/* /sys/devices/system/cpu/vulnerabilities/*; do
	[ -f "$f" ] && emit CPU "$f"
done
for f in /sys/kernel/mm/*/* /sys/kernel/mm/*/*/* /sys/power/* /sys/kernel/security/lsm \
	/sys/class/thermal/thermal_zone*/* /sys/class/watchdog/watchdog*/*; do
	[ -f "$f" ] && emit SYSFS "$f"
done
find /sys/module -path '*/parameters/*' -type f | sort | while read -r f; do emit MODPARAM "$f"; done
emit PROC /proc/cmdline
emit PROC /proc/version
emit PROC /proc/meminfo
emit PROC /proc/mounts
emit PROC /proc/swaps
emit PROC /proc/cpuinfo
emit PROC /proc/interrupts
# shellcheck disable=SC3045 # BusyBox ash supports ulimit -a.
printf 'ULIMIT|ulimit -a||%s\n' "$(ulimit -a 2>&1 | tr '\n' ';')"
printf 'MODULES|lsmod||%s\n' "$(lsmod 2>&1 | tr '\n' ';')"
if [ -r /proc/config.gz ]; then
	zcat /proc/config.gz | grep -E '^CONFIG_' | while read -r c; do printf 'KCONFIG|%s||%s\n' "${c%%=*}" "${c#*=}"; done
fi
