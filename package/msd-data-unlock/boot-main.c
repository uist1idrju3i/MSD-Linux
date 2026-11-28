/* SPDX-License-Identifier: GPL-2.0-only */
#define _GNU_SOURCE
#include "boot.h"
#include "terminal.h"

#include <errno.h>
#include <fcntl.h>
#include <libcryptsetup.h>
#include <limits.h>
#include <signal.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

struct boot {
	const char *device, *mode;
	int tty, device_fd;
	struct msd_ui ui;
	struct timespec scan_start;
	time_t last_scan;
};

static void quiet_log(int level, const char *text, void *ctx)
{
	(void)level;
	(void)text;
	(void)ctx;
}

static int health(void)
{
	FILE *mounts = fopen("/proc/mounts", "re");
	if (!mounts)
		return -errno;
	int r = msd_boot_mounted(mounts, "/dev/mapper/msd-data");
	if (fclose(mounts) && r >= 0)
		r = -errno;
	return r;
}

static int probe(void *ctx, char *label, size_t size)
{
	struct boot *b = ctx;
	struct crypt_device *cd = NULL;
	const char *phase = "Checking LUKS2 metadata";
	int r = b->ui.progress(b->ui.ctx, phase, true);
	if (r < 0)
		return r;
	crypt_set_log_callback(NULL, quiet_log, NULL);
	r = crypt_init(&cd, b->device);
	if (r >= 0) {
		crypt_set_log_callback(cd, quiet_log, NULL);
		r = crypt_load(cd, CRYPT_LUKS2, NULL);
		if (r == -EINVAL)
			r = 0;
		else if (r >= 0) {
			const char *value = crypt_get_label(cd);
			if (!value || strlen(value) >= size)
				r = -EINVAL;
			else {
				strcpy(label, value);
				r = 1;
			}
		}
	}
	crypt_free(cd);
	int end = b->ui.progress(b->ui.ctx, phase, false);
	return r < 0 ? r : end < 0 ? end : r;
}

static ssize_t read_at(void *ctx, void *buffer, size_t size, off_t offset)
{
	struct boot *b = ctx;
	if (msd_interrupted)
		return -EINTR;
	ssize_t n = pread(b->device_fd, buffer, size, offset);
	return n < 0 ? -errno : n;
}

static int scanning(void *ctx, uint64_t done, uint64_t total)
{
	struct boot *b = ctx;
	struct timespec now;
	if (clock_gettime(CLOCK_MONOTONIC, &now))
		return -errno;
	if (!done) {
		b->scan_start = now;
		b->last_scan = now.tv_sec;
		int r = b->ui.message(b->ui.ctx,
			"Checking that the image-defined data region is empty. Read-only check; safe to power off.\n");
		if (r < 0)
			return r;
	}
	if (done && done != total && b->last_scan == now.tv_sec)
		return 0;
	char text[192];
	snprintf(text, sizeof(text), "Checking empty data region: %llu/%llu bytes, %llu seconds. Read-only; safe to power off.\n",
		(unsigned long long)done, (unsigned long long)total,
		(unsigned long long)(now.tv_sec - b->scan_start.tv_sec));
	b->last_scan = now.tv_sec;
	return b->ui.message(b->ui.ctx, text);
}

static int wait_child(pid_t pid)
{
	int status;
	for (;;) {
		if (msd_interrupted)
			return -EINTR;
		pid_t r = waitpid(pid, &status, WNOHANG);
		if (r == pid)
			return WIFEXITED(status) && WEXITSTATUS(status) == 0 ? 0 : -ECHILD;
		if (r < 0 && errno != EINTR)
			return -errno;
		struct timespec delay = { .tv_nsec = 100000000 };
		nanosleep(&delay, NULL);
	}
}

static void stop_child(pid_t pid)
{
	kill(pid, SIGTERM);
	for (int i = 0; i < 50; i++) {
		int status;
		pid_t r = waitpid(pid, &status, WNOHANG);
		if (r == pid || (r < 0 && errno == ECHILD))
			return;
		struct timespec delay = { .tv_nsec = 100000000 };
		nanosleep(&delay, NULL);
	}
	kill(pid, SIGKILL);
	while (waitpid(pid, NULL, 0) < 0 && errno == EINTR) {}
}

static int command(struct boot *b, const char *phase, char *const argv[])
{
	char path[PATH_MAX];
	const char *program = argv[0];
	if (!strchr(program, '/')) {
		const char *dirs[] = {"/usr/sbin", "/usr/bin", "/sbin", "/bin"};
		bool found = false;
		for (size_t i = 0; i < 4; i++) {
			snprintf(path, sizeof(path), "%s/%s", dirs[i], program);
			if (!access(path, X_OK)) {
				program = path;
				found = true;
				break;
			}
		}
		if (!found)
			return -ENOENT;
	}
	int r = b->ui.progress(b->ui.ctx, phase, true);
	if (r < 0)
		return r;
	pid_t pid = fork();
	if (!pid) {
		if (dup2(b->tty, STDOUT_FILENO) < 0 || dup2(b->tty, STDERR_FILENO) < 0)
			_exit(127);
		execv(program, argv);
		_exit(127);
	}
	r = pid < 0 ? -errno : wait_child(pid);
	if (pid > 0 && r == -EINTR)
		stop_child(pid);
	int end = b->ui.progress(b->ui.ctx, phase, false);
	return r < 0 ? r : end;
}

static int grow(void *ctx)
{
	struct boot *b = ctx;
	char *args[] = {"/usr/sbin/msd-data-partition-grow", NULL};
	return command(b, "Growing data partition", args);
}

