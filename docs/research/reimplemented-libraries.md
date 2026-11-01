# 再実装ライブラリとアロケータの調査（2026-11）

既存のライブラリを実装し直したもの（フォーク・スクラッチ再実装）の調査です。調査のみで、採否・実装の決定は行いません。本機の前提: Buildroot 2026.08、glibc（外部 Bootlin ツールチェーン、64 ビット）、OpenSSL が有効な唯一の TLS/暗号ライブラリ、SSH は未導入。

フォーク（既存コードを分岐）とスクラッチ再実装（API 互換を目指す新規実装）は区別します。効能は「小ささ・起動時間・攻撃面・保守性・ライセンス」のどれに効くかで記します。

## 1. TLS / 暗号

| 実装 | 元実装との関係 | Buildroot | 効能と本機への適用 |
|---|---|---|---|
| LibreSSL | OpenSSL 1.0.1g からの OpenBSD フォーク（2014、Heartbleed 対応で分岐）。API 面を削減し続けており OpenSSL 3.x とは非互換部分が増えている | `BR2_PACKAGE_LIBRESSL` あり | 削減された API 面とコード量が攻撃面を下げる効能。ただし依存パッケージ側が OpenSSL 3.x API を要求する場合に移植コストが出る。本機は openssl のみで、署名検証 (Ed25519) に限定用途なら候補になり得るが、現状の openssl 置換の利得は限定的【推測】 |
| BoringSSL | Google の OpenSSL フォーク。配布を前提としない（「自前の利用以外の配布対象として意図していない」と公式が明言） | なし | 非推奨。配布しない方針のため組み込み製品への利用は意図外【一次: BoringSSL README】 |
| mbed TLS | ARM 主導のスクラッチ実装（旧 PolarSSL）。TLS 1.3 は 3.x で段階対応 | `BR2_PACKAGE_MBEDTLS` あり | 小型・PSA Crypto API・分離したコンポーネント選択が強み。PSK/DTLS を使う組み込み TLS で実績が多い。効能は「小ささと選択性」。本機で TLS サーバー実装を入れるなら第一候補 |
| wolfSSL | スクラッチ再実装（組み込み・RTOS 向け）。FIPS 140-3 認証版あり | `BR2_PACKAGE_WOLFSSL` あり | FIPS 認証が要る案件向け。本機に認証要件はなく、効能は mbed TLS と重複 |
| BearSSL | Thomas Pornin のスクラッチ実装。極小・定数時間の実装を標榜 | `BR2_PACKAGE_BEARSSL` あり | 最小の TLS 実装候補。機能は限定的（TLS 1.2 系中心）で、本機の用途には過少の可能性【未確認】 |
| GnuTLS | OpenSSL と独立した GNU 実装 | `BR2_PACKAGE_GNUTLS` あり | LGPL であり効能は OpenSSL と大きく変わらない。置換の利得は薄い |
| libsodium / nettle / libgcrypt | TLS ではなく暗号プリミティブ層 | `BR2_PACKAGE_LIBSODIUM` / `NETTLE` / `LIBGCRYPT` あり | libsodium は Ed25519 署名だけなら極小で済む候補。msd-update の Ed25519 検証を openssl より小さく構成できる可能性【推測】 |
| monocypher / libhydrogen | TweetNaCl 系の最小暗号ライブラリ | なし（Buildroot 未収録） | Ed25519 検証だけなら数千行で済む。署名検証の最小構成として注目だが、vendor 追加コストと監査が必要 |

現行 openssl 維持が妥当なのは、カーネル同様に成熟した実装・更新監視が効く点です。置換の動機が「イメージサイズ」なら libsodium/monocypher 系の調査の方が筋がよいと考えます。

## 2. C ライブラリ（libc）

比較表は [ユーザー空間・libc 調査](userspace-and-security.md) §17.3 が正です（glibc / musl / uClibc-ng / Newlib / picolibc / llvm-libc）。ここでは補足のみ。

- **musl**: MIT、スクラッチ再実装。静的リンク・小ささ・決定的な実装が強み。本機が外部 Bootlin ツールチェーンの glibc を使う現状では、musl への切替はツールチェーン変更（Buildroot 内蔵 musl ツールチェーン or Bootlin musl 版）が必要で、署名済みユーザーランド全体の再ビルド・再検証を伴う。効能はイメージサイズと依存の簡素化【推測】。
- **picolibc**: Keith Packard 主導。newlib-nano と AVR libc の流れを統合した組み込み向け libc。printf/scanf を削減した `tinystdio` が特徴。**設計上 Linux ホスト環境は想定しておらず、Linux hosted ビルドは試験用**。本機のルートfs の libc としては対象外で、仮に bare-metal 補助コアやブートローダを自作する場合の候補【一次: picolibc README】。
- **llvm-libc**: LLVM 製 libc。公式が「重要関数が不足」と警告しており本機用途では未成熟【一次: libc.llvm.org】。

## 3. malloc 実装

