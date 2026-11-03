#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPT="${REPO_ROOT}/board/cardputerzero/tools/write-version-info.sh"
POST_BUILD="${REPO_ROOT}/board/cardputerzero/post-build.sh"
TEST_DIR="$(mktemp -d)"
EXPECTED_TIME='2026-11-03 23:00:00 JST'

cleanup() {
	rm -rf "$TEST_DIR"
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM

fail() {
	printf 'not ok - %s\n' "$*" >&2
	exit 1
}

make_repo() {
	local repo="${TEST_DIR}/$1"
	mkdir -p "$repo"
	git -C "$repo" init -q
	printf 'tracked\n' > "$repo/tracked.txt"
	git -C "$repo" add tracked.txt
	env \
		GIT_AUTHOR_NAME='Version Info Test' \
		GIT_AUTHOR_EMAIL='version-info@example.invalid' \
		GIT_AUTHOR_DATE='@1793714400' \
		GIT_COMMITTER_NAME='Version Info Test' \
		GIT_COMMITTER_EMAIL='version-info@example.invalid' \
		GIT_COMMITTER_DATE='@1793714400' \
		git -C "$repo" commit -q -m fixture
	printf '%s\n' "$repo"
}

make_target() {
	local target="${TEST_DIR}/target-$1"
	mkdir -p "$target/etc" "$target/usr/lib"
	printf '%s\n' "$target"
}

assert_output() {
	local target="$1"
	local issue="$2"
	local pretty_name="$3"
	local version="$4"
	local version_id="$5"
	local build_id="$6"

	printf '%s\n' "$issue" > "$TEST_DIR/expected-issue"
	cmp "$TEST_DIR/expected-issue" "$target/etc/issue" ||
		fail "unexpected /etc/issue in $target"

	{
		printf 'NAME="MSD/Linux"\n'
		printf 'ID=msd-linux\n'
		printf 'PRETTY_NAME="%s"\n' "$pretty_name"
		printf 'VERSION="%s"\n' "$version"
		if [ -n "$version_id" ]; then
			printf 'VERSION_ID=%s\n' "$version_id"
		fi
		printf 'BUILD_ID=%s\n' "$build_id"
		printf 'HOME_URL="https://muromi.moe/"\n'
	} > "$TEST_DIR/expected-os-release"
	cmp "$TEST_DIR/expected-os-release" "$target/usr/lib/os-release" ||
		fail "unexpected /usr/lib/os-release in $target"
}

check_symlink() {
	local target="$1"
	[ -L "$target/etc/os-release" ] ||
		fail "/etc/os-release is not a symlink in $target"
	[ "$(readlink "$target/etc/os-release")" = '../usr/lib/os-release' ] ||
		fail "/etc/os-release symlink target changed in $target"
}

# shellcheck disable=SC2016 # Match the literal invocation in post-build.sh.
grep -Fq '"$(dirname "$0")/tools/write-version-info.sh" "$target_dir" "$(dirname "$0")"' \
	"$POST_BUILD" || fail "post-build does not invoke write-version-info.sh"
printf 'ok - post-build invokes write-version-info.sh\n'

repo="$(make_repo no-tag)"
full_commit="$(git -C "$repo" rev-parse HEAD)"
short_commit="$(git -C "$repo" rev-parse --short=7 HEAD)"
target="$(make_target no-tag)"
"$SCRIPT" "$target" "$repo"
version="unreleased ($EXPECTED_TIME, commit $short_commit)"
assert_output "$target" "MSD/Linux $version" "MSD/Linux unreleased" \
	"$version" '' "$full_commit"
printf 'ok - untagged repository writes unreleased metadata\n'

repo_rc="$(make_repo rc)"
git -C "$repo_rc" tag v0.1.0-rc.1
full_rc="$(git -C "$repo_rc" rev-parse HEAD)"
short_rc="$(git -C "$repo_rc" rev-parse --short=7 HEAD)"
target_rc="$(make_target rc)"
"$SCRIPT" "$target_rc" "$repo_rc"
version="v0.1.0-rc.1 ($EXPECTED_TIME, commit $short_rc)"
assert_output "$target_rc" "MSD/Linux $version" "MSD/Linux v0.1.0-rc.1" \
	"$version" '0.1.0-rc.1' "$full_rc"
printf 'ok - rc tag and VERSION_ID are displayed\n'

repo_release="$(make_repo release)"
git -C "$repo_release" tag v0.1.0
full_release="$(git -C "$repo_release" rev-parse HEAD)"
short_release="$(git -C "$repo_release" rev-parse --short=7 HEAD)"
target_release="$(make_target release)"
"$SCRIPT" "$target_release" "$repo_release"
version="v0.1.0 ($EXPECTED_TIME, commit $short_release)"
assert_output "$target_release" "MSD/Linux $version" "MSD/Linux v0.1.0" \
	"$version" '0.1.0' "$full_release"
printf 'ok - release tag is displayed\n'

repo_invalid="$(make_repo invalid-tags)"
git -C "$repo_invalid" tag v1
git -C "$repo_invalid" tag foo
git -C "$repo_invalid" tag v0.1.0-rc1
full_invalid="$(git -C "$repo_invalid" rev-parse HEAD)"
short_invalid="$(git -C "$repo_invalid" rev-parse --short=7 HEAD)"
target_invalid="$(make_target invalid-tags)"
"$SCRIPT" "$target_invalid" "$repo_invalid"
version="unreleased ($EXPECTED_TIME, commit $short_invalid)"
assert_output "$target_invalid" "MSD/Linux $version" "MSD/Linux unreleased" \
	"$version" '' "$full_invalid"
printf 'ok - non-SemVer tags are ignored\n'

repo_multiple="$(make_repo multiple-tags)"
git -C "$repo_multiple" tag v0.1.0-rc.1
git -C "$repo_multiple" tag v0.1.0
target_multiple="$(make_target multiple-tags)"
if "$SCRIPT" "$target_multiple" "$repo_multiple" > "$TEST_DIR/multiple-tags.log" 2>&1; then
	fail "multiple SemVer tags unexpectedly succeeded"
fi
grep -Fq 'error: multiple SemVer tags point at HEAD' "$TEST_DIR/multiple-tags.log" ||
	fail "multiple-tag error was not reported"
printf 'ok - multiple SemVer tags fail\n'

repo_dirty="$(make_repo dirty)"
git -C "$repo_dirty" tag v0.1.0-rc.1
full_dirty="$(git -C "$repo_dirty" rev-parse HEAD)"
short_dirty="$(git -C "$repo_dirty" rev-parse --short=7 HEAD)"
printf 'modified\n' > "$repo_dirty/tracked.txt"
target_dirty="$(make_target dirty)"
"$SCRIPT" "$target_dirty" "$repo_dirty"
version="v0.1.0-rc.1 ($EXPECTED_TIME, commit ${short_dirty}-dirty)"
assert_output "$target_dirty" "MSD/Linux $version" "MSD/Linux v0.1.0-rc.1" \
	"$version" '0.1.0-rc.1' "${full_dirty}-dirty"
printf 'ok - modified tracked files add the dirty suffix\n'

mkdir -p "$TEST_DIR/not-a-repo"
target_unknown="$(make_target not-a-repo)"
"$SCRIPT" "$target_unknown" "$TEST_DIR/not-a-repo"
assert_output "$target_unknown" 'MSD/Linux unreleased (commit unknown)' \
	'MSD/Linux unreleased' 'unreleased (commit unknown)' '' unknown
printf 'ok - a non-repository directory uses unknown metadata\n'

no_git_bin="$TEST_DIR/no-git-bin"
mkdir -p "$no_git_bin"
for utility in mkdir ln readlink; do
	ln -s "$(command -v "$utility")" "$no_git_bin/$utility"
done
target_no_git="$(make_target no-git)"
PATH="$no_git_bin" "$SCRIPT" "$target_no_git" "$repo_rc"
assert_output "$target_no_git" 'MSD/Linux unreleased (commit unknown)' \
	'MSD/Linux unreleased' 'unreleased (commit unknown)' '' unknown
printf 'ok - missing git uses unknown metadata\n'

target_tz="$(make_target caller-tz)"
TZ=America/New_York "$SCRIPT" "$target_tz" "$repo_rc"
version="v0.1.0-rc.1 ($EXPECTED_TIME, commit $short_rc)"
assert_output "$target_tz" "MSD/Linux $version" "MSD/Linux v0.1.0-rc.1" \
	"$version" '0.1.0-rc.1' "$full_rc"
printf 'ok - caller timezone does not change JST output\n'

target_link="$(make_target existing-link)"
ln -s ../usr/lib/os-release "$target_link/etc/os-release"
"$SCRIPT" "$target_link" "$repo_rc"
check_symlink "$target_link"
version="v0.1.0-rc.1 ($EXPECTED_TIME, commit $short_rc)"
assert_output "$target_link" "MSD/Linux $version" "MSD/Linux v0.1.0-rc.1" \
	"$version" '0.1.0-rc.1' "$full_rc"
printf 'ok - existing /etc/os-release symlink is preserved\n'

printf 'All version-info host tests passed.\n'
