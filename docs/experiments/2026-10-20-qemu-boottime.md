# QEMU での起動時間の内訳と改善候補の比較

- 状態: 完了
- 日付: 2026-10-20
- 担当: Devin
- 関連: [起動時間（実測値と分析）](../research/boot-time-measurements.md)、`board/cardputerzero/tools/bench/boottime/`、`board/cardputerzero/tools/kernel-candidates.txt`

## 目的と仮説

QEMU で MSD/Linux の起動処理を段階ごとに測り、時間のかかる箇所を特定します。改善候補を 1 つずつ入れて、基準の版と比べます。QEMU の秒数は実機の秒数ではありません。固定した QEMU 設定のもとで、版どうしを比べるためだけに使います。

測定の前に立てた仮説は次のとおりです。

- U1: `S10mdev` が起動時に `/sys/` 全体から `modalias` を探すため遅い。探す範囲を `/sys/devices` に絞れば短くなる。
- K1: カーネルの `init_kprobe_trace`（icount で約 1.1 秒）は kprobe event の機能そのものの初期化である。`CONFIG_KPROBE_EVENTS` を無効にすれば消える。
- K2: K1 の結果を見て足した候補です（下の「結論」を参照）。ftrace 全体を無効にすれば、tracing の初期化にかかる時間が消える。
- D1: 改善の候補ではなく、診断用です。TCG でだけ長い区間が、ゲストの CPU の処理なのか、QEMU が SD カードなどのデバイスを模倣する時間なのかを調べる。

## 採否の基準（結果を見る前に書く）

U1 と K1 の結果を見る前の 2026-10-20 17:55 UTC ごろに、次の基準を決めました。K2 にも同じ基準を使いました。

- 各条件で初回起動 1 回と通常起動 5 回を行います。基準の版は 2 回（A/A）測ります。
- 主指標は、通常起動 5 回の `t_ready`（`MSD/Linux ready` のカーネル時刻）の中央値です。TCG と icount で別々に判定します。副指標は `t_init`、`t_data`、initcall の合計、各スクリプトと initcall の中央値、ホストの経過時間です。
- 候補を QEMU 上の改善とみなすのは、次をすべて満たす場合だけです。
  - 6 回の起動がすべて valid で、`test-boot.sh` の終了値が 0。
  - 通常起動の `t_ready` の中央値が baseline-a より 5 % 以上短く、かつ同じモードの A/A の差の 2 倍を超えて短い。
  - シリアルログに新しいエラーがない。読み込まれるモジュールの集合が基準と同じ。
- TCG と icount の結論が分かれたら、そのことを書き、改善とはみなしません。
- 製品に採り入れるかどうかは、実機で測ってから決めます。

## 条件

| 項目 | 値 |
|---|---|
| 基準のイメージ | PR #68 の HEAD `0b34be9c7e20a89ec003312eeada3f9931c1881e` からビルドした出力。`rootfs.squashfs` の SHA-256 は `493962124ce7e19531e070b7dc6c3e3fde5edb85638973dee3907f26994b40fa`（23,891,968 B）。カーネル `Image` の SHA-256 は `04d85a8a9863b419fc29ec2c8f62812fceeb60e383f05db14f4d46893c5879c6`（26,380,800 B） |
| QEMU 側の版 | PR #69 の HEAD `0d32e242736023084229956a1f53da0e89b9320b`（QEMU の GPIO の変更。ゲストのイメージは変えない） |
| 計測ハーネス | PR #70 の commit `bc9db6e5e159003b187a266dcc1dd7b62caf9141`。実行時に作業木への未コミットの変更はない。この commit は後で `main` の上へ載せ直し（`04cd9ce`）、ハーネスのファイルは変わっていない |
| ホスト | Ubuntu 26.04.1 LTS、Linux 7.0.0-38-generic、x86_64 |
| 開発用イメージ | `docker/msd-dev` の `msd-dev:local`（image ID `sha256:05159c6f45c0cdd5c349ecf1ce10476a3f17752a60a5c2208c641f4e3ac93ab4`） |
| QEMU | 11.1.2。machine `raspi3ap`、512 MiB、CM0 の DTB、A slot |
| Buildroot / GCC / カーネル | Buildroot 2026.08（`d6061d653d7`）、AArch64 GCC 14.3.0、kernel `6.18.57-v8` |
| モード | TCG（ホストの実時間に沿う仮想時間）と icount（`QEMU_ICOUNT=shift=0`。命令 1 個を 1 ns とする仮想時間） |
| カーネルの引数（追加分） | `initcall_debug printk.time=1 log_buf_len=4M msd.sweep=1 msd.boottime=1` |
| 変える条件 | 候補ごとに 1 か所（下表） |
| 変えない条件 | QEMU の machine と設定、DTB、SD イメージの構成、計測ハーネス |
| 繰り返し | 各条件で初回起動 1 回と通常起動 5 回。基準は 2 組。12 条件で計 72 回 |

