#include <libkmod.h>
#include <stdio.h>

int main(void)
{
	struct kmod_ctx *ctx = kmod_new(NULL, NULL);
	struct kmod_module *module = NULL;
	int rc;

	if (!ctx)
		return 1;
	rc = kmod_module_new_from_name(ctx, "configs", &module);
	if (!rc)
		rc = kmod_module_probe_insert_module(module, 0, NULL, NULL, NULL, NULL);
	printf("libkmod configs load rc=%d\n", rc);
	kmod_module_unref(module);
	kmod_unref(ctx);
	return rc ? 1 : 0;
}
