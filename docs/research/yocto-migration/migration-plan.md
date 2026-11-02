# Yocto Project への移行計画（案・未着手）

- 状態: 案。移行作業は始めていません。
- 系列: Wrynose 6.0 LTS（2030-04 まで。利用者の判断で決定）
- 作成: 2026-11-02

AGENTS.md §7 では計画をリポジトリにコミットせずチャットで共有しますが、この計画は「調査結果・検討結果・移行計画・検証結果を漏れなく RESEARCH に反映する」という利用者の指示（2026-11-02）により、例外として残します。実装を始めるときは、各フェーズの開始前に改めて計画を共有し、承認を得ます。

## 1. 方針

Buildroot の構成をそのまま写すことは目標にしません。Yocto Project の層、レシピ、パッケージのメタデータ、SPDX、sstate を製品の監査と保守に使う構成を、ゼロから組み立てます。そのうえで、MSD/Linux の考え方は変えません。

| MSD/Linux の考え方 | Yocto での扱い |
|---|---|
| LCD のテキストコンソールと内蔵キーボードの CLI だけ | image に GUI・ネットワーク管理・パッケージ管理を入れない |
| rootfs は読み取り専用、可変データは小さな領域 | `read-only-rootfs` の IMAGE_FEATURE と SquashFS（`squashfs-zst`）。/data は ext4 |
| A/B で前の世代に戻れる | firmware の `autoboot.txt` / tryboot を継続し、U-Boot を入れない |
| 電源断に強い | 書き込み経路を増やさない。電断試験を受け入れ基準にする |
| 標準版と Lite 版を同じイメージで扱う | 製品の image は一つ。別の image は比較実験用に限る |
| 最小で監査できる | 層を BSP と distro に分け、ライセンス・SBOM・ソースを Yocto の仕組みで出す |

六つの設計柱（起動速度、電源断耐性、A/B 復帰、全ハードウェアの利用、セキュリティ、検証可能性）は §4 の受け入れ基準にします。Buildroot で見送った案の見直しは [reevaluation.md](reevaluation.md) にあります。

## 2. 構成の設計

### 2.1 層

| 層 | 中身 | 理由 |
|---|---|---|
| openembedded-core、bitbake | Wrynose の `yocto-6.0.x` タグで固定 | Wrynose 以降は poky リポジトリにブランチがないため、個別に固定します（[releases-and-layers.md](releases-and-layers.md)） |
| meta-raspberrypi | wrynose ブランチのコミットで固定 | RPi の firmware、カーネル、`rpi-config` |
| meta-msd-bsp（新規） | machine `cardputerzero`、カーネルの bbappend と fragment、M5Stack のドライバー・overlay・ファームウェアのレシピ | BSP だけを分けると、他の distro からも CardputerZero を使えます |
| meta-msd（新規） | distro `msd`、image、init スクリプト、`msd-update`、鍵と署名、QEMU の起動試験 | 製品の方針をここに集めます |
| meta-oe、meta-security | 必要になったときだけ（dm-verity を採る場合） | 層を増やすと監査の範囲が広がるため |

Yocto Project Compatible の考え方（層を足しただけで挙動が変わらない、BSP と distro を分ける）に合わせ、`yocto-check-layer` を通すことを目標にします【一次: https://docs.yoctoproject.org/test-manual/yocto-project-compatible.html】。

### 2.2 machine `cardputerzero`

- meta-raspberrypi に CM0 用の machine はありません。CM0 は Zero 2 W と同じ RP3A0 なので、`raspberrypi0-2w-64` と同じ include（`raspberrypi3-64.conf` 系）を元にします【一次: [releases-and-layers.md](releases-and-layers.md)】。
- `KERNEL_DEVICETREE` に `bcm2710-rpi-cm0.dtb` と M5 の overlay を指定します。既定では `bcm2710-rpi-cm0.dtb` が作られないことを構築試験で確認しています【実測】。
- `SERIAL_CONSOLES` は meta-raspberrypi の既定（`115200;ttyS0`）のままでは QEMU でログイン画面が出ません。QEMU では PL011 が `ttyAMA1` になります【実測: [QEMU 起動記録](../../experiments/2026-11-02-yocto-qemu-boot.md)】。実機の UART 配線を確かめてから決めます。
- CM0 の machine を meta-raspberrypi に提案するかは、外部リポジトリへの書き込みになるため、利用者の承認を得てから決めます。

### 2.3 distro `msd`

