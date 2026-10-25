# SSH・VPN・鍵保管の調査

[ユーザー空間・libc 調査](userspace-and-security.md) から分けた節です。節の番号（21）は元の文書のものを残しています。

## 21. SSH・VPN、暗号拡張、鍵保管と A/B OTA

### Firmware と再配布条件

- 【未確認】CYW43439 の firmware は `firmware-nonfree` / `brcmfmac_sdio-firmware-rpi` などの配布経路と関連し、再配布条件の確認が必要です。採用する blob とそのライセンスを特定してから同梱します。https://github.com/RPi-Distro/firmware-nonfree<br>https://github.com/raspberrypi/firmware
- 【未確認】M5 LCD 初期化用 binary、BMI270 初期化 firmware、keymap のライセンスは公開ソース内で確認できていません。公開配布前に M5Stack へ利用・再配布条件を確認します。https://github.com/m5stack/m5stack-linux-dtoverlays/tree/75518549a2640486f5d13ea72ca4935b198d7c20/modules/st7789v-1.0<br>https://github.com/m5stack/m5stack-linux-dtoverlays/tree/75518549a2640486f5d13ea72ca4935b198d7c20/modules/imu-1.0<br>https://github.com/m5stack/m5stack-linux-dtoverlays/tree/75518549a2640486f5d13ea72ca4935b198d7c20/modules/tca8418-1.0

### 21.1 BCM2837 の ARMv8 Crypto Extensions
| 事実 | 出典URL | 確認度 |
|---|---|---|
| Cortex-A53 の Cryptography Extension はオプションで、標準製品に含まれず追加ライセンスで供給されると Arm DDI 0501F に記載されています（Cortex-A53 一般の説明で、BCM2837 が実装しているかは別です）。 | https://documentation-service.arm.com/static/5e9077ee8259fe2368e2acf7?token= （Arm DDI 0501F）。https://documentation-service.arm.com/static/5e9077ee8259fe2368e2acf7 | 一次 |
| `ID_AA64ISAR0_EL1` の AES / SHA1 / SHA2 フィールドは、Cryptographic Extension を含まない実装では 0x0 です（Arm のレジスタ定義）。 | https://support.arm.com/documentation/101433/0102/Register-descriptions/AArch64-system-registers/ID-AA64ISAR0-EL1--AArch64-Instruction-Set-Attribute-Register-0--EL1 | 未確認（HTTP 403 で取得できず） |
| BCM2837 は JTAG で当該レジスタを読み、AES / SHA1 / SHA2 = 0、CRC32 = 1 だったとの個人報告があります。BCM2837B0（Pi 3B+）の `/proc/cpuinfo` Features に `aes / pmull / sha1 / sha2` がなく、`crc32` があるとの報告もあります。 | https://forums.raspberrypi.com/viewtopic.php?t=207888<br>https://forums.raspberrypi.com/viewtopic.php?t=263234 | 二次（個人報告。HTTP 403 で取得できず。Broadcom / RPi の一次仕様ページも未確認） |
| sbc-bench:Broadcom の 64bit 対応 RPi(BCM2712 以外)は crypto 加速が無いと記載 | https://github.com/ThomasKaiser/sbc-bench/blob/master/results/ARMv8-Crypto-Extensions.md | 二次 |
| 帰結:CM0（BCM2837）は AES / SHA / PMULL 命令を持たないと推測されますが、メーカー仕様の一次資料では確認できていません。実機の `/proc/cpuinfo` の Features で確認できます（実機未入手）。 | — | 二次 + 推測（実機で未確認） |
| カーネルは CE 版と NEON 版・汎用版を持つ(`arch/arm64/crypto/aes-ce-*`、`aes-neon*`、`lib/crypto/arm64/chacha-neon-core.S`、`sha256-ce.S` 等)。ChaCha は `CRYPTO_LIB_CHACHA_ARCH` が `ARM64 && KERNEL_MODE_NEON` で既定有効 | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/lib/crypto/Kconfig#L46-L52 / https://github.com/raspberrypi/linux/tree/234188315037848e5b07d65b85d38edc64095caa/lib/crypto/arm64 | 一次 |

