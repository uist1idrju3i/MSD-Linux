#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../../.." && pwd -P)"
CONFIGS_FILE="${SCRIPT_DIR}/fs-compare-configs.tsv"
FS_COMPARE="${SCRIPT_DIR}/fs-compare.sh"
SUMMARY_HEADER='run_id,config,test,status,wall_seconds,workload_size,points,loss_points,mount_fail,fsck_fail,recovered,manifest_ok,quiesce_seconds,quiesce_write_ios,quiesce_write_sectors,write_ios,write_sectors,last_write_s,logical_bytes,lost_records,lost_seconds,fsync_lost,read_result,scrub_corrected,scrub_uncorrectable,fsck_detection,repaired,mkfs_seconds,mount_seconds,fsck_seconds,mem_available_kb,setup_points,setup_mount_fail,setup_fsck_fail,setup_seconds'

DEFAULT_RUNS_DIR="${HOME:-${REPO_ROOT}}/fscmp/runs"
RUNS_DIR="${FS_COMPARE_RUNS_DIR:-${QEMU_LOG_DIR:-${DEFAULT_RUNS_DIR}}}"
MATRIX_ID=
JOBS=4
GENERATE_PHASE1=0
PLAN_FILE=

usage()
{
	cat >&2 <<EOF
Usage:
  ${BASH_SOURCE[0]} --generate-phase1
  ${BASH_SOURCE[0]} [-j N] [--matrix-id ID] [--runs-dir DIR] PLAN.tsv

PLAN.tsv contains config<TAB>test<TAB>repetition rows. The generated plan
is written to stdout and can be saved, for example, with:
  ${BASH_SOURCE[0]} --generate-phase1 > phase1-plan.tsv
EOF
	exit "${1:-2}"
}

die()
{
	printf 'fs-compare-matrix: %s\n' "$*" >&2
	exit 1
}

while (($#)); do
	case "$1" in
		--generate-phase1)
			GENERATE_PHASE1=1
			shift
			;;
		-j|--jobs)
			(($# >= 2)) || usage
			JOBS=$2
			shift 2
			;;
		--matrix-id)
			(($# >= 2)) || usage
			MATRIX_ID=$2
			shift 2
			;;
		--runs-dir)
			(($# >= 2)) || usage
			RUNS_DIR=$2
			shift 2
			;;
		-h|--help)
			usage 0
			;;
		--)
			shift
			break
			;;
		-*)
			usage
			;;
		*)
			[[ -z "$PLAN_FILE" ]] || usage
			PLAN_FILE=$1
			shift
			;;
	esac
