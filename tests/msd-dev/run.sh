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
    cp -- "${repo_root}/docker/qemu-patches/0001-hw-arm-bcm2835_peripherals-add-unimp-ASB.patch" \
        "${destination}/docker/qemu-patches/0001-hw-arm-bcm2835_peripherals-add-unimp-ASB.patch"
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
    "docker/qemu-patches/0001-hw-arm-bcm2835_peripherals-add-unimp-ASB.patch",
    "docker/qemu-signing-key.asc",
]
assert inputs == expected, f"unexpected image inputs: {inputs!r}"

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
            if str(path.relative_to(root)) not in inputs
        )

assert not missing, f"COPY sources absent from IMAGE_INPUTS: {missing!r}"
print("ok - every Dockerfile COPY source is covered by IMAGE_INPUTS")
PY

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