### 21.2 WireGuard の速度への影響
| 事実 | 出典URL | 確認度 |
|---|---|---|
| WireGuard カーネルモジュールは `CRYPTO_LIB_CHACHA20POLY1305` と `CRYPTO_LIB_CURVE25519` を使う(AES を使わない) | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/net/Kconfig#L75-L83 | 一次 |
| 公式のパフォーマンスページのベンチは **Intel Core i7-3820QM / i7-5200U、Linux 4.6.1、GbE** の古い測定で、公式自身が「old, crusty, and not super well conducted」と注記。**ARM/CM0 の数値は無い** | https://www.wireguard.com/performance/ | 一次 |
| 帰結:WireGuard は AES を使わず ChaCha20-Poly1305 を使うため、Crypto Extensions がなくても NEON 実装を利用できます（カーネルに `chacha-neon` があります）。OpenSSH は既定暗号に ChaCha20-Poly1305 を含み、Dropbear は ChaCha20-Poly1305 を有効、GCM を無効にしています。OpenVPN は `--data-ciphers` の既定順で AES-GCM が先なので、CE のない CM0 では ChaCha20-Poly1305 を先頭にする設定が必要と推測されます。CM0 での実スループットは公開値がなく、実機未測定です。Wi-Fi は 2.4 GHz 802.11n、Ethernet は 10 / 100 Mbit/s（USB 2.0）なので、リンク側が先に上限になる可能性があります（推測）。 | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/lib/crypto/arm64<br>https://raw.githubusercontent.com/openssh/openssh-portable/V_10_5_P1/myproposal.h<br>https://raw.githubusercontent.com/mkj/dropbear/DROPBEAR_2026.94/src/default_options.h<br>https://openvpn.net/community-docs/community-articles/openvpn-2-7-manual.html<br>https://docs.m5stack.com/en/CardputerZero | 推測 |
| Dropbear のオプションには、ChaCha20-Poly1305 は AES 命令のない CPU で AES256 より概して速いとのコメントがあります。 | https://github.com/mkj/dropbear/blob/DROPBEAR_2026.94/src/default_options.h | 一次（コメント） |

### 21.3 SSH と VPN の選択肢
| 項目 | 事実 | 出典URL | 見立て(推測) |
|---|---|---|---|
| Dropbear | 小型の SSH サーバ/クライアント。`PROGRAMS=dropbear` でサーバのみビルド、`localoptions.h` でアルゴリズム/認証/転送を無効化して小さくできる。静的ビルドでは zlib を無効にするとサイズが減る | https://github.com/mkj/dropbear/blob/master/README.md / https://github.com/mkj/dropbear/blob/master/SMALL.md | 小さく BusyBox 系と相性が良い。socket activation(systemd)で常駐を避ける案 |
| OpenSSH（sshd） | 標準的です。既定の暗号・KEX は `myproposal.h` で確認できます。https://man.openbsd.org/sshd.8 は接続できず取得できていません。 | https://raw.githubusercontent.com/openssh/openssh-portable/V_10_5_P1/myproposal.h | サイズが大きく依存も多い（OpenSSL / libcrypto など）一方、systemd 構成なら導入は簡単です。 |
| WireGuard | カーネル内蔵(`CONFIG_WIREGUARD`)+ `wg` ツール。導入手順は公式 https://www.wireguard.com/install/ と https://www.wireguard.com/quickstart/ | https://www.wireguard.com/quickstart/ | 起動時間の影響はモジュールロード時のみ。**終点の後に起動** で良い |
| OpenVPN | ユーザー空間デーモン + OpenSSL です。Buildroot 2026.08 は 2.7.6 です。公式マニュアルは 2.7 で、旧 2.6 URL は同コミュニティ文書へ移転しました。https://raw.githubusercontent.com/buildroot/buildroot/2026.08/package/openvpn/openvpn.mk | https://openvpn.net/community-docs/community-articles/openvpn-2-7-manual.html<br>https://openvpn.net/community-docs/community-articles/openvpn-2-6-manual.html（旧URL） | **暗号は `--data-ciphers` の設定が必要です**（既定は AES-256-GCM : AES-128-GCM : CHACHA20-POLY1305。ChaCha は利用可能な場合のみ）。CM0 では AES-GCM がソフト実装で遅いと推測されるため、ChaCha20-Poly1305 を先頭にする案です。 |

