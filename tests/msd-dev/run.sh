#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
launcher="${repo_root}/docker/msd-dev"
temporary_root="$(mktemp -d)"
trap 'rm -rf -- "$temporary_root"' EXIT

first_tag="$("${launcher}" tag)"
second_tag="$("${launcher}" tag)"
if [[ ! "${first_tag}" =~ ^inputs-[0-9a-f]{16}$ ]]; then
    printf 'Unexpected image tag: %s\n' "${first_tag}" >&2
    exit 1
fi
if [[ "${first_tag}" != "${second_tag}" ]]; then
    printf 'Image tag is not deterministic: %s != %s\n' "${first_tag}" "${second_tag}" >&2
    exit 1
fi
printf 'ok - tag is deterministic: %s\n' "${first_tag}"

copy_inputs() {
    local destination="$1"
    mkdir -p -- "${destination}/.github" "${destination}/docker/qemu-patches"
    cp -p -- "${launcher}" "${destination}/docker/msd-dev"
    cp -- "${repo_root}/.github/zizmor-requirements.txt" \
        "${destination}/.github/zizmor-requirements.txt"
    cp -- "${repo_root}/docker/debian.sources" \
        "${destination}/docker/debian.sources"
    cp -- "${repo_root}/docker/msd-dev.Dockerfile" \
        "${destination}/docker/msd-dev.Dockerfile"
    cp -- "${repo_root}/docker/qemu-signing-key.asc" \
        "${destination}/docker/qemu-signing-key.asc"
    cp -- "${repo_root}"/docker/qemu-patches/*.patch \
        "${destination}/docker/qemu-patches/"
}

inputs=(
    .github/zizmor-requirements.txt
    docker/debian.sources
    docker/msd-dev.Dockerfile
    docker/qemu-patches/0001-hw-arm-bcm2835_peripherals-add-unimp-ASB.patch
    docker/qemu-signing-key.asc
)

for input in "${inputs[@]}"; do
    fixture="$(mktemp -d "${temporary_root}/input.XXXXXX")"
    copy_inputs "${fixture}"
    fixture_launcher="${fixture}/docker/msd-dev"
    before="$("${fixture_launcher}" tag)"
    printf '\n# tag test mutation\n' >> "${fixture}/${input}"
    after="$("${fixture_launcher}" tag)"
    if [[ "${before}" == "${after}" ]]; then
        printf 'Changing %s did not change the tag.\n' "${input}" >&2
        exit 1
    fi
    printf 'ok - changing %s changes the tag\n' "${input}"
done

fixture="$(mktemp -d "${temporary_root}/patches.XXXXXX")"
copy_inputs "${fixture}"
fixture_launcher="${fixture}/docker/msd-dev"
before="$("${fixture_launcher}" tag)"
printf '%s\n' 'dummy patch' > "${fixture}/docker/qemu-patches/0002-dummy.patch"
after="$("${fixture_launcher}" tag)"
if [[ "${before}" == "${after}" ]]; then
    printf 'Adding a second QEMU patch did not change the tag.\n' >&2
    exit 1
fi
printf 'ok - adding a second QEMU patch changes the tag\n'

rm -- "${fixture}"/docker/qemu-patches/*.patch
if "${fixture_launcher}" tag >/dev/null 2>&1; then
    printf 'Tag command succeeded without QEMU patches.\n' >&2
    exit 1
fi
printf 'ok - tag fails when no QEMU patches are present\n'

python3 - "${repo_root}" <<'PY'
import json
import pathlib
import re
import shlex
import sys

root = pathlib.Path(sys.argv[1])
launcher = (root / "docker/msd-dev").read_text()
match = re.search(r"^IMAGE_INPUTS=\(\n(.*?)^\)", launcher, re.M | re.S)
assert match, "IMAGE_INPUTS array is missing"
inputs = [
    line.strip()
    for line in match.group(1).splitlines()
    if line.strip()
]
expected = [
    ".github/zizmor-requirements.txt",
    "docker/debian.sources",
    "docker/msd-dev.Dockerfile",
    "docker/qemu-signing-key.asc",
]
assert inputs == expected, f"unexpected image inputs: {inputs!r}"
patch_inputs = sorted(
    str(path.relative_to(root))
    for path in (root / "docker/qemu-patches").glob("*.patch")
)
assert patch_inputs, "no QEMU source patches found"
covered_inputs = {*inputs, *patch_inputs}

dockerfile = (root / "docker/msd-dev.Dockerfile").read_text()
assert "ARG QEMU_VERSION=11.1.2" in dockerfile
assert "/opt/qemu/bin/qemu-system-aarch64 -machine help" in dockerfile
assert "raspi3ap" in dockerfile and "raspi3b" in dockerfile
assert "libinsn.so" in dockerfile or "libhotblocks.so" in dockerfile
assert "qemu-img create -f raw /tmp/qemu-smoke.raw 1M" in dockerfile
missing = []
instructions = []
pending = ""
for line in dockerfile.splitlines():
    pending += line.strip()
    if pending.endswith("\\"):
        pending = pending[:-1] + " "
        continue
    instructions.append(pending)
    pending = ""
if pending:
    instructions.append(pending)

for instruction in instructions:
    if not re.match(r"^COPY\s+", instruction):
        continue
    if re.search(r"(?:^|\s)--from(?:=|\s)", instruction):
        continue
    payload = re.sub(r"^COPY\s+", "", instruction, count=1)
    if payload.startswith("["):
        sources = json.loads(payload)[:-1]
    else:
        arguments = [
            argument
            for argument in shlex.split(payload)
            if not argument.startswith("--")
        ]
        sources = arguments[:-1]
    for source in sources:
        matches = list(root.glob(source)) if any(char in source for char in "*?[") else [root / source]
        if not matches:
            missing.append(source)
        missing.extend(
            str(path.relative_to(root))
            for path in matches
            if str(path.relative_to(root)) not in covered_inputs
        )

assert not missing, f"COPY sources absent from IMAGE_INPUTS: {missing!r}"
print("ok - every Dockerfile COPY source is covered by IMAGE_INPUTS")
PY
fake_bin="${temporary_root}/fake-bin"
no_gh_bin="${temporary_root}/no-gh-bin"
docker_log="${temporary_root}/docker.log"
gh_log="${temporary_root}/gh.log"
output="${temporary_root}/output.log"
mkdir -p -- "${fake_bin}" "${no_gh_bin}"
cat > "${fake_bin}/docker" <<'SH'
#!/usr/bin/env bash
printf 'docker %s\n' "$*" >> "${FAKE_DOCKER_LOG}"
if [[ "$1 $2 $3" == "buildx imagetools inspect" ]]; then
    printf '%s\n' "${IMAGETOOLS_OUTPUT:-}" >&2
    exit "${IMAGETOOLS_STATUS:-0}"
fi
exit "${DOCKER_STATUS:-0}"
SH
cat > "${fake_bin}/gh" <<'SH'
#!/usr/bin/env bash
printf 'gh %s\n' "$*" >> "${FAKE_GH_LOG}"
exit "${GH_STATUS:-0}"
SH
chmod +x "${fake_bin}/docker" "${fake_bin}/gh"
for tool in bash dirname sha256sum cut sort; do
    ln -s -- "$(command -v "${tool}")" "${no_gh_bin}/${tool}"
done
ln -s -- "${fake_bin}/docker" "${no_gh_bin}/docker"
env_bin="$(command -v env)"

run_ensure() {
    local path="$1"
    shift
    : > "${docker_log}"
    : > "${gh_log}"
    if "${env_bin}" \
        PATH="${path}" \
        FAKE_DOCKER_LOG="${docker_log}" \
        FAKE_GH_LOG="${gh_log}" \
        MSD_DEV_IMAGE=msd-dev:ensure-test \
        MSD_DEV_REQUIRE_ATTESTATION=1 \
        "$@" \
        "${launcher}" ensure >"${output}" 2>&1; then
        status=0
    else
        status=$?
    fi
}

assert_no_docker_command() {
    local pattern="$1"
    if grep -Eq "${pattern}" "${docker_log}"; then
        printf 'Unexpected Docker command in log: %s\n' "${pattern}" >&2
        return 1
    fi
}

run_ensure "${fake_bin}:${PATH}" IMAGETOOLS_STATUS=0 GH_STATUS=0
[[ "${status}" -eq 0 ]]
grep -Eq '^docker pull ghcr.io/uist1idrju3i/msd-dev:inputs-' "${docker_log}"
grep -Eq '^gh attestation verify oci://ghcr.io/uist1idrju3i/msd-dev:inputs-' "${gh_log}"
grep -Eq '^docker tag ghcr.io/uist1idrju3i/msd-dev:inputs-.* msd-dev:ensure-test$' "${docker_log}"
assert_no_docker_command '^docker build '
printf 'ok - ensure pulls and verifies a published image\n'

run_ensure "${fake_bin}:${PATH}" IMAGETOOLS_STATUS=0 GH_STATUS=1
[[ "${status}" -ne 0 ]]
assert_no_docker_command '^docker build '
printf 'ok - ensure does not build when attestation verification fails\n'

run_ensure "${fake_bin}:${PATH}" IMAGETOOLS_STATUS=1 \
    IMAGETOOLS_OUTPUT='ERROR: ghcr.io/uist1idrju3i/msd-dev:inputs-probe: not found'
[[ "${status}" -eq 0 ]]
grep -Eq '^docker build -f ' "${docker_log}"
grep -Eq 'was not found; building locally' "${output}"
printf 'ok - ensure builds when the remote tag is not found\n'

run_ensure "${fake_bin}:${PATH}" IMAGETOOLS_STATUS=1 \
    IMAGETOOLS_OUTPUT='ERROR: failed to authorize: authentication required'
[[ "${status}" -ne 0 ]]
assert_no_docker_command '^docker build '
printf 'ok - ensure fails closed on registry errors\n'

run_ensure "${no_gh_bin}" IMAGETOOLS_STATUS=0
[[ "${status}" -ne 0 ]]
grep -Eq 'gh is required when MSD_DEV_REQUIRE_ATTESTATION=1' "${output}"
assert_no_docker_command '^docker tag '
assert_no_docker_command '^docker build '
printf 'ok - ensure requires gh when attestation is mandatory\n'

: > "${docker_log}"
"${env_bin}" \
    PATH="${fake_bin}:${PATH}" \
    FAKE_DOCKER_LOG="${docker_log}" \
    MSD_DEV_IMAGE=msd-dev:ensure-test \
    CCACHE_MAXSIZE=3G \
    GITHUB_SHA=deadbeef \
    "${launcher}" true >"${output}" 2>&1
grep -Fq -- '--env CCACHE_MAXSIZE=3G' "${docker_log}"
grep -Fq -- '--env GITHUB_SHA=deadbeef' "${docker_log}"
printf 'ok - launcher passes ccache size and commit to the container\n'

if [[ -n "${MSD_DEV_QEMU_IMAGE:-}" ]]; then
    version_output="$(
        docker run --rm --entrypoint qemu-system-aarch64 \
            "${MSD_DEV_QEMU_IMAGE}" --version
    )"
    [[ "${version_output}" == *"QEMU emulator version 11.1.2"* ]]
    machine_output="$(
        docker run --rm --entrypoint qemu-system-aarch64 \
            "${MSD_DEV_QEMU_IMAGE}" -machine help
    )"
    grep -Eq '(^|[[:space:]])raspi3ap([[:space:]]|$)' <<< "${machine_output}"
    grep -Eq '(^|[[:space:]])raspi3b([[:space:]]|$)' <<< "${machine_output}"
    docker run --rm --entrypoint /bin/bash "${MSD_DEV_QEMU_IMAGE}" -euc \
        'test -s /opt/qemu/lib/qemu-plugins/libinsn.so || test -s /opt/qemu/lib/qemu-plugins/libhotblocks.so'
    docker run --rm --entrypoint /bin/bash "${MSD_DEV_QEMU_IMAGE}" -euc \
        'qemu-img create -f raw /tmp/msd-dev-smoke.img 1M && qemu-img info /tmp/msd-dev-smoke.img >/dev/null'
    printf 'ok - QEMU 11.1.2, machines, plugins, and qemu-img work in %s\n' \
        "${MSD_DEV_QEMU_IMAGE}"
fi
