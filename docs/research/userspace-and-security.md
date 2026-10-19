# ユーザー空間・SSH/VPN 調査

## 16. ユーザー空間の除去・遅延起動・init 選択

### 16.1 BusyBox 最小化と実使用の洗い出し
| 項目 | 事実 | 出典URL | 確認度 |
|---|---|---|---|
| 静的リンク BusyBox | FAQ に「静的ビルドは `LDFLAGS=--static`」と記載。静的リンクのコスト/利点(共有ライブラリ読込の省略)は FAQ の「relocatable code, PIC, and static linking」節にある | https://busybox.net/FAQ.html | 一次 |
| 最小アプレット選定 | `make menuconfig` でアプレット単位に選択できます（BusyBox の標準手順）。**CM0 向けの最小セットは未作成**です。実使用の洗い出しは `strace -f -e trace=execve,openat` などで記録し、使われたコマンドだけ残す方法が考えられます（手順案・推測）。 | https://busybox.net/FAQ.html<br>https://man7.org/linux/man-pages/man1/strace.1.html | 一次（ツール） / 推測（手順） |
| 依存確認 | `ldd` はターゲット実行になる場合があるため、クロス環境では `readelf -d`（NEEDED）で確認する方が安全との情報があります。根拠となる一次資料は未確認です。 | — | 推測 |
| fork 削減 | シェルスクリプトの外部コマンド呼び出し(fork+exec)を減らす、BusyBox の `NOFORK/NOEXEC`(ash の組込み実行)機能など。**BusyBox の該当設定の一次確認は未実施** | — | 未確認 |

### 16.2 init の選択:全機能維持(LCD/キーボード/音声/IMU/RTC/電池/Wi-Fi/Ethernet/IR/カメラ)で何が使えるか

事実(一次)と見立て(推測)を分けます。

| 論点 | 事実(出典) | 判断への含意(見立て=推測) |
|---|---|---|
| M5 の LCD / キーボード設定は **udev 前提** | M5 の公開 udev ルールは `ENV{ID_PATH}`（udev の path_id）でデバイスを特定し、`/dev/dri/cardputer-zero-internal`、`/dev/fb_lcd`、`/dev/input/cardputer-zero-internal` の symlink と seat タグを作ります。LED ルールは `RUN+="/bin/chgrp gpio ..."` を使います。https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/st7789v-1.0/99-cardputer-zero-lcd.rules<br>https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/tca8418-1.0/99-cardputer-zero-keyboard.rules<br>https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/60-cardputerzero-leds.rules | BusyBox mdev が ID_PATH を同じ形式で提供するかは未確認です。udev 形式のルールをそのまま使えるかも未確認です。BusyBox init / 自作 init を選ぶ場合、(a) eudev / systemd-udevd を単体で入れる、(b) 固定パス（例：`/dev/input/event0`）を前提にアプリを書く、のいずれかが案です（推測）。 |
| M5 の fb 表示サービスが **systemd unit** | `fb_load.service` は `After=systemd-udev-trigger.service systemd-udevd.service systemd-modules-load.service`、`WantedBy=sysinit.target` を指定します。https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/st7789v-1.0/fb_load.service | systemd 以外では同等のスクリプト化が必要です。スプラッシュを使わない要件では、fb_load 自体が不要となる可能性があります（推測）。 |
| LCD パネルの設定は **ファームウェア .bin** | `panel-mipi-dbi.c` は `<compatible>.bin` を `request_firmware` で取得します。https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/gpu/drm/tiny/panel-mipi-dbi.c#L220-L232 | rootfs が見える前に probe すると失敗または待機する可能性があります。built-in 化する場合は firmware のビルド埋め込み（`EXTRA_FIRMWARE`）か initramfs が必要です（構成が増えるため推測）。 |
| モジュールの自動ロード | M5 のモジュールソースには `MODULE_DEVICE_TABLE(of/i2c)` があり、modalias による自動ロードに利用できます。自動ロードには udev / `mdev -s` / `modprobe` 呼び出しが必要です。https://github.com/m5stack/m5stack-linux-dtoverlays/tree/75518549a2640486f5d13ea72ca4935b198d7c20/modules | systemd なら systemd-udevd + modules-load、BusyBox なら `modprobe` を明示列挙する自作スクリプトが案です（推測）。 |
| IMU / カメラ / 音声の上位ソフト | IMU は IIO、音声は ALSA（ASoC）、カメラは media / libcamera、IR は rc-core です。udev / systemd が必須との記述は未確認で、`libcamera` など上位ソフトも未調査です。https://docs.kernel.org/driver-api/iio/index.html<br>https://www.alsa-project.org/wiki/ASoC<br>https://docs.kernel.org/userspace-api/media/index.html<br>https://libcamera.org/docs.html<br>https://docs.kernel.org/driver-api/rc-core.html | 全機能維持には「ドライバが動く」ことと「上位ライブラリが動く」ことの 2 段階が必要です。後者は未調査です。 |
| Wi-Fi / Ethernet | `wpa_supplicant` / `dhcpcd` / `udhcpc` などを使う案があります。BusyBox の `udhcpc` の有無は未確認です。https://raw.githubusercontent.com/buildroot/buildroot/2026.08/package/wpa_supplicant/Config.in<br>https://raw.githubusercontent.com/buildroot/buildroot/2026.08/package/dhcpcd/Config.in<br>https://busybox.net/downloads/BusyBox.html | systemd-networkd なしでも構成可能と考えられます（推測）。 |
| 電池 / 電源 | BQ27220 は power_supply sysfs を使います。電源断処理は `handle_sysrq('u')` の後、バックライト輝度を 0 にし、disabled GPIO をアサートします。SysRq `i` / `s` と `kernel_power_off()` はコメントアウトされています。https://docs.kernel.org/power/power_supply_class.html<br>https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/power/supply/bq27xxx_battery.c<br>https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/powerfail_suo.c#L472-L510 | userspace daemon が必須かは未確認です。 |

