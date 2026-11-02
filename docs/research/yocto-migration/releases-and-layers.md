# Yocto リリース系列・レイヤー・ホスト要件の調査

Buildroot から Yocto Project へ移るときに選ぶリリース系列と、組み合わせるレイヤーの対応状況を調べました。確認日は 2026-11-02 です。ブランチ名・コミット・ファイル内容は、各リポジトリを `git ls-remote` と `git clone` で取得して確かめました。本書はリリース系列を決めず、判断材料だけを並べます。系列はその後、2026-11-02 に利用者の判断で Wrynose 6.0 LTS に決まりました。

## 1. リリース系列とサポート期間

| 系列 | 版 | 初版 | 最新（確認日時点） | サポート | BitBake | 確認度 |
|---|---|---|---|---|---|---|
| Garburn | 6.2 | 2027-04 予定 | 開発中 | 6 か月（2027-10 まで）予定 | 2.22 | 【一次】 |
| Blacksail | 6.1 | 2026-09 | 6.1.0 | 安定版（2027-04 まで） | 2.20 | 【一次】 |
| Wrynose | 6.0 | 2026-04 | 6.0.4（2026-09） | LTS（2030-04 まで） | 2.18 | 【一次】 |
| Whinlatter | 5.3 | 2025-11 | 5.3.4（2026-04） | EOL | 2.16 | 【一次】 |
| Walnascar | 5.2 | 2025-04 | 5.2.4（2025-09） | EOL | 2.12 | 【一次】 |
| Styhead | 5.1 | 2024-09 | 5.1.4（2025-03） | EOL | 2.10 | 【一次】 |
| Scarthgap | 5.0 | 2024-04 | 5.0.21（2026-09） | LTS（2028-04 まで） | 2.8 | 【一次】 |

- 依頼文にあった Styhead・Walnascar・Whinlatter は、いずれも LTS ではなく、すでに EOL です。現在サポートされているのは Scarthgap 5.0 LTS、Wrynose 6.0 LTS、Blacksail 6.1 の三つです【一次】。
- 公式サイトの releases ページと wiki の Releases 表では、最新版の記載が一部食い違います。wiki では Scarthgap が 5.0.18（2026-06）のまま、公式サイトは 5.0.21（2026-09）です。版は公式サイトを優先し、BitBake の対応は wiki から取りました。
- 4 年 LTS の方針は wiki の注記に「Future LTS releases are planned for 4 years」とあります【一次】。
- Wrynose 6.0 の主要部品は Linux 6.18、GCC 15.2、glibc 2.43、LLVM 22.1.2、systemd v258 です。Blacksail 6.1 は Linux 7.2、GCC 16.2、glibc 2.44 です【一次: 各リリースノート】。6.0.4 で実際にビルドされた GCC は 15.3.0 でした【一次: 実験記録】。

## 2. 構成リポジトリ（Poky の扱いが変わった）

Whinlatter 5.3 の移行ガイドには「The Poky repository master branch is no longer updated」とあります。Poky ディストリビューション自体は廃止されていません。ただし配布方法が変わり、Whinlatter 以降の系列には Poky リポジトリのブランチがありません【一次】。`git ls-remote` で見ても、Poky リポジトリのブランチは `master` と `scarthgap` だけです。

| リポジトリ | Scarthgap | Whinlatter | Wrynose | Blacksail | 備考 |
|---|---|---|---|---|---|
| poky（git.yoctoproject.org） | ブランチあり | なし | なし | なし | 5.0.x のタグは継続 |
| openembedded-core | あり | あり | あり（`yocto-6.0.4` タグ） | あり（`yocto-6.1` タグ） | wrynose 先端 `ae5a301`（2026-10-27） |
| bitbake | タグ | — | `2.18.0`、`yocto-6.0.x` | `yocto-6.1`（2.19.0 タグもあり） | ブランチ名は系列名でない |
| meta-yocto（Poky ディストリ設定） | あり | あり | あり | ブランチなし・`yocto-6.1` タグのみ | |
| meta-openembedded | あり | あり | あり | あり | |
| meta-raspberrypi | あり | あり | あり | **ブランチなし**（master が blacksail 対応） | §3 |

