# S12 SquashFS の圧縮方式と block size

- 状態: 完了（QEMU とホスト）
- 日付: 2026-10-25
- 担当: Devin
- 関連: [シミュレーション検証計画](../research/simulation-plan.md)、[起動時間の QEMU 測定](2026-10-20-qemu-boottime.md)、`board/cardputerzero/tools/bench/s12-squashfs-codec.sh`

## 目的と仮説

rootfs の SquashFS は、いまは zstd、block size 128 KiB です（`BR2_TARGET_ROOTFS_SQUASHFS4_ZSTD`、`BR2_TARGET_ROOTFS_SQUASHFS_BS_128K`）。圧縮方式と block size を変えたときの rootfs のサイズと、QEMU の icount での起動時間を測ります。

仮説は次のとおりです。

- サイズは xz が最も小さく、lz4 と lzo が最も大きい。
- icount の起動時間は、展開の命令数が少ない lz4 が最も短く、xz が最も長い。ただし、起動で読む量は rootfs の一部なので、差は数 % に留まる。
- block size を大きくすると、サイズは小さくなる。起動時間は、小さなファイルを読むたびに大きな block を展開するので、長くなる。

## 採否の基準（結果を見る前に書く）

- 主指標は、通常起動 5 回の `t_ready` の中央値（icount）です。基準は zstd128a（いまの設定）です。
- 差が「A/A の差（zstd128a と zstd128b の中央値の差）の 2 倍」と「基準の 5 %」の両方を超えたときだけ、差があるとみなします。
- サイズは、mksquashfs の出力のバイト数をそのまま比べます。rootfs の A/B パーティションに入らない条件は不採用とします。
- QEMU は SD カードの読み出しの速さを模していません。icount の仮想時間は、ゲストの命令数を表します。そのため、QEMU の結果だけでは既定の設定を変えません。差があった条件は、実機で測る候補として残します。

## 条件

| 項目 | 値 |
|---|---|
| 基準の commit | `87aadf5c27846838d2eb16f2f81bb62675569b16`（ビルド）。runner は `703beec11b29c9bc68698f5a4d461cb70838c7d6`（S12 のブランチ。`run-boottime.sh` に `--squashfs-comp` と `--squashfs-block` を足しただけ） |
| ホスト | Ubuntu 26.04.1 LTS、12 CPU。開発用イメージ（`docker/msd-dev`）の中で実行 |
| QEMU | `QEMU emulator version 11.1.2`、machine `raspi3ap`、`QEMU_ICOUNT=shift=0`。開発用イメージは `ghcr.io/uist1idrju3i/msd-dev:inputs-36d7c1601eab8fc5`（image ID `sha256:2a2c70d17140c650ee59d4b4fcf31819670851ad0b44164544ccfb35afa0b157`、手元では `msd-dev:local` の名前で使った）。この tag は、runner の commit `703beec` で `docker/msd-dev tag` を実行した値と一致する。image 内の `qemu-system-aarch64` の SHA-256 は `a1dfa3b632e3864fe887c90198947c470dc9f47c4e7c0cce8ba952fefe2f0d59` |
| mksquashfs / unsquashfs | `mksquashfs version 4.7.5 (2026/03/01)`（Buildroot の `output/host/bin`） |
| カーネル | `rpi-6.18.y` の `234188315037848e5b07d65b85d38edc64095caa`。`CONFIG_SQUASHFS_ZLIB`、`_LZ4`、`_LZO`、`_XZ`、`_ZSTD` がすべて `y`、`CONFIG_SQUASHFS_DECOMP_SINGLE=y` |
| 入力 | `Image` SHA-256 `1c085405fedf067be7c8efeadd1f1a779896baa7de60d6ed139f7faf3c5eb8a3`、基準の rootfs `28164bdda81a7ca44e87c444937d01db62cee29a41b33a75e7a4231f7678434b`、DTB `e035db2336d4081dcaf76bf2d336404aca4d9421a8c0de8133e8962ef385c98f` |
| 変える条件 | 圧縮方式（zstd、gzip、xz、lz4、lzo）と block size（128 KiB、256 KiB、1 MiB）。block size を変えるのは zstd だけ |
| 変えない条件 | rootfs の中身（基準の rootfs を展開し、起動時間の測定用の `rcS` と `S99zz-boottime-dump` を足したもの）、mksquashfs の他の option（`-noappend -all-root -no-xattrs`）、カーネル、DTB、カーネルの引数 |
| 繰り返し | 条件ごとに初回起動 1 回と通常起動 5 回。集計は通常起動 5 回の中央値と最小・最大。ホストでの展開時間（`unsquashfs -processors 1`）は 5 回 |

