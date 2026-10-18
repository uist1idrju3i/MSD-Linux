# ユーザー空間・SSH/VPN 調査

## 16. ユーザー空間の除去・遅延起動・init 選択(提案 3)

> 11 章との対応: 11.1(rootfs)、11.3 D2・D3(11.5 に対応表)

### 16.1 BusyBox 最小化と実使用の洗い出し
| 項目 | 事実 | 出典URL | 確認度 |
|---|---|---|---|
| 静的リンク BusyBox | FAQ に「静的ビルドは `LDFLAGS=--static`」と記載。静的リンクのコスト/利点(共有ライブラリ読込の省略)は FAQ の「relocatable code, PIC, and static linking」節にある | https://busybox.net/FAQ.html | 一次 |
| 最小アプレット選定 | `make menuconfig` でアプレット単位に選択(BusyBox の標準手順)。**CM0 向けの最小セットは未作成**。実使用の洗い出しは `strace -f -e trace=execve,openat` 等でログ化→使われたコマンドのみ残す(手法の提案=推測) | https://busybox.net/FAQ.html / https://man7.org/linux/man-pages/man1/strace.1.html | 一次(ツール)/ 推測(手順) |
| 依存確認 | `ldd` はターゲット実行になる場合があるため、クロス環境では `readelf -d`(NEEDED)で確認するのが安全(一般知識。本調査で一次ページは取得していない) | — | 推測 |
| fork 削減 | シェルスクリプトの外部コマンド呼び出し(fork+exec)を減らす、BusyBox の `NOFORK/NOEXEC`(ash の組込み実行)機能など。**BusyBox の該当設定の一次確認は未実施** | — | 未確認 |

### 16.2 init の選択:全機能維持(LCD/キーボード/音声/IMU/RTC/電池/Wi-Fi/Ethernet/IR/カメラ)で何が使えるか

事実(一次)と見立て(推測)を分けます。

