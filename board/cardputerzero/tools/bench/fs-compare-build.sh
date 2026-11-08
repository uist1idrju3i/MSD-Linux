#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../../.." && pwd -P)"
BUILDROOT="${REPO_ROOT}/vendor/buildroot"
OUTPUT_DIR="${OUTPUT_DIR:-${REPO_ROOT}/output-fscmp}"
BR2_FRAGMENT="${SCRIPT_DIR}/fs-compare.buildroot.fragment"
REPLAY_LOG_URL="https://github.com/josefbacik/log-writes.git"
REPLAY_LOG_COMMIT="7b70d8a6863c5de30933d42a7672d35d01d2dc6c"
REPLAY_LOG_SOURCE="${OUTPUT_DIR}/build/fs-compare/log-writes"
ARTIFACT_DIR="${OUTPUT_DIR}/fs-compare"

mkdir -p "$OUTPUT_DIR"
if [[ ! -s "${OUTPUT_DIR}/.config" ]]; then
	cat "${REPO_ROOT}/configs/msd_cardputerzero_defconfig" "$BR2_FRAGMENT" \
		>"${OUTPUT_DIR}/fs-compare_defconfig"
	make -C "$BUILDROOT" BR2_EXTERNAL="$REPO_ROOT" O="$OUTPUT_DIR" \
		BR2_DEFCONFIG="${OUTPUT_DIR}/fs-compare_defconfig" defconfig
elif ! grep -Fq 'fs-compare.fragment' "${OUTPUT_DIR}/.config"; then
	printf 'Refusing to reuse %s without the fs-compare config fragment\n' \
		"${OUTPUT_DIR}/.config" >&2
	exit 1
fi

if ! grep -Eq '^BR2_EXTERNAL_MSD_PATH="[^"]+"' "${OUTPUT_DIR}/.config"; then
	printf 'Buildroot configuration lost BR2_EXTERNAL_MSD_PATH\n' >&2
	exit 1
fi
linux_fragment_value="$(
	sed -n 's/^BR2_LINUX_KERNEL_CONFIG_FRAGMENT_FILES="\(.*\)"/\1/p' \
		"${OUTPUT_DIR}/.config"
)"
for fragment in \
	board/cardputerzero/linux.fragment \
	board/cardputerzero/tools/bench/fs-compare.fragment; do
	if [[ "$linux_fragment_value" != *"$fragment"* ]]; then
		printf 'Buildroot configuration lost Linux fragment %s\n' \
			"$fragment" >&2
		exit 1
	fi
done

required_buildroot=(
	BR2_PACKAGE_BTRFS_PROGS
	BR2_PACKAGE_F2FS_TOOLS
	BR2_PACKAGE_CRYPTSETUP
	BR2_PACKAGE_LVM2
	BR2_PACKAGE_FSCRYPTCTL
	BR2_PACKAGE_UTIL_LINUX_FALLOCATE
	BR2_PACKAGE_UTIL_LINUX_LOSETUP
	BR2_PACKAGE_UTIL_LINUX_PARTX
)
missing_buildroot=()
for symbol in "${required_buildroot[@]}"; do
	if ! grep -qx "${symbol}=y" "${OUTPUT_DIR}/.config"; then
		missing_buildroot+=("$symbol")
	fi
