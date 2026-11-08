#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <linux/fs.h>
#include <openssl/evp.h>
#include <stdint.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#define W1_FILES 200
#define W1_SIZE 4096
#define W2_UPDATES 100
#define W2_SIZE 2048
#define W3_RECORDS 1000
#define W3_RECORD_SIZE 128
#define W3_SYNC_INTERVAL 50
#define W4_SIZE (32U * 1024U * 1024U)

static int console_fd = -1;

static void report(const char *format, ...)
{
	va_list args;

	if (console_fd < 0)
		console_fd = open("/dev/console", O_WRONLY | O_CLOEXEC);
	if (console_fd < 0)
		console_fd = STDOUT_FILENO;
	va_start(args, format);
	dprintf(console_fd, "msd.fscmp: ");
	vdprintf(console_fd, format, args);
	dprintf(console_fd, "\n");
	va_end(args);
}

static void fail(const char *message)
{
	report("error=%s errno=%d", message, errno);
	exit(1);
}

static void join_path(char *output, size_t size, const char *left,
		      const char *right)
{
	int ret = snprintf(output, size, "%s/%s", left, right);

	if (ret < 0 || (size_t)ret >= size) {
		errno = ENAMETOOLONG;
		fail("path_too_long");
	}
}

static void make_directory(const char *path)
{
	if (mkdir(path, 0755) < 0 && errno != EEXIST)
		fail("mkdir");
}

static void write_all(int fd, const void *buffer, size_t length)
{
	const unsigned char *cursor = buffer;

	while (length) {
		ssize_t written = write(fd, cursor, length);

		if (written < 0) {
			if (errno == EINTR)
				continue;
			fail("write");
		}
		if (!written) {
			errno = EIO;
			fail("short_write");
		}
		cursor += written;
		length -= (size_t)written;
	}
}

static void sha256_bytes(const void *buffer, size_t length, char output[65])
{
	EVP_MD_CTX *context = EVP_MD_CTX_new();
	unsigned char digest[EVP_MAX_MD_SIZE];
	unsigned int digest_length = 0;
	size_t index;

	if (!context)
		fail("EVP_MD_CTX_new");
	if (EVP_DigestInit_ex(context, EVP_sha256(), NULL) != 1 ||
	    EVP_DigestUpdate(context, buffer, length) != 1 ||
	    EVP_DigestFinal_ex(context, digest, &digest_length) != 1) {
		EVP_MD_CTX_free(context);
		errno = EIO;
		fail("sha256");
	}
	EVP_MD_CTX_free(context);
	for (index = 0; index < digest_length; index++)
		snprintf(output + index * 2, 3, "%02x", digest[index]);
	output[digest_length * 2] = '\0';
}

static void sha256_file(const char *path, char output[65])
{
	EVP_MD_CTX *context = EVP_MD_CTX_new();
	unsigned char digest[EVP_MAX_MD_SIZE];
	unsigned char buffer[64 * 1024];
	unsigned int digest_length = 0;
	ssize_t length;
	int fd;
	size_t index;

	if (!context)
		fail("EVP_MD_CTX_new");
	fd = open(path, O_RDONLY | O_CLOEXEC);
	if (fd < 0) {
		EVP_MD_CTX_free(context);
		fail("open_hash_file");
	}
	if (EVP_DigestInit_ex(context, EVP_sha256(), NULL) != 1) {
		close(fd);
		EVP_MD_CTX_free(context);
		errno = EIO;
		fail("sha256_init");
	}
	while ((length = read(fd, buffer, sizeof(buffer))) != 0) {
		if (length < 0) {
			if (errno == EINTR)
				continue;
			close(fd);
			EVP_MD_CTX_free(context);
			fail("read_hash_file");
		}
		if (EVP_DigestUpdate(context, buffer, (size_t)length) != 1) {
			close(fd);
			EVP_MD_CTX_free(context);
			errno = EIO;
			fail("sha256_update");
		}
	}
	close(fd);
	if (EVP_DigestFinal_ex(context, digest, &digest_length) != 1) {
		EVP_MD_CTX_free(context);
		errno = EIO;
		fail("sha256_final");
	}
	EVP_MD_CTX_free(context);
	for (index = 0; index < digest_length; index++)
		snprintf(output + index * 2, 3, "%02x", digest[index]);
	output[digest_length * 2] = '\0';
}

