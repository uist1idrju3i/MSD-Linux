# Cライブラリーの適用範囲と再評価

[代替比較](README.md) / [RESEARCH](../../../RESEARCH.md)

## 基準と結論

2026-11-02に一次資料と固定Buildrootの選択肢を照合しました。現行はBootlin SDK `2025.08-1`のglibc `2.41-70-g1502c248d58cb99a203731707987a4342926e830`です。上流glibcの公式ページが示す安定版2.44や、Buildroot内蔵toolchainのglibcとは区別します。

現行glibcを比較基準として残し、rootfs全体の軽量化ではmusl、関数やhelperを絞った構成ではLLVM libcを実験候補とすることを提案します。新しい実装なら自動的に安全・小型になるとは判断しません。代替libcによるMSD/Linuxのbuild・実行は、本リポジトリでは試していません。

未リリースなのでglibcのbinary ABIを維持する必要はありません。それでも、同じrootfsの実行ファイル・shared library・loaderは整合させる必要があります。libcを一つ差し替えるだけではなく、ユーザー空間全体の再build・試験と、対応する外部SDKまたは内蔵toolchainの準備が必要です。

## 候補の比較

| 候補 | 対象・使える機能の根拠 | 本機での条件・失う可能性があるもの | 再評価 |
|---|---|---|---|
| glibc | GNU/Linux向けのC/POSIX・thread・resolver・dynamic loading等。公式は6か月ごとのreleaseとsecurity連絡先を公開（L1） | GNU拡張・NSS・locale・既存libraryとの統合を比較基準にできる。使わない機能の配布を減らせるかは別途調べる。外部SDK内の固定版へsecurity修正が入る経路も必要 | 現行維持。互換性だけが維持理由ではない |
| musl | Linux syscall上のISO C/POSIX、thread、static/dynamic linkingを対象とする。公式はMITとstatic配布を説明（L2） | locale・IDN等の範囲とGNU拡張の差を調べる。M5 kernel moduleがlibcを使わないことは、関連する全userspace toolも動く証拠ではない | 全体置換の優先実験候補。init変更と一緒に行わない |
| uClibc-ng | 公式はAArch64、Linux、shared library、thread、MMUなしの構成まで記載（L3） | 組み合わせる構成項目が増える。SSP・PIE・FORTIFY等の実効値、resolver・locale・ABIを固定構成で確認する必要がある。MMUなし対応だけでは本機の利点にならない | 実験候補として残すが、muslより先に選ぶ根拠は未確認。保守停止・AArch64非対応という理由では除外しない |
| LLVM libc | upstreamの現行説明は、x86-64/AArch64の静的Linux server/container等で用途を絞った本番利用を記載。一方、regex・locale・wide-character I/O等の不足も明記（L4） | Buildrootのlibc選択肢にない。Linux向けcross buildにはkernel API headers・sysroot等が必要（L5）。上流の一部用途の成功は、BusyBox・OpenSSL・kbd・libv4l等の全APIが足りる証拠ではない | 一律の未成熟扱いを撤回し、限定したhelper・関数の実験候補へ戻す。全rootfs置換は必要APIの照合後 |
| newlib | 組み込み向けC library。公式Syscalls章はOS側のread/write/sbrk等とreentrant wrapperを説明（L6） | AArch64のcodeを生成できることと、Linux/POSIXの全体を提供することは別。OS glue、thread、resolver、dynamic loading、localeを照合せずglibcの代替としない | 用途限定。必要なら別のbare-metal firmwareで検討。Linux全体の置換は根拠不足 |
| picolibc | newlibとAVR libc由来の、小さいRAMを対象とするC library。READMEは32/64-bit ARMを含む試験基盤を記載（L7） | READMEのLinux hosted試験例はi386/x86_64。そこからAArch64 LinuxのPOSIX全体対応は導けない。stdio縮小の効果と、欠けるAPIのglueを作る費用を分ける | 用途限定。Linux向けの小型glibcと見なさず、bare-metal・補助firmwareで再検討 |
| Bionic | AOSPのlibc・libm・dynamic linker等。保守者向け概要はAndroid固有の構成、kernel UAPI header更新等を説明（L8） | Androidのtoolchain・linker・周辺libraryとの統合を評価する必要がある。Buildrootに単独libcとして追加する実装と本機での利益は未確認 | 今回のrootfs置換対象外。Androidの一部技術を使う場合は範囲を限定して再検討 |
| klibc | kernel.orgの配布索引は確認したが、公式GitのREADME取得はbot判定画面だった（L9） | 本文・現行版の機能・AArch64条件を読めていない。配布索引への到達だけで最小POSIX対応や保守状態を確定しない | 未確認。初期userspace用途も含めて一次本文を取得してから判定する |

