# zram の CONFIG_ZRAM=y と =m の起動時間

- 状態: QEMUで測定。m側swap無効で機能非等価。明示loadを加えた場合の起動時間は未測定
- 日付: 2026-11-15
- 担当: Devin
- 関連: [起動時間の測定器](../../board/cardputerzero/tools/bench/boottime/)、[書き込みの台帳](../design/write-policy.md)

## 目的と仮説

zramをモジュール（`CONFIG_ZRAM=m`）にするとkernel本体の初期化が少し早くなり、起動時間が短くなるのでは、という仮説を確かめます。引き継ぎタスク5です。

## 採否の基準（計測前）

- 各variantで独立したbootを6回（初回1回＋2回目以降5回）行い、t_readyの中央値・最小・最大を記録します。
- icount mode（`QEMU_ICOUNT=shift=0`）で測り、host負荷の影響を除きます。
- 両variantでzram swapが実際に有効かを確認します。=mで有効化されていなければ公平な比較にならないため、その旨を明記します。
  → 結果として =m 側は swap が有効化されておらず（後述）、起動時間の比較自体は成立しますが「機能込みの等価比較」ではありません。

## 条件と手順

基準は `733d27e66c8499aa306325cb4ce928c6ed2f1034`、Buildrootは `8b238854d909c9cce32ef9671d968b03e323b55d`。QEMUは11.1.2、kernelは6.18.59-v8。

- y側: `output-openssl-lts`（linux.fragmentの `CONFIG_ZRAM=y` そのまま）
- m側: `output-zram-m`。`CONFIG_ZRAM=m` のfragmentを `BR2_LINUX_KERNEL_CONFIG_FRAGMENT_FILES` に追加してdefconfigから作り直し

測定は `board/cardputerzero/tools/bench/boottime/run-boottime.sh --mode icount --runs 5` で、boottime用のtest rootfsへinstrumentを注入して実行しました。kernelとdtbは各variantの `images/` から渡しています。

## 結果

t_ready（kernel開始からrcS完了までの経過、秒）:

| variant | 初回 | warm中央値 | warm最小 | warm最大 | n |
|---|---:|---:|---:|---:|---|
| =y | 2.153361 | 1.644829 | 1.629338 | 1.675305 | 5 |
| =m | 2.185409 | 1.639744 | 1.631340 | 1.669734 | 5 |

補助の値（warm中央値）:

| variant | t_init | initcall_total | initcall_count | module_initcall_total | module_initcall_count | S99msd-zram | t_data |
|---|---:|---:|---:|---:|---:|---:|---:|
| =y | 0.907 | 0.719897 | 774 | 0.000965 | 5 | 0.0059 | 1.13 |
| =m | 0.901 | 0.708598 | 773 | 0.001213 | 5 | 0.0059 | 1.13 |

## 帰属

- 差はwarm中央値で約0.005秒（=mの方がわずかに小さい）。最小・最大の帯域は重なります。この条件では明確な差を検出していませんが、機能非等価の比較で、同等性の証明ではありません。
- =mではzram swapは有効になりませんでした。`zram.ko.xz` はimageに入りますが、zramにはhardware modaliasがなく、S10mdevの `modprobe -abq`（modalias自動load）ではloadされません。`/etc/modules-load.d/` も空で、`S99msd-zram` のworkerは `test -b /dev/zram0` でexit 1します。serialログインでの実測: `/proc/swaps` はheaderのみ、`/dev/zram0` 不在、`/run/msd-zram.log` は空（status=0・所要0.006秒はworkerの起動結果で、swap有効化の完了ではありません）。
- module_initcall_totalは両variantとも5件・0.001秒程度ですが、全moduleの集計でありzram単体の初期化時間ではありません。m側ではzramをloadしていないため、load追加時の遅延は測れていません。

## 結論

