#!/bin/bash
set -euo pipefail
shopt -s nullglob

readme=docs/experiments/README.md
if [ ! -f "$readme" ]; then
	printf '::error file=%s::実験記録の索引がありません。\n' "$readme"
	exit 1
fi

indexes=("$readme")
for index in docs/experiments/[0-9][0-9][0-9][0-9]-[0-9][0-9]-index.md; do
	name="${index##*/}"
	if grep -Fq "($name)" "$readme"; then
		indexes+=("$index")
	fi
done

status=0
for record in docs/experiments/*.md; do
	name="${record##*/}"
	[ "$name" = README.md ] && continue
	if ! grep -Fq "($name)" "${indexes[@]}"; then
		printf '::error file=%s::%s が README.md または参照先の月別索引にありません。\n' "$record" "$name"
		status=1
	fi
done
exit "$status"
