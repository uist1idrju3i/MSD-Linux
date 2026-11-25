/* SPDX-License-Identifier: GPL-2.0-only */
#define _POSIX_C_SOURCE 200809L
#include <fcntl.h>
#include <string.h>
#include <sys/uio.h>
#include <unistd.h>

int main(int argc, char **argv)
{
	char newline = '\n';
	struct iovec message[2];
	int status = 0;

	if (argc < 3)
		return 2;
	message[0].iov_base = argv[1];
	message[0].iov_len = strlen(argv[1]);
	message[1].iov_base = &newline;
	message[1].iov_len = 1;
	for (int i = 2; i < argc; i++) {
		int fd = open(argv[i], O_WRONLY | O_APPEND | O_NONBLOCK | O_NOCTTY | O_CLOEXEC);
		if (fd < 0) {
			status = 1;
			continue;
		}
		if (writev(fd, message, 2) != (ssize_t)(message[0].iov_len + 1))
			status = 1;
		if (close(fd) < 0)
			status = 1;
	}
	return status;
}
