# rootfsの読込み順・配置・先読みの調査

[保存領域の案内へ戻る](README.md) / [ユーザー空間](../userspace/README.md)

現行rootfsはSquashFS+zstdで、可変な設定にはoverlayを使います。以下のsort・観測・先読みは手順案と過去の試験を含み、配置最適化を製品へ採用済みという意味ではありません。[QEMUの読込み観測](../../experiments/2026-10-25-qemu-boot-read-order.md)はSDのFTLや実機の速度を再現せず、[filesystemの比較](../alternatives/filesystems.md)とも役割を分けます。

元の16.4節を表・コマンド・条件・出典ごと移しています。SquashFSの並びだけでなく、圧縮、読込みの観測、EROFSとの比較条件を続けて読みます。

### 16.4 SquashFS + overlayfs と読込み順最適化

#### (a) mksquashfs のオプション（Squashfs-tools 4.7.5 / 4.7.6）
| 項目 | 事実 | 出典URL | 確認度 |
|---|---|---|---|
| 並び順指定 `-sort` | `-sort SORT-FILE`:「SORT-FILE の優先度に従ってファイルを並べる。1 行に 1 ファイル or ディレクトリと優先度、優先度は -32768〜32767、既定 0」 | https://github.com/plougher/squashfs-tools/blob/db038ef265ed00bb17aaf695a72f9b0c3489eb20/Documentation/manpages/mksquashfs.1#L179-L181 | 一次(man、sort.c)。`sort_files_and_write` は優先度 65535 から 0 へ降順に処理し、優先度の高いファイルが先に書かれます。同一優先度では後から追加されたものが先です。通常ファイルのみが対象で、ディレクトリ指定は配下に優先度を継承します。https://github.com/plougher/squashfs-tools/blob/db038ef265ed00bb17aaf695a72f9b0c3489eb20/squashfs-tools/sort.c |
| ブロックサイズ | `-b` の既定は 128 KiB で、4 KiB〜1 MiB を選べます。128 KiB を超えると圧縮率（特に XZ / ZSTD）や I/O 性能が上がる可能性がある一方、断片が多く参照局所性がない場合はレイテンシが増えうるため、256 KiB 以上を試すよう記載されています。 | https://github.com/plougher/squashfs-tools/blob/db038ef265ed00bb17aaf695a72f9b0c3489eb20/Documentation/4.7.5/USAGE-MKSQUASHFS#L189-L219<br>https://github.com/plougher/squashfs-tools/blob/db038ef265ed00bb17aaf695a72f9b0c3489eb20/Documentation/4.7.5/USAGE-MKSQUASHFS#L340-L352 | 一次 |
| 圧縮方式 | GZIP（既定）/ LZO / LZ4 / XZ / ZSTD。USAGE には「LZO は GZIP より圧縮率が低いが展開が速い。XZ は圧縮率が良いが展開が遅い。LZ4 は LZO に近い。ZSTD は圧縮率と速度の両立を狙う」とあります。カーネルで該当方式が有効である必要があります。 | https://github.com/plougher/squashfs-tools/blob/db038ef265ed00bb17aaf695a72f9b0c3489eb20/Documentation/4.7.5/USAGE-MKSQUASHFS#L283-L303 | 一次 |
| SquashFS カーネル側 | 圧縮は zlib/lz4/lzo/xz/zstd、ブロックは最大 1MiB(既定 128K)。ディレクトリはソート済みで索引あり | https://docs.kernel.org/filesystems/squashfs.html | 一次 |
| 圧縮なしイメージ | `-no-compression`（= `-noI -noD -noF -noX`）で無圧縮の SquashFS を作れます。SD の読込量は増えますが、展開 CPU が不要になる効果は未測定です（推測）。 | https://github.com/plougher/squashfs-tools/blob/db038ef265ed00bb17aaf695a72f9b0c3489eb20/Documentation/4.7.5/USAGE-MKSQUASHFS#L353-L356 | 一次（機能） / 推測（効果） |

#### (b) 起動時に読むファイルの記録方法
| 手法 | 事実 | 出典URL | 確認度 / 注意 |
|---|---|---|---|
| strace | `-e trace=openat,execve` 等でプロセスごとのファイル open を記録。ただし**読込順=開く順** であり、実際のブロック I/O 順ではない。ptrace のオーバーヘッドで起動順序が変わりうる(推測) | https://man7.org/linux/man-pages/man1/strace.1.html | 一次(機能)/ 推測(影響) |
| fanotify | ファイルシステム全体の open/access 等のイベントを監視できる API(man の fanotify_mark 節参照)。strace より影響が小さく、全プロセスを横断して「実際にアクセスされたファイル」を取れる。使うには CAP_SYS_ADMIN 相当(man の記載範囲) | https://man7.org/linux/man-pages/man7/fanotify.7.html | 一次(API)/ 推測(低影響) |
| blktrace | ブロック層の I/O(セクタ・サイズ・順序)を記録。**SquashFS 上のブロック読込順を直接観測** でき、配置最適化の効果検証に向く。開発用カーネルに `CONFIG_BLK_DEV_IO_TRACE` が必要(man 参照。CM0 向けビルドでの有効化は未確認) | https://man7.org/linux/man-pages/man8/blktrace.8.html | 一次(ツール)/ CM0 での実績は未確認 |
| readahead(2) | 起動時に先読みする用途のシステムコール | https://man7.org/linux/man-pages/man2/readahead.2.html | 一次（システムコールの説明）。SD での効果は未確認です。CardputerZero 上で有効・無効を比較測定する必要があります。 |

