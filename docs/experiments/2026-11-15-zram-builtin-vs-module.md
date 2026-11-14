# zram の CONFIG_ZRAM=y と =m の起動時間

- 状態: QEMUで測定。起動時間の差は実質なし。=mでも起動中に自動loadされzram swapは有効
- 日付: 2026-11-15
- 担当: Devin
- 関連: [起動時間の測定器](../../board/cardputerzero/tools/bench/boottime/)、[書き込みの台帳](../design/write-policy.md)

## 目的と仮説

zramをモジュール（`CONFIG_ZRAM=m`）にするとkernel本体の初期化が少し早くなり、起動時間が短くなるのでは、という仮説を確かめます。引き継ぎタスク5です。

## 採否の基準（計測前）

- 各variantで独立したbootを6回（初回1回＋2回目以降5回）行い、t_readyの中央値・最小・最大を記録します。
- icount mode（`QEMU_ICOUNT=shift=0`）で測り、host負荷の影響を除きます。
- 両variantでzram swapが実際に有効かを確認します。=mで有効化されていなければ公平な比較にならないため、その旨を明記します。

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

- 差はwarm中央値で約0.005秒（=mの方がわずかに小さい）。最小・最大の帯域がほぼ重なり、計測系のばらつき以下です。**起動時間の差は実質ありません。**
- =mでもzram swapは有効でした。`zram.ko.xz` がimageに入り、S10mdevの `modprobe -abq`（modalias自動load）で起動中にloadされ、`/dev/zram0` が作られて `S99msd-zram` が `zstd`・`MemTotal/2`・`swapon -p 100` を完了しています（status=0、所要0.006秒）。
- zramのinit自体が0.001秒級のmodule_initcall_totalから見て、組込みでもモジュールでも支配項ではありません。
- module_initcall_totalは両variantとも5件・0.001秒程度で、=mにしてもmodprobeによる遅延は発生していません。

## 結論

`CONFIG_ZRAM` を `=y` → `=m` に変えても起動時間は変わりません。zram自体のinitが支配項でなく、mdevのmodalias自動loadで実害なく有効化されるためです。`=y` を維持するか、モジュール化でrootfs容量をわずかに減らすかは、起動時間以外の観点（容量、署名方針）で判断すればよい状態です。

## 失敗・限界

- QEMUのicountは決定的ですが、wall timeはhost負荷で変わります（warm wall median: =y 157秒、=m 160秒）。sector数・t_ready等のicount値は負荷非依存です。
- 実機ではmicroSDの読み出し速度でkernel本体のload時間が変わり、=mにした分のkernel削減が実時間に効く可能性はあります。実機未測定です。
- =m側のserial logでS10mdevがstatus=123を返しますが、これはmdev本体の終了コードでありmodaliasのload失敗を意味しません（zram含め問題なくloadされています）。

## 再生成

```sh
# m側の環境（output-zram-m。fragmentは output-zram-m/linux-zram-m.fragment）
docker/msd-dev sh -c 'make -C vendor/buildroot BR2_EXTERNAL=/work O=/work/output-zram-m msd_cardputerzero_defconfig && make -C output-zram-m -j8'
# 計測（各variant）
board/cardputerzero/tools/bench/boottime/run-boottime.sh \
  --output output-e2 --variant y --runs 5 --csv output-e2/zram-y.csv \
  --log-dir output-e2/logs-y --mode icount \
  --kernel output-openssl-lts/images/Image --dtb output-openssl-lts/images/bcm2710-rpi-cm0.dtb \
  --rootfs output-openssl-lts/images/rootfs.squashfs
```

raw CSVは [2026-11-15-zram-builtin-vs-module.csv](2026-11-15-zram-builtin-vs-module.csv)。logのSHA-256はCSVの `log_sha256` 列に入っています。
