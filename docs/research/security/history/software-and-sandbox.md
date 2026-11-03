# sandbox・compiler hardening・Rustの調査履歴

[強化項目の案内へ戻る](README.md) / [現在のinit比較](../../alternatives/init.md) / [Linuxの機構](../principles.md)

以下は元の12・14・15節です。systemdの設定例はBusyBoxの製品設定ではありません。Debian/Ubuntuのcompiler設定やBuildrootの選択から、外部toolchain・全packageの実際の引数とELF属性を一括で推定しません。

Rust表の原見出しは2025-11-01、元の原稿名は2026-11-01でした。この整理ではどちらかを誤記と断定して書き換えず、表を現在の最新版情報と扱わないよう分けています。languageの変更自体を特権分離やsandboxの代わりにはしません。採否は[基本コマンド](../../alternatives/commands.md)・[init](../../alternatives/init.md)・[compiler](../../alternatives/toolchains.md)の現在の比較と合わせて判断します。

## 12. systemd の ProtectSystem 等 Sandboxing（調査のみ）

- 本機に systemd はないため `ProtectSystem=`・`PrivateTmp=`・`NoNewPrivileges=` 等の directive は直接対象外。**調査のみ**。
- 概念のマッピング（本機で使える同等物）:
  - `ProtectSystem=strict` → rootfs RO + `/data` 制限マウント（既に近い構造）
  - `NoNewPrivileges`は`prctl(PR_SET_NO_NEW_PRIVS, 1, ...)`等に対応する機能で、nosuid mountやLSMとの単純な同等置換ではありません。既存daemonやlauncherでの適用経路、exec・profile遷移・保有権限との整合を先に確認します。
  - `PrivateTmp`/`ProtectHome`/`ProtectKernel*` → mount namespace での隔離が同等概念。BusyBox の `unshare`・`nsenter` アプレット有無を確認し、必要なら util-linux 系を足す。
  - LSM による sandbox 化は AppArmor（カーネル ON 済）のプロファイルとして実装する方向が現実的。

## 14. Debian/Ubuntu におけるコンパイルオプション強化の経緯

Debian/Ubuntu が「ディストリビューション全体のデフォルト」を段階的に強化してきた流れは、本機（Buildroot で全体を自前ビルド）にとって「どのフラグが本当に効いたか」の実績表として使える。

### Debian の経緯

