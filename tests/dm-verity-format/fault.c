#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int failing(int fd, const char *operation)
{
	char link[64], path[4096], wanted[64];
	const char *fault = getenv("VERITYFMT_FAIL");
	ssize_t size;

	snprintf(link, sizeof(link), "/proc/self/fd/%d", fd);
	size = readlink(link, path, sizeof(path) - 1);
	if (size < 0 || !fault)
		return 0;
	path[size] = 0;
	snprintf(wanted, sizeof(wanted), "%s-%s",
		 strstr(path, "test.img") ? "image" : "params", operation);
	if (!strstr(path, "test.img") && !strstr(path, "test.env"))
		return 0;
	if (strcmp(fault, wanted))
		return 0;
	errno = EIO;
	return 1;
}

int fsync(int fd)
{
	int (*real_sync)(int) = dlsym(RTLD_NEXT, "fsync");
	return failing(fd, "sync") ? -1 : real_sync(fd);
}

int close(int fd)
{
	int (*real_close)(int) = dlsym(RTLD_NEXT, "close");
	int fail = failing(fd, "close");
	int result = real_close(fd);
	if (fail) {
		errno = EIO;
		return -1;
	}
	return result;
}

int fclose(FILE *stream)
{
	int (*real_close)(FILE *) = dlsym(RTLD_NEXT, "fclose");
	int fail = failing(fileno(stream), "close");
	int result = real_close(stream);
	return fail ? EOF : result;
}

ssize_t pread(int fd, void *buffer, size_t size, off_t offset)
{
	ssize_t (*real_read)(int, void *, size_t, off_t) = dlsym(RTLD_NEXT, "pread");
	return failing(fd, "read") ? 0 : real_read(fd, buffer, size, offset);
}

ssize_t pwrite(int fd, const void *buffer, size_t size, off_t offset)
{
	ssize_t (*real_write)(int, const void *, size_t, off_t) = dlsym(RTLD_NEXT, "pwrite");
	return failing(fd, "write") ? -1 : real_write(fd, buffer, size, offset);
}