この表の「実験候補」は、版の選定やintegrationを終えた意味ではありません。各候補の安定release・security修正・EOLを固定版へ対応付けること、閉じた依存一覧とライセンスの照合は、採用前の条件です。LLVM libcについては、安定releaseで同じ説明が成り立つかと、今回確認した開発treeの状態も分けます。

## LLVM libcの旧評価を変える根拠

旧調査では`full_host_build`の重要関数不足の警告を根拠に、本機では未成熟とまとめていました。現行の公式トップと、その原文を持つLLVM commit `7a35ab1791fbfc25a0ab56b14693a516cf205bbe`は、用途を絞った本番利用と、まだ不足している機能を併記しています（L4）。今回読んだ`full_host_build.md`は、sysroot・kernel headers・bootstrap・buildの手順を説明する文書です。古い警告の表現を現在もあるものとして引用しません。

この変化は「Linuxに不向きなので候補から除く」という扱いを変える根拠になりますが、MSD/Linuxの互換性・速度・安全性を保証するものではありません。上流のGoogleでの利用は上流の報告であり、本リポジトリで確認した運用結果ではありません。

評価を進める方法は二つあります。

- **overlay・部分利用**: 必要な関数だけを既存libcと組み合わせられるか調べます。関数・symbolの衝突、ライセンス、CPU別実装、試験範囲を限定できますが、混在させれば自動的に正しくなるわけではありません。
- **full build**: libc自身と実行環境を一式構築し、必要なC/POSIX APIを照合します。公式cross buildのAArch64向け例は出発点になりますが、Buildrootへの組込みや全packageの適合を済ませた例ではありません。

置換できる関数の数だけで採否を決めず、入力が攻撃者の制御下にある処理、thread、signal、errno、allocation失敗、locale、時刻、ファイルの境界を調べます。

## Buildrootと全機能への影響

固定Buildrootの[内蔵toolchain設定](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/toolchain/toolchain-buildroot/Config.in)で選べるlibcはglibc・musl・uClibc-ngです。これは外部Bootlin SDKのlibcをmenuconfigで単体交換できるという意味ではありません。newlib等のbare-metal向けpackageが存在しても、製品Linuxのlibc選択とは別です。

| 境界 | 比較する契約・試験 | 合格として扱わないもの |
|---|---|---|
| ELF / ABI | interpreter、`DT_NEEDED`、symbol version、startup object、TLS、errno、thread、time_t・large file | hello world一つがlinkできたこと |
| CLI・日本語 | BusyBox shell、kbdのkeymap/font、UTF-8、`mbrtowc`・`wcwidth`等の必要API、locale、stdioの失敗 | フォントが表示できることだけでlocale・文字幅も互換とすること |
| ネットワーク | IPv4/IPv6、DHCP後のDNS、resolver timeout、reconnect、時刻、証明書、entropy | kernelのWi-Fi driverだけが有効なこと。userspace接続の未実装も試験条件に残す |
| 更新・保存 | 既存の署名検証・hash・拒否条件、両slot、readback、rollback、read-only rootfs、ext4の検査 | 更新bundleを解凍できるだけで署名・復旧が同じとすること |
| カメラ・音声等 | libv4l・ioctl、各CLI/helper、device nodeと権限、選ぶ上位library | kernel moduleがloadしたことだけで上位softwareも対応とすること |
| init / device管理 | 現行BusyBox init・mdevをまず維持。systemd等の条件は別に評価 | libc・init・device管理を同時に変え、原因をlibcだけに帰すること |

固定Buildrootの[systemd設定](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/package/systemd/Config.in)には`BR2_TOOLCHAIN_USES_GLIBC`への依存があります。これは、その固定recipeの制約です。上流systemdの別releaseまで永久にmusl非対応とする根拠ではありません。現行はBusyBox initなので、libcを比べるためにsystemdを追加する必要はありません。

## 最小特権・保守・ライセンス

libcを小さくすることと、processの権限を小さくすることは別です。muslやLLVM libcに変えても、rootで動く更新処理、deviceへの書込み、受け付ける入力は残ります。最小特権・特権分離、read-only、署名検証、syscallやfile accessの制限は、libcにかかわらず設計します。static linkは不要なloader依存を減らせる場合がありますが、libcの修正を各binaryへ反映して再配布する費用が生じます。