- **hardening-wrapper → dpkg-buildflags**: 初期は `hardening-wrapper` で個別有効化していたが、dpkg 1.16.1 系で `dpkg-buildflags` に一本化され、wheezy（Debian 7）のリリースゴールとして既定フラグに **`-Wl,-z,relro`（partial RELRO）、`-fstack-protector`、`-D_FORTIFY_SOURCE`、`-Wformat -Werror=format-security`** が入った。この時点で PIE と `-z now`（bindnow）は既定外で、`DEB_BUILD_MAINT_OPTIONS=hardening=+all` の opt-in。【一次: [Debian HardeningWalkthrough](https://wiki.debian.org/HardeningWalkthrough)、[Hardening](https://wiki.debian.org/Hardening)】
- **stretch（Debian 9）頃**: PIE を既定にする案が持ち上がり、dpkg ではなく **GCC 6 の `--enable-default-pie` configure オプション経由で gcc が既定 PIE を吐く**形にした（`-fPIC` 衝突を gcc 側で自動解決させるため）。bindnow もこの時期に既定化の方向へ。【一次: [debian-devel 2016-05](https://lists.debian.org/debian-devel/2016/05/msg00229.html)】
- 以後: `-fstack-clash-protection`、x86 向け `-fcf-protection`（CET）などは gcc 側の既定/機能有効化として吸収される形が主流。`DEB_BUILD_MAINT_OPTIONS` による feature 単位の切替（`hardening=+pie,-fortify` 等）は現在も有効。

### Ubuntu の経緯

Ubuntu は「ディストリビューションの gcc に既定フラグを埋め込む」方針を早くから採り、歴史的に Debian より先行している点が特徴。

- **Ubuntu 6.10（2006）**: `-fstack-protector` を gcc 既定で有効化（glibc 側の stack check ルーチンへのリンクを gcc パッチで既定化）。【一次: [Ubuntu ToolChain/CompilerFlags](https://wiki.ubuntu.com/ToolChain/CompilerFlags)】
- **Ubuntu 8.10（2008）**: `-D_FORTIFY_SOURCE=2` を既定化。【一次: Ruffell 氏の調査まとめに基づく wiki 記述】
- **Ubuntu 10.10（2010）**: `--param ssp-buffer-size=4` で stack protector の適用対象を拡大。
- **Ubuntu 14.10（2014）**: `-fstack-protector-strong` に切替。
- **Ubuntu 16.10**: PIE を amd64/ppc64el/s390x で既定化（gcc の default-pie 切替）。【一次: [Ubuntu Security documentation - compiler flags](https://documentation.ubuntu.com/security/security-features/process-memory/compiler-flags/)】
- **Ubuntu 17.10**: 全アーキテクチャで PIE を既定化。x86 以外はレジスタ数の影響が小さいため全 arch 化の判断。
- **その後**: `-Wl,-z,now`（bindnow）の既定化、x86 向け `-fcf-protection`（Intel CET）・`-fstack-clash-protection`、`-D_GLIBCXX_ASSERTIONS` 等が 19.10〜24.04 頃にかけて段階導入（個別リリース単位の正確な有効化時期は要検証）。

### 教訓（本機への適用）

- Ubuntu/Debian が得た効果の実績: ASLR の実効化（PIE）、リターンアドレス破壊の検知（SSP strong）、memcpy 系のバッファ境界検査（FORTIFY）、GOT の RO 化（RELRO/bindnow）、format string 脆弱のコンパイル時検出。**これらは互いに別の攻撃経路を閉じる層**で、どれか 1 つではなく重ねる設計。
- 本機の Buildroot 設定は既に **`BR2_PIC_PIE=y`、`BR2_SSP_STRONG=y`、`BR2_RELRO_FULL=y`（bindnow 含む）、`BR2_FORTIFY_SOURCE_3=y`** で、Ubuntu が 10 年以上かけて既定化したセットをほぼ踏襲している。【一次: `output*/.config`】
- 残りの差分候補: `-fstack-clash-protection`（Buildroot に個別オプションはなく、gcc 側 `-fstack-clash-protection` を `BR2_TARGET_OPTIMIZATION` に足す形）、`-fcf-protection` は ARM64 非対象（x86 専用）、`-D_GLIBCXX_ASSERTIONS` は stdc++ を使うパッケージがほぼないため効果薄。
- Debian/Ubuntu の「default-pie を gcc configure で有効化した」経緯は、Buildroot でも `BR2_PIC_PIE` がグローバルに効くため同等とみなせる。
- Ubuntu の hardening は「gcc パッチで既定にし、壊れる個別パッケージだけ例外的に外す」運用で、Buildroot の per-package `*_CONF_OPTS`/`CFLAGS` と同じ発想。

## 15. システムソフトウェアの Rust 化（最新情報）

「C 系の長年のバグの素因であるメモリ安全を、言語レベルで取る」動きが 2025 年に Debian/Ubuntu 系で顕在化した。本機は BusyBox ベースで対象ソフト自体を持たないものが多いが、方向性として記録する。

### 各ソフトの状況（2025-11-01 時点）

| ソフト | 状況 | 本機との関係 |
|---|---|---|
| sudo-rs（Trifecta Tech） | Ubuntu 25.10 で既定の sudo 実装に採用（元の sudo は `sudo.ws` として併存、0.2.8 で `sudoedit`・NOEXEC・AppArmor 切替に対応）。CVE-2021-3156（2011 年から潜伏した sudo のヒープ破壊）を「メモリ安全で防げた類」として採用理由に挙げられている。【一次: [Ubuntu 25.10 release notes](https://documentation.ubuntu.com/release-notes/25.10/)、[Trifecta Tech sudo-rs](https://trifectatech.org/projects/sudo-rs/)】 | 本機に sudo はない（BusyBox の `su` のみ）。対象外 |
| rust-coreutils（uutils coreutils） | Ubuntu 25.10 で既定の coreutils に（0.2.2、GNU 版は併存で切替可能、互換性の差分リストを公開）。base64 が大幅に高速化。【一次: 同上】 | 本機は BusyBox アプレットで coreutils を持たない。Buildroot に uutils のパッケージはない（GNU `coreutils` のみ収録）【一次: `vendor/buildroot/package/`】 |
| ntpd-rs（Trifecta Tech） | Debian パッケージあり（1.9.0）。NTS を早期に実装した実装として知られる。Ubuntu 25.10 は ntpd-rs ではなく Chrony+NTS を既定に採用。【一次: [Debian Rust tracker](https://rustsec.debian.net/pkgs/ntpd-rs.html)、Trifecta Tech】 | Buildroot 未収録（`openntpd`・`chrony`・`ntpsec` のみ）。9 節の NTS 案で Chrony を選んだ現状、別選択肢として名前だけ残す |
| APT（Debian） | 2025-11 に APT メンテナの Julian Klode が「2026-05 以降、APT に Rust の強い依存を入れる」と Debian 開発者リストで表明。.deb/.ar/tar のパーサと HTTP 署名検証が第一候補で、Sequoia（Rust 製 OpenPGP 実装）系を使う方針。【一次: [The New Stack](https://thenewstack.io/debian-mandates-rust-for-apt-reshaping-ubuntu-and-other-linux-distros/)】 | 本機に APT はない。Debian 系を使う将来の派生物で影響が出る可能性だけ記録 |
| zlib-rs / libzstd-rs | Trifecta Tech の data-compression イニシアティブで進行。sudo-rs 0.2.8 が両者対応済み。【一次: Trifecta Tech】 | squashfs/zstd の伸張を行う mksquashfs・カーネルとは別レイヤ。現状関係なし |
| Sequoia（OpenPGP） | APT の署名検証を支える Rust 実装として Debian が採用方向。【一次: 同上】 | 本機の msd-update は Ed25519 直接検証（OpenPGP 非使用） |
| statime（PTP） | Trifecta Tech の時刻同期イニシアティブで進行中。IEEE 1588 PTP の Rust 実装。 | NTP ではなく PTP。時計同期の選択肢に入らない |

### 傾向と本機への示唆

- 採用されているのは「**権限境界・パーサ・プロトコル実装**」（sudo、.deb/HTTP 署名、NTP/NTS）で、攻撃面が外部入力の解釈に集中する領域。本機の外部入力面は msd-update の署名検証とカーネルのプロトコル処理が主。
- 本機はユーザー空間が BusyBox（C）＋カーネルで構成され、置き換えられる個別ソフトがそもそもないため、**Rust 化の恩恵は「依存先の上流が安全になる」形で間接的に入る**。例: ホスト側ビルド環境が Debian 系なら、将来 APT・sudo が Rust 化した恩恵を受ける。
- 仮に将来 userspace を拡充するとき、uutils coreutils・sudo-rs・ntpd-rs は「Buildroot 未収録」のため手組みが要る（外部 toolchain + cargo ビルド）。対費用効果は現状低い。
