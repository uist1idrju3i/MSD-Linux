# 当初の設計案と判断の記録

[調査の索引](../../../RESEARCH.md) / [検証の入口](README.md)

以下は整理前の設計記録です。RAUC custom backend、ext4への移行、HDMI除去などを現在の採用済み機能とは読みません。
現行値は[defconfig](../../../configs/msd_cardputerzero_defconfig)、[kernel fragment](../../../board/cardputerzero/linux.fragment)、[更新操作](../../UPDATE.md)を参照します。
rootfsはSquashFS + zstd、`/data`はext4、更新は`msd-update`です。比較候補の新しい評価は[代替比較](../alternatives/README.md)にまとめています。

## 推奨案と未決事項

以下は公開資料と未測定事項を踏まえた暫定案です。設計上の選択肢は候補であり、実機での確認が必要な項目は未確認または推測として記します。

### 推奨案
| 項目 | 推奨 | 推奨理由 | 出典URL |
|---|---|---|---|
| 方向性 | **Linux を第一候補** | Zephyr 26.04 LTS と v4.4.0 の CM0 対応、microSD、SDHCI の有無は公開ボード情報だけでは確認できていません。実機で確認する必要があります（未確認）。 | https://github.com/zephyrproject-rtos/zephyr/tree/684c9e8f32e4373a21098559f748f06915f950c9/boards/raspberrypi<br>https://github.com/zephyrproject-rtos/zephyr/tree/a915b2f12675b48b16d56653ea145dcd8f20cbbf/boards/raspberrypi/rpi_zero_2w |
| ベース | **Buildroot が第一候補**、Yocto（meta-raspberrypi wrynose、raspberrypi0-2w-64）が代替候補 | Buildroot は単一リポジトリの最小構成として管理しやすく、対象システムに apt を含めない設計を取りやすいと考えます（推測）。Yocto は opkg/rpm を利用できますが、初回ビルドは数時間・50 GB 超となる見込みです（推測、実測なし）。pi-gen は公式 Debian 互換性が高い一方、読み取り専用 rootfs と A/B は追加実装が必要で、既存資料の起動時間は 7〜9 秒です。 | https://github.com/buildroot/buildroot/commit/d5180309b1b66ef3b8eaccca70ad69be8e0729a1<br>https://docs.yoctoproject.org/overview-manual/concepts.html#package-management<br>https://github.com/agherzan/meta-raspberrypi/blob/919588393f41b48cb6c5d832aa35e58a19b6762d/conf/machine/raspberrypi0-2w-64.conf<br>https://github.com/CardputerZero/pi-gen<br>https://downloads.raspberrypi.com/os_list_imagingutility_v4.json |
| カーネル | **rpi-6.18.y をコミット固定**（6.18.57） | M5 の `panel-mipi-dbi-m.c` は `drm_client_setup.h` を include します。このヘッダーは rpi-6.18.y にあります。rpi-6.12.y の同じパスは HTTP 404 ですが、6.12 系全体でヘッダーがないかは未確認です。6.13〜6.17 も未確認です。pi-gen は 6.18.39 を指定しています。Linux 6.18 の LTS 期間は 2028-12 までです。 | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/Makefile#L2-L4<br>https://github.com/raspberrypi/linux/commit/234188315037848e5b07d65b85d38edc64095caa<br>https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage0/02-firmware/files/kernel.pref#L3<br>https://raw.githubusercontent.com/m5stack/m5stack-linux-dtoverlays/75518549a2640486f5d13ea72ca4935b198d7c20/modules/st7789v-1.0/panel-mipi-dbi-m.c<br>https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.18.y/include/drm/clients/drm_client_setup.h<br>https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/include/drm/clients/drm_client_setup.h<br>https://www.kernel.org/category/releases.html |
| rootfs | **SquashFS または EROFS の読み取り専用 rootfs + overlayfs（upper は tmpfs / zram）+ 小さな ext4 RW データ領域** | Raspberry Pi の公開ホワイトペーパーは、読み取り専用 rootfs と書き込み領域を分ける方式を推奨しています。 | https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-003610-WP-3-Making%20a%20more%20resilient%20file%20system.pdf |
| A/B | **MBR + tryboot / autoboot.txt + RAUC custom バックエンド**（試行カウンターとフォールバックは自前） | Raspberry Pi の文書は tryboot を全モデル向けに説明していますが、BCM2837 での実動作は未確認です。U-Boot なしで追加段を避けられる可能性はあります（推測）。公式 image-rota は GPT を使い、対応モデルは Pi 4 / 5 です。代替候補の Rugix は Pi 3 で rpi-tryboot、Zero 2 W で rpi-uboot を示します。 | https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/autoboot.adoc#L5-L60<br>https://github.com/raspberrypi/rpi-image-gen/blob/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/image/gpt/ab_userdata/image.yaml#L2-L11<br>https://api.github.com/repos/rauc/rauc/pulls/1599<br>https://rugix.org/docs/bakery/devices/ |
| UI | **CLI 専用を候補とし、HDMI / vc4 を外す構成を実測で評価** | ユーザー要件に基づく案です。HDMI / vc4 を外した実機での動作は未確認です。 | — |
| 電源断 | 読み取り専用 rootfs に加え、GPIO6 の通知・同期を実装。正常停止は hold-up 時間の測定後に判断 | package patch が通知と同期を SysRq-U より前に実行します。バックライト消灯と disabled GPIO の処理は維持しています。 | [電源断処理](../power-and-updates.md#63-powerfail_suo) |

### 設計上の未決事項
| 論点 | 選択肢・留保 | 状態 |
|---|---|---|
| 起動完了条件 | 主指標は **T_shell**（LCD にプロンプトが表示され、キー入力できる時点）、副指標は **T_init**（PID 1 の完了マーカー）とし、両方を測ります。 | 測定方針 |
| 読み取り専用 rootfs | SquashFS（`-sort` で優先度の高いファイルを先に配置）と EROFS（`-z` を指定すれば圧縮でき、`--sort` は tar 入力向け）を実機で比較する案です。どちらが速いかは未測定です。 | 未決 |
| init と libc | 初期案は BusyBox init + mdev + glibc とします。mdev への udev ルール移植、必要なら musl との比較、systemd の最小化も検討します。起動時間は未測定です。[関連資料](../userspace-and-security.md) | 未着手 |
| A/B 方式 | MBR + tryboot / autoboot.txt + RAUC custom、U-Boot 系、Rugix を候補とします。tryboot と watchdog が CM0 で動作するか未確認です。FAT の boot 領域が単一障害点となる可能性があります（推測）。 | 未決 |
| カーネル版 | Linux 6.18.y、7.2.y、7.3.y を候補とします。7.2.y / 7.3.y の PREEMPT は LAZY / FULL のみです。7.1 で DRM API が変わり、7.3 の alias unmap 再適用後の CM0 起動は未確認です。 | 未決 |
| 開発中のログ | 開発ビルドでは ext4 に記録し、電断試験時は専用領域または pstore に切り替える案です。完全 read-only との両立方法と、測定条件の差を記録する必要があります。 | 未決 |
| SSH / VPN | Dropbear または OpenSSH、WireGuard または OpenVPN を候補とします。SSH サーバーは起動完了後に socket activation で起動する案です。[関連資料](../ssh-vpn-and-keys.md) | 未決 |
| 名称 | MSD/Linux の由来は [RESEARCH.md](../../../RESEARCH.md) に記載しています。 | — |

### 判断と関連資料
| 項目 | 関連資料 |
|---|---|
| 起動完了条件・測定 | [実機で測る項目](hardware-measurements.md#実機が届いたら最初に測る項目優先順の案) |
| カーネル・UI | [起動・カーネル調査](../boot/sequence.md) |
| rootfs・init・libc | [ユーザー空間・セキュリティ調査](../userspace-and-security.md) |
| A/B・電源断 | [電源・更新方式の調査](../power-and-updates.md) |
| 開発中のログ | [開発中の観測手段](observability.md#開発中の観測手段) |
| SSH / VPN | [SSH・VPN・鍵保管の調査](../ssh-vpn-and-keys.md) |
| 名称の由来 | [RESEARCH.md](../../../RESEARCH.md) |

---

## 調査範囲と限界

以下は当初の調査範囲と取得失敗の記録です。後の検証結果や現在の到達性へ読み替えません。

調査した公開資料は[出典一覧](../sources.md)に記載しています。kernel.org の kernel 文書、EROFS FAQ、squashfs-tools documentation、man7、BusyBox FAQ、Dropbear、WireGuard、musl、mimalloc、M5 documentation と overlay、raspberrypi/linux、raspberrypi/documentation を参照しました。起動時間や電断耐性など、実機での測定は未実施です。したがって性能効果は推測です。

未取得・未調査事項は次の一覧にまとめます。bootchart の man7 は HTTP 404、OpenSSH sshd の man、Raspberry Pi の processors ページ、Arm の ID_AA64ISAR0_EL1 定義ページは取得できていません。BCM2837 の暗号拡張に関するメーカー一次仕様、`systemd.timer` の本文、BusyBox の NOFORK / NOEXEC 設定、mdev の仕様、WireGuard / OpenVPN / Dropbear / OpenSSH の CM0 実測値、IR・カメラの DT、brcmfmac firmware の取得元、SR9900A の実機 USB ID、Linux 7.2 / 7.3 の `bcm2711_defconfig` の PREEMPT 値も未確認です。