このimageのm側は **zram swap自体が有効化されていません**。現行の `=y` を維持する判断材料ですが、明示loadを追加して機能を揃えた比較は未実施です。load追加後の速度・RAM・Image容量を含む利得の有無や、実機での性能は、この測定から決められません。

## 失敗・限界

- QEMUのicountは決定的ですが、wall timeはhost負荷で変わります（warm wall median: =y 157秒、=m 160秒）。sector数・t_ready等のicount値は負荷非依存です。
- 実機ではmicroSDの読み出し速度でkernel本体のload時間が変わり、=mにした分のkernel削減が実時間に効く可能性はあります。実機未測定です。
- =m側のserial logでS10mdevがstatus=123を返しますが、これはmdev本体の終了コードです。zram.ko.xz は rootfs に入っていますが、hardware modalias を持たないため `modprobe -abq` ではloadされず、`/etc/modules-load.d/` も空なので、実際にはloadされずswapは無効のままです（serialログインして `/proc/swaps`・`/dev/zram0` を実測確認）。=mにするなら明示的なload機構が別途必要です。

## 再生成

```sh
# m側の環境。保存済みのm用fragmentを先に取得して配置する（本文参照）。
docker/msd-dev make -C vendor/buildroot BR2_EXTERNAL=/work O=/work/output-zram-m msd_cardputerzero_defconfig
docker/msd-dev vendor/buildroot/utils/config --file output-zram-m/.config --set-str BR2_LINUX_KERNEL_CONFIG_FRAGMENT_FILES '$(BR2_EXTERNAL_MSD_PATH)/board/cardputerzero/linux.fragment /work/output-zram-m/linux-zram-m.fragment'
docker/msd-dev make -C output-zram-m olddefconfig
docker/msd-dev make -C output-zram-m -j8
# 計測（各variant。入力rootfsなどはOUTPUT_DIR環境変数で指定）
docker/msd-dev env OUTPUT_DIR=/work/output-openssl-lts \
  board/cardputerzero/tools/bench/boottime/run-boottime.sh \
  --variant y --runs 5 --csv /work/output-e2/zram-y.csv \
  --log-dir /work/output-e2/logs-y --mode icount
docker/msd-dev env OUTPUT_DIR=/work/output-zram-m \
  board/cardputerzero/tools/bench/boottime/run-boottime.sh \
  --variant m --runs 5 --csv /work/output-e2/zram-m.csv \
  --log-dir /work/output-e2/logs-m --mode icount
# swap有効の確認（serialログインで /proc/swaps を採取）
docker/msd-dev python3 docs/experiments/2026-11-15-zram-builtin-vs-module-check-swap.py \
  /work/output-zram-m /work/output-e2/zram-check-m.log
```

raw CSVは [2026-11-15-zram-builtin-vs-module.csv](2026-11-15-zram-builtin-vs-module.csv)。logのSHA-256はCSVの `log_sha256` 列に入っています。

rawは[data枝の保存directory](https://github.com/uist1idrju3i/MSD-Linux/tree/ab61a9ffa86635b02e0382f357d7da9e7d084077/session-2026-11-15/evidence)にあります。m用fragmentを `e2-zram-m-inputs.tar.zst` から新規の `output-zram-m/linux-zram-m.fragment` へ配置してから上記を実行します。fragmentを設定せずdefconfigだけ再生成してもm構成になりません。warm treeを再利用する場合はkernelの再configure/buildが必要です。当時のimageとのbyte一致は未確認です。

| archive | SHA-256 |
|---|---|
| `e2-zram-boottime.tar.zst` | `7869e1ef833fb6ca74b67c5f72ebeba40635db5475e956fd4f6a7614fe04d8a1` |
| `e2-zram-m-inputs.tar.zst` | `43af747e5919115649e0778f1c092325f6a4af6339dbe22ac8fb8fdd89dc2903` |
| `e2-zram-swap-check.tar.zst` | `3124e6221ad2313eb5302fd7256b8fdb623f0ac215db7162ade4ccc234019972` |
