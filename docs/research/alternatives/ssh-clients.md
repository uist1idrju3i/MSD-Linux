# SSH clientの候補と暗号library

[代替比較](README.md) / [更新framework](updates.md) / [暗号・TLS](crypto.md) / [ネットワーク](network.md) / [署名](signing.md) / [build option](update-build-options.md) / [RESEARCH](../../../RESEARCH.md)

## 前提

2026-11-03に、MSD/Linuxの`origin/main` `94915bfef27f0d50ae0f4c6e24ffa98daf68a12e`と、固定Buildroot `8b238854d909c9cce32ef9671d968b03e323b55d`を基準に確認しました。SSH client候補のbuild、生成binaryの大きさ、RAM使用量、本機での接続は本リポジトリでは試していません。OpenSSLとほかの暗号libraryの関係は[build optionの比較](update-build-options.md)を参照してください。

## 利用者の判断（2026-11-19、#9）

> 必須要件は無し。3候補（OpenSSH 10.6p1、Dropbear 2026.94 dbclient、PuTTY 0.85 plink）の比較ではOpenSSHが良さそう

OpenSSHを優先候補としますが、採用は未決定です。clientだけのbuild、size、RSS、永続storageへの書込み量は未測定です。SSH serverの導入やSSH機能の製品採用を決めた記録ではありません。

OpenSSLは既にほかの用途で必要です。SSH clientを替えてもOpenSSL全体を除去できるとは扱わず、各候補を追加したときのsizeと依存の差を比較します。下記のOpenSSLなしのOpenSSHは参考情報です。

## 3候補の比較（2026-11-19追記）

固定Buildroot `75f325ad84251ee9d903467f84d3683e3bcf3fd5`のrecipeと各版の上流資料を静的に照合しました。接続・暗号交渉・hardware tokenの動作を測定した表ではありません。PQは耐量子鍵交換、skはsecurity keyを指します。

| 比較項目 | OpenSSH 10.6p1 | Dropbear 2026.94 `dbclient` | PuTTY 0.85 `plink` |
|---|---|---|---|
| 暗号実装 | 通常はOpenSSLと内蔵実装。固定BuildrootはOpenSSLを選択 | libtomcrypt／libtommath。BuildrootのSMALLでは同梱版、それ以外は外部libtomcrypt。OpenSSLは不要 | PuTTY独自の暗号実装。OpenSSLは不要 |
| PQ鍵交換 | ML-KEMとX25519、sntrup761とX25519のhybridに対応 | ML-KEM、sntrup761とX25519のhybridが既定で有効 | ML-KEMのhybridとsntrup761のhybridに対応 |
| sk／FIDO | sk鍵に対応。直接tokenを操作する構成のlibfido2、USB、helperも確認が要る | `DROPBEAR_SK_KEYS`はserver専用。dbclientのFIDO対応とは扱わない | OpenSSHのsk鍵型とFIDOの直接操作には非対応。agent連携は別途確認 |
| `~/.ssh/config` | 標準で読む。Host、Include、ProxyJump等を使える | 同じfileは読まず、`~/.ssh/dropbear_config`で限られた設定だけを読む。`-o`の対応も一部 | 同じfileは読まない。PuTTYの保存sessionとcommand lineを使う |
| host keyの保存と書込み | `~/.ssh/known_hosts`。新規鍵の受諾や`UpdateHostKeys`による更新が書込み候補 | `~/.ssh/known_hosts`。鍵の受諾時に追記。読込処理でも`.ssh`の作成とfileの`a+` openを試す | Unix版はPuTTY専用の`sshhostkeys`。`PUTTYSSHHOSTKEYS`等で保存先を変更できる。OpenSSHのknown_hostsとは別形式 |
| clientだけにする際の注意 | Buildrootのclient／server選択はinstallを分けるが、build対象をclientだけに絞る保証ではない。client選択でもssh以外のtool・helperが入る | 上流は`PROGRAMS=dbclient`で対象を指定できるが、固定recipeはserver等を含むmulti-call binary。install後のsymlink削除だけではserverコードの除外にならない | GTKなしでもCLI tool群をbuildする。`plink`だけのbuild targetとinstall対象を分けて確認する。固定recipeはGSSAPIを無効にする |
| MSD/Linuxでの状態 | 優先候補、未採用 | 比較候補 | 比較候補 |

