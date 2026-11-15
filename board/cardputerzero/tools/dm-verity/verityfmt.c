// SPDX-License-Identifier: GPL-2.0-or-later
/*
 * verityfmt -- append a dm-verity hash tree (and optional FEC parity) to a
 * data image, in the on-disk format used by the kernel's dm-verity target.
 *
 * The layout matches `veritysetup format` (format version 1, verity
 * superblock) and `veritysetup --fec-device` interleaved RS(255, N) parity,
 * while supporting hash algorithms that veritysetup's userspace crypto
 * backends reject (notably "crc32c", which the kernel accepts via the
 * crypto API).
 *
 * Layout written into the image file (all sizes in data/hash block units):
 *   [data area: data_blocks][superblock: 1 block][hash levels][FEC parity]
 * level order inside the hash area: top level (1 block) first, level 0
 * (per-data-block digests) last -- identical to the kernel's
 * hash_level_block[] order in drivers/md/dm-verity-target.c.
 *
 * FEC covers data blocks followed by the hash level blocks (the superblock
 * is NOT covered), identical to VERITY_FEC_process() in cryptsetup's
 * lib/verity/verity_fec.c and fec_read_bufs() in dm-verity-fec.c.
 *
 * Build:  cc -O2 -Wall -Wextra -o verityfmt verityfmt.c
 * Usage:  verityfmt [--hash crc32c|sha256] [--salt HEX|-|--salt-random]
 *                   [--fec-roots 2..24|0] [--no-superblock]
 *                   [--block-size N] [--params-file PATH] IMAGE
 *
 * Exit status: 0 on success, 1 on error.
 */

#include <errno.h>
#include <fcntl.h>
#include <getopt.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

/* ------------------------------------------------------------------ */
/* CRC-32C (Castagnoli), reflected, init/xorout 0xFFFFFFFF              */
/* ------------------------------------------------------------------ */

static uint32_t crc32c_table[256];

static void crc32c_init_table(void)
{
	uint32_t poly = 0x82F63B78U;
	uint32_t i, j, c;

	for (i = 0; i < 256; i++) {
		c = i;
		for (j = 0; j < 8; j++)
			c = (c & 1) ? (c >> 1) ^ poly : c >> 1;
		crc32c_table[i] = c;
	}
}

static uint32_t crc32c_buf(uint32_t crc, const uint8_t *buf, size_t len)
{
	size_t i;

	crc = ~crc;
	for (i = 0; i < len; i++)
		crc = crc32c_table[(crc ^ buf[i]) & 0xff] ^ (crc >> 8);
	return ~crc;
}

/* ------------------------------------------------------------------ */
/* SHA-256 (FIPS 180-4)                                                 */
/* ------------------------------------------------------------------ */

struct sha256_ctx {
	uint32_t h[8];
	uint64_t len;
	uint8_t buf[64];
	size_t buf_len;
};

static const uint32_t sha256_k[64] = {
	0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
	0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
	0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
	0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
	0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
	0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
	0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
	0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
	0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
	0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
	0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
	0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
	0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
	0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
	0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
	0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
};

#define SHA256_ROTR(x, n) (((x) >> (n)) | ((x) << (32 - (n))))

static void sha256_block(struct sha256_ctx *c, const uint8_t *p)
{
	uint32_t w[64], a, b, d, e, f, g, h, t1, t2, cc;
	int i;

	for (i = 0; i < 16; i++)
		w[i] = (uint32_t)p[i * 4] << 24 | (uint32_t)p[i * 4 + 1] << 16 |
		       (uint32_t)p[i * 4 + 2] << 8 | (uint32_t)p[i * 4 + 3];
	for (i = 16; i < 64; i++) {
		uint32_t s0 = SHA256_ROTR(w[i - 15], 7) ^ SHA256_ROTR(w[i - 15], 18) ^ (w[i - 15] >> 3);
		uint32_t s1 = SHA256_ROTR(w[i - 2], 17) ^ SHA256_ROTR(w[i - 2], 19) ^ (w[i - 2] >> 10);
		w[i] = w[i - 16] + s0 + w[i - 7] + s1;
	}
	a = c->h[0]; b = c->h[1]; cc = c->h[2]; d = c->h[3];
	e = c->h[4]; f = c->h[5]; g = c->h[6]; h = c->h[7];
	for (i = 0; i < 64; i++) {
		uint32_t S1 = SHA256_ROTR(e, 6) ^ SHA256_ROTR(e, 11) ^ SHA256_ROTR(e, 25);
		uint32_t ch = (e & f) ^ (~e & g);
		t1 = h + S1 + ch + sha256_k[i] + w[i];
		uint32_t S0 = SHA256_ROTR(a, 2) ^ SHA256_ROTR(a, 13) ^ SHA256_ROTR(a, 22);
		uint32_t maj = (a & b) ^ (a & cc) ^ (b & cc);
		t2 = S0 + maj;
		h = g; g = f; f = e; e = d + t1;
		d = cc; cc = b; b = a; a = t1 + t2;
	}
	c->h[0] += a; c->h[1] += b; c->h[2] += cc; c->h[3] += d;
	c->h[4] += e; c->h[5] += f; c->h[6] += g; c->h[7] += h;
}