- このため、依頼文の「poky をサブモジュールで管理」は Wrynose 以降では使えません。bitbake・openembedded-core・meta-yocto（Poky ディストリを使う場合）を別々に固定する必要があります。
- 公式の新しい取得手段は `bitbake-setup` です。Wrynose のリリースノートに `bitbake-setup init`・`status`・`update` の記述があり、Blacksail では PyPI 配布が加わりました【一次】。
- kas でも同じ構成を固定できます。kas は 2026-08-31 のコミット `0555188` が 5.5 です。5.5 では省略形コミットへの警告と、取得後のコミット SHA 照合（GHSA-6p9r-86f2-f954）が入りました。5.4 では CI 外での SSH ホスト鍵確認の扱いが修正されています（CVE-2026-54548）【一次: CHANGELOG】。kas の設定書式には `header.version`、`machine`、`distro`、`repos`（`commit`・`branch`）、`local_conf_header` があります【一次】。
- サブモジュールで固定する現行の流れ（`git clone --recurse-submodules`）を残すか、kas のロックファイルや `bitbake-setup` の設定に移すかは、フェーズ1で決めます（[README](README.md) §4）。

## 3. meta-raspberrypi

| ブランチ | 先端コミット | `LAYERSERIES_COMPAT` |
|---|---|---|
| `master` | `96d0b6d`（2026-10-27） | `blacksail` |
| `wrynose` | `9195883`（2026-10-10） | `wrynose` |
| `whinlatter` | `469e232`（2026-03-31） | `whinlatter` |
| `scarthgap` | `018d444`（2026-10-08） | `nanbield scarthgap` |

### 3.1 CardputerZero（CM0）に近い machine

- **CM0 用の machine はありません**。`master` を `cm0` で検索しても該当はありませんでした【一次】。
- 近いのは `raspberrypi0-2w-64` と `raspberrypi3-64` です。`raspberrypi0-2w-64` は `raspberrypi3-64.conf` を include し、`MACHINEOVERRIDES` に `raspberrypi3-64` を加えます。device tree は `bcm2710-rpi-zero-2.dtb` だけです。CM0 と Zero 2 W は同じ RP3A0（BCM2710A1 系）を載せています（[hardware-spec.md](../hardware-spec.md)）。
- `raspberrypi3-64.conf` の主な値は次のとおりです【一次】。
  - `DEFAULTTUNE ?= "cortexa53-nocrypto"`（`tune-cortexa53.inc`）
  - `SDIMG_KERNELIMAGE ?= "kernel8.img"`、`KERNEL_IMAGETYPE_DIRECT ?= "Image"`
  - `SERIAL_CONSOLES ?= "115200;ttyS0"`、`ARMSTUB ?= "armstub8.bin"`
  - `RPI_KERNEL_DEVICETREE` に `bcm2710-rpi-3-b.dtb` などがあり、`bcm2710-rpi-cm0.dtb` はありません
- MSD が使う `bcm2710-rpi-cm0.dtb` は、独自 machine（仮称 `cardputerzero`）で `RPI_KERNEL_DEVICETREE` に足す必要があります【推測】。
- 共通設定 `rpi-base.inc` は `IMAGE_FSTYPES ?= "tar.bz2 ext3 wic.bz2 wic.bmap"`、`WKS_FILE ?= "sdimage-raspberrypi.wks"` を既定にしています。`rpi-default-settings.inc` は `IMAGE_CLASSES += "sdcard_image-rpi"` を加えます【一次】。

### 3.2 カーネル系列

| ブランチ | 収録レシピ | 既定 |
|---|---|---|
| `wrynose`・`master` | `linux-raspberrypi` 6.1、6.6、6.12、6.18 | `PREFERRED_VERSION_linux-raspberrypi ??= "6.18.%"`（armv7 は 6.12） |
| `scarthgap` | 6.1、6.6、6.12 | `"6.6.%"` |

