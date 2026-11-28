/* SPDX-License-Identifier: GPL-2.0-only */
#define _GNU_SOURCE
#include "unlock.h"

#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>

struct input { const char *text; int error; };
struct fake {
	struct input input[128];
	unsigned count, next, inspect_count, inspect_fail_at;
	int inspect_error, mask;
	bool ready, bad_pin, delete_noop, mapped;
	int deactivations, deactivate_error, ready_error;
	unsigned bad_recovery;
	int ops[128], used, fail_at, failure, auth_success;
	int checkpoints, checkpoint_fail, random_error, message_error, display_error;
	int message_fail_at, messages;
	int progress_error, progress_calls, progress_fail_at;
	char output[32768];
};

static void init(struct fake *f)
{
	memset(f, 0, sizeof(*f));
	f->mask = 3;
	f->ready = true;
	f->checkpoint_fail = -1;
	f->auth_success = 1;
	f->failure = -EIO;
}

static void input(struct fake *f, const char *text)
{
	assert(f->count < 128);
	f->input[f->count++].text = text;
}

static void input_error(struct fake *f, int error)
{
	f->input[f->count++].error = error;
}

static int read_line(void *ctx, char *out, size_t cap)
{
	struct fake *f = ctx;
	if (f->next == f->count)
		return -ENODATA;
	struct input *in = &f->input[f->next++];
	if (in->error)
		return in->error;
	if (strlen(in->text) >= cap)
		return -EINVAL;
	memcpy(out, in->text, strlen(in->text)+1);
	return (int)strlen(out);
}

static int message(void *ctx, const char *text)
{
	struct fake *f = ctx;
	f->messages++;
	if (f->message_error && (!f->message_fail_at || f->messages == f->message_fail_at))
		return f->message_error;
	assert(strlen(f->output) + strlen(text) < sizeof(f->output));
	strcat(f->output, text);
	return 0;
}

static int display(void *ctx, const char *key)
{
	struct fake *f = ctx;
	assert(!strcmp(key, "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"));
	return f->display_error;
}

static int random_bytes(void *ctx, unsigned char *out, size_t len)
{
	struct fake *f = ctx;
	assert(len == 20);
	memset(out, 0, len);
	return f->random_error;
}

static int checkpoint(void *ctx, enum msd_checkpoint step)
{
	struct fake *f = ctx;
	assert((int)step == f->checkpoints++);
	if (step == MSD_GROW)
		assert(f->used == 0);
	else
		assert(f->used == 3 && f->mask == 3);
	return (int)step == f->checkpoint_fail ? -EIO : 0;
}

static int progress(void *ctx, const char *phase, bool start)
{
	struct fake *f = ctx;
	assert(phase && *phase);
	assert(start == (f->progress_calls++ % 2 == 0));
	return !f->progress_fail_at || f->progress_calls == f->progress_fail_at ? f->progress_error : 0;
}

static int inspect(void *ctx, bool ready)
{
	struct fake *f = ctx;
	assert(f->progress_calls % 2 == 1);
	if (++f->inspect_count == f->inspect_fail_at)
		return f->inspect_error;
	if (f->ready != ready)
		return -EINVAL;
	return f->mask;
}

static int operate(void *ctx, enum msd_op op, const char *a, const char *b)
{
	struct fake *f = ctx;
	assert(f->used < 128);
	f->ops[f->used++] = op;
	if (f->used == f->fail_at)
		return f->failure;
	switch (op) {
	case MSD_FORMAT:
		assert(msd_pin_valid(a) && !b);
		f->mask = 1;
		f->ready = false;
		return 0;
	case MSD_ADD_RECOVERY:
		assert(msd_pin_valid(a) && strlen(b) == 32 && f->mask == 1);
		f->mask = 3;
		return 1;
	case MSD_AUTH_PIN:
		assert(msd_pin_valid(a) && !b && (f->mask & 1));
		if (f->bad_pin)
			return -EPERM;
		if (f->mapped)
			return -EEXIST;
		f->mapped = true;
		return f->auth_success;
	case MSD_AUTH_RECOVERY:
		assert(strlen(a) == 32 && !b && (f->mask & 2));
		if (f->bad_recovery) {
			f->bad_recovery--;
			return -EPERM;
		}
		if (f->mapped)
			return -EEXIST;
		f->mapped = true;
		return f->auth_success;
	case MSD_DELETE_PIN:
		assert(f->mask == 3 && !a && !b);
		if (!f->delete_noop)
			f->mask = 2;
		return 0;
	case MSD_ADD_PIN:
		assert(strlen(a) == 32 && msd_pin_valid(b) && f->mask == 2);
		f->mask = 3;
		return 0;
	case MSD_READY:
		assert(f->mask == 3 && !f->ready && !a && !b);
		f->ready = true;
		return f->ready_error;
	}
	assert(0);
	return -EINVAL;
}

