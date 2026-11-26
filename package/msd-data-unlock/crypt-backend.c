/* SPDX-License-Identifier: GPL-2.0-only */
#define _GNU_SOURCE
#include "crypt-backend.h"

#include <errno.h>
#include <fcntl.h>
#include <libcryptsetup.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

struct msd_crypt {
	struct crypt_device *cd;
	const char *path;
	const char *mapping;
	struct msd_secret *secret;
};

static const struct crypt_pbkdf_type pbkdf = {
	.type = CRYPT_KDF_ARGON2ID, .time_ms = 2000,
	.max_memory_kb = 65536, .parallel_threads = 1
};

static void quiet_log(int level, const char *text, void *ctx)
{
	(void)level;
	(void)text;
	(void)ctx;
}

static int inspect(void *ctx, bool ready)
{
	struct msd_crypt *c = ctx;
	int r = crypt_load(c->cd, CRYPT_LUKS2, NULL), mask = 0;
	if (r < 0)
		return r;
	const char *label = crypt_get_label(c->cd);
	if (!label || strcmp(label, ready ? "ready" : "pending"))
		return -EINVAL;
	int max = crypt_keyslot_max(CRYPT_LUKS2);
	if (max < 2)
		return -EINVAL;
	for (int i = 0; i < max; i++) {
		crypt_keyslot_info state = crypt_keyslot_status(c->cd, i);
		if (state == CRYPT_SLOT_INACTIVE)
			continue;
		if (i > 1 || (state != CRYPT_SLOT_ACTIVE && state != CRYPT_SLOT_ACTIVE_LAST))
			return -EINVAL;
		mask |= 1 << i;
	}
	return mask;
}

static int persist(struct msd_crypt *c)
{
	int fd = open(c->path, O_RDONLY | O_CLOEXEC);
	if (fd < 0)
		return -errno;
	int r = fsync(fd) < 0 ? -errno : 0;
	if (close(fd) < 0 && !r)
		r = -errno;
	return r;
}

static int operate(void *ctx, enum msd_op op, const char *first, const char *second)
{
	struct msd_crypt *c = ctx;
	int r;
	struct crypt_params_luks2 params = {
		.pbkdf = &pbkdf, .label = "pending", .sector_size = 512
	};
	switch (op) {
	case MSD_FORMAT:
		r = crypt_format(c->cd, CRYPT_LUKS2, "aes", "xts-plain64", NULL,
				 NULL, 64, &params);
		if (r >= 0)
			r = crypt_keyslot_add_by_volume_key(c->cd, 0, NULL, 0,
							first, strlen(first));
		break;
	case MSD_ADD_RECOVERY:
	case MSD_ADD_PIN:
		r = crypt_set_pbkdf_type(c->cd, &pbkdf);
		if (r >= 0)
			r = crypt_keyslot_add_by_passphrase(c->cd,
					op == MSD_ADD_PIN ? 0 : 1,
					first, strlen(first), second, strlen(second));
		break;
	case MSD_AUTH_PIN:
	case MSD_AUTH_RECOVERY:
	{
		size_t size = sizeof(c->secret->volume_key);
		r = crypt_volume_key_get(c->cd, op == MSD_AUTH_PIN ? 0 : 1,
			(char *)c->secret->volume_key, &size, first, strlen(first));
		if (r >= 0 && c->mapping) {
			int activated = crypt_activate_by_volume_key(c->cd, c->mapping,
				(char *)c->secret->volume_key, size, 0);
			if (activated < 0)
				r = activated == -EPERM ? -EACCES : activated;
		}
		explicit_bzero(c->secret->volume_key, sizeof(c->secret->volume_key));
		return r;
	}
	case MSD_DELETE_PIN:
		r = inspect(c, true);
		if (r != 3)
			return r < 0 ? r : -EINVAL;
		r = crypt_keyslot_destroy(c->cd, 0);
		break;
	case MSD_READY:
		r = inspect(c, false);
		if (r != 3)
			return r < 0 ? r : -EINVAL;
		r = crypt_set_label(c->cd, "ready", NULL);
		break;
	default:
		return -EINVAL;
	}
	if (r < 0)
		return r;
	int sync = persist(c);
	return sync < 0 ? sync : r;
}

int msd_crypt_open(struct msd_crypt **out, struct msd_backend *b,
		   const char *path, const char *mapping)
{
	struct msd_crypt *c = calloc(1, sizeof(*c));
	if (!c)
		return -ENOMEM;
	c->secret = msd_secret_alloc();
	if (!c->secret) {
		free(c);
		return -ENOMEM;
	}
	crypt_set_log_callback(NULL, quiet_log, NULL);
	int r = crypt_init(&c->cd, path);
	if (r < 0) {
		msd_secret_free(c->secret);
		free(c);
		return r;
	}
	crypt_set_log_callback(c->cd, quiet_log, NULL);
	c->path = path;
	c->mapping = mapping;
	*out = c;
	*b = (struct msd_backend){ .ctx = c, .inspect = inspect, .operate = operate };
	return 0;
}

void msd_crypt_close(struct msd_crypt *c)
{
	if (!c)
		return;
	crypt_free(c->cd);
	msd_secret_free(c->secret);
	free(c);
}