static void sha256_init(struct sha256_ctx *c)
{
	static const uint32_t iv[8] = {
		0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
		0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
	};
	memcpy(c->h, iv, sizeof(iv));
	c->len = 0;
	c->buf_len = 0;
}

static void sha256_update(struct sha256_ctx *c, const uint8_t *p, size_t len)
{
	c->len += len;
	while (len) {
		size_t n = 64 - c->buf_len;
		if (n > len)
			n = len;
		memcpy(c->buf + c->buf_len, p, n);
		c->buf_len += n;
		p += n;
		len -= n;
		if (c->buf_len == 64) {
			sha256_block(c, c->buf);
			c->buf_len = 0;
		}
	}
}

static void sha256_final(struct sha256_ctx *c, uint8_t out[32])
{
	uint64_t bits = c->len * 8;
	uint8_t pad = 0x80;
	uint8_t lenbuf[8];
	int i;

	sha256_update(c, &pad, 1);
	pad = 0;
	while (c->buf_len != 56)
		sha256_update(c, &pad, 1);
	for (i = 0; i < 8; i++)
		lenbuf[i] = (uint8_t)(bits >> (56 - i * 8));
	sha256_update(c, lenbuf, 8);
	for (i = 0; i < 8; i++) {
		out[i * 4] = (uint8_t)(c->h[i] >> 24);
		out[i * 4 + 1] = (uint8_t)(c->h[i] >> 16);
		out[i * 4 + 2] = (uint8_t)(c->h[i] >> 8);
		out[i * 4 + 3] = (uint8_t)c->h[i];
	}
}

/* ------------------------------------------------------------------ */
/* Generic hash interface (format version 1: salt prepended)           */
/* ------------------------------------------------------------------ */

struct hash_alg {
	const char *name;
	size_t digest_size;
};

static const struct hash_alg HASH_CRC32C = { "crc32c", 4 };
static const struct hash_alg HASH_SHA256 = { "sha256", 32 };

/* digest = H(salt || data) -- dm-verity hash format version 1 */
static void verity_hash(const struct hash_alg *alg,
			const uint8_t *salt, size_t salt_size,
			const uint8_t *data, size_t data_size,
			uint8_t *digest)
{
	if (alg->digest_size == 4) {
		uint32_t crc;

		crc = crc32c_buf(0, salt, salt_size);
		crc = crc32c_buf(crc, data, data_size);
		digest[0] = (uint8_t)crc;
		digest[1] = (uint8_t)(crc >> 8);
		digest[2] = (uint8_t)(crc >> 16);
		digest[3] = (uint8_t)(crc >> 24);
	} else {
		struct sha256_ctx c;

		sha256_init(&c);
		sha256_update(&c, salt, salt_size);
		sha256_update(&c, data, data_size);
		sha256_final(&c, digest);
	}
}

/* ------------------------------------------------------------------ */
/* Reed-Solomon encoder (RS(255, 255-roots) over GF(2^8), poly 0x11d,   */
/* fcr=0, prim=1 -- identical parameters to cryptsetup verity_fec.c     */
/* and the kernel's fec_init()/init_rs_gfp). Ported from Phil Karn's    */
/* libfec-derived rs_encode_char.c (LGPL-2.1-or-later).                 */
/* ------------------------------------------------------------------ */

struct rs_codec {
	uint8_t alpha_to[256];
	uint8_t index_of[256];
	uint8_t genpoly[64];
	int nn;			/* 255 */
	int nroots;
};

