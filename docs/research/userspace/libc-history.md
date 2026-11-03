# libc・allocatorの資料と条件付き比較

[ユーザー空間の案内へ戻る](README.md) / [現在のlibc比較](../alternatives/libc.md)

以下は資料を調べた時点の版・制約と、第三者の測定を条件付きで並べた記録です。現行の外部toolchainはglibcです。Buildrootの選択条件と、上流そのものが対応できる範囲は区別します。systemdとmusl、LLVM libc等の後の再評価は上の比較が正本です。

別のCPU・ABI・compiler・link方式で測った値を合成したり、異なる配布物のサイズ比をCM0の効果にしたりはしません。末尾に重複していた要約で版の情報を未確認とした原文も[CSV](original-summaries.csv)へ保持し、後の確認状態とは分けました。代替構成のbuild・実行は本リポジトリでは試していません。

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
| aarch64 Linux | 可 | 可 | 可 | Newlib の `newlib/libc/sys` の確認は未完了。picolibcのREADMEのLinux hosted試験例はi386/x86_64であり、AArch64 Linux全体対応とは扱いません。LLVM libcは用途を絞ったAArch64 Linuxでの本番利用を公式が記載しますが、regex・locale・wide-character I/O等の不足も明記しています。 | https://github.com/buildroot/buildroot/blob/2026.08/toolchain/toolchain-buildroot/Config.in<br>https://sourceware.org/git/?p=newlib-cygwin.git;a=tree;f=newlib/libc/sys;hb=HEAD（取得できず）<br>https://github.com/picolibc/picolibc<br>[2026-11-02の再評価と固定した一次資料](../alternatives/libc.md)。候補のbuildは本リポジトリでは試していません |
| systemd | **Buildroot の systemd は glibc のみ**（`depends on BR2_TOOLCHAIN_USES_GLIBC`）。upstream の musl 対応は v259（2025-12-17）で「不完全・実験的」、継続サポート非約束です。v260では glibc >= 2.34 への引上げが予告されています。 | NSS 系（nss-systemd など）・`DynamicUser=` などが使えないとの情報がありますが、musl との組合せでの確認は未実施です。【未確認】 | — | — | https://github.com/buildroot/buildroot/blob/2026.08/package/systemd/Config.in<br>https://github.com/systemd/systemd/releases/tag/v259<br>https://github.com/systemd/systemd/pull/38825 【一次 / 一部未確認】 |
| RAUC / SWUpdate | RAUC 1.15.2 の Config.in は libc を限定しません（glib2・OpenSSL などが必要です）。SWUpdate は静的リンクできません（`!BR2_STATIC_LIBS`）。 | musl・uClibc-ng での実機動作は未確認 | 同左 | — | https://github.com/buildroot/buildroot/blob/2026.08/package/rauc/Config.in<br>https://github.com/buildroot/buildroot/blob/2026.08/package/swupdate/Config.in 【一次（Config.in） / 動作未確認】 |
| セキュリティ | `_FORTIFY_SOURCE` は glibc ツールチェーンが必要です（Buildroot Config.in）。SSP は常時利用可能です。 | **musl 本体に FORTIFY はないとの情報がありますが未確認です。** Alpine は fortify-headers 3.0.1 を使います。既知脆弱性として CVE-2026-40200（32 bit の qsort。aarch64 は対象外と読めます）、CVE-2026-6042（iconv GB18030 DoS）があり、musl 1.2.6 までの範囲が記載されています。 | `UCLIBC_BUILD_PIE` は aarch64 が依存条件になく、SSP は既定で無効、FORTIFY 設定は見つかりません。 | — | https://github.com/buildroot/buildroot/blob/2026.08/Config.in<br>https://raw.githubusercontent.com/wbx-github/uclibc-ng/master/extra/Configs/Config.in<br>https://musl.libc.org/releases.html<br>https://wiki.musl-libc.org/functional-differences-from-glibc.html<br>https://gitlab.alpinelinux.org/alpine/fortify-headers<br>https://nvd.nist.gov/vuln/detail/CVE-2026-40200<br>https://nvd.nist.gov/vuln/detail/CVE-2026-6042 【一次 / FORTIFY は未確認】 |
| 機能差 | lazy binding あり | lazy binding なし(意図的)、dlclose は no-op、locale/iconv 限定 | — | — | https://wiki.musl-libc.org/functional-differences-from-glibc.html 一次 |
| サイズ(配布元の索引。**ミニマム構成の値ではない**) | Debian trixie arm64 libc6 2.41-12+deb13u4:パッケージ 2,483,572 B / Installed-Size 23,769 KB(gconv・locale 含む) | Alpine aarch64 musl 1.2.6-r2:パッケージ 417,710 B / 展開後 723,480 B | — | — | https://deb.debian.org/debian/dists/trixie/main/binary-arm64/Packages.xz / https://dl-cdn.alpinelinux.org/alpine/latest-stable/main/aarch64/APKINDEX.tar.gz 一次(索引)。**両者の比を計算しない**(版・ビルドが違う) |

