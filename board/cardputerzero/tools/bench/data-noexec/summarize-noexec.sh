#!/bin/bash
# Usage (inside docker/msd-dev): summarize-noexec.sh LOG_DIR > CSV
set -uo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../../../.." && pwd)"
dir="$1"
echo "variant,run,boot,result_marker,ready,serial_check,p1,p2_rc,p3_rc,p4_rc,p5_rc,log_sha256"
for log in "$dir"/{base,noexec}-r*.boot{1,2}.log; do
	b="$(basename "$log" .log)"; variant="${b%%-r*}"; rest="${b#*-r}"; run="${rest%%.*}"; boot="${rest##*.boot}"
	clean="$(tr -d '\r\0' <"$log")"
	marker=no
	if [[ "$boot" == 1 ]]; then grep -Fq '=noexec= stage1-done' <<<"$clean" && marker=yes
	else grep -Fq '=noexec= finished' <<<"$clean" && marker=yes; fi
	ready="$(grep -c 'MSD/Linux ready' <<<"$clean")"
	if "${REPO_ROOT}/board/cardputerzero/qemu/check-serial-log.sh" "$log" >"${log%.log}.serialcheck" 2>&1; then sc=pass; else sc=fail; fi
	field() { sed -n "s/.*=noexec= $1 \(noexec=[a-z]*\|rc=[0-9]*\).*/\1/p" <<<"$clean" | head -1; }
	printf '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n' "$variant" "$run" "$boot" "$marker" "$ready" "$sc" \
		"$(field P1)" "$(field P2)" "$(field P3)" "$(field P4)" "$(field P5)" "$(sha256sum "$log" | cut -c1-64)"
done