static int mod255(const struct rs_codec *rs, int x)
{
	while (x >= rs->nn) {
		x -= rs->nn;
		x = (x >> 8) + (x & rs->nn);
	}
	return x;
}

static int rs_init(struct rs_codec *rs, int gfpoly, int fcr, int prim,
		   int nroots)
{
	int i, j, sr, root;

	if (nroots <= 0 || nroots >= 256)
		return -1;
	rs->nn = 255;
	rs->nroots = nroots;
	memset(rs->index_of, 0, sizeof(rs->index_of));
	rs->index_of[0] = 255;	/* A0 */
	rs->alpha_to[255] = 0;
	sr = 1;
	for (i = 0; i < rs->nn; i++) {
		rs->index_of[sr] = i;
		rs->alpha_to[i] = sr;
		sr <<= 1;
		if (sr & 256)
			sr ^= gfpoly;
		sr &= rs->nn;
	}
	if (sr != 1)
		return -1;

	rs->genpoly[0] = 1;
	for (i = 0, root = fcr * prim; i < nroots; i++, root += prim) {
		rs->genpoly[i + 1] = 1;
		for (j = i; j > 0; j--) {
			if (rs->genpoly[j] != 0)
				rs->genpoly[j] = rs->genpoly[j - 1] ^
					rs->alpha_to[mod255(rs, rs->index_of[rs->genpoly[j]] + root)];
			else
				rs->genpoly[j] = rs->genpoly[j - 1];
		}
		rs->genpoly[0] = rs->alpha_to[mod255(rs, rs->index_of[rs->genpoly[0]] + root)];
	}
	for (i = 0; i <= nroots; i++)
		rs->genpoly[i] = rs->index_of[rs->genpoly[i]];
	return 0;
}

/* encode rsn data bytes, append nroots parity bytes */
static void rs_encode(const struct rs_codec *rs, const uint8_t *data,
		      uint8_t *parity)
{
	int i, j;
	uint8_t feedback;
	int rsn = rs->nn - rs->nroots;

	memset(parity, 0, (size_t)rs->nroots);
	for (i = 0; i < rsn; i++) {
		feedback = rs->index_of[data[i] ^ parity[0]];
		if (feedback != 255) {
			for (j = 1; j < rs->nroots; j++)
				parity[j] ^= rs->alpha_to[mod255(rs, feedback + rs->genpoly[rs->nroots - j])];
		}
		memmove(&parity[0], &parity[1], (size_t)(rs->nroots - 1));
		if (feedback != 255)
			parity[rs->nroots - 1] = rs->alpha_to[mod255(rs, feedback + rs->genpoly[0])];
		else
			parity[rs->nroots - 1] = 0;
	}
}

/* ------------------------------------------------------------------ */
/* dm-verity superblock (struct verity_sb, 512 bytes)                   */
/* ------------------------------------------------------------------ */

struct verity_sb {
	uint8_t signature[8];	/* "verity\0\0" */
	uint32_t version;	/* 1 */
	uint32_t hash_type;	/* 1 = normal */
	uint8_t uuid[16];
	uint8_t algorithm[32];
	uint32_t data_block_size;
	uint32_t hash_block_size;
	uint64_t data_blocks;
	uint16_t salt_size;
	uint8_t pad1[6];
	uint8_t salt[256];
	uint8_t pad2[168];
} __attribute__((packed));

/* ------------------------------------------------------------------ */
/* helpers                                                              */
/* ------------------------------------------------------------------ */

static unsigned int floor_log2(uint64_t u)
{
	unsigned int i = 0;

	while (u >> (i + 1))
		i++;
	return i;
}

static unsigned int ceil_log2(uint64_t u)
{
	unsigned int i = 0;

	while ((1ULL << i) < u)
		i++;
	return i;
}

static int pread_full(int fd, void *buf, size_t count, off_t off)
{
	while (count) {
		ssize_t r = pread(fd, buf, count, off);

		if (r < 0 && errno == EINTR)
			continue;
		if (r == 0)
			errno = EIO;
		if (r <= 0)
			return -1;
		buf = (uint8_t *)buf + r;
		count -= (size_t)r;
		off += r;
	}
	return 0;
}

