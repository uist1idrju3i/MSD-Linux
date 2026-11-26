/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef MSD_UNLOCK_H
#define MSD_UNLOCK_H

#include <stdbool.h>
#include <stddef.h>

#define MSD_PIN_MAX 64
#define MSD_LINE_MAX 96
#define MSD_RECOVERY_LEN 32
#define MSD_FORGOT "Forgot PIN? Press Enter on an empty line to use the recovery key.\n"

enum msd_op {
	MSD_FORMAT, MSD_ADD_RECOVERY, MSD_AUTH_PIN, MSD_AUTH_RECOVERY,
	MSD_DELETE_PIN, MSD_ADD_PIN, MSD_READY
};
enum msd_checkpoint { MSD_GROW, MSD_FILESYSTEM };
struct msd_backend {
	void *ctx;
	int (*inspect)(void *, bool ready);
	int (*operate)(void *, enum msd_op, const char *, const char *);
};
struct msd_ui {
	void *ctx;
	int (*message)(void *, const char *);
	int (*line)(void *, char *, size_t);
	int (*recovery)(void *, const char *);
	int (*random)(void *, unsigned char *, size_t);
	int (*checkpoint)(void *, enum msd_checkpoint);
	int (*progress)(void *, const char *, bool);
};
struct msd_secret {
	char pin[MSD_PIN_MAX + 1];
	char again[MSD_PIN_MAX + 1];
	char recovery[MSD_RECOVERY_LEN + 1];
	char line[MSD_LINE_MAX];
	unsigned char random[20];
	unsigned char volume_key[64];
	unsigned char key;
	unsigned failures;
};

bool msd_pin_valid(const char *);
bool msd_pin_weak(const char *);
void msd_base32(const unsigned char[20], char[33]);
int msd_recovery_parse(const char *, char[33]);
int msd_prepare(struct msd_backend *, struct msd_ui *, struct msd_secret *);
int msd_unlock(struct msd_backend *, struct msd_ui *, struct msd_secret *);
struct msd_secret *msd_secret_alloc(void);
void msd_secret_free(struct msd_secret *);

#endif