| 候補 | ライセンスの確認範囲と残件 |
|---|---|
| glibc / uClibc-ng | LGPL系列の実装として扱う。外部SDK全体のheaders、runtime、第三者部分、対応sourceと再link条件の照合完了とはしない |
| musl | 公式aboutのMIT表記を確認（L2）。採用する固定sourceのCOPYRIGHTと個々の由来も照合する |
| LLVM libc | 固定したLICENSE.TXTでApache-2.0 with LLVM Exceptionsを確認。source別の例外・同梱物を含む配布確認は別に行う（L4） |
| newlib | 複数由来のコードを含むため、一つのBSDライセンスとして一括処理しない。選ぶ版の個別noticeの照合は未完了 |
| picolibc | READMEはBSD系を説明する一方、printf試験の2ファイルにGPL-2.0-or-later、`GeneratePicolibcCrossFile.sh`にAGPL-3.0-or-laterを記載。runtime・試験・helperを分ける。`COPYING.picolibc`の全件確認は未完了（L7） |
| Bionic / klibc | 固定版と全配布物のlicense確認は未完了。Android由来・kernel関連という名称だけでBSDまたはGPLに一括分類しない |

脆弱性の公開件数の単純比較はしません。使うAPI・target・build条件への影響、upstreamの修正、SDKやBuildrootへの反映、製品の再配布までを確認します。代表licenseや上流のsecurity窓口の存在だけで採用を確定しません。

## 次の検証で判定すること

以下は未実施です。compiler・最適化・init等をそろえた構成を作り、libc以外の変更を記録します。glibc SDKとmusl SDKでcompiler版まで違う場合は、libc単独の比較とは呼びません。

1. 全targetとSDK内包物の必要APIを一覧化し、compile/linkとsymbolを検査する。static/dynamicの構成を混ぜない。
2. C/POSIX・thread・signal・DNS・UTF-8・時刻・entropyの機能試験を行う。未実装のWi-Fi接続等を、libc互換と見なして省略しない。
3. 署名済み更新と拒否条件、QEMUのA/B・powerfail smoke、全周辺機能の試験を行い、実機未確認を区別する。
4. 同じ条件で5回以上、compressed image・展開サイズ・runtime依存・PSS/RSS・起動・CPU・build時間と失敗を記録する。第三者のx86や別distributionのlibcパッケージサイズ比は本機へ適用しない。
5. security修正の入ったsource・binary・SBOM・配布物を追えることを確認し、節約したサイズと増えた保守・試験費用を並べる。

現段階では節約量を数値で示せません。muslは全体置換、LLVM libcは対象を限定した検証という異なる問いから始めるのが妥当です。newlibやpicolibcの小ささだけを理由に、Linux機能のglueを自作し直す案は勧めません。

## 一次資料

本文確認日は2026-11-02 UTCです。時刻・hash・取得失敗は[sources.json](sources.json)を参照してください。

| ID | 資料 |
|---|---|
| L1 | [glibc公式](https://sourceware.org/glibc/)。API、release周期、stable 2.44とdevelopment 2.45、security連絡先 |
| L2 | [musl公式about](https://musl.libc.org/about.html)。Linux・C/POSIX・thread・MIT・static配布と機能の制約 |
| L3 | [uClibc-ng公式](https://www.uclibc-ng.org/)。AArch64、Linux、shared library、threadの対応 |
| L4 | [LLVM libc公式](https://libc.llvm.org/)、[本文の固定source](https://github.com/llvm/llvm-project/blob/7a35ab1791fbfc25a0ab56b14693a516cf205bbe/libc/docs/index.md)、[LICENSE.TXT](https://github.com/llvm/llvm-project/blob/7a35ab1791fbfc25a0ab56b14693a516cf205bbe/libc/LICENSE.TXT) |
| L5 | 同commitの[host build](https://github.com/llvm/llvm-project/blob/7a35ab1791fbfc25a0ab56b14693a516cf205bbe/libc/docs/full_host_build.md)、[cross build](https://github.com/llvm/llvm-project/blob/7a35ab1791fbfc25a0ab56b14693a516cf205bbe/libc/docs/full_cross_build.md)、[platform support](https://github.com/llvm/llvm-project/blob/7a35ab1791fbfc25a0ab56b14693a516cf205bbe/libc/docs/platform_support.md) |
| L6 | [newlib公式manualのSyscalls章](https://sourceware.org/newlib/libc.html#Syscalls)。reentrant wrapperとOS側の実装 |
| L7 | [picolibc README](https://github.com/picolibc/picolibc)。機能、試験platform、licenseと例外。取得したGit blobはsources.jsonに記録 |
| L8 | [Bionic maintainer overview](https://android.googlesource.com/platform/bionic/+/master/README.md)。libc・libm・linker・UAPI等の構成 |
| L9 | [klibc配布索引](https://www.kernel.org/pub/linux/libs/klibc/)、[取得できなかったREADME](https://git.kernel.org/pub/scm/libs/klibc/klibc.git/tree/README)。後者はbot判定画面で本文未確認 |