static int pwrite_full(int fd, const void *buf, size_t count, off_t off)
{
	while (count) {
		ssize_t r = pwrite(fd, buf, count, off);

		if (r < 0 && errno == EINTR)
			continue;
		if (r == 0)
			errno = EIO;
		if (r <= 0)
			return -1;
		buf = (const uint8_t *)buf + r;
		count -= (size_t)r;
		off += r;
	}
	return 0;
}

static int hex_digit(unsigned char c)
{
	if (c >= '0' && c <= '9')
		return c - '0';
	if (c >= 'a' && c <= 'f')
		return c - 'a' + 10;
	if (c >= 'A' && c <= 'F')
		return c - 'A' + 10;
	return -1;
}

static int hex_decode(const char *hex, uint8_t *out, size_t out_size)
{
	size_t len = strlen(hex), i;

	if (!len || len % 2 || len / 2 > out_size)
		return -1;
	for (i = 0; i < len / 2; i++) {
		int hi = hex_digit((unsigned char)hex[i * 2]);
		int lo = hex_digit((unsigned char)hex[i * 2 + 1]);

		if (hi < 0 || lo < 0)
			return -1;
		out[i] = (uint8_t)((hi << 4) | lo);
	}
	return (int)(len / 2);
}

static void hex_encode(const uint8_t *in, size_t len, char *out)
{
	size_t i;

	for (i = 0; i < len; i++)
		sprintf(out + i * 2, "%02x", in[i]);
	out[len * 2] = '\0';
}

static void die(const char *msg)
{
	fprintf(stderr, "verityfmt: %s: %s\n", msg, strerror(errno));
	exit(1);
}

static uint64_t parse_number(const char *text, uint64_t maximum)
{
	char *end;
	unsigned long long value;

	errno = 0;
	if (*text < '0' || *text > '9') {
		fprintf(stderr, "verityfmt: invalid number '%s'\n", text);
		exit(2);
	}
	value = strtoull(text, &end, 0);
	if (errno == ERANGE || *end || value > maximum) {
		fprintf(stderr, "verityfmt: invalid number '%s'\n", text);
		exit(2);
	}
	return (uint64_t)value;
}

static void random_bytes(uint8_t *out, size_t size)
{
	int fd = open("/dev/urandom", O_RDONLY);

	if (fd < 0)
		die("open random source");
	while (size) {
		ssize_t n = read(fd, out, size);

		if (n < 0 && errno == EINTR)
			continue;
		if (n == 0)
			errno = EIO;
		if (n <= 0)
			die("read random source");
		out += n;
		size -= (size_t)n;
	}
	if (close(fd) < 0)
		die("close random source");
}

/* ------------------------------------------------------------------ */

