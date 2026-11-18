#define _GNU_SOURCE
#include <errno.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int __real_close(int fd);

int __wrap_syncfs(int fd)
{
	const char *fault = getenv("SYNCFS_TEST_FAULT");
	(void)fd;
	if (fault && strcmp(fault, "syncfs") == 0) {
		errno = EIO;
		return -1;
	}
	return 0;
}

int __wrap_close(int fd)
{
	const char *fault = getenv("SYNCFS_TEST_FAULT");
	int status = __real_close(fd);
	if (fault && strcmp(fault, "close") == 0) {
		errno = EIO;
		return -1;
	}
	return status;
}