| 条件 | 変更内容 | 作り方 |
|---|---|---|
| baseline-a、baseline-b | 変更なし | 基準のイメージをそのまま使う |
| U1 | `/etc/init.d/S10mdev` の `find /sys/ -name modalias -print0` を `find /sys/devices -name modalias -print0` に置き換える | 試験用 rootfs だけを変える。置き換える行が 1 か所だけであることを確かめる |
| K1 | カーネル設定に `# CONFIG_KPROBE_EVENTS is not set` を足す | `board/cardputerzero/linux.fragment` の末尾に追記し、`linux-reconfigure`、`m5stack-cardputerzero-rebuild`、全体のビルドを行う。`CONFIG_MODVERSIONS=y` のため、外部モジュールのパッケージも作り直す。`Image` の SHA-256 は `5acce573008baa758c57d4a919ab309c1cf2f8aa026bef1c701daa9868b5d55e`、`rootfs.squashfs` は `1260a42a710f29ccbc2a3082b9b9db9381fce85e839059f134e77ab68a742e4e` |
| K2 | K1 の追記を戻し、代わりに `# CONFIG_FTRACE is not set` を足す | K1 と同じ手順。生成した `.config` では `CONFIG_FTRACE` が無効で、`CONFIG_TRACING`、`CONFIG_KPROBE_EVENTS`、`CONFIG_BLK_DEV_IO_TRACE` の行は消えた。`Image` の SHA-256 は `320572ae61c585e2d3d6b0b347ed3b7c3b2b37b00f0b4356857dceb097989228`（20,941,312 B）、`rootfs.squashfs` は `a17ee4642b990bc1f4266cabcafdc5cc87a52fa5c16283af4070d477719df13b`（23,289,856 B） |
| D1（診断用） | inittab の sysinit の 11 行と、`S02msd-data` の各処理の前に `/dev/kmsg` への目印を足す | 試験用 rootfs だけを変える。目印の数（sysinit 11 か所、`S02msd-data` 6 か所）を確かめる |

## 手順

```sh
docker/msd-dev build
OUTPUT_DIR=/path/to/buildroot-output QEMU_LOG_DIR=/path/to/logs \
  docker/msd-dev board/cardputerzero/tools/bench/boottime/run-boottime.sh \
  --variant baseline-a --mode tcg --runs 5 --csv /path/to/logs/boot.csv --log-dir /path/to/logs
# icount は --mode icount。U1 と D1 は rootfs を変えた OUTPUT_DIR を、K1 と K2 は再ビルドした OUTPUT_DIR を渡す
python3 board/cardputerzero/tools/bench/boottime/summarize-boottime.py /path/to/logs/boot.csv
```

`run-boottime.sh` は既存の SquashFS を展開し、`rcS`（各スクリプトの開始と終了を `/dev/kmsg` に書く版）と `S99zz-boottime-dump` だけを足して試験用イメージを作ります。製品の rootfs には入りません。U1 と D1 は、その前に元の SquashFS を展開して変更し、同じ圧縮方式とブロックサイズで作り直したものを使いました。

QEMU の測定は同じホストで 1 条件ずつ順に実行し、2 つの測定を同時に走らせていません。ただし、K1 のビルドは baseline-b（icount）と、K2 のビルドは D1（icount）と同時に行いました。icount の仮想時間はホストの負荷の影響を受けにくく、baseline-b と baseline-a の差は 0.85 % でした。

## 計測器の検証

