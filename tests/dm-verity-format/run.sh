#!/bin/sh
set -eu

# verityfmt の自己検査: veritysetup (cryptsetup) との比較で
# hash tree と FEC parity が byte 一致することを確認する。
# docker/msd-dev tests/dm-verity-format/run.sh で実行する。

repo_root="$(CDPATH='' cd "$(dirname "$0")/../.." && pwd)"
tool_src="$repo_root/board/cardputerzero/tools/dm-verity/verityfmt.c"
test_root="$(mktemp -d)"

cleanup() {
	rm -rf "$test_root"
}
trap cleanup 0
trap 'exit 1' HUP INT TERM

fail() {
	printf 'not ok - %s\n' "$*" >&2
	exit 1
}

cc -O2 -Wall -Wextra -o "$test_root/verityfmt" "$tool_src" \
	|| fail "verityfmt.c does not compile"
printf 'ok - verityfmt builds\n'

"$test_root/verityfmt" --selftest >/dev/null \
	|| fail "verityfmt built-in test vectors"
printf 'ok - crc32c/sha256 test vectors\n'
python3 "$repo_root/tests/dm-verity-format/test-inputs.py" "$test_root/verityfmt"
python3 "$repo_root/tests/dm-verity-format/test-harness.py"
python3 "$repo_root/tests/dm-verity-format/test-stage-a.py"
python3 "$repo_root/tests/dm-verity-format/test-followup.py"
python3 "$repo_root/tests/dm-verity-format/test-remaining.py"

# 732 x 4096 bytes の乱数 image（block 境界で切り詰め）
data_blocks=732
bs=4096
data_bytes=$((data_blocks * bs))
head -c "$data_bytes" /dev/urandom > "$test_root/seed.bin"
salt="00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff"

# --- 1. hash tree: sha256, no-superblock ---
cp "$test_root/seed.bin" "$test_root/ref.img"
cp "$test_root/seed.bin" "$test_root/tool.img"

veritysetup format --no-superblock \
	--data-block-size="$bs" --hash-block-size="$bs" \
	--hash-offset="$data_bytes" --salt="$salt" --hash=sha256 \
	"$test_root/ref.img" "$test_root/ref.img" >"$test_root/ref.log" 2>&1 \
	|| fail "veritysetup format failed"

"$test_root/verityfmt" --hash sha256 --salt "$salt" --no-superblock \
	"$test_root/tool.img" >"$test_root/tool.log" 2>/dev/null \
	|| fail "verityfmt failed"

ref_root="$(awk -F: '/Root hash/ {gsub(/[ \t]/, "", $2); print $2}' "$test_root/ref.log")"
tool_root="$(awk -F= '/^root_hash=/ {print $2}' "$test_root/tool.log")"
[ "$ref_root" = "$tool_root" ] \
	|| fail "root hash mismatch: veritysetup=$ref_root verityfmt=$tool_root"
printf 'ok - sha256 root hash matches veritysetup\n'

cmp "$test_root/ref.img" "$test_root/tool.img" >/dev/null \
	|| fail "hash area bytes differ from veritysetup output"
printf 'ok - sha256 hash area is byte-identical to veritysetup\n'

# --- 2. hash tree + FEC: sha256 ---
cp "$test_root/seed.bin" "$test_root/ref-fec.img"
cp "$test_root/seed.bin" "$test_root/tool-fec.img"

hash_area_blocks=7	# sha256, 732 data blocks, 4096B blocks
fec_offset=$(( (data_blocks + hash_area_blocks) * bs ))
veritysetup format --no-superblock \
	--data-block-size="$bs" --hash-block-size="$bs" \
	--hash-offset="$data_bytes" --salt="$salt" --hash=sha256 \
	--fec-device="$test_root/ref-fec.img" --fec-roots=8 \
	--fec-offset="$fec_offset" \
	"$test_root/ref-fec.img" "$test_root/ref-fec.img" \
	>"$test_root/ref-fec.log" 2>&1 \
	|| fail "veritysetup format --fec-device failed"

"$test_root/verityfmt" --hash sha256 --salt "$salt" --fec-roots 8 \
	--no-superblock "$test_root/tool-fec.img" >"$test_root/tool-fec.log" 2>/dev/null \
	|| fail "verityfmt --fec-roots failed"

cmp "$test_root/ref-fec.img" "$test_root/tool-fec.img" >/dev/null \
	|| fail "hash+FEC bytes differ from veritysetup output"
printf 'ok - sha256 hash area + FEC parity are byte-identical to veritysetup\n'

# --- 3. veritysetup verify で readback 確認 ---
veritysetup verify --no-superblock \
	--data-block-size="$bs" --hash-block-size="$bs" \
	--data-blocks="$data_blocks" \
	--hash-offset="$data_bytes" --salt="$salt" --hash=sha256 \
	"$test_root/tool-fec.img" "$test_root/tool-fec.img" "$tool_root" \
	>"$test_root/verify.log" 2>&1 \
	|| fail "veritysetup verify failed"
printf 'ok - veritysetup verify accepts the generated image\n'

# --- 4. crc32c: superblock 付きで生成し superblock を読めるか ---
cp "$test_root/seed.bin" "$test_root/crc.img"
"$test_root/verityfmt" --hash crc32c --salt "$salt" --fec-roots 8 \
	--params-file "$test_root/crc.env" \
	"$test_root/crc.img" >"$test_root/crc.log" 2>/dev/null \
	|| fail "verityfmt crc32c failed"
grep -q '^root_hash=[0-9a-f]\{8\}$' "$test_root/crc.env" \
	|| fail "crc32c root hash missing or malformed"
printf 'ok - crc32c image generated (superblock present, veritysetup cannot parse it: expected)\n'

printf 'PASS - dm-verity-format\n'