## 手順

ホストで、runner の commit を clone した場所を `/work` に、Buildroot の出力先（`O=`）を同じパスに mount して、開発用イメージの中で次を実行しました。開始は 2026-10-25T10:06:33Z、終了は 14:00 UTC ごろです。

```sh
docker run --rm --user 0:0 --env HOME=/tmp/home \
  --volume "$CLONE":/work --workdir /work \
  --security-opt no-new-privileges --cap-drop ALL \
  --volume "$OUTPUT_DIR":"$OUTPUT_DIR" --env OUTPUT_DIR="$OUTPUT_DIR" \
  --entrypoint /bin/bash msd-dev:local -c 'mkdir -p -- /tmp/home && exec "$@"' msd-dev \
  board/cardputerzero/tools/bench/s12-squashfs-codec.sh
```

`s12-squashfs-codec.sh` は、条件ごとに `run-boottime.sh --mode icount --squashfs-comp <方式> --squashfs-block <バイト数> --runs 5` を呼ぶ runner です。`run-boottime.sh` は、基準の rootfs を展開し、測定用のファイルを足して `mksquashfs -noappend -all-root -no-xattrs -comp <方式> -b <バイト数>` で作り直し、image の rootfs A に書き込んでから、初回起動（repeat 0）1 回と通常起動 5 回を行います。起動の後に、同じ rootfs をホストで `unsquashfs -no-progress -no-xattrs -processors 1` で 5 回展開した時間も測ります。条件は既定の 8 個（`zstd128a gzip128 xz128 lz4128 lzo128 zstd256 zstd1m zstd128b`）で、環境変数では変えていません。runner は、既存の CSV があれば止まります。

## 計測器の検証

- A/A 試行: zstd128a と zstd128b は同じ条件です。`t_ready` の中央値の差は 0.002134 秒（+0.07 %）でした。rootfs のバイト数は同じ（23,891,968）で、SHA-256 は違いました（`acc10cc4…`、`2e365f18…`）。mksquashfs が作成時刻を書き込むためです。
- 作った rootfs の方式: 8 個の rootfs を `unsquashfs -s` で読み、`Compression` と `Block size` が条件どおりであることを確かめました。
- 起動: 48 回の起動すべてで、`exit_status` は 0 で、シリアルのログに `VFS: Mounted root (squashfs filesystem) readonly` がありました。カーネルは 5 つの方式をすべて組み込んでいるので、どの方式でも rootfs を読めています。
- 警告とエラー: 条件ごとに、シリアルのログの `error`、`fail`、`warn`、`oops` を含む行を集めて比べました。どの条件にも、次の既知の行だけがありました。圧縮方式に関係する行はありません。
  - `bcm2835-aux-uart …: error -EINVAL: unable to register 8250 port`（QEMU の mini UART）
  - `check access for rdinit=/init failed: -2, ignoring`
  - `mmc1: Failed to initialize a non-removable card`（Wi-Fi の SDIO。gzip128、lzo128、zstd1m の 6 回の起動では出なかった）
  - `tty->count` の警告（どの条件でも 96 行。原因は [tty->count の記録](2026-10-25-qemu-tty-count.md)）
- スクリプトの終了値: `S10mdev` はすべての起動で 123 でした。[起動時間の QEMU 測定](2026-10-20-qemu-boottime.md) と同じ既知の値です。ほかのスクリプトはすべて 0 でした。
- `initcall:deferred_probe_initcall` の行: パーサーは 50 ms 以上かかった initcall を行にします。この行は 48 回のうち 8 回に出ました（0.051〜0.063 秒）。条件との対応はありません。
- ホストでの展開: 40 回すべて `valid=1` でした。

## 結果

`t_init`、`t_data`、`t_ready` は icount の仮想時間（秒）です。通常起動 5 回の中央値と、括弧内に最小〜最大を書きます。QEMU wall は QEMU の実時間（秒）で、ほかの作業と同時に走らせた回があるため、判定には使いません。展開はホスト（x86_64、1 CPU）の秒数です。