int main(int argc, char **argv)
{
	static const struct option opts[] = {
		{ "hash", required_argument, NULL, 'h' },
		{ "salt", required_argument, NULL, 's' },
		{ "salt-random", required_argument, NULL, 'r' },
		{ "fec-roots", required_argument, NULL, 'f' },
		{ "no-superblock", no_argument, NULL, 'n' },
		{ "block-size", required_argument, NULL, 'b' },
		{ "params-file", required_argument, NULL, 'p' },
		{ "selftest", no_argument, NULL, 't' },
		{ NULL, 0, NULL, 0 },
	};
	const struct hash_alg *alg = &HASH_CRC32C;
	uint8_t salt[256];
	size_t salt_size = 32;
	int salt_given = 0;
	int fec_roots = 0;
	int use_superblock = 1;
	uint64_t bs = 4096;
	const char *params_file = NULL;
	const char *image_path = NULL;
	int c;

	while ((c = getopt_long(argc, argv, "", opts, NULL)) != -1) {
		switch (c) {
		case 'h':
			if (!strcmp(optarg, "crc32c"))
				alg = &HASH_CRC32C;
			else if (!strcmp(optarg, "sha256"))
				alg = &HASH_SHA256;
			else {
				fprintf(stderr, "verityfmt: unsupported hash '%s' (use crc32c or sha256)\n", optarg);
				return 2;
			}
			break;
		case 's':
			if (!strcmp(optarg, "-")) {
				salt_size = 0;
			} else {
				int n = hex_decode(optarg, salt, sizeof(salt));

				if (n < 0) {
					fprintf(stderr, "verityfmt: invalid salt hex\n");
					return 2;
				}
				salt_size = (size_t)n;
			}
			salt_given = 1;
			break;
		case 'r':
			salt_size = (size_t)parse_number(optarg, sizeof(salt));
			if (!salt_size || salt_size > 256) {
				fprintf(stderr, "verityfmt: invalid random salt size\n");
				return 2;
			}
			salt_given = 0;
			break;
		case 'f':
			fec_roots = (int)parse_number(optarg, 24);
			if (fec_roots && (fec_roots < 2 || fec_roots > 24)) {
				fprintf(stderr, "verityfmt: fec-roots must be 0 or 2..24\n");
				return 2;
			}
			break;
		case 'n':
			use_superblock = 0;
			break;
		case 'b':
			bs = parse_number(optarg, 512 * 1024);
			break;
		case 'p':
			params_file = optarg;
			break;
		case 't':
			{
				uint8_t d[32];
				char hex[65];

				crc32c_init_table();
				uint32_t crc = crc32c_buf(0, (const uint8_t *)"123456789", 9);
				printf("crc32c(\"123456789\") = %08x (expect e3069283)\n", crc);
				verity_hash(&HASH_SHA256, NULL, 0,
					    (const uint8_t *)"abc", 3, d);
				hex_encode(d, 32, hex);
				printf("sha256(\"abc\") = %s\n(expect ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad)\n", hex);
				return crc == 0xe3069283 && !strcmp(hex,
					"ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad") ? 0 : 1;
			}
		default:
			fprintf(stderr, "usage: verityfmt [--hash crc32c|sha256] [--salt HEX|-] [--salt-random N] "
				"[--fec-roots 0|2..24] [--no-superblock] [--block-size N] "
				"[--params-file PATH] IMAGE\n");
			return 2;
		}
	}
	if (optind + 1 != argc) {
		fprintf(stderr, "verityfmt: expected one IMAGE\n");
		return 2;
	}
	image_path = argv[optind];

	if (!bs || (bs & (bs - 1)) || bs < 512 || bs > 512 * 1024) {
		fprintf(stderr, "verityfmt: block size must be a power of two in [512, 524288]\n");
		return 2;
	}

	crc32c_init_table();

	if (!salt_given)
		random_bytes(salt, salt_size);

	int fd = open(image_path, O_RDWR);
	if (fd < 0)
		die(image_path);

	struct stat st;
	if (fstat(fd, &st) < 0)
		die("fstat");
	if (!S_ISREG(st.st_mode) || st.st_size < 0 ||
	    (uint64_t)st.st_size > (uint64_t)INT64_MAX / 2) {
		fprintf(stderr, "verityfmt: unsupported image type or size\n");
		return 1;
	}
	uint64_t data_bytes = ((uint64_t)st.st_size + bs - 1) / bs * bs;
	uint64_t data_blocks = data_bytes / bs;
	if (data_blocks < 2) {
		fprintf(stderr, "verityfmt: input image too small: need at least 2 data blocks\n");
		return 1;
	}
	if (data_bytes != (uint64_t)st.st_size && ftruncate(fd, (off_t)data_bytes) < 0)
		die("ftruncate pad");

	/* hash tree geometry (same as kernel verity_ctr) */
	size_t ds = alg->digest_size;
	size_t ds_full = 1ULL << ceil_log2(ds);
	unsigned int hpbb = floor_log2(bs / ds);	/* hash_per_block_bits */
	uint64_t sb_blocks = use_superblock ? 1 : 0;
	uint64_t hash_offset_blocks = data_blocks;
	uint64_t hash_start_block = hash_offset_blocks + sb_blocks;

	int levels = 0;
	while (hpbb * (unsigned int)levels < 64 &&
	       (data_blocks - 1) >> (hpbb * (unsigned int)levels))
		levels++;
	if (levels > 63) {
		fprintf(stderr, "verityfmt: too many tree levels\n");
		return 1;
	}
	uint64_t level_blocks[64], level_size[64];
	uint64_t pos = hash_start_block;
	int i;

	for (i = levels - 1; i >= 0; i--) {
		level_blocks[i] = pos;
		level_size[i] = (data_blocks + (1ULL << ((i + 1) * hpbb)) - 1) >>
				((i + 1) * hpbb);
		pos += level_size[i];
	}
	uint64_t hash_area_blocks = pos - hash_start_block;
	uint64_t fec_area_offset = pos * bs;

	fprintf(stderr, "verityfmt: data_blocks=%llu levels=%d hash_area_blocks=%llu "
		"(block=%llu, superblock=%s)\n",
		(unsigned long long)data_blocks, levels,
		(unsigned long long)hash_area_blocks,
		(unsigned long long)bs, use_superblock ? "yes" : "no");

	/* superblock */
	if (use_superblock) {
		struct verity_sb sb;

		memset(&sb, 0, sizeof(sb));
		memcpy(sb.signature, "verity\0\0", 8);
		sb.version = 1;
		sb.hash_type = 1;
		random_bytes(sb.uuid, sizeof(sb.uuid));
		strncpy((char *)sb.algorithm, alg->name, sizeof(sb.algorithm) - 1);
		sb.data_block_size = (uint32_t)bs;
		sb.hash_block_size = (uint32_t)bs;
		sb.data_blocks = data_blocks;
		sb.salt_size = (uint16_t)salt_size;
		memcpy(sb.salt, salt, salt_size);
		_Static_assert(sizeof(sb) == 512, "verity_sb size");
		if (pwrite_full(fd, &sb, sizeof(sb), (off_t)(hash_offset_blocks * bs)) < 0)
			die("write superblock");
	}

	/* hash tree: level 0 = data digests; level i = digests of level i-1 blocks */
	uint8_t *block = malloc(bs);
	uint8_t *digest = malloc(ds);
	uint8_t *prev = NULL;	/* previous level image (level_size[i-1]*bs) */
	uint8_t *top_block = calloc(1, bs);
	uint8_t root_hash[64];
	size_t lv;

	if (!block || !digest || !top_block) {
		fprintf(stderr, "verityfmt: out of memory\n");
		return 1;
	}

	for (lv = 0; lv < (size_t)levels; lv++) {
		uint64_t in_blocks = lv ? level_size[lv - 1] : data_blocks;
		uint64_t out_blocks = level_size[lv];
		uint8_t *out = calloc((size_t)out_blocks, bs);

		if (!out) {
			fprintf(stderr, "verityfmt: out of memory (level %zu)\n", lv);
			return 1;
		}

		uint64_t e;
		for (e = 0; e < in_blocks; e++) {
			if (!lv) {
				if (pread_full(fd, block, bs, (off_t)(e * bs)) < 0)
					die("read data");
			} else {
				memcpy(block, prev + e * bs, bs);
			}
			verity_hash(alg, salt, salt_size, block, bs, digest);
			memcpy(out + e * ds_full, digest, ds);
		}
		if (lv == (size_t)levels - 1) {
			/* root hash = H(salt || top-level block) */
			memcpy(top_block, out, bs);
			verity_hash(alg, salt, salt_size, top_block, bs, root_hash);
		}
		if (pwrite_full(fd, out, (size_t)out_blocks * bs,
				(off_t)(level_blocks[lv] * bs)) < 0)
			die("write hash level");
		free(prev);
		prev = out;
	}
	free(prev);

	/* FEC: covers [data blocks] + [hash level blocks] (superblock excluded) */
	uint64_t fec_blocks = 0, fec_bytes = 0;
	if (fec_roots) {
		int rsn = 255 - fec_roots;
		uint64_t covered = data_blocks + hash_area_blocks;
		uint64_t rounds = (covered + rsn - 1) / rsn;
		struct rs_codec rs;
		uint8_t *bufs, *par;

		if (rs_init(&rs, 0x11d, 0, 1, fec_roots))
			die("rs_init");
		bufs = malloc((size_t)rsn * bs);
		par = malloc((size_t)fec_roots * bs);
		if (!bufs || !par)
			die("malloc fec");

		fec_blocks = covered;
		fec_bytes = rounds * bs * (uint64_t)fec_roots;

		uint64_t n;
		for (n = 0; n < rounds; n++) {
			uint64_t i2;
			for (i2 = 0; i2 < (uint64_t)rsn; i2++) {
				uint64_t blk = i2 * rounds + n;
				uint8_t *dst = bufs + i2 * bs;

				if (blk >= covered) {
					memset(dst, 0, bs);
				} else if (blk < data_blocks) {
					if (pread_full(fd, dst, bs, (off_t)(blk * bs)) < 0)
						die("fec read data");
				} else {
					uint64_t hb = hash_start_block + blk - data_blocks;
					if (pread_full(fd, dst, bs, (off_t)(hb * bs)) < 0)
						die("fec read hash");
				}
			}
			uint64_t b;
			for (b = 0; b < bs; b++) {
				uint8_t msg[255];
				for (i2 = 0; i2 < (uint64_t)rsn; i2++)
					msg[i2] = bufs[i2 * bs + b];
				rs_encode(&rs, msg, par + b * (size_t)fec_roots);
			}
			if (pwrite_full(fd, par, (size_t)fec_roots * bs,
					(off_t)(fec_area_offset + n * (uint64_t)fec_roots * bs)) < 0)
				die("write fec");
		}
		free(bufs);
		free(par);
	}
	if (fsync(fd) < 0)
		die("sync image");
	if (close(fd) < 0)
		die("close image");

	/* report */
	char root_hex[129], salt_hex[513];
	hex_encode(root_hash, ds, root_hex);
	hex_encode(salt, salt_size, salt_hex);
	printf("data_bytes=%llu\n", (unsigned long long)data_bytes);
	printf("data_blocks=%llu\n", (unsigned long long)data_blocks);
	printf("hash_offset=%llu\n", (unsigned long long)(hash_offset_blocks * bs));
	printf("hash_start_block=%llu\n", (unsigned long long)hash_start_block);
	printf("hash_area_blocks=%llu\n", (unsigned long long)hash_area_blocks);
	printf("root_hash=%s\n", root_hex);
	printf("salt=%s\n", salt_size ? salt_hex : "-");
	printf("hash_alg=%s\n", alg->name);
	if (fec_roots) {
		printf("fec_area_offset=%llu\n", (unsigned long long)fec_area_offset);
		printf("fec_blocks=%llu\n", (unsigned long long)fec_blocks);
		printf("fec_roots=%d\n", fec_roots);
		printf("fec_bytes=%llu\n", (unsigned long long)fec_bytes);
	}
	{
		printf("dmcreate_nofec=0 %llu verity 1 DEV DEV %llu %llu %llu %llu %s %s %s 1 panic_on_corruption\n",
		       (unsigned long long)(data_bytes / 512),
		       (unsigned long long)bs, (unsigned long long)bs,
		       (unsigned long long)data_blocks,
		       (unsigned long long)hash_start_block,
		       alg->name, root_hex, salt_size ? salt_hex : "-");
		if (fec_roots) {
			printf("dmcreate=0 %llu verity 1 DEV DEV %llu %llu %llu %llu %s %s %s 9 "
			       "use_fec_from_device DEV fec_roots %d fec_blocks %llu fec_start %llu panic_on_corruption\n",
			       (unsigned long long)(data_bytes / 512),
			       (unsigned long long)bs, (unsigned long long)bs,
			       (unsigned long long)data_blocks,
			       (unsigned long long)hash_start_block,
			       alg->name, root_hex, salt_size ? salt_hex : "-",
			       fec_roots, (unsigned long long)fec_blocks,
			       /* fec_start is in hash_block_size units
				* (kernel shifts it by block_bits - SECTOR_SHIFT) */
			       (unsigned long long)(fec_area_offset / bs));
		}
	}

	if (params_file) {
		FILE *f = fopen(params_file, "w");
		if (!f)
			die("params file");
		fprintf(f, "data_bytes=%llu\ndata_blocks=%llu\nhash_offset=%llu\n"
			   "hash_start_block=%llu\nhash_area_blocks=%llu\n"
			   "root_hash=%s\nsalt=%s\nhash_alg=%s\n",
			(unsigned long long)data_bytes,
			(unsigned long long)data_blocks,
			(unsigned long long)(hash_offset_blocks * bs),
			(unsigned long long)hash_start_block,
			(unsigned long long)hash_area_blocks,
			root_hex, salt_size ? salt_hex : "-", alg->name);
		if (fec_roots)
			fprintf(f, "fec_area_offset=%llu\nfec_blocks=%llu\nfec_roots=%d\nfec_bytes=%llu\n",
				(unsigned long long)fec_area_offset,
				(unsigned long long)fec_blocks, fec_roots,
				(unsigned long long)fec_bytes);
		if (ferror(f) || fflush(f) == EOF)
			die("write params file");
		if (fsync(fileno(f)) < 0)
			die("sync params file");
		if (fclose(f) == EOF)
			die("close params file");
	}
	if (fflush(stdout) == EOF)
		die("write report");
	return 0;
}