static int mark_log(const char *device, const char *marker)
{
	pid_t child;
	int status;

	if (!device || !*device || !strcmp(device, "-"))
		return 0;
	child = fork();
	if (child < 0)
		return -1;
	if (child == 0) {
		execlp("dmsetup", "dmsetup", "message", device, "0", "mark",
		       marker, (char *)NULL);
		_exit(127);
	}
	while (waitpid(child, &status, 0) < 0) {
		if (errno != EINTR)
			return -1;
	}
	if (!WIFEXITED(status) || WEXITSTATUS(status) != 0) {
		errno = EIO;
		return -1;
	}
	return 0;
}

static void append_manifest(const char *manifest, unsigned int sequence,
			    const char *workload, const char *event,
			    const char *path, const char *hash, int acknowledged,
			    const char *marker)
{
	int fd = open(manifest, O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC, 0600);

	if (fd < 0)
		fail("open_manifest");
	if (dprintf(fd, "%u\t%s\t%s\t%s\t%s\t%d\t%s\n", sequence,
		    workload, event, path, hash, acknowledged, marker) < 0) {
		close(fd);
		fail("write_manifest");
	}
	if (fsync(fd) < 0) {
		close(fd);
		fail("fsync_manifest");
	}
	close(fd);
}

static void record_event(const char *manifest, const char *device,
			 unsigned int *sequence, const char *workload,
			 const char *event, const char *path, const char *hash,
			 int acknowledged, const char *marker)
{
	(*sequence)++;
	append_manifest(manifest, *sequence, workload, event, path, hash,
			acknowledged, marker);
	if (mark_log(device, marker) < 0)
		fail("dm_log_writes_mark");
	report("MANIFEST seq=%u workload=%s event=%s path=%s sha256=%s ack=%d marker=%s",
	       *sequence, workload, event, path, hash, acknowledged, marker);
}

static void prepare_workload_dirs(const char *root, const char *manifest,
				  const char *device, unsigned int *sequence)
{
	static const char *directories[] = {"W1", "W2", "W3", "W4", "T3", "T6"};
	char path[4096];
	int root_fd;
	size_t index;
	const char *marker = "workload-dirs";

	for (index = 0; index < sizeof(directories) / sizeof(directories[0]);
	     index++) {
		join_path(path, sizeof(path), root, directories[index]);
		make_directory(path);
	}
	root_fd = open(root, O_RDONLY | O_DIRECTORY | O_CLOEXEC);
	if (root_fd < 0)
		fail("open_workload_root");
	if (fsync(root_fd) < 0) {
		close(root_fd);
		fail("fsync_workload_root");
	}
	close(root_fd);
	record_event(manifest, device, sequence, "setup", "directories", ".",
		     "-", 0, marker);
}

static void make_payload(unsigned char *buffer, size_t length,
			 unsigned int seed)
{
	size_t index;

	for (index = 0; index < length; index++)
		buffer[index] = (unsigned char)((index * 31U + seed * 17U) & 0xff);
}