| 条件 | rootfs（バイト） | `t_init` | `t_data` | `t_ready` | 初回起動の `t_ready` | QEMU wall | ホストでの展開 |
|---|---:|---|---|---|---:|---|---|
| zstd128a（基準） | 23,891,968 | 1.839（1.839〜1.851） | 2.081（2.072〜2.084） | 3.046（3.035〜3.059） | 3.549 | 300.3（248.7〜306.3） | 0.132（0.130〜0.150） |
| gzip128 | 24,993,792 | 1.845（1.839〜1.859） | 2.106（2.100〜2.119） | 3.114（3.079〜3.123） | 3.620 | 306.2（285.1〜329.5） | 0.233（0.223〜0.261） |
| xz128 | 22,425,600 | 1.844（1.836〜1.901） | 2.611（2.602〜2.667） | 3.776（3.771〜3.837） | 4.276 | 287.1（237.7〜291.2） | 0.687（0.633〜0.720） |
| lz4128 | 30,167,040 | 1.852（1.838〜1.856） | 2.009（1.999〜2.020） | 2.949（2.943〜2.954） | 3.538 | 291.2（277.0〜318.4） | 0.095（0.076〜0.103） |
| lzo128 | 26,214,400 | 1.840（1.835〜1.892） | 2.020（2.016〜2.069） | 2.958（2.950〜3.007） | 3.478 | 299.2（268.0〜308.3） | 0.145（0.130〜0.159） |
| zstd256 | 23,486,464 | 1.866（1.840〜1.886） | 2.117（2.105〜2.134） | 3.098（3.087〜3.107） | 3.581 | 283.1（260.8〜327.5） | 0.133（0.132〜0.155） |
| zstd1m | 23,879,680 | 1.851（1.834〜1.916） | 2.131（2.114〜2.196） | 3.178（3.172〜3.241） | 3.673 | 284.1（271.0〜295.2） | 0.116（0.111〜0.122） |
| zstd128b（A/A） | 23,891,968 | 1.839（1.832〜1.879） | 2.077（2.065〜2.119） | 3.048（3.030〜3.089） | 3.548 | 304.3（281.1〜325.5） | 0.145（0.138〜0.147） |

基準との差です。判定の閾値は、A/A の差の 2 倍（0.004268 秒）と基準の 5 %（0.152277 秒）の両方を超えることなので、実際には 0.152277 秒を超えた条件だけが差ありになります。

| 条件 | `t_ready` の差 | `t_data` の差 | rootfs の差 | 判定 |
|---|---:|---:|---:|---|
| gzip128 | +0.068723（+2.26 %） | +0.025424 | +1,101,824（+4.61 %） | 差なし |
| xz128 | +0.729994（+23.97 %） | +0.530868 | −1,466,368（−6.14 %） | 差あり（遅い） |
| lz4128 | −0.096894（−3.18 %） | −0.072017 | +6,275,072（+26.26 %） | 差なし |
| lzo128 | −0.087058（−2.86 %） | −0.060039 | +2,322,432（+9.72 %） | 差なし |
| zstd256 | +0.052518（+1.72 %） | +0.036277 | −405,504（−1.70 %） | 差なし |
| zstd1m | +0.131978（+4.33 %） | +0.050506 | −12,288（−0.05 %） | 差なし |
| zstd128b | +0.002134（+0.07 %） | −0.003889 | 0 | A/A |

- `t_init`（カーネルが init を始めるまで）は、どの条件でも 1.83〜1.92 秒で、方式による差はありません。差は、init が rootfs のファイルを読み始めてから（`t_data` と `t_ready`）に出ています。
- どの rootfs も、A/B の rootfs パーティション（256 MiB）に入ります。最も大きい lz4128 でも 30,167,040 バイトです。

仮説との対応です。

- サイズ: xz が最も小さく、lz4 が最も大きいという仮説は合っていました。lzo は 2 番目に大きいです。
- 起動時間: lz4 が最も短く、xz が最も長いという順は合っていました。ただし、lz4 と lzo の短縮は約 3 % で、基準の 5 % に届きません。xz は 24 % 長く、「数 % に留まる」という仮説は外れました。
- block size: 256 KiB では rootfs が 1.7 % 小さくなりました。1 MiB では 128 KiB とほぼ同じ（−12,288 バイト）で、256 KiB より大きくなりました。「大きくすると小さくなる」は 1 MiB では成り立ちません。起動時間は block size が大きいほど長くなりましたが、どちらも基準の 5 % 未満です。

