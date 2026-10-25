# 測定の落とし穴

## このリポジトリで実際に起きたこと

| 落とし穴 | 実例 | 対策 |
|---|---|---|
| 計測器が数えていない | QEMU 6.2 の SD モデルでは QMP `query-blockstats` が読み書きとも 0 だった。「書き込みなし」と誤読しかけた | 読み込み側も 0 なら計測器を疑う。ゲスト側の `/sys/class/block/<dev>/stat` など別の計測器と照らし合わせる |
| 背景の処理が混ざる | ext4 の lazy-init の書き込みが混ざり、条件の差が見えなくなった | 測定前にアイドル時の増分が 0 かを確かめ、0 でない回は捨てて記録する |
| 版を別のバイナリから取る | CI が PATH 上の mke2fs（apt の 1.47.2）を記録したが、イメージを作ったのは Buildroot の 1.47.4 だった | 実際に使われたバイナリのパスを指定して版を取る |
| 試験が機能を動かしていない | QEMU の起動試験がモジュールを使わない範囲しか通らず、`modules.dep` が空のまま出荷されかけた | 対象の機能を実際に呼び出し、ログで確かめる |
| エラーを読まない | post-build の `grep: invalid option` が出てもビルドは成功し、mdev のルールが重複していた | ログのエラーと警告を読む。結果の不変条件（重複がないことなど）を検査する |
| 結果が PR 本文にしかない | S1 の試行結果が文書になかった | 結果は docs/experiments/ に書き、PR からリンクする |
| 測った binary が commit と違う | S11 v2 で使った QEMU は、commit した patch からではなく、image の `COPY` の層にあった作り置きの binary だった。commit した patch は、そのままでは当たらなかった（[S11 の Amendment 1](../../../../docs/experiments/2026-10-20-s11-qemu-watchdog.md)） | binary の SHA-256 と、作った commit または image の層を記録し、commit から作り直した binary と照らし合わせる |
| 条件の選択が届かない | S21 の再試行で、`docker/msd-dev` が `S21_MODES` などの環境変数を渡さず、runner が既定の P0 から始まった。runner は既存の run ID の上書きを拒否しなかった（[S21 の Amendment 1](../../../../docs/experiments/2026-10-21-s21-qemu-sysctl-ramoops.md)） | 条件の選択は CLI 引数で受け取る。既存のログや CSV があれば止める |
| 判定の行がゲートより前に出る | 電源断の試験で、driver の `SysRq U` の行は `handle_sysrq('u')` より前に出るため、SysRq を無効にした負の対照でも出た。正しい結果が矛盾に見えた（[S21 の Amendment 4](../../../../docs/experiments/2026-10-21-s21-qemu-sysctl-ramoops.md)） | 判定に使う行がどこで出るかをソースで確かめ、負の対照で出ないことを見る |
| 新しい行が既存の検査に当たる | `run-qemu.sh` の provenance の行を `msd-qemu:` で始めたところ、DTB のパス（`powerfail-raspi3ap.dtb`）の `fail` がログ検査の `msd-*` の規則に当たり、CI が失敗した（[PR #95](https://github.com/uist1idrju3i/MSD-Linux/pull/95)） | ログに新しく出す行は既存の検査に通し、検査の回帰試験に加える |
| 根拠が個人環境に依存 | 調査文書が個人の VM 上にあるファイルだけを根拠にしていた | リポジトリ内のファイル、CI の成果物、公開 URL を示す |

## 一般的な規則

| 規則 | 出典 |
|---|---|
| 改善する指標だけでなく、劣化しうる指標も測る。都合のよい部分だけを選ばない | Heiser, Systems Benchmarking Crimes A1・A2（https://gernot-heiser.org/benchmarking-crimes.html） |
| ばらつきを示し、相対値だけで書かない。環境の仕様を書く | 同 B4・E1・E3 |
| シミュレーションでの測定は、そうと明記する。調整に使ったデータで評価しない | 同 C1・C3 |
| 同じ状態から始め、最低 3 回、できれば 5 回以上繰り返す | OLS 2003 Performance Testing the Linux Kernel（https://www.kernel.org/doc/ols/2003/ols2003-pages-457-469.pdf） |
| 実験のスクリプト、入力、生の値、解析のスクリプトを残す | ACM Artifact Review and Badging（https://www.acm.org/publications/policies/artifact-review-and-badging-current） |
| 覆った結論も消さず、置換として残す | Nygard, Documenting Architecture Decisions（https://www.cognitect.com/blog/2011/11/15/documenting-architecture-decisions） |
| Buildroot は同じ `O=` のパスでなければ同一の出力にならない | Buildroot `BR2_REPRODUCIBLE` の help |