- `INIT_MANAGER = "mdev-busybox"`。Wrynose で起動することを QEMU で確認済みです【実測】。
- `DISTRO_FEATURES` は最小にします（`x11`、`wayland`、`opengl`、`pulseaudio`、`bluetooth` などを外す。必要なものは機能ごとに足す）。
- 最適化とハードニング: `-Os`、LTO（`lto.inc`）、`_FORTIFY_SOURCE=3`、SSP、PIE、RELRO を distro に書き、生成物の ELF で確かめます。oe-core の既定は `_FORTIFY_SOURCE=2` です（[verification-and-ops.md](verification-and-ops.md) §3.2）。
- ツールチェーンは内部の GCC（Wrynose では 15.3.0【実測】）と glibc にします。
- パッケージは ipk で作りますが、image には `package-management` を入れません。
- ライセンス: SPDX 3.0（既定の `create-spdx`）、`license.manifest`、archiver（GPL 系は `original` の source）を有効にします。M5Stack の不明ライセンスのバイナリは `LicenseRef-` と `NO_GENERIC_LICENSE` で扱います。`INCOMPATIBLE_LICENSE` に何を入れるかは、MSD のライセンス方針と照らして決めます（未決）。

### 2.4 image `msd-image`

- 中身: BusyBox、kmod、kbd、e2fsprogs（fsck・resize2fs）、OpenSSL、util-linux の `partx`、v4l-utils の必要部分、M5 の BSP、`msd-update`、init スクリプト（現行の `S01msd-watchdog`〜`S99msd-health` をレシピに分ける）。
- `IMAGE_FEATURES += "read-only-rootfs"`、`IMAGE_FSTYPES = "squashfs-zst wic"`。`mksquashfs -sort` は oe-core の型にないため、meta-msd で image の型を足します。
- パーティションは wks で書きます。現行の genimage（MBR、4 MiB 境界、bootsel 16 MiB、boot-a / boot-b 各 64 MiB、rootfs-a / rootfs-b 各 256 MiB、data 64 MiB）を出発点にし、サイズは image の実測から決め直します。
- `config.txt` は `rpi-config` と `RPI_EXTRA_CONFIG` で作り、A/B の `autoboot.txt` と slot ごとの `cmdline.txt` は meta-msd のレシピで作ります（`rpi-cmdline` は一つの `cmdline.txt` しか作らないため）。
- 鍵の埋め込み、モジュール署名、更新 bundle の manifest と Ed25519 署名は、image の後処理または専用のレシピにします。鍵は sstate や SPDX に入らないよう、ビルドの外から渡す設計にします【推測】。

### 2.5 カーネル

- `linux-raspberrypi_6.18.bbappend` で、MSD の固定コミット（現行は `b3495ea`、6.18.59）と `linux.fragment` を当てます。B2 で、要求 490 項目のうち最終の `.config` と違うのは `CONFIG_NODES_SHIFT` だけでした【実測】。ただし fragment にない項目では、Buildroot の最終 `.config` と 544 項目が違い、`CONFIG_THERMAL` が `n` でした【実測: [成果物の比較](../../experiments/2026-11-02-buildroot-yocto-artifacts.md)】。Y2 で差を一つずつ説明します。
- fragment は、ハードニング、PREEMPT_RT、サイズ削減のように目的ごとに分けると、Yocto の `KERNEL_FEATURES` や比較実験で入れ替えやすくなります。
- M5 のドライバーは `inherit module` のレシピにし、`kernel-module-*` のパッケージとして image に入れます。

### 2.6 開発環境と CI

- 構成管理は kas の YAML とロックファイル、ビルドは kas-container にします（[dev-environment.md](dev-environment.md)）。rootless では Podman が推奨です。Docker を使う場合は `DOCKER_CONTEXT=rootless` が必要でした【実測】。
- 既存の `docker/msd-dev`（ASB パッチ入り QEMU、検査ツール）は QEMU の起動試験と検査に使い続けます。
- CI: 空の状態からのビルドは 2 時間 4 分、作業領域は約 54 GB でした【実測】。hosted runner に載せるかは、sstate の共有ミラーと hash equivalence サーバーを使った 2 回目以降の時間を測ってから決めます。
- Dependabot は kas のロックファイルを扱えないため、「固定版の更新確認」ワークフローに層のコミットを加えます。

## 3. フェーズ

