#!/bin/sh
set -eu

target_dir="${1:?Buildroot must pass TARGET_DIR}"
linux_dir="${2:?Buildroot must pass the Linux build directory}"
sign_file="$linux_dir/scripts/sign-file"
signing_key="$linux_dir/certs/signing_key.pem"
signing_cert="$linux_dir/certs/signing_key.x509"
signature_marker='~Module signature appended~'

for path in "$sign_file" "$signing_key" "$signing_cert"; do
	if [ ! -f "$path" ]; then
		printf 'Kernel module signing input is missing: %s\n' "$path" >&2
		exit 1
	fi
done

modules_dir="$target_dir/lib/modules"
if [ ! -d "$modules_dir" ]; then
	printf 'Installed kernel modules are missing: %s\n' "$modules_dir" >&2
	exit 1
fi

find "$modules_dir" -type f \( -name '*.ko' -o -name '*.ko.xz' \) -print |
	while IFS= read -r module; do
		case "$module" in
			*.ko.xz)
				if xz -dc "$module" | tail -c 28 | grep -Fq "$signature_marker"; then
					continue
				fi
				raw_module="${module}.signing"
				signed_module="${module}.signed"
				xz -dc "$module" > "$raw_module"
				"$sign_file" sha256 "$signing_key" "$signing_cert" "$raw_module"
				xz -c "$raw_module" > "$signed_module"
				mv "$signed_module" "$module"
				rm -f "$raw_module"
				;;
			*.ko)
				if tail -c 28 "$module" | grep -Fq "$signature_marker"; then
					continue
				fi
				"$sign_file" sha256 "$signing_key" "$signing_cert" "$module"
				;;
		esac
	done

find "$modules_dir" -type f \( -name '*.ko' -o -name '*.ko.xz' \) -print |
	while IFS= read -r module; do
		case "$module" in
			*.ko.xz)
				if ! xz -dc "$module" | tail -c 28 | grep -Fq "$signature_marker"; then
					printf 'Kernel module remains unsigned: %s\n' "$module" >&2
					exit 1
				fi
				;;
			*.ko)
				if ! tail -c 28 "$module" | grep -Fq "$signature_marker"; then
					printf 'Kernel module remains unsigned: %s\n' "$module" >&2
					exit 1
				fi
				;;
		esac
	done
