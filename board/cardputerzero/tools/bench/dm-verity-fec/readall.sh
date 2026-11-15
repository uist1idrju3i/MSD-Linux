#!/bin/sh
set -eu
/bin/dd if="${B3_READALL_DEVICE:-/dev/dm-0}" of=/dev/null bs=1048576
printf 'verity-readall-complete\n' > "${B3_READALL_MARKER:-/dev/kmsg}"
