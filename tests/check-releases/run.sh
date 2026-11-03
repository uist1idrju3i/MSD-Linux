#!/bin/sh
set -eu
cd "$(git rev-parse --show-toplevel)"
python3 -m unittest discover -s tests/check-releases -p 'test_*.py' -v