static void run_w1(const char *root, const char *manifest, const char *device,
		   unsigned int *sequence, int no_fsync)
{
	unsigned char buffer[W1_SIZE];
	char relative[128], full_path[4096], hash[65], marker[128];
	unsigned int index;
	int root_fd, directory_fd;

	root_fd = open(root, O_RDONLY | O_DIRECTORY | O_CLOEXEC);
	if (root_fd < 0)
		fail("open_workload_root");
	directory_fd = openat(root_fd, "W1",
			      O_RDONLY | O_DIRECTORY | O_CLOEXEC);
	close(root_fd);
	if (directory_fd < 0)
		fail("open_w1_directory");
	for (index = 0; index < W1_FILES; index++) {
		int fd;

		snprintf(relative, sizeof(relative), "W1/file-%03u.dat", index);
		join_path(full_path, sizeof(full_path), root,
			  relative + strlen("W1/"));
		fd = openat(directory_fd, relative + strlen("W1/"),
			    O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0644);
		if (fd < 0)
			fail("open_w1_file");
		make_payload(buffer, sizeof(buffer), index);
		write_all(fd, buffer, sizeof(buffer));
		if (!no_fsync && fsync(fd) < 0) {
			close(fd);
			fail("fsync_w1_file");
		}
		sha256_bytes(buffer, sizeof(buffer), hash);
		snprintf(marker, sizeof(marker), "w1-file-%03u", index);
		record_event(manifest, device, sequence, "W1", "file", relative,
			     hash, no_fsync ? 0 : 1, marker);
		if (close(fd) < 0)
			fail("close_w1_file");
	}
	if (!no_fsync) {
		if (fsync(directory_fd) < 0)
			fail("fsync_w1_directory");
		record_event(manifest, device, sequence, "W1", "directory", "W1",
			     "-", 0, "w1-directory");
	}
	close(directory_fd);
	report("W1 files=%d bytes_per_file=%d fsync=%s", W1_FILES, W1_SIZE,
	       no_fsync ? "omitted" : "each");
}

static void run_w2(const char *root, const char *manifest, const char *device,
		   unsigned int *sequence, unsigned int cycle)
{
	unsigned char buffer[W2_SIZE];
	char relative[128], hash[65], marker[128];
	unsigned int index;
	int root_fd, directory_fd;

	root_fd = open(root, O_RDONLY | O_DIRECTORY | O_CLOEXEC);
	if (root_fd < 0)
		fail("open_workload_root");
	directory_fd = openat(root_fd, "W2",
			      O_RDONLY | O_DIRECTORY | O_CLOEXEC);
	close(root_fd);
	if (directory_fd < 0)
		fail("open_w2_directory");
	for (index = 0; index < W2_UPDATES; index++) {
		int fd;

		make_payload(buffer, sizeof(buffer), cycle * W2_UPDATES + index);
		fd = openat(directory_fd, "target.tmp",
			    O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0644);
		if (fd < 0)
			fail("open_w2_temp");
		write_all(fd, buffer, sizeof(buffer));
		if (fsync(fd) < 0) {
			close(fd);
			fail("fsync_w2_temp");
		}
		snprintf(marker, sizeof(marker), "w2-temp-%03u-%03u", cycle, index);
		record_event(manifest, device, sequence, "W2", "temp_fsync",
			     "W2/target.tmp", "-", 0, marker);
		if (close(fd) < 0)
			fail("close_w2_temp");
		if (renameat(directory_fd, "target.tmp", directory_fd,
			     "target.dat") < 0)
			fail("rename_w2_target");
		if (fsync(directory_fd) < 0)
			fail("fsync_w2_directory");
		sha256_bytes(buffer, sizeof(buffer), hash);
		snprintf(relative, sizeof(relative), "W2/target.dat");
		snprintf(marker, sizeof(marker), "w2-update-%03u-%03u", cycle,
			 index);
		record_event(manifest, device, sequence, "W2", "atomic_update",
			     relative, hash, 1, marker);
	}
	close(directory_fd);
	report("W2 updates=%d bytes_per_update=%d cycle=%u", W2_UPDATES, W2_SIZE,
	       cycle);
}