- `wrynose` の 6.18 レシピは `LINUX_VERSION ?= "6.18.33"`、`LINUX_RPI_BRANCH ?= "rpi-6.18.y"`、`SRCREV_machine = "95b85be…"` です。kernel-meta は yocto-kernel-cache の `yocto-6.18` ブランチを使います【一次】。
- MSD が固定している raspberrypi/linux `b3495ea` の Makefile は 6.18.59 です。レシピ既定の 6.18.33 より新しいため、移行後も今の固定を保つには、bbappend で `SRCREV_machine` と `LINUX_VERSION` を上書きします【一次: 両コミットの Makefile、推測: 上書き方法】。
- Scarthgap の meta-raspberrypi には 6.18 レシピがありません。Scarthgap を選ぶと、現行の rpi-6.18.y を保つためのレシピを自前で用意することになります【一次: ブランチの内容、推測: 対応作業】。
- 現行 MSD と同じく、`raspberrypi3-64` の `KBUILD_DEFCONFIG` は `bcm2711_defconfig` です。`KCONFIG_MODE = "--alldefconfig"` で、`linux-yocto.inc` の fragment 機構（`SRC_URI` の `.cfg`、`KERNEL_FEATURES` の `.scc`）を使います【一次】。

### 3.3 ファームウェアと起動ファイル

- `rpi-bootfiles` は raspberrypi/firmware `09267f5`（`RPIFW_DATE ?= "20260521"`）の `*.elf`・`*.dat`・`*.bin` をすべて deploy します。ライセンスは `Broadcom-RPi` です【一次】。MSD が使う `start_cd.elf`・`fixup_cd.dat`・`bootcode.bin` もここに含まれます。
- `rpi-config` は Evilpaul/RPi-config の `config.txt` を `sed` で書き換えます。任意の行は `RPI_EXTRA_CONFIG` で足せます。`ENABLE_UART`、`ENABLE_I2C`、`ENABLE_SPI_BUS`、`DISABLE_SPLASH`、`BOOT_DELAY`、`GPU_MEM` などの変数もあります【一次: meta-raspberrypi の `extra-build-config.md`】。
- `rpi-cmdline` は `CMDLINE_ROOT_PARTITION ?= "/dev/mmcblk0p2"` を既定に、一つの `cmdline.txt` を作ります【一次】。MSD は A/B 用に `cmdline_rootfs_a.txt` と `cmdline_rootfs_b.txt` を使い分けるため、このレシピの出力はそのままでは使えません【推測】。
- `linux-firmware-rpidistro` の一部は Synaptics ライセンスで、`LICENSE_FLAGS_ACCEPTED = "synaptics-killswitch"` を明示しないとビルドできません【一次: meta-raspberrypi の `ipcompliance.md`】。

## 4. ホスト要件

| 項目 | Scarthgap（5.0 文書） | Wrynose（6.0.4 文書） |
|---|---|---|
| 空きディスク | 90 GB 以上 | 140 GB 以上 |
| RAM | 8 GB（qemux86-64、4 コアの古い機械） | 32 GB（同条件） |
| Ubuntu | 22.04、24.04 | 22.04、24.04、25.04、25.10、26.04 |
| Python | 3.8.0 以上 | 3.9.0 以上 |
| gcc | 8.0 以上 | 10.1 以上 |
| Git / tar / make | Git 1.8.3.1、tar 1.28 | Git 1.8.3.1、tar 1.28、GNU make 4.0 |

- 現行の開発環境と CI の Ubuntu 26.04 は、Wrynose の対応ディストリビューションに入っています。Scarthgap の対応表には入っていません【一次】。
- GitHub-hosted runner（public リポジトリ用の標準 Linux）の SSD 容量は 14 GB です【一次: GitHub Docs】。Wrynose の 140 GB には届かないため、CI でフルビルドするには、sstate の外部キャッシュかセルフホスト runner が必要になります【推測】。詳しくは [verification-and-ops.md](verification-and-ops.md) §5 にまとめました。

