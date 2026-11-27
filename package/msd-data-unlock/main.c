/* SPDX-License-Identifier: GPL-2.0-only */
#define _GNU_SOURCE
#include "crypt-backend.h"
#include "terminal.h"

#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

static void lcd_failure(void)
{
	const char *paths[] = {"/dev/console", "/dev/kmsg"};
	const char text[] = "Boot stopped. LCD console unavailable. Safe to power off.\n";
	for (size_t i = 0; i < 2; i++) {
		int fd = open(paths[i], O_WRONLY | O_NONBLOCK | O_CLOEXEC | O_NOCTTY);
		if (fd >= 0) {
			ssize_t ignored = write(fd, text, sizeof(text)-1);
			(void)ignored;
			close(fd);
		}
	}
}

static int control_fd(const char *value)
{
	char *end;
	errno = 0;
	long n = strtol(value, &end, 10);
	if (errno || !*value || *end || n < 3 || n > INT_MAX)
		return -1;
	int type;
	socklen_t size = sizeof(type);
	struct sockaddr_storage address;
	socklen_t addr_size = sizeof(address);
	if (getsockopt((int)n, SOL_SOCKET, SO_TYPE, &type, &size) ||
	    type != SOCK_STREAM || getsockname((int)n, (struct sockaddr *)&address, &addr_size) ||
	    address.ss_family != AF_UNIX || fcntl((int)n, F_SETFD, FD_CLOEXEC))
		return -1;
	return (int)n;
}

int main(int argc, char **argv)
{
	const char *device = NULL, *mode = NULL, *control = NULL;
	bool prepare;
	int fd = -1, channel = -1, r = -EINVAL;
	struct msd_secret *secret = NULL;
	struct msd_crypt *crypt = NULL;
	struct msd_backend backend;
	struct msd_ui ui;
	struct msd_terminal terminal = {0};
	if (argc < 2 || (strcmp(argv[1], "prepare") && strcmp(argv[1], "unlock")))
		goto usage;
	prepare = !strcmp(argv[1], "prepare");
	for (int i = 2; i < argc; i += 2) {
		if (i + 1 >= argc)
			goto usage;
		if (!strcmp(argv[i], "--device") && !device)
			device = argv[i+1];
		else if (!strcmp(argv[i], "--io") && !mode)
			mode = argv[i+1];
		else if (!strcmp(argv[i], "--control-fd") && !control)
			control = argv[i+1];
		else
			goto usage;
	}
	if (!device || !*device || !mode || (strcmp(mode, "product") && strcmp(mode, "qemu")) ||
	    (prepare && !control) || (!prepare && control))
		goto usage;
	if (control && (channel = control_fd(control)) < 0)
		goto usage;
	if (msd_security_init() < 0 || !(secret = msd_secret_alloc()))
		goto done;
	const char *tty = !strcmp(mode, "product") ? "/dev/tty1" : "/dev/ttyAMA1";
	fd = open(tty, O_RDWR | O_NOCTTY | O_NONBLOCK | O_CLOEXEC);
	if (fd < 0) {
		if (!strcmp(mode, "product"))
			lcd_failure();
		goto done;
	}
	if (msd_terminal_open(&terminal, fd, channel, secret, &ui) < 0)
		goto done;
	if (msd_crypt_open(&crypt, &backend, device, "msd-data") < 0)
		goto done;
	r = prepare ? msd_prepare(&backend, &ui, secret) : msd_unlock(&backend, &ui, secret);
done:
	if (terminal.active && r < 0)
		ui.message(ui.ctx, "Boot stopped. Safe to power off.\n");
	int restored = msd_terminal_close(&terminal);
	if (restored < 0 && !prepare && r >= 0) {
		r = restored;
		backend.deactivate(backend.ctx);
	}
	msd_crypt_close(crypt);
	if (fd >= 0)
		close(fd);
	msd_secret_free(secret);
	if (r < 0)
		fputs("msd-data-unlock: stopped\n", stderr);
	return r < 0 ? 1 : 0;
usage:
	fputs("Usage: msd-data-unlock prepare|unlock --device DEVICE --io product|qemu [--control-fd FD]\n", stderr);
	return 2;
}