done
if ((${#missing_buildroot[@]})); then
	printf 'Buildroot configuration did not enable: %s\n' \
		"${missing_buildroot[*]}" >&2
	exit 1
fi
if ! grep -qx '# BR2_PACKAGE_LVM2_STANDARD_INSTALL is not set' \
	"${OUTPUT_DIR}/.config"; then
	printf 'Buildroot configuration did not keep LVM2 dmsetup-only\n' >&2
	exit 1
fi

make -C "$BUILDROOT" BR2_EXTERNAL="$REPO_ROOT" O="$OUTPUT_DIR" -j"$(nproc)"

kernel_configs=()
while IFS= read -r config; do
	kernel_configs+=("$config")
done < <(find "${OUTPUT_DIR}/build" -maxdepth 3 -type f -path '*/linux*/.config' -print)
if ((${#kernel_configs[@]} != 1)); then
	printf 'Expected one built Linux .config under %s/build, found %d\n' \
		"$OUTPUT_DIR" "${#kernel_configs[@]}" >&2
	exit 1
fi

required_kernel=(
	CONFIG_BLK_DEV_LOOP
	CONFIG_BLK_DEV_DM
	CONFIG_DM_LOG_WRITES
	CONFIG_BTRFS_FS
	CONFIG_F2FS_FS
	CONFIG_F2FS_FS_COMPRESSION
	CONFIG_F2FS_FS_ZSTD
	CONFIG_F2FS_FS_LZ4
	CONFIG_FS_ENCRYPTION
	CONFIG_DM_CRYPT
	CONFIG_DM_INTEGRITY
	CONFIG_CRYPTO_ADIANTUM
	CONFIG_CRYPTO_XXHASH
	CONFIG_CRYPTO_BLAKE2B
	CONFIG_CRYPTO_SHA256
	CONFIG_CRYPTO_HMAC
	CONFIG_CRYPTO_XTS
)
not_built=()
printf 'kernel_config=%s\n' "${kernel_configs[0]}"
for symbol in "${required_kernel[@]}"; do
	if grep -qx "${symbol}=y" "${kernel_configs[0]}"; then
		printf '%s=y\n' "$symbol"
	else
		value="$(grep -E "^(${symbol}=|# ${symbol} is not set$)" \
			"${kernel_configs[0]}" || printf 'missing')"
		printf '%s: %s\n' "$symbol" "$value"
		not_built+=("$symbol")
	fi
done
if ((${#not_built[@]})); then
	printf 'Required kernel symbols are not =y: %s\n' \
		"${not_built[*]}" >&2
	exit 1
fi

mapfile -t target_compilers < <(compgen -G "${OUTPUT_DIR}/host/bin/aarch64*-gcc")
if ((${#target_compilers[@]} != 1)); then
	printf 'Expected one Buildroot aarch64 compiler, found %d\n' \
		"${#target_compilers[@]}" >&2
	exit 1
fi
target_cc="${target_compilers[0]}"
target_triplet="$("$target_cc" -dumpmachine)"
case "$target_triplet" in
	aarch64*) ;;
	*)
		printf 'Buildroot compiler target is not aarch64: %s\n' \
			"$target_triplet" >&2
		exit 1
		;;
esac

if [[ ! -e "$REPLAY_LOG_SOURCE" ]]; then
	mkdir -p "$(dirname -- "$REPLAY_LOG_SOURCE")"
	git clone --no-checkout "$REPLAY_LOG_URL" "$REPLAY_LOG_SOURCE"
	git -C "$REPLAY_LOG_SOURCE" checkout --detach "$REPLAY_LOG_COMMIT"
elif [[ ! -d "${REPLAY_LOG_SOURCE}/.git" ]]; then
	printf 'Refusing to use non-git replay-log source: %s\n' \
		"$REPLAY_LOG_SOURCE" >&2
	exit 1
fi
source_commit="$(git -C "$REPLAY_LOG_SOURCE" rev-parse HEAD)"
if [[ "$source_commit" != "$REPLAY_LOG_COMMIT" ]]; then
	printf 'Unexpected replay-log commit: %s (expected %s)\n' \
		"$source_commit" "$REPLAY_LOG_COMMIT" >&2
	exit 1
fi
if [[ -n "$(git -C "$REPLAY_LOG_SOURCE" status --porcelain --untracked-files=no)" ]]; then
	printf 'Refusing to build replay-log from a modified source tree: %s\n' \
		"$REPLAY_LOG_SOURCE" >&2
	exit 1
fi

make -B -C "$REPLAY_LOG_SOURCE" CC="$target_cc" \
	CFLAGS="-O2 -Wall -Wextra" replay-log
mkdir -p "$ARTIFACT_DIR"
install -m 0755 "${REPLAY_LOG_SOURCE}/replay-log" "${ARTIFACT_DIR}/replay-log"
binary_sha="$(sha256sum "${ARTIFACT_DIR}/replay-log" | cut -d' ' -f1)"
{
	printf 'source=%s\n' "$REPLAY_LOG_URL"
	printf 'commit=%s\n' "$source_commit"
	printf 'compiler=%s\n' "$target_cc"
	printf 'target=%s\n' "$target_triplet"
	printf 'sha256=%s\n' "$binary_sha"
} >"${ARTIFACT_DIR}/replay-log.provenance"
printf 'replay-log: source_commit=%s sha256=%s compiler=%s\n' \
	"$source_commit" "$binary_sha" "$target_cc"
file "${ARTIFACT_DIR}/replay-log"

staging_dir="${OUTPUT_DIR}/staging"
if [[ ! -f "${staging_dir}/usr/include/openssl/evp.h" ]]; then
	printf 'Buildroot target OpenSSL headers are missing from %s\n' \
		"${staging_dir}/usr/include/openssl/evp.h" >&2
	exit 1
fi
"$target_cc" -O2 -Wall -Wextra -std=c11 \
	-I"${staging_dir}/usr/include" \
	"${SCRIPT_DIR}/fs-compare-workload.c" \
	-L"${staging_dir}/usr/lib" -Wl,-rpath-link,"${staging_dir}/usr/lib" \
	-lcrypto -o "${ARTIFACT_DIR}/fs-compare-workload"
printf 'fs-compare-workload: sha256=%s compiler=%s\n' \
	"$(sha256sum "${ARTIFACT_DIR}/fs-compare-workload" | cut -d' ' -f1)" \
	"$target_cc"
file "${ARTIFACT_DIR}/fs-compare-workload"