known_hosts等を読取り専用にしたときの挙動、新規鍵・鍵変更・`UpdateHostKeys`・保存の取消しと中断、乱数seedやsession情報を含む書込み先は未検証です。自動登録や検証無効化を、書込み回避策として選んだわけではありません。[製品の書込み規則](../../design/write-policy.md)に沿って保存の時機と利用者への表示を検討します。

### 一次資料

- OpenSSH: [INSTALL](https://raw.githubusercontent.com/openssh/openssh-portable/V_10_6_P1/INSTALL)、[ssh_config.5](https://raw.githubusercontent.com/openssh/openssh-portable/V_10_6_P1/ssh_config.5)、[PROTOCOL.u2f](https://raw.githubusercontent.com/openssh/openssh-portable/V_10_6_P1/PROTOCOL.u2f)、[kex-names.c](https://raw.githubusercontent.com/openssh/openssh-portable/V_10_6_P1/kex-names.c)。
- Dropbear: [dbclient.1](https://raw.githubusercontent.com/mkj/dropbear/DROPBEAR_2026.94/manpages/dbclient.1)、[default_options.h](https://raw.githubusercontent.com/mkj/dropbear/DROPBEAR_2026.94/src/default_options.h)、[cli-kex.c](https://raw.githubusercontent.com/mkj/dropbear/DROPBEAR_2026.94/src/cli-kex.c)、[INSTALL.md](https://raw.githubusercontent.com/mkj/dropbear/DROPBEAR_2026.94/INSTALL.md)。
- PuTTY: [0.85のsource archive](https://the.earth.li/~sgtatham/putty/0.85/putty-0.85.tar.gz)内の`crypto/`、`ssh/transport2.c`、`unix/storage.c`、`CMakeLists.txt`と、[Plinkのmanual](https://www.chiark.greenend.org.uk/~sgtatham/putty/0.85/htmldoc/Chapter7.html)。WindowsのRegistry保存とUnix版のfile保存を区別します。
- 固定Buildroot: `vendor/buildroot/package/openssh/`、`dropbear/`、`putty/`の`Config.in`と各`.mk`。clientのinstall選択と、serverコードを含まないbuildを区別します。

### 採用前に残る確認

以下は未実施の比較案です。同じtoolchain、最適化、link方式で3候補をclientだけにし、build条件と生成物を保存します。strip後のbinaryとrootfs差分、既存OpenSSLを共有した追加容量、待機時・接続時・転送時のRSSを比較します。初回接続、登録済み鍵、鍵変更、接続拒否、保存中断ごとに永続書込みを測定します。これらの実測とbuild／実行時optionの[component-options表](../component-options/README.md)をそろえてから採否を判断します。

## client候補

| 候補 | 固定Buildrootの版／上流版 | 暗号とlicense | clientとしての制約 |
|---|---|---|---|
| Dropbear（`dbclient`） | 2026.94／上流の最新版は未確認 | libtomcryptとlibtommath（SMALLでは同梱版）、OpenSSLなし。MIT、BSD-2-Clause、Public domain | 固定recipeはclientを選んでもserverと補助toolをbuildする。`BR2_PACKAGE_DROPBEAR_LOCALOPTIONS_FILE`で外部の`localoptions.h`を渡せる |
| OpenSSH | 10.6p1／V_10_6_P1 | OpenSSLと内蔵実装。BSD-3-Clause等 | 固定recipeのclient選択は上表参照。`--without-openssl`は参考扱い |
| PuTTY（`plink`） | 0.85／比較対象は0.85 | 独自実装。MIT | GTKなしでもCLI tool群をbuildする。plinkだけの生成物とinstall範囲は未確認 |
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
| host key | RSA（SHA-1署名は無効）、ECDSA、Ed25519 | DSS |
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
- 各clientだけのbuild、binary size、RSS、永続書込み量
- OpenSSLなしのOpenSSHが実際にbuildできるか
- 固定BuildrootでDropbear serverコードをbuild対象から除く方法
- known_hostsの互換性
- 上表の設定file・host key形式の差を踏まえた移行と、保存拒否・中断時の動作
