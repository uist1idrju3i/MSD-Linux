# zizmorの配布物選択とビルドキャッシュの確認

- 状態: 配布物選択・cache除去・offline監査の確認は完了。Brotliによる公開阻止は継続
- 日付: 2026-11-02
- 担当: Devin
- 関連: [開発用OCIの監視](../research/development-image-security.md)、[CI監査PR](https://github.com/uist1idrju3i/MSD-Linux/pull/185)

## 目的と判定基準

arm64の最終OCIに残ったRustビルド用キャッシュを、実行バイナリーの依存と分けて調べる。両CPUで同版のhash固定wheelを選び、ソースビルドへ暗黙に戻らず、installと同じレイヤーでキャッシュを除去した後もzizmorのoffline監査を実行できることを採用条件とする。Brotliの版、Trivyの公開ゲート、除外規則は変更しない。

これは構築・検査の可否を確認する試験であり、速度・容量の性能比較ではない。配布物選択は各CPUで5回、OCIの構築は各CPUで1回を基本とする。後者はCIのコマンド・終了状態・生成物を確認するための回数であり、統計的な性能の結論には使わない。

## 基準と一次資料

| 項目 | 値 |
|---|---|
| 変更前commit | `ad7b88a307e7f5cebe96bef32ca06109c5d51615` |
| 変更前arm64のCI | [run 41499766995](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/41499766995/job/125466380606) |
| 変更前artifact | [13169865900](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/41499766995/artifacts/13169865900) |
| 変更前arm64 image ID | `sha256:eb04a3107c3d61b11d322062e50eaa3d910acec1a9cf7f6d2786257ee09ac7df` |
| Trivy / DB UpdatedAt | `0.76.1` / `2026-11-02T13:15:56.441126560Z` |
| ローカルの配布物選択 | 固定OCIのPython 3.13・pip、networkなし、各CPUで5回 |
| 変更しない版 | zizmor `1.31.1`、Debian snapshot、base image、QEMU、Buildroot、GCC、kernel |
| PyPIの配布物・hash | [1.31.1のJSON](https://pypi.org/pypi/zizmor/1.31.1/json) |

変更前arm64のログは、`zizmor-1.31.1.tar.gz`の取得とwheelのローカル構築を示す。requirementsにはamd64 wheelとsdistのhashしかなく、公開済みarm64 wheelのhashは入っていなかった。PyPIの実ファイルを取得し、metadataのSHA-256と照合した。

| 配布物 | SHA-256 | 確認したlicense |
|---|---|---|
| `manylinux_2_28_x86_64.whl` | `58e878eb2dbd2c6183c105e1ac28c14f7dd1eca44a783f1fe2a69647d012c410` | METADATAのMIT、同梱LICENSE |
| `manylinux_2_24_aarch64.whl` | `d9b36840c560a8abe39d9ef3d077239aabf6d572c5c2b629c970592a617dbf6f` | METADATAのMIT、同梱LICENSE |
| `zizmor-1.31.1.tar.gz` | `eb9c8a3e2c1080810fdb68bc36717b2a9d61283bb98e3a48689f5a852fc48e9f` | 既存のsource配布物。今回OCIでは選択不可 |

版は変えず、同版のarm64 wheelを許可する。wheelの内部依存までライセンス審査を完了したという意味ではない。

## キャッシュのlockfileとsourceの照合

変更前のblocking検出39件のうち、1件はDebianのBrotliで、38件は`root/.cache/puccinialin/cargo/registry/src/`内のCargo.lockを対象としていた。これは最終OCIに不要なsource・toolchainのキャッシュが残っていた証拠であり、実行バイナリーに38件が到達可能という証拠ではない。

sdistのroot Cargo.lockは451 packageで、SHA-256は`7dca47e1169d952ecfdca9cc3c9517f605c7ae7527f9f44ff491c06da1d076ff`だった。[全38照合](2026-11-02-zizmor-cache-blockers.csv)のpackage名・検出版をこのlockfileと比較すると、同じ名と版の組は0件だった。例えば、cache内の`aws-lc-sys 0.29.0`などに対しroot lockfileは`0.41.0`、`quinn-proto 0.11.14`に対して`0.11.16`だった。

この比較はsourceのlockfileとの対応だけを示す。旧OCIで構築されたbinaryや公式wheelが、そのlockfile・feature・compilerだけで作られたことを証明していない。両wheel内のELFは`libgcc_s`、`libpthread`、`libm`、`libdl`、`libc`をNEEDEDに持つ。静的に組み込まれたRustコードはこの一覧だけでは判定できないため、全runtime依存の安全性や到達性を確認済みとはしない。

## 変更と回帰試験

- requirementsへarm64 wheelのhashを追加する。sdistのhashは既存のほかの利用者向けに残すが、OCI内では`--only-binary=:all:`により選択できない。
- pipへ`--no-cache-dir`を指定し、installと同じRUNで`/root/.cache`を除去する。後のレイヤーで隠すだけの削除にはしない。
- 除去後、最小workflowをstdinからzizmorのoffline監査へ渡す。これは各CPUの実際のDocker buildで実行する。
- `tests/msd-dev/run.sh`で、hash固定、wheel限定、pip cache無効化、同一RUN内の削除と存在検査、削除後のoffline監査を要求する。

wheel限定の削除、pip cache無効化の削除、cache除去の削除、除去を別RUNへ移動、offline監査の削除という[5変異](2026-11-02-zizmor-mutations.csv)は、いずれも回帰試験が失敗して検出した。arm64 hashを落としたrequirementsでのoffline選択もhash不一致で失敗した。検査器のこの反応を確認してから、通常入力の結果を採用した。

## ローカルの配布物選択

両wheelをPyPIから取得して公開SHA-256と照合し、取得済みファイルだけをread-onlyで渡す。次のコマンドを各CPU・独立した出力先で5回実行した。`$PLATFORM`はarm64で`manylinux_2_24_aarch64`、amd64で`manylinux_2_28_x86_64`とする。

```sh
python3 -m venv "$OUT/venv"
"$OUT/venv/bin/pip" download --only-binary=:all: --require-hashes \
  --no-index --find-links="$WHEELS" --platform="$PLATFORM" \
  --python-version=313 --implementation=py --abi=none \
  --dest="$OUT/selected" -r .github/zizmor-requirements.txt
sha256sum "$OUT/selected/"*.whl
```

[10回の生の値](2026-11-02-zizmor-wheel-selection.csv)は、両CPUで各5回とも対応するwheelのhashと一致した。これはforeign platformの配布物選択の確認であり、ローカルでarm64 binaryを実行した確認ではない。

## 新しいOCIとnative両CPUの結果

Docker入力が`inputs-fcf14a3abc4d89ac`の変更commit `7632e6af9dc31b9af0e33cf9c1f4f0b64594bfae`を確認した。ローカルamd64もDockerfile全体から新規構築し、Python `3.13.5`とzizmor `1.31.1`を実行した。実行ファイルのSHA-256はwheelから取り出したものと同じ`5c7ded5347e2f3c96046457668405dffbceda2ad065a26abd59717252c51686f`である。

ローカルimage IDは`sha256:c813692f2419472f753fb50531f3d446354eb1aff7005869d1142792ccafc5d9`だった。networkなしで起動し、cacheが監査の前後に存在せず、offline監査の結果が空配列になることを[5回確認](2026-11-02-zizmor-runtime.csv)した。同じimageのTrivy検出は2,184件、blockingはBrotliの1件で、cache由来は0件だった。公開ゲート用コマンドも終了状態1を返した。

native CIの結果は次のとおり。[全列のCSV](2026-11-02-zizmor-image-scans.csv)にはimage ID、commit、入力tag、DB更新時刻、全分類の件数、終了状態、artifactを保存した。

| native CPU | 実行ログ | artifact | 脆弱性records | cache由来 | blocking | 公開前検査 |
|---|---|---|---:|---:|---:|---|
| amd64 | [job 125487769747](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/41506689803/job/125487769747) | [13170394999](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/41506689803/artifacts/13170394999) | 2,184 | 0 | 1 | Brotliで終了状態1 |
| arm64 | [job 125487769751](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/41506689803/job/125487769751) | [13172071043](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/41506689803/artifacts/13172071043) | 2,179 | 0 | 1 | Brotliで終了状態1 |

両jobの構築ログは対応するwheelの取得、cache除去と存在検査、その後のzizmor `1.31.1`によるoffline監査の成功を示す。artifactの選別済み全件JSONとTrivyの版・DBも読んだ。credential ruleとmisconfigurationの検出は両方0件だが、これだけで秘密情報や設定不備の不存在を証明したとはしない。

DBの更新時刻は変更前後で同じだった。旧arm64にあったcache由来141 records・うちblocking 38件がなくなった。実行バイナリーの141件の脆弱性を修正した、とは解釈しない。両CPUに残ったblockingは、同じ`libbrotli1 1.1.0-2+b7`の`CVE-2026-111497`だけである。延期したBrotliを更新せず、ゲートを緩めず、公開を止めた状態を維持した。

この結果の対象は開発用OCIであり、配布OSや実機の機能確認ではない。image IDの一致による構築のbit再現性も検証していない。

## 失敗した試行と未確認の点

- 最初のoffline選択はrequirementsをcontainerへ渡し忘れ、file not foundで失敗した。明示的なread-only mountを加えた再実行と区別する。
- 開発用OCIにはhadolintが入っていない。OCI内で呼んだ試行はcommand not foundで失敗し、workflowと同じ固定hadolint imageでの確認へ切り替える。
- 上流wheelの再ビルド照合、全Rust featureの到達性、実行バイナリーからの完全な依存抽出は行っていない。

## 元ログの同一性

CIのartifactとjob logから再取得できる。元Trivy JSONは保存・公開せず、既存の選別済みJSONだけを比較した。privateなパスや秘密値はこの記録へ転記していない。

| 取得物 | SHA-256 |
|---|---|
| 変更前arm64 artifact zip | `5df2b4f096f0af2b82473d8a89beb0a381f9d8cbd99344988eaf4b00e47d1d25` |
| 変更前arm64 job log | `1e795e9af5e4ccede5f8eedf3c065d08cb95ce4e3bd284f37ba9e5d6d0ed21a8` |
| 変更後arm64 artifact zip | `48cb12613935265eb35ba1c5f6420bfcad946ca5eeca237aca3b48b30885df4c` |
| 変更後arm64 job log | `ad2413d145cb56528a7ce6a5863e046d8e2d896401725ac69c51f75c3f3f61bc` |
| 変更後amd64 artifact zip | `9a4f389354e6a28954524769fb20fce1f466a393b2e6dcdd47f93de9dd20db2f` |
