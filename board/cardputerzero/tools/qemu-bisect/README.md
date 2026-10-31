# qemu-bisect

QEMU の icount 起動時間回帰を `git bisect` で特定するツールです。2026-10-31 に QEMU 11.1.2 の約 8 倍遅延（第一 bad: `01b223f895`、A-profile の WFE sleeping）を特定した手順を製品条件で再現できるように整備したものです。詳細な経緯は `docs/experiments/2026-10-31-qemu-1112-bisect.md` を参照してください。

## 使い方

```sh
board/cardputerzero/tools/qemu-bisect/run-bisect.sh <bad-ref> <good-ref>
# 例: 遅い側 v11.1.2、速い側 v11.0.2
board/cardputerzero/tools/qemu-bisect/run-bisect.sh v11.1.2 v11.0.2
```

- debian:trixie-slim コンテナ内で QEMU ソース（`--filter=blob:none` クローン）とビルド領域を `output/qemu-bisect/`（`QEMU_BISECT_WORK` で変更可）に用意し、`git bisect run` を回します。
- 各コミットで `docker/qemu-patches/` の製品パッチを適用（`git apply`、失敗時は `patch --fuzz=3`、それでも不可のものだけ省略）して `qemu-system-aarch64` をビルドし、`run-qemu.sh` と同じ起動条件で起動します。
- 判定は「`MSD/Linux ready` までの実時間が `BISECT_GOOD_LIMIT` 秒以内」（既定 45 秒）。超えた時点で QEMU を打ち切って bad とするため、bad 側のコミットも 1 分程度で判定できます。
- `step.sh` の戻り値: 0=good、1=bad、125=skip（ビルド失敗・バイナリなし）。

## 必要なもの

- Docker（root 実行できる環境）
- `output/images/` に sdcard.img・Image・bcm2710-rpi-cm0.dtb のある製品ビルド
- ホストの実時間で各ステップ数分（ビルド＋起動）、全体で 10 ステップ前後

## 注意

- 判定は実時間なので、計測中はホストの負荷を一定に保ってください。
- しきい値は速い側と遅い側の中間に置きます。前回実測は good 約 15 秒・bad 約 99 秒で、45 秒で明確に分離できました。
- `QEMU_MODULE_TEST` 相当のモジュール検査は行いません（バリアント QEMU とカーネルモジュールの vermagic 不一致による誤検出を避けるため）。
