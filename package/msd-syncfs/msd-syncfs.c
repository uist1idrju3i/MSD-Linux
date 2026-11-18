/* SPDX-License-Identifier: GPL-2.0-only */
#define _GNU_SOURCE
#include <fcntl.h>
#include <stdio.h>
#include <unistd.h>

int main(int argc, char **argv)
{
	int fd, status = 0;

	if (argc != 2) {
		fprintf(stderr, "Usage: msd-syncfs DIRECTORY\n");
		return 2;
	}
	fd = open(argv[1], O_RDONLY | O_DIRECTORY | O_CLOEXEC);
	if (fd < 0) {
		perror(argv[1]);
		return 1;
	}
	if (syncfs(fd) < 0) {
		perror("msd-syncfs: syncfs");
		status = 1;
	}
	if (close(fd) < 0) {
		perror("msd-syncfs: close");
		status = 1;
	}
	return status;
}
