# SSH clientの候補と暗号library

[代替比較](README.md) / [更新framework](updates.md) / [暗号・TLS](crypto.md) / [ネットワーク](network.md) / [署名](signing.md) / [build option](update-build-options.md) / [RESEARCH](../../../RESEARCH.md)

## 前提

2026-11-03に、MSD/Linuxの`origin/main` `94915bfef27f0d50ae0f4c6e24ffa98daf68a12e`と、固定Buildroot `8b238854d909c9cce32ef9671d968b03e323b55d`を基準に確認しました。SSH client候補のbuild、生成binaryの大きさ、RAM使用量、本機での接続は本リポジトリでは試していません。OpenSSLとほかの暗号libraryの関係は[build optionの比較](update-build-options.md)を参照してください。

## client候補

| 候補 | 固定Buildrootの版／上流版 | 暗号とlicense | clientとしての制約 |
|---|---|---|---|
| Dropbear（`dbclient`） | 2026.94／上流の最新版は未確認 | 同梱のlibtomcryptとlibtommath（SMALLでは同梱版）、OpenSSLなし。MIT、BSD-2-Clause、Public domain | clientを選んでもserverのbinary（`dropbear`、`dropbearkey`、`scp`）もbuildされる。`BR2_PACKAGE_DROPBEAR_LOCALOPTIONS_FILE`で外部の`localoptions.h`を渡せる |
| OpenSSH（`--without-openssl`） | 10.6p1／V_10_6_P1 | OpenSSLなしの内蔵実装はBSD-3-Clause等 | BuildrootのrecipeがOpenSSLを必ずselectするため、OpenSSLなしでは外部packageが必要 |
| libssh | 0.12.1／0.12.2 | OpenSSL、mbedTLS、libgcrypt。LGPL-2.1 | libraryのみ。BuildrootにCLI clientはない |
| libssh2 | 1.11.1／1.11.1 | OpenSSL、mbedTLS、libgcrypt。BSD | libraryのみ |
| tinyssh | 20240101／20261101 | 同梱の実装。CC0-1.0 | serverのみとの見方は推測で、確認が要る。固定Buildrootの版は古い |
| autossh、sshpass、sshfs | - | 別のSSH clientを呼ぶ補助tool | client本体の代替ではない |

固定Buildrootのpackage資料は`vendor/buildroot/package/openssh/Config.in`、`openssh.mk`、`vendor/buildroot/package/dropbear/Config.in`、`dropbear.mk`、`vendor/buildroot/package/libssh/Config.in`、`libssh.mk`、`vendor/buildroot/package/libssh2/Config.in`、`libssh2.mk`です。

## OpenSSHをOpenSSLなしで使う場合

OpenSSH 10.6p1は上流で`--without-openssl`を指定できますが、暗号方式は内蔵実装の範囲に限られます。

- cipher: aes128/192/256-ctr、chacha20-poly1305
- key exchange: curve25519-sha256、sntrup761x25519、mlkem768x25519
- host keyとuser key: Ed25519（security key版を含む）、`USE_MLDSA`時のmldsa44-ed25519
- ECDSAとRSAのkeyはOpenSSLが必要

Buildrootの`vendor/buildroot/package/openssh/Config.in`と`openssh.mk`ではOpenSSLをselectします。OpenSSLなしで使うには外部packageが必要です。上流の詳細は[INSTALL](https://raw.githubusercontent.com/openssh/openssh-portable/V_10_6_P1/INSTALL)、[cipher.c](https://raw.githubusercontent.com/openssh/openssh-portable/V_10_6_P1/cipher.c)、[kex-names.c](https://raw.githubusercontent.com/openssh/openssh-portable/V_10_6_P1/kex-names.c)、[sshkey.c](https://raw.githubusercontent.com/openssh/openssh-portable/V_10_6_P1/sshkey.c)にあります。

## Dropbear 2026.94の既定値

`src/default_options.h`で確認した既定値は次のとおりです。

| 種類 | 有効 | 無効 |
|---|---|---|
| cipher | AES128、AES256、chacha20-poly1305 | 3DES |
| MAC | hmac-sha2-256 | SHA1-HMAC |
| host key | RSA（SHA-1署名は無効）、ECDSA、Ed25519、security key | DSS |
| key exchange | curve25519、sntrup761、mlkem768、ECDH、DH group14-sha256 | DH group1 |
| client機能 | local/remote転送、agent転送、ProxyCommand、netcat | 圧縮 |

Buildrootの`DROPBEAR_LEGACY_CRYPTO`を選ぶと、3DES、CBC、SHA1、DH group1、DSSが戻ります。Buildrootのpackage資料は`vendor/buildroot/package/dropbear/Config.in`と`dropbear.mk`です。

`CHANGES`には次のsecurity修正が記録されています。

- CVE-2025-14282: unix stream転送による権限昇格（2024.84から2025.88が影響）
- CVE-2025-47203: `dbclient`のhostname引数がlocal commandとして解釈される問題
- CVE-2026-35385: `scp`が受け取ったfileのsetuid/setgidを消していなかった問題（OpenSSHのpatch）
- CVE-2023-48795（Terrapin）への対応
- 2026.94でX11転送のuse-after-freeを修正

上流資料: [default_options.h](https://raw.githubusercontent.com/mkj/dropbear/DROPBEAR_2026.94/src/default_options.h)、[CHANGES](https://raw.githubusercontent.com/mkj/dropbear/DROPBEAR_2026.94/CHANGES)。

## 未確認

- 上流Dropbearの最新版
- 各clientのbinary sizeとRAM使用量
- OpenSSLなしのOpenSSHが実際にbuildできるか
- Dropbear server部品を除く方法（post-buildでの削除か`localoptions.h`か）
- known_hostsの互換性
- `~/.ssh/config`との互換性。`dbclient`はこのfileを読まない可能性がある（推測）
