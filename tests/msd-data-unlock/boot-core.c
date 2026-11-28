/* SPDX-License-Identifier: GPL-2.0-only */
#define _GNU_SOURCE
#include "boot.h"
#include "terminal.h"

#include <assert.h>
#include <errno.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/sysmacros.h>
#include <sys/wait.h>
#include <unistd.h>

volatile sig_atomic_t msd_interrupted;

struct fixture {
	const char *label;
	int probe_error, read_error, progress_error, grow_error, fs_error;
	uint64_t read_bytes, last_progress;
	int nonzero, short_read, grow_calls, fs_calls, disconnect;
	int fd;
};

static int probe(void *ctx, char *label, size_t size)
{
	struct fixture *f = ctx;
	if (f->probe_error)
		return -EIO;
	if (!f->label)
		return 0;
	assert(strlen(f->label) < size);
	strcpy(label, f->label);
	return 1;
}

static ssize_t read_at(void *ctx, void *buffer, size_t size, off_t offset)
{
	struct fixture *f = ctx;
	assert((uint64_t)offset == f->read_bytes);
	if (f->read_error)
		return -EIO;
	if (f->short_read)
		return 0;
	memset(buffer, 0, size);
	if (f->nonzero && (uint64_t)offset + size == MSD_DATA_INITIAL_BYTES)
		((char *)buffer)[size - 1] = 1;
	f->read_bytes += size;
	return (ssize_t)size;
}

static int scanning(void *ctx, uint64_t done, uint64_t total)
{
	struct fixture *f = ctx;
	assert(total == MSD_DATA_INITIAL_BYTES && done >= f->last_progress);
	f->last_progress = done;
	return f->progress_error ? -EIO : 0;
}

static int grow(void *ctx)
{
	struct fixture *f = ctx;
	f->grow_calls++;
	if (f->disconnect)
		shutdown(f->fd, SHUT_RDWR);
	return f->grow_error ? -EIO : 0;
}

static int filesystem(void *ctx)
{
	struct fixture *f = ctx;
	assert(f->grow_calls == 1);
	f->fs_calls++;
	return f->fs_error ? -EIO : 0;
}

static struct msd_boot_ops ops(struct fixture *f)
{
	return (struct msd_boot_ops){f, probe, read_at, scanning, grow, filesystem};
}

static void classification(void)
{
	enum msd_data_state state;
	struct fixture f = {0};
	struct msd_boot_ops o = ops(&f);
	assert(msd_boot_classify(&o, &state) == 0 && state == MSD_DATA_EMPTY);
	assert(f.read_bytes == MSD_DATA_INITIAL_BYTES && f.last_progress == MSD_DATA_INITIAL_BYTES);
	const char *labels[] = {"pending", "ready", "unknown", ""};
	for (size_t i = 0; i < 4; i++) {
		f = (struct fixture){.label = labels[i]};
		int r = msd_boot_classify(&o, &state);
		assert(i < 2 ? r == 0 : r < 0);
		if (i < 2)
			assert(state == (i ? MSD_DATA_READY : MSD_DATA_PENDING));
		assert(!f.read_bytes);
	}
	for (int i = 0; i < 5; i++) {
		f = (struct fixture){0};
		if (i == 0) f.nonzero = 1;
		if (i == 1) f.read_error = 1;
		if (i == 2) f.short_read = 1;
		if (i == 3) f.probe_error = 1;
		if (i == 4) f.progress_error = 1;
		assert(msd_boot_classify(&o, &state) < 0);
	}
	puts("ok - boot state: fixed N, rear nonzero, pending/ready skip scan, unknown/header/read/progress errors");
}

static void protocol(const char *requests, const char *reply, int g, int fs,
		     int disconnect, bool success, int grows, int filesystems)
{
	int pair[2];
	assert(socketpair(AF_UNIX, SOCK_STREAM, 0, pair) == 0);
	pid_t pid = fork();
	assert(pid >= 0);
	if (!pid) {
		close(pair[0]);
		assert(write(pair[1], requests, strlen(requests)) == (ssize_t)strlen(requests));
		shutdown(pair[1], SHUT_WR);
		char response[128] = {0};
		size_t used = 0;
		ssize_t n;
		while ((n = read(pair[1], response + used, sizeof(response) - used - 1)) > 0)
			used += (size_t)n;
		assert(!strcmp(response, reply));
		close(pair[1]);
		_exit(0);
	}
	close(pair[1]);
	struct fixture f = {.grow_error = g, .fs_error = fs, .disconnect = disconnect, .fd = pair[0]};
	struct msd_boot_ops o = ops(&f);
	assert((msd_boot_control(pair[0], &o) == 0) == success);
	assert(f.grow_calls == grows && f.fs_calls == filesystems);
	close(pair[0]);
	int status;
	assert(waitpid(pid, &status, 0) == pid && WIFEXITED(status) && !WEXITSTATUS(status));
}

int __wrap_stat(const char *path, struct stat *st)
{
	memset(st, 0, sizeof(*st));
	st->st_mode = S_IFBLK;
	st->st_rdev = makedev(253, !strcmp(path, "/wrong") ? 8 : 7);
	if (!strcmp(path, "/regular"))
		st->st_mode = S_IFREG;
	if (!strcmp(path, "/missing")) {
		errno = ENOENT;
		return -1;
	}
	return 0;
}

static void mounted(const char *text, bool expected)
{
	FILE *stream = fmemopen((void *)text, strlen(text), "r");
	assert(stream);
	assert((msd_boot_mounted(stream, "/mapper") == 0) == expected);
	fclose(stream);
}

int main(void)
{
	classification();
	protocol("grow\nfilesystem\n", "grown\nsynced\n", 0, 0, 0, true, 1, 1);
	protocol("", "", 0, 0, 0, false, 0, 0);
	protocol("grow\n", "grown\n", 0, 0, 0, false, 1, 0);
	protocol("filesystem\n", "", 0, 0, 0, false, 0, 0);
	protocol("grow\ngrow\n", "grown\n", 0, 0, 0, false, 1, 0);
	protocol("abcdefghijklmnopqrstuvwxyzabcdef\n", "", 0, 0, 0, false, 0, 0);
	protocol("grow\nfilesystem\n", "", 1, 0, 0, false, 1, 0);
	protocol("grow\nfilesystem\n", "grown\n", 0, 1, 0, false, 1, 1);
	protocol("grow\n", "", 0, 0, 1, false, 1, 0);
	puts("ok - boot control: ordered acknowledgements, grow/filesystem failures, EOF, malformed request, disconnect");
	mounted("/dev/dm-7 /data btrfs rw 0 0\n", true);
	mounted("/dev/dm-7 /data ext4 rw 0 0\n", false);
	mounted("/wrong /data btrfs rw 0 0\n", false);
	mounted("/regular /data btrfs rw 0 0\n", false);
	mounted("/missing /data btrfs rw 0 0\n", false);
	mounted("", false);
	mounted("/dev/dm-7 /data btrfs rw 0 0\n/dev/dm-7 /data btrfs rw 0 0\n", false);
	puts("ok - boot health: Btrfs and block major/minor identity, aliases, wrong source/type, missing/duplicate mount");
	return 0;
}
