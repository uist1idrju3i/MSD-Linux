/* SPDX-License-Identifier: GPL-2.0-only */
#define _GNU_SOURCE
#include "unlock.h"

#include <errno.h>
#include <stdint.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>

static const char *const blocklist[] = {
	"password", "password1", "qwerty", "qwerty123", "letmein", "welcome",
	"admin", "admin123", "123456", "12345678", "123456789", "111111",
	"000000", "abcdef"
};

static unsigned char upper(unsigned char c)
{
	return c >= 'a' && c <= 'z' ? c - 'a' + 'A' : c;
}

bool msd_pin_valid(const char *pin)
{
	size_t n = strlen(pin);
	if (n < 4 || n > MSD_PIN_MAX)
		return false;
	for (size_t i = 0; i < n; i++)
		if ((unsigned char)pin[i] < 0x20 || (unsigned char)pin[i] > 0x7e)
			return false;
	return true;
}

bool msd_pin_weak(const char *pin)
{
	if (strlen(pin) < 6)
		return true;
	for (size_t i = 0; i < sizeof(blocklist) / sizeof(blocklist[0]); i++) {
		size_t j = 0;
		while (pin[j] && blocklist[i][j] &&
		       upper(pin[j]) == upper(blocklist[i][j]))
			j++;
		if (!pin[j] && !blocklist[i][j])
			return true;
	}
	return false;
}

