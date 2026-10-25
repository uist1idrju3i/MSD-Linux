# CardputerZero 向け MSD/Linux 調査記録

## 目的と前提

MSD/Linux は Muromi Software Distribution / Linux の略で、開発場所の近くを流れる福岡県の室見川から名前をとりました（[名称](#名称)）。M5Stack CardputerZero（標準版・Lite 版の両方）向けに、再現可能な Linux イメージを作ることを目指します。

外部の事前調査を出発点に公開資料で再確認し、確認度は各行の出典に基づいて示しています。

### 決定済みの方針

- ベースは Buildroot。M5 のドライバと Raspberry Pi カーネルを組み込む。
- UI は LCD のテキストコンソールと内蔵キーボードによる CLI のみ。公式 LVGL ランチャー、公式アプリ、Debian `.deb` 互換は目標にしない。
- 標準版と Lite 版を同じイメージで扱う。Lite 版にも microSD スロットはあるが、microSD カードは付属しない。
- 起動を速くし、突然の電源断に備えて rootfs を読み取り専用にし、更新失敗時は A/B の前のスロットへ自動復帰することを目指す。
- SSH・VPN は調査対象にとどめ、実装しない。
- リポジトリのライセンス方針は GPL-2.0-or-later。配布物ごとのライセンスとソース提供に注意する。
- 開発中。実機の出荷は 2026 年 11 月に始まる予定（[最新動向](docs/research/scope-and-hardware.md#9-最新動向2026-10-18-時点)）。起動イメージは CI で作り QEMU で起動を確かめているが、実機では試していない。起動時間の目標値は実機測定後に決める。

### 概略アーキテクチャ案

| 層 | 方針 |
|---|---|
| ビルド | Buildroot 2026.08、BR2_EXTERNAL として管理 |
| カーネル | Raspberry Pi `rpi-6.18.y` を基準にし、コミットを固定 |
| 起動 | Raspberry Pi firmware と `autoboot.txt` / `tryboot` による A/B を調査・実装する。CM0 実機で要検証 |
| rootfs | SquashFS を読み取り専用で使う案を第一候補とし、EROFS と実機比較する |
| 可変データ | 小さな書込み可能領域と tmpfs overlay を検討。領域・ファイルシステムは電断試験後に決める |
| UI | ST7789V3 の LCD に fbcon を使う CLI と、TCA8418 内蔵キーボード |

## ハードウェア

以下の表は公開資料で確認したハードウェア情報です。Devin が 2026-10-18 に公開資料で確認しました。

| 項目 | 確認内容 |
|---|---|
| SoC | Raspberry Pi CM0（RP3A0 / BCM2837）、Cortex-A53 4 コア、1 GHz、aarch64、LPDDR2 512 MB |
| ストレージ | microSD のみ。標準版 C154 は 32 GB カード付き、Lite 版 C155 はカードなしだがスロットあり |
| LCD | ST7789V3、320×170、SPI0（MOSI G10、SCLK G11、DC G25、CS G8、TE G5）。RST と BL は M5IOE1（I2C 0x4F）の PYG12 / PYG10 |
| キーボード | 46 キー、TCA8418（I2C 0x34、INT G27）。リセット PYG3 は USB ハブ GL852G と共用 |
| I2C1 | G2/G3 に ES8389（0x10）、TCA8418（0x34）、BMI270（0x68）、RX8130CE（0x32）、M5IOE1（0x4F）。BMM150 は BMI270 の裏側 |
| 音声 | ES8389 + I2S（G18〜21）、AW8737A アンプ EN=G24、HP_DET=G17 |
| USB | Host/Slave スイッチあり。Host 時は GL852G 経由で SR9900A Ethernet、USB-A、左 Type-C、HAT。Slave 時は右 Type-C が CM0 に直結し、ADB / rpiboot に使う |
| 電源 | 1750 mAh、BQ27220 燃料計、スイッチ検出 SW_DET=G6、PWR_DET / PWR_EN は M5IOE1 |
| その他 | IR TX G12 / RX G13、HY2.0-4P（既定 UART G14/G15、G4 で I2C に切替）、EXT 14P、HDMI 出力、IMX219 カメラ（Lite 版にはない） |
| 製品状態 | M5 の製品ページは Work in progress、SDK / Kernel ページは coming soon |

出典: [M5Stack CardputerZero](https://docs.m5stack.com/en/CardputerZero)、[回路図 V0.6.1](https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf)。

## 公式ソフトウェア構成

公式イメージ（pi-gen による Raspberry Pi OS 派生）、カーネル、M5 ドライバの構成と、よくある誤解の訂正は、[公式ソフトウェア構成](docs/research/official-software.md) に分けました。

### 詳細な調査記録

本文の条件、数値、確認度、根拠 URL を含む調査記録は、次の文書に分割しています。

- [調査の前提・ハードウェア・候補](docs/research/scope-and-hardware.md)
- [起動高速化・カーネル](docs/research/boot-and-kernel.md)
- [起動時間の実測と分析](docs/research/boot-time-measurements.md)
- [カーネル縮小](docs/research/kernel-size.md)
- [ハードウェア仕様と機能対応表](docs/research/hardware-spec.md)
- [シミュレーション検証計画](docs/research/simulation-plan.md)
- [sysctl の既定値](docs/research/tunables-sysctl.md)
- [モジュールパラメーター](docs/research/tunables-module-params.md)
- [公式サイトの HTML・CSS](docs/research/site-html-css.md)
- [電源断耐性・A/B 更新](docs/research/power-and-updates.md)
- [ストレージ・SD カード・フラッシュ測定](docs/research/storage-and-flash.md)
- [セキュリティ・ハードニング](docs/research/security-hardening.md)
- [ハードウェア機能の対応表](docs/research/hardware-spec.md#ハードウェア機能の対応表)
- [公式ソフトウェア構成](docs/research/official-software.md)
- [ユーザー空間・libc 調査](docs/research/userspace-and-security.md)
- [SSH・VPN・鍵保管の調査](docs/research/ssh-vpn-and-keys.md)
- [未確認事項・測定・調査限界](docs/research/measurement-and-planning.md)
- [訂正済み事項](docs/research/corrections.md)
- [出典一覧と URL 取得記録](docs/research/sources.md)
- [高速起動記事とCortex-A53調整](docs/research/fastboot-and-cpu-tuning.md)
- [CPU・割り込み・sysctl の調整余地](docs/research/cpu-irq-and-sysctl.md)
- [調整項目の全一覧（QEMU で取得した既定値）](docs/research/tunables-defaults.md)
- [開発環境と CI の選定・予備的な測定](docs/research/dev-environment-and-ci.md)
- [CI・Issue・リポジトリ設定の点検（2026-10-20）](docs/research/repo-operations-review.md)
- [作業の振り返りと残タスク（2026-10-22）](docs/research/retrospective-2026-10.md)
- [読み取り専用領域・ファイルシステム・障害試験](docs/research/readonly-data-and-fs.md)
- [ファイルシステムの候補と設計例](docs/research/fs-candidates.md)
- [和柄（日本の伝統文様）の調査とロゴ・サイトでの採否](docs/research/wagara.md)

### この記録に含めないもの

特定の外部製品比較、商標の個別確認、レポートの版管理情報は収録対象外です。名称の由来は本書に残します。

## 起動時間（実測値と分析）

詳しくは [boot-time-measurements.md](docs/research/boot-time-measurements.md) を参照してください。実機では未測定です。QEMU での段階ごとの測定では、`CONFIG_FTRACE` を無効にすると `MSD/Linux ready` が icount で 37.88 %、TCG で 5.68 % 早くなりました（[実験記録](docs/experiments/2026-10-20-qemu-boottime.md)。製品の設定は未変更）。

## 高速化のアイデア一覧

詳しくは [fastboot-ideas.md](docs/research/fastboot-ideas.md) を参照してください。

## 電源断耐性

### 方針と候補

- rootfs は SquashFS の読み取り専用領域を第一候補にする。設定・ログ等の書込みを分離し、必要なら overlayfs の upper を tmpfs / zram に置く。
- 永続領域は小さく保つ。ext4 の `data=ordered`、`metadata_csum`、一時ファイルへの書込み後 `fsync` + `rename` を候補とし、ファイルシステムと SD の実電断試験で選ぶ。
- `/boot` は通常読み取り専用とし、更新時だけ書き込む。FAT の `autoboot.txt` も単一障害点になり得る。
- microSD の FTL が書込み中の電源断で無関係なデータを壊す可能性は、公開一次資料で確認できていません。未確認を前提に、更新中以外の書込みを減らします。A/B の非稼働スロットが常に無傷とは保証しません。
- F2FS は Raspberry Pi の white paper が電断後の破損について警告しているため保留。btrfs は microSD 上での電断保証を確認できず保留。UBIFS は生 MTD 向け、microSD では対象外。ext3 が Linux 6.18 で独立候補ではなく ext4 に統合済みとの情報は未確認です。確認には Linux 6.18 の公開 source tree の `fs/ext3` と `fs/ext4` を照合します。
- ext4 の `data=journal` は kernel 文書の最新版と 7.3-rc7 で非推奨（2028 年 1 月に削除予定）とされていますが、6.18 / 7.2 の該当文書には記載がありません。通常案は `data=ordered` です。最新版の注意を過去 kernel に誤って当てはめないよう、[最新版](https://docs.kernel.org/filesystems/ext4/journal.html)、[7.3-rc7](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/Documentation/filesystems/ext4/journal.rst?id=v7.3-rc7)、[6.18](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/Documentation/filesystems/ext4/journal.rst?id=v6.18)、[7.2](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/Documentation/filesystems/ext4/journal.rst?id=v7.2) の記述を分けて確認します。
- 電源喪失保護（PLP）付き SD の研究・ベンダー主張は microSD 製品で確認が必要。pSLC は eMMC 向けで microSD には適用できないとの調査。スーパーキャパシタは筐体上難しいとの見立て。
- `dm-verity` は rootfs 検証の候補だが、BCM2837 に SHA 命令がない可能性があり、読み込み時のソフトウェア検証負荷は未測定。A/B 切替時のみ検証する案も未確認。
- `powerfail_suo` は GPIO6 の立下り後 500 ms debounce し、実装上は SysRq `u`（read-only 再マウント）のみ実行する。`s` と poweroff はコメントアウトされ、バックライトを消し `disabled-gpios` も駆動する。overlay に gpio-keys entry はなく、ユーザー空間へ電源断イベントを届けて正常停止する経路も未実装です。したがって突然の電池抜けや枯渇を救う機能ではない。
- zram は RAM 上の block device なので read-only rootfs と併用できる見込み。zswap は swap 先を必要とし、SD swap を避けるなら zram swap と同時に有効化しない案。実機では未検証。

出典: [overlayfs docs](https://docs.kernel.org/filesystems/overlayfs.html)、[ext4 docs](https://docs.kernel.org/admin-guide/ext4.html)、[Raspberry Pi resilient filesystem white paper](https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-003610-WP-3-Making%20a%20more%20resilient%20file%20system.pdf)、[M5 powerfail driver](https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/powerfail_suo.c#L93-L115)。

### 電源断試験

起動時間測定・電断試験・障害解析は別モードにし、記録方式で結果を汚さないようにする。起動測定時はログを最小化し、UART と ext4 ログを無効にする。電断試験では USB-UART 経由で給電が回り込まないようにし、pstore/ramoops（リセット時のみ）、専用領域への追記、または電断後の外部回収を比較する。SysRq `s` / `u` / `b` はソフトな近似で、本物の電断試験の代用ではない。試験回数、書込み中の電断、アイドル時の電断、起動不能数を記録する。

電断時の block I/O 順序を評価する候補として、`dm-flakey`、`dm-log-writes`、CrashMonkey 等の障害注入があります。これらは実カードの FTL を再現するものではなく、実物の電源遮断試験も別途必要です。

出典: [ramoops docs](https://docs.kernel.org/admin-guide/ramoops.html)、[pstore block docs](https://docs.kernel.org/admin-guide/pstore-blk.html)、[SysRq docs](https://docs.kernel.org/admin-guide/sysrq.html)。

## A/B 更新

### tryboot と制約

- Raspberry Pi の文書は全モデルが tryboot に対応すると記載する。`autoboot.txt`、`[tryboot]`、`tryboot_a_b=1` で起動パーティションを切り替え、`reboot "0 tryboot"` で一度だけ試行する仕組みが説明されている。CM0 実機での確認は未実施。
- `PARTITION_WALK` は EEPROM 機能で Pi 4 以降のみ。CM0 の復旧策として使えない。
- 人手の recovery menu は設けず、自動ロールバックを目標とする。設計案は非稼働スロットへ書き込み、tryboot で試行し、選択した終点とヘルスチェックを通ってから既定スロットを確定する。終点判定は LCD + keyboard と PID 1 marker の両方を記録する案。失敗・再起動時の復帰動作、FAT 更新の原子性、試行回数カウンタは実機で確認する。
- ウォッチドッグの `kernel_watchdog_timeout` / `kernel_watchdog_partition`、BCM2835 WDT、systemd の watchdog 連携は候補だが、BCM2837 firmware でどの機能が有効か未確認。最初の実機試験は tryboot と watchdog の確認。
- boot パーティション（FAT）と Raspberry Pi firmware 自体は A/B 化されず、単一障害点になり得る。試行中の電断・`autoboot.txt` 更新中の電断も検証が必要。

### 更新フレームワーク比較

| 方式 | 調査結果 | 判断 |
|---|---|---|
| 自作 + tryboot | CM0 の公式実装は見つからず、独自の試行カウンタ / 確定判定が必要 | Buildroot の構成に合わせる有力案。ただし設計・実装・電断試験が必要 |
| RAUC | Raspberry Pi firmware 初期対応 PR #1599 は調査時点で未マージ。tryboot 用 custom backend が必要になる可能性 | 候補。カウンタや primary 起動失敗時の挙動を調査する |
| SWUpdate | tryboot 連携を確認できず | 次点 |
| Mender | Buildroot 統合は古い系列。mender-convert の RPi3 64-bit は U-Boot 方式、CM0 構成は未確認 | 次点。U-Boot を使わない方針と整合確認が必要 |
| rpi-image-gen `image-rota` | GPT A/B 層は cm4/pi4/cm5/pi5 限定。zero2w / pi3 の device 層はあるが A/B 層は対象外 | CM0 の直接的な公式構成ではない |
| MCUboot / boot-mbr-switch | VideoCore boot の先頭になれないという見立て。`boot-mbr-switch` は rootfs A/B ではなく bootloader 領域向け | 優先しない |

GPT と MBR の CM0 での挙動は未確認。MBR は安全側との見立てがある一方、複数 boot / rootfs パーティションに主パーティション 4 個の制約があるため、レイアウトは実機ブートで決める。RAUC custom backend を使う場合も、FAT 単一障害点と失敗復帰を別途扱う。

出典: [autoboot.txt docs](https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/autoboot.adoc#L36-L83)、[watchdog config docs](https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc#L242-L271)、[BCM2835 WDT driver](https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/watchdog/bcm2835_wdt.c)、[rpi-image-gen A/B layer](https://github.com/raspberrypi/rpi-image-gen/blob/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/image/gpt/ab_userdata/image.yaml#L2-L11)、[RAUC PR #1599](https://github.com/rauc/rauc/pull/1599)、[Rugix devices](https://rugix.org/docs/bakery/devices/)。

## ストレージとフラッシュの要点

現行 CI イメージの MBR パーティション開始セクターは p1–p7 = `1 / 32769 / 163841 / 294913 / 294914 / 819203 / 1343492` です。各値の 4 KiB 境界からの余りは `1 / 1 / 1 / 1 / 2 / 3 / 4` セクターで、4 MiB 境界からの余りも同じです（1 セクター = 512 bytes）。genimage v20 で測定した `align=4M` 案では全開始位置が 4 MiB 境界にそろい、イメージは 736 MiB（現行より約 16 MiB 増）になりました。速度・寿命・電断耐性への効果は実機で未確認です。【実測】【未確認】[詳細と比較表](docs/research/storage-and-flash.md)

FAT データ領域はパーティション開始位置から 292 セクター（149,504 bytes）後に始まります。現行 p2 の絶対位置は 4 MiB 境界から 150,016 bytes ずれ、パーティション整列だけでは FAT 内部の BPB／データ領域 offset は変わりません。現行 `/data` は `data=journal` で、ext4 の現行文書はこの mode を非推奨とし、2028 年 1 月の削除予定を記載しています。`data=ordered` は移行候補ですが、アプリの `fsync`／rename と電断試験なしに同等の耐久性は主張できません。discard／fstrim、A1／A2、AU・消去単位はカードとホストで実測します。【一次】【実測】【推測】[用語、ext4、discard、測定計画](docs/research/storage-and-flash.md)

CI artifact の `/data` ext4 は `dumpe2fs` で 1,024 B ブロックと実測しました。これは 4 KiB page より小さい設定です。genimage の `extraargs` と実行時 formatter の両方に `-b 4096` を指定する案がありますが、page 境界との整合が性能や耐久性を高めるかは未測定で、効果は【推測】です。[実測値と mke2fs の選択理由](docs/research/storage-and-flash.md)

## セキュリティとハードニングの要点

microSD を物理交換できる攻撃者は Linux より前の起動ファイルを差し替えられます。Raspberry Pi の secure-boot 手順は Pi 4 以降が対象で、BCM2837 向け経路は文書化されていません（物理的に不可能とは断定しません）。現行 updater は `manifest.sig` を検証し、SHA-256 manifest と書込み後の read-back を確認します。鍵や dm-verity root digest を同じカードに置いても、カード全体の交換を防げません。【一次】【未確認】[脅威モデルと A/B/C 案](docs/research/security-hardening.md)

署名検証と読み取り専用 rootfs への公開鍵配置は実装済みです。今後は署名鍵のリリース・更新・失効手順、カーネル／sysctl のハードニング、不要な無線／USB 機能の採否を検討します。dm-verity は信頼できる digest の保管が条件です。起動・RAM・保守コストとハードウェア機能への影響、QEMU で検証できる更新処理と実機でしか検証できない BootROM／OTP・周辺機器を区別します。【一次】【推測】【未確認】[詳細と検証境界](docs/research/security-hardening.md)

## アイデア総覧

詳しくは [ideas-overview.md](docs/research/ideas-overview.md) を参照してください。

## QEMU で検証できる範囲

QEMU の `raspi3ap` と `raspi3b` は BCM2837 SoC をエミュレートしますが、Raspberry Pi の GPU ファームウェアや `tryboot`、CardputerZero の LCD・内蔵キーボード・M5 I2C デバイスは再現しません。`test-boot.sh` と `test-ab.sh` は p5／p6 の rootfs 起動後に `MSD/Linux ready` marker と login prompt を確認します。ホストテストでは更新処理の slot 判定・切替ロジックを確認します。ファームウェアによる tryboot、自動 rollback、実機周辺機器は実機検証の対象です。

## OS ベース比較

以下は公開資料で確認した OS 候補の比較です。値や互換性は出典に記載された条件とともに示し、本リポジトリでは試していません。

| 候補 | 調査結果 | 起動 / 要件への評価 |
|---|---|---|
| Buildroot 2026.08 | `raspberrypizero2w_64_defconfig` と `raspberrypi3_64_defconfig` があります。CM0 専用 defconfig の有無は未確認です。GCC 既定は 15.3.0 | 最小化・独自 A/B に適しそうとの推測です。Zero 2 W で <3.5 s の第三者値は条件が大きく異なります |
| 公式 CardputerZero pi-gen | Debian trixie / systemd / labwc、kernel 6.18.39 固定。追跡対象の公開ファイルでは A/B / RO 設定を確認できていません | M5 の現行ベースラインとして有用です。Linux 可用 7〜9 s は終点定義がありません |
| Yocto / meta-raspberrypi | `raspberrypi0-2w-64.conf` と `linux-raspberrypi_6.18.bb` があります。CM0 専用 machine の有無は未確認です。read-only-rootfs は利用可能です | Buildroot の代替です。ビルド・学習負担が大きく、起動時間の比較値はありません |
| Ubuntu Server / Minimal Ubuntu 26.04.1 | Imager 一覧に Pi 3 向け Server がある | 起動時間・A/B の根拠なし。systemd 標準 |
| Ubuntu Core 26 | Imager 一覧で pi3-64bit 向けを確認。最小 RAM / ストレージや起動高速化資料は未確認 | snap の recovery / seed が A/B 相当か未確認、秒数もなし |
| rpi-image-gen | Pi 3 / Zero 2 W の device 定義あり。`image-rota` は Pi 4 / 5 クラスのみ | CM0 の公式 A/B 構成には使えない |
| Zephyr v4.4 / Canonical Zephyr 26.04 | v4.4 に `rpi_zero_2w` / `bcm2710` 定義がないとの記述がありますが、公開 tree で未確認です。Canonical fork も未確認です | upstream main の Pi Zero 2 W 定義と SDHCI 対応状況は未確認です。CM0 対応は評価できません |
| Alpine 3.24.2 / piCore64 17.0 | CM0 対応、kernel 6.18 系との情報がありますが、公開資料の確認が未完了です | A/B と起動時間の根拠はありません。RAM 展開型は 512 MB で厳しい可能性があります |
| BusyBox 単独 | OS ではなく userland。Buildroot の最小構成で利用できる | kernel / firmware は Buildroot と共通。独立した起動時間根拠なし |
| Rugix Bakery / Ctrl | 【一次】（2026-10-19 確認）対応表では Pi 5/Pi 4（Tier 1）/CM4（Tier 2）が `rpi-tryboot`、Pi 3/Zero 2 W（Tier 2）と Pi 2 v1.2/Pi 2/Pi 1/Zero（Tier 3）が `rpi-uboot`。Pi 3 の制約は Rugix の target による | Raspberry Pi firmware は全モデルで tryboot に対応します。CM0 で Rugix を使うには実験的な U-Boot flow が必要で、firmware 更新不可のため U-Boot 非採用の MSD 方針とは合いません。MSD 自身の tryboot 設計は影響を受けず、CM0 実機確認は継続します |
| Android / BSD / RTOS / OpenWrt | 512 MB / CLI、M5 Linux ドライバ非対応、または kernel 6.12 系という理由で優先外 | FreeBSD 15.1 の Zero 2 W 対応は未確認です。LCD / keyboard / M5IOE1 も未確認です |

出典: [Buildroot 2026.08](https://github.com/buildroot/buildroot/commit/d5180309b1b66ef3b8eaccca70ad69be8e0729a1)、[Yocto meta-raspberrypi](https://github.com/agherzan/meta-raspberrypi/blob/919588393f41b48cb6c5d832aa35e58a19b6762d/conf/machine/raspberrypi0-2w-64.conf)、[Raspberry Pi Imager OS list](https://downloads.raspberrypi.com/os_list_imagingutility_v4.json)、[Zephyr Pi Zero 2 W board](https://github.com/zephyrproject-rtos/zephyr/tree/a915b2f12675b48b16d56653ea145dcd8f20cbbf/boards/raspberrypi/rpi_zero_2w)、[Rugix devices](https://rugix.org/docs/bakery/devices/)、[Rugix Raspberry Pi flow](https://rugix.org/docs/bakery/devices/raspberry-pi)、[Raspberry Pi bootflow](https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/raspberry-pi/bootflow-eeprom.adoc#L91)。

## カーネル

- `kernel8.img` は `pigz -11 -n` で作成し、gunzip 後に `Image` と一致することを検査する。実サイズはビルドログの `Kernel compression sizes` 行に記録する。この文書では未測定値を記載しない。
- 基準は `rpi-6.18.y` とします。RPi kernel 6.18.57、Buildroot 2026.08 の 2026-09-04 版を公開情報で確認しました。カーネルと M5 driver は commit 固定します。
- M5 DRM panel API が 7.1 で削除され、7.0 で ASoC API が変更されたとの情報は未確認です。確認には M5 driver と Raspberry Pi kernel の公開 tree を版ごとに比較する必要があります。M5 driver をそのまま build できるかは未確認です。6.18 を基準、7.2 は同一構成での比較候補とします。
- 6.18 から 7.2 で BCM2835 SD host / KASLR / 圧縮展開コードの変更がないとの調査。ただし BCM2837 の実測差はない。6.18 以降の起動時間に関係しそうな公開変更は条件付き、未マージ、または x86 / 大容量向けで、CM0 に適用できる証拠は乏しい。
- 6.18 arm64 は PREEMPT_NONE が既定で VOLUNTARY 選択可能との調査。7.2 では arm64 の PREEMPT_LAZY 機能により NONE / VOLUNTARY を選べないとの調査。起動時間への影響は未測定。PREEMPT_RT は対象外。
- 7.3 系で arm64 linear alias unmap の変更が再適用されたとの情報は、公開 commit history を確認できていないため未確認です。再適用後の Raspberry Pi 3 / CM0 起動も未確認です。確認先は [Raspberry Pi Linux 7.3.y source tree](https://github.com/raspberrypi/linux/tree/rpi-7.3.y/arch/arm64/mm) です。7.x 比較時は起動可否を先に確認します。
- M5 の v5 overlay 依存では I2C1 → M5IOE1 → LCD backlight / SPI0 panel、および keyboard / input の鎖を考慮する。optional driver は終点後に modprobe する案。
- arm64 kernel は firmware 起動で gzip または非圧縮を前提に評価する。LZ4 / ZSTD / LZO kernel 形式を標準起動で使う根拠は見つかっていない。カスタム ARM stub / TF-A は未確認。

出典: [RPi kernel rpi-6.18.y](https://github.com/raspberrypi/linux/tree/rpi-6.18.y)、[6.18 Kconfig.preempt](https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/kernel/Kconfig.preempt)、[7.2 Kconfig.preempt](https://github.com/raspberrypi/linux/blob/61d337138d273f134f41ef06eb0dd97c90123934/kernel/Kconfig.preempt)、[deferred probe change](https://github.com/torvalds/linux/commit/56e3ee721b33)、[Raspberry Pi boot docs](https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc#L26-L52)。

## init・libc

### init と周辺デバイス

M5 の udev ルールは `ID_PATH` で LCD / input device を識別して symlink と seat tag を設定し、LED に `chgrp` を実行する。LCD の `fb_load.service` は systemd unit。LCD panel は `request_firmware()` で `<compatible>.bin` を読む。M5 モジュールに `MODULE_DEVICE_TABLE` があるため modalias 自動ロードの余地はあるが、udev / mdev / modprobe の設定が必要。

BusyBox mdev は udev 形式のルールをそのまま使えない可能性があり、eudev を併用するか固定デバイスパスを使う必要がある。音声（ALSA / ASoC）、IMU（IIO）、カメラ（media / libcamera）、IR（rc-core）の上位ソフトがどこまで udev / systemd に依存するかは未調査。

### init の比較

| 観点 | systemd 最小化 | BusyBox init + mdev / eudev | 自作 init |
|---|---|---|---|
| M5 udev / unit 整合 | 高い | udev 移植または eudev が必要 | 全て自作 |
| 全機能維持の実装コスト | 低い | 中程度 | 高い |
| 並列起動 | 標準機能 | 自前で `::once` / background を設定 | 自由度は高いが自前 |
| サイズ・診断 | 大きいが journal 等の診断あり | 小さい | 最小だが診断も自作 |
| 起動時間の優位 | 未測定。unit 削減余地あり | 推測上大きい余地 | 推測上最大。ただし作り込み負担が大きい |

### libc / toolchain の調査

| 項目 | glibc | musl | uClibc-ng |
|---|---|---|---|
| Buildroot 2026.08 | 選択可能、systemd の Buildroot 設定で必須 | 選択可能 | 選択可能 |
| 主な制約 | 大きめ | NSS / nss-systemd や DynamicUser 等の差。lazy binding なし、`dlclose` no-op、locale / iconv の範囲が異なる | aarch64 PIE 条件、SSP 既定値など要確認 |
| ライセンス | LGPL-2.1+ | MIT | LGPL-2.1+ |
| CM0 起動比較 | 現行 aarch64 の比較値なし | 同左 | 同左 |

Buildroot 2026.08 の BusyBox 1.38.0、binutils 2.45.1、glibc 2.44、musl 1.2.6、uClibc-ng 1.0.59、systemd 258.7、RAUC 1.15.2、SWUpdate 2026.05.1 と、Yocto Wrynose 6.0 が glibc / musl を選べるとの情報は未確認です。確認先は [Buildroot 2026.08 package tree](https://github.com/buildroot/buildroot/tree/2026.08/package) と [Yocto release documentation](https://docs.yoctoproject.org/releases.html) です。

公開 microbenchmark は Intel Atom N280 / x86 や x86_64 の値で、Cortex-A53 の比較にはできません。Zero 2 W の 3.5 秒事例は full glibc であり、特定 libc が起動を速める証拠ではありません。mimalloc は自社 benchmark の主張と合成 benchmark への注意書きがありますが、CM0 の起動時間値はありません。jemalloc は未調査です。静的 BusyBox + musl は軽量案、systemd と全 M5 udev / unit の流用を優先するなら glibc 案という設計案は推測です。

出典: [Buildroot toolchain options](https://github.com/buildroot/buildroot/blob/2026.08/toolchain/toolchain-buildroot/Config.in)、[systemd Buildroot config](https://github.com/buildroot/buildroot/blob/2026.08/package/systemd/Config.in)、[musl functional differences](https://wiki.musl-libc.org/functional-differences-from-glibc.html)、[musl comparison](https://www.etalabs.net/compare_libcs.html)、[uClibc-ng](https://uclibc-ng.org/)、[M5 udev / systemd files](https://github.com/m5stack/m5stack-linux-dtoverlays/tree/75518549a2640486f5d13ea72ca4935b198d7c20/modules)。

## ログと観測

### 開発中の観測方法

- UART: M5 の資料では HY2.0-4P と EXT 2.54-14P に G14 / G15 がある。G4 の切替で I2C1 / UART を切り替える。EXT の物理ピンは RX=12、TX=14。3.3 V logic。GPIO14/15 の最終 pinmux と UART 種別は M5 overlay / config 実機確認が必要。`enable_uart=1` が mini-UART の core frequency を固定する場合があり、速度測定に影響し得る。
- USB gadget serial: `g_serial` で `/dev/ttyGS0` を作れる。右 USB-C が OTG slave のときのみ CM0 直結し、host 側の hub / Ethernet / USB-A は同時に使えない。公式 config は `dwc2,dr_mode=host` のため gadget 運用は別設定が必要との推測。
- Ethernet SSH は実装しない。Ethernet は USB 2.0 の SR9900A、10/100 Mb/s。実際の USB ID とドライバは未確認。
- pstore / ramoops は panic / watchdog 等の reset 再起動後のログ候補。完全な電源断では RAM が消える。予約領域と firmware のメモリ配置衝突は未確認。
- 開発用 ext4 ログや専用 raw partition は候補だが、量産 rootfs に含めない。起動測定では無効にする。
- 起動時間測定は UART 設定・ログ量を固定。電断試験は給電経路を分離。障害解析では UART + printk 全開を使う。

出典: [CardputerZero docs](https://docs.m5stack.com/en/CardputerZero)、[USB gadget serial](https://docs.kernel.org/usb/gadget_serial.html)、[ramoops](https://docs.kernel.org/admin-guide/ramoops.html)、[SysRq](https://docs.kernel.org/admin-guide/sysrq.html)。

## SSH・VPN（調査のみ・実装しない）

この節は技術調査の保存のみを目的とし、MSD/Linux に SSH / VPN を実装する計画ではありません。

- Arm Cortex-A53 の Crypto Extension は optional です。BCM2837 に AES / SHA / PMULL 命令があるかはメーカー一次仕様で確認できていません。CPU feature の二次資料では AES / SHA なし、CRC32 ありとされていますが、実機の `/proc/cpuinfo` で確認する必要があります。
- WireGuard は ChaCha20-Poly1305 / Curve25519 / BLAKE2s / HKDF を使い、AES を使わない。ARM NEON 実装がある。CM0 の throughput 公開値なし。OpenVPN は既定 data cipher が AES-GCM を先頭にするため、AES 拡張がない場合は ChaCha20-Poly1305 を先頭に設定する案があるが、実装・性能は未検証。
- Buildroot 2026.08 の調査時点の版: OpenSSH 10.5p1、Dropbear 2026.94、OpenVPN 2.7.6、WireGuard tools 1.0.20260223。OpenSSH は ChaCha20-Poly1305 が既定順の先頭で、ML-KEM-768 + X25519 のハイブリッド鍵交換が既定で先頭。Dropbear は ChaCha20-Poly1305 と ML-KEM / sntrup ハイブリッドを有効、AES-GCM は既定無効との調査。OpenVPN の実効 PQ 鍵交換は OpenSSL 版依存で、接続確認なし。WireGuard 標準プロトコルに PQ hybrid はなく、PSK は任意の追加層。
- Dropbear は小型 SSH 実装で静的 build に向くとの調査。OpenSSH は標準的だが依存が多い。OpenVPN は userspace + OpenSSL、WireGuard は kernel と tools の組み合わせ。全て起動時間・CM0 throughput 未測定。
- 将来実装を再検討する場合、鍵を A/B rootfs に格納せず個体ごとの永続領域に生成する案、初回起動で固有鍵を作る案がある。SD を物理的に取り出せるため暗号化なしの秘密鍵保護は未解決。署名鍵管理・ローテーション・古いクライアントとの PQ 互換も未調査。

出典: [Arm Cortex-A53 TRM](https://documentation-service.arm.com/static/5e9077ee8259fe2368e2acf7?token=)、[sbc-bench crypto extensions](https://github.com/ThomasKaiser/sbc-bench/blob/master/results/ARMv8-Crypto-Extensions.md)、[WireGuard protocol](https://www.wireguard.com/protocol/)、[WireGuard performance](https://www.wireguard.com/performance/)、[OpenSSH 10.0 release](https://www.openssh.org/txt/release-10.0)、[Dropbear defaults](https://raw.githubusercontent.com/mkj/dropbear/DROPBEAR_2026.94/src/default_options.h)、[OpenVPN 2.7 manual](https://openvpn.net/community-docs/community-articles/openvpn-2-7-manual.html)。

## 名称

MSD/Linux は Muromi Software Distribution / Linux の略です。

名付け方は、ぷらっとホームの [SSD/Linux](https://www.plathome.co.jp/support/labo/ssdlinux/) にならいました。公式ページによれば、SSD は「BSD (Berkeley Software Distribution) にならい、開発場所である外神田 (Sotokanda) を冠した名称」です。SSD/Linux は、開発者が中学3年生だった 2004 年に初めて触れた Linux です。

MSD/Linux も同じように、開発場所の近くを流れる福岡県の室見川（Muromi）から名前をとりました。ロゴは、室見川が博多湾へ注ぐ姿を描いています（[ロゴの意匠](docs/logo/README.md#意匠)）。ロゴと公式サイトの文様を選んだ調査は、[和柄（日本の伝統文様）の調査](docs/research/wagara.md)にまとめました。

名前には、もう一つの由来があります。開発者が好きなライトノベル『なれる!SE』（夏海公司、電撃文庫、2010〜2017 年）に登場する、室見立華（むろみ りっか）です。作中では、ネットワーク系のシステムエンジニアとして描かれています。作中の主要な登場人物の苗字は、どれも福岡市地下鉄の駅名からとられていて、室見立華は空港線の室見駅に由来します（[Wikipedia「なれる!SE」](https://ja.wikipedia.org/wiki/%E3%81%AA%E3%82%8C%E3%82%8B!SE)）。

## 公式サイトの HTML・CSS

詳しくは [site-html-css.md](docs/research/site-html-css.md) を参照してください。

## 未確認事項

| 項目 | 次に確認すること |
|---|---|
| BCM2837 / CM0 の tryboot | 実機で `autoboot.txt` / `tryboot_a_b=1`、再起動時復帰を確認 |
| watchdog | `kernel_watchdog_*` と BCM2835 WDT が firmware / CM0 で有効か実機試験 |
| 起動速度 | 公式 image baseline、Buildroot baseline、LCD + keyboard の終点と PID 1 marker を測定 |
| rootfs / SD | microSD FTL の電断に関する一次資料と、複数カードでの実電断試験 |
| Wi-Fi / Ethernet | Wi-Fi chip ID、firmware blob、SR9900A の USB ID / driver |
| HDMI / UART / framebuffer | HDMI connector type、UART pinmux / console、FRAMEBUFFER_CONSOLE の最終 `.config` と LCD fbcon |
| GPT / MBR | BCM2837 での GPT boot、パーティションレイアウト制約 |
| M5 overlay | `cardputerzero-overlay` と `cardputerzero-v3/v5-overlay` の名称不整合、RTC overlay の I2C address |
| image-rota / Zephyr | zero2w / pi3 での image-rota 挙動、Canonical Zephyr fork の内容 |
| Buildroot packages | 最終構成で `make legal-info` を生成し、各配布物のバージョン・ライセンス・source archive を確認 |
| 開発環境・CI の比較 | [記録](docs/research/dev-environment-and-ci.md)の artifact 比較は予備的です。第3段階の PR で正式な実験記録を作成し、未測定の build 最適化候補を評価 |
| M5 hardware revision | v3 / v5 overlay と製品回路の整合、GL852G reset と keyboard shared GPIO |
| SSH / VPN | 実装しない方針。将来方針が変わる場合に限り暗号性能・鍵管理を再調査 |
| sysctl・I/O の実機値 | QEMU で取った既定値（[一覧](docs/research/tunables-defaults.md)）を CM0 実機で取り直し、RAM、SD、cpufreq、温度に依存する値の差を記録 |
| IRQ の分散 | 実機の `/proc/interrupts` で、周辺機器の割り込みが 4 コアへ回っているかを確認 |
| `arm_boost=1` | CM0 で `arm_freq` が変わるかを `vcgencmd` で確認。`config.txt` のコメント（Pi 3 のブーストモード）は公式資料と一致しない |
| `kernel.sysrq=32` | GPIO6 の電源断で remount が実行されることを、値を変えたイメージで実機確認 |
| SD の配置・性能 | 現行／1 MiB／4 MiB の image layout、FAT data-area absolute offset、target card の sysfs erase/AU 値と実性能を実機で確認 |
| `/data` の ext4 | `data=journal` から `data=ordered` へ移す場合の `fsync`/rename、barrier、`commit=` と電源断の整合性を確認 |
| discard / fstrim | target card の discard capability と処理結果を実機で確認 |
| update trust chain | 署名検証、鍵ローテーション、dm-verity root digest の保管場所を設計し、全カード交換の脅威境界を確認 |
| kernel / userspace hardening | SSP、FORTIFY、RELRO、PIE、mount options、sysctl の Buildroot 実効値と機能影響を確認 |
| watchdog / tryboot | BCM2837 での one-shot tryboot、`kernel_watchdog_timeout`、S01msd-watchdog の実 reset 動作を実機で確認 |
| hardware functions | IR、camera、IP2315 charger、SR9900A、各 M5 driver の probe と実機動作を確認 |

## 出典一覧

本書の各節に主要な根拠を記載しました。以下は本文で引用した主要な一次資料・技術資料です。版・取得日時に関する詳細は各節を参照してください。

### 製品・M5 ドライバ

- [CardputerZero 製品資料](https://docs.m5stack.com/en/CardputerZero)
- [CardputerZero 回路図 V0.6.1](https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf)
- [CardputerZero pi-gen](https://github.com/CardputerZero/pi-gen/commit/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc)
- [M5 Linux dtoverlays](https://github.com/m5stack/m5stack-linux-dtoverlays/tree/75518549a2640486f5d13ea72ca4935b198d7c20)
- [M5 powerfail_suo.c](https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/powerfail_suo.c)
- [CardputerZero boot benchmark](https://github.com/CardputerZero/circle-boot-splash/blob/b80d7c6a537c09c1ca233aeffa9c2e8601b113df/app/cardputerzero-splash/BENCHMARK.md)

### Raspberry Pi・Linux・Buildroot

- [Raspberry Pi config.txt boot docs](https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc)
- [Raspberry Pi autoboot.txt docs](https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/autoboot.adoc)
- [Raspberry Pi EEPROM bootflow docs](https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/raspberry-pi/bootflow-eeprom.adoc)
- [Raspberry Pi boot-time white paper](https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-010196-WP-1-Optimising%20boot%20time%20on%20Raspberry%20Pi%20single-board%20computers.pdf)
- [Raspberry Pi resilient filesystem white paper](https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-003610-WP-3-Making%20a%20more%20resilient%20file%20system.pdf)
- [Buildroot 2026.08 commit](https://github.com/buildroot/buildroot/commit/d5180309b1b66ef3b8eaccca70ad69be8e0729a1)
- [Raspberry Pi kernel rpi-6.18.y](https://github.com/raspberrypi/linux/tree/rpi-6.18.y)
- [SquashFS kernel docs](https://docs.kernel.org/filesystems/squashfs.html)
- [EROFS FAQ](https://erofs.docs.kernel.org/en/latest/faq.html)
- [EROFS kernel docs](https://docs.kernel.org/filesystems/erofs.html)
- [overlayfs kernel docs](https://docs.kernel.org/filesystems/overlayfs.html)
- [ext4 kernel docs](https://docs.kernel.org/admin-guide/ext4.html)
- [Raspberry Pi rpi-image-gen](https://github.com/raspberrypi/rpi-image-gen)

### 計測・userland・更新

- [Kernel parameters](https://docs.kernel.org/admin-guide/kernel-parameters.html)
- [systemd-analyze](https://man7.org/linux/man-pages/man1/systemd-analyze.1.html)
- [strace](https://man7.org/linux/man-pages/man1/strace.1.html)
- [fanotify](https://man7.org/linux/man-pages/man7/fanotify.7.html)
- [blktrace](https://man7.org/linux/man-pages/man8/blktrace.8.html)
- [BusyBox FAQ](https://busybox.net/FAQ.html)
- [RAUC](https://rauc.io/)
- [SWUpdate](https://sbabic.github.io/swupdate/)
- [Mender docs](https://docs.mender.io/)
- [Rugix device support](https://rugix.org/docs/bakery/devices/)

### 暗号

- [Arm Cortex-A53 technical reference](https://documentation-service.arm.com/static/5e9077ee8259fe2368e2acf7?token=)
- [WireGuard protocol](https://www.wireguard.com/protocol/)
- [OpenSSH 10.0 release notes](https://www.openssh.org/txt/release-10.0)
- [OpenVPN 2.7 manual](https://openvpn.net/community-docs/community-articles/openvpn-2-7-manual.html)