【推測】手順案：(1) 開発ビルドで fanotify（または strace）を使ってアクセス一覧を採取、(2) 初回アクセス順に優先度を付けた SORT-FILE を生成（起動に使うファイルほど高い優先度で先頭付近に置く想定）、(3) `mksquashfs -sort` で再パック、(4) blktrace で読込がシーケンシャルに近づいたか確認、(5) [起動時間の測定](../verification/open-questions.md)と比較します。`-sort` は優先度の高いものが先に書かれます（sort.c に基づく一次情報）。実イメージ上の物理配置と SD の読込改善は未測定です。

2026-10-25 に、手順案の (1) にあたる観測を QEMU で行いました。fanotify と blktrace の代わりに、QEMU の SD の trace（`sdcard_read_block`）を使っています。起動で読む rootfs は 16.5 % で、data block を全部読むファイルは 13 個でした（[記録](../../experiments/2026-10-25-qemu-boot-read-order.md)）。(2) 以降は実施していません。

#### (c) EROFS との比較(一次)
| 観点 | EROFS | SquashFS | 出典URL |
|---|---|---|---|
| 既定圧縮 | **圧縮する場合は LZ4 が既定の性格（FAQ）。ただし mkfs.erofs は `-z` を指定しないと圧縮しません（man）。FAQ の「既定 LZ4」は圧縮時のみです。** | GZIP | https://erofs.docs.kernel.org/en/latest/faq.html<br>https://git.kernel.org/pub/scm/linux/kernel/git/xiang/erofs-utils.git/tree/man/mkfs.erofs.1?h=v1.9.4<br>https://docs.kernel.org/filesystems/squashfs.html |
| 圧縮単位 | 物理クラスタの既定は 4 KiB（ブロック単位）です。1 MiB などの大クラスタはランダム読込を大きく悪化させうると警告されています。 | 128 KiB | https://erofs.docs.kernel.org/en/latest/faq.html<br>https://docs.kernel.org/filesystems/squashfs.html |
| 同条件比較の注意 | 比較時は圧縮アルゴリズム・クラスタ・レベル・`-Efragments` を揃えます。EROFS は既定でイメージが大きくなりうる（64 B inode、メタデータ非圧縮。ただし 6.17 以降は圧縮可能、ファイル重複排除なしのため `-Efragments` / `-Ededupe` を使用）。小さい圧縮単位（32 KiB 未満）では EROFS の方が小さくなることも多いとされます。 | — | https://erofs.docs.kernel.org/en/latest/faq.html<br>https://git.kernel.org/pub/scm/linux/kernel/git/xiang/erofs-utils.git/tree/man/mkfs.erofs.1?h=v1.9.4 |
| 公表ベンチ | Android 端末でアプリ起動が SquashFS 比で最大 22.9% 高速との報告です（条件固有の値です）。 | — | https://www.usenix.org/system/files/atc19-gao.pdf 【二次】 |
| RPi ツリーでの有効性 | RPi の `bcm2711_defconfig` は `EROFS_FS_ZIP_ZSTD=y` です。SquashFS も有効です。 | — | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L1671-L1685<br>https://docs.kernel.org/filesystems/squashfs.html 【一次】 |
| カーネル文書 | 4 KiB ブロック整列、LZ4 / LZMA / DEFLATE / ZSTD などをサポートします。Direct I/O や FSDAX は非圧縮 inode が対象です。 | — | https://docs.kernel.org/filesystems/erofs.html 【一次】 |

**EROFS の配置最適化（`--sort` など）:** erofs-utils v1.9.4 の man page では、`mkfs.erofs --sort` は tar 入力用で、ディレクトリ入力の配置最適化には使えません。圧縮方式は `-z` で指定(`-zlz4hc` など)します。`-C` は物理クラスタの最大サイズ、`--MZ` はメタデータ/ディレクトリデータを別領域にまとめて高レイテンシ記憶装置向けにします。`-m#[:alg]` はメタデータ圧縮(Linux 6.17+)の指定です。**EROFS には SquashFS の `-sort` に相当する配置指定の手段は未確認です。** EROFS の「4 KiB クラスタ + LZ4」が SD の低レイテンシ・ランダム読みに有利かもしれませんが、CM0 + SD での実測はありません（推測）。https://git.kernel.org/pub/scm/linux/kernel/git/xiang/erofs-utils.git/tree/man/mkfs.erofs.1?h=v1.9.4

【推測・未測定】読み取り専用 rootfs は、まず SquashFS（zstd または lz4、ブロック 128K〜256K）と EROFS（lz4、4 KiB）の 2 構成を実機で比較し、終点時間・SD 読込量・RAM 使用量を測ります。どちらが適するかは未確認です。

#### (d) overlayfs
- overlayfs の公式文書では、upper / work には書き込み可能なファイルシステムが必要とされています。RO rootfs と tmpfs upper を組み合わせる場合、書き込みは RAM に置かれます。電断耐性の詳細は未確認で、使用するカーネルの仕様と実機試験で確認が必要です。https://docs.kernel.org/filesystems/overlayfs.html 【一次】
- ext4 の `data=ordered`(既定)/`commit=` 等の公式説明:https://docs.kernel.org/admin-guide/ext4.html。【一次】
