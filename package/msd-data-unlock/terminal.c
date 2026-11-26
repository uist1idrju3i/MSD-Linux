/* SPDX-License-Identifier: GPL-2.0-only */
#define _GNU_SOURCE
#include "terminal.h"

#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/prctl.h>
#include <sys/random.h>
#include <sys/resource.h>
#include <time.h>
#include <unistd.h>

volatile sig_atomic_t msd_interrupted;

static void interrupted(int sig)
{
	(void)sig;
	msd_interrupted = 1;
}

int msd_security_init(void)
{
	struct rlimit limit = {0, 0};
	struct sigaction action = { .sa_handler = interrupted };
	sigemptyset(&action.sa_mask);
	if (setrlimit(RLIMIT_CORE, &limit) || prctl(PR_SET_DUMPABLE, 0) || clearenv())
		return -errno;
	int signals[] = {SIGINT, SIGTERM, SIGHUP, SIGQUIT, SIGPIPE, SIGTSTP};
	for (size_t i = 0; i < sizeof(signals)/sizeof(signals[0]); i++)
		if (sigaction(signals[i], &action, NULL))
			return -errno;
	return 0;
}

static int put(int fd, const char *text, size_t size)
{
	while (size) {
		if (msd_interrupted)
			return -EINTR;
		struct pollfd p = { .fd = fd, .events = POLLOUT };
		int n = poll(&p, 1, 1000);
		if (n < 0)
			return -errno;
		if (!n)
			return -ETIMEDOUT;
		if (!(p.revents & POLLOUT))
			return -EIO;
		ssize_t written = write(fd, text, size);
		if (written <= 0)
			return written < 0 ? -errno : -EIO;
		text += written;
		size -= (size_t)written;
	}
	return 0;
}

static int message(void *ctx, const char *text)
{
	struct msd_terminal *t = ctx;
	return put(t->fd, text, strlen(text));
}

static int get_byte(struct msd_terminal *t)
{
	for (;;) {
		if (msd_interrupted)
			return -EINTR;
		struct pollfd p = { .fd = t->fd, .events = POLLIN };
		int r = poll(&p, 1, 250);
		if (r < 0)
			return -errno;
		if (!r)
			continue;
		ssize_t n = read(t->fd, &t->secret->key, 1);
		if (n == 1)
			return 0;
		return n == 0 ? -ENODATA : -errno;
	}
}

static int escape_sequence(struct msd_terminal *t)
{
	struct pollfd p = { .fd = t->fd, .events = POLLIN };
	int r = poll(&p, 1, 100);
	if (r <= 0)
		return r < 0 ? -errno : -EINTR;
	if ((r = get_byte(t)) < 0)
		return r;
	unsigned char c = t->secret->key;
	t->secret->key = 0;
	if (c != '[' && c != 'O')
		return -EINTR;
	bool first = true;
	for (;;) {
		if ((r = get_byte(t)) < 0)
			return r;
		c = t->secret->key;
		t->secret->key = 0;
		if (c >= 0x40 && c <= 0x7e && !(first && c == '['))
			return 0;
		if (c < 0x20 || c > 0x3f) {
			if (!(first && c == '['))
				return c == 3 ? -EINTR : -EINVAL;
		}
		first = false;
	}
}

static int read_line(void *ctx, char *out, size_t cap)
{
	struct msd_terminal *t = ctx;
	size_t len = 0;
	bool invalid = false;
	int r;
	for (;;) {
		if ((r = get_byte(t)) < 0)
			break;
		unsigned char c = t->secret->key;
		t->secret->key = 0;
		if (t->skip_lf) {
			t->skip_lf = false;
			if (c == '\n')
				continue;
		}
		if (c == 27) {
			if ((r = escape_sequence(t)) < 0)
				break;
			continue;
		}
		if (c == 3) { r = -EINTR; break; }
		if (c == 4) { r = -ENODATA; break; }
		if (c == '\n' || c == '\r') {
			t->skip_lf = c == '\r';
			r = message(t, "\n");
			if (!r)
				r = invalid ? -EINVAL : (int)len;
			break;
		}
		if (c == 8 || c == 127) {
			if (len && !invalid) {
				out[--len] = 0;
				if ((r = message(t, "\b \b")) < 0)
					break;
			}
			continue;
		}
		if (c < 0x20 || c > 0x7e || len + 1 >= cap) {
			invalid = true;
			continue;
		}
		if (invalid)
			continue;
		out[len++] = (char)c;
		if ((r = message(t, "*")) < 0)
			break;
	}
	if (r < 0)
		explicit_bzero(out, cap);
	else
		out[len] = 0;
	t->secret->key = 0;
	return r;
}