static int deactivate(void *ctx)
{
	struct fake *f = ctx;
	f->deactivations++;
	if (f->deactivate_error)
		return f->deactivate_error;
	f->mapped = false;
	return 0;
}

static int run(struct fake *f, bool prepare)
{
	struct msd_secret *s = msd_secret_alloc();
	assert(s);
	memset(s, 0xa5, sizeof(*s));
	struct msd_backend b = {f, inspect, operate, deactivate};
	struct msd_ui u = {f, message, read_line, display, random_bytes, checkpoint, progress};
	int r = prepare ? msd_prepare(&b, &u, s) : msd_unlock(&b, &u, s);
	if (r < 0 && !f->deactivate_error)
		assert(!f->mapped);
	for (size_t i = 0; i < sizeof(*s); i++)
		assert(((unsigned char *)s)[i] == 0);
	msd_secret_free(s);
	assert(!strstr(f->output, "Long safe PIN 99!"));
	assert(!strstr(f->output, "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"));
	return r;
}

static void prepare_input(struct fake *f)
{
	input(f, "Long safe PIN 99!");
	input(f, "Long safe PIN 99!");
	input(f, "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA");
}

static void recovery_input(struct fake *f)
{
	input(f, "aaaa-aaaa-aaaa-aaaa-aaaa-aaaa-aaaa-aaaa");
	input(f, "Long safe PIN 99!");
	input(f, "Long safe PIN 99!");
}

static void validation(void)
{
	assert(!msd_pin_valid("123") && msd_pin_valid("1234"));
	char pin[66];
	memset(pin, 'x', 65); pin[65] = 0;
	assert(!msd_pin_valid(pin)); pin[64] = 0;
	assert(msd_pin_valid(pin));
	assert(msd_pin_valid("    ") && msd_pin_valid("  ab  "));
	for (int c = 0x20; c <= 0x7e; c++) {
		char all[] = "abcd";
		all[0] = (char)c;
		assert(msd_pin_valid(all));
	}
	for (int c = 1; c <= 255; c++) {
		if (c >= 0x20 && c <= 0x7e)
			continue;
		char bad[] = "abcd"; bad[1] = (char)c;
		assert(!msd_pin_valid(bad));
	}
	assert(msd_pin_weak("1234") && msd_pin_weak("PassWORD"));
	assert(msd_pin_weak("qwerty123") && !msd_pin_weak("Long safe PIN 99!"));
	unsigned char raw[20] = {0};
	char key[33], parsed[33];
	msd_base32(raw, key);
	assert(!strcmp(key, "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"));
	memset(raw, 255, sizeof(raw)); msd_base32(raw, key);
	assert(!strcmp(key, "77777777777777777777777777777777"));
	assert(!msd_recovery_parse("abcd-efgh-ijkl-mnop-qrst-uvwx-yz23-4567", parsed));
	assert(!strcmp(parsed, "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"));
	assert(!msd_recovery_parse("abcd efgh ijkl mnop qrst uvwx yz23 4567", parsed));
	const char *invalid[] = {"", "abcd", "ABCDEFGHIJKLMNOPQRSTUVWXYZ234560",
		"ABCDEFGHIJKLMNOPQRSTUVWXYZ234567 ", " abcd efgh ijkl mnop qrst uvwx yz23 4567",
		"abcd-efgh ijkl-mnop-qrst-uvwx-yz23-4567", "abcd_efgh_ijkl_mnop_qrst_uvwx_yz23_4567"};
	for (size_t i = 0; i < sizeof(invalid)/sizeof(invalid[0]); i++) {
		assert(msd_recovery_parse(invalid[i], parsed) == -EINVAL);
		for (size_t j = 0; j < sizeof(parsed); j++) assert(!parsed[j]);
	}
}