static void run_w3(const char *root, const char *manifest, const char *device,
		   unsigned int *sequence, unsigned int cycle)
{
	char full_path[4096], hash[65], marker[128], record[W3_RECORD_SIZE];
	unsigned int index;
	int fd;

	join_path(full_path, sizeof(full_path), root, "W3/append.log");
	fd = open(full_path, O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC, 0644);
	if (fd < 0)
		fail("open_w3_file");
	for (index = 1; index <= W3_RECORDS; index++) {
		int length;

		memset(record, ' ', sizeof(record));
		length = snprintf(record, sizeof(record), "%010u %010u\n",
				  cycle, index);
		if (length < 0 || (size_t)length >= sizeof(record)) {
			close(fd);
			errno = EOVERFLOW;
			fail("format_w3_record");
		}
		write_all(fd, record, sizeof(record));
		if (index % W3_SYNC_INTERVAL == 0) {
			if (fsync(fd) < 0) {
				close(fd);
				fail("fsync_w3_file");
			}
			sha256_file(full_path, hash);
			snprintf(marker, sizeof(marker), "w3-record-%03u-%04u",
				 cycle, index);
			record_event(manifest, device, sequence, "W3", "batch_fsync",
				     "W3/append.log", hash, 1, marker);
		}
	}
	if (close(fd) < 0)
		fail("close_w3_file");
	report("W3 records=%d bytes_per_record=%d fsync_every=%d cycle=%u",
	       W3_RECORDS, W3_RECORD_SIZE, W3_SYNC_INTERVAL, cycle);
}

static void run_w4(const char *root, const char *manifest, const char *device,
		   unsigned int *sequence, unsigned int cycle)
{
	const size_t chunk_size = 1024U * 1024U;
	unsigned char *buffer = malloc(chunk_size);
	char full_path[4096], hash[65], marker[128];
	size_t remaining = W4_SIZE;
	int fd;

	if (!buffer)
		fail("malloc_w4");
	make_payload(buffer, chunk_size, cycle + 4000);
	join_path(full_path, sizeof(full_path), root, "W4/large.bin");
	fd = open(full_path, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0644);
	if (fd < 0) {
		free(buffer);
		fail("open_w4_file");
	}
	while (remaining) {
		write_all(fd, buffer, chunk_size);
		remaining -= chunk_size;
	}
	if (fsync(fd) < 0) {
		close(fd);
		free(buffer);
		fail("fsync_w4_file");
	}
	close(fd);
	free(buffer);
	sha256_file(full_path, hash);
	snprintf(marker, sizeof(marker), "w4-fsync-%03u", cycle);
	record_event(manifest, device, sequence, "W4", "file_fsync",
		     "W4/large.bin", hash, 1, marker);
	report("W4 bytes=%u cycle=%u", W4_SIZE, cycle);
}

static void run_workload(const char *root, const char *manifest,
			 const char *device, int no_fsync, int repeat)
{
	unsigned int sequence = 0;
	unsigned int cycle = 0;
	int manifest_fd;

	manifest_fd = open(manifest, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC,
			   0600);
	if (manifest_fd < 0)
		fail("create_manifest");
	if (dprintf(manifest_fd,
		    "seq\tworkload\tevent\tpath\tsha256\tack\tmarker\n") < 0 ||
	    fsync(manifest_fd) < 0) {
		close(manifest_fd);
		fail("initialize_manifest");
	}
	close(manifest_fd);
	prepare_workload_dirs(root, manifest, device, &sequence);
	report("workload-start mode=%s", repeat ? "repeat" :
	       (no_fsync ? "negative-control" : "once"));
	do {
		run_w1(root, manifest, device, &sequence, no_fsync);
		if (no_fsync)
			break;
		run_w2(root, manifest, device, &sequence, cycle);
		run_w3(root, manifest, device, &sequence, cycle);
		run_w4(root, manifest, device, &sequence, cycle);
		cycle++;
	} while (repeat);
	report("workload-finished cycles=%u", cycle);
}

