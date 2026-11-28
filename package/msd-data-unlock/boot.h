/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef MSD_BOOT_H
#define MSD_BOOT_H

#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <sys/stat.h>
#include <sys/types.h>

enum msd_data_state { MSD_DATA_EMPTY, MSD_DATA_PENDING, MSD_DATA_READY };

struct msd_boot_ops {
	void *ctx;
	int (*probe)(void *, char *, size_t);
	ssize_t (*read_at)(void *, void *, size_t, off_t);
	int (*scanning)(void *, uint64_t, uint64_t);
	int (*grow)(void *);
	int (*filesystem)(void *);
};

int msd_boot_classify(const struct msd_boot_ops *, enum msd_data_state *);
int msd_boot_control(int, const struct msd_boot_ops *);
bool msd_boot_same_device(const struct stat *, const struct stat *);
int msd_boot_mounted(FILE *, const char *);

#endif
