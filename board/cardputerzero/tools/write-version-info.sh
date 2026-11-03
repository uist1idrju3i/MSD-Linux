#!/bin/sh
set -eu

target_dir="${1:?Buildroot must pass TARGET_DIR}"
repo_dir="${2:?Repository directory is required}"

version_label=unreleased
version_id=
display_version='unreleased (commit unknown)'
build_id=unknown

if command -v git >/dev/null 2>&1 &&
	git -C "$repo_dir" rev-parse --verify HEAD >/dev/null 2>&1; then
	valid_tags="$(git -C "$repo_dir" tag --points-at HEAD --list 'v*' |
		grep -E '^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-rc\.([1-9][0-9]*))?$' ||
		true)"
	tag_count=0
	if [ -n "$valid_tags" ]; then
		tag_count="$(printf '%s\n' "$valid_tags" | wc -l | tr -d '[:space:]')"
	fi
	if [ "$tag_count" -gt 1 ]; then
		printf '%s\n' 'error: multiple SemVer tags point at HEAD' >&2
		exit 1
	fi
	if [ "$tag_count" -eq 1 ]; then
		version_label="$valid_tags"
		version_id="${version_label#v}"
	fi

	full_commit="$(git -C "$repo_dir" rev-parse HEAD)"
	short_commit="$(git -C "$repo_dir" rev-parse --short=7 HEAD)"
	dirty_suffix=
	if ! git -C "$repo_dir" diff --quiet --ignore-submodules=dirty HEAD --; then
		dirty_suffix=-dirty
	fi
	full_commit="${full_commit}${dirty_suffix}"
	short_commit="${short_commit}${dirty_suffix}"
	build_id="$full_commit"
	commit_epoch="$(git -C "$repo_dir" log -1 --format=%ct HEAD)"
	commit_time="$(TZ=JST-9 date -d "@$commit_epoch" '+%Y-%m-%d %H:%M:%S JST')"
	display_version="$version_label ($commit_time, commit $short_commit)"
fi

mkdir -p "$target_dir/etc" "$target_dir/usr/lib"
printf 'MSD/Linux %s\n' "$display_version" > "$target_dir/etc/issue"

os_release_link="$target_dir/etc/os-release"
if [ -L "$os_release_link" ]; then
	if [ "$(readlink "$os_release_link")" != '../usr/lib/os-release' ]; then
		printf 'error: unexpected /etc/os-release symlink target: %s\n' \
			"$(readlink "$os_release_link")" >&2
		exit 1
	fi
elif [ -e "$os_release_link" ]; then
	printf '%s\n' 'error: /etc/os-release exists and is not a symlink' >&2
	exit 1
else
	ln -s ../usr/lib/os-release "$os_release_link"
fi

{
	printf 'NAME="MSD/Linux"\n'
	printf 'ID=msd-linux\n'
	printf 'PRETTY_NAME="MSD/Linux %s"\n' "$version_label"
	printf 'VERSION="%s"\n' "$display_version"
	if [ -n "$version_id" ]; then
		printf 'VERSION_ID=%s\n' "$version_id"
	fi
	printf 'BUILD_ID=%s\n' "$build_id"
	printf 'HOME_URL="https://muromi.moe/"\n'
} > "$target_dir/usr/lib/os-release"