static int mount_data(struct boot *b)
{
	char *args[] = {"/bin/mount", "-t", "btrfs", "-o",
		"noatime,nodev,nosuid,compress=zstd:3", "/dev/mapper/msd-data", "/data", NULL};
	int r = command(b, "Mounting data filesystem", args);
	if (r < 0 || (r = health()) < 0)
		return r;
	return b->ui.message(b->ui.ctx,
		"msd-data: /data btrfs noatime,nodev,nosuid,compress=zstd:3\n");
}

static int filesystem(void *ctx)
{
	struct boot *b = ctx;
	char *mkfs[] = {"mkfs.btrfs", "-d", "dup", "-m", "dup",
		"--csum", "xxhash", "/dev/mapper/msd-data", NULL};
	char *dirs[] = {"/bin/mkdir", "-p", "/data/etc", "/data/msd-update", NULL};
	char *sync[] = {"/usr/sbin/msd-syncfs", "/data", NULL};
	int r = command(b, "Creating Btrfs filesystem", mkfs);
	if (r >= 0)
		r = mount_data(b);
	if (r >= 0)
		r = command(b, "Creating data directories", dirs);
	if (r >= 0)
		r = command(b, "Synchronizing data filesystem", sync);
	return r;
}

static int helper(struct boot *b, const struct msd_boot_ops *ops, bool prepare)
{
	int pair[2] = {-1, -1};
	if (prepare && socketpair(AF_UNIX, SOCK_STREAM | SOCK_CLOEXEC, 0, pair))
		return -errno;
	pid_t pid = fork();
	if (!pid) {
		if (prepare) {
			close(pair[0]);
			if ((pair[1] != 3 && dup2(pair[1], 3) < 0) ||
			    fcntl(3, F_SETFD, 0))
				_exit(127);
			if (pair[1] != 3)
				close(pair[1]);
			execl("/usr/sbin/msd-data-unlock", "msd-data-unlock", "prepare",
				"--device", b->device, "--io", b->mode, "--control-fd", "3", (char *)NULL);
		} else {
			execl("/usr/sbin/msd-data-unlock", "msd-data-unlock", "unlock",
				"--device", b->device, "--io", b->mode, (char *)NULL);
		}
		_exit(127);
	}
	int r = pid < 0 ? -errno : 0;
	if (prepare) {
		close(pair[1]);
		if (r >= 0)
			r = msd_boot_control(pair[0], ops);
		close(pair[0]);
	}
	if (pid > 0 && r < 0)
		stop_child(pid);
	else if (pid > 0) {
		r = wait_child(pid);
		if (r == -EINTR)
			stop_child(pid);
	}
	return r;
}

static void lcd_failure(void)
{
	const char *paths[] = {"/dev/console", "/dev/kmsg"};
	const char text[] = "Boot stopped. LCD console unavailable. Safe to power off.\n";
	for (size_t i = 0; i < 2; i++) {
		int fd = open(paths[i], O_WRONLY | O_NONBLOCK | O_CLOEXEC | O_NOCTTY);
		if (fd >= 0) {
			ssize_t ignored = write(fd, text, sizeof(text) - 1);
			(void)ignored;
			close(fd);
		}
	}
}

int main(int argc, char **argv)
{
	if (argc == 2 && !strcmp(argv[1], "health"))
		return health() < 0 ? 1 : 0;
	struct boot b = { .device = "/dev/mmcblk0p7", .tty = -1, .device_fd = -1 };
	if (argc != 3 || strcmp(argv[1], "start") ||
	    (strcmp(argv[2], "product") && strcmp(argv[2], "qemu")))
		return 2;
	b.mode = argv[2];
	if (msd_security_init() < 0 || setenv("PATH", "/usr/sbin:/usr/bin:/sbin:/bin", 1))
		return 1;
	b.tty = open(!strcmp(b.mode, "product") ? "/dev/tty1" : "/dev/ttyAMA1",
		O_RDWR | O_NOCTTY | O_NONBLOCK | O_CLOEXEC);
	if (b.tty < 0) {
		if (!strcmp(b.mode, "product"))
			lcd_failure();
		return 1;
	}
	struct msd_terminal terminal = {0};
	struct msd_secret *secret = msd_secret_alloc();
	int r = -ENOMEM;
	bool prepare = false;
	if (!secret || msd_terminal_open(&terminal, b.tty, -1, secret, &b.ui) < 0)
		goto done;
	b.device_fd = open(b.device, O_RDONLY | O_CLOEXEC);
	if (b.device_fd < 0) {
		r = -errno;
		goto done;
	}
	const struct msd_boot_ops ops = { &b, probe, read_at, scanning, grow, filesystem };
	enum msd_data_state state;
	r = msd_boot_classify(&ops, &state);
	if (r < 0)
		goto done;
	if (state == MSD_DATA_PENDING &&
	    (r = b.ui.message(b.ui.ctx, "Initialization was interrupted. Initialization will restart with a new recovery key. The previous recovery key will no longer work.\n")) < 0)
		goto done;
	prepare = state != MSD_DATA_READY;
	r = helper(&b, &ops, prepare);
	if (r >= 0 && !prepare)
		r = mount_data(&b);
done:
	if (terminal.active && r < 0)
		b.ui.message(b.ui.ctx, "Boot stopped. Safe to power off.\n");
	int restored = msd_terminal_close(&terminal);
	if (r >= 0 && restored < 0 && !prepare)
		r = restored;
	if (b.device_fd >= 0)
		close(b.device_fd);
	close(b.tty);
	msd_secret_free(secret);
	return r < 0 ? 1 : 0;
}
