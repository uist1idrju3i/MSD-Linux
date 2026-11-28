/* SPDX-License-Identifier: GPL-2.0-only */
#define _GNU_SOURCE
#include "terminal.h"

#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/prctl.h>
#include <sys/resource.h>
#include <time.h>

struct fake { int mask; bool ready, bad_pin, delete_failure, echo_pin, repeat_key; struct msd_ui *ui; };
static int inspect(void *ctx, bool ready)
{
	struct fake *f = ctx;
	return ready == f->ready ? f->mask : -EINVAL;
}
static int operate(void *ctx, enum msd_op op, const char *a, const char *b)
{
	struct fake *f = ctx;
	(void)a; (void)b;
	switch (op) {
	case MSD_FORMAT: f->mask = 1; f->ready = false; break;
	case MSD_ADD_RECOVERY:
		f->mask = 3;
		if (f->repeat_key) assert(f->ui->recovery(f->ui->ctx, b) == 0);
		break;
	case MSD_DELETE_PIN:
		if (f->delete_failure) return -EIO;
		f->mask = 2; break;
	case MSD_AUTH_PIN:
		if (f->echo_pin) {
			f->echo_pin = false;
			assert(f->ui->message(f->ui->ctx, a) == 0);
		}
		if (f->bad_pin) return -EPERM;
		break;
	case MSD_ADD_PIN: f->mask = 3; break;
	case MSD_READY: f->ready = true; break;
	default: break;
	}
	return op == MSD_AUTH_RECOVERY || op == MSD_ADD_RECOVERY ? 1 : 0;
}
static int deactivate(void *ctx)
{
	(void)ctx;
	return 0;
}

int main(int argc, char **argv)
{
	assert(argc >= 3);
	int fd = atoi(argv[2]);
	int control = argc > 3 ? atoi(argv[3]) : -1;
	assert(msd_security_init() == 0);
	assert(!getenv("MSD_TEST_SECRET"));
	struct rlimit limit;
	assert(getrlimit(RLIMIT_CORE, &limit) == 0 && !limit.rlim_cur && !limit.rlim_max);
	assert(prctl(PR_GET_DUMPABLE) == 0);
	struct msd_secret *s = msd_secret_alloc();
	assert(s);
	struct msd_terminal t;
	struct msd_ui u;
	assert(fcntl(fd, F_SETFL, O_NONBLOCK) == 0);
	assert(msd_terminal_open(&t, fd, control, s, &u) == 0);
	puts("READY"); fflush(stdout);
	int r;
	if (!strcmp(argv[1], "read")) {
		r = u.line(u.ctx, s->pin, sizeof(s->pin));
		printf("line-result=%d length=%zu\n", r, strlen(s->pin));
	} else if (!strcmp(argv[1], "display")) {
		r = u.random(u.ctx, s->random, sizeof(s->random));
		if (!r) {
			msd_base32(s->random, s->recovery);
			r = u.recovery(u.ctx, s->recovery);
		}
	} else if (!strcmp(argv[1], "progress")) {
		r = u.progress(u.ctx, "Test operation", true);
		assert(r == 0);
		struct timespec wait = {2, 100000000};
		nanosleep(&wait, NULL);
		r = u.progress(u.ctx, "Test operation", false);
	} else {
		bool prepare = !strcmp(argv[1], "prepare") || !strcmp(argv[1], "prepare-repeat-key");
		struct fake f = { .mask = prepare ? 0 : 3, .ready = !prepare,
			.bad_pin = !strncmp(argv[1], "lockout", 7),
			.delete_failure = !strcmp(argv[1], "lockout-delete-failure"),
			.echo_pin = !strcmp(argv[1], "lockout-echo"), .ui = &u,
			.repeat_key = !strcmp(argv[1], "prepare-repeat-key") };
		struct msd_backend b = {&f, inspect, operate, deactivate};
		r = prepare ? msd_prepare(&b, &u, s) : msd_unlock(&b, &u, s);
		printf("result=%d mask=%d ready=%d\n", r, f.mask, f.ready);
	}
	assert(msd_terminal_close(&t) == 0);
	msd_secret_free(s);
	puts("DONE");
	return 0;
}
