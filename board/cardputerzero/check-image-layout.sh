#!/bin/sh
set -eu
board_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
exec python3 "$board_dir/data-image.py" check "$@"
