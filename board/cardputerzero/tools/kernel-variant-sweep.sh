#!/bin/bash
set -euo pipefail
unset BASH_ENV

SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)"
OUTPUT_DIR="${OUTPUT_DIR:-$PWD}"
CANDIDATES="${REPO_ROOT}/board/cardputerzero/tools/kernel-candidates.txt"
CSV="${SWEEP_CSV:-${OUTPUT_DIR}/kernel-sweep.csv}"
ONLY=
NO_QEMU=false
JOBS=${SWEEP_JOBS:-1}
WORKER=${SWEEP_WORKER:-}
SDCARD="${SWEEP_SDCARD:-${OUTPUT_DIR}/images/sdcard.img}"
DTB="${SWEEP_DTB:-${OUTPUT_DIR}/images/bcm2710-rpi-3-b.dtb}"
SWEEP_LOG_DIR="${SWEEP_LOG_DIR:-${OUTPUT_DIR}/kernel-sweep-logs}"

while [ "$#" -gt 0 ]; do
	case "$1" in
		--no-qemu) NO_QEMU=true; shift ;;
		--only) ONLY="${2:?--only requires a symbol}"; shift 2 ;;
		--jobs) JOBS="${2:?--jobs requires a count}"; shift 2 ;;
		--candidates) CANDIDATES="${2:?--candidates requires a file}"; shift 2 ;;
		*) printf 'Unknown option: %s\n' "$1" >&2; exit 2 ;;
	esac
done
if ! [[ "$JOBS" =~ ^[0-9]+$ ]] || [ "$JOBS" -lt 1 ]; then
	printf -- '--jobs must be a positive integer.\n' >&2
	exit 2
fi

if [ ! -d "${OUTPUT_DIR}/build" ]; then
	printf 'Run from a Buildroot output directory or set OUTPUT_DIR.\n' >&2
	exit 2
fi
LINUX_DIR="${LINUX_DIR:-${OUTPUT_DIR}/build/linux-custom}"
if [ ! -r "$CANDIDATES" ]; then
	printf 'Candidate file must be readable: %s\n' "$CANDIDATES" >&2
	exit 2
fi

# ドライバー: --jobs N>1 のときワーカーを N 本並列起動し、CSV を結合する。
# 各ワーカーは linux-custom を複製した独立ツリーで動き（reflink 優先・なければ完全コピー）、
# 候補は行番号の round-robin で分ける。共有 sdcard は QEMU_COPY_IMAGE=1 の既定により
# 各起動で tmpdir に複製されるため並列 QEMU は衝突しない（QMP ソケットは未指定時なし）。
if [ -z "$WORKER" ] && [ "$JOBS" -gt 1 ]; then
	base_tree="$LINUX_DIR"
	jobs_tmp="$(mktemp -d "${OUTPUT_DIR}/.kernel-sweep-jobs.XXXXXX")"
	# 失敗時は jobs_tmp を残す（ワーカーログを調べるため）。成功時のみ掃除する。
	trap 'if [ "$?" -eq 0 ]; then rm -rf "$jobs_tmp"; else printf "kept %s\n" "$jobs_tmp" >&2; fi' EXIT
	printf 'kernel-variant-sweep: %d workers (trees under %s)\n' "$JOBS" "$jobs_tmp"
	pids=()
	for w in $(seq 0 "$((JOBS - 1))"); do
		(
			wtree="$jobs_tmp/linux-w$w"
			cp -a --reflink=auto "$base_tree" "$wtree" 2>/dev/null || cp -a "$base_tree" "$wtree"
			SWEEP_WORKER=$w SWEEP_JOBS_TOTAL=$JOBS \
				LINUX_DIR="$wtree" \
				SWEEP_CSV="$CSV.w$w" \
				SWEEP_SDCARD="$SDCARD" SWEEP_DTB="$DTB" \
				SWEEP_LOG_DIR="$SWEEP_LOG_DIR" \
				"$0" --candidates "$CANDIDATES" \
				${NO_QEMU:+--no-qemu}
		) >"$jobs_tmp/worker$w.log" 2>&1 &
		pids+=("$!")
	done
	fail=0
	for p in "${pids[@]}"; do
		if ! wait "$p"; then fail=1; fi
	done
	printf 'symbol,value,category,status,image_bytes,gz_bytes,delta_gz,collateral,qemu_ready_vtime,initcalls\n' > "$CSV"
	for w in $(seq 0 "$((JOBS - 1))"); do
		[ -f "$CSV.w$w" ] && tail -n +2 "$CSV.w$w" >> "$CSV"
	done
	if [ "$fail" -ne 0 ]; then
		printf 'Some workers failed; logs in %s\n' "$jobs_tmp" >&2
		exit 1
	fi
	rm -f "$CSV".w*
	printf 'Sweep results: %s\n' "$CSV"
	exit 0