基準の版を 2 回測りました（A/A）。通常起動の `t_ready` の中央値の差は、icount で 0.025674 秒（0.85 %）、TCG で 0.179828 秒（0.74 %）でした。どちらも 5 % の基準より十分小さいため、比較に使えると判断しました。判定に使う「A/A の差の 2 倍」は icount で 0.051348 秒、TCG で 0.359656 秒、「5 %」は icount で 0.151895 秒、TCG で 1.216379 秒です。

ログで次のことも確かめました。

- 72 回の起動はすべて `valid=1` で、各条件の `test-boot.sh` の終了値は 0 でした。`test-boot.sh` はシリアルログの検査（`check-serial-log.sh` と許可リスト）を含みます。
- 読み込まれたモジュールは、baseline-a、U1、K1、K2 のすべての起動で同じ 9 個（`aes_ce_blk aes_ce_cipher bluetooth ecdh_generic ghash_ce hci_uart raspberrypi_gpiomem raspberrypi_hwmon rfkill`）でした。K1 と K2 のシリアルログに `disagrees about version`、`Invalid module format`、`verification failed`、`Unknown symbol` はありませんでした。
- `S10mdev` の終了値は、どの起動でも 123 でした。`xargs modprobe` が、対応するモジュールのない alias で 0 以外を返すためで、基準の版から同じです。

## 結果

値は中央値（最小〜最大）で、単位は秒です。試行ごとの値は同名の CSV にあります。

### 通常起動の `t_ready`（主指標）

| 条件 | icount | baseline-a との差 | TCG | baseline-a との差 | 判定 |
|---|---:|---:|---:|---:|---|
| baseline-a | 3.037890（3.031327〜3.114359） | — | 24.327573（24.019177〜26.175232） | — | 基準 |
| baseline-b | 3.063564（3.041508〜3.102215） | +0.025674（+0.85 %） | 24.507401（23.516046〜28.065498） | +0.179828（+0.74 %） | A/A |
| U1 | 2.943922（2.903880〜2.952458） | −0.093968（−3.09 %） | 23.585238（23.512894〜26.555493） | −0.742335（−3.05 %） | 基準未達（5 % に届かない） |
| K1 | 3.067266（3.030481〜3.091956） | +0.029376（+0.97 %） | 25.115355（24.412282〜27.621857） | +0.787782（+3.24 %） | 不採用 |
| K2 | 1.887120（1.876126〜1.894978） | −1.150770（−37.88 %） | 22.944577（21.927892〜25.517419） | −1.382996（−5.68 %） | QEMU 上の改善（両モード） |
| D1（診断用） | 3.108231（3.073582〜3.131238） | +0.070341（+2.32 %） | 25.159738（25.050805〜27.682648） | +0.832165（+3.42 %） | 判定しない（目印の分だけ遅い） |

### 初回起動の `t_ready`

初回起動は 1 回ずつです。

| 条件 | icount | TCG |
|---|---:|---:|
| baseline-a | 3.559526 | 26.158969 |
| baseline-b | 3.560636 | 27.089572 |
| U1 | 3.419857 | 26.751950 |
| K1 | 3.527337 | 28.206759 |
| K2 | 2.391974 | 24.931158 |
| D1 | 3.575846 | 28.395762 |

### 副指標（通常起動の中央値）

| 条件 | モード | `t_init` | `t_data` | initcall の合計 |
|---|---|---:|---:|---:|
| baseline-a | icount | 1.838838 | 2.079192 | 1.650265 |
| U1 | icount | 1.847826 | 2.084179 | — |
| K1 | icount | 1.854249 | 2.090869 | 1.667487 |
| K2 | icount | 0.713438 | 0.947870 | 0.544213 |
| baseline-a | TCG | 6.044377 | 13.374172 | — |
| K2 | TCG | 4.418181 | 11.784290 | 2.967219 |

`t_init` は `Run /sbin/init` のカーネル時刻、`t_data` は `/data` を mount した時刻です。表で「—」の欄は CSV にあり、この記録では引用していない値です。ホストの経過時間（TCG）は baseline-a で 30.103436 秒、K2 で 25.992111 秒でした。

### 時間のかかる処理（通常起動の中央値）