static void initialization(void)
{
	struct fake f;
	init(&f); prepare_input(&f);
	assert(run(&f, true) == 0 && f.ready && f.used == 4);
	assert(f.ops[0] == MSD_FORMAT && f.ops[1] == MSD_ADD_RECOVERY &&
	       f.ops[2] == MSD_AUTH_PIN && f.ops[3] == MSD_READY);
	for (int at = 1; at <= 4; at++) {
		init(&f); prepare_input(&f); f.fail_at = at;
		assert(run(&f, true) == -EIO && f.used == at);
	}
	for (int at = 0; at < 2; at++) {
		init(&f); prepare_input(&f); f.checkpoint_fail = at;
		assert(run(&f, true) == -EIO && f.used == (at == 0 ? 0 : 3));
	}
	for (int at = 1; at <= 4; at++) {
		init(&f); prepare_input(&f); f.inspect_fail_at = at; f.inspect_error = -EIO;
		assert(run(&f, true) == (at == 4 ? 0 : -EIO));
		assert(f.ready == (at == 4));
	}
	for (int at = 1; at <= 14; at++) {
		init(&f); prepare_input(&f);
		f.ready = false;
		f.progress_fail_at = at; f.progress_error = -EINTR;
		assert(run(&f, true) == (at == 14 ? 0 : -EINTR));
		assert(f.ready == (at == 14));
	}
	init(&f); prepare_input(&f);
	assert(run(&f, true) == 0 && f.inspect_count == 3);
	assert(f.ops[f.used - 1] == MSD_READY);
	const int ready_errors[] = {-EIO, -ENOSPC};
	for (size_t i = 0; i < sizeof(ready_errors)/sizeof(ready_errors[0]); i++) {
		for (int busy = 0; busy < 2; busy++) {
			init(&f); prepare_input(&f); f.ready_error = ready_errors[i];
			f.deactivate_error = busy ? -EBUSY : 0;
			assert(run(&f, true) == ready_errors[i] && f.ready && f.mask == 3);
			assert(f.used == 4 && f.checkpoints == 2 && f.deactivations == 1);
			assert(f.mapped == (busy != 0));
		}
	}
	init(&f); prepare_input(&f); f.fail_at = 4; f.deactivate_error = -EBUSY;
	assert(run(&f, true) == -EIO && f.checkpoints == 2 && !f.ready);
	assert(f.deactivations == 1 && f.mapped);
	init(&f); prepare_input(&f); f.progress_fail_at = 13;
	f.progress_error = -EINTR; f.deactivate_error = -EBUSY;
	assert(run(&f, true) == -EINTR && f.checkpoints == 2 && !f.ready);
	assert(f.deactivations == 1 && f.mapped);
	init(&f); prepare_input(&f); f.random_error = -EIO;
	assert(run(&f, true) == -EIO && f.used == 0);
	init(&f); prepare_input(&f); f.display_error = -EIO;
	assert(run(&f, true) == -EIO && f.used == 0);
	init(&f); prepare_input(&f); f.message_error = -EIO;
	assert(run(&f, true) == -EIO && f.used == 0);
	init(&f);
	input(&f, "bad"); input(&f, "1234"); input(&f, "1235");
	input(&f, "1234"); input(&f, "1234");
	input(&f, "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB");
	input(&f, ""); input(&f, "no");
	input(&f, ""); input(&f, "yes");
	assert(run(&f, true) == 0 && f.next == f.count);
	assert(strstr(f.output, "PINs do not match") && strstr(f.output, "offline guessing"));
	assert(strstr(f.output, "recovery will be impossible"));
	for (int n = 0; n < 3; n++) {
		init(&f);
		for (int i = 0; i < n; i++) input(&f, "1234");
		input_error(&f, -EINTR);
		assert(run(&f, true) == -EINTR && f.used == 0);
	}
}