### 17.3 起動・exec コストの公表値(**条件併記・合成禁止**)
| 値 | 条件 | 出典 | 確認度 |
|---|---|---|---|
| 自己 exec(静的)musl 234μs / uClibc 245μs / dietlibc 272μs / glibc 457μs。動的は 446/590/675/864μs | musl 1.1.5、uClibc 0.9.33.2、dietlibc 0.32、glibc 2.19、**Intel Atom N280(32bit x86)**、著者注記「近似値」 | https://www.etalabs.net/compare_libcs.html | 二次(musl 作者のページ) |
| fork+exec:動的 131μs/静的 31μs(Core i5-6600K)、動的 1762μs/静的 507μs(Celeron N3060。**ChromeOS の Crostini VM 上での測定** で、実機と同列には比べられない。gist 本文で確認) | **x86_64、libc 比較ではなく静的/動的の比較**(musl-gcc でビルド) | https://gist.github.com/hadrianw/ad07a76f338f09565703ae6ea35993c8 | 二次 |
| Zero 2 W、Buildroot 2024.02.1、**フル glibc**、カーネル大幅削減・非圧縮・initramfs なしで電源投入からユーザー空間まで約 3.5 秒（カーネル実行約 400 ms） | 個人ブログ（電源投入から GPIO トグルまで。KASLR・Spectre 緩和・sound / USB などを無効化） | https://kittenlabs.de/blog/2024/09/01/extreme-pi-boot-optimization/ | 二次 |
- **aarch64 / Cortex-A53 / 現行バージョン（musl 1.2.6、glibc 2.44）での公表比較は確認できていません（未確認。否定ではありません）。対象 SoC と libc のバージョンを明記した公開測定で確認する必要があります。**

### 17.4 アロケータ(jemalloc / mimalloc など)
- mimalloc README は、自社ベンチで他の主要アロケータを上回ると主張する一方、ベンチには合成的なものが含まれ、結果を注意して解釈するよう注記しています。CM0・起動時間の数値はありません。jemalloc は未調査です。https://github.com/microsoft/mimalloc/blob/main/readme.md 【一次（README の記載）】
- 【推測】512 MB・CLI 構成では、アロケータ差し替えの効果は起動時間より RSS / 断片化に出る可能性があり、優先度は低いと考えられます。

### 17.5 設計上の見立て（推測・未測定）
- **systemd を使うなら glibc が必要**です（Buildroot の制約）。**BusyBox init + 自作ミニ init なら musl の静的リンクが有利**と考えられます（MIT・小さいため）。uClibc-ng は新規設計での優先度が低いと考えられます。Newlib / picolibc / llvm-libc は Buildroot の選択肢にありません。Newlib の Linux 対応は未確認です。
- 初期案は BusyBox init + mdev + glibc です。M5 の udev / systemd unit を変更せず全機能を維持する必要がある場合は、glibc + systemd の最小化を代替案として比較します。musl + BusyBox は静的リンクの利点がありますが、udev ルールの移植と NSS の制約を評価する必要があります。
- 起動時間への libc 差は、静的 BusyBox などで exec 回数が少なければ全体のうち数十 ms 未満と推測されます（未実測）。支配項は firmware とカーネル側と考えられます（[KittenLabs の測定例](https://kittenlabs.de/blog/2024/09/01/extreme-pi-boot-optimization/)）。CM0 実機で `perf trace` / bootchart 相当を取る必要があります。
- OpenSSH は glibc なら libxcrypt を選びます（Buildroot Config.in）。Dropbear は静的ビルドに向きます。https://github.com/buildroot/buildroot/blob/2026.08/package/openssh/Config.in 【一次】