static int display_recovery(void *ctx, const char *key)
{
	struct msd_terminal *t = ctx;
	for (size_t i = 0; i < 8; i++) {
		int r = put(t->fd, key + 4*i, 4);
		if (r < 0)
			return r;
		if ((r = message(t, i == 7 ? "\n" : " ")) < 0)
			return r;
	}
	return 0;
}

static int random_bytes(void *ctx, unsigned char *out, size_t size)
{
	(void)ctx;
	while (size) {
		if (msd_interrupted)
			return -EINTR;
		ssize_t n = getrandom(out, size, 0);
		if (n <= 0)
			return n < 0 ? -errno : -EIO;
		out += n;
		size -= (size_t)n;
	}
	return 0;
}

static int checkpoint(void *ctx, enum msd_checkpoint phase)
{
	struct msd_terminal *t = ctx;
	const char *request = phase == MSD_GROW ? "grow\n" : "filesystem\n";
	const char *reply = phase == MSD_GROW ? "grown\n" : "synced\n";
	int r = put(t->control, request, strlen(request));
	if (r < 0)
		return r;
	for (size_t i = 0; reply[i]; i++) {
		char c = 0;
		for (;;) {
			if (msd_interrupted)
				return -EINTR;
			struct pollfd p = { .fd = t->control, .events = POLLIN };
			r = poll(&p, 1, 250);
			if (r < 0)
				return -errno;
			if (r)
				break;
		}
		ssize_t n = read(t->control, &c, 1);
		if (n != 1 || c != reply[i])
			return -EIO;
	}
	return 0;
}

static void *ticker(void *ctx)
{
	struct msd_terminal *t = ctx;
	unsigned elapsed = 0;
	pthread_mutex_lock(&t->mutex);
	while (!t->stop) {
		struct timespec until;
		clock_gettime(CLOCK_MONOTONIC, &until);
		until.tv_sec++;
		int r = pthread_cond_timedwait(&t->condition, &t->mutex, &until);
		if (!t->stop && r == ETIMEDOUT) {
			char text[160];
			snprintf(text, sizeof(text), "%s: %u seconds. Do not power off.\n", t->phase, ++elapsed);
			r = message(t, text);
			if (r < 0) {
				t->output_error = r;
				break;
			}
		}
	}
	pthread_mutex_unlock(&t->mutex);
	return NULL;
}

static int progress(void *ctx, const char *phase, bool start)
{
	struct msd_terminal *t = ctx;
	if (start) {
		int r = message(t, phase);
		if (!r)
			r = message(t, ": starting. Do not power off.\n");
		if (r < 0)
			return r;
		t->phase = phase;
		t->stop = false;
		t->output_error = 0;
		r = pthread_create(&t->thread, NULL, ticker, t);
		if (r)
			return -r;
		t->ticking = true;
		return 0;
	}
	pthread_mutex_lock(&t->mutex);
	t->stop = true;
	pthread_cond_signal(&t->condition);
	pthread_mutex_unlock(&t->mutex);
	pthread_join(t->thread, NULL);
	t->ticking = false;
	if (msd_interrupted)
		return -EINTR;
	return t->output_error;
}

int msd_terminal_open(struct msd_terminal *t, int fd, int control,
		      struct msd_secret *secret, struct msd_ui *u)
{
	memset(t, 0, sizeof(*t));
	t->fd = fd;
	t->control = control;
	t->secret = secret;
	if (tcgetattr(fd, &t->saved))
		return -errno;
	struct termios raw = t->saved;
	cfmakeraw(&raw);
	raw.c_oflag = OPOST | ONLCR;
	if (tcsetattr(fd, TCSAFLUSH, &raw))
		return -errno;
	t->active = true;
	int r = pthread_mutex_init(&t->mutex, NULL);
	if (r)
		goto fail;
	pthread_condattr_t attr;
	r = pthread_condattr_init(&attr);
	if (r)
		goto mutex_fail;
	r = pthread_condattr_setclock(&attr, CLOCK_MONOTONIC);
	if (!r)
		r = pthread_cond_init(&t->condition, &attr);
	pthread_condattr_destroy(&attr);
	if (r)
		goto mutex_fail;
	*u = (struct msd_ui){ t, message, read_line, display_recovery,
			     random_bytes, checkpoint, progress };
	return 0;
mutex_fail:
	pthread_mutex_destroy(&t->mutex);
fail:
	tcsetattr(fd, TCSAFLUSH, &t->saved);
	t->active = false;
	return -r;
}

int msd_terminal_close(struct msd_terminal *t)
{
	if (!t->active)
		return 0;
	if (t->ticking)
		progress(t, t->phase, false);
	int r = tcsetattr(t->fd, TCSAFLUSH, &t->saved) < 0 ? -errno : 0;
	pthread_cond_destroy(&t->condition);
	pthread_mutex_destroy(&t->mutex);
	t->active = false;
	return r;
}
