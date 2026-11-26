/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef MSD_CRYPT_BACKEND_H
#define MSD_CRYPT_BACKEND_H

#include "unlock.h"

struct msd_crypt;
int msd_crypt_open(struct msd_crypt **, struct msd_backend *, const char *, const char *);
void msd_crypt_close(struct msd_crypt *);

#endif
