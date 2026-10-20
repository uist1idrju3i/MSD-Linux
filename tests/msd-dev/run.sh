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
    mkdir -p -- "${destination}/.github" "${destination}/docker"
    cp -p -- "${launcher}" "${destination}/docker/msd-dev"
    cp -- "${repo_root}/.github/zizmor-requirements.txt" \
        "${destination}/.github/zizmor-requirements.txt"
    cp -- "${repo_root}/docker/debian.sources" \
        "${destination}/docker/debian.sources"
    cp -- "${repo_root}/docker/msd-dev.Dockerfile" \
        "${destination}/docker/msd-dev.Dockerfile"
}

inputs=(
    .github/zizmor-requirements.txt
    docker/debian.sources
    docker/msd-dev.Dockerfile
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
]
assert inputs == expected, f"unexpected image inputs: {inputs!r}"

dockerfile = (root / "docker/msd-dev.Dockerfile").read_text()
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
    missing.extend(source for source in sources if source not in inputs)

assert not missing, f"COPY sources absent from IMAGE_INPUTS: {missing!r}"
print("ok - every Dockerfile COPY source is covered by IMAGE_INPUTS")
PY