| 実装 | 系譜 | Buildroot | 効能 |
|---|---|---|---|
| ptmalloc（glibc 内蔵） | dlmalloc をスレッド対応に改変したもの。glibc 既定 | （glibc 内部） | 現行。スレッドアリーナで競合時にヒープが分裂する既知の欠点はあるが、本機は常駐プロセスが少ない |
| musl malloc / mallocng | musl 独自。mallocng は 1.2.1 以降の新アロケータで quarantine・スレッド安全の設計 | musl 採用時のみ | musl 化とセットの効能。単体では取り出せない |
| dlmalloc | Doug Lea の古典実装。ptmalloc の祖先 | なし | 小さく参照実装として有名。自前リンクに使えるが保守は止まっている |
| jemalloc | FreeBSD 由来。FreeBSD/NetBSD の libc 標準でもある | `BR2_PACKAGE_JEMALLOC` あり | スケーラビリティとフラグメンテーション耐性が強み。LD_PRELOAD で差し替え可能だが、ライブラリ自体のサイズ増が見込まれる【未確認：サイズ差】 |
| mimalloc | Microsoft。短い実装・free-list sharding | なし | §17.4 のメモどおり README ベンチは合成的。差し替え実験するならサイズと起動時間の測定が前提 |
| tcmalloc（gperftools） | Google。スレッドキャッシュが特徴 | なし | 常駐サーバー向けの効能。組み込み最小構成では過剰 |
| snmalloc | Microsoft Research。一定時間メタデータ参照を志向 | なし | 新しく利用実績は限定的【未確認】 |
| scudo | LLVM/compiler-rt 付属。セキュリティ志向のヒープ | なし | Android の既定ヒープ。隔離とヒープ攻撃緩和が効能。本機に常駐マルチスレッド server がない現状では優先度は低い |
| rpmalloc | スレッドローカルヒープ型 | なし | 同上 |

本機は glibc 内蔵の ptmalloc が現状で、常駐プロセスが少なく、更新系コマンドは短命です。フラグメンテーションや速度より、ライブラリ自体の追加コストの方が支配的になるため、アロケータ差し替えの利得は薄いと考えます【推測】。差し替え検討は「常駐プロセスのメモリ断片化」が観測されたときの対策として待つのが妥当です。

## 4. JVM・ランタイムの再実装

| 実装 | 元実装との関係 | 本機への適用 |
|---|---|---|
| OpenJ9 | IBM の JVM。JDK 7 時代から社内実装を持ち、Eclipse へ移管。HotSpot と同じ API の別実装 | CardputerZero（CM0、RAM 512MB）に Java 常駐は現実的でなく、効能（小ヒープ・共有クラスキャッシュ・省メモリ）を受ける場面がない。調査記録のみ |
| GraalVM native-image | HotSpot ベースの JDK から AOT コンパイルする機構。別実装ではなく同族ツール | 同上。native-image は起動時間を大きく下げる効能があるが、JVM ワークロードが前提 |
| Android Runtime（ART） | Dalvik の後継として Google が作り直した | 対象外 |

効能として記録する価値があるのは「小さいメモリで JVM が回る」点ですが、本機に Java ワークロードがないため適用先はありません。

## 5. その他の再実装（パッケージ候補）

| 実装 | 元実装との関係 | Buildroot | 効能と適用 |
|---|---|---|---|
| zlib-ng | zlib からのフォーク（next-gen）。SIMD 最適化 | `BR2_PACKAGE_ZLIB_NG` あり | gzip 系処理の速度効能。initramfs・カーネル側は zstd のため、本機で効く場面は限定的 |
| libdeflate | スクラッチ再実装（EB Wise）。zlib API 一部互換 | `BR2_PACKAGE_LIBDEFLATE` あり | gzip/zlib の圧縮・展開を大幅に高速化する効能。msd-update の圧縮データ処理が zlib 系なら差し替え候補【未確認：呼び出し側の対応】 |
| libjpeg-turbo | libjpeg からのフォーク＋SIMD | `BR2_PACKAGE_JPEG_TURBO` あり（`jpeg` 仮想パッケージの実装選択肢） | 画像処理を入れた場合の速度効能 |
| toybox | BusyBox と同じ方向の、もう一つの minimal userland 再実装（BSD ライセンス） | `BR2_PACKAGE_BUSYBOX` 代替選択肢なし（busybox 固定） | BusyBox からの全面差し替えは根拠が薄い【推測】 |
| sbase / ubase | suckless の minimal coreutils。設計で最小化 | なし | 同上 |
| openntpd | OpenBSD 製 NTP 実装（ntpd の簡素版） | `BR2_PACKAGE_OPENNTPD` あり | NTS 非対応。9 節の時刻合わせで Chrony（NTS 対応）を選んだ現状では劣位 |
| dropbear | OpenSSH と独立した SSH 実装 | `BR2_PACKAGE_DROPBEAR` あり | SSH を入れるなら openssh より小さい効能。セキュリティ調査の前提（SSH 未導入）から先に採否を決める必要がある |
| mandoc | man-db と独立した man/groff 系実装 | なし（`mandoc` パッケージは現行 Buildroot 未収録） | オンライン man は本機に不要 |
| openrsync | OpenBSD の rsync 再実装 | なし | 更新経路で rsync を使う場合の小さい選択肢 |
| sudo-rs / uutils coreutils | Trifecta Tech の Rust 再実装（Ubuntu 25.10 で uutils が既定化） | なし | [セキュリティ強化項目の調査](security-2026-11-hardening-list.md) §15 を参照。本機は BusyBox アプレットで sudo・coreutils を持たず差し替え対象がない |

