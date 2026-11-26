/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef MSD_TERMINAL_H
#define MSD_TERMINAL_H

#include "unlock.h"
#include <pthread.h>
#include <signal.h>
#include <termios.h>

struct msd_terminal {
	int fd, control;
	struct termios saved;
	bool active, skip_lf, ticking, stop;
	pthread_t thread;
	pthread_mutex_t mutex;
	pthread_cond_t condition;
	const char *phase;
	int output_error;
	struct msd_secret *secret;
};
extern volatile sig_atomic_t msd_interrupted;
int msd_terminal_open(struct msd_terminal *, int, int, struct msd_secret *, struct msd_ui *);
int msd_terminal_close(struct msd_terminal *);
int msd_security_init(void);

#endif