done
if (($#)); then
	[[ -z "$PLAN_FILE" && $# -eq 1 ]] || usage
	PLAN_FILE=$1
fi

if ((GENERATE_PHASE1)); then
	[[ -z "$PLAN_FILE" ]] || usage
	[[ -f "$CONFIGS_FILE" ]] || die "configuration list not found"
	mapfile -t config_ids < <(
		awk -F '\t' '$1 != "id" && $1 !~ /^#/ && $1 != "" { print $1 }' \
			"$CONFIGS_FILE"
	)
	((${#config_ids[@]} == 20)) ||
		die "expected 20 configurations, found ${#config_ids[@]}"

	t1_order=(L3 I1 I2)
	for config in "${config_ids[@]}"; do
		case " ${t1_order[*]} " in
			*" ${config} "*) ;;
			*) t1_order+=("$config") ;;
		esac
	done
	for test in T1 T4-sync T4-nosync T5 T3 T2 T6 T7; do
		case "$test" in
			T1)
				config_order=("${t1_order[@]}")
				repetitions=1
				;;
			T2)
				config_order=("${config_ids[@]}")
				repetitions=20
				;;
			T3)
				config_order=("${config_ids[@]}")
				repetitions=5
				;;
			*)
				config_order=("${config_ids[@]}")
				repetitions=1
				;;
		esac
		for config in "${config_order[@]}"; do
			for ((repetition = 1; repetition <= repetitions; repetition++)); do
				printf '%s\t%s\t%s\n' "$config" "$test" "$repetition"
			done
		done
	done
	exit 0
fi

[[ "$JOBS" =~ ^[1-9][0-9]*$ ]] || die "-j must be a positive integer"
[[ -n "$PLAN_FILE" && -r "$PLAN_FILE" ]] || usage
[[ "$RUNS_DIR" == /* ]] || die "--runs-dir must be an absolute path"
if [[ -z "$MATRIX_ID" ]]; then
	MATRIX_ID="phase1-$(date +%s)"
fi
[[ "$MATRIX_ID" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] ||
	die "invalid matrix ID"
command -v flock >/dev/null 2>&1 || die "flock is required"

mapfile -t CONFIG_IDS < <(
	awk -F '\t' '$1 != "id" && $1 !~ /^#/ && $1 != "" { print $1 }' \
		"$CONFIGS_FILE"
)
declare -A VALID_CONFIG=()
for config in "${CONFIG_IDS[@]}"; do
	VALID_CONFIG["$config"]=1
done

is_valid_test()
{
	case "$1" in
		smoke|T1|T2|T3|T4-sync|T4-nosync|T5|T6|T7) return 0 ;;
		*) return 1 ;;
	esac
}

declare -a PLAN_CONFIGS=() PLAN_TESTS=() PLAN_REPETITIONS=()
declare -A PLAN_SEEN=()
while IFS= read -r line || [[ -n "$line" ]]; do
	line=${line%$'\r'}
	[[ -z "$line" || "$line" == \#* ]] && continue
	tab_chars="${line//[!$'\t']/}"
	((${#tab_chars} == 2)) ||
		die "plan row must have exactly three TSV columns: $line"
	IFS=$'\t' read -r config test repetition extra <<<"$line"
	[[ -z "${extra:-}" && -n "$config" && -n "$test" && -n "$repetition" ]] ||
		die "plan row must have exactly three non-empty columns: $line"
	[[ "$config" =~ ^(E[1-5]|F[1-5]|B[1-5]|L[1-3]|I[1-2])$ ]] ||
		die "invalid configuration in plan: $config"
	[[ -n "${VALID_CONFIG[$config]+yes}" ]] ||
		die "unknown configuration in plan: $config"
	is_valid_test "$test" || die "unsupported test in plan: $test"
	[[ "$repetition" =~ ^[1-9][0-9]*$ ]] ||
		die "repetition must be a positive integer: $repetition"
	key="${config}|${test}|${repetition}"
	[[ -z "${PLAN_SEEN[$key]+yes}" ]] || die "duplicate plan row: $line"
	PLAN_SEEN["$key"]=1
	PLAN_CONFIGS+=("$config")
	PLAN_TESTS+=("$test")
	PLAN_REPETITIONS+=("$repetition")
done <"$PLAN_FILE"
((${#PLAN_CONFIGS[@]} > 0)) || die "plan contains no rows"

mkdir -p "$RUNS_DIR"
RUNS_DIR="$(cd -- "$RUNS_DIR" && pwd -P)"
MATRIX_DIR="${RUNS_DIR}/${MATRIX_ID}"
mkdir -p "$MATRIX_DIR"
MATRIX_PLAN="${MATRIX_DIR}/plan.tsv"
MATRIX_SUMMARY="${MATRIX_DIR}/matrix-summary.csv"
PROGRESS_LOG="${MATRIX_DIR}/progress.log"
HOST_LOAD="${MATRIX_DIR}/host-load.txt"
STATE_FILE="${MATRIX_DIR}/.state"
WRITE_LOCK="${MATRIX_DIR}/.write.lock"
DRIVER_LOCK="${MATRIX_DIR}/.driver.lock"
MATRIX_HEADER="repetition,attempt,${SUMMARY_HEADER}"

exec {driver_lock_fd}>"$DRIVER_LOCK"
flock -n "$driver_lock_fd" ||
	die "matrix ID is already running: $MATRIX_ID"

plan_tmp="${MATRIX_DIR}/.plan.$$"
: >"$plan_tmp"
for ((index = 0; index < ${#PLAN_CONFIGS[@]}; index++)); do
	printf '%s\t%s\t%s\n' "${PLAN_CONFIGS[index]}" \
		"${PLAN_TESTS[index]}" "${PLAN_REPETITIONS[index]}" >>"$plan_tmp"
done
if [[ -e "$MATRIX_PLAN" ]]; then
	if ! cmp -s "$plan_tmp" "$MATRIX_PLAN"; then
		rm -f -- "$plan_tmp"
		die "plan differs from the saved plan for matrix $MATRIX_ID"
	fi
	rm -f -- "$plan_tmp"
else
	mv -- "$plan_tmp" "$MATRIX_PLAN"
fi
if [[ -s "$MATRIX_SUMMARY" ]]; then
	read -r existing_header <"$MATRIX_SUMMARY"
	[[ "$existing_header" == "$MATRIX_HEADER" ]] ||
		die "matrix-summary.csv header does not match this driver"
fi
(
	exec {lock_fd}>"$WRITE_LOCK"
	flock -x "$lock_fd"
	if [[ ! -s "$MATRIX_SUMMARY" ]]; then
		printf '%s\n' "$MATRIX_HEADER" >"$MATRIX_SUMMARY"
	fi
	flock -u "$lock_fd"
	exec {lock_fd}>&-
)

append_matrix_row()
{
	local repetition=$1 attempt=$2 run_id=$3 row=$4
	local lock_fd

	(
		exec {lock_fd}>"$WRITE_LOCK"
		flock -x "$lock_fd"
		if [[ ! -s "$MATRIX_SUMMARY" ]]; then
			printf '%s\n' "$MATRIX_HEADER" >"$MATRIX_SUMMARY"
		fi
		if ! awk -F, -v id="$run_id" \
			'NR > 1 && $3 == id { found = 1 } END { exit !found }' \
			"$MATRIX_SUMMARY"; then
			printf '%s,%s,%s\n' "$repetition" "$attempt" "$row" \
				>>"$MATRIX_SUMMARY"
		fi
		flock -u "$lock_fd"
		exec {lock_fd}>&-
	)
}

matrix_run_recorded()
{
	local run_id=$1
	awk -F, -v id="$run_id" \
		'NR > 1 && $3 == id { found = 1 } END { exit !found }' \
		"$MATRIX_SUMMARY"
}

SUMMARY_ROW=
SUMMARY_STATUS=
SUMMARY_WALL=
SUMMARY_RUN_ID=
SUMMARY_CONFIG=
SUMMARY_TEST=
read_summary()
{
	local summary_file=$1 header field_count
	[[ -f "$summary_file" ]] || return 1
	IFS= read -r header <"$summary_file" || return 1
	[[ "$header" == "$SUMMARY_HEADER" ]] || return 1
	SUMMARY_ROW="$(tail -n 1 "$summary_file")"
	[[ -n "$SUMMARY_ROW" ]] || return 1
	field_count="$(awk -F, '{ print NF }' <<<"$SUMMARY_ROW")"
	[[ "$field_count" == 35 ]] || return 1
	SUMMARY_RUN_ID="$(cut -d, -f1 <<<"$SUMMARY_ROW")"
	SUMMARY_CONFIG="$(cut -d, -f2 <<<"$SUMMARY_ROW")"
	SUMMARY_TEST="$(cut -d, -f3 <<<"$SUMMARY_ROW")"
	SUMMARY_STATUS="$(cut -d, -f4 <<<"$SUMMARY_ROW")"
	SUMMARY_WALL="$(cut -d, -f5 <<<"$SUMMARY_ROW")"
}

DONE=0
FAILED=0
WALL_SUM=0
WALL_COUNT=0
declare -a QUEUE_CONFIGS=() QUEUE_TESTS=() QUEUE_REPETITIONS=() QUEUE_ATTEMPTS=()
	for ((index = 0; index < ${#PLAN_CONFIGS[@]}; index++)); do
		config=${PLAN_CONFIGS[index]}
		test=${PLAN_TESTS[index]}
		repetition=${PLAN_REPETITIONS[index]}
		attempt_count="$(awk -F, -v config="$config" -v test="$test" \
			-v repetition="$repetition" \
			'NR > 1 && $1 == repetition && $4 == config && $5 == test { count++ }
				END { print count + 0 }' "$MATRIX_SUMMARY")"
	success_found=0
	run_dirs=()
	shopt -s nullglob
	run_dirs=("$RUNS_DIR/${MATRIX_ID}-${test}-${config}-r${repetition}-"*)
	shopt -u nullglob
	for run_dir in "${run_dirs[@]}"; do
		[[ -d "$run_dir" ]] || continue
		summary_file="${run_dir}/summary.csv"
		if ! read_summary "$summary_file"; then
			continue
		fi
		[[ "$SUMMARY_CONFIG" == "$config" && "$SUMMARY_TEST" == "$test" &&
			"$SUMMARY_RUN_ID" == "${run_dir##*/}" ]] ||
			die "summary does not match run directory: $summary_file"
		if ! matrix_run_recorded "$SUMMARY_RUN_ID"; then
			((attempt_count += 1))
			append_matrix_row "$repetition" "$attempt_count" \
				"$SUMMARY_RUN_ID" "$SUMMARY_ROW"
		fi
		if [[ "$SUMMARY_STATUS" == ok ]]; then
			success_found=1
		fi
	done
	failure_count="$(awk -F, -v config="$config" -v test="$test" \
		-v repetition="$repetition" \
		'NR > 1 && $1 == repetition && $4 == config && $5 == test &&
			$6 != "ok" { count++ }
			END { print count + 0 }' "$MATRIX_SUMMARY")"
	if ((success_found)); then
		((DONE += 1))
	elif ((failure_count >= 2)); then
		((DONE += 1))
		((FAILED += 1))
	else
		QUEUE_CONFIGS+=("$config")
		QUEUE_TESTS+=("$test")
		QUEUE_REPETITIONS+=("$repetition")
		QUEUE_ATTEMPTS+=("$((failure_count + 1))")
	fi
done

if [[ -s "$MATRIX_SUMMARY" ]]; then
	read -r WALL_SUM WALL_COUNT < <(
		awk -F, 'NR > 1 && $7 ~ /^[0-9]+$/ { sum += $7; count++ }
			END { printf "%d %d\n", sum, count }' "$MATRIX_SUMMARY"
	)
fi
TOTAL=${#PLAN_CONFIGS[@]}
RUNNING=0

write_progress_locked()
{
	local done_count failed_count running_count wall_sum wall_count eta
	IFS=$'\t' read -r done_count failed_count running_count wall_sum wall_count \
		<"$STATE_FILE"
	eta="$(awk -v remaining="$((TOTAL - done_count))" \
		-v sum="$wall_sum" -v count="$wall_count" -v jobs="$JOBS" \
		'BEGIN {
			if (count == 0 || jobs == 0) print 0;
			else printf "%d", (remaining * sum / count / jobs) + 0.5;
		}')"
	printf '%s done=%s/%s running=%s failed=%s eta_seconds=%s\n' \
		"$(date -Is)" "$done_count" "$TOTAL" "$running_count" \
		"$failed_count" "$eta" >>"$PROGRESS_LOG"
}

write_state()
{
	local done_count=$1 failed_count=$2 running_count=$3
	local wall_sum=$4 wall_count=$5 lock_fd
	(
		exec {lock_fd}>"$WRITE_LOCK"
		flock -x "$lock_fd"
		printf '%s\t%s\t%s\t%s\t%s\n' "$done_count" "$failed_count" \
			"$running_count" "$wall_sum" "$wall_count" >"$STATE_FILE"
		write_progress_locked
		flock -u "$lock_fd"
		exec {lock_fd}>&-
	)
}

append_progress()
{
	local lock_fd
	(
		exec {lock_fd}>"$WRITE_LOCK"
		flock -x "$lock_fd"
		write_progress_locked
		flock -u "$lock_fd"
		exec {lock_fd}>&-
	)
}

append_host_sample()
{
	local sample lock_fd
	sample="$(
		printf 'timestamp=%s\n' "$(date -Is)"
		uptime
		free -m
	)"
	(
		exec {lock_fd}>"$WRITE_LOCK"
		flock -x "$lock_fd"
		printf '%s\n\n' "$sample" >>"$HOST_LOAD"
		flock -u "$lock_fd"
		exec {lock_fd}>&-
	)
}

host_sampler()
{
	local sleep_pid=
	trap 'if [[ -n "$sleep_pid" ]]; then
		kill "$sleep_pid" 2>/dev/null || true
	fi
	exit 0' TERM INT
	while :; do
		append_host_sample
		append_progress
		sleep 60 &
		sleep_pid=$!
		wait "$sleep_pid" || true
		sleep_pid=
	done
}

write_state "$DONE" "$FAILED" "$RUNNING" "$WALL_SUM" "$WALL_COUNT"
host_sampler &
HOST_SAMPLER_PID=$!

INTERRUPTED=0
INTERRUPT_STATUS=0
declare -a ACTIVE_PIDS=()
declare -A PID_CONFIG=() PID_TEST=() PID_REPETITION=() PID_ATTEMPT=()
declare -A PID_RUN_ID=() PID_START_SECONDS=()

# shellcheck disable=SC2329
on_signal()
{
	local signal_status=$1
	if ((INTERRUPTED)); then
		return 0
	fi
	INTERRUPTED=1
	INTERRUPT_STATUS=$signal_status
	for pid in "${ACTIVE_PIDS[@]}"; do
		kill -TERM "$pid" 2>/dev/null || true
	done
}
trap 'on_signal 143' TERM
trap 'on_signal 130' INT

stop_host_sampler()
{
	if [[ -n "${HOST_SAMPLER_PID:-}" ]]; then
		kill -TERM "$HOST_SAMPLER_PID" 2>/dev/null || true
		wait "$HOST_SAMPLER_PID" 2>/dev/null || true
		HOST_SAMPLER_PID=
	fi
}

# shellcheck disable=SC2329
cleanup()
{
	local exit_status=$?
	trap - EXIT
	for pid in "${ACTIVE_PIDS[@]}"; do
		kill -TERM "$pid" 2>/dev/null || true
	done
	for pid in "${ACTIVE_PIDS[@]}"; do
		wait "$pid" 2>/dev/null || true
	done
	stop_host_sampler
	exit "$exit_status"
}
trap cleanup EXIT

unique_run_id()
{
	local test=$1 config=$2 repetition=$3 epoch run_id
	epoch="$(date +%s)"
	run_id="${MATRIX_ID}-${test}-${config}-r${repetition}-${epoch}"
	while [[ -e "${RUNS_DIR}/${run_id}" ||
		-e "${RUNS_DIR}/${run_id}.host.log" ]]; do
		((epoch += 1))
		run_id="${MATRIX_ID}-${test}-${config}-r${repetition}-${epoch}"
	done
	printf '%s\n' "$run_id"
}

start_job()
{
	local config=$1 test=$2 repetition=$3 attempt=$4 run_id pid
	((INTERRUPTED)) && return 1
	run_id="$(unique_run_id "$test" "$config" "$repetition")"
	((RUNNING += 1))
	write_state "$DONE" "$FAILED" "$RUNNING" "$WALL_SUM" "$WALL_COUNT"
	if ((INTERRUPTED)); then
		RUNNING=$((RUNNING - 1))
		write_state "$DONE" "$FAILED" "$RUNNING" "$WALL_SUM" "$WALL_COUNT"
		return 1
	fi
	QEMU_LOG_DIR="$RUNS_DIR" "$FS_COMPARE" "$config" "$test" "$run_id" \
		>"${RUNS_DIR}/${run_id}.host.log" 2>&1 &
	pid=$!
	PID_CONFIG["$pid"]=$config
	PID_TEST["$pid"]=$test
	PID_REPETITION["$pid"]=$repetition
	PID_ATTEMPT["$pid"]=$attempt
	PID_RUN_ID["$pid"]=$run_id
	PID_START_SECONDS["$pid"]=$SECONDS
	ACTIVE_PIDS+=("$pid")
	if ((INTERRUPTED)); then
		kill -TERM "$pid" 2>/dev/null || true
	fi
}

append_synthetic_failure()
{
	local config=$1 test=$2 run_id=$3 wall=$4
	local -a fields=("$run_id" "$config" "$test" fail:summary_missing "$wall")
	while ((${#fields[@]} < 35)); do
		fields+=("")
	done
	local IFS=,
	printf '%s\n' "${fields[*]}"
}

complete_job()
{
	local pid=$1 child_status=$2
	local config=${PID_CONFIG[$pid]} test=${PID_TEST[$pid]}
	local repetition=${PID_REPETITION[$pid]} attempt=${PID_ATTEMPT[$pid]}
	local run_id=${PID_RUN_ID[$pid]} start_seconds=${PID_START_SECONDS[$pid]}
	local summary_file="${RUNS_DIR}/${run_id}/summary.csv"
	local wall status success=0 row
	local -a remaining_pids=()
	local active_pid

	if read_summary "$summary_file" &&
		[[ "$SUMMARY_RUN_ID" == "$run_id" && "$SUMMARY_CONFIG" == "$config" &&
			"$SUMMARY_TEST" == "$test" ]]; then
		status=$SUMMARY_STATUS
		wall=$SUMMARY_WALL
		row=$SUMMARY_ROW
	else
		wall=$((SECONDS - start_seconds))
		status=fail:summary_missing
		row="$(append_synthetic_failure "$config" "$test" "$run_id" "$wall")"
	fi
	append_matrix_row "$repetition" "$attempt" "$run_id" "$row"
	if [[ "$wall" =~ ^[0-9]+$ ]]; then
		WALL_SUM=$((WALL_SUM + wall))
		((WALL_COUNT += 1))
	fi
	RUNNING=$((RUNNING - 1))
	for active_pid in "${ACTIVE_PIDS[@]}"; do
		[[ "$active_pid" == "$pid" ]] || remaining_pids+=("$active_pid")
	done
	ACTIVE_PIDS=("${remaining_pids[@]}")
	unset "PID_CONFIG[$pid]" "PID_TEST[$pid]" "PID_REPETITION[$pid]"
	unset "PID_ATTEMPT[$pid]" "PID_RUN_ID[$pid]" "PID_START_SECONDS[$pid]"

	if [[ "$status" == ok ]]; then
		((DONE += 1))
		success=1
	elif ((attempt < 2 && !INTERRUPTED)); then
		QUEUE_CONFIGS+=("$config")
		QUEUE_TESTS+=("$test")
		QUEUE_REPETITIONS+=("$repetition")
		QUEUE_ATTEMPTS+=("$((attempt + 1))")
	else
		((DONE += 1))
		((FAILED += 1))
	fi
	write_state "$DONE" "$FAILED" "$RUNNING" "$WALL_SUM" "$WALL_COUNT"
	if ((child_status != 0 && success)); then
		printf 'Warning: %s exited %s although summary status was ok\n' \
			"$run_id" "$child_status" >&2
	fi
}

queue_index=0
while :; do
	while ((!INTERRUPTED && RUNNING < JOBS &&
		queue_index < ${#QUEUE_CONFIGS[@]})); do
		if start_job "${QUEUE_CONFIGS[queue_index]}" \
			"${QUEUE_TESTS[queue_index]}" \
			"${QUEUE_REPETITIONS[queue_index]}" \
			"${QUEUE_ATTEMPTS[queue_index]}"; then
			((queue_index += 1))
		else
			break
		fi
	done
	((RUNNING > 0)) || break
	completed_pid=
	child_status=0
	if wait -n -p completed_pid "${ACTIVE_PIDS[@]}"; then
		child_status=0
	else
		child_status=$?
	fi
	if [[ -z "${completed_pid:-}" ]]; then
		continue
	fi
	complete_job "$completed_pid" "$child_status"
done

stop_host_sampler
append_progress
if ((INTERRUPTED)); then
	exit "$INTERRUPT_STATUS"
fi
if ((FAILED > 0)); then
	exit 1
fi
exit 0
