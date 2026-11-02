# 使用部品・ツールの代替比較

[RESEARCH](../../../RESEARCH.md)へ戻る。

## 読み方と対象

この比較は、MSD/Linuxを保守する人が、現行の機能を残したまま依存を削減・置換できるか判断するためのものです。未リリースなのでABIや更新形式の変更も候補に含めます。ただし、互換性の維持が不要でも、LCD・キーボード・周辺機器や署名検証を失ってよいわけではありません。

| 主題 | この文書で答えること |
|---|---|
| [コンパイラーとランタイム](toolchains.md) | GCCとClang/LLVM、ZigのCコンパイル、linker、C++標準ライブラリー・ABI・unwinderを別々に選べるか |
| [Cライブラリー](libc.md) | glibc、musl、uClibc-ng、LLVM libc、newlib、picolibc、Bionic、klibcの適用範囲と再検討条件 |
| [基本コマンド・シェル](commands.md) | BusyBox、Toybox、GNU coreutils、uutilsと、更新・起動・復旧で必要な引数と挙動 |
| [init・service監視・device管理](init.md) | PID 1、supervision、readiness、権限制限を分け、s6、runit、OpenRC、systemd、Dinit等を比べる |
| [暗号・TLS](crypto.md) | OpenSSLの保守期限、署名専用libraryとTLSの別々の選定、依存・license・旧算法の削減条件 |
| [署名・鍵・配信の信頼境界](signing.md) | raw Ed25519の移植条件、manifest、鍵rotation、SemVerとanti-rollback、HTTPSと特権helperの分離 |
| [保存領域と実行時検証](filesystems.md) | SquashFS/EROFS、ext4/F2FS、設定overlay、dm-verity/fs-verityの違いと移行条件 |
| [A/B更新framework](updates.md) | 現行処理とRAUC・SWUpdate・Mender・Rugix・OSTree・bootc・sysupdateの責務、署名形式、CM0の未確認範囲 |
| [TUF・Uptane metadata](update-metadata.md) | role、threshold、expiry、freeze、rotationと、A/B health・SemVer・内部番号を分けた配信設計 |
| [Wi-Fi・接続管理・通信防御](network.md) | 認証・IP・DNS・時刻・HTTPSとfirewallを分け、wpa_supplicant・iwd・各managerの条件と未実装機能の計画を比べる |
| [周辺機能・BSP・device API](peripherals.md) | LCD・入力・音声・camera・IMU・RTC・電池・GPIO等を、driverとlibraryの層を分けて比べる |
| [圧縮・生成・host補助依存](build-support.md) | zlib互換性、image生成、build systemと内包libraryの置換条件を比べる |
| [構築基盤・開発・CI](development.md) | Buildrootと他の基盤、OCI、cache、QEMU、lint・scanner・SBOM・provenanceの責務と費用を比べる |

各分野の役割と代替・再検討条件を比較しましたが、全候補の機能・版・licenseや代替構成の実行確認を完了した索引ではありません。最小特権とnetwork隔離の具体設計、鍵・Releaseの利用者向け設定手順も未完了です。構成情報の母集団は[SBOMの確認範囲](../sbom-coverage.md)、現行の構築手順は[BUILD](../../BUILD.md)を参照してください。

### 構成要素との対応

