# QEMU の温度を任意値にする（bcm2835_thermal）

- 状態: 完了（QEMU のみ）
- 日付: 2026-10-29
- 担当: Devin
- 関連: [docker/qemu-patches/README.md](../../docker/qemu-patches/README.md)

## 目的

QEMU の bcm2835_thermal は常に約 25 °C を返すダミーで、温度に依存する動作（throttling、警告、過熱時の挙動）を試せなかった。任意の温度を注入できるようにする。

## 変更

- `docker/qemu-patches/0004-hw-misc-bcm2835_thermal-make-temperature-settable.patch`: デバイスに `temp` プロパティ（int32、°C、既定 25）を追加し、A_STAT の返り値を定数からその値に変える。QEMU 11.1.2 のプロパティ配列は `device_class_set_props` で要素数を数えるため終端子は不要。
- `board/cardputerzero/qemu/run-qemu.sh`: `QEMU_EXTRA_ARGS`（空白区切り）を QEMU の引数に追加できるようにする。`-global` など既存の環境変数で渡せないオプション用。
- 使い方: `QEMU_EXTRA_ARGS='-global bcm2835-thermal.temp=90'`。

## 条件

- パッチ適用済みの QEMU 11.1.2（`docker/msd-dev.Dockerfile` の qemu ステージを `QEMU_VERSION=11.1.2` でビルド）
- 起動パラメーターは `init=/bin/sh`（init なしのため `mount -t sysfs none /sys` を先に実行）、`QEMU_DTB_BLUETOOTH=0`
- 読み取りは `/sys/class/thermal/thermal_zone0/temp`（ミリ°C、ドライバー `CONFIG_BCM2835_THERMAL=y`、thermal zone `cpu-thermal`）

## 生の値

| `-global` の値 | ゲストの読み取り（m°C） |
|---|---|
| 未指定 | 25178 |
| `bcm2835-thermal.temp=-20` | -19476 |
| `bcm2835-thermal.temp=90` | 90276 |

## 結果

- 注入した温度がゲストの thermal zone から読める。既定（未指定）は従来どおり約 25 °C。
- 読み取り値は係数変換の刻みで量子化される（90 → 90.276 °C、-20 → -19.476 °C）。±0.5 °C 程度のずれは仕様として許容する。
- VMState に `temp_c` を `version_id=2` で加えたので、移行なしの利用では互換性の問題は出ない。

## 失敗した試行

- `docker/msd-dev` 経由では、標準入力が端末でないとき `-i` が付かず、パイプしたコマンドがゲストのシリアルに届かなかった。`docker run -i` でコンテナを直接起動して解決した。
- パッチの include を QEMU 11.0 系の `hw/qdev-properties.h` にしたままビルドしたところ、11.1 系ではヘッダーが `hw/core/qdev-properties.h` に移っていてビルドエラーになった。

## 未検証

- 実機での読み取り値との比較は未実施（本実験は QEMU のみ）。
- throttling / 警告をトリガーする製品側の動作はこの記録では試していない。