fi

CONFIG="${LINUX_DIR}/.config"
IMAGE="${LINUX_DIR}/arch/arm64/boot/Image"
SCRIPTS_CONFIG="${LINUX_DIR}/scripts/config"
export CROSS_COMPILE="${OUTPUT_DIR}/host/bin/aarch64-linux-"
KEEP="${SCRIPT_DIR}/kernel-keep.txt"
if [ ! -r "$CONFIG" ] || [ ! -x "$SCRIPTS_CONFIG" ] || [ ! -r "$IMAGE" ]; then
	printf 'Linux build and .config are required in %s.\n' "$LINUX_DIR" >&2
	exit 2
fi
if [ ! -r "$KEEP" ]; then
	printf 'Keep file must be readable.\n' >&2
	exit 2
fi
if [ "$NO_QEMU" = false ] && { [ ! -r "$SDCARD" ] || [ ! -r "$DTB" ]; }; then
	printf 'QEMU image or DTB missing; use --no-qemu or set SWEEP_SDCARD/SWEEP_DTB.\n' >&2
	exit 2
fi

tmp="$(mktemp -d "${OUTPUT_DIR}/.kernel-sweep.XXXXXX")"
trap 'cp "$tmp/base.config" "$CONFIG"; cp "$tmp/base.Image" "$IMAGE"; rm -rf "$tmp"' EXIT
cp "$CONFIG" "$tmp/base.config"
cp "$IMAGE" "$tmp/base.Image"
if command -v pigz >/dev/null 2>&1; then
	compressed_size() {
		pigz -11 -p 2 -c "$1" | wc -c
	}
else
	compressed_size() {
		gzip -9 -c "$1" | wc -c
	}
fi
base_gz=$(compressed_size "$IMAGE")
printf 'symbol,value,category,status,image_bytes,gz_bytes,delta_gz,collateral,qemu_ready_vtime,initcalls\n' > "$CSV"

config_value() {
	local symbol=$1
	sed -n -e "s/^CONFIG_${symbol}=//p" -e "s/^# CONFIG_${symbol} is not set$/n/p" "$CONFIG" | head -n 1
}

