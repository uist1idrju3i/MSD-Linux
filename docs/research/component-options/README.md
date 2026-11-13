# 固定コンポーネントの機能・設定・引数

[RESEARCH](../../../RESEARCH.md)へ戻る。

## 何が分かるか

固定した版のsource、正規化した設定、Buildrootの変数展開、CIの生成物、SDKとOCIのhelpを照合した。固定時点の採取では製品設定や依存版を変更していない。後日のtimezone採用は別の記録とし、機能・設定面・現行値・候補の効果と背反・追加検証を、以下の本文と台帳に分ける。

| 主題 | 本文 |
|---|---|
| 2026-11-13の利用者判断と未実装・未決定の区別 | [製品方針](../../design/product-decisions.md)。seed非保存・初回zram・速度優先・更新移行までのCMS／CLI維持・legal-info補足collectorを決定。PQCと`/data`の具体値は未決定 |
| OpenSSL 3.5.9の最小化・openssl.cnf・ARM最適化の調査草案 | [現状・採否・設定案](openssl-minimal.md)、[全option表](openssl-minimal-options.csv) |
| Buildroot、GCC、binutils、外部SDK、共通flags、PIE・RELRO・LTOの適用範囲 | [Buildroot・toolchain](buildroot-toolchain.md) |
| kernel Kconfig、compile、cmdline、module、sysctl、DeviceTree、firmware | [kernel・firmware](kernel-firmware.md) |
| target 18件、BusyBox、glibc、OpenSSL、util-linux、network・保守command | [ユーザー空間](userspace.md)、[OpenSSL系列差](openssl-series.md) |
| timezoneの既定値、tzdataの収録範囲、host-zicの引数 | [timezone](timezone.md)。2026-11-12に追加した採用記録で、下の固定時点の18件の採取結果とは別です |
| host 49件、configure、Meson/Make等、圧縮、FS・disk image生成 | [host・image生成](host-image.md) |
| 開発用OCI、APT、pip/Go、CI tools、Actionsとrunner | [OCI・CI tools](ci-tools.md) |
| 取得元・hash、母集団、失敗試行、同じ入力での再生成、検査の範囲 | [採取・再生成](reproduction.md) |

## 台帳

| 資料 | 件数・単位 | 読む際の制限 |
|---|---|---|
| [packages.csv](packages.csv) | 67 component。target 18、host 49 | 全78 show-info recordsのうちvirtual 8、rootfs 3を除いたもの。SBOMは`bom-ref`で結合 |
| [package-variables.json](package-variables.json) | 上記componentごとの採取変数 | 全Make変数ではない。raw/expandedを分離。未解決の`PKG`・`$@`を実際のbuild commandとしない |
| [common-variables.json](common-variables.json) | 共通flags・wrapperの7変数 | wrapper・package・kernelの追加と上書きを含む最終compile logではない |
| [buildroot-symbols.csv](buildroot-symbols.csv) | 8,376 symbol宣言行 | source path・行番号と正規化値。未選択branchや重複宣言を含み、depends/default/select/helpの全条件を解決した表ではない |
| [gcc-options.csv](gcc-options.csv) | 1,779 option/category照会行 | GCC 14.3.0へ`-Q -Os -mcpu=cortex-a53`。5 categoryを別々に採取。同じoptionの重複と空欄を保つ |
| [kernel-config.csv](kernel-config.csv) | CI生成物の最終6,836 symbol | 全kernel Kconfig宣言ではない。moduleのロード、policy適用、実機動作は別 |
| [configure-options.csv](configure-options.csv) | 28 sourceのhelpから1,776行 | 最初の説明行。wrapped help・既定値・条件や非Autoconfの全設定を網羅しない |
| [apt-surfaces.csv](apt-surfaces.csv) | 固定amd64 OCIの231 package | 機能概要、homepage、実行file・設定・manualのpath。pip/Go/直接導入binaryを含む全imageのSBOMではない |
| [source-archives.json](source-archives.json) | legal-infoの56 archive | sourceのpath・bytes・SHA-256。licenseの適合や全source利用許諾の解決済みという意味ではない |
| [provenance.json](provenance.json) | 入力hash・版・OCI・artifact・helpの終了状態 | 新しく正規化した設定、過去のCI生成物、host helpの証拠を分離 |
| [verification.csv](verification.csv) | 5回・35照合のhash・bytes・判定 | 変換の再現性の確認。製品imageのbit単位再現性ではない |

`not-recorded`は無効ではなく、正規化した設定に値がなかったことを表す。`n`は明示された無効行、`withheld`は秘密値になり得るsymbolの非公開扱い。空欄、未収録、対象外、選択不可も混同しない。Buildrootのsymbolが`y`でも、上流の既定無効機能がenableになるとは限らない。

## 調査の境界と続く作業

これは固定時点の設定調査であり、全optionの意味解析、全compile/link引数の実行記録、全commandの実行試験、全componentの代替比較の完了ではない。実機、TLS・provider、libc tunables、firewall/LSM policyの実行時確認も別の試験が必要である。kernel module/sysctlの過去の値は、[取得時の版とQEMU条件](../tuning/tunables-defaults.md)を保って参照する。

未リリースで互換性維持が不要という方針に沿い、不要機能・旧暗号の削減、build/runtimeの権限分離、SDK内包物のSBOM、同名commandの引数差を優先的に検討する。採否は追加の比較・測定へつなげ、台帳の行数だけを理由に「全て検証済み」としない。
