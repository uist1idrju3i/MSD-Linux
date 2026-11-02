#!/bin/sh
set -eu
cd "$(dirname "$0")/../.."
python3 -m unittest discover -s tests/yocto-compare -p 'test_*.py'