[比較台帳](coverage.csv)は、[設定調査の67行](https://github.com/uist1idrju3i/MSD-Linux/blob/85cc4eb8d9e949708516754b32ae62d6b30c5868/docs/research/component-options/packages.csv)を、欠落・重複なしで比較本文へ対応づけます。host 49行、target 18行です。指定版とSBOM版、host/target、比較の境界、上流で観測した候補の範囲を分けます。上流候補は[依存台帳](https://github.com/uist1idrju3i/MSD-Linux/blob/40dee88d0ce4f2d2afb5dba87809eca3c04b9f16/docs/research/dependencies/buildroot-packages.json)の取得時点の値であり、全てを最新の安定版と呼ぶ表ではありません。

同じ本文への対応には、同じ責務としての比較と、親packageの移植が必要な比較を含みます。全67要素にdrop-inの代替があるという意味ではありません。GCC・libc等の外部toolchain内包物、OCIのAPT、Actionのnpm内包物、runnerはこの67行だけでは覆えないため、本文と依存監査の範囲を併読してください。実bundle・全配布binary・全licenseの監査と、深掘り待ちの候補は未確認のまま残します。

## 判定をそろえる

- **現行維持**: 比較の基準に残すという提案です。最新・最速・最安全との認定ではありません。
- **実験候補**: 置換の目的と条件を定め、独立した構成で試す候補です。製品設定には入れていません。
- **用途限定**: helper、初期起動、別のファームウェア等には用途がありますが、同じ機能の代替ではありません。
- **今回の置換対象外**: 現行機能に対応しない、または統合作業に見合う効果を確認できないものです。恒久的な不採用ではありません。
- **未確認**: 一次資料を取得できない、実体を調べていない等の理由を示します。非対応や脆弱性なしと読み替えません。

候補を本リポジトリでbuild・実行していない場合は、「本リポジトリでは試していない」と記します。上流の対応表、上流の本番利用例、本機での動作確認は別の証拠です。

## 比較の共通条件

1. direct/transitive、target/host、runtime/build-time、製品/開発/CIを区別します。コンパイラーはhostで動いても、生成するruntimeはtargetに入る場合があります。
2. 削除すると失う機能と、置換に必要なAPI・ABI・syscall・device・Buildrootの条件を先に確かめます。
3. AArch64対応とCortex-A53での命令実行を分けます。ほかのCPUの拡張命令や、hostの`-march=native`を本機へ持ち込みません。
4. ライセンスはruntime・headers・compiler・build helper・試験コードを分けます。代表的なライセンス名だけで配布の可否を確定しません。
5. 上流のrelease・security窓口と、こちらが使う固定版の保守を分けます。monorepoやBuildrootを固定しただけでは、内包する全依存を監視できません。
6. imageサイズ、RAM、CPU、起動時間、build時間、保守・復旧費用を比較します。小さいという自己紹介や別環境の測定を、本機での改善値にはしません。
7. privilege、入力の信頼境界、更新経路、不要な機能と依存の増減を比べます。実装言語や脆弱性件数だけで安全性を順位づけません。
8. 採用前の実験ではbase commit、tool版・hash、最終設定、生成物、失敗も保存します。同じ条件で5回以上反復し、サイズ差であっても機能を削った構成との比較を成功とはしません。

一次資料のURL・固定ref・取得状態・確認時刻・hashは[sources.json](sources.json)に記録します。本文の転載ではなく、取得経路と確認範囲の台帳です。

- `extracted-text`はWeb取得ツールの抽出結果です。途中で切れている可能性があり、raw HTMLの取得や全文の精読を意味しません。
- `capture-file-mtime`は、元の取得時刻が残っていない場合の保存ファイルの更新時刻です。取得時刻そのものと区別します。
- Gitの原文ファイル、raw HTML、SDK内のREADMEは、それぞれhashの対象を記します。Git blob SHAとSHA-256も別の値です。
- `not-returned-in-capture`、`retrieval-failed`、`bot-challenge`を取得・読了の成功に数えません。再取得した同じ資料の成功とは別の試行として残します。

本文の判断に使った範囲と、採用前に残る機能・license・版の確認は各比較文書に示します。出典のソースコードは取り込んでいません。

## 周辺・開発・CIの照合記録

2026-11-02 UTCに、周辺機能・host補助依存・開発/CIの比較を追加しました。比較基準は`f809fdffc833a7d47eaf255a0b3d50e58d68be9d`です。製品設定は変更していません。

- 出典は405件を変更せず、142件を追加しました。110件の取得応答と固定Buildroot由来20件についてbytesとSHA-256を照合し、そのうちGit blob IDのある57件も一致しました。11件の取得失敗とALSA wiki初回captureの上書き1件は、この130件の成功へ数えていません。上書きした初回captureの古いhashを、後のcaptureで照合した値と読み替えません。
- 67構成要素の名前・host/target・show-info版・SBOM版を上記の固定した設定調査CSVと照合し、欠落・重複なし、各比較先の存在を確認しました。依存台帳との名前の集合とscopeも一致しました。この対応は責務の索引であり、APIの互換試験ではありません。
- リンク・JIS文字集合・文書サイズ・スキル・サイトの検査と、各検査の回帰試験、既存`msd-update`のhost test、固定版チェッカーの回帰試験を実行しました。固定開発コンテナーのactionlint・ShellCheckと、offline zizmorも通りました。既存のJIS警告と20,000 bytes超の文書は残っています。
- yomiyasuで本文・差分と最終稿のhashを確認しました。libdeflateの旧評価を否定して訂正する表現、追加した未確認事項、役割別の表は意味を保つため残しています。`版`はsoftware version、`台帳`は行単位の一覧、`ゲート`は公開可否の検査を指すため残しました。自動検査の完了を意味の正しさの認定とはしません。

取得内容の全文精読、全候補のlicense・EOLの監査、代替構成のbuild・boot・性能測定・実機試験は、この照合記録の対象外です。
