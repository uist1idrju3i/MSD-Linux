# 実機で確かめる指標と機能

[調査の索引](../../../RESEARCH.md) / [検証の入口](README.md)

以下は実機未入手時点からの測定案です。手順・チェックリストを作ったことを、CardputerZeroで実行した結果とは扱いません。
当時の採用情報と比較値も条件ごと保存しています。現在の試験状況・不足は[S1–S17](experiment-catalog.md)と[未確認事項](open-questions.md)を参照します。
とくにS13の比較は単独の`-Os + LTO`効果を示さず、仮想時刻や他機種の起動秒数を実機性能へ換算しません。
カメラのコマンドと出力保存は[実機確認手順](../../VERIFY.md)にまとめています。

## カメラ測定で保存する出力

- [ ] `dmesg` から IMX219 の sensor ID を採取する。
- [ ] IMX219 overlay 適用後に `media-ctl -p` を実行し、sensor → Unicam の media topology と link 状態を記録する。
- [ ] CSI1 の 2-lane 接続で対応する raw format を選び、`v4l2-ctl --stream-mmap` による capture を実施して format、解像度、frame 数、drop/error を記録する。
- [ ] カメラのない Lite 版で IMX219 probe が失敗する場合の実際の kernel message を採取し、想定内であることを確認する。【未確認】

### 実機が届いたら最初に測る項目（優先順の案）
1. **公式イメージの起動時間**(systemd-analyze、vclog)。ベースライン
2. **tryboot/autoboot.txt の動作**(A/B 方式の成否を左右する)
3. **CM0 の arm_64bit/kernel8.img の挙動**
4. **kernel8.img の非圧縮と gzip の比較**
5. **vc4 除去の効果**(HDMI/cma を外した場合)
6. **Wi-Fi の chip ID**
7. **GL852G のリセット挙動**(PYG3 はキーボードと共用)
8. **電源断試験**(書込み中/アイドル時の電源断を多数回)
9. **GPIO6 電源断スイッチの hold-up 時間**（信号発生から電源が失われるまでを実機測定し、正常停止を追加できるか判断する）
10. **microSD の実測特性:** `/sys/block/mmcblk0/device/preferred_erase_size`、queue の `minimum_io_size` / `optimal_io_size` / `discard_granularity` / `discard_max_bytes`、MMC card 情報を記録し、モデル・容量・firmware とともに保存する。
11. **パーティション比較:** 現行、`align=1M`、`align=4M` の各 image で開始 sector、FAT data-area 絶対位置、image size を記録する。4 MiB alignment が速度や寿命を改善すると先に仮定しない。
12. **SD 性能:** 同じカード・ホスト・温度で sequential / random read-write と同期書込みを測り、反復回数、中央値、p90、card 使用状態を記録する。A1/A2 のラベルのみから性能を推定しない。
13. **ext4 と電断:** `/data` の実 mount options、`data=journal` / `data=ordered`、barrier、`commit=` を記録し、アプリケーションの `fsync`/rename を含む更新と電源断試験を行う。
14. **discard:** target card が報告する discard 能力、`fstrim` の成否・時間・結果を記録する。対応や効果をカード仕様から推定しない。
15. **ハードウェア機能:** matrix の各 driver probe、firmware load、ユーザー空間利用を別々に確認し、電源異常・通常 shutdown は実測で区別する。
16. **セキュリティ:** 署名不正／鍵違いの更新拒否、read-only root 上の鍵、dm-verity digest の信頼起点を確認する。試験でカード全体を差し替えた場合に防げないことも記録する。
17. **割り当て単位と小さい file:** 同一の file tree を使い、FAT／exFAT の cluster、ext4 の 1 KiB／4 KiB block と `inline_data`、SquashFS fragment の有無を比較する。容量、fsck 時間、連続／4 KiB random I/O、同期書込み latency をカード別に記録し、外部公開の速度差をそのまま当てはめない。

 本リポジトリでは試していません。flashbench は手順案のみで、カード内部の erase unit を確定する計測として扱いません。【未確認】

### 今後の検討アイデア

- **実装済み・実機未検証:** GPIO6 電源断イベントの通知と `/`, `/boot`, `/data` の同期を Buildroot package patch で SysRq-U より前に行う。正常停止は hold-up 時間の実機測定後に判断する。
- **実装済み・実機未検証:** 初回起動時に p7 の末尾まで拡張し、ext4 `/data` を拡張する。
- **実装済み・実機未検証:** Ed25519 で更新 bundle の manifest を署名・検証する。リリース鍵の配布・更新手順は今後の運用課題として残る。
- **未着手:** 実機の公式イメージをベースラインとして測定し、比較条件を固定する。
- **未着手:** 電源断耐性の合格条件の例として、更新中を含む 200 回の電源断試験で起動不能を 0 件とする。
- **未着手:** 山城さん向けに、各フェーズの書き込み・観測・ログ採取方法を記した実機手順書を作る。