### 21.4 鍵保管と A/B OTA
【推測・設計案（一次情報で検証した設計ではありません）】
- **ホスト鍵(SSH)・WireGuard 秘密鍵・認証情報は A/B のどちらの rootfs にも入れず、別の永続 RW パーティション(小さい ext4)に置く**。A/B 切替・ロールバックで鍵が変わると、クライアント側の known_hosts 警告や VPN 切断が起こるため。
- 鍵の生成は**初回起動時(個体ごと)** に行う。イメージに共通鍵を焼くと全個体が同じ鍵になる(典型的な落とし穴)。
- 電断耐性：鍵ファイルは「tmp に書く → fsync → rename」で更新する案です（[電源遮断耐性の調査](power-and-updates.md)）。RW パーティションが壊れても機器は起動できるよう分離し、破損時に鍵を再生成する運用を許容するか決める必要があります。
- 権限は `0600` とします。microSD は取り外せるため、暗号化しなければ鍵を読み取れる可能性があります（個体の物理的脅威モデルは未検討）。dm-crypt は CM0 に AES 命令がなく遅いと推測されます。ChaCha20 系の Adiantum は RPi defconfig で `CRYPTO_ADIANTUM=m` ですが、CE 非搭載機向けとの説明は未確認です。https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig 【一次（設定） / 用途は未確認】
- OTA ペイロードの署名検証は RAUC / SWUpdate の導入候補に含まれます（[電源・更新方式の調査](power-and-updates.md)）。**署名鍵・検証鍵の保管とローテーション**は未調査です。
- Dropbear は `-r` でホスト鍵ファイルのパスを指定できるとの記述がありますが、現時点では未確認です。確認先は [Dropbear README](https://github.com/mkj/dropbear/blob/main/README.md) です。OpenSSH の `HostKey` も man を取得できておらず未確認です。

### 21.5 ポスト量子（PQ）鍵交換と SSH / VPN の既定暗号

Devin が 2026-10-18 JST に各実装の既定値を定義するファイルを公開資料で確認しました。Buildroot 2026.08（コミット d5180309）の同梱版は、各 `package/*/*.mk` に記載された版です。https://github.com/buildroot/buildroot/commit/d5180309 **CM0 での実行時間・スループットは公表値が見つからず、実機未測定です。**

| 実装(版:何の版か) | 既定の暗号・鍵交換(定義ファイル) | PQ ハイブリッド | コスト(出典にある範囲) | 出典 |
|---|---|---|---|---|
| **OpenSSH 10.5p1**（Buildroot 2026.08 同梱版。ポータブル版のタグ V_10_5_P1） | 暗号の既定順（`myproposal.h` の `KEX_SERVER_ENCRYPT`）は **`chacha20-poly1305@openssh.com`**、`aes128-gcm@openssh.com`、`aes256-gcm@openssh.com`、aes128 / 192 / 256-ctr です。MAC は ETM 系が先頭です。鍵交換の既定順は **`mlkem768x25519-sha256`**、`sntrup761x25519-sha512`、`sntrup761x25519-sha512@openssh.com`、`curve25519-sha256` などです（クライアントは DH group exchange なども追加）。 | **あり・既定で先頭**（ML-KEM-768 + X25519）。OpenSSH 10.0 のリリースノート（2025-04-09）は `mlkem768x25519-sha256` が既定の鍵交換方式になったと記載します。 | リリースノートは「前の既定よりかなり高速」と記載しますが、比較対象は明記されていません。CM0 での時間は不明です。ChaCha が先頭のため、AES 命令がない構成でも不利になりにくいと推測されます。 | https://raw.githubusercontent.com/openssh/openssh-portable/V_10_5_P1/myproposal.h<br>https://www.openssh.org/txt/release-10.0<br>https://raw.githubusercontent.com/buildroot/buildroot/2026.08/package/openssh/openssh.mk |
| **Dropbear 2026.94**(Buildroot 2026.08 同梱版。CHANGES の日付 2026-07-23) | `default_options.h`:`DROPBEAR_CHACHA20POLY1305 1`、`DROPBEAR_AES128/256 1`、**`DROPBEAR_ENABLE_GCM_MODE 0`(AES-GCM は既定で無効)**。鍵交換:`DROPBEAR_CURVE25519 1`、`DROPBEAR_ECDH 1` | **あり・既定で有効**:`DROPBEAR_SNTRUP761 1` と `DROPBEAR_MLKEM768 1`(ともにハイブリッド) | 同ファイルのコメント:「sntrup uses ~9kB code size, mlkem uses ~34kB code size (32-bit armv7)」「Both are fast」。GCM は「slower than CTR on CPU w/o dedicated AES/GHASH instructions」とコメント(CM0 は該当見込み)。CHANGES:「These do increase code size, at least sntrup761 is recommended」 | https://raw.githubusercontent.com/mkj/dropbear/DROPBEAR_2026.94/src/default_options.h / https://raw.githubusercontent.com/mkj/dropbear/DROPBEAR_2026.94/CHANGES / https://raw.githubusercontent.com/buildroot/buildroot/2026.08/package/dropbear/dropbear.mk |
| **OpenVPN 2.7.6**（Buildroot 2026.08 同梱版。マニュアルは 2.7） | **暗号は設定が必要です**。`--data-ciphers` の既定は AES-256-GCM : AES-128-GCM : CHACHA20-POLY1305（ChaCha20-Poly1305 が使える場合。なければ前の 2 つ）です。`--cipher` は 2.6.0 以降 TLS モードで無視されます。`--auth` の既定は SHA1（AEAD では無視）で、`--data-ciphers-fallback` は 2.3 以前の相手向けです。 | マニュアル上、既定の PQ 鍵交換はありません。実効既定は OpenSSL 版に依存します。`--tls-groups` の説明は OpenSSL 1.1 以降の既定リストに ML-KEM を含めませんが、OpenVPN 2.7.6 は `--tls-groups` を指定した場合だけグループを設定します。OpenSSL 3.6.4 の既定グループ一覧は `X25519MLKEM768` が先頭です。実際の接続で ML-KEM が使われるかは未確認です。 | AES-GCM が先頭のため、AES 命令のない CM0 では **`--data-ciphers CHACHA20-POLY1305:AES-256-GCM` のように ChaCha を先頭にする設定が必要**と推測されます。実測はありません。 | https://openvpn.net/community-docs/community-articles/openvpn-2-7-manual.html<br>https://raw.githubusercontent.com/buildroot/buildroot/2026.08/package/openvpn/openvpn.mk<br>https://github.com/OpenVPN/openvpn/blob/v2.7.6/src/openvpn/ssl.c#L552<br>https://github.com/openssl/openssl/blob/openssl-3.6.4/ssl/t1_lib.c#L209<br>https://github.com/buildroot/buildroot/blob/2026.08/package/libopenssl/libopenssl.mk |
| **WireGuard**（カーネル組込み。wireguard-tools 1.0.20260223、wireguard-linux-compat 1.0.20220627 は Buildroot 2026.08 の版） | 固定プリミティブは ChaCha20-Poly1305、Curve25519、BLAKE2s、HKDF です（暗号選択の設定はありません）。 | **標準ではありません。** 公式プロトコル説明では、追加の対称鍵暗号が必要な場合（例：耐量子性）に任意の事前共有鍵を使えるとしています。 | AES を使わず NEON 実装があります。事前共有鍵（PSK）は任意で、鍵配布は別途必要です。 | https://www.wireguard.com/protocol/<br>https://raw.githubusercontent.com/buildroot/buildroot/2026.08/package/wireguard-tools/wireguard-tools.mk<br>https://raw.githubusercontent.com/buildroot/buildroot/2026.08/package/wireguard-linux-compat/wireguard-linux-compat.mk |

**読み取れること(事実の範囲)**
- OpenSSH 10.5p1 と Dropbear 2026.94 は、Buildroot 2026.08 同梱版で設定なしでも PQ ハイブリッド鍵交換が有効です。OpenVPN 2.7.6 はマニュアル上の既定に PQ はありません。実効既定は OpenSSL 版に依存し、実接続で ML-KEM が使われるかは未確認です。WireGuard は PSK による追加層のみです。
- データ暗号では OpenSSH は ChaCha20-Poly1305 が先頭、Dropbear は ChaCha20-Poly1305 が有効で GCM は無効、OpenVPN は GCM が先頭（設定変更が必要）です。
- Dropbear の ML-KEM は約 34kB(armv7 の値)、sntrup は約 9kB の追加コード。ディスクと RAM が小さい構成では 34kB を見積もるが、**CM0(aarch64)での値や起動時間への影響は未測定**。

【推測・未測定】鍵交換は接続ごとに 1 回の計算なので、[起動完了条件](measurement-and-planning.md)の後に sshd / Dropbear を socket activation で起動すれば、起動時間への影響は小さいと見込まれます。実測では SSH 接続確立までの時間が重要です。CM0 の A53 での ML-KEM / X25519 の実測は、実機入手後に行う必要があります。PQ を使う場合のサーバー・クライアント双方の版要件（古いクライアントとの互換性）は未調査です。

【未確認】OpenSSH の ML-KEM が CM0 でどの程度時間を要するか（公開値なし）、OpenVPN で ML-KEM 系グループが実際に使われるか（OpenSSL 3.6.4 の既定は `X25519MLKEM768` が先頭ですが、OpenVPN 2.7.6 は `--tls-groups` 未指定ならグループを設定しません。ソース確認のみで実接続は未確認）、`--tls-groups` に指定できる値、Buildroot での OpenSSH の `libcrypto` 構成は未確認です。実機測定と対象版の公開ソースで確認が必要です。