| 処理 | baseline-a icount | U1 icount | K1 icount | K2 icount | baseline-a TCG | K2 TCG |
|---|---:|---:|---:|---:|---:|---:|
| `initcall:init_kprobe_trace` | 1.101849 | 1.100820 | なし | なし | 1.566741 | なし |
| `initcall:init_blk_tracer` | 0.05 未満 | 0.05 未満 | 1.051737 | なし | 0.05 未満 | なし |
| `script:S10mdev` | 0.817086 | 0.704289 | 0.814523 | 0.784939 | 5.561549 | 5.341954 |
| `initcall:dwc_otg_driver_init` | 0.402151 | 0.402143 | 0.401819 | 0.401842 | 0.560628 | 0.534077 |
| `script:S02msd-data` | 0.166192 | 0.169099 | 0.165586 | 0.162905 | 4.994613 | 5.427920 |

initcall は 0.05 秒以上のものだけを CSV に記録しています。「0.05 未満」は CSV に行がないことを、「なし」はその initcall がカーネルにないことを表します。

### D1: TCG でだけ長い区間

D1 の目印の間隔です（通常起動 5 回の中央値）。目印は各処理の直前に出します。

| 区間 | TCG | icount |
|---|---:|---:|
| `Run /sbin/init` → 最初の sysinit の行 | 2.298068 | 0.068299 |
| sysinit 6 行目（`/sbin/swapon -a`） | 1.027857 | 0.031781 |
| rcS の開始 → `S02msd-data` の開始 | 0.465427 | 0.011542 |
| `S02msd-data`: ext4 の magic の確認 | 0.163563 | 0.029139 |
| `S02msd-data`: `fsck.ext4 -p` | 2.048385 | 0.058982 |
| `S02msd-data`: `mount` | 0.509790 | 0.013156 |
| `S02msd-data`: `msd-data-grow` | 2.274982 | 0.056801 |
| `S02msd-data` の終了 → `MSD/Linux ready` | 8.546717 | 0.905430 |

## 捨てた試行と経緯

- 計測ハーネスの初期版では、dmesg の行頭を `msd-dmesg:` にしていました。`check-serial-log.sh` がこれを `msd-*` サービスのログとして調べ、カーネルの `failed` などの語で `test-boot.sh` が失敗しました。行頭を `=dmesg= ` に変えて直しました（PR #70）。
- 最初の icount の試行は、`docker/msd-dev` が `QEMU_ICOUNT` をコンテナに渡していなかったため、実際には TCG で動いていました。転送する変数に加えて直しました（PR #70）。それより前に icount の値として報告した内訳は、TCG の値でした。
- K1 のビルドでは、作業木を別の場所に複製したため、コンテナの中で submodule の git の情報を辿れず、`M5STACK_CARDPUTERZERO_VERSION is empty` で 3 回失敗しました。4 回目は値を make の引数で渡して先へ進みましたが、ビルドを起動したシェルを終了したときにビルドも止まりました。コンパイラーのエラーではありません。5 回目に最後までビルドしました。K2 は同じ方法で 1 回でビルドできました。
- K1 と K2 は同じ作業木でビルドしたため、K1 の `Image` と rootfs は K2 で上書きされました。K1 の SHA-256 は上書きの前に記録しました。

## 結論

- K2（`CONFIG_FTRACE` を無効にする）は、TCG と icount の両方で基準を満たしました。QEMU 上の改善とみなします。icount では initcall の合計が 1.650265 秒から 0.544213 秒に減り、`t_ready` が 1.150770 秒（37.88 %）短くなりました。`Image` は 5,439,488 B、rootfs は 602,112 B 小さくなりました。
  - ただし、この PR では製品の設定を変えていません。ftrace を無効にすると、kprobe、blktrace、ブート時の tracing が使えなくなります。調査文書では、SquashFS の読み込み順を blktrace で調べる案が出ています（[fastboot-ideas.md](../research/fastboot-ideas.md)）。製品のビルドと調査用のビルドを分けるか、実機で測ってから決めます。`kernel-candidates.txt` にも `FTRACE n` が候補として載っています。