| フェーズ | 内容 | 完了の条件 |
|---|---|---|
| Y0（済み） | 調査、構築試験、BSP のビルド、QEMU 起動 | [調査](README.md)、[構築試験](../../experiments/2026-11-02-yocto-wrynose-probe.md)、[QEMU 起動](../../experiments/2026-11-02-yocto-qemu-boot.md) |
| Y1 | 層と kas の骨組み（meta-msd-bsp、meta-msd、kas とロックファイル） | `bitbake -p` が通る。`yocto-check-layer` の結果を記録する |
| Y2 | BSP（machine、カーネル、M5 のレシピ、パッチの `Upstream-Status`） | `.ko` 16 個、dtbo 3 個、ファームウェアとキーマップがそろう。Buildroot の最終 `.config` との差（2026-11-02 時点で 544 項目）をすべて説明できる。CM0 の dtb で QEMU が起動する |
| Y3 | distro と image（読み取り専用の SquashFS、init、/data、wks の A/B） | 既存の `test-boot.sh` と `test-ab.sh` に相当する QEMU 試験が通る。Buildroot の image とファイル一覧・サイズを比べる |
| Y4 | 更新と電源断（`msd-update`、bundle と署名、tryboot） | `tests/msd-update/run.sh` と QEMU の A/B・障害注入（S4・S17 相当）が通る |
| Y5 | Yocto で容易になる比較実験（dm-verity、RAUC の custom backend、systemd、musl、`overlayfs-etc`） | 実験ごとに採否の基準を先に書き、`docs/experiments/` に記録する |
| Y6 | CI と監査（kas のビルド、sstate ミラー、SPDX、`sbom-cve-check`、archiver、再現性の試験） | 配布物に SPDX、`license.manifest`、ソースを添付できる。同じ入力から 2 回ビルドして差を記録する |
| Y7 | 受け入れと Buildroot の削除 | §4 の基準をすべて満たし、利用者が承認する |

## 4. 受け入れ基準（Buildroot を削除する前提）

| 設計柱 | QEMU で確かめること | 実機で確かめること |
|---|---|---|
| 起動速度 | `MSD/Linux ready` までの時間を 5 回以上測り、Buildroot の中央値から劣化しない（許容幅は Y3 の開始前に決める） | 電源投入からプロンプトとキー入力まで |
| 電源断耐性 | 既存の電断・障害注入試験と同じ回数で同じ結果 | 実機での電源断の反復 |
| A/B 復帰 | A / B の起動、更新、失敗時の戻り | tryboot の実動作 |
| 全ハードウェアの利用 | モジュールと overlay の読み込み、dmesg のエラーなし | LCD、キーボード、音声、IMU、電池、LED、カメラ |
| セキュリティ | ハードニングの検査、モジュール署名の強制、sysctl | 同左を実機で |
| 検証可能性 | QEMU の起動試験を CI か手順で再実行できる。SPDX とソースがそろう | 実機の確認手順を [VERIFY.md](../../VERIFY.md) に書く |

## 5. 未決事項

| 項目 | 選択肢 | 推奨と理由 |
|---|---|---|
| 層の数 | meta-msd-bsp と meta-msd の 2 層 / 1 層 | 2 層。BSP の再利用と Yocto Project Compatible の考え方に合う |
| CM0 の machine | meta-msd-bsp に置く / meta-raspberrypi に提案する | まず自分の層に置く。提案は利用者の承認後 |
| 更新方式 | `msd-update` の移植 / RAUC の custom backend | まず移植。RAUC は Y5 で比べる（RAUC の tryboot 対応 PR #1599 は 2026-11-02 時点で未マージ） |
| CI の実行場所 | hosted runner と外部キャッシュ / セルフホスト / 手動 | sstate ミラーでの 2 回目以降の時間を測ってから決める |
| 開発コンテナ | kas-container（Podman） / `docker/msd-dev` の拡張 | kas-container。QEMU と検査は `docker/msd-dev` を使い続ける |
| M5 の不明ライセンスのバイナリ | `LicenseRef-` で配布 / 配布物から外す / M5Stack に確認 | M5Stack に確認するまで、配布物の扱いは決めない |
| `INCOMPATIBLE_LICENSE` | GPL-3.0 系を除く / 除かない | MSD のライセンス方針と照らして決める |

## 6. 危険と対策

- ビルドの重さ: sstate と hash equivalence を前提にし、空の状態からのビルドは定期実行に限る。
- 起動時間とサイズの劣化: ツールチェーンと init の中身が変わるため、Y3 で Buildroot と同じ指標を測る。
- `Upstream-Status` の QA: Wrynose ではないとビルドが止まる。MSD のパッチすべてに付ける。
- 実機が未入手: QEMU で確かめられない項目（LCD、キーボード、tryboot、電源断）は、実機が届くまで Buildroot を残す理由になる。

## 7. この計画でまだ行わないこと

meta-msd・meta-msd-bsp の作成、Buildroot の削除や置き換え、`vendor/` の変更、上流への提案、実機での確認。
