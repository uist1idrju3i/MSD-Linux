#!/bin/sh
set -eu
root=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd)
include=${MSD_TEST_CRYPTSETUP_INCLUDE:-/usr/include}
case ${MSD_TEST_REQUIRE_CRYPTSETUP:-0} in
	0) ;;
	1)
		if [ ! -f "$include/libcryptsetup.h" ]; then
			printf '%s\n' 'FAIL: real libcryptsetup test is required but development header is missing' >&2
			exit 1
		fi
		;;
	*) printf '%s\n' 'Invalid MSD_TEST_REQUIRE_CRYPTSETUP (expected 0 or 1)' >&2; exit 2 ;;
esac
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT HUP INT TERM
src="$root/package/msd-data-unlock"
cc=${CC:-cc}
"$cc" -std=c11 -Wall -Wextra -Werror -I"$src" \
	"$src/unlock.c" "$root/tests/msd-data-unlock/core.c" -o "$work/core"
"$work/core"
"$cc" -std=c11 -Wall -Wextra -Werror -pthread -I"$src" \
	"$src/unlock.c" "$src/terminal.c" "$root/tests/msd-data-unlock/terminal-driver.c" \
	-o "$work/terminal-driver"
python3 "$root/tests/msd-data-unlock/terminal.py" "$work/terminal-driver"
python3 "$root/tests/msd-data-unlock/requirements.py"
if [ -f "$include/libcryptsetup.h" ]; then
	"$cc" -std=c11 -Wall -Wextra -Werror -I"$src" -I"$include" \
		"$src/unlock.c" "$src/crypt-backend.c" "$root/tests/msd-data-unlock/real.c" \
		-Wl,--wrap=fsync -Wl,-l:libcryptsetup.so.12 -o "$work/real"
	"$cc" -std=c11 -Wall -Wextra -Werror -pthread -I"$src" -I"$include" \
		"$src/main.c" "$src/unlock.c" "$src/terminal.c" "$src/crypt-backend.c" \
		-Wl,-l:libcryptsetup.so.12 -o "$work/helper"
	python3 - "$work/helper" <<'PY'
import resource
import subprocess
import sys
helper = sys.argv[1]
for arguments in ([], ["unlock"], ["unlock", "--device", "/missing", "--io", "auto"],
                  ["unlock", "--device", "/missing", "--io", "qemu", "--pin", "not-accepted"],
                  ["prepare", "--device", "/missing", "--io", "qemu", "--control-fd", "0"]):
    p = subprocess.run([helper, *arguments], capture_output=True, timeout=5)
    assert p.returncode == 2 and not p.stdout and b"not-accepted" not in p.stderr
def no_lock():
    resource.setrlimit(resource.RLIMIT_MEMLOCK, (0, 0))
p = subprocess.run([helper, "unlock", "--device", "/missing", "--io", "qemu"],
                   capture_output=True, timeout=5, preexec_fn=no_lock)
assert p.returncode == 1 and not p.stdout and p.stderr == b"msd-data-unlock: stopped\n"
print("ok - CLI: fixed mode, no PIN option, control socket validation, mlock fail-closed")
PY
	truncate -s 64M "$work/header.img"
	"$work/real" "$work/header.img" > "$work/real.log" 2>&1 || {
		printf '%s\n' 'FAIL: real libcryptsetup header test (output withheld to avoid leaking secrets)'
		exit 1
	}
	python3 - "$work/real.log" <<'PY'
from pathlib import Path
import sys
data = Path(sys.argv[1]).read_bytes()
for secret in (b"  original PIN 93!  ", b"replacement PIN 94!", b"ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"):
    assert secret not in data, "secret leaked from real backend"
print(data.decode(), end="")
PY
else
	printf '%s\n' 'SKIP: optional real libcryptsetup test (development header not installed)'
fi
printf '%s\n' 'All msd-data-unlock tests passed.'
