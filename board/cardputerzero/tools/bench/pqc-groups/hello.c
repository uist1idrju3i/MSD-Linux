#include <stdio.h>
#include <openssl/err.h>
#include <openssl/ssl.h>

int main(int argc, char **argv)
{
	SSL_CTX *ctx;
	SSL *ssl;
	BIO *output;
	int result;

	if (argc != 2)
		return 2;
	ctx = SSL_CTX_new(TLS_client_method());
	if (ctx == NULL || !SSL_CTX_set1_groups_list(ctx, argv[1]))
		goto fail;
	ssl = SSL_new(ctx);
	if (ssl == NULL)
		goto fail;
	output = BIO_new(BIO_s_mem());
	SSL_set_bio(ssl, BIO_new(BIO_s_mem()), output);
	SSL_set_connect_state(ssl);
	if (!SSL_set_tlsext_host_name(ssl, "example.test"))
		goto fail;
	result = SSL_do_handshake(ssl);
	if (result >= 0 || SSL_get_error(ssl, result) != SSL_ERROR_WANT_READ)
		goto fail;
	printf("CLIENTHELLO %s %zu\n", argv[1], BIO_ctrl_pending(output));
	SSL_free(ssl);
	SSL_CTX_free(ctx);
	return 0;
fail:
	ERR_print_errors_fp(stderr);
	return 1;
}