**init 3 方式の比較（推測。起動時間はすべて未測定）**

| 観点 | systemd(最小化) | BusyBox init(+mdev または eudev) | 自作 init(静的 PID 1) |
|---|---|---|---|
| M5 の udev/unit 前提との整合 | **高**(そのまま流用可) | 中(udev ルール移植 or eudev 併用) | 低(全て自作) |
| 全機能維持の実装コスト | 低 | 中 | 高 |
| 並列起動 | 標準(依存解析・socket activation・timer) | `::once`/バックグラウンド `&`で手動 | 完全に自由(fork 後 wait しない等) |
| 静的リンク・小ささ | 小さくはない(バイナリ+依存多) | 小さい | 最小 |
| 失敗時の挙動 | 診断が強い(journal, analyze) | 弱い | 自前 |
| 終点(プロンプト+キー)までの最短化余地 | 中(unit を削り、`systemd-analyze critical-chain` で詰める) | 高 | 最高(ただし作り込み) |

- systemd の起動可視化・並列化・活性化機能:`systemd-analyze blame/critical-chain/plot`(https://man7.org/linux/man-pages/man1/systemd-analyze.1.html)、socket activation(https://man7.org/linux/man-pages/man5/systemd.socket.5.html)、`sd_notify`(https://man7.org/linux/man-pages/man3/sd_notify.3.html)、`Type=` 等(https://man7.org/linux/man-pages/man5/systemd.service.5.html)。【一次】
- 【推測・初期案】初期ユーザー空間は BusyBox init + mdev + glibc とし、M5 の udev ルールを mdev 向けに移植できるか試します。M5 のルールは少数のため移植候補になりますが、mdev が `ID_PATH` を同じ形式で提供するかは未確認です。必要な機能を再現できない場合は systemd 最小化または eudev との比較に戻り、musl は必要に応じて比較します。systemd の起動オーバーヘッドは A53 / RAM 512 MB で数百 ms〜1 秒という推測がありますが、実測値はありません。

### 16.3 systemd の起動短縮手段(一次の範囲)
- critical-chain で終点ユニットに至る最長経路を可視化し、そこにないものは `WantedBy` を変えて後段化できる(systemd-analyze man)。【一次】
- socket activation：`.socket` ユニットで待受を先に作り、サービス本体を初回接続時に起動します（Dropbear / OpenSSH サーバーやネットワーク系サービスの遅延に使えます）。https://man7.org/linux/man-pages/man5/systemd.socket.5.html 【一次（機能） / CM0 での効果は推測】
- timer で終点後に重い処理を遅延できます（`OnBootSec=`）。本文は未確認です。https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html 【未確認】
- `systemd-analyze blame` の値は並列起動のため起動時間への寄与と一致しません。また `Type=simple` のサービスは即時起動扱いで blame に表示されず、キュー待ち時間も含まれません。【一次】https://man7.org/linux/man-pages/man1/systemd-analyze.1.html

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

【推測】手順案：(1) 開発ビルドで fanotify（または strace）を使ってアクセス一覧を採取、(2) 初回アクセス順に優先度を付けた SORT-FILE を生成（起動に使うファイルほど高い優先度で先頭付近に置く想定）、(3) `mksquashfs -sort` で再パック、(4) blktrace で読込がシーケンシャルに近づいたか確認、(5) [起動時間の測定](measurement-and-planning.md)と比較します。`-sort` は優先度の高いものが先に書かれます（sort.c に基づく一次情報）。実イメージ上の物理配置と SD の読込改善は未測定です。

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

## 17. libc・アロケータ

確認度は各項目に示す公開出典に基づきます。数値は測定条件が異なるため合成しません。

### 17.1 版と対応（Buildroot 2026.08、タグ 813cbac、2026-09-04T15:31Z = 2026-09-05 00:31 JST） https://github.com/buildroot/buildroot/tree/2026.08
- BusyBox 1.38.0、binutils 既定 2.45.1（選択肢 2.44 / 2.45.1 / 2.46.1）、glibc 2.44-36-g2d5421f（git 固定）、musl 1.2.6（2026-03-20 公開）、uClibc-ng 1.0.59（2026-08-08 公開）、mbedTLS 3.6.6、OpenSSH 10.5p1、systemd 258.7、RAUC 1.15.2、SWUpdate 2026.05.1 です。Devin が 2026-10-18 に公開資料で確認しました。
  - https://raw.githubusercontent.com/buildroot/buildroot/2026.08/package/busybox/busybox.mk
  - https://raw.githubusercontent.com/buildroot/buildroot/2026.08/package/binutils/Config.in.host
  - https://raw.githubusercontent.com/buildroot/buildroot/2026.08/package/glibc/glibc.mk
  - https://raw.githubusercontent.com/buildroot/buildroot/2026.08/package/musl/musl.mk
  - https://raw.githubusercontent.com/buildroot/buildroot/2026.08/package/uclibc/uclibc.mk
  - https://raw.githubusercontent.com/buildroot/buildroot/2026.08/package/mbedtls/mbedtls.mk
  - https://raw.githubusercontent.com/buildroot/buildroot/2026.08/package/openssh/openssh.mk
  - https://raw.githubusercontent.com/buildroot/buildroot/2026.08/package/systemd/systemd.mk
  - https://raw.githubusercontent.com/buildroot/buildroot/2026.08/package/rauc/rauc.mk
  - https://raw.githubusercontent.com/buildroot/buildroot/2026.08/package/swupdate/swupdate.mk
  - https://musl.libc.org/releases.html
  - https://uclibc-ng.org/
- Buildroot の C ライブラリ選択肢は uClibc-ng / glibc / musl(既定 glibc)。aarch64 は 3 つとも対応。Newlib・picolibc・llvm-libc の選択肢は無い。https://github.com/buildroot/buildroot/blob/2026.08/toolchain/toolchain-buildroot/Config.in 【一次】
- Yocto Wrynose 6.0(LTS、2030-04 まで):glibc 2.43+git / musl 1.2.6+git。TCLIBC の docs は glibc / musl / newlib / baremetal。uClibc-ng は選択肢に無い。https://docs.yoctoproject.org/migration-guides/release-notes-6.0.html 、https://docs.yoctoproject.org/ref-manual/variables.html 【一次】

### 17.2 比較表
| 観点 | glibc | musl | uClibc-ng | Newlib / picolibc / llvm-libc | 出典・確認度 |
|---|---|---|---|---|---|
| ライセンス | LGPL-2.1+ | MIT | LGPL-2.1+ | BSD 系 / BSD 系 / Apache-2.0 w/ LLVM Exception | 【未確認】各プロジェクトのライセンスファイルで再確認が必要です。https://sourceware.org/git/?p=glibc.git;a=blob;f=COPYING.LIB;hb=HEAD<br>https://git.musl-libc.org/cgit/musl/tree/COPYRIGHT<br>https://github.com/wbx-github/uclibc-ng/blob/master/COPYING.LIB<br>https://sourceware.org/git/?p=newlib-cygwin.git;a=summary<br>https://github.com/picolibc/picolibc<br>https://github.com/llvm/llvm-project/tree/main/libc |
| aarch64 Linux | 可 | 可 | 可 | Newlib は `newlib/libc/sys` に Linux がないとの情報がありますが、ディレクトリの有無は未確認です（sourceware のページを取得できませんでした）。picolibc の Linux hosted は試験用との記載があります。llvm-libc は「重要関数が不足」と公式 docs が警告しています。 | https://github.com/buildroot/buildroot/blob/2026.08/toolchain/toolchain-buildroot/Config.in<br>https://sourceware.org/git/?p=newlib-cygwin.git;a=tree;f=newlib/libc/sys;hb=HEAD（取得できず）<br>https://github.com/picolibc/picolibc<br>https://libc.llvm.org/full_host_build.html（llvm-libc の記述。Linux 非対応とは断定しません）<br>【一部未確認】 |
| systemd | **Buildroot の systemd は glibc のみ**（`depends on BR2_TOOLCHAIN_USES_GLIBC`）。upstream の musl 対応は v259（2025-12-17）で「不完全・実験的」、継続サポート非約束です。v260では glibc >= 2.34 への引上げが予告されています。 | NSS 系（nss-systemd など）・`DynamicUser=` などが使えないとの情報がありますが、musl との組合せでの確認は未実施です。【未確認】 | — | — | https://github.com/buildroot/buildroot/blob/2026.08/package/systemd/Config.in<br>https://github.com/systemd/systemd/releases/tag/v259<br>https://github.com/systemd/systemd/pull/38825 【一次 / 一部未確認】 |
| RAUC / SWUpdate | RAUC 1.15.2 の Config.in は libc を限定しません（glib2・OpenSSL などが必要です）。SWUpdate は静的リンクできません（`!BR2_STATIC_LIBS`）。 | musl・uClibc-ng での実機動作は未確認 | 同左 | — | https://github.com/buildroot/buildroot/blob/2026.08/package/rauc/Config.in<br>https://github.com/buildroot/buildroot/blob/2026.08/package/swupdate/Config.in 【一次（Config.in） / 動作未確認】 |
| セキュリティ | `_FORTIFY_SOURCE` は glibc ツールチェーンが必要です（Buildroot Config.in）。SSP は常時利用可能です。 | **musl 本体に FORTIFY はないとの情報がありますが未確認です。** Alpine は fortify-headers 3.0.1 を使います。既知脆弱性として CVE-2026-40200（32 bit の qsort。aarch64 は対象外と読めます）、CVE-2026-6042（iconv GB18030 DoS）があり、musl 1.2.6 までの範囲が記載されています。 | `UCLIBC_BUILD_PIE` は aarch64 が依存条件になく、SSP は既定で無効、FORTIFY 設定は見つかりません。 | — | https://github.com/buildroot/buildroot/blob/2026.08/Config.in<br>https://raw.githubusercontent.com/wbx-github/uclibc-ng/master/extra/Configs/Config.in<br>https://musl.libc.org/releases.html<br>https://wiki.musl-libc.org/functional-differences-from-glibc.html<br>https://gitlab.alpinelinux.org/alpine/fortify-headers<br>https://nvd.nist.gov/vuln/detail/CVE-2026-40200<br>https://nvd.nist.gov/vuln/detail/CVE-2026-6042 【一次 / FORTIFY は未確認】 |
| 機能差 | lazy binding あり | lazy binding なし(意図的)、dlclose は no-op、locale/iconv 限定 | — | — | https://wiki.musl-libc.org/functional-differences-from-glibc.html 一次 |
| サイズ(配布元の索引。**ミニマム構成の値ではない**) | Debian trixie arm64 libc6 2.41-12+deb13u4:パッケージ 2,483,572 B / Installed-Size 23,769 KB(gconv・locale 含む) | Alpine aarch64 musl 1.2.6-r2:パッケージ 417,710 B / 展開後 723,480 B | — | — | https://deb.debian.org/debian/dists/trixie/main/binary-arm64/Packages.xz / https://dl-cdn.alpinelinux.org/alpine/latest-stable/main/aarch64/APKINDEX.tar.gz 一次(索引)。**両者の比を計算しない**(版・ビルドが違う) |

### 17.3 起動・exec コストの公表値(**条件併記・合成禁止**)
| 値 | 条件 | 出典 | 確認度 |
|---|---|---|---|
| 自己 exec(静的)musl 234µs / uClibc 245µs / dietlibc 272µs / glibc 457µs。動的は 446/590/675/864µs | musl 1.1.5、uClibc 0.9.33.2、dietlibc 0.32、glibc 2.19、**Intel Atom N280(32bit x86)**、著者注記「近似値」 | https://www.etalabs.net/compare_libcs.html | 二次(musl 作者のページ) |
| fork+exec:動的 131µs/静的 31µs(Core i5-6600K)、動的 1762µs/静的 507µs(Celeron N3060。**ChromeOS の Crostini VM 上での測定** で、実機と同列には比べられない。gist 本文で確認) | **x86_64、libc 比較ではなく静的/動的の比較**(musl-gcc でビルド) | https://gist.github.com/hadrianw/ad07a76f338f09565703ae6ea35993c8 | 二次 |
| Zero 2 W、Buildroot 2024.02.1、**フル glibc**、カーネル大幅削減・非圧縮・initramfs なしで電源投入からユーザー空間まで約 3.5 秒（カーネル実行約 400 ms） | 個人ブログ（電源投入から GPIO トグルまで。KASLR・Spectre 緩和・sound / USB などを無効化） | https://kittenlabs.de/blog/2024/09/01/extreme-pi-boot-optimization/ | 二次 |
- **aarch64 / Cortex-A53 / 現行版（musl 1.2.6、glibc 2.44）での公表比較は確認できていません（未確認。否定ではありません）。対象 SoC と libc の版を明記した公開測定で確認する必要があります。**

### 17.4 アロケータ(jemalloc / mimalloc など)
- mimalloc README は、自社ベンチで他の主要アロケータを上回ると主張する一方、ベンチには合成的なものが含まれ、結果を注意して解釈するよう注記しています。CM0・起動時間の数値はありません。jemalloc は未調査です。https://github.com/microsoft/mimalloc/blob/main/readme.md 【一次（README の記載）】
- 【推測】512 MB・CLI 構成では、アロケータ差し替えの効果は起動時間より RSS / 断片化に出る可能性があり、優先度は低いと考えられます。

### 17.5 設計上の見立て（推測・未測定）
- **systemd を使うなら glibc が必要**です（Buildroot の制約）。**BusyBox init + 自作ミニ init なら musl の静的リンクが有利**と考えられます（MIT・小さいため）。uClibc-ng は新規設計での優先度が低いと考えられます。Newlib / picolibc / llvm-libc は Buildroot の選択肢にありません。Newlib の Linux 対応は未確認です。
- 初期案は BusyBox init + mdev + glibc です。M5 の udev / systemd unit を変更せず全機能を維持する必要がある場合は、glibc + systemd の最小化を代替案として比較します。musl + BusyBox は静的リンクの利点がありますが、udev ルールの移植と NSS の制約を評価する必要があります。
- 起動時間への libc 差は、静的 BusyBox などで exec 回数が少なければ全体のうち数十 ms 未満と推測されます（未実測）。支配項は firmware とカーネル側と考えられます（[KittenLabs の測定例](https://kittenlabs.de/blog/2024/09/01/extreme-pi-boot-optimization/)）。CM0 実機で `perf trace` / bootchart 相当を取る必要があります。
- OpenSSH は glibc なら libxcrypt を選びます（Buildroot Config.in）。Dropbear は静的ビルドに向きます。https://github.com/buildroot/buildroot/blob/2026.08/package/openssh/Config.in 【一次】

## 21. SSH・VPN、暗号拡張、鍵保管と A/B OTA

### Firmware と再配布条件

- 【未確認】CYW43439 の firmware は `firmware-nonfree` / `brcmfmac_sdio-firmware-rpi` などの配布経路と関連し、再配布条件の確認が必要です。採用する blob とそのライセンスを特定してから同梱します。https://github.com/RPi-Distro/firmware-nonfree<br>https://github.com/raspberrypi/firmware
- 【未確認】M5 LCD 初期化用 binary、BMI270 初期化 firmware、keymap のライセンスは公開ソース内で確認できていません。公開配布前に M5Stack へ利用・再配布条件を確認します。https://github.com/m5stack/m5stack-linux-dtoverlays/tree/75518549a2640486f5d13ea72ca4935b198d7c20/modules/st7789v-1.0<br>https://github.com/m5stack/m5stack-linux-dtoverlays/tree/75518549a2640486f5d13ea72ca4935b198d7c20/modules/imu-1.0<br>https://github.com/m5stack/m5stack-linux-dtoverlays/tree/75518549a2640486f5d13ea72ca4935b198d7c20/modules/tca8418-1.0

### 21.1 BCM2837 の ARMv8 Crypto Extensions
| 事実 | 出典URL | 確認度 |
|---|---|---|
| Cortex-A53 の Cryptography Extension はオプションで、標準製品に含まれず追加ライセンスで供給されると Arm DDI 0501F に記載されています（Cortex-A53 一般の説明で、BCM2837 が実装しているかは別です）。 | https://documentation-service.arm.com/static/5e9077ee8259fe2368e2acf7?token= （Arm DDI 0501F）。https://documentation-service.arm.com/static/5e9077ee8259fe2368e2acf7 | 一次 |
| `ID_AA64ISAR0_EL1` の AES / SHA1 / SHA2 フィールドは、Cryptographic Extension を含まない実装では 0x0 です（Arm のレジスタ定義）。 | https://support.arm.com/documentation/101433/0102/Register-descriptions/AArch64-system-registers/ID-AA64ISAR0-EL1--AArch64-Instruction-Set-Attribute-Register-0--EL1 | 未確認（HTTP 403 で取得できず） |
| BCM2837 は JTAG で当該レジスタを読み、AES / SHA1 / SHA2 = 0、CRC32 = 1 だったとの個人報告があります。BCM2837B0（Pi 3B+）の `/proc/cpuinfo` Features に `aes / pmull / sha1 / sha2` がなく、`crc32` があるとの報告もあります。 | https://forums.raspberrypi.com/viewtopic.php?t=207888<br>https://forums.raspberrypi.com/viewtopic.php?t=263234 | 二次（個人報告。HTTP 403 で取得できず。Broadcom / RPi の一次仕様ページも未確認） |
| sbc-bench:Broadcom の 64bit 対応 RPi(BCM2712 以外)は crypto 加速が無いと記載 | https://github.com/ThomasKaiser/sbc-bench/blob/master/results/ARMv8-Crypto-Extensions.md | 二次 |
| 帰結:CM0（BCM2837）は AES / SHA / PMULL 命令を持たないと推測されますが、メーカー仕様の一次資料では確認できていません。実機の `/proc/cpuinfo` の Features で確認できます（実機未入手）。 | — | 二次 + 推測（実機で未確認） |
| カーネルは CE 版と NEON 版・汎用版を持つ(`arch/arm64/crypto/aes-ce-*`、`aes-neon*`、`lib/crypto/arm64/chacha-neon-core.S`、`sha256-ce.S` 等)。ChaCha は `CRYPTO_LIB_CHACHA_ARCH` が `ARM64 && KERNEL_MODE_NEON` で既定有効 | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/lib/crypto/Kconfig#L46-L52 / https://github.com/raspberrypi/linux/tree/234188315037848e5b07d65b85d38edc64095caa/lib/crypto/arm64 | 一次 |

### 21.2 WireGuard の速度への影響
| 事実 | 出典URL | 確認度 |
|---|---|---|
| WireGuard カーネルモジュールは `CRYPTO_LIB_CHACHA20POLY1305` と `CRYPTO_LIB_CURVE25519` を使う(AES を使わない) | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/net/Kconfig#L75-L83 | 一次 |
| 公式のパフォーマンスページのベンチは **Intel Core i7-3820QM / i7-5200U、Linux 4.6.1、GbE** の古い測定で、公式自身が「old, crusty, and not super well conducted」と注記。**ARM/CM0 の数値は無い** | https://www.wireguard.com/performance/ | 一次 |
| 帰結:WireGuard は AES を使わず ChaCha20-Poly1305 を使うため、Crypto Extensions がなくても NEON 実装を利用できます（カーネルに `chacha-neon` があります）。OpenSSH は既定暗号に ChaCha20-Poly1305 を含み、Dropbear は ChaCha20-Poly1305 を有効、GCM を無効にしています。OpenVPN は `--data-ciphers` の既定順で AES-GCM が先なので、CE のない CM0 では ChaCha20-Poly1305 を先頭にする設定が必要と推測されます。CM0 での実スループットは公開値がなく、実機未測定です。Wi-Fi は 2.4 GHz 802.11n、Ethernet は 10 / 100 Mbit/s（USB 2.0）なので、リンク側が先に上限になる可能性があります（推測）。 | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/lib/crypto/arm64<br>https://raw.githubusercontent.com/openssh/openssh-portable/V_10_5_P1/myproposal.h<br>https://raw.githubusercontent.com/mkj/dropbear/DROPBEAR_2026.94/src/default_options.h<br>https://openvpn.net/community-docs/community-articles/openvpn-2-7-manual.html<br>https://docs.m5stack.com/en/CardputerZero | 推測 |
| Dropbear のオプションには、ChaCha20-Poly1305 は AES 命令のない CPU で AES256 より概して速いとのコメントがあります。 | https://github.com/mkj/dropbear/blob/DROPBEAR_2026.94/src/default_options.h | 一次（コメント） |

### 21.3 SSH と VPN の選択肢
| 項目 | 事実 | 出典URL | 見立て(推測) |
|---|---|---|---|
| Dropbear | 小型の SSH サーバ/クライアント。`PROGRAMS=dropbear` でサーバのみビルド、`localoptions.h` でアルゴリズム/認証/転送を無効化して小さくできる。静的ビルドでは zlib を無効にするとサイズが減る | https://github.com/mkj/dropbear/blob/master/README.md / https://github.com/mkj/dropbear/blob/master/SMALL.md | 小さく BusyBox 系と相性が良い。socket activation(systemd)で常駐を避ける案 |
| OpenSSH（sshd） | 標準的です。既定の暗号・KEX は `myproposal.h` で確認できます。https://man.openbsd.org/sshd.8 は接続できず取得できていません。 | https://raw.githubusercontent.com/openssh/openssh-portable/V_10_5_P1/myproposal.h | サイズが大きく依存も多い（OpenSSL / libcrypto など）一方、systemd 構成なら導入は簡単です。 |
| WireGuard | カーネル内蔵(`CONFIG_WIREGUARD`)+ `wg` ツール。導入手順は公式 https://www.wireguard.com/install/ と https://www.wireguard.com/quickstart/ | https://www.wireguard.com/quickstart/ | 起動時間の影響はモジュールロード時のみ。**終点の後に起動** で良い |
| OpenVPN | ユーザー空間デーモン + OpenSSL です。Buildroot 2026.08 は 2.7.6 です。公式マニュアルは 2.7 で、旧 2.6 URL は同コミュニティ文書へ移転しました。https://raw.githubusercontent.com/buildroot/buildroot/2026.08/package/openvpn/openvpn.mk | https://openvpn.net/community-docs/community-articles/openvpn-2-7-manual.html<br>https://openvpn.net/community-docs/community-articles/openvpn-2-6-manual.html（旧URL） | **暗号は `--data-ciphers` の設定が必要です**（既定は AES-256-GCM : AES-128-GCM : CHACHA20-POLY1305。ChaCha は利用可能な場合のみ）。CM0 では AES-GCM がソフト実装で遅いと推測されるため、ChaCha20-Poly1305 を先頭にする案です。 |

### 21.4 鍵保管と A/B OTA
【推測・設計案（一次情報で検証した設計ではありません）】
- **ホスト鍵(SSH)・WireGuard 秘密鍵・認証情報は A/B のどちらの rootfs にも入れず、別の永続 RW パーティション(小さい ext4)に置く**。A/B 切替・ロールバックで鍵が変わると、クライアント側の known_hosts 警告や VPN 切断が起こるため。
- 鍵の生成は**初回起動時(個体ごと)** に行う。イメージに共通鍵を焼くと全個体が同じ鍵になる(典型的な落とし穴)。
- 電断耐性：鍵ファイルは「tmp に書く → fsync → rename」で更新する案です（[電源遮断耐性の調査](power-and-updates.md)）。RW パーティションが壊れても機器は起動できるよう分離し、破損時に鍵を再生成する運用を許容するか決める必要があります。
- 権限は `0600` とします。microSD は取り外せるため、暗号化しなければ鍵を読み取れる可能性があります（個体の物理的脅威モデルは未検討）。dm-crypt は CM0 に AES 命令がなく遅いと推測されます。ChaCha20 系の Adiantum は RPi defconfig で `CRYPTO_ADIANTUM=m` ですが、CE 非搭載機向けとの説明は未確認です。https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig 【一次（設定） / 用途は未確認】
- OTA ペイロードの署名検証は RAUC / SWUpdate の導入候補に含まれます（[電源・更新方式の調査](power-and-updates.md)）。**署名鍵・検証鍵の保管とローテーション**は未調査です。
- Dropbear は `-r` でホスト鍵ファイルのパスを指定できるとの記述がありますが、現時点では未確認です。確認先は [Dropbear README](https://github.com/mkj/dropbear/blob/main/README.md) です。OpenSSH の `HostKey` も man を取得できておらず未確認です。

### 21.5 ポスト量子（PQ）鍵交換と SSH / VPN の既定暗号

Devin が 2026-10-18 JST に各実装の既定値を定義するファイルを公開資料で確認しました。Buildroot 2026.08（コミット d5180309）の同梱版は、各 `package/*/*.mk` に記載された版です。https://github.com/buildroot/buildroot/commit/d5180309 **CM0 での実行時間・スループットは公表値が見つからず、実機未測定です。**

| 実装(版:何の版か) | 既定の暗号・鍵交換(定義ファイル) | PQ ハイブリッド | コスト(出典にある範囲) | 出典 |
|---|---|---|---|---|
| **OpenSSH 10.5p1**（Buildroot 2026.08 同梱版。ポータブル版のタグ V_10_5_P1） | 暗号の既定順（`myproposal.h` の `KEX_SERVER_ENCRYPT`）は **`chacha20-poly1305@openssh.com`**、`aes128-gcm@openssh.com`、`aes256-gcm@openssh.com`、aes128 / 192 / 256-ctr です。MAC は ETM 系が先頭です。鍵交換の既定順は **`mlkem768x25519-sha256`**、`sntrup761x25519-sha512`、`sntrup761x25519-sha512@openssh.com`、`curve25519-sha256` などです（クライアントは DH group exchange なども追加）。 | **あり・既定で先頭**（ML-KEM-768 + X25519）。OpenSSH 10.0 のリリースノート（2025-04-09）は `mlkem768x25519-sha256` が既定の鍵交換方式になったと記載します。 | リリースノートは「前の既定よりかなり高速」と記載しますが、比較対象は明記されていません。CM0 での時間は不明です。ChaCha が先頭のため、AES 命令がない構成でも不利になりにくいと推測されます。 | https://raw.githubusercontent.com/openssh/openssh-portable/V_10_5_P1/myproposal.h<br>https://www.openssh.org/txt/release-10.0<br>https://raw.githubusercontent.com/buildroot/buildroot/2026.08/package/openssh/openssh.mk |
| **Dropbear 2026.94**(Buildroot 2026.08 同梱版。CHANGES の日付 2026-07-23) | `default_options.h`:`DROPBEAR_CHACHA20POLY1305 1`、`DROPBEAR_AES128/256 1`、**`DROPBEAR_ENABLE_GCM_MODE 0`(AES-GCM は既定で無効)**。鍵交換:`DROPBEAR_CURVE25519 1`、`DROPBEAR_ECDH 1` | **あり・既定で有効**:`DROPBEAR_SNTRUP761 1` と `DROPBEAR_MLKEM768 1`(ともにハイブリッド) | 同ファイルのコメント:「sntrup uses ~9kB code size, mlkem uses ~34kB code size (32-bit armv7)」「Both are fast」。GCM は「slower than CTR on CPU w/o dedicated AES/GHASH instructions」とコメント(CM0 は該当見込み)。CHANGES:「These do increase code size, at least sntrup761 is recommended」 | https://raw.githubusercontent.com/mkj/dropbear/DROPBEAR_2026.94/src/default_options.h / https://raw.githubusercontent.com/mkj/dropbear/DROPBEAR_2026.94/CHANGES / https://raw.githubusercontent.com/buildroot/buildroot/2026.08/package/dropbear/dropbear.mk |
| **OpenVPN 2.7.6**（Buildroot 2026.08 同梱版。マニュアルは 2.7） | **暗号は設定が必要です**。`--data-ciphers` の既定は AES-256-GCM : AES-128-GCM : CHACHA20-POLY1305（ChaCha20-Poly1305 が使える場合。なければ前の 2 つ）です。`--cipher` は 2.6.0 以降 TLS モードで無視されます。`--auth` の既定は SHA1（AEAD では無視）で、`--data-ciphers-fallback` は 2.3 以前の相手向けです。 | マニュアル上、既定の PQ 鍵交換はありません。実効既定は OpenSSL 版に依存します。`--tls-groups` の説明は OpenSSL 1.1 以降の既定リストに ML-KEM を含めませんが、OpenVPN 2.7.6 は `--tls-groups` を指定した場合だけグループを設定します。OpenSSL 3.6.4 の既定グループ一覧は `X25519MLKEM768` が先頭です。実際の接続で ML-KEM が使われるかは未確認です。 | AES-GCM が先頭のため、AES 命令のない CM0 では **`--data-ciphers CHACHA20-POLY1305:AES-256-GCM` のように ChaCha を先頭にする設定が必要**と推測されます。実測はありません。 | https://openvpn.net/community-docs/community-articles/openvpn-2-7-manual.html<br>https://raw.githubusercontent.com/buildroot/buildroot/2026.08/package/openvpn/openvpn.mk<br>https://github.com/OpenVPN/openvpn/blob/v2.7.6/src/openvpn/ssl.c#L552<br>https://github.com/openssl/openssl/blob/openssl-3.6.4/ssl/t1_lib.c#L209<br>https://github.com/buildroot/buildroot/blob/2026.08/package/libopenssl/libopenssl.mk |
| **WireGuard**（カーネル組込み。wireguard-tools 1.0.20260223、wireguard-linux-compat 1.0.20220627 は Buildroot 2026.08 の版） | 固定プリミティブは ChaCha20-Poly1305、Curve25519、BLAKE2s、HKDF です（暗号選択の設定はありません）。 | **標準ではありません。** 公式プロトコル説明では、追加の対称鍵暗号が必要な場合（例：耐量子性）に任意の事前共有鍵を使えるとしています。 | AES を使わず NEON 実装があります。事前共有鍵（PSK）は任意で、鍵配布は別途必要です。 | https://www.wireguard.com/protocol/<br>https://raw.githubusercontent.com/buildroot/buildroot/2026.08/package/wireguard-tools/wireguard-tools.mk<br>https://raw.githubusercontent.com/buildroot/buildroot/2026.08/package/wireguard-linux-compat/wireguard-linux-compat.mk |

**読み取れること(事実の範囲)**
- OpenSSH 10.5p1 と Dropbear 2026.94 は、Buildroot 2026.08 同梱版で設定なしでも PQ ハイブリッド鍵交換が有効です。OpenVPN 2.7.6 はマニュアル上の既定に PQ はありません。実効既定は OpenSSL 版に依存し、実接続で ML-KEM が使われるかは未確認です。WireGuard は PSK による追加層のみです。
- データ暗号では OpenSSH は ChaCha20-Poly1305 が先頭、Dropbear は ChaCha20-Poly1305 が有効で GCM は無効、OpenVPN は GCM が先頭（設定変更が必要）です。
- Dropbear の ML-KEM は約 34kB(armv7 の値)、sntrup は約 9kB の追加コード。ディスクと RAM が小さい構成では 34kB を見積もるが、**CM0(aarch64)での値や起動時間への影響は未測定**。

【推測・未測定】鍵交換は接続ごとに 1 回の計算なので、[起動完了条件](measurement-and-planning.md)の後に sshd / Dropbear を socket activation で起動すれば、起動時間への影響は小さいと見込まれます。実測では SSH 接続確立までの時間が重要です。CM0 の A53 での ML-KEM / X25519 の実測は、実機入手後に行う必要があります。PQ を使う場合のサーバー・クライアント双方の版要件（古いクライアントとの互換性）は未調査です。

【未確認】OpenSSH の ML-KEM が CM0 でどの程度時間を要するか（公開値なし）、OpenVPN で ML-KEM 系グループが実際に使われるか（OpenSSL 3.6.4 の既定は `X25519MLKEM768` が先頭ですが、OpenVPN 2.7.6 は `--tls-groups` 未指定ならグループを設定しません。ソース確認のみで実接続は未確認）、`--tls-groups` に指定できる値、Buildroot での OpenSSH の `libcrypto` 構成は未確認です。実機測定と対象版の公開ソースで確認が必要です。
