/* SPDX-License-Identifier: GPL-2.0-only */
#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <libcryptsetup.h>
#include <pty.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <termios.h>
#include <unistd.h>

int msd_boot_main(int, char **);
static const char *scenario;
static int slave, data_fd, trace_fd;

int __real_tcsetattr(int, int, const struct termios *);
int __wrap_tcsetattr(int fd, int action, const struct termios *settings)
{
	static int calls;
	if (++calls == 2 && strstr(scenario, "restore-fail")) {
		errno = EIO;
		return -1;
	}
	return __real_tcsetattr(fd, action, settings);
}

int __real_open(const char *, int, ...);
int __wrap_open(const char *path, int flags, ...)
{
	if (!strcmp(path, "/dev/tty1") || !strcmp(path, "/dev/ttyAMA1")) {
		if (!strcmp(scenario, "tty-missing")) {
			errno = ENOENT;
			return -1;
		}
		return fcntl(slave, F_DUPFD_CLOEXEC, 10);
	}
	if (!strcmp(path, "/dev/console") || !strcmp(path, "/dev/kmsg"))
		return fcntl(trace_fd, F_DUPFD_CLOEXEC, 10);
	if (!strcmp(path, "/dev/mmcblk0p7"))
		return fcntl(data_fd, F_DUPFD_CLOEXEC, 10);
	mode_t mode = 0;
	if (flags & O_CREAT) {
		va_list ap;
		va_start(ap, flags);
		mode = (mode_t)va_arg(ap, int);
		va_end(ap);
	}
	return __real_open(path, flags, mode);
}

int __wrap_crypt_init(struct crypt_device **cd, const char *path)
{
	assert(!strcmp(path, "/dev/mmcblk0p7"));
	*cd = (struct crypt_device *)1;
	return 0;
}

int __wrap_crypt_load(struct crypt_device *cd, const char *type, void *params)
{
	(void)cd; (void)params;
	assert(!strcmp(type, CRYPT_LUKS2));
	if (!strcmp(scenario, "probe-error"))
		return -EIO;
	return !strcmp(scenario, "empty") ? -EINVAL : 0;
}

const char *__wrap_crypt_get_label(struct crypt_device *cd)
{
	(void)cd;
	if (!strcmp(scenario, "unknown"))
		return "unknown";
	return !strcmp(scenario, "ready") || !strcmp(scenario, "unlock-fail") ||
		!strcmp(scenario, "ready-restore-fail") ? "ready" : "pending";
}

void __wrap_crypt_set_log_callback(struct crypt_device *cd,
				 void (*log)(int, const char *, void *), void *ctx)
{
	(void)cd; (void)log; (void)ctx;
}

void __wrap_crypt_free(struct crypt_device *cd) { (void)cd; }

int __wrap_stat(const char *path, struct stat *st)
{
	assert(!strcmp(path, "/dev/mapper/msd-data") || !strcmp(path, "/dev/dm-7"));
	memset(st, 0, sizeof(*st));
	st->st_mode = S_IFBLK;
	st->st_rdev = makedev(253, 7);
	return 0;
}

FILE *__real_fopen(const char *, const char *);
FILE *__wrap_fopen(const char *path, const char *mode)
{
	static char mounts[] = "/dev/dm-7 /data btrfs rw 0 0\n";
	if (!strcmp(path, "/proc/mounts"))
		return fmemopen(mounts, strlen(mounts), "r");
	return __real_fopen(path, mode);
}

int __real_access(const char *, int);
int __wrap_access(const char *path, int mode)
{
	if (!strcmp(path, "/usr/sbin/mkfs.btrfs"))
		return 0;
	return __real_access(path, mode);
}

int __wrap_execv(const char *path, char *const argv[])
{
	for (size_t i = 0; argv[i]; i++)
		dprintf(trace_fd, "%s%s", i ? " " : "", argv[i]);
	dprintf(trace_fd, "\n");
	const char *fail = !strcmp(scenario, "grow-fail") ? "msd-data-partition-grow" :
		!strcmp(scenario, "mkfs-fail") ? "mkfs.btrfs" :
		!strcmp(scenario, "mount-fail") ? "/bin/mount" :
		!strcmp(scenario, "mkdir-fail") ? "/bin/mkdir" :
		!strcmp(scenario, "sync-fail") ? "msd-syncfs" : NULL;
	if (strstr(path, "mkfs.btrfs"))
		assert(!strcmp(argv[1], "-d") && !strcmp(argv[2], "dup") &&
		       !strcmp(argv[3], "-m") && !strcmp(argv[4], "dup") &&
		       !strcmp(argv[5], "--csum") && !strcmp(argv[6], "xxhash"));
	if (!strcmp(path, "/bin/mount"))
		assert(!strcmp(argv[2], "btrfs") &&
		       !strcmp(argv[4], "noatime,nodev,nosuid,compress=zstd:3") &&
		       !strcmp(argv[5], "/dev/mapper/msd-data"));
	_exit(fail && strstr(path, fail) ? 1 : 0);
}

