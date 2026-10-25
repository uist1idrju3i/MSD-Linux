# 調査の前提・ハードウェア・候補

## 調査の目的と前提

M5Stack CardputerZero（Raspberry Pi CM0、BCM2837、RAM 512 MB、microSD）向けの MSD/Linux を検討するため、ハードウェア、Linux ディストリビューション、起動、ファイルシステム、更新方式を調べます。この記録でいう「ファームウェア」は Linux システムまたは OS イメージであり、MCU 向けファームウェアではありません。調査時点では実機を入手しておらず、ビルドと実測は未実施です。

## プロジェクトの設計条件

以下はプロジェクトの設計条件であり、外部資料で確認した事実とは区別します。

- 起動を数秒程度まで短縮することを目指し、電源断への耐性を重視する。読み取り専用 rootfs と A/B 更新を候補とし、常に 2 つ以上のシステムイメージを保持して失敗時に自動復旧できる方式を検討する。
- 起動後は CLI のみとし、GUI、回復モード、ブートメニューは必須にしない。CardputerZero の LCD、キーボード、音声、IMU、RTC、電池、Wi-Fi、Ethernet、IR、カメラなどの機能を維持する。
- M5 公式ドライバを前提にする。カーネルは LTS に限定せず新しいバージョンも比較し、PREEMPT_RT は対象外とする。カーネルを小さくし、デバイスの遅延読込みも検討する。
- カーネル圧縮、initramfs、btrfs の透過圧縮、SquashFS の配置順、読み取り専用構成での zram/zswap を調べる。カーネルログは SD に保存する案があり、開発中は ext4、電源断試験時は専用領域または pstore に切り替える方法を検討する。
- init、glibc/musl、Newlib、jemalloc 等のアロケータ、ユーザー領域の不要機能除去と遅延起動を比較する。将来の SSH/VPN も対象にする。
- Zephyr、Linux 系、Android、BSD 系、Debian、Arch、Buildroot、BusyBox、Yocto、Ubuntu Core、Minimal Ubuntu などを比較し、自作構成も検討する。一次資料の URL と、調査済み・未確認の区別を記録する。
- 実機到着後に開発へ移れるよう、起動測定、電源断試験、OTA、ハードウェア機能の確認方法を整理する。イメージ名の由来は [RESEARCH.md](../../RESEARCH.md) を参照する。

## 未決の設計論点

| 論点 | 選択肢・条件 | 状態 |
|---|---|---|
| 起動完了の定義 | A: LCD にプロンプトが表示され、キー入力できるまで。B: init（PID 1）が終点マーカーを書き、LCD・キーボードはその後に遅延読込みする。C: 両方を測定する。 | 未決。遅延読込みと LCD・キー入力までを起動時間に含める定義は両立しない。 |
| 読み取り専用 rootfs | SquashFS は `-sort` で優先度の高いファイルを先頭に配置できる。EROFS は `-z` を指定した場合に圧縮され、`--sort` は tar 入力に適用される。実機で 2 構成を比較する案。詳細は[電源断対策の調査](power-and-updates.md)を参照。 | 速度は未測定。 |
| init と libc | systemd 最小化＋glibc（M5 の udev ルール・unit を利用可能）、BusyBox init＋eudev＋musl 静的、自作 init（最終手段）。 | 全機能を維持する場合は glibc＋systemd が候補だが、起動時間は未測定。 |
| A/B 方式 | MBR＋tryboot/autoboot.txt＋RAUC custom、U-Boot 系（Mender・RAUC）、Rugix。GPT の採否も検討する。詳細は[更新方式の調査](power-and-updates.md)を参照。 | Raspberry Pi の文書は tryboot を全モデルに適用すると説明するが、CM0 での動作、watchdog、復旧は未検証。FAT の boot 領域は単一障害点となる。 |
| カーネル版 | 6.18.y（VOLUNTARY を選択可能）と 7.2.y・7.3.y（PREEMPT は LAZY/FULL のみ）を比較する。7.1 以降の DRM API 変更と 7.3 の alias unmap 再適用も考慮する。詳細は[カーネル調査](boot-and-kernel.md)を参照。 | CM0 の実機起動と M5 モジュールのビルドは未確認。 |
| 開発中ログ | 開発中は ext4 に書き、電源断試験時は専用領域または pstore に切り替える案。 | 完全 read-only 構成との両立と実装方式は未決。 |
| SSH/VPN | Dropbear または OpenSSH、WireGuard または OpenVPN を比較し、起動完了後に socket activation で開始する案。 | 未決。 |

## 未確認事項