---

#### 実機でしか検証できない項目

##### 起動速度の確認（QEMU 採用済みの項目が実機で効くかの検証）

| 項目 | 実機で確かめること | 採用・根拠 |
|---|---|---|
| `CC_OPTIMIZE_FOR_SIZE` | icount では ready 仮想時刻が 3.3s → 3.69s と微増。実機では命令密度の効果（SD 読み込み削減）が逆転する可能性がある。実機の起動時間で採否を再確認 | #139 で採用（gz −1.5 MB） |
| `CONFIG_PREEMPT_RT` | 起動時間・スループットの回帰と、`cyclictest` でスケジューリングの最悪遅延を測る（RT の本来の効果は QEMU では評価不可） | #133 で採用（[比較記録](../../experiments/2026-10-30-preempt-models.md)） |
| `CONFIG_FTRACE=n` | icount −37.9 %（最大の削減）が実機でも再現するか | #135 で採用（[記録](../../experiments/2026-10-20-qemu-boottime.md)） |
| `quiet` | 実時間 −20 %（シリアル出力削減が主因）。実機の UART 速度・ログ量で効果を測る | 採用済み（[記録](../../experiments/2026-10-29-quiet-lpj.md)） |
| `mksquashfs -sort` + zstd レベル 22 | 起動時の読み順に並べた squashfs の、実機 SD 読み込み時間 | #134 で採用（[観測記録](../../experiments/2026-10-25-qemu-boot-read-order.md)） |
| userspace `-Os`+LTO、sweep 採用の kernel OFF（計 16 件+8 件） | squashfs −22.8 %・kernel gz の縮小が実機の起動時間に効くか | #138・#139・#141 で採用 |
| 起動時間の内訳（initcall_debug） | `initcall_debug` の出力から、実機での時間配分を取り残りの削減余地を洗う | [QEMU の内訳](../../experiments/2026-10-20-qemu-boottime.md) |
| dwc_otg の deferred probe | QEMU では deferred probe が WARN を出す。実機で同じ経路を通るか、USB 初期化の遅延要因になるかを確認 | [bisect 記録の罠](../../experiments/2026-10-31-qemu-1112-bisect.md) |
| gzip 再圧縮 `kernel8.img` と `align=4M` | firmware が読み込む側の時間とパーティション境界効果 | 実装済み（#8・#19） |

##### 動作・周辺機器の確認

| 項目 | 実機で確かめること |
|---|---|
| tryboot と A/B の slot 選択 | autoboot.txt・tryboot の切り替え、更新後の B スロット起動 |
| watchdog の引き継ぎ | firmware → OS の WDT 継続、給餌停止で reset（QEMU では 6 mode × 5 回済、[記録](../../experiments/2026-10-20-s11-qemu-watchdog.md)） |
| config.txt の設定 | `boot_delay`、`start_cd.elf`、`gpu_mem`、`max_framebuffers`、`core_freq`、`initial_turbo`、`arm_boost` |
| CPU governor・`maxcpus=1`・温度 | 実温度・周波数と起動時間の関係。QEMU の `temp` プロパティは模擬のみ（[記録](../../experiments/2026-10-29-qemu-thermal-temp.md)） |
| I/O スケジューラー・`read_ahead_kb`・SD の速度と erase の単位 | SD の実測転送速度・消去単位との整合 |
| `get_throttled` | 低電圧・熱制限の検出 |
| 実際の電源断 | S9 の残りと 200 回試験（[GPIO6 経路は QEMU 済](../../experiments/2026-10-20-qemu-powerfail-gpio6.md)） |
| LCD の fbcon、カメラ（S2）、IR（S7）、充電 IC（S8） | 各周辺機器の動作 |
| Lite 機判定 | BMI270/BMM150 を持たない Lite 機での `bmi270_bmm150_overlay` probe failure と msd-hwinfo の判定（QEMU では probe 失敗が無害であることを確認済み、[記録](../../experiments/2026-10-29-qemu-lite-variants.md)） |
| CMA の量 | graphics/camera 用途での確保量 |
| 更新の署名検証・dm-verity・`/data` の拡張・ramoops | 実機での拒否・性能・復旧・retention（QEMU 済のものは記録参照） |