static void exchange(const char *request, const char *reply)
{
	assert(write(3, request, strlen(request)) == (ssize_t)strlen(request));
	char buffer[32] = {0};
	size_t used = 0;
	while (used < strlen(reply)) {
		ssize_t n = read(3, buffer + used, strlen(reply) - used);
		if (n <= 0)
			_exit(1);
		used += (size_t)n;
	}
	assert(!strcmp(buffer, reply));
	dprintf(trace_fd, "ack %s", reply);
}

int __wrap_execl(const char *path, const char *arg0, ...)
{
	assert(!strcmp(path, "/usr/sbin/msd-data-unlock") && !strcmp(arg0, "msd-data-unlock"));
	va_list ap;
	va_start(ap, arg0);
	const char *mode = va_arg(ap, const char *);
	dprintf(trace_fd, "helper %s\n", mode);
	va_end(ap);
	if (!strcmp(mode, "unlock"))
		_exit(!strcmp(scenario, "unlock-fail"));
	assert(!strcmp(mode, "prepare"));
	if (!strcmp(scenario, "helper-eof"))
		_exit(1);
	if (!strcmp(scenario, "helper-bad")) {
		exchange("filesystem\n", "synced\n");
		_exit(1);
	}
	exchange("grow\n", "grown\n");
	exchange("filesystem\n", "synced\n");
	_exit(!strcmp(scenario, "post-synced-fail"));
}

int main(int argc, char **argv)
{
	assert(argc == 2);
	scenario = argv[1];
	int master;
	assert(openpty(&master, &slave, NULL, NULL, NULL) == 0);
	FILE *data = tmpfile(), *trace = tmpfile();
	assert(data && trace);
	data_fd = fileno(data);
	trace_fd = fileno(trace);
	assert(ftruncate(data_fd, 536870912) == 0);
	char *args[] = {"msd-data-boot", "start", "product", NULL};
	int r = msd_boot_main(3, args);
	bool success = !strcmp(scenario, "empty") || !strcmp(scenario, "pending") ||
		!strcmp(scenario, "ready") || !strcmp(scenario, "prepare-restore-fail");
	assert((r == 0) == success);
	assert(lseek(trace_fd, 0, SEEK_SET) == 0);
	char log[4096] = {0};
	assert(read(trace_fd, log, sizeof(log) - 1) >= 0);
	if (!strcmp(scenario, "tty-missing")) {
		assert(strstr(log, "LCD console unavailable") && !strstr(log, "helper"));
	} else if (!strcmp(scenario, "unknown") || !strcmp(scenario, "probe-error")) {
		assert(!log[0]);
	} else if (!strcmp(scenario, "ready") || !strcmp(scenario, "ready-restore-fail")) {
		assert(strstr(log, "helper unlock") && strstr(log, "/bin/mount") &&
		       !strstr(log, "grow") && !strstr(log, "mkfs") && !strstr(log, "mkdir"));
	} else if (!strcmp(scenario, "unlock-fail")) {
		assert(!strcmp(log, "helper unlock\n"));
	} else {
		assert(strstr(log, "helper prepare"));
		if (success) {
			char *grow = strstr(log, "msd-data-partition-grow");
			char *grown = strstr(log, "ack grown");
			char *mkfs = strstr(log, "mkfs.btrfs");
			char *mount = strstr(log, "/bin/mount");
			char *dirs = strstr(log, "/bin/mkdir");
			char *sync = strstr(log, "msd-syncfs");
			char *synced = strstr(log, "ack synced");
			assert(grow && grown && mkfs && mount && dirs && sync && synced &&
			       grow < grown && grown < mkfs && mkfs < mount && mount < dirs && dirs < sync && sync < synced);
		} else if (strcmp(scenario, "post-synced-fail")) {
			assert(!strstr(log, "ack synced"));
			if (!strcmp(scenario, "grow-fail"))
				assert(!strstr(log, "mkfs") && !strstr(log, "ack grown"));
			if (!strcmp(scenario, "mkfs-fail"))
				assert(!strstr(log, "/bin/mount"));
			if (!strcmp(scenario, "mount-fail"))
				assert(!strstr(log, "mkdir"));
			if (!strcmp(scenario, "mkdir-fail"))
				assert(!strstr(log, "msd-syncfs"));
		} else {
			assert(strstr(log, "ack synced"));
			assert(!strstr(strstr(log, "helper prepare") + 1, "helper prepare"));
		}
	}
	fclose(data);
	fclose(trace);
	close(master);
	close(slave);
	printf("ok - boot coordinator integration: %s\n", scenario);
	return 0;
}