- BCM2837（CM0）で tryboot、autoboot.txt、`kernel_watchdog_*` が動作するか。Raspberry Pi 文書は tryboot を全モデルに適用すると説明するが、CM0 の動作は未確認。確認先: https://www.raspberrypi.com/documentation/computers/configuration.html#tryboot
- 起動時間の基準値と最適化効果、SquashFS と EROFS、無圧縮と gzip カーネルの比較。実機で未測定で、公表値は条件が異なるため合算できない。
- A53 の Crypto Extension はオプション（Arm DDI 0501F）だが、BCM2837 に実装されているかの一次仕様と、SSH/VPN・耐量子鍵交換の CM0 実測は未確認。確認先: https://developer.arm.com/documentation/ddi0501/latest/
- 7.2/7.3 を CM0 で起動できるか、alias unmap の再適用が与える影響。コミットメッセージだけでは、RPi 3/4 の起動問題が解消したか判断できない。詳細は[カーネル調査](boot-and-kernel.md)を参照。
- M5 の名称・ロゴを第三者が利用する場合の公式ルールは未確認。確認先: https://docs.m5stack.com/
- Kickstarter の期間・金額・更新内容は本体が HTTP 403 で、一部 SNS も本文を確認できていない。詳細は[最新動向](scope-and-hardware.md#9-最新動向2026-10-18-時点)を参照。
- OpenVPN 2.7.6 と OpenSSL 3.6.4 の実接続で ML-KEM（X25519MLKEM768）が使われるか。ソース確認のみで、実機・実接続は未実施。詳細は[SSH・VPN・鍵保管の調査](ssh-vpn-and-keys.md)を参照。
- Raspberry Pi 3B+ の WP-1 ログにおける kernel の `Loaded` から `Device tree loaded` までの 2.63 s の内訳と、GPU 段のサイズ依存。実機未測定で、サイズ依存は推測。詳細は[起動・測定の調査](boot-and-kernel.md)を参照。
- Newlib に Linux 用の sys ディレクトリがないか。sourceware のページを取得できず未確認。確認先: https://sourceware.org/newlib/

## 確認度と出典の扱い

| 表記 | 意味 |
|---|---|
| 一次 | 引用した公開の一次資料（公式文書、公開ソース、公開 API 等）で裏付けた事項。 |
| 二次 | 公開された二次資料・第三者記事・SNS に基づく事項。元の事実は独立に未検証の場合がある。 |
| 未確認 | 公開情報で裏付けていない事項、取得できなかった事項、または実機検証が必要な事項。確認先の公開 URL やファイルパスを併記する。 |
| 推測 | 事実から導いた推論または設計案。実装・測定済みの事実とは区別する。 |
| 取得できず | URL への GET で 403/404/タイトルのみ/接続不可となり、本文を確認できなかった状態。 |

数値には対象 SoC と測定条件（始点・終点）を併記し、条件の異なる数値を合算しません。コンポーネントのバージョンと日付を記録します。日付のない一次資料の確認は 2026-10-18 時点です。コミット固定 URL はそのハッシュ時点のファイルを指します。HTTP 200 でも本文未読の場合、本文の内容は裏付け済みとは扱いません。取得日は 2026-10-18（JST）です。

## 用語

| 用語 | 意味 |
|---|---|
| CM0 | Raspberry Pi の Compute Module 0。CardputerZero の SoC は BCM2837（Cortex-A53）、DT 名は `bcm2710-rpi-cm0`。 |
| tryboot / autoboot.txt | Raspberry Pi ファームウェアの「次回 1 回だけ別パーティションから起動」する機能と設定ファイル。 |
| A/B OTA | 2 面のシステム領域を交互に更新し、失敗時に前の面へ戻す方式。 |
| MBR / GPT | パーティション表の方式。 |
| SquashFS / EROFS | 読み取り専用の圧縮ファイルシステム（`mksquashfs` / `mkfs.erofs` で作成）。 |
| overlayfs | 読み取り専用の下層に書込み可能な上層を重ねる仕組み。 |
| M5IOE1 / TCA8418 | M5 基板の IO エキスパンダ（LCD の RST/BL、LED 等の親）/ キーボードコントローラ。 |
| SW_DET / powerfail_suo | 電源スイッチ検知（G6）/ それを使う M5 のカーネルモジュール。 |
| SysRq | カーネルの緊急操作（s=sync、u=読み取り専用で再マウント、o=電源断）。 |
| mini-UART / PL011 | BCM283x の 2 種類の UART（前者はコアクロック依存、後者は Bluetooth に割当）。 |
| KEX / ML-KEM / sntrup761 | SSH の鍵交換 / NIST 標準の耐量子 KEM（ML-KEM-768）/ OpenSSH 系で先行した耐量子 KEM。いずれも X25519 とのハイブリッド。 |
| alias unmap | arm64 でカーネル data/bss の線形マップ上の別名を unmap する変更。 |
| pstore / ramoops | 再起動後にクラッシュログを読む仕組み（RAM または専用領域）。 |
| pi-gen / rpi-image-gen | Raspberry Pi OS イメージ作成ツール / Raspberry Pi 公式のイメージ生成ツール（A/B の image-rota を含む）。 |
| RAUC / SWUpdate / Mender / Rugix | OTA 更新フレームワーク。 |
| Buildroot / Yocto | 組込み Linux のビルドシステム。 |
| glibc / musl | C ライブラリ。 |

---

## ハードウェア機能の対応表

詳しくは [hardware-spec.md](hardware-spec.md) を参照してください。

## 調査範囲

- Zephyr 26.04 LTS と Linux ベースの方式を比較し、Ubuntu Core 26、Minimal Ubuntu、Buildroot、BusyBox、Yocto、Debian、Arch、Android、BSD 系、OpenBIOS、自作構成などを調べます。候補チップとして ESP32 での Linux 実行可否、nRF9151 単体と Zephyr も対象にします。
- 起動短縮（Boot Naked Linux、buildroot-quickpi、カーネル圧縮、ブート ROM から kernel8.img までの段階）、電源断対策（btrfs、UBIFS、ext3/ext4、overlayfs、read-only-rootfs、SquashFS、tmpfs）、公式 CardputerZero リポジトリ、MBR/GPT を対象にします。
- 追加の確認事項は、read-only 構成での zram/zswap、LCD のみを使う場合の起動時間、実際には HDMI の表示ドライバの遅延読込みです。
- 調査時点ではコンパイル、実機測定、電源断試験を行っていません。数値は測定条件と対象 SoC を添え、異なる条件の結果を合算しません。

## 誤解されやすい前提と訂正

| 誤解されやすい記述 | 正しい内容 | 出典 |
|---|---|---|
| 映像出力は DisplayPort | 回路図と製品資料に示されているのは HDMI で、DisplayPort は確認できません。 | https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf （P10 J5。ページの再照合は未実施） |
| UBIFS を microSD で使える | UBIFS は NAND/MTD と UBI を対象とします。microSD/eMMC での利用可否はカーネル文書で確認してください。 | 未確認。確認先: https://github.com/torvalds/linux/blob/master/Documentation/filesystems/ubifs.rst |
| 公式イメージは約 2.1 秒で起動する | 【二次】2.1 秒は M5 の自己申告で、227 KB の独自小型カーネルを読む構成の「ARM 起動まで」です。公式イメージ全体の起動時間ではありません。 | https://github.com/CardputerZero/circle-boot-splash/blob/b80d7c6a537c09c1ca233aeffa9c2e8601b113df/app/cardputerzero-splash/BENCHMARK.md#L14-L21 |
| `powerfail_suo` は S→U→O を実行する | SysRq-U（読み取り専用で再マウント）に加え、バックライトと GPIO を操作します。`'s'`、`'i'`、`kernel_power_off()` はコメントアウトされています。 | https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/powerfail_suo.c |

---

## 2. ハードウェア仕様

詳しくは [hardware-spec.md](hardware-spec.md) を参照してください。

## 3. 候補 OS 別の対応状況と起動時間

> CM0 でのベースライン実測値はありません。下表の起動時間は条件の異なる値を併記しており、足し算や平均はしていません。予測は推測として区別します。

| 候補（対象の版） | 対応状況・根拠 | 適合性・未確認事項 | 起動時間の根拠 | 出典 URL |
|---|---|---|---|---|
| Zephyr（Canonical Zephyr 26.04 LTS） | 【一次】発表ページの題名と日付は 2026-09-21。 | CM0 への対応、upstream 4.4 ベースか、Canonical のフォーク内容、公式 Raspberry Pi 対応の記載は未確認。 | 評価不能。 | https://ubuntu.com/blog/zephyr-lts-announcement |
| Zephyr v4.4.0 | 【一次】upstream の Raspberry Pi ボード一覧と v4.4.0 リリースを参照。CM0/BCM2710 のボード定義は未確認。 | CM0 対応は未確認。 | 評価不能。 | https://github.com/zephyrproject-rtos/zephyr/tree/684c9e8f32e4373a21098559f748f06915f950c9/boards/raspberrypi<br>https://github.com/zephyrproject-rtos/zephyr/releases/tag/v4.4.0 |
| Zephyr upstream main | 【一次】2026-10-16 時点の commit `a915b2f12` に `boards/raspberrypi/rpi_zero_2w` があり、PR #110189 は 2026-08-17 にマージ。 | ボードは単コアと mini-UART を備える。SDHCI 対応と microSD 利用可否は未確認。CM0 と同等の対応ではない。 | 評価不能。 | https://github.com/zephyrproject-rtos/zephyr/tree/a915b2f12675b48b16d56653ea145dcd8f20cbbf/boards/raspberrypi/rpi_zero_2w<br>https://api.github.com/repos/zephyrproject-rtos/zephyr/pulls/110189 |
| 公式 OS（CardputerZero/pi-gen、branch `cardputerzero_v1.0`、HEAD `791a985`、2026-10-08、Debian trixie） | 【一次】カーネル `6.18.39-1+rpt1` は SHA-256 検証、APT pin、hold の対象。M5 dtoverlays は `main` から `--depth=1` で取得し、実際に取得したコミットを記録しますが、branch tip は固定されません。`CONFIG_CARDPUTERO_V0_5=y`。 | GUI は labwc/Wayland。read-only、overlayfs、tryboot、RAUC、Mender、A/B OTA の有無は、参照した公開ファイルだけでは未確認。 | M5 の BENCHMARK.md は「Linux 可用 ~7〜9 s」とするが、自己申告で終点定義がなく、実測と概算を含む。GUI を含む起動時間の推定は未確認。 | https://github.com/CardputerZero/pi-gen/commit/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc<br>https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage0/02-firmware/files/kernel.pref#L3<br>https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage0/02-firmware/01-run.sh#L32<br>https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage2/05-cardputerzero/01-run.sh#L20<br>https://github.com/CardputerZero/circle-boot-splash/blob/b80d7c6a537c09c1ca233aeffa9c2e8601b113df/app/cardputerzero-splash/BENCHMARK.md#L14-L21 |
| Buildroot 2026.08（2026-09-04、`d5180309`） | 【一次】`raspberrypi3_64`/`zero2w_64` defconfig は 6.12.61 固定。GCC の既定は `BR2_GCC_VERSION_15_X`（15.3.0）、選択可能なバージョンは 14.4.0/15.3.0/16.2.0 です。CM0 専用 defconfig は未確認。確認先: 公開 `configs/`。 | 【推測】Buildroot はプロジェクト要件を構成で満たせる候補だが未検証。 | KittenLabs の Zero 2 W 構成は <3.5 s とする。これは電源から独自 userspace の GPIO まで、非圧縮 8.5 MiB カーネル、USB/HDMI/sound 無効、KASLR/Spectre 無効の条件で、CM0・M5 ドライバ・LCD を含まない。 | https://github.com/buildroot/buildroot/commit/d5180309b1b66ef3b8eaccca70ad69be8e0729a1<br>https://github.com/buildroot/buildroot/blob/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/package/gcc/Config.in.host#L6<br>https://github.com/buildroot/buildroot/blob/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/package/gcc/gcc.hash<br>https://github.com/buildroot/buildroot/blob/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/configs/raspberrypi3_64_defconfig#L12-L13<br>https://github.com/buildroot/buildroot/blob/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/configs/raspberrypizero2w_64_defconfig#L11-L12<br>https://github.com/buildroot/buildroot/tree/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/configs<br>https://kittenlabs.de/blog/2024/09/01/extreme-pi-boot-optimization/ |
| BusyBox 単独 | BusyBox は userland であり OS ではない。Buildroot の最小構成（既定 init は BusyBox）と同等の構成になる。BusyBox 1.38.0 は未確認。 | 単独の OS 候補ではない。 | 独立した根拠なし。 | https://busybox.net/downloads/ |
| Yocto（meta-raspberrypi、branch `wrynose`） | 【一次】`conf/machine/raspberrypi0-2w-64.conf`、`LAYERSERIES_COMPAT=wrynose`、`linux-raspberrypi_6.18.bb` がある。 | CM0 専用 machine の有無、Wrynose 6.0 の LTS 期間（2030-04 まで）は未確認。read-only-rootfs 機能があり、meta-rauc-community の Raspberry Pi 構成は U-Boot 方式。 | 【推測】構成次第で Buildroot に近い起動時間を目指せる。 | https://github.com/agherzan/meta-raspberrypi/blob/919588393f41b48cb6c5d832aa35e58a19b6762d/conf/machine/raspberrypi0-2w-64.conf<br>https://github.com/agherzan/meta-raspberrypi/blob/919588393f41b48cb6c5d832aa35e58a19b6762d/conf/layer.conf#L12<br>https://github.com/agherzan/meta-raspberrypi/tree/919588393f41b48cb6c5d832aa35e58a19b6762d/recipes-kernel/linux<br>https://wiki.yoctoproject.org/wiki/Releases |
| Minimal Ubuntu / Ubuntu Server 26.04.1 | 【一次】Imager 一覧には Raspberry Pi 3 対応の「Server 26.04.1」がある（2026-10-18 参照）。 | systemd が標準。A/B 機構の有無は未確認。 | 根拠なし。【推測】標準構成では GUI なしでも公式 OS 並みかそれ以上の可能性がある。 | https://downloads.raspberrypi.com/os_list_imagingutility_v4.json |
| Ubuntu Core 26（2026-06-05） | 【一次】Imager 一覧に pi3-64bit 向けがある（2026-10-18 参照）。最小 RAM 512 MB、最小ストレージ 1 GB、NAND 非対応、起動速度の how-to、Pi 4/5 が公式テスト対象という情報は未確認。 | snap の A/B 相当機構（recovery/seed）の有無は未確認。 | 根拠なし。snapd 初期化を含む実測値はない。 | https://downloads.raspberrypi.com/os_list_imagingutility_v4.json<br>https://ubuntu.com/core/docs |
| rpi-image-gen（公式、master `d7616a2`、2026-10-16。release v2.8.0、2026-08-13） | 【一次】device 層に pi3/zero2w/cm4/cm5/pi4/pi5 がある。image-rota は cm4/pi4/cm5/pi5 を対象とする。 | CM0 専用 device の有無は未確認。zero2w/pi3 の公式 A/B は成立しない。 | 公式ホワイトペーパー RP-010196-WP の数値は対象・条件を分けて参照する。 | https://github.com/raspberrypi/rpi-image-gen/blob/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/image/gpt/ab_userdata/image.yaml#L2-L11<br>https://github.com/raspberrypi/rpi-image-gen/tree/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/device<br>https://api.github.com/repos/raspberrypi/rpi-image-gen/releases<br>https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-010196-WP-1-Optimising%20boot%20time%20on%20Raspberry%20Pi%20single-board%20computers.pdf |
| Alpine 3.24.2（2026-09-17） | CM0 対応、linux-rpi 6.18.52 は未確認。 | diskless（RAM 常駐）は 512 MB では厳しい可能性がある。A/B は標準にないとの記述も未確認。 | 実測なし。 | https://wiki.alpinelinux.org/wiki/Raspberry_Pi |
| piCore64 17.0（2026-08-02、kernel 6.18.37） | RAM 展開型との情報は未確認。 | A/B は標準にないとの情報も未確認。 | 実測なし。 | http://tinycorelinux.net/ |
| Rugix Bakery/Ctrl（v1.3.0） | 【一次】（2026-10-19 確認）対応表は Pi 5/Pi 4（Tier 1）と CM4（Tier 2）を `rpi-tryboot`、Pi 3/Zero 2 W（Tier 2）と Pi 2 v1.2/Pi 2/Pi 1/Zero（Tier 3）を `rpi-uboot` とする。Pi 3 の制約は Rugix の対応 target によるもので、Raspberry Pi firmware は全モデルで tryboot に対応する。 | CM0 で Rugix を使うには実験的な U-Boot flow が必要で、firmware 更新ができないため、U-Boot を採用しない MSD の方針とは合いません。MSD 自身の tryboot 設計は影響を受けず、CM0 実機での確認は引き続き必要です。 | 実測なし。 | https://rugix.org/docs/bakery/devices/<br>https://rugix.org/docs/bakery/devices/raspberry-pi<br>https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/raspberry-pi/bootflow-eeprom.adoc#L91 |

---

## 4. 除外・保留した項目と理由

| 項目 | 判定 | 理由 | 出典 URL |
|---|---|---|---|
| Zephyr 26.04 LTS（Canonical） | 保留 | CM0 対応は未確認。 | https://ubuntu.com/blog/zephyr-lts-announcement<br>https://github.com/zephyrproject-rtos/zephyr/tree/684c9e8f32e4373a21098559f748f06915f950c9/boards/raspberrypi |
| Zephyr upstream main（rpi_zero_2w） | 保留（将来監視） | 単コアと UART のみ。SDHCI 対応は未確認のため、microSD が使えるか確認が必要。 | https://github.com/zephyrproject-rtos/zephyr/tree/a915b2f12675b48b16d56653ea145dcd8f20cbbf/boards/raspberrypi/rpi_zero_2w<br>https://api.github.com/repos/zephyrproject-rtos/zephyr/pulls/110189 |
| UBIFS | 除外 | UBIFS は raw MTD/UBI を対象とし、microSD の通常のブロックデバイスには適用しない。 | https://github.com/torvalds/linux/blob/master/Documentation/filesystems/ubifs.rst |
| ext3 | 独立候補から除外 | CONFIG_EXT3_FS は Linux 6.18 で削除され、ext4 ドライバに統合されたとの記述は未確認。確認先は Linux 6.18 の ext4 設定。 | https://github.com/torvalds/linux/tree/v6.18/fs/ext4 |
| btrfs | 保留 | microSD 上での COW が電源断時に保証される根拠は未確認。 | https://docs.kernel.org/filesystems/btrfs.html |
| F2FS | 保留 | Raspberry Pi の公式ホワイトペーパーは、電源断後の破損報告が多いと警告する。 | https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-003610-WP-3-Making%20a%20more%20resilient%20file%20system.pdf<br>https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L1641 |
| ext4 data=journal | 除外 | 現行 docs.kernel.org と Linux v7.3-rc7 の ext4.rst に、2028-01 の削除予定が記載される（raw ファイルの L175-176、L422-423）。v7.2、rpi-7.2.y、v6.18、rpi-6.18.y に該当記載がないかは未確認。 | https://docs.kernel.org/admin-guide/ext4.html<br>https://raw.githubusercontent.com/torvalds/linux/v7.3-rc7/Documentation/admin-guide/ext4.rst<br>https://github.com/raspberrypi/linux/tree/rpi-7.2.y/Documentation/admin-guide<br>https://github.com/raspberrypi/linux/tree/rpi-6.18.y/Documentation/admin-guide |
| Boot Naked Linux | 手法のみ参考 | QEMU 上の測定のみとの情報は未確認。TechFeed の記事 URL は特定できていない。 | 未確認。公開記事の URL を特定する必要がある。 |
| buildroot-quickpi | 手法のみ参考 | 2018 年で更新停止。対象は Pi 1 と 32bit Pi 3 のみ。 | https://github.com/johschmitz/buildroot-quickpi/commit/2f62ac8b7a1d2edb29aad7008f2c5f38aa5195a5<br>https://github.com/johschmitz/buildroot-quickpi/blob/2f62ac8b7a1d2edb29aad7008f2c5f38aa5195a5/README.md#L15-L16 |
| カーネルの LZ4/ZSTD/LZO 圧縮 | 【推測】標準構成では不可。armstub/TF-A で展開する余地は未確認。 | arm64 に HAVE_KERNEL_* 圧縮選択肢がないとの記述、start.elf（VPU）が読めるのは非圧縮か gzip との記述は未確認。rpi-eeprom #541 は Pi 4 の話で、timg236 はカスタム ARM stub や TF-A での展開に触れている。 | https://github.com/raspberrypi/rpi-eeprom/issues/541<br>https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc#L26-L52 |
| MCUboot | 除外 | VideoCore 起動で最初段になれないとの記述は未確認。 | https://docs.mcuboot.com/design.html |
| boot-mbr-switch | 除外 | ブートローダー領域の A/B 用で rootfs の A/B 用ではないとの記述は未確認。 | https://github.com/search?q=boot-mbr-switch&type=repositories |
| SWUpdate / Mender | 次点 | Raspberry Pi firmware（tryboot）との連携は未確認。Mender Client 6.1.0 は製品版との情報があるが、版は未確認。mender-convert は Raspberry Pi 3（64bit）を公式構成に持つ（U-Boot 方式、CM0 は未確認）。 | https://api.github.com/repos/sbabic/swupdate/releases/latest<br>https://docs.mender.io<br>https://github.com/buildroot/buildroot/blob/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/package/mender/mender.mk#L7<br>https://github.com/mendersoftware/mender-convert |
| rpi-image-gen の image-rota | CM0 では不採用 | 公式 A/B は Pi 4/5 クラスのみを対象とする。 | https://github.com/raspberrypi/rpi-image-gen/blob/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/image/gpt/ab_userdata/image.yaml#L2-L11<br>https://github.com/raspberrypi/rpi-image-gen/tree/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/device |
| GPU 段スキップ（rpi-open-firmware / lk-overlay） | 除外 | 実験的で対応 SoC と安定性が未確認。 | https://github.com/search?q=rpi-open-firmware&type=repositories<br>https://github.com/search?q=lk-overlay&type=repositories |
| Ubuntu Core / Minimal Ubuntu / BusyBox 単独 / Yocto | 優先度低 | A/B 機構と起動時間の根拠が不足。Yocto は代替候補。詳細は [候補 OS 別の比較](scope-and-hardware.md#3-候補-os-別の対応状況と起動時間) を参照。 | https://downloads.raspberrypi.com/os_list_imagingutility_v4.json |
| DisplayPort | 除外 | 製品の出力は HDMI。 | https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf<br>https://docs.m5stack.com/en/CardputerZero |

---

## 8. 公式 OS・公式リポジトリの状況

### 8.1 CardputerZero/pi-gen（branch `cardputerzero_v1.0`、HEAD `791a985`、2026-10-08）

【一次】公開ソースは Debian trixie arm64、labwc/Wayland、systemd を構成します。カーネル `6.18.39-1+rpt1` は APT pin され、`kernel-packages.sha256` で検証され、`apt-mark hold` の対象です。M5 dtoverlays は `main` から `--depth=1` で取得し、取得コミットを `/etc/cardputerzero-dtoverlays.commit` に記録しますが、branch tip は固定されません。`CONFIG_CARDPUTERO_V0_5=y` で、回路図は V0.6.1 です。

参照した公開ファイルだけでは、read-only、overlayfs、tryboot、RAUC、Mender、A/B の実装有無は未確認です。追跡ソースの確認先は [pi-gen の固定コミット](https://github.com/CardputerZero/pi-gen/commit/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc) です。M5 BENCHMARK.md は「Linux 可用 ~7〜9 s」と記載しますが、これは自己申告で、終点定義がなく実測と概算が合算されています。GUI を含む公式 OS の起動時間がそれより長いという見方は推測です。

- 既定アカウント `pi/raspberry` と `ENABLE_SSH=1` は公開 CI workflow の値です。配布イメージ全体の出荷時既定かは未確認です。first-boot ウィザード（piwiz/LaunchWizard）があり、OOBE は export 時に無効化されるとの情報も未確認です。確認先は [固定コミットの公開ソース](https://github.com/CardputerZero/pi-gen/commit/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc) です。Pi OS 本家が 2022-04 に `pi` ユーザーを廃止し、2026-04-13 から passwordless sudo も既定で無効にしたとの情報は未確認です。確認先: https://www.raspberrypi.com/documentation/computers/configuration.html#sudo
- CI の値がイメージに入る場合、SSH 有効と既定パスワードはセキュリティ上好ましくないという判断は推測です。実際の出荷イメージは未確認です。

出典:
- https://github.com/CardputerZero/pi-gen/commit/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc
- https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage0/02-firmware/files/kernel.pref#L3
- https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage0/02-firmware/files/kernel-packages.sha256
- https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage0/02-firmware/01-run.sh#L32
- https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage2/05-cardputerzero/01-run.sh#L20
- https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/.github/workflows/build.yml#L52-L54
- https://github.com/CardputerZero/circle-boot-splash/blob/b80d7c6a537c09c1ca233aeffa9c2e8601b113df/app/cardputerzero-splash/BENCHMARK.md#L14-L21

### 8.2 cardputer-zero-os / cardputer-zero-shell

- 【一次】2026-10-18 時点で `https://github.com/CardputerZero/cardputer-zero-os` と `https://github.com/CardputerZero/cardputer-zero-shell` は 404 でした。404 の原因（削除、非公開化、改名など）は未確認です。org API の一覧も公開確認先です。
- 【一次・Wayback】2026-06-23 の cardputer-zero-os snapshot（取得時刻 2026-06-24 04:56 JST）には Star 12、Fork 2、14 commits、About「system profile for running Raspberry Pi OS / Debian as a Cardputer Zero appliance」、Topics `community`/`third-party`、MIT とあります。README は内蔵画面を panel-mipi-dbi-spi → DRM/KMS → labwc → Wayland greeter と説明し、画像ではなく Raspberry Pi OS/Debian 向けの system profile としています。greeter→PAM→labwc→ZeroShell の記述もあります。内部 LCD は `panel-mipi-dbi-spi` と `cardputerzero,st7789v.bin`、HDMI は seat0/LightDM の別系統と記載されています。
- 【一次・Wayback】cardputer-zero-shell の Wayland 側にも 2026-05-27 の snapshot がありますが、内容は未確認です。
- 【推測】作者 liu weikai（vicliu624）の個人リポジトリは 2026-07-23T10:25:33Z（JST 19:25）に作成され、fork ではなく HEAD `7d9b078`（2026-06-08）です。org 配下の community/third-party リポジトリが org から外れ、作者個人に移った可能性がありますが、GitHub の削除・移管ログが公開 API で得られないため原因は未確認です。
- org の `.github` README（2026-08-11）に両リポジトリの記載がないとの情報は未確認です。確認先: https://github.com/CardputerZero/.github
- fork（vicliu624、stanley-fork）が残っていますが、中身と公式最新版との一致は未確認です。確認先: https://github.com/search?q=cardputer-zero-os&type=repositories

出典:
- https://github.com/CardputerZero/cardputer-zero-os
- https://api.github.com/orgs/CardputerZero/repos
- https://web.archive.org/web/20260623195631/https://github.com/CardputerZero/cardputer-zero-os
- https://web.archive.org/web/20260527131053/https://github.com/CardputerZero/cardputer-zero-shell
- https://github.com/vicliu624/cardputer-zero-os

### 8.3 更新機構・周辺ツール

【一次】公開情報には .deb の APT リポジトリ（CardputerZero/packages、m5stack/CardputerZeroRepository）、launcher の updater、M5 Imager があります。参照した公開ファイルだけでは OS イメージやカーネルの A/B OTA の有無を確認できません。AppBuilder と Template（LVGL/SDL3）も公開されています。dev.cardputer.cc と cardputer.cc（Hub）の情報は未確認です。

出典:
- https://github.com/CardputerZero/packages
- https://github.com/m5stack/CardputerZeroRepository
- https://github.com/CardputerZero/Template
- https://github.com/m5stack/CardputerZero-AppBuilder
- https://dev.cardputer.cc/
- https://cardputer.cc/

---

## 9. 最新動向（2026-10-18 時点）

### 9.1 公式

- 【未確認】Kickstarter の期間は 2026-05-26〜07-03、支援者 13,644 人、調達額 HK$14,960,226（目標 HK$78,500）、更新 13 件、最終更新 2026-10-16 との情報があります。数値は WebSearch・BackerKit・BackerLens 等に由来し、Kickstarter 本体は HTTP 403（Cloudflare）で本文を読めていません。
  - 通常版は Super Early Bird $89 / Early Bird $104 / KS Special $119 / MSRP $149。Lite 版は $59 / $69 / $79 / MSRP $99。2 台セットは $238。
  - 出荷目標は 2026 年 11 月頃です。
- 【二次】Update 13「CardputerZero Update: The First 3,000 CM0s Are Here — Production Software Is Ready!」は、X のリンクカード本文の引用に基づく公式更新です。引用は「the first 3,000 CM0 units have finally arrived! The second batch of 12,000 units is currently expected to arrive by the end of October… We plan to begin shipping the first batch in November. The second batch will also begin shipping in November once the CM0 modules arrive and production is completed.」です。Kickstarter 本文全体は読めていません。「Production Software Is Ready!」の内容も未確認です。
- 【一次】@M5Stack は 2026-10-16 に「The first batch of CM0 arrived.」と投稿しました。CM0 入荷であり、製品出荷開始を意味しません。
- 【一次】英語マニュアル PDF は公開されています。公開日は 2026-09-28 との情報がありますが、その日付は未確認です。
- 【一次】GitHub の CardputerZero org API は公開リポジトリ 33 件を示します（取得値）。別の公開一覧は 34 件という記録があり、差異は未確認です。主な更新日は packages（10/17）、cardputerzero.github.io（10/17）、Template（10/12）、pi-gen（10/08）、launcher（09-28、60★）、AppBuilder（52★）です。circle-boot-splash は archived、org に u-boot（2026-06-11）があるという情報は未確認です。https://api.github.com/orgs/CardputerZero/repos?per_page=100<br>https://github.com/orgs/CardputerZero/repositories

出典:
- https://www.kickstarter.com/projects/m5stack/cardputerzero
- https://www.kickstarter.com/projects/m5stack/cardputerzero/posts/4829886
- https://x.com/saitotetsuya/status/2111008950107910198
- https://x.com/M5Stack/status/2110949681601871946
- https://m5stack.oss-cn-shenzhen.aliyuncs.com/resource/docs/static/pdf/static/en/CardputerZero.pdf
- https://api.github.com/orgs/CardputerZero
- https://api.github.com/repos/CardputerZero/circle-boot-splash
- https://github.com/CardputerZero/u-boot

### 9.2 コミュニティ・SNS（未確認）

- 日本にも発送されたとの投稿（@Tokagetchi、10/16）、11 月に届く可能性があるとの投稿（@k2kkrm、10/17）は未確認です。投稿 URL は特定できていません。
- 【二次】Klipper 動作（@Rw7DVtscPX、10/17、KlipperDeckZero）は公開投稿で確認できます。
- PocketJS 移植（@pocket_js、2026-09-11）、ZeroRadio の CardputerZero Store 掲載（2026-10-17）、Dirtywave M8 風トラッカー（開発中）、OpenELAB のカメラデモ（2026-09-28）は未確認です。ZeroRadio に関する投稿以外は URL を特定できていません。
- openboardsguide の試用記事（Debian 13.6、パッケージ取得中のフリーズ、Wi-Fi 切断、試作機）は未確認で、出典 URL を特定できていません。
- TELEC の遅延（gearinhere、2026-09-16）は未確認です。FCC/CE/TELEC の取得状況も未確認です。
- 第三者による CardputerZero の起動時間実測、電源断や OTA の公開情報は未確認です。確認先として CNX、Hackaday と M5 の BENCHMARK.md を参照してください。

出典:
- https://x.com/Tokagetchi
- https://x.com/k2kkrm
- https://x.com/Rw7DVtscPX/status/2111293684952289420
- https://x.com/HarrisonXu1998/status/2111387043775512697
- https://x.com/pocket_js
- https://x.com/gearinhere
- https://www.cnx-software.com/
- https://hackaday.com/
- https://github.com/CardputerZero/circle-boot-splash/blob/b80d7c6a537c09c1ca233aeffa9c2e8601b113df/app/cardputerzero-splash/BENCHMARK.md#L14-L21

---
