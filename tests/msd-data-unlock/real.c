/* SPDX-License-Identifier: GPL-2.0-only */
#define _GNU_SOURCE
#include "crypt-backend.h"

#include <assert.h>
#include <errno.h>
#include <libcryptsetup.h>
#include <stdio.h>
#include <string.h>

int main(int argc, char **argv)
{
	assert(argc == 2);
	const char *pin = "  original PIN 93!  ";
	const char *new_pin = "replacement PIN 94!";
	const char *key = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
	struct msd_crypt *c;
	struct msd_backend b;
	assert(msd_crypt_open(&c, &b, argv[1], NULL) == 0);
	assert(b.inspect(b.ctx, true) < 0);
	assert(b.operate(b.ctx, MSD_FORMAT, pin, NULL) == 0);
	assert(b.inspect(b.ctx, false) == 1);
	assert(b.operate(b.ctx, MSD_ADD_RECOVERY, pin, key) == 1);
	assert(b.inspect(b.ctx, false) == 3);
	assert(b.operate(b.ctx, MSD_AUTH_PIN, pin, NULL) == 0);
	assert(b.operate(b.ctx, MSD_AUTH_RECOVERY, key, NULL) == 1);
	assert(b.operate(b.ctx, MSD_AUTH_PIN, "wrong PIN", NULL) == -EPERM);
	assert(b.operate(b.ctx, MSD_READY, NULL, NULL) == 0);
	msd_crypt_close(c);
	assert(msd_crypt_open(&c, &b, argv[1], NULL) == 0);
	assert(b.inspect(b.ctx, true) == 3);
	assert(b.operate(b.ctx, MSD_DELETE_PIN, NULL, NULL) == 0);
	assert(b.inspect(b.ctx, true) == 2);
	assert(b.operate(b.ctx, MSD_DELETE_PIN, NULL, NULL) < 0);
	assert(b.operate(b.ctx, MSD_AUTH_RECOVERY, key, NULL) == 1);
	assert(b.operate(b.ctx, MSD_ADD_PIN, key, new_pin) == 0);
	assert(b.inspect(b.ctx, true) == 3);
	assert(b.operate(b.ctx, MSD_AUTH_PIN, new_pin, NULL) == 0);
	assert(b.operate(b.ctx, MSD_AUTH_PIN, pin, NULL) == -EPERM);
	msd_crypt_close(c);
	struct crypt_device *cd;
	assert(crypt_init(&cd, argv[1]) == 0);
	assert(crypt_load(cd, CRYPT_LUKS2, NULL) == 0);
	assert(!strcmp(crypt_get_cipher(cd), "aes"));
	assert(!strcmp(crypt_get_cipher_mode(cd), "xts-plain64"));
	assert(crypt_get_volume_key_size(cd) == 64);
	assert(!strcmp(crypt_get_label(cd), "ready"));
	for (int i = 0; i < 2; i++) {
		struct crypt_pbkdf_type p;
		assert(crypt_keyslot_get_pbkdf(cd, i, &p) == 0);
		assert(!strcmp(p.type, CRYPT_KDF_ARGON2ID));
		assert(p.max_memory_kb <= 65536 && p.parallel_threads == 1);
	}
	assert(crypt_keyslot_add_by_passphrase(cd, 2, key, strlen(key), "extra", 5) == 2);
	assert(msd_crypt_open(&c, &b, argv[1], NULL) == 0);
	assert(b.inspect(b.ctx, true) == -EINVAL);
	msd_crypt_close(c);
	assert(crypt_keyslot_destroy(cd, 2) == 0);
	assert(crypt_set_label(cd, "unknown", NULL) == 0);
	assert(msd_crypt_open(&c, &b, argv[1], NULL) == 0);
	assert(b.inspect(b.ctx, true) == -EINVAL);
	msd_crypt_close(c);
	crypt_free(cd);
	puts("ok - real libcryptsetup: pending/ready, fixed slots, passphrase validation, reset, PBKDF, unexpected slot/label");
	return 0;
}