## 捨てた試行と経緯

- 最初は S12 の worktree の中で runner を実行しようとしました。開発用イメージの中から worktree の `.git` が指す先が見えず、`fatal: not a git repository` で `git_head` を取れませんでした。そこで止め、runner の commit を別の場所に clone して実行しました。この試行の値は使っていません。
- 測定中に、同じホストで別の QEMU 試験（[PR #95](https://github.com/uist1idrju3i/MSD-Linux/pull/95) の確認、[tty->count の記録](2026-10-25-qemu-tty-count.md) の本番）を走らせた時間があります。icount の仮想時間はホストの負荷に左右されないので、判定の値はそのまま使います。QEMU wall はその影響を受けるので、判定には使いません。
- runner の commit `703beec` は、記録を出す前に main へ rebase したので、ブランチ上では `1a11956` になりました。`s12-squashfs-codec.sh` と `boottime/` の中身は同じです。`run-qemu.sh` には、測定の後に [PR #95](https://github.com/uist1idrju3i/MSD-Linux/pull/95) の provenance の行が入りました。測定に使った `703beec` にはこの行がないため、ログに `run-qemu: sha256` の行はありません。QEMU の SHA-256 は image から直接取りました。
- QEMU の binary の出どころを確かめるため、測定の後に、現在の main（`cf60569`）から開発用イメージの QEMU の段（`docker build --target qemu`）を手元で作りました。できた binary の SHA-256 は `7199b846…` で、測定に使った GHCR の image の `a1dfa3b6…` とは違いました。`7199b846…` は、S11 v3 で手元で作った binary と同じ値です。QEMU の段の入力（Dockerfile の QEMU の部分と patch）は、`703beec` から main まで変わっていません。手元と CI の build で binary が一致しないと考えられますが、確かめてはいません。測定に使った image が `703beec` の入力から作られたことは、image の tag で確かめました。

## 結論

- QEMU の icount では、基準（zstd、128 KiB）と比べて差があったのは xz だけでした。xz は rootfs を 6.1 % 小さくしますが、`t_ready` を 24 % 長くします。
- lz4 と lzo は約 3 % 短く、rootfs は 26 % と 10 % 大きくなりました。gzip と、zstd の 256 KiB・1 MiB は、起動時間で差なしです。
- QEMU の結果からは、既定の設定（zstd、128 KiB）を変える理由はありません。製品の設定は変えていません。
- 採否の基準に従い、実機で測る候補は差があった xz です。xz は rootfs が小さく、SD カードから読む量が減ります。実機では、そのぶん QEMU より差が縮む可能性があります。
- lz4 と lzo は差なしと判定しました。ただし短くなる向きなので、実機で xz を測るときに一緒に測ると比べやすくなります（基準の外の追加の提案）。lz4 は rootfs が 26 % 大きく、実機では読む量が増える不利が出る可能性があります。

## 未確認の点

- 実機の起動時間。QEMU は SD カードの読み出しの速さを模していません。icount の仮想時間は命令数を表し、Cortex-A53 の実際の速さやキャッシュの効果は入っていません。
- 起動後のアプリの起動時間、RAM の使用量（page cache と展開の buffer）。
- EROFS との比較（S12 の計画にはあるが、今回は行っていない）。
- 測定に使った GHCR の image の QEMU の binary を、commit から作り直して一致させること（上の「捨てた試行と経緯」）。

## ログ

- 生の値: [2026-10-25-s12-squashfs-codec.csv](2026-10-25-s12-squashfs-codec.csv)。起動の行（`metric` が `t_ready` など）と、ホストの行（`rootfs_bytes`、`host_unsquashfs_1cpu`）を 1 つにまとめた。repeat 0 が初回起動。
- シリアルと試験のログ（96 個）はコミットしていません。SHA-256 を [2026-10-25-s12-squashfs-codec.sha256](2026-10-25-s12-squashfs-codec.sha256) に書きました。上の「手順」のコマンドで再生成できます。