static void run_t3(const char *root, const char *manifest,
		   const char *device)
{
	char full_path[4096], record[64], hash[65], marker[128];
	unsigned int sequence = 0, manifest_sequence = 0;
	int fd, root_fd, manifest_fd;
	struct stat manifest_stat;

	make_directory(root);
	join_path(full_path, sizeof(full_path), root, "T3");
	make_directory(full_path);
	root_fd = open(root, O_RDONLY | O_DIRECTORY | O_CLOEXEC);
	if (root_fd < 0)
		fail("open_t3_root");
	if (fsync(root_fd) < 0) {
		close(root_fd);
		fail("fsync_t3_root");
	}
	close(root_fd);
	manifest_fd = open(manifest, O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC,
			   0600);
	if (manifest_fd < 0)
		fail("open_t3_manifest");
	if (fstat(manifest_fd, &manifest_stat) < 0) {
		close(manifest_fd);
		fail("stat_t3_manifest");
	}
	if (manifest_stat.st_size == 0 &&
	    dprintf(manifest_fd,
		    "seq\tworkload\tevent\tpath\tsha256\tack\tmarker\n") < 0) {
		close(manifest_fd);
		fail("initialize_t3_manifest");
	}
	if (fsync(manifest_fd) < 0) {
		close(manifest_fd);
		fail("fsync_t3_manifest");
	}
	close(manifest_fd);
	record_event(manifest, device, &manifest_sequence, "setup",
		     "directory", ".", "-", 0, "t3-directory");

	join_path(full_path, sizeof(full_path), root, "T3/records.log");
	fd = open(full_path, O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC, 0644);
	if (fd < 0)
		fail("open_t3_file");
	report("writer-start");
	for (;;) {
		struct timespec now, delay = {.tv_sec = 1, .tv_nsec = 0};
		int length;

		sequence++;
		if (clock_gettime(CLOCK_MONOTONIC, &now) < 0)
			fail("clock_gettime");
		memset(record, ' ', sizeof(record));
		length = snprintf(record, sizeof(record), "%010u %020llu\n",
				  sequence,
				  (unsigned long long)now.tv_sec * 1000000000ULL +
					  (unsigned long long)now.tv_nsec);
		if (length < 0 || (size_t)length >= sizeof(record)) {
			errno = EOVERFLOW;
			fail("format_t3_record");
		}
		write_all(fd, record, sizeof(record));
		report("T3_SEQ seq=%u monotonic_ns=%llu", sequence,
		       (unsigned long long)now.tv_sec * 1000000000ULL +
			       (unsigned long long)now.tv_nsec);
		if (sequence % 10 == 0) {
			if (fsync(fd) < 0)
				fail("fsync_t3_file");
			sha256_file(full_path, hash);
			snprintf(marker, sizeof(marker), "t3-fsync-%010u", sequence);
			record_event(manifest, device, &manifest_sequence, "T3",
				     "fsync_record", "T3/records.log", hash, 1,
				     marker);
			report("T3_FSYNC_ACK seq=%u", sequence);
		}
		while (nanosleep(&delay, &delay) < 0 && errno == EINTR)
			;
	}
}

static void make_known_file(const char *root, const char *manifest,
			    const char *device)
{
	unsigned char buffer[4096];
	char path[4096], hash[65];
	unsigned int sequence = 0;
	int fd, root_fd, directory_fd, manifest_fd;
	struct stat manifest_stat;

	make_directory(root);
	join_path(path, sizeof(path), root, "T6");
	make_directory(path);
	manifest_fd = open(manifest, O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC,
			   0600);
	if (manifest_fd < 0)
		fail("open_known_manifest");
	if (fstat(manifest_fd, &manifest_stat) < 0) {
		close(manifest_fd);
		fail("stat_known_manifest");
	}
	if (manifest_stat.st_size == 0 &&
	    dprintf(manifest_fd,
		    "seq\tworkload\tevent\tpath\tsha256\tack\tmarker\n") < 0) {
		close(manifest_fd);
		fail("initialize_known_manifest");
	}
	if (fsync(manifest_fd) < 0) {
		close(manifest_fd);
		fail("fsync_known_manifest");
	}
	close(manifest_fd);
	make_payload(buffer, sizeof(buffer), 0x5a);
	join_path(path, sizeof(path), root, "T6/known.bin");
	fd = open(path, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0644);
	if (fd < 0)
		fail("open_known_file");
	write_all(fd, buffer, sizeof(buffer));
	if (fsync(fd) < 0) {
		close(fd);
		fail("fsync_known_file");
	}
	close(fd);
	sha256_bytes(buffer, sizeof(buffer), hash);
	root_fd = open(root, O_RDONLY | O_DIRECTORY | O_CLOEXEC);
	if (root_fd < 0)
		fail("open_known_root");
	directory_fd = openat(root_fd, "T6",
			      O_RDONLY | O_DIRECTORY | O_CLOEXEC);
	close(root_fd);
	if (directory_fd < 0)
		fail("open_known_directory");
	if (fsync(directory_fd) < 0) {
		close(directory_fd);
		fail("fsync_known_directory");
	}
	close(directory_fd);
	record_event(manifest, device, &sequence, "T6", "known_file",
		     "T6/known.bin", hash, 1, "t6-known-file");
	report("T6_KNOWN sha256=%s", hash);
}