void msd_base32(const unsigned char raw[20], char out[33])
{
	static const char alphabet[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
	for (size_t i = 0; i < 32; i++) {
		size_t bit = i * 5;
		unsigned value = 0;
		for (size_t j = 0; j < 5; j++)
			value = value * 2 + ((raw[(bit+j)/8] >> (7-(bit+j)%8)) & 1);
		out[i] = alphabet[value];
	}
	out[32] = 0;
}

int msd_recovery_parse(const char *in, char out[33])
{
	size_t len = strlen(in), j = 0;
	char separator = len == 39 ? in[4] : 0;
	explicit_bzero(out, 33);
	if (len != 32 && (len != 39 || (separator != ' ' && separator != '-')))
		return -EINVAL;
	for (size_t i = 0; i < len; i++) {
		if (len == 39 && i % 5 == 4) {
			if (in[i] != separator)
				goto invalid;
			continue;
		}
		unsigned char c = upper(in[i]);
		if (!((c >= 'A' && c <= 'Z') || (c >= '2' && c <= '7')))
			goto invalid;
		out[j++] = c;
	}
	return 0;
invalid:
	explicit_bzero(out, 33);
	return -EINVAL;
}

static int say(struct msd_ui *u, const char *text)
{
	return u->message(u->ctx, text);
}

static int line(struct msd_ui *u, char *out, size_t size)
{
	explicit_bzero(out, size);
	int r = u->line(u->ctx, out, size);
	if (r < 0)
		explicit_bzero(out, size);
	return r;
}

static int confirm(struct msd_ui *u, struct msd_secret *s, const char *prompt)
{
	int r = say(u, prompt);
	if (r >= 0) {
		r = line(u, s->line, sizeof(s->line));
		if (r == -EINVAL)
			r = 0;
		else if (r >= 0)
			r = !strcmp(s->line, "yes");
	}
	explicit_bzero(s->line, sizeof(s->line));
	return r;
}

static int new_pin(struct msd_ui *u, struct msd_secret *s)
{
	int r;
	for (;;) {
		if ((r = say(u, "Set a new PIN (4-64 printable ASCII characters):\n")) < 0)
			return r;
		r = line(u, s->pin, sizeof(s->pin));
		if (r == -EINVAL || (r >= 0 && !msd_pin_valid(s->pin)))
			continue;
		if (r < 0)
			return r;
		if ((r = say(u, "Enter the new PIN again:\n")) < 0)
			return r;
		r = line(u, s->again, sizeof(s->again));
		if (r == -EINVAL)
			continue;
		if (r < 0)
			return r;
		bool equal = !strcmp(s->pin, s->again);
		explicit_bzero(s->again, sizeof(s->again));
		if (!equal) {
			if ((r = say(u, "PINs do not match. Try again.\n")) < 0)
				return r;
			continue;
		}
		if (msd_pin_weak(s->pin))
			return say(u, "Warning: This PIN is weak against offline guessing if the SD card is removed.\n");
		return 0;
	}
}

static int make_recovery(struct msd_ui *u, struct msd_secret *s)
{
	int r = u->random(u->ctx, s->random, sizeof(s->random));
	if (r < 0)
		return r;
	msd_base32(s->random, s->recovery);
	explicit_bzero(s->random, sizeof(s->random));
	if ((r = say(u, "Write down this recovery key on paper and keep it outside the SD card.\n")) < 0 ||
	    (r = u->recovery(u->ctx, s->recovery)) < 0)
		return r;
	for (;;) {
		if ((r = say(u, "Enter the recovery key to check your copy, or an empty line to skip:\n")) < 0)
			return r;
		r = line(u, s->line, sizeof(s->line));
		if (r == -EINVAL)
			continue;
		if (r < 0)
			return r;
		if (!s->line[0]) {
			r = confirm(u, s, "If you copied this key incorrectly, recovery will be impossible.\nSkip verification? Type yes to confirm:\n");
			if (r < 0)
				return r;
			if (r)
				return 0;
			continue;
		}
		r = msd_recovery_parse(s->line, s->again);
		explicit_bzero(s->line, sizeof(s->line));
		bool equal = r == 0 && !strcmp(s->again, s->recovery);
		explicit_bzero(s->again, sizeof(s->again));
		if (equal)
			return 0;
		if ((r = say(u, "Recovery key does not match. Try again.\n")) < 0)
			return r;
	}
}

static int operation(struct msd_backend *b, struct msd_ui *u, enum msd_op op,
		     const char *first, const char *second)
{
	static const char *const phases[] = {
		"Formatting LUKS2", "Adding recovery slot", "Unlocking with PIN",
		"Unlocking with recovery key", "Removing PIN slot", "Setting PIN slot",
		"Saving ready label"
	};
	int r = u->progress(u->ctx, phases[op], true);
	if (r < 0)
		return r == -EPERM ? -EIO : r;
	r = b->operate(b->ctx, op, first, second);
	int end = u->progress(u->ctx, phases[op], false);
	if (op == MSD_READY && r >= 0)
		return r;
	return end < 0 ? (end == -EPERM ? -EIO : end) : r;
}

static int metadata(struct msd_backend *b, struct msd_ui *u, bool ready)
{
	const char *phase = "Checking LUKS2 metadata";
	int r = u->progress(u->ctx, phase, true);
	if (r < 0)
		return r == -EPERM ? -EIO : r;
	r = b->inspect(b->ctx, ready);
	int end = u->progress(u->ctx, phase, false);
	return end < 0 ? (end == -EPERM ? -EIO : end) : r;
}

static int slots(struct msd_backend *b, struct msd_ui *u, bool ready, int expected)
{
	int r = metadata(b, u, ready);
	return r < 0 ? r : r == expected ? 0 : -EINVAL;
}

static int finish(struct msd_backend *b, int r)
{
	if (r < 0)
		b->deactivate(b->ctx);
	return r;
}

int msd_prepare(struct msd_backend *b, struct msd_ui *u, struct msd_secret *s)
{
	int r;
	explicit_bzero(s, sizeof(*s));
	if ((r = new_pin(u, s)) < 0 || (r = make_recovery(u, s)) < 0 ||
	    (r = say(u, "If power is lost, initialization normally restarts on the next boot. If it cannot, boot stops without formatting.\n")) < 0 ||
	    (r = u->checkpoint(u->ctx, MSD_GROW)) < 0 ||
	    (r = operation(b, u, MSD_FORMAT, s->pin, NULL)) < 0 ||
	    (r = slots(b, u, false, 1)) < 0 ||
	    (r = operation(b, u, MSD_ADD_RECOVERY, s->pin, s->recovery)) < 0 ||
	    (r = slots(b, u, false, 3)) < 0 ||
	    (r = operation(b, u, MSD_AUTH_PIN, s->pin, NULL)) < 0 ||
	    (r = u->checkpoint(u->ctx, MSD_FILESYSTEM)) < 0 ||
	    (r = slots(b, u, false, 3)) < 0 ||
	    (r = operation(b, u, MSD_READY, NULL, NULL)) < 0)
		goto done;
	r = 0;
done:
	explicit_bzero(s, sizeof(*s));
	return finish(b, r);
}

static int recover(struct msd_backend *b, struct msd_ui *u, struct msd_secret *s)
{
	int r, mask;
	for (;;) {
		if ((r = say(u, "Enter recovery key:\n")) < 0)
			return r;
		r = line(u, s->line, sizeof(s->line));
		if (r == -EINVAL)
			continue;
		if (r < 0)
			return r;
		r = msd_recovery_parse(s->line, s->recovery);
		explicit_bzero(s->line, sizeof(s->line));
		if (r < 0)
			continue;
		mask = metadata(b, u, true);
		if (mask < 0 || (mask != 2 && mask != 3))
			return mask < 0 ? mask : -EINVAL;
		r = operation(b, u, MSD_AUTH_RECOVERY, s->recovery, NULL);
		if (r == -EPERM)
			continue;
		if (r < 0)
			return r;
		break;
	}
	if ((r = new_pin(u, s)) < 0)
		return r;
	mask = metadata(b, u, true);
	if (mask < 0 || (mask != 2 && mask != 3))
		return mask < 0 ? mask : -EINVAL;
	if (mask == 3 && (r = operation(b, u, MSD_DELETE_PIN, NULL, NULL)) < 0)
		return r;
	if ((r = slots(b, u, true, 2)) < 0 ||
	    (r = operation(b, u, MSD_ADD_PIN, s->recovery, s->pin)) < 0)
		return r;
	return slots(b, u, true, 3);
}

int msd_unlock(struct msd_backend *b, struct msd_ui *u, struct msd_secret *s)
{
	int r;
	explicit_bzero(s, sizeof(*s));
	for (;;) {
		int mask = metadata(b, u, true);
		if (mask < 0 || (mask != 2 && mask != 3)) {
			r = mask < 0 ? mask : -EINVAL;
			break;
		}
		if (mask == 2) {
			r = recover(b, u, s);
			break;
		}
		if ((r = say(u, MSD_FORGOT "Enter PIN:\n")) < 0)
			break;
		r = line(u, s->pin, sizeof(s->pin));
		if (r == -EINVAL)
			continue;
		if (r < 0)
			break;
		if (!s->pin[0]) {
			r = confirm(u, s, "Use the recovery key? Type yes to confirm:\n");
			if (r < 0)
				break;
			if (!r)
				continue;
			r = recover(b, u, s);
			break;
		}
		if (!msd_pin_valid(s->pin))
			continue;
		r = operation(b, u, MSD_AUTH_PIN, s->pin, NULL);
		explicit_bzero(s->pin, sizeof(s->pin));
		if (r >= 0) {
			s->failures = 0;
			r = 0;
			break;
		}
		if (r != -EPERM)
			break;
		if (++s->failures < 10)
			continue;
		if ((r = slots(b, u, true, 3)) < 0 ||
		    (r = operation(b, u, MSD_DELETE_PIN, NULL, NULL)) < 0 ||
		    (r = slots(b, u, true, 2)) < 0)
			break;
		r = recover(b, u, s);
		break;
	}
	explicit_bzero(s, sizeof(*s));
	return finish(b, r);
}

struct msd_secret *msd_secret_alloc(void)
{
	size_t n = (size_t)sysconf(_SC_PAGESIZE);
	if (n < sizeof(struct msd_secret))
		return NULL;
	void *p = mmap(NULL, n, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
	if (p == MAP_FAILED)
		return NULL;
	if (mlock(p, n) || madvise(p, n, MADV_DONTDUMP)) {
		munmap(p, n);
		return NULL;
	}
	return p;
}

void msd_secret_free(struct msd_secret *s)
{
	if (!s)
		return;
	size_t n = (size_t)sysconf(_SC_PAGESIZE);
	explicit_bzero(s, n);
	munlock(s, n);
	munmap(s, n);
}
