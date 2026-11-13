#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void)
{
	FILE *file = fopen("/proc/meminfo", "r");
	char line[256];
	unsigned long available = 0;
	if (!file)
		return 1;
	while (fgets(line, sizeof(line), file))
		if (sscanf(line, "MemAvailable: %lu kB", &available) == 1)
			break;
	fclose(file);
	if (!available)
		return 1;
	size_t size = (available + 32768) * 1024;
	unsigned char *data = malloc(size);
	if (!data)
		return 1;
	for (size_t offset = 0; offset + 4096 <= size; offset += 4096) {
		memset(data + offset, 0xa5, 4096);
		memcpy(data + offset, &offset, sizeof(offset));
		__asm__ volatile ("" : : "r" (data) : "memory");
	}
	file = fopen("/proc/swaps", "r");
	if (!file)
		return 1;
	unsigned long used = 0;
	while (fgets(line, sizeof(line), file)) {
		char device[128], type[32];
		unsigned long total, current;
		int priority;
		if (sscanf(line, "%127s %31s %lu %lu %d",
			   device, type, &total, &current, &priority) == 5 &&
		    strcmp(device, "/dev/zram0") == 0)
			used = current;
	}
	fclose(file);
	printf("MSDLOAD available_kib=%lu bytes=%zu swap_used_kib=%lu\n",
	       available, size, used);
	fflush(stdout);
	free(data);
	return used ? 0 : 1;
}