static void run_odirect(const char *device)
{
	const size_t length = 1024U * 1024U;
	void *buffer = NULL;
	int fd;

	if (posix_memalign(&buffer, 4096, length) != 0) {
		errno = ENOMEM;
		fail("posix_memalign");
	}
	memset(buffer, 0xa5, length);
	fd = open(device, O_WRONLY | O_DIRECT | O_SYNC | O_CLOEXEC);
	if (fd < 0) {
		free(buffer);
		fail("open_odirect_device");
	}
	if (write(fd, buffer, length) != (ssize_t)length) {
		close(fd);
		free(buffer);
		fail("write_odirect_device");
	}
	if (fsync(fd) < 0) {
		close(fd);
		free(buffer);
		fail("fsync_odirect_device");
	}
	close(fd);
	free(buffer);
	report("ODIRECT bytes=%zu", length);
}

static int run_timed_command(char **arguments)
{
	struct timespec start, end;
	pid_t child;
	int status;
	long long elapsed;

	if (!arguments[0]) {
		errno = EINVAL;
		fail("timer_missing_command");
	}
	if (clock_gettime(CLOCK_MONOTONIC, &start) < 0)
		fail("timer_start");
	child = fork();
	if (child < 0)
		fail("timer_fork");
	if (child == 0) {
		execvp(arguments[0], arguments);
		_exit(127);
	}
	while (waitpid(child, &status, 0) < 0) {
		if (errno != EINTR)
			fail("timer_waitpid");
	}
	if (clock_gettime(CLOCK_MONOTONIC, &end) < 0)
		fail("timer_end");
	elapsed = (long long)(end.tv_sec - start.tv_sec) * 1000000000LL +
		  (long long)end.tv_nsec - start.tv_nsec;
	report("TIMER command=%s elapsed_ns=%lld status=%d", arguments[0],
	       elapsed, WIFEXITED(status) ? WEXITSTATUS(status) : 128);
	if (WIFEXITED(status))
		return WEXITSTATUS(status);
	return 128;
}

static void verify_t3(const char *root, const char *manifest)
{
	char path[4096], record[65], line[512], marker[128];
	unsigned char present[100001] = {0};
	unsigned int last = 0;
	unsigned int fsync_lost = 0;
	FILE *file;
	int fd;

	join_path(path, sizeof(path), root, "T3/records.log");
	fd = open(path, O_RDONLY | O_CLOEXEC);
	if (fd < 0) {
		report("T3_DISK last_seq=0 open_errno=%d", errno);
		return;
	}
	while (read(fd, record, 64) == 64) {
		unsigned int current;

		record[64] = '\0';
		if (sscanf(record, "%10u", &current) == 1) {
			if (current > last)
				last = current;
			if (current < sizeof(present))
				present[current] = 1;
		}
	}
	close(fd);
	file = fopen(manifest, "r");
	if (!file)
		fail("open_t3_manifest_for_verify");
	while (fgets(line, sizeof(line), file)) {
		unsigned int sequence, acknowledged, t3_sequence;
		char workload[32], event[32], relative[256], hash[65];

		if (sscanf(line, "%u\t%31[^\t]\t%31[^\t]\t%255[^\t]\t%64[^\t]\t%u\t%127s",
			   &sequence, workload, event, relative, hash,
			   &acknowledged, marker) == 7 &&
		    !strcmp(workload, "T3") && acknowledged &&
		    sscanf(marker, "t3-fsync-%u", &t3_sequence) == 1 &&
		    t3_sequence < sizeof(present) && !present[t3_sequence])
				fsync_lost++;
	}
	fclose(file);
	report("T3_DISK last_seq=%u", last);
	report("T3_FSYNC_LOST count=%u", fsync_lost);
}