static void authentication(void)
{
	struct fake f;
	for (int success = 0; success <= 2; success++) {
		init(&f); f.auth_success = success; input(&f, "Long safe PIN 99!");
		assert(run(&f, false) == 0 && f.used == 1);
	}
	int failures[] = {-EIO, -ENOMEM, -EINVAL, -ENODEV, -EINTR, -EACCES};
	for (size_t i = 0; i < sizeof(failures)/sizeof(failures[0]); i++) {
		init(&f); input(&f, "1234"); f.fail_at = 1; f.failure = failures[i];
		assert(run(&f, false) == failures[i] && f.used == 1 && f.mask == 3);
	}
	init(&f); input(&f, "1234"); f.inspect_fail_at = 1; f.inspect_error = -EPERM;
	assert(run(&f, false) == -EPERM && f.used == 0);
	init(&f); input(&f, "1234"); f.progress_error = -EPERM;
	assert(run(&f, false) == -EIO && f.used == 0);
	for (int mask = 0; mask <= 7; mask++) {
		if (mask == 2 || mask == 3) continue;
		init(&f); f.mask = mask;
		assert(run(&f, false) == -EINVAL && f.used == 0);
	}
	init(&f); f.ready = false; input(&f, "1234");
	assert(run(&f, false) == -EINVAL && f.used == 0);
	for (int n = 0; n <= 10; n++) {
		init(&f); f.bad_pin = true;
		for (int i = 0; i < n; i++) input(&f, "1234");
		assert(run(&f, false) == -ENODATA);
		assert(f.used == n + (n == 10));
		assert(f.mask == (n == 10 ? 2 : 3));
		assert((strstr(f.output, "PIN is no longer available. A recovery key is required.") != NULL) == (n == 10));
	}
	init(&f); f.bad_pin = true; f.message_fail_at = 11; f.message_error = -EIO;
	for (int i = 0; i < 10; i++) input(&f, "1234");
	assert(run(&f, false) == -EIO && f.mask == 2 && f.used == 11);
	assert(f.next == 10 && !strstr(f.output, "Enter recovery key:"));
	init(&f); f.bad_pin = true;
	for (int i = 0; i < 9; i++) input(&f, "1234");
	input(&f, ""); input(&f, "no"); input(&f, "abc"); input_error(&f, -EINVAL);
	input(&f, "1234"); recovery_input(&f);
	assert(run(&f, false) == 0 && f.used == 13 && f.mask == 3);
	assert(f.ops[10] == MSD_DELETE_PIN && f.ops[11] == MSD_AUTH_RECOVERY && f.ops[12] == MSD_ADD_PIN);
	init(&f); f.bad_pin = true; f.fail_at = 11;
	for (int i = 0; i < 10; i++) input(&f, "1234");
	recovery_input(&f);
	assert(run(&f, false) == -EIO && f.used == 11 && f.mask == 3);
	assert(!strstr(f.output, "PIN is no longer available."));
	init(&f); f.bad_pin = true; f.delete_noop = true;
	for (int i = 0; i < 10; i++) input(&f, "1234");
	assert(run(&f, false) == -EINVAL && f.used == 11);
	init(&f); input_error(&f, -EINTR);
	assert(run(&f, false) == -EINTR && f.used == 0);
	init(&f); input(&f, ""); f.message_fail_at = 2; f.message_error = -EINVAL;
	assert(run(&f, false) == -EINVAL && f.used == 0);
	init(&f); input(&f, "1234");
	assert(run(&f, false) == 0 && f.used == 1);
}

static void recovery(void)
{
	struct fake f;
	for (int mask = 2; mask <= 3; mask++) {
		init(&f); f.mask = mask;
		if (mask == 3) { input(&f, ""); input(&f, "yes"); }
		recovery_input(&f);
		assert(run(&f, false) == 0 && f.mask == 3 && f.used == (mask == 3 ? 3 : 2));
	}
	init(&f); f.mask = 2; f.bad_recovery = 11;
	input(&f, "invalid");
	for (int i = 0; i < 11; i++) input(&f, "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA");
	recovery_input(&f);
	assert(run(&f, false) == 0 && f.used == 13);
	for (int at = 1; at <= 3; at++) {
		init(&f); input(&f, ""); input(&f, "yes"); recovery_input(&f); f.fail_at = at;
		assert(run(&f, false) == -EIO && f.used == at);
		assert(f.mask == (at == 3 ? 2 : 3));
	}
	init(&f); f.mask = 2; input(&f, "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA");
	input_error(&f, -EINTR);
	assert(run(&f, false) == -EINTR && f.mask == 2 && f.used == 1);
	init(&f); f.mask = 2; recovery_input(&f);
	assert(run(&f, false) == 0);
	init(&f); input(&f, ""); input_error(&f, -EINTR);
	assert(run(&f, false) == -EINTR && f.used == 0);
	for (int mask = 2; mask <= 3; mask++) {
		for (int at = 0; at < 3; at++) {
			init(&f); f.mask = mask;
			if (mask == 3) { input(&f, ""); input(&f, "yes"); }
			input(&f, "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA");
			if (at == 0)
				input_error(&f, -EINTR);
			else {
				input(&f, "Long safe PIN 99!");
				if (at == 1)
					input_error(&f, -ENODATA);
				else {
					input(&f, "Long safe PIN 99!");
					f.fail_at = mask == 3 ? 3 : 2;
				}
			}
			assert(run(&f, false) < 0 && !f.mapped && f.deactivations == 1);
			f.count = f.next = f.used = f.fail_at = 0;
			memset(f.input, 0, sizeof(f.input));
			if (f.mask == 3) { input(&f, ""); input(&f, "yes"); }
			recovery_input(&f);
			assert(run(&f, false) == 0 && f.mapped);
		}
	}
	init(&f); f.mask = 2; f.deactivate_error = -EBUSY;
	input(&f, "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"); input_error(&f, -EINTR);
	assert(run(&f, false) == -EINTR && f.deactivations == 1);
	init(&f); f.mask = 2; f.progress_error = -EINTR; f.progress_fail_at = 6;
	input(&f, "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA");
	assert(run(&f, false) == -EINTR && !f.mapped && f.deactivations == 1);
}

int main(void)
{
	validation(); initialization(); authentication(); recovery();
	puts("ok - core: validation, setup, recovery, slot safety, error classification, interruption, wiping");
	return 0;
}