- U1 は 2 つのモードで約 3 % 短くなり、向きはそろいました。5 % の基準には届かないため、改善とはみなしません。icount で `S10mdev` は 0.817086 秒から 0.704289 秒になりました。
- K1 は不採用です。`init_kprobe_trace` は消えましたが、ほぼ同じ時間が `init_blk_tracer` に移り、`t_ready` は短くなりませんでした。
- D1 で、TCG でだけ長い区間（init の起動直後、swapon、fsck、`msd-data-grow` など）は、icount ではどれも 0.07 秒以下でした。これらはゲストの CPU の処理ではなく、QEMU が SD カードなどを模倣するのにかかったホストの時間だと考えます。TCG の秒数で、ユーザー空間の I/O の速さを判断しません。
- K2 のあとに icount で残る大きな処理は、`S10mdev`（0.784939 秒）と `dwc_otg_driver_init`（0.401842 秒）です。

### K1 で時間が移った理由（仮説）

ソースを読んで立てた仮説で、確かめてはいません。`trace_eval_init`（`subsys_initcall`）は、全 trace event の書式を更新する処理を workqueue に入れます。この処理（`kernel/trace/trace_events.c` の `trace_event_update_all()`）は、`event_mutex` と `trace_event_sem` を取ったまま全 event を回ります。そのため、後の initcall のうち最初にこれらのロックを取るものが、その終わりを待たされる、という見立てです。基準では `init_kprobe_trace`（`fs_initcall`）が、K1 では `register_trace_event()` を呼ぶ `init_blk_tracer`（`device_initcall`）が待っていたことになります。K2 で initcall の合計が約 1.1 秒減ったことは、この仮説と矛盾しません。ただし、ロックを待っていたことは直接観測していません。

## 未確認の点

- 実機では試していない。QEMU は GPU firmware、microSD の実際の読み書きの速さ、LCD、キーボード、M5 の I2C デバイスを再現しません。実機での秒数と、K2 の効果の大きさは未確認です。
- 計測用の `initcall_debug` と dmesg の出力そのものにかかる時間は、すべての条件に同じように入っています。製品のイメージでの秒数は測っていません。
- `raspi3b`、別の QEMU の版では測っていません。

## ログ

ログは commit しません。72 回の起動のシリアルログ、`test-boot.sh` のログ、条件ごとの CSV の SHA-256 を、同名の `.sha256` ファイルに記録しました（パスは条件ごとのログ置き場からの相対パス）。再生成には上記の手順を使います。条件ごとの CSV の SHA-256 は次のとおりです。

| CSV | SHA-256 |
|---|---|
| `baseline/tcg-a/boot.csv` | `c9d183db24851eca06c5bfc71b7128af3c07c8b1b82ed3bc47000daf313ff938` |
| `baseline/tcg-b/boot.csv` | `22ae5a49da97ebc48d06c1e504d2035f1e21a3ad86d36239f4ef87835a255a81` |
| `baseline/icount-a/boot.csv` | `e17a2decbc057013d9e7a7b5eba3ea8c8d7f7bfec5a16521fc04f7cb79af17f1` |
| `baseline/icount-b/boot.csv` | `bd902ec78cc8fa03f26700121c646f418939025a3892b453c1346368e60aed49` |
| `u1/tcg/boot.csv` | `c62c66394f02bb76a0211bebe6ce4cfc05a511a640a6259eecf646dbc35484c5` |
| `u1/icount/boot.csv` | `922c1583667daff9303c09667db996a915860e97c6f83c0b135363a2f073ca06` |
| `k1/tcg/boot.csv` | `97f97e28af4a124e126b01036923d5a4646c23f94b3663cb227929f573cd9610` |
| `k1/icount/boot.csv` | `c1cdce50cf1f6eb2e4812b8bc2d9a67d5e172905e5f2c08b44ffb0d3b2bf366d` |
| `d1/tcg/boot.csv` | `8be395859831dc51d93f048aceb27da1b6b72627764d235add89cb45d18b7ffe` |
| `d1/icount/boot.csv` | `aa1477010c57b965d58dc2357dfc41e43200f5835306a607b8a5755b099af180` |
| `k2/tcg/boot.csv` | `33cf693af12f7fb223829d89918c6389bcb0e3278e3a7ecf3c6874a481d3eabd` |
| `k2/icount/boot.csv` | `fb52e0a120e37e673792e7e52fa1b8af0fc41c10cbe5c619b666e94e24092e72` |