## 5. 系列選択の判断材料

| 観点 | Scarthgap 5.0 | Wrynose 6.0 | Blacksail 6.1 |
|---|---|---|---|
| サポート期限 | 2028-04 | 2030-04 | 2027-04 |
| meta-raspberrypi | ブランチあり、6.18 なし | ブランチあり、6.18 既定 | 専用ブランチなし（master） |
| Poky リポジトリ | 使える | 使えない（個別固定） | 使えない |
| Ubuntu 26.04 | 対応表外 | 対応 | 対応 |
| A/B 用レイヤー | meta-rauc・meta-mender-community・meta-swupdate にブランチあり | meta-rauc・meta-mender-community・meta-swupdate にブランチあり | meta-swupdate のみブランチあり |
| `LICENSE` 書式 | 従来式 | 従来式 | SPDX 式（`CLOSED` は警告） |

- 期限・BSP・ホスト対応の三点で見ると、Wrynose が最も条件に合います【推測】。ただし、系列は依頼どおりここでは決めません。決める前に、開発環境で実際にビルドして確かめます（[README](README.md) §4）。

## 出典（確認日 2026-11-02）

- https://wiki.yoctoproject.org/wiki/Releases 【一次】系列・版・BitBake・4 年 LTS の注記
- https://www.yoctoproject.org/development/releases/ 【一次】現行・過去系列の最新版とサポート期限
- https://docs.yoctoproject.org/migration-guides/migration-5.3.html 【一次】Poky リポジトリ master の更新停止、bitbake-setup
- https://docs.yoctoproject.org/migration-guides/release-notes-6.0.html 【一次】Wrynose の部品版、bitbake-setup、wic の分離、sbom-cve-check
- https://docs.yoctoproject.org/dev/migration-guides/release-notes-6.1.html 【一次】Blacksail の部品版、bitbake-setup の PyPI 配布
- https://docs.yoctoproject.org/dev/migration-guides/migration-6.1.html 【一次】`LICENSE` の SPDX 式化、`CLOSED` の非推奨
- https://docs.yoctoproject.org/6.0.4/ref-manual/system-requirements.html 【一次】Wrynose のホスト要件
- https://docs.yoctoproject.org/scarthgap/ref-manual/system-requirements.html 【一次】Scarthgap のホスト要件
- https://github.com/agherzan/meta-raspberrypi/tree/919588393f41b48cb6c5d832aa35e58a19b6762d 【一次】wrynose ブランチ（machine、カーネル、rpi-config、rpi-cmdline、docs）
- https://github.com/agherzan/meta-raspberrypi/tree/96d0b6dadfb8773d23356b1211936536a526dd07 【一次】master ブランチ（blacksail 対応）
- https://github.com/agherzan/meta-raspberrypi/tree/018d44467c4f09eb63f8ea5e86e85d755250cf89 【一次】scarthgap ブランチ
- https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/Makefile 【一次】MSD 固定のカーネル（6.18.59）
- https://github.com/raspberrypi/linux/blob/95b85bebbedcaedfa7ca79116ed38b7376fba412/Makefile 【一次】meta-raspberrypi 既定のカーネル（6.18.33）
- https://github.com/siemens/kas/blob/055518846c3963114efbd0107bf3f2e59b4b3ba5/CHANGELOG.md 【一次】kas 5.4・5.5 の変更
- https://kas.readthedocs.io/en/latest/userguide/project-configuration.html 【一次】kas 設定書式
- https://docs.github.com/en/actions/reference/runners/github-hosted-runners 【一次】hosted runner の SSD 容量
- ブランチとタグの一覧は、poky・openembedded-core・bitbake・meta-yocto・meta-openembedded・meta-raspberrypi・kas の各リポジトリに `git ls-remote` を実行して得ました。
