# CardputerZero / Raspberry Pi CM0 エコシステム調査（2026-11-01）

M5 公式・コミュニティと Raspberry Pi 公式・コミュニティの最新状況を調べました。ドライバ・BSP・ファームウェア・配布機構を軸に整理します。【一次】は一次資料を確認済み、【推測】は根拠のない推定、【未確認】は公開情報の確認が未完です。

## 1. CardputerZero 公式（M5Stack / CardputerZero org）

`github.com/CardputerZero` org の活動は活発です。MSD が基準にしている `pi-gen`（branch `cardputerzero_v1.0`、HEAD `791a985`、2026-10-08）は安定していますが、同 org に「アプリ配布基盤」が新たに整備されています。

| リポジトリ | 内容 | MSD との関係 |
|---|---|---|
| `CardputerZero/pi-gen` | 公式 OS ビルド（2026-10-08 以降は更新なし） | MSD の対照ベースライン。変化なし |
| `CardputerZero/packages` | APT リポジトリ兼 AppStore レジストリ。`.deb` は GitHub Release（`apt-pool`）に置き、git は `registry.json` と manifest のみ。端末は md5 で検証してインストール。中国向けは Aliyun OSS ミラー | 【一次】2026-11-01 更新あり。**インストール検証が MD5 のみ**で、MSD の Ed25519 署名方針とは対照的。AppStore 型エコシステムの事実として記録 |
| `CardputerZero/Store` | 端末側の LVGL AppStore。registry.json から `.deb` を取得し `download.md5` で検証して Debian 系ツールでインストール | 【一次】公式の配布経路として存在確認 |
| `CardputerZero/AppBuilder` | `czdev` CLI（Python）＋ GHA で aarch64 `.deb` をクロスビルドし AppStore へ公開 | サードパーティアプリのビルド基盤として確立 |
| `CardputerZero/launcher` `dev-portal` `m5stack-imager` `cardputerzero.github.io` | ランチャ、開発ポータル、イメージャ、サイト | 活動中（2026-10 末〜11-01） |
| `CardputerZero/dtoverlays` | M5 拡張デバイスの DT overlay。pi-gen は `main` から `--depth=1` で取得 | MSD も参照している（rootfs 生成で利用） |
| `CardputerZero/circle-boot-splash` | bare metal の起動スプラッシュ（circle ベース） | 既知どおり |
| `CardputerZero/u-boot` | u-boot fork | MSD の方針（U-Boot 非採用）とは別経路 |

アプリケーションレイヤ（Cap-LoRa-1262、Cap-CC1101、IR-Chat、Camera、Recorder など多数）は CardputerZero 公式 org 内で維持されています。MSD とは層が違うため、動作の参考情報としてのみ扱います。

## 2. Raspberry Pi 公式（CM0 向け）

| 項目 | 状況 | MSD との関係 |
|---|---|---|
| `raspberrypi/linux` `rpi-6.18.y` | `arch/arm64/boot/dts/broadcom/bcm2710-rpi-cm0.dts` あり【一次】 | CM0 は upstream カーネルで公式サポート。MSD の pin カーネル系列に含まれる |
| `raspberrypi/firmware` | `boot/bcm2710-rpi-cm0.dtb` あり【一次】 | ファームウェア側も CM0 対応済み |
| `rpi-image-gen` | `device/` に `zero2w` はあるが `cm0` なし【一次】 | 公式イメージ生成器では CM0 専用 device は未提供 |
| Compute Module 0 本体 | RP3A0 SiP（BCM2710 + 512MB LPDDR2） | MSD の対象 SoC と一致（Zero 2 W と同 SiP） |
| Zephyr v4.5.0 | `boards/raspberrypi/rpi_zero_2w` 追加（[Zephyr 更新](os-candidates.md) を参照） | SDHCI 未確認。評価不能のまま |

## 3. CM0 コミュニティ（GitHub 検索・フォーラム系）

| プロジェクト | 内容 | 参考になる点 |
|---|---|---|
| `JasonYANG170/pikvm-cm0` | PiKVM の CM0 移植 | CM0 での OTG/USB 運用の実例【未確認：構成詳細】 |
| `magic-blue-smoke/Raspberry-Pi-CM0-TV-Stick` | CM0 ベースの TV stick | 小型化フォームファクタの例 |
| `magic-blue-smoke/Raspberry-Pi-CM0IQ` | CM0 ベースの基板 | キャリアボード実装例 |
| `mfolejewski/RPI_SOM_CM0_SCH_PCB_LIB` | CM0 の KiCad SCH/PCB ライブラリ | CM0 の回路図シンボル・フットプリントが共有されている |
| `osprey74/cardputerzero-apps` | CardputerZero 用アプリの monorepo | コミュニティのアプリ実装例 |
| `evaderkrub/gothcawili` | pwnagotchi の CM0 移植（FreeWili 2 内蔵） | CM0 を使った別製品の例 |
| `hringdrifi/skjar` | CM0 + 8.8" DSI ディスプレイの cyberdeck | 40% キーボード＋大画面の例 |
| `hishizuka/pizero_bikecomputer` | Pi Zero 系の自転車コンピュータ | Zero 系の消費電力設計の参考【関連性は薄い】 |