csv_field() {
	local value=${1//\"/\"\"}
	printf '"%s"' "$value"
}

index=0
while read -r symbol value category _reason || [ -n "${symbol:-}" ]; do
	[ -n "${symbol:-}" ] || continue
	[[ "$symbol" == \#* ]] && continue
	if [ -n "${WORKER:-}" ]; then
		if [ $((index % ${SWEEP_JOBS_TOTAL:-1})) -ne "$WORKER" ]; then
			index=$((index + 1))
			continue
		fi
		index=$((index + 1))
	fi
	if [ -n "$ONLY" ] && [ "$symbol" != "$ONLY" ]; then
		continue
	fi

	status=PASS
	collateral=
	image_bytes=
	gz_bytes=
	delta_gz=
	ready=
	initcalls=
	cp "$tmp/base.config" "$CONFIG"
	case "$value" in
		n) "$SCRIPTS_CONFIG" --file "$CONFIG" --disable "$symbol" ;;
		m) "$SCRIPTS_CONFIG" --file "$CONFIG" --module "$symbol" ;;
		y) "$SCRIPTS_CONFIG" --file "$CONFIG" --enable "$symbol" ;;
		*) "$SCRIPTS_CONFIG" --file "$CONFIG" --set-val "$symbol" "$value" ;;
	esac

	if ! env -u BASH_ENV make -C "$LINUX_DIR" ARCH=arm64 \
		CROSS_COMPILE="$CROSS_COMPILE" olddefconfig; then
		status=OLDDEFCONFIG_FAILED
	elif [ "$(config_value "$symbol")" != "$value" ]; then
		status=TARGET_MISMATCH
	else
		while read -r keep_symbol keep_value _; do
			[ -n "${keep_symbol:-}" ] || continue
			[[ "$keep_symbol" == \#* ]] && continue
			if [ "$(config_value "$keep_symbol")" != "$keep_value" ]; then
				status=KEEP_CHANGED
				break
			fi
		done < "$KEEP"
	fi

	if [ "$status" = PASS ]; then
		while IFS= read -r line; do
			[[ "$line" =~ ^CONFIG_ ]] || [[ "$line" =~ ^#\ CONFIG_.*\ is\ not\ set$ ]] || continue
			if [[ "$line" == CONFIG_* ]]; then
				name=${line#CONFIG_}
				name=${name%%=*}
			else
				name=${line#"# CONFIG_"}
				name=${name% is not set}
			fi
			[ "$name" = "$symbol" ] && continue
			base_line=$(grep -E "^(CONFIG_${name}=|# CONFIG_${name} is not set$)" "$tmp/base.config" || true)
			[ "$line" = "$base_line" ] || collateral+="${name};"
		done < <(grep -E '^(CONFIG_|# CONFIG_.* is not set)' "$CONFIG")
		rm -f "$IMAGE"
		if ! env -u BASH_ENV make -C "$LINUX_DIR" -j2 ARCH=arm64 \
			CROSS_COMPILE="$CROSS_COMPILE" Image; then
			status=BUILD_FAILED
		else
			image_bytes=$(wc -c < "$IMAGE")
			gz_bytes=$(compressed_size "$IMAGE")
			delta_gz=$((gz_bytes - base_gz))
			if [ "$NO_QEMU" = false ]; then
				logdir="${tmp}/qemu"
				mkdir -p "$logdir"
				qemu_status=0
				# sdcard 内のモジュールはベースラインカーネル由来のため、
				# 差し替えた variant カーネルとは vermagic が必ず不一致になる。
				# モジュールのロード検査は製品ビルドのゲートに任せ、sweep では
				# QEMU_MODULE_TEST を空にして無効化する（SWEEP_MODULE_TEST で上書き可）。
				if QEMU_LOG_DIR="$logdir" OUTPUT_DIR="$OUTPUT_DIR" \
					KERNEL_IMAGE="$IMAGE" DTB_IMAGE="$DTB" \
					QEMU_MODULE_TEST="${SWEEP_MODULE_TEST-}" \
					QEMU_ICOUNT='shift=0,sleep=off' QEMU_EXTRA_APPEND='initcall_debug printk.time=1 msd.sweep=1' \
					"${REPO_ROOT}/board/cardputerzero/qemu/test-boot.sh" "$SDCARD"; then
					:
				else
					qemu_status=$?
				fi
				logfile="${logdir}/serial-mmcblk0p5.log"
				if [ -r "$logfile" ]; then
					ready=$(awk '
						/MSD\/Linux ready/ {
							if (match($0, /\[[[:space:]]*[0-9.]+\]/)) {
								stamp = substr($0, RSTART + 1, RLENGTH - 2)
								gsub(/[[:space:]]/, "", stamp)
								print stamp
							} else if (last != "") {
								print "~" last
							}
							exit
						}
						{
							if (match($0, /\[[[:space:]]*[0-9.]+\]/)) {
								last = substr($0, RSTART + 1, RLENGTH - 2)
								gsub(/[[:space:]]/, "", last)
							}
						}
					' "$logfile")
					initcalls=$(awk '/initcall .* returned .* after [0-9]+ usecs/ { n++; total += $(NF-1) } END { printf "%d/%d", n, total }' "$logfile")
				else
					qemu_status=1
				fi
				if [ "$qemu_status" -ne 0 ]; then
					status=QEMU_FAILED
					mkdir -p "$SWEEP_LOG_DIR"
					cp -a "$logdir" "${SWEEP_LOG_DIR}/${symbol}" 2>/dev/null || true
				fi
			fi
		fi
	fi
	printf '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n' \
		"$(csv_field "$symbol")" "$(csv_field "$value")" "$(csv_field "$category")" \
		"$(csv_field "$status")" "$(csv_field "$image_bytes")" "$(csv_field "$gz_bytes")" \
		"$(csv_field "$delta_gz")" "$(csv_field "$collateral")" \
		"$(csv_field "$ready")" "$(csv_field "$initcalls")" >> "$CSV"
done < "$CANDIDATES"

cp "$tmp/base.config" "$CONFIG"
cp "$tmp/base.Image" "$IMAGE"
printf 'Sweep results: %s\n' "$CSV"