## 6. ブラウザエンジンの再実装

| 実装 | 元実装との関係 | Buildroot | 効能と本機への適用 |
|---|---|---|---|
| Servo | Mozilla 始まりの Rust 製ブラウザエンジンのスクラッチ再実装。現在は Linux Foundation Europe 傘下。v0.7.0（2026-10-05、月次リリース）を公開。SpiderMonkey は ESR 153 系。MPL-2.0、MSRV 1.88。`servo-aarch64-linux-ohos.so` などの組み込み向けライブラリ形態もあり、埋め込み用 API を公表している | なし | 「埋め込み可能な WebView」をうたう Rust 製エンジンとして最新状況を記録。ただし 512MB RAM の CM0 では実用サイズに届かない可能性が高く【推測】、レイアウト・JIT の重さから本機では対象外扱いが妥当。月次リリースが続く活発さを記録する |
| NetSurf | 独立した小型ブラウザエンジン（独自レンダラ） | `BR2_PACKAGE_NETSURF` あり | フレームバッファ・SDL フロントエンドを持ち、組み込み最小構成で最も現実的な本格ブラウザ。JS 限定的だが、情報表示には十分【推測】 |
| Dillo | C 製の超小型ブラウザ。GTK3 版もある | `BR2_PACKAGE_DILLO` あり | 最小ブラウザの代表格。JS 非対応。リーダー用途には合う |
| links | テキスト/グラフィカルブラウザ | `BR2_PACKAGE_LINKS` あり | 最低限の描画で済む用途向け |
| WebKitGTK / WPEWebKit | WebKit からの GTK/埋め込み向け分岐 | `BR2_PACKAGE_WEBKITGTK` / `WPEWEBKIT` あり | フル機能の WebView を入れる場合の実用候補だが、RAM・起動時間のコストが大きい |
| Ladybird | SerenityOS 発の独立ブラウザエンジン（プロジェクト分離済み） | なし | 開発中の新実装。実用段階ではない |
| qt-webkit-kiosk | Qt WebKit のキオスク実装 | `BR2_PACKAGE_QT_WEBKIT_KIOSK` あり | Qt ベースのキオスク用途 |

**本機へのまとめ**: 物理 LCD へのリッチ表示を今後検討するなら、現実的な順位は NetSurf > Dillo/links > WPEWebKit。Servo は現在のリソース要件から見送りが妥当ですが、月次リリースで進化しているため定点観測の価値はあります。

## 7. 本機への適用まとめ

1. **置換の利得が見込める候補**: msd-update の Ed25519 検証を openssl から小さい実装（libsodium / monocypher 系）に分離できるか。署名・検証だけならイメージを削れる可能性。要・サイズ実測。
2. **速度向上が見込める候補**: libdeflate / zlib-ng（更新データの圧縮・展開を zlib 系で行っている場合）。
3. **観測待ち**: アロケータ差し替え（jemalloc/mimalloc）はフラグメンテーションの観測が前提。
4. **評価不能・対象外**: Zephyr 4.5（`rpi_zero_2w` ボードは追加されたが SDHCI 未確認）、OpenJ9、picolibc（Linux hosted は試験用）、BoringSSL（配布を意図しない）。

## 出典

- Buildroot 2026.08 `vendor/buildroot/package/` のパッケージディレクトリ（libressl・mbedtls・wolfssl・bearssl・gnutls・libsodium・nettle・libgcrypt・jemalloc・libdeflate・zlib-ng・libjpeg-turbo・openntpd・dropbear・newlib-bare-metal の存在を確認。monocypher・libhydrogen・picolibc・toybox・sbase・mandoc・openrsync・sudo-rs・uutils・mimalloc・tcmalloc・snmalloc・scudo・rpmalloc は未収録）【一次】
- BoringSSL README（配布非意図の記載） https://github.com/google/boringssl 【一次】
- picolibc README https://github.com/picolibc/picolibc 【一次】
- llvm-libc full host build の警告 https://libc.llvm.org/full_host_build.html 【一次】
- musl malloc については [ユーザー空間・libc 調査](userspace-and-security.md) §17.3-4 を参照
- Rust 再実装の最新状況は [セキュリティ強化項目の調査](security-2026-11-hardening-list.md) §15 を参照