| 論点 | 事実(出典) | 判断への含意(見立て=推測) |
|---|---|---|
| M5 の LCD/キーボード設定は **udev 前提** | M5 repo の udev ルールは `ENV{ID_PATH}`(udev の path_id)でデバイスを特定し、`/dev/dri/cardputer-zero-internal`、`/dev/fb_lcd`、`/dev/input/cardputer-zero-internal` の symlink と seat タグを作る。LED は `RUN+="/bin/chgrp gpio ..."` を使う(https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/st7789v-1.0/99-cardputer-zero-lcd.rules / …/tca8418-1.0/99-cardputer-zero-keyboard.rules / …/CardputerZero/60-cardputerzero-leds.rules) | BusyBox mdev は ID_PATH を同じ形で提供しない(mdev の一次確認は今回していないが、**udev 形式のルールはそのままは使えない**可能性が高い)。BusyBox init/自作 init を選ぶ場合は、(a) eudev/systemd-udevd を単体で入れる、(b) 固定パス(`/dev/input/event0` 等)を前提にアプリを書く、のいずれかになる |
| M5 の fb 表示サービスが **systemd unit** | `fb_load.service`:`After=systemd-udev-trigger.service systemd-udevd.service systemd-modules-load.service`、`WantedBy=sysinit.target`(https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/st7789v-1.0/fb_load.service) | systemd 以外では同等のスクリプト化が必要。スプラッシュ不要(ユーザー要件)なので fb_load 自体は不要の可能性 |
| LCD パネルの設定は **ファームウェア .bin** | `panel-mipi-dbi-m.c` が `<compatible>.bin` を `request_firmware` で取得(L220-232) | rootfs が見える前に probe すると失敗/待ち。built-in 化する場合は firmware のビルド埋込(`EXTRA_FIRMWARE`)か initramfs が必要(後者は構成が増える。見立て) |
| モジュールの自動ロード | M5 モジュールは `MODULE_DEVICE_TABLE(of/i2c)` を持つ=modalias で自動ロード可能(modules/*.c)。自動ロードには udev/mdev -s/`modprobe` 呼び出しのいずれかが必要 | systemd なら systemd-udevd+modules-load。BusyBox なら `modprobe` を明示列挙する自作スクリプトが速く確実(見立て) |
| IMU/カメラ/音声の上位ソフト | IMU は IIO、音声は ALSA(ASoC)、カメラは media/libcamera、IR は rc-core。いずれも udev/systemd を**必須とする記述は見つけていない**が、`libcamera` 等の上位は未調査 | 全機能維持=「ドライバが動く」と「上位ライブラリが動く」の 2 段。**後者は未調査** |
| Wi-Fi/Ethernet | `wpa_supplicant`/`dhcpcd`/`udhcpc` など。BusyBox にも `udhcpc` あり(FAQ 範囲外・未確認) | systemd-networkd なしでも可(見立て) |
| 電池/電源 | BQ27220 は power_supply sysfs。`powerfail_suo` が実行するのは `handle_sysrq('u')`(L93)のみ。`'i'`(L74)・`'s'`(L83)・`kernel_power_off()`(L106)はコメントアウト(6.3 と同じ。一次)。userspace の daemon は必須ではない | — |

**init 3 方式の比較(作成者の見立て=推測。起動時間は全て未測定)**

| 観点 | systemd(最小化) | BusyBox init(+mdev または eudev) | 自作 init(静的 PID1) |
|---|---|---|---|
| M5 の udev/unit 前提との整合 | **高**(そのまま流用可) | 中(udev ルール移植 or eudev 併用) | 低(全て自作) |
| 全機能維持の実装コスト | 低 | 中 | 高 |
| 並列起動 | 標準(依存解析・socket activation・timer) | `::once`/バックグラウンド `&`で手動 | 完全に自由(fork 後 wait しない等) |
| 静的リンク・小ささ | 小さくはない(バイナリ+依存多) | 小さい | 最小 |
| 失敗時の挙動 | 診断が強い(journal, analyze) | 弱い | 自前 |
| 終点(プロンプト+キー)までの最短化余地 | 中(unit を削り、`systemd-analyze critical-chain` で詰める) | 高 | 最高(ただし作り込み) |

- systemd の起動可視化・並列化・活性化機能:`systemd-analyze blame/critical-chain/plot`(https://man7.org/linux/man-pages/man1/systemd-analyze.1.html)、socket activation(https://man7.org/linux/man-pages/man5/systemd.socket.5.html)、`sd_notify`(https://man7.org/linux/man-pages/man3/sd_notify.3.html)、`Type=` 等(https://man7.org/linux/man-pages/man5/systemd.service.5.html)。【一次】
- 【作成者の見立て】**全機能維持を最優先にするなら systemd を最小化(不要 unit を mask、journald volatile、networkd/resolved を外す)して出発し、15 章の測定で critical-chain の上位を詰める**。それでも終点が目標に届かない場合のみ BusyBox init+eudev へ。自作 init は最後の手段(コスト大)。この序列は実機測定前の推測で、systemd の起動オーバーヘッドが A53 で何 ms かは**未測定**。

### 16.3 systemd の起動短縮手段(一次の範囲)
- critical-chain で終点ユニットに至る最長経路を可視化し、そこにないものは `WantedBy` を変えて後段化できる(systemd-analyze man)。【一次】
- socket activation:`.socket` ユニットで待受を先に作り、サービス本体は初回接続時に起動(dropbear/sshd や ネットワーク系の遅延に使える。21 章)。【一次(機能)/ CM0 での効果は推測】
- timer で終点後に重い処理を遅延(`OnBootSec=`)。man は `systemd.timer`(今回本文は取得していない)=【未取得】。
- `systemd-analyze blame` の注意:並列起動のため blame の値は起動時間への寄与と一致しない。また `Type=simple` のサービスは即時起動扱いで blame に表示されない(測定不能)。キュー待ちの時間も含まれない。【一次】(man、V9A-004)

### 16.4 SquashFS+overlayfs と読込み順最適化(追加依頼分)

#### (a) mksquashfs のオプション(SQT 4.7.5/4.7.6 Documentation)
| 項目 | 事実 | 出典URL | 確認度 |
|---|---|---|---|
| 並び順指定 `-sort` | `-sort SORT-FILE`:「SORT-FILE の優先度に従ってファイルを並べる。1 行に 1 ファイル or ディレクトリと優先度、優先度は -32768〜32767、既定 0」 | https://github.com/plougher/squashfs-tools/blob/db038ef265ed00bb17aaf695a72f9b0c3489eb20/Documentation/manpages/mksquashfs.1#L179-L181 | 一次(man)。**v5:sort.c(@db038ef)で、`sort_files_and_write` は優先度 65535 から 0 へ降順に処理=優先度の高いファイルが先に書かれる(同一優先度は後から追加されたものが先)。通常ファイルのみが対象で、ディレクトリ指定は配下に優先度を継承**(13.4A) |
| ブロックサイズ | `-b`:既定 128KiB。4K〜1M を選択可。USAGE は「128K 超にすると圧縮率が上がり(特に XZ/ZSTD)I/O 性能も上がるはずだが、断片(fragment)が多く参照局所性が無い場合はレイテンシが増えうる。256K 以上を試すこと」と記載 | https://github.com/plougher/squashfs-tools/blob/db038ef265ed00bb17aaf695a72f9b0c3489eb20/Documentation/4.7.5/USAGE-MKSQUASHFS(L189, L219, L340-L352 付近) | 一次 |
| 圧縮方式 | GZIP(既定)/LZO/LZ4/XZ/ZSTD。USAGE:「LZO は GZIP より圧縮率が低いが展開が速い。XZ は圧縮率が良いが展開が遅い。LZ4 は LZO に近い。ZSTD は圧縮率と速度の両立を狙う」。カーネルが当該方式をビルドしている必要あり | 同 USAGE L283-L303 | 一次 |
| SquashFS カーネル側 | 圧縮は zlib/lz4/lzo/xz/zstd、ブロックは最大 1MiB(既定 128K)。ディレクトリはソート済みで索引あり | https://docs.kernel.org/filesystems/squashfs.html | 一次 |
| 圧縮なしイメージ | `-no-compression`(= `-noI -noD -noF -noX`)で無圧縮の SquashFS を作れる(SD 読込量は増えるが展開 CPU が不要になる。効果は**未測定=推測**) | USAGE L353-L356 付近 | 一次(機能)/ 推測(効果) |

#### (b) 起動時に読むファイルの記録方法
| 手法 | 事実 | 出典URL | 確認度 / 注意 |
|---|---|---|---|
| strace | `-e trace=openat,execve` 等でプロセスごとのファイル open を記録。ただし**読込順=開く順** であり、実際のブロック I/O 順ではない。ptrace のオーバーヘッドで起動順序が変わりうる(推測) | https://man7.org/linux/man-pages/man1/strace.1.html | 一次(機能)/ 推測(影響) |
| fanotify | ファイルシステム全体の open/access 等のイベントを監視できる API(man の fanotify_mark 節参照)。strace より影響が小さく、全プロセスを横断して「実際にアクセスされたファイル」を取れる。使うには CAP_SYS_ADMIN 相当(man の記載範囲) | https://man7.org/linux/man-pages/man7/fanotify.7.html | 一次(API)/ 推測(低影響) |
| blktrace | ブロック層の I/O(セクタ・サイズ・順序)を記録。**SquashFS 上のブロック読込順を直接観測** でき、配置最適化の効果検証に向く。開発用カーネルに `CONFIG_BLK_DEV_IO_TRACE` が必要(man 参照。CM0 向けビルドでの有効化は未確認) | https://man7.org/linux/man-pages/man8/blktrace.8.html | 一次(ツール)/ CM0 での実績は未確認 |
| readahead(2) | 起動時に先読みする用途のシステムコール | https://man7.org/linux/man-pages/man2/readahead.2.html | 一次(存在)。**効果は SD で小さいとの二次報告あり**(idea 資料 F-13、スニペットのみ) |

【作成者の見立て=推測】手順案:(1) 開発ビルドで fanotify(または strace)でアクセス一覧を採取 → (2) 初回アクセス順に優先度を付けた SORT-FILE を生成(起動に使うファイルほど高い優先度=先頭付近に配置される想定)→ (3) `mksquashfs -sort` で再パック → (4) blktrace で読込がシーケンシャルに近づいたか確認 → (5) 終点時間を 15 章の方法で比較。`-sort` は優先度の高いものが先に書かれる(sort.c で確認済み=一次)。ただし実イメージ上の物理配置と SD での読込改善は未測定=推測。

#### (c) EROFS との比較(一次)
| 観点 | EROFS | SquashFS | 出典URL |
|---|---|---|---|
| 既定圧縮 | **圧縮する場合は LZ4 が既定の性格(FAQ)。ただし mkfs.erofs は `-z` を指定しないと圧縮しない(main.c・man)** | GZIP | https://erofs.docs.kernel.org/en/latest/faq.html |
| 圧縮単位 | 物理クラスタ既定 4KiB(ブロック単位)。1MiB 等の大クラスタはランダム読込を大きく悪化させうると警告 | 128KiB | 同上 |
| 同条件比較の注意 | 比較時は圧縮アルゴリズム・クラスタ・レベル・`-Efragments` を揃える。EROFS は既定でイメージが大きくなりうる(64B inode、メタデータ非圧縮=6.17 以降は圧縮可、ファイル重複排除なし→`-Efragments`/`-Ededupe`)。小さい圧縮単位(32KiB 未満)では EROFS の方が小さくなることも多い | 同上 | 同上 |
| カーネル文書 | 4KiB ブロック整列、LZ4/LZMA/DEFLATE/ZSTD 等、Direct I/O や FSDAX は非圧縮 inode | https://docs.kernel.org/filesystems/erofs.html | 一次 |
| 公表ベンチ(v3 5.x 引用) | EROFS 論文(ATC'19):Android 端末でアプリ起動が SquashFS 比最大 22.9% 高速(**条件固有**)。https://www.usenix.org/system/files/atc19-gao.pdf | — | 二次(v3/idea 資料より、本文は今回再確認せず)|
| RPi ツリーでの有効性 | RPi の bcm2711_defconfig は `EROFS_FS_ZIP_ZSTD=y`(6.18 比較資料)。SquashFS も RPi 既定 | v3 6 章 | 一次 |

**EROFS の配置最適化(`--sort` 等)**:v5:mkfs.erofs(erofs-utils v1.9.4 @f36cadb)の man では **`--sort` は tar 入力用で、ディレクトリ入力の配置最適化には使えない**。圧縮は `-z` で指定(`-zlz4hc` など)。`-C` は物理クラスタの最大サイズ、`--MZ` はメタデータ/ディレクトリデータを別領域にまとめて高レイテンシ記憶装置向けにする、`-m#[:alg]` はメタデータ圧縮(Linux 6.17+)。**EROFS には SquashFS の `-sort` に相当する配置指定の手段を v5 では見つけられていない**(未確認)。EROFS 側は「4KiB クラスタ+LZ4」が既定の性格であり、SD の低レイテンシ・ランダム読みが課題なら有利になり得るが、CM0+SD での実測は無い(推測)。

【作成者の見立て】読み取り専用 rootfs は **まず SquashFS(zstd または lz4、ブロック 128K〜256K)と EROFS(lz4、4KiB)の 2 構成を実機で比較**し、終点時間・SD 読込量・RAM 使用量を測る。どちらが勝つかは未測定。

#### (d) overlayfs
- overlayfs の公式文書:https://docs.kernel.org/filesystems/overlayfs.html(upper/work は書込み可 FS が必要。RO rootfs+tmpfs upper の構成で書込みは RAM に逃げる)。【一次(文書の存在)。電断耐性の細部(7.0 の fsync opt-in 化は 6.18 比較資料)は別途】
- ext4 の `data=ordered`(既定)/`commit=` 等の公式説明:https://docs.kernel.org/admin-guide/ext4.html。【一次】

## 17. libc・アロケータ(提案 4)

> 11 章との対応: 11.3 D3(libc)(11.5 に対応表)

出典:別 executor の調査 事前資料(2026-10-18 完成)を取り込みました。同資料は一次=公式ソース/配布元索引、二次=第三者記事。**数値は条件が異なるため合成しません**。確認度は同資料のラベルを維持し、v5 でも libc 比較の本文は再取得していません(原資料に基づく=報告による。同資料が一次と明記した項目は URL を示します)。v5 で再取得したのは Buildroot 2026.08 の openssh/dropbear/openvpn/wireguard の版のみ(13.4A)。

### 17.1 版と対応(Buildroot 2026.08、タグ 813cbac、2026-09-04T15:31Z = 2026-09-05 00:31 JST)
- BusyBox 1.38.0、binutils 既定 2.45.1(選択肢 2.44/2.45.1/2.46.1)、glibc 2.44-36-g2d5421f(git 固定)、musl 1.2.6(2026-03-20 公開)、uClibc-ng 1.0.59(2026-08-08 公開)、mbedTLS 3.6.6、OpenSSH 10.5p1、systemd 258.7、RAUC 1.15.2、SWUpdate 2026.05.1。**これで v3 の N15 は一次で解消**。 【一次】出典:https://raw.githubusercontent.com/buildroot/buildroot/2026.08/package/busybox/busybox.mk (同 `binutils/Config.in.host`、`glibc/glibc.mk`、`musl/musl.mk`、`uclibc/uclibc.mk`)、https://musl.libc.org/releases.html 、https://uclibc-ng.org/
- Buildroot の C ライブラリ選択肢は uClibc-ng / glibc / musl(既定 glibc)。aarch64 は 3 つとも対応。Newlib・picolibc・llvm-libc の選択肢は無い。https://github.com/buildroot/buildroot/blob/2026.08/toolchain/toolchain-buildroot/Config.in 【一次】
- Yocto Wrynose 6.0(LTS、2030-04 まで):glibc 2.43+git / musl 1.2.6+git。TCLIBC の docs は glibc / musl / newlib / baremetal。uClibc-ng は選択肢に無い。https://docs.yoctoproject.org/migration-guides/release-notes-6.0.html 、https://docs.yoctoproject.org/ref-manual/variables.html 【一次】

### 17.2 比較表(要約。詳細は原資料 1.1〜1.8)
| 観点 | glibc | musl | uClibc-ng | Newlib / picolibc / llvm-libc | 出典・確認度 |
|---|---|---|---|---|---|
| ライセンス | LGPL-2.1+ | MIT | LGPL-2.1+ | BSD 系 / BSD 系 / Apache-2.0 w/ LLVM Exc. | 原資料 |
| aarch64 Linux | 可 | 可 | 可 | Newlib は `newlib/libc/sys` に linux が無い(【**未確認**】:sourceware のページは bot 防御ページで取得できず=13.4B V5B-181。linux ディレクトリが無いことは未確認)。picolibc は Linux hosted は試験用(README)。llvm-libc は「重要関数が不足」と公式 docs が警告 | https://sourceware.org/git/?p=newlib-cygwin.git;a=tree;f=newlib/libc/sys;hb=HEAD(取得できず)/ https://libc.llvm.org/full_host_build.html(llvm-libc 部分のみ。Linux で不可と断定はしない) |
| systemd | **Buildroot の systemd は glibc のみ**(`depends on BR2_TOOLCHAIN_USES_GLIBC`)。upstream の musl 対応は v259(2025-12-17)で「不完全・実験的」、継続サポート非約束。v260 で glibc>=2.34 に引上げ予告 | NSS 系(nss-systemd 等)・DynamicUser= 等は動かない | — | — | https://github.com/buildroot/buildroot/blob/2026.08/package/systemd/Config.in / https://github.com/systemd/systemd/releases/tag/v259 / https://github.com/systemd/systemd/pull/38825 一次 |
| RAUC / SWUpdate | RAUC 1.15.2:Config.in は libc 非限定(glib2・OpenSSL 等必要)。SWUpdate:**静的リンク不可**(`!BR2_STATIC_LIBS`) | musl・uClibc-ng での実機動作は未確認 | 同左 | — | https://github.com/buildroot/buildroot/blob/2026.08/package/rauc/Config.in / …/package/swupdate/Config.in 一次(Config.in)/ 動作未確認 |
| セキュリティ | `_FORTIFY_SOURCE` は glibc ツールチェーン必須(Buildroot Config.in)。SSP 常時可 | **FORTIFY は本体に無い**(Alpine は fortify-headers 3.0.1。本体に無い点は二次/推測)。既知脆弱性 CVE-2026-40200(32bit の qsort。aarch64 は対象外と読める)、CVE-2026-6042(iconv GB18030 DoS)、1.2.6 まで | `UCLIBC_BUILD_PIE` は aarch64 が依存条件に無い、SSP は既定無効、FORTIFY 設定は見つからず | — | https://github.com/buildroot/buildroot/blob/2026.08/Config.in / https://raw.githubusercontent.com/wbx-github/uclibc-ng/master/extra/Configs/Config.in / https://musl.libc.org/releases.html 一次 |
| 機能差 | lazy binding あり | lazy binding なし(意図的)、dlclose は no-op、locale/iconv 限定 | — | — | https://wiki.musl-libc.org/functional-differences-from-glibc.html 一次 |
| サイズ(配布元の索引。**ミニマム構成の値ではない**) | Debian trixie arm64 libc6 2.41-12+deb13u4:パッケージ 2,483,572 B / Installed-Size 23,769 KB(gconv・locale 含む) | Alpine aarch64 musl 1.2.6-r2:パッケージ 417,710 B / 展開後 723,480 B | — | — | https://deb.debian.org/debian/dists/trixie/main/binary-arm64/Packages.xz / https://dl-cdn.alpinelinux.org/alpine/latest-stable/main/aarch64/APKINDEX.tar.gz 一次(索引)。**両者の比を計算しない**(版・ビルドが違う) |

### 17.3 起動・exec コストの公表値(**条件併記・合成禁止**)
| 値 | 条件 | 出典 | 確認度 |
|---|---|---|---|
| 自己 exec(静的)musl 234µs / uClibc 245µs / dietlibc 272µs / glibc 457µs。動的は 446/590/675/864µs | musl 1.1.5、uClibc 0.9.33.2、dietlibc 0.32、glibc 2.19、**Intel Atom N280(32bit x86)**、著者注記「近似値」 | https://www.etalabs.net/compare_libcs.html | 二次(musl 作者のページ) |
| fork+exec:動的 131µs/静的 31µs(Core i5-6600K)、動的 1762µs/静的 507µs(Celeron N3060。**ChromeOS の Crostini VM 上での測定** で、実機と同列には比べられない。gist 本文で確認) | **x86_64、libc 比較ではなく静的/動的の比較**(musl-gcc でビルド) | https://gist.github.com/hadrianw/ad07a76f338f09565703ae6ea35993c8 | 二次 |
| Zero 2 W、Buildroot 2024.02.1、**フル glibc**、カーネル大幅削減・非圧縮・initramfs なしで電源投入からユーザ空間まで約 3.5 秒(カーネル実行約 400ms) | 個人ブログ(条件:電源投入→GPIO トグル、KASLR・Spectre 緩和無効、sound/USB 等無効。5.2) | https://kittenlabs.de/blog/2024/09/01/extreme-pi-boot-optimization/ | 二次 |
- **aarch64 / Cortex-A53 / 現行版(musl 1.2.6、glibc 2.44)での公表比較は見つからなかった(未確認。否定ではない)**。

### 17.4 アロケータ(jemalloc / mimalloc など)
- 原資料には含まれていません。v4 で確認できた一次は mimalloc README(「自社ベンチで他の主要アロケータを上回る」と主張しつつ「ベンチは合成的なものを含み、結果は注意して解釈せよ」と注記):https://github.com/microsoft/mimalloc/blob/main/readme.md 【一次(主張の存在)。CM0・起動時間の数値なし】。jemalloc は**未調査**。
- 【作成者の見立て=推測】512MB・CLI 構成では、アロケータ差し替えの効果は起動時間より RSS/断片化に出る可能性があり**優先度は低い**。

### 17.5 作成者の見立て(原資料の見立て+v4 の整理。全て推測・未実測)
- **systemd を使う → glibc 一択**(Buildroot 側の制約が一次で確認済み)。**BusyBox init+自作ミニ init → musl 静的リンク**が有利(MIT・小さい)。uClibc-ng は新規設計では優先度低。Newlib/picolibc/llvm-libc は Linux 用 libc としては候補外(Newlib の Linux 非対応は上の表のとおり【未確認】。Buildroot の選択肢に無いことだけが根拠)。
- 16.2 の init 選択と連動:M5 の udev/systemd unit 前提(16.2)を考えると、**全機能維持を優先するなら glibc+systemd 最小化が現実的**。musl+BusyBox は軽いが、M5 の udev ルール移植・NSS 非対応の制約を負う。
- 起動時間への libc 差は、静的 BusyBox 等で exec 回数が少なければ全体のうち数十 ms 未満と推測(未実測)。支配項は firmware+カーネル側(KittenLabs の事例)。CM0 実機で `perf trace`/bootchart 相当を取るのが確実。
- SSH/VPN(21 章)との関係:OpenSSH は glibc なら libxcrypt を選ぶ(Buildroot Config.in)、Dropbear は静的ビルドに向く。

## 21. SSH・VPN の追加、暗号拡張、鍵保管と A/B OTA

> 11 章との対応: 11.3 D7(SSH/VPN)(11.5 に対応表)

### 21.1 BCM2837 の ARMv8 Crypto Extensions
| 事実 | 出典URL | 確認度 |
|---|---|---|
| Cortex-A53 の Cryptography Extension は**オプションで、標準製品に含まれず追加ライセンスで供給**される(Arm DDI 0501F の本文:「The optional Cryptography Extension is not included in the base product. ARM supplies the Cryptography Extension only under an additional licence…」。v9 で PDF を取得し `pdftotext` 後 L303-304 で確認) | https://documentation-service.arm.com/static/5e9077ee8259fe2368e2acf7?token=(Arm DDI 0501F。13.4A V9A-003) | 確認済み(一次。v9。Cortex-A53 一般の話で、BCM2837 が実装しているかは別) |
| `ID_AA64ISAR0_EL1` の AES/SHA1/SHA2 フィールドは「Cryptographic Extension を含まない実装では 0x0」(Arm のレジスタ定義) | https://support.arm.com/documentation/101433/0102/Register-descriptions/AArch64-system-registers/ID-AA64ISAR0-EL1--AArch64-Instruction-Set-Attribute-Register-0--EL1 | 取得できず(HTTP 403。v4 の「一次(定義)」は v5 で再取得できず) |
| BCM2837 は JTAG で当該レジスタを読み **AES/SHA1/SHA2=0、CRC32=1** との個人報告。BCM2837B0(Pi 3B+)の `/proc/cpuinfo` Features に `aes/pmull/sha1/sha2` が無く `crc32` がある、との報告 | https://forums.raspberrypi.com/viewtopic.php?t=207888 / https://forums.raspberrypi.com/viewtopic.php?t=263234 | 取得できず(HTTP 403)。v4 の記述は個人報告(**Broadcom/RPi の一次仕様ページは取得できず**。RPi の processors ページは HTTP 403) |
| sbc-bench:Broadcom の 64bit 対応 RPi(BCM2712 以外)は crypto 加速が無いと記載 | https://github.com/ThomasKaiser/sbc-bench/blob/master/results/ARMv8-Crypto-Extensions.md | 二次 |
| 帰結:**CM0(BCM2837)は AES/SHA/PMULL 命令なしと見てよいが、一次(メーカー仕様)での確認は未取得**。実機で `/proc/cpuinfo` の Features を見れば確定できる(実機未入手) | — | 二次+推測 |
| カーネルは CE 版と NEON 版・汎用版を持つ(`arch/arm64/crypto/aes-ce-*`、`aes-neon*`、`lib/crypto/arm64/chacha-neon-core.S`、`sha256-ce.S` 等)。ChaCha は `CRYPTO_LIB_CHACHA_ARCH` が `ARM64 && KERNEL_MODE_NEON` で既定有効 | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/lib/crypto/Kconfig#L46-L52 / https://github.com/raspberrypi/linux/tree/234188315037848e5b07d65b85d38edc64095caa/lib/crypto/arm64 | 一次 |

### 21.2 WireGuard の速度への影響
| 事実 | 出典URL | 確認度 |
|---|---|---|
| WireGuard カーネルモジュールは `CRYPTO_LIB_CHACHA20POLY1305` と `CRYPTO_LIB_CURVE25519` を使う(AES を使わない) | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/net/Kconfig#L75-L83 | 一次 |
| 公式のパフォーマンスページのベンチは **Intel Core i7-3820QM / i7-5200U、Linux 4.6.1、GbE** の古い測定で、公式自身が「old, crusty, and not super well conducted」と注記。**ARM/CM0 の数値は無い** | https://www.wireguard.com/performance/ | 一次 |
| 帰結:**WireGuard は AES を使わず ChaCha20-Poly1305 のため、Crypto Extensions が無くても NEON 実装が使える(カーネルに `chacha-neon`)。OpenSSH の既定暗号は ChaCha20-Poly1305 が先頭(21.5)、Dropbear は GCM が既定無効で ChaCha20-Poly1305 が有効のため、CE が無くても不利になりにくい。OpenVPN は `--data-ciphers` 既定が AES-GCM 先頭なので、CE の無い CM0 では ChaCha20-Poly1305 を先頭にする設定が要る**。ただし CM0 での実スループットは**公表値が見つからず、実機未測定=推測**。Wi-Fi は 2.4GHz 802.11n、Ethernet は 10/100M(USB 2.0)なので、リンク側が先に上限になる可能性が高い(推測) | https://docs.m5stack.com/en/CardputerZero | 推測 |
| Dropbear のオプション:ChaCha20-Poly1305 は「AES 命令のない CPU では AES256 より概して速い」とコメントあり | https://github.com/mkj/dropbear/blob/DROPBEAR_2026.94/src/default_options.h(既定:CHACHA20POLY1305=1、GCM=0。21.5) | 一次(コメント) |

### 21.3 SSH と VPN の選択肢
| 項目 | 事実 | 出典URL | 見立て(推測) |
|---|---|---|---|
| Dropbear | 小型の SSH サーバ/クライアント。`PROGRAMS=dropbear` でサーバのみビルド、`localoptions.h` でアルゴリズム/認証/転送を無効化して小さくできる。静的ビルドでは zlib を無効にするとサイズが減る | https://github.com/mkj/dropbear/blob/master/README.md / https://github.com/mkj/dropbear/blob/master/SMALL.md | 小さく BusyBox 系と相性が良い。socket activation(systemd)で常駐を避ける案 |
| OpenSSH(sshd) | 標準的。既定の暗号・KEX は `myproposal.h`(V_10_5_P1)で確認(21.5)。`man.openbsd.org/sshd.8` の取得は接続不可で未取得 | https://raw.githubusercontent.com/openssh/openssh-portable/V_10_5_P1/myproposal.h | サイズ大・依存多(OpenSSL/libcrypto 等)。systemd 構成なら導入は簡単 |
| WireGuard | カーネル内蔵(`CONFIG_WIREGUARD`)+ `wg` ツール。導入手順は公式 https://www.wireguard.com/install/ と https://www.wireguard.com/quickstart/ | https://www.wireguard.com/quickstart/ | 起動時間の影響はモジュールロード時のみ。**終点の後に起動** で良い |
| OpenVPN | ユーザー空間デーモン+OpenSSL。Buildroot 2026.08 は 2.7.6。公式マニュアル(2.7):https://openvpn.net/community-docs/community-articles/openvpn-2-7-manual.html(2.6 の旧 URL はこのコミュニティ文書へ移転) | 同 | **暗号は `--data-ciphers` の設定が要る**(既定は AES-256-GCM:AES-128-GCM:CHACHA20-POLY1305。ChaCha は利用可能な場合のみ)。CM0 では AES-GCM がソフト実装で遅い見込み(推測)なので ChaCha20-Poly1305 を先頭にする(21.5) |

### 21.4 鍵保管と A/B OTA
【作成者の見立て=推測(一次情報で検証した設計ではない)】
- **ホスト鍵(SSH)・WireGuard 秘密鍵・認証情報は A/B のどちらの rootfs にも入れず、別の永続 RW パーティション(小さい ext4)に置く**。A/B 切替・ロールバックで鍵が変わると、クライアント側の known_hosts 警告や VPN 切断が起こるため。
- 鍵の生成は**初回起動時(個体ごと)** に行う。イメージに共通鍵を焼くと全個体が同じ鍵になる(典型的な落とし穴)。
- 電断耐性:鍵ファイルは「tmp に書く→fsync→rename」(v3 6 章/RP WP の手順)で更新。RW パーティションが壊れても機器は起動する分離(P-6)。破損時は鍵再生成になる点を許容するかを決める。
- 権限:`0600`。microSD は取り外せるため**暗号化なしでは鍵が抜き取り可能**(個体の物理的脅威モデルは未検討)。dm-crypt は CM0 に AES 命令が無く遅い見込み(推測)。ChaCha20 系(Adiantum:RPi defconfig に `CRYPTO_ADIANTUM=m`)は CE 非搭載機向けとされる(本調査では一次未確認)。
- OTA ペイロードの署名検証(RAUC/SWUpdate)は v3 7 章。**署名鍵・検証鍵の保管とローテーション**は未調査。
- Dropbear: `-r` でホスト鍵ファイルのパスを指定できる(`dropbear` の man/README を要確認。**今回未確認**)。sshd は `HostKey`(OpenSSH の man 未取得)。

### 21.5 ポスト量子(PQ)鍵交換と SSH/VPN の既定暗号(v5 追加。実装の既定ファイルで確認)

**確認方法**:各実装の「既定値を定義するファイル」を GET して読んだ(2026-10-18 JST)。Buildroot 2026.08(コミット d5180309)の同梱版は各 `package/*/*.mk` の版を GET。**CM0 での実行時間・スループットは公表値が見つからず、実機未測定=すべて推測**。

| 実装(版:何の版か) | 既定の暗号・鍵交換(定義ファイル) | PQ ハイブリッド | コスト(出典にある範囲) | 出典 |
|---|---|---|---|---|
| **OpenSSH 10.5p1**(Buildroot 2026.08 同梱版。ポータブル版のタグ V_10_5_P1) | 暗号の既定順(`myproposal.h` の `KEX_SERVER_ENCRYPT`):**`chacha20-poly1305@openssh.com`**、`aes128-gcm@openssh.com`、`aes256-gcm@openssh.com`、aes128/192/256-ctr。MAC は ETM 系が先頭。鍵交換の既定順:**`mlkem768x25519-sha256`**、`sntrup761x25519-sha512`、`sntrup761x25519-sha512@openssh.com`、`curve25519-sha256`…(クライアントは DH group exchange 等も追加) | **あり・既定で先頭**(ML-KEM-768 + X25519)。OpenSSH 10.0 のリリースノート(2025-04-09)が「mlkem768x25519-sha256 is now used by default for key agreement」と記載 | リリースノートは「considerably faster than the previous default」と記載(比較対象の「previous default」が何かはノートに明記なし)。**CM0 での時間は不明**。ChaCha 先頭のため AES 命令なし(21.1)でも不利になりにくい(推測) | https://raw.githubusercontent.com/openssh/openssh-portable/V_10_5_P1/myproposal.h / https://www.openssh.org/txt/release-10.0 / https://raw.githubusercontent.com/buildroot/buildroot/2026.08/package/openssh/openssh.mk |
| **Dropbear 2026.94**(Buildroot 2026.08 同梱版。CHANGES の日付 2026-07-23) | `default_options.h`:`DROPBEAR_CHACHA20POLY1305 1`、`DROPBEAR_AES128/256 1`、**`DROPBEAR_ENABLE_GCM_MODE 0`(AES-GCM は既定で無効)**。鍵交換:`DROPBEAR_CURVE25519 1`、`DROPBEAR_ECDH 1` | **あり・既定で有効**:`DROPBEAR_SNTRUP761 1` と `DROPBEAR_MLKEM768 1`(ともにハイブリッド) | 同ファイルのコメント:「sntrup uses ~9kB code size, mlkem uses ~34kB code size (32-bit armv7)」「Both are fast」。GCM は「slower than CTR on CPU w/o dedicated AES/GHASH instructions」とコメント(CM0 は該当見込み)。CHANGES:「These do increase code size, at least sntrup761 is recommended」 | https://raw.githubusercontent.com/mkj/dropbear/DROPBEAR_2026.94/src/default_options.h / https://raw.githubusercontent.com/mkj/dropbear/DROPBEAR_2026.94/CHANGES / https://raw.githubusercontent.com/buildroot/buildroot/2026.08/package/dropbear/dropbear.mk |
| **OpenVPN 2.7.6**(Buildroot 2026.08 同梱版。マニュアルは 2.7) | **暗号は設定が要る**:`--data-ciphers` の既定は「AES-256-GCM:AES-128-GCM:CHACHA20-POLY1305(ChaCha20-Poly1305 が使える場合。なければ前 2 つ)」。`--cipher` は 2.6.0 以降 TLS モードで無視。`--auth` 既定 SHA1(AEAD では無視)。`--data-ciphers-fallback` は 2.3 以前の相手向け | **マニュアル上は既定になし、実効既定は OpenSSL 版依存**:`--tls-groups` の説明は「OpenSSL 1.1+ restricts the list per default to "X25519:secp256r1:X448:secp521r1:secp384r1"」で ML-KEM を含まないが、OpenVPN 2.7.6 は `--tls-groups` を指定したときだけグループを設定する(ssl.c L552。`options->tls_groups` が真の場合のみ)。マニュアル 2.7 は「OpenSSL 1.1+ の既定は X25519:secp256r1:X448:secp521r1:secp384r1」と書くが**古い記述の可能性**があり、Buildroot 2026.08 の OpenSSL 3.6.4 の既定グループ一覧は先頭が `X25519MLKEM768`(ssl/t1_lib.c L209)。**実際の接続で ML-KEM が使われるかは未確認**(出典:openvpn v2.7.6 `ssl.c` L552、openssl-3.6.4 `ssl/t1_lib.c` L209、buildroot 2026.08 `libopenssl.mk` の `LIBOPENSSL_VERSION = 3.6.4`) | AES-GCM が先頭のため、AES 命令なしの CM0 では **`--data-ciphers CHACHA20-POLY1305:AES-256-GCM` のように ChaCha を先頭にする設定が要る**(推測)。実測なし | https://openvpn.net/community-docs/community-articles/openvpn-2-7-manual.html / https://raw.githubusercontent.com/buildroot/buildroot/2026.08/package/openvpn/openvpn.mk |
| **WireGuard**(カーネル組込み。wireguard-tools 1.0.20260223、wireguard-linux-compat 1.0.20220627 は Buildroot 2026.08 の版) | 固定のプリミティブ:ChaCha20-Poly1305、Curve25519、BLAKE2s、HKDF(暗号選択の設定なし) | **標準にはなし**。公式プロトコル説明:「If an additional layer of symmetric-key crypto is required (for, say, post-quantum resistance), WireGuard also supports an optional pre-shared key」 | AES を使わず NEON 実装あり(21.2)。事前共有鍵(PSK)は任意で、鍵配布は別途必要 | https://www.wireguard.com/protocol/ / https://raw.githubusercontent.com/buildroot/buildroot/2026.08/package/wireguard-tools/wireguard-tools.mk / https://raw.githubusercontent.com/buildroot/buildroot/2026.08/package/wireguard-linux-compat/wireguard-linux-compat.mk |

**読み取れること(事実の範囲)**
- OpenSSH 10.5p1 と Dropbear 2026.94 は、**何も設定しなくても PQ ハイブリッド鍵交換が有効**(Buildroot 2026.08 が同梱する版)。OpenVPN 2.7.6 はマニュアル上は既定で PQ なし(実効既定は OpenSSL 版依存。OpenSSL 3.6.4 の既定グループは先頭が X25519MLKEM768 で、OpenVPN 2.7.6 は `--tls-groups` 未指定ならグループを設定しない。実接続での使用は未確認=UN-27)。WireGuard は PSK による追加層のみ。
- 暗号(データ保護)側は、OpenSSH は ChaCha20-Poly1305 が先頭、Dropbear は ChaCha20-Poly1305 有効・GCM 無効、OpenVPN は GCM 先頭(要設定)。**v4 の OpenSSH 既定暗号の記述は誤り**(12.5)。
- Dropbear の ML-KEM は約 34kB(armv7 の値)、sntrup は約 9kB の追加コード。ディスクと RAM が小さい構成では 34kB を見積もるが、**CM0(aarch64)での値や起動時間への影響は未測定**。

【**作成者の見立て=推測、未測定**】:①鍵交換は接続ごとの 1 回の計算なので、起動の終点(15 章)の**後** に sshd/dropbear を socket activation で起動する限り、起動時間への影響は小さいと見込める。②実測で重要なのは「SSH 接続確立までの時間」で、CM0 の A53(Crypto Extensions なし)での ML-KEM/X25519 の実測を実機到着後に行う(10.2 に追加)。③PQ を使う場合のサーバ・クライアント双方の版要件(古いクライアントとの互換)は**未調査**。

**未確認**:OpenSSH の ML-KEM 実装が CM0 でどの程度の時間かかるか(OpenSSH 側の公表値なし)、OpenVPN で ML-KEM 系のグループが実際に使われるか(OpenSSL 3.6.4 の既定は先頭 X25519MLKEM768 だが、OpenVPN 2.7.6 は `--tls-groups` 未指定ならグループを設定しない=ソース読みのみ。実接続は未確認。`--tls-groups` に何を書けるかも未確認)、Buildroot での OpenSSH の `libcrypto` 構成(21.3)。