static int command_timer(int argc, char **argv)
{
	(void)argc;
	return run_timed_command(&argv[2]);
}

static int read_check(const char *path, const char *expected)
{
	EVP_MD_CTX *context = EVP_MD_CTX_new();
	unsigned char digest[EVP_MAX_MD_SIZE];
	unsigned char buffer[64 * 1024];
	char actual[65];
	unsigned int digest_length = 0;
	ssize_t length;
	size_t index;
	int fd;

	if (!context) {
		report("READCHECK result=error reason=digest_context");
		return 4;
	}
	fd = open(path, O_RDONLY | O_CLOEXEC);
	if (fd < 0) {
		int error = errno;

		EVP_MD_CTX_free(context);
		report("READCHECK result=%s errno=%d",
		       error == EIO ? "eio" : "missing", error);
		return error == EIO ? 3 : 4;
	}
	if (EVP_DigestInit_ex(context, EVP_sha256(), NULL) != 1) {
		close(fd);
		EVP_MD_CTX_free(context);
		report("READCHECK result=error reason=digest_init");
		return 4;
	}
	while ((length = read(fd, buffer, sizeof(buffer))) != 0) {
		if (length < 0) {
			int error = errno;

			if (error == EINTR)
				continue;
			close(fd);
			EVP_MD_CTX_free(context);
			report("READCHECK result=%s errno=%d",
			       error == EIO ? "eio" : "error", error);
			return error == EIO ? 3 : 4;
		}
		if (EVP_DigestUpdate(context, buffer, (size_t)length) != 1) {
			close(fd);
			EVP_MD_CTX_free(context);
			report("READCHECK result=error reason=digest_update");
			return 4;
		}
	}
	close(fd);
	if (EVP_DigestFinal_ex(context, digest, &digest_length) != 1) {
		EVP_MD_CTX_free(context);
		report("READCHECK result=error reason=digest_final");
		return 4;
	}
	EVP_MD_CTX_free(context);
	for (index = 0; index < digest_length; index++)
		snprintf(actual + index * 2, 3, "%02x", digest[index]);
	actual[digest_length * 2] = '\0';
	if (!strcmp(actual, expected)) {
		report("READCHECK result=ok sha256=%s", actual);
		return 0;
	}
	report("READCHECK result=wrong expected=%s actual=%s", expected, actual);
	return 2;
}

int main(int argc, char **argv)
{
	if (argc < 2) {
		fprintf(stderr, "usage: fs-compare-workload command ...\n");
		return 2;
	}
	if (!strcmp(argv[1], "timer"))
		return command_timer(argc, argv);
	if (!strcmp(argv[1], "odirect") && argc == 3) {
		run_odirect(argv[2]);
		return 0;
	}
	if (!strcmp(argv[1], "workload") && argc >= 5) {
		int no_fsync = 0, repeat = 0;
		int index;

		for (index = 5; index < argc; index++) {
			if (!strcmp(argv[index], "--no-fsync"))
				no_fsync = 1;
			else if (!strcmp(argv[index], "--repeat"))
				repeat = 1;
			else {
				fprintf(stderr, "unknown workload option: %s\n",
					argv[index]);
				return 2;
			}
		}
		run_workload(argv[2], argv[3], argv[4], no_fsync, repeat);
		return 0;
	}
	if (!strcmp(argv[1], "t3") && argc == 5) {
		run_t3(argv[2], argv[3], argv[4]);
		return 0;
	}
	if (!strcmp(argv[1], "known") && argc == 5) {
		make_known_file(argv[2], argv[3], argv[4]);
		return 0;
	}
	if (!strcmp(argv[1], "verify-t3") && argc == 4) {
		verify_t3(argv[2], argv[3]);
		return 0;
	}
	if (!strcmp(argv[1], "readcheck") && argc == 4)
		return read_check(argv[2], argv[3]);
	fprintf(stderr, "invalid command arguments\n");
	return 2;
}
