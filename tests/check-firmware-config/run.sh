#!/bin/sh
set -eu
cd "$(dirname "$0")/../.."
python3 -m unittest discover -s tests/check-firmware-config -p 'test_*.py'
