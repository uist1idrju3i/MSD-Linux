/* SPDX-License-Identifier: GPL-2.0-only */
#define _GNU_SOURCE
#include "boot.h"
#include "terminal.h"

#include <errno.h>
#include <limits.h>
#include <poll.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/sysmacros.h>
#include <unistd.h>

#ifndef MSD_DATA_INITIAL_BYTES
#error MSD_DATA_INITIAL_BYTES must come from board/cardputerzero/data-layout.conf
#endif
_Static_assert(MSD_DATA_INITIAL_BYTES >= 536870912ULL, "data region too small");

int msd_boot_classify(const struct msd_boot_ops *ops, enum msd_data_state *state)
{
	char label[64] = {0};
	int r = ops->probe(ops->ctx, label, sizeof(label));
	if (r < 0)
		return r;
	if (r) {
		if (!strcmp(label, "ready"))
			*state = MSD_DATA_READY;
		else if (!strcmp(label, "pending"))
			*state = MSD_DATA_PENDING;
		else
			return -EINVAL;
		return 0;
	}
	uint64_t offset = 0, total = MSD_DATA_INITIAL_BYTES;
	unsigned char buffer[65536];
	if ((r = ops->scanning(ops->ctx, 0, total)) < 0)
		return r;
	while (offset < total) {
		size_t count = total - offset < sizeof(buffer) ?
			(size_t)(total - offset) : sizeof(buffer);
		ssize_t n = ops->read_at(ops->ctx, buffer, count, (off_t)offset);
		if (n < 0)
			return (int)n;
		if (!n || (size_t)n > count)
			return -EIO;
		for (ssize_t i = 0; i < n; i++)
			if (buffer[i])
				return -ENOTEMPTY;
		offset += (uint64_t)n;
		if ((r = ops->scanning(ops->ctx, offset, total)) < 0)
			return r;
	}
	*state = MSD_DATA_EMPTY;
	return 0;
}

static int receive_line(int fd, char *line, size_t size)
{
	size_t used = 0;
	while (used + 1 < size) {
		if (msd_interrupted)
			return -EINTR;
		struct pollfd p = { .fd = fd, .events = POLLIN };
		int r = poll(&p, 1, 250);
		if (r < 0)
			return -errno;
		if (!r)
			continue;
		ssize_t n = read(fd, line + used, 1);
		if (n <= 0)
			return n < 0 ? -errno : -ENODATA;
		if (line[used++] == '\n') {
			line[used] = 0;
			return 0;
		}
	}
	return -EOVERFLOW;
}

int msd_boot_control(int fd, const struct msd_boot_ops *ops)
{
	const char *requests[] = {"grow\n", "filesystem\n"};
	const char *replies[] = {"grown\n", "synced\n"};
	for (size_t i = 0; i < 2; i++) {
		char line[32];
		int r = receive_line(fd, line, sizeof(line));
		if (r < 0)
			return r;
		if (strcmp(line, requests[i]))
			return -EPROTO;
		r = i ? ops->filesystem(ops->ctx) : ops->grow(ops->ctx);
		if (r < 0)
			return r;
		size_t used = 0, length = strlen(replies[i]);
		while (used < length) {
			struct pollfd p = { .fd = fd, .events = POLLOUT };
			r = poll(&p, 1, 1000);
			if (r <= 0)
				return r < 0 ? -errno : -ETIMEDOUT;
			ssize_t n = send(fd, replies[i] + used, length - used, MSG_NOSIGNAL);
			if (n <= 0)
				return n < 0 ? -errno : -EIO;
			used += (size_t)n;
		}
	}
	return 0;
}

bool msd_boot_same_device(const struct stat *a, const struct stat *b)
{
	return S_ISBLK(a->st_mode) && S_ISBLK(b->st_mode) &&
		major(a->st_rdev) == major(b->st_rdev) &&
		minor(a->st_rdev) == minor(b->st_rdev);
}

int msd_boot_mounted(FILE *mounts, const char *mapper)
{
	struct stat expected, source;
	if (stat(mapper, &expected) < 0 || !S_ISBLK(expected.st_mode))
		return -ENODEV;
	char line[8192], device[PATH_MAX], path[PATH_MAX], type[64];
	int found = 0;
	while (fgets(line, sizeof(line), mounts)) {
		if (!strchr(line, '\n'))
			return -EOVERFLOW;
		if (sscanf(line, "%4095s %4095s %63s", device, path, type) != 3)
			return -EINVAL;
		if (strcmp(path, "/data"))
			continue;
		if (++found != 1 || strcmp(type, "btrfs") ||
		    stat(device, &source) < 0 || !msd_boot_same_device(&expected, &source))
			return -ENODEV;
	}
	return !ferror(mounts) && found == 1 ? 0 : -ENODEV;
}
