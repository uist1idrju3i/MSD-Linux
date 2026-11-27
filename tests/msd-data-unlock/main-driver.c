/* SPDX-License-Identifier: GPL-2.0-only */
#include "crypt-backend.h"
#include "terminal.h"

#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

struct msd_crypt { bool closed; };
static struct msd_crypt crypt;
static struct msd_secret secret;
static bool mapped;
static int operation_error, restore_error, cleanup_error, deactivations;
int msd_helper_main(int, char **);
int __real_open(const char *, int, ...);

int __wrap_open(const char *path, int flags, ...)
{
	assert(!strcmp(path, "/dev/ttyAMA1"));
	return __real_open("/dev/null", flags);
}

int msd_security_init(void) { return 0; }
struct msd_secret *msd_secret_alloc(void) { return &secret; }
void msd_secret_free(struct msd_secret *s) { assert(s == &secret); }

static int deactivate(void *ctx)
{
	assert(ctx == &crypt && !crypt.closed && mapped);
	deactivations++;
	if (!cleanup_error)
		mapped = false;
	return cleanup_error;
}

int msd_crypt_open(struct msd_crypt **out, struct msd_backend *b,
		   const char *path, const char *mapping)
{
	assert(!strcmp(path, "/device") && !strcmp(mapping, "msd-data"));
	crypt.closed = false;
	*out = &crypt;
	*b = (struct msd_backend){ .ctx = &crypt, .deactivate = deactivate };
	return 0;
}

void msd_crypt_close(struct msd_crypt *c)
{
	assert(c == &crypt && !c->closed);
	c->closed = true;
}

static int message(void *ctx, const char *text)
{
	(void)ctx; (void)text;
	return 0;
}

int msd_terminal_open(struct msd_terminal *t, int fd, int channel,
		      struct msd_secret *s, struct msd_ui *u)
{
	(void)fd; (void)channel;
	assert(s == &secret);
	t->active = true;
	*u = (struct msd_ui){ .message = message };
	return 0;
}

int msd_terminal_close(struct msd_terminal *t)
{
	assert(t->active && !crypt.closed);
	t->active = false;
	return restore_error;
}

int msd_unlock(struct msd_backend *b, struct msd_ui *u, struct msd_secret *s)
{
	(void)b; (void)u; (void)s;
	if (operation_error)
		return operation_error;
	if (mapped)
		return -EEXIST;
	mapped = true;
	return 0;
}

int msd_prepare(struct msd_backend *b, struct msd_ui *u, struct msd_secret *s)
{
	return msd_unlock(b, u, s);
}

static int invoke(bool prepare, int operation, int restore, int cleanup)
{
	int channel[2];
	assert(socketpair(AF_UNIX, SOCK_STREAM, 0, channel) == 0);
	char number[32];
	snprintf(number, sizeof(number), "%d", channel[0]);
	char *argv[] = {"helper", prepare ? "prepare" : "unlock", "--device",
		"/device", "--io", "qemu", "--control-fd", number, NULL};
	operation_error = operation; restore_error = restore; cleanup_error = cleanup;
	deactivations = 0;
	int r = msd_helper_main(prepare ? 8 : 6, argv);
	assert(crypt.closed);
	close(channel[0]); close(channel[1]);
	return r;
}

int main(void)
{
	assert(invoke(false, 0, -EIO, 0) == 1 && !mapped && deactivations == 1);
	assert(invoke(false, 0, 0, 0) == 0 && mapped && !deactivations);
	assert(invoke(false, 0, -EIO, 0) == 1 && mapped && !deactivations);
	mapped = false;
	assert(invoke(false, 0, -ENOSPC, -EBUSY) == 1 && mapped && deactivations == 1);
	mapped = false;
	assert(invoke(false, -EINTR, -EIO, 0) == 1 && !mapped && !deactivations);
	assert(invoke(true, 0, -EIO, 0) == 0 && mapped && !deactivations);
	mapped = false;
	assert(invoke(true, -EIO, -ENOSPC, -EBUSY) == 1 && !mapped && !deactivations);
	puts("ok - main: terminal restore failure cleanup, retry, existing mapping, prepare completion");
	return 0;
}