フォーラム系（Raspberry Pi Forums、M5Stack Community）の個別スレッドは今回の範囲では精査していません。【未確認】

## 4. MSD への示唆

1. **AppStore 系配布が公式に動き出した**: `packages`/`Store`/`AppBuilder` が AppStore 型の配布基盤。MSD の Ed25519 署名方式とは設計が違うため、混ぜるなら信頼モデル（MD5 検証 vs 署名）を区別して記録する必要があります。
2. **CM0 の公式サポートは rpi-6.18.y で済んでいる**: `bcm2710-rpi-cm0.dts` とファームウェア `bcm2710-rpi-cm0.dtb` が upstream にある。追加の BSP を自作する必要はありません。
3. **rpi-image-gen に CM0 device がない**: 公式イメージ生成器では CM0 専用エントリがないため、MSD が「CM0 向けの公式生成器」に乗る余地はまだあります。
4. **コミュニティの CM0 採用例が増えている**: PiKVM、FreeWili 2、各種 cyberdeck など。ドライバ（USB OTG、DSI、SD）の先行実装として参照できます。

## 5. Buildroot / Yocto の最新情報

| 項目 | 状況 | MSD との関係 |
|---|---|---|
| Buildroot 2026.08.1 | `buildroot/buildroot` に `2026.08.1` タグあり（2026.08 系列の保守リリース）【一次】 | MSD は 2026.08（`d5180309`）を pin。点リリースの取り込み可否は「固定版の更新確認」ワークフロー側の話題として記録 |
| Buildroot 次期系列 | `news.html` の記載は 2026.08 まで。2026.11 はまだ未リリース【一次】 | 年 4 回（02/05/08/11）のサイクルなら次は 2026.11。出たら系列変更の検討対象 |
| Yocto 安定系 | poky タグの最新は `yocto-5.2.4`（Whinlatter）。meta-raspberrypi に `whinlatter` ブランチあり【一次】 | Yocto 候補としては 5.2 系が現行安定 |
| Yocto LTS | Scarthgap（5.0 系、`yocto-5.0.21` までタグあり） | LTS 採用なら Scarthgap。meta-raspberrypi に `scarthgap` ブランチあり【一次】 |
| Yocto 次期 | meta-raspberrypi に `wrynose` ブランチが存在（5.3 系の開発ライン相当）【推測：番号対応】 | 次の安定系は Wrynose 相当の可能性。タグが出ていない段階 |
| meta-raspberrypi 活動 | `sdcard_image-rpi`・`pi-bluetooth`・CI を Ubuntu 26.04 へ更新、などが 2026-10 に進行【一次】 | Pi 向け BSP は活発。MSD が Buildroot なので直接の変更影響はないが、DT/機能有無の比較先として有用 |

## 出典

- CardputerZero org リポジトリ一覧 https://github.com/orgs/CardputerZero/repositories （各 README を確認）【一次】
- `CardputerZero/packages` README https://github.com/CardputerZero/packages 【一次】
- `CardputerZero/Store` README https://github.com/CardputerZero/Store 【一次】
- `CardputerZero/AppBuilder` README https://github.com/CardputerZero/AppBuilder 【一次】
- `raspberrypi/linux` `rpi-6.18.y` `arch/arm64/boot/dts/broadcom/` https://github.com/raspberrypi/linux/tree/rpi-6.18.y/arch/arm64/boot/dts/broadcom 【一次】
- `raspberrypi/firmware` `boot/` https://github.com/raspberrypi/firmware/tree/master/boot 【一次】
- `raspberrypi/rpi-image-gen` `device/` https://github.com/raspberrypi/rpi-image-gen/tree/main/device 【一次】
- Zephyr v4.5.0 `boards/raspberrypi/` https://github.com/zephyrproject-rtos/zephyr/tree/v4.5.0/boards/raspberrypi 【一次】
- CM0 コミュニティプロジェクトは GitHub 検索結果（`cm0 raspberry pi`）の pushed 順。個別 README の精査は限定的【未確認】
- `buildroot/buildroot` タグ https://github.com/buildroot/buildroot/tags 【一次】
- Buildroot ニュース https://buildroot.org/news.html 【一次】
- poky タグ（`git ls-remote https://git.yoctoproject.org/poky`）【一次】
- `agherzan/meta-raspberrypi` ブランチ・コミット https://github.com/agherzan/meta-raspberrypi 【一次】
