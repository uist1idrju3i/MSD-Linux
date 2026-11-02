# zizmorの配布物選択とビルドキャッシュの確認

- 状態: ローカルの配布物照合は完了。新しいOCIの構築とnative CIは確認中
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

wheel限定の削除、pip cache無効化の削除、cache除去の削除、除去を別RUNへ移動、offline監査の削除という5変異は、いずれも回帰試験が失敗して検出した。arm64 hashを落としたrequirementsでのoffline選択もhash不一致で失敗した。検査器のこの反応を確認してから、通常入力の結果を採用した。

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

## 失敗した試行と未確認の点

- 最初のoffline選択はrequirementsをcontainerへ渡し忘れ、file not foundで失敗した。明示的なread-only mountを加えた再実行と区別する。
- 開発用OCIにはhadolintが入っていない。OCI内で呼んだ試行はcommand not foundで失敗し、workflowと同じ固定hadolint imageでの確認へ切り替える。
- 新しいOCIのnative両CPUでの構築、cache消失・scan結果は確認中。Brotliによるゲート失敗を成功扱いしたり、検出除外で隠したりしない。

## 元ログの同一性

CIのartifactとjob logから再取得できる。元Trivy JSONは保存・公開せず、既存の選別済みJSONだけを比較した。privateなパスや秘密値はこの記録へ転記していない。

| 取得物 | SHA-256 |
|---|---|
| 変更前arm64 artifact zip | `5df2b4f096f0af2b82473d8a89beb0a381f9d8cbd99344988eaf4b00e47d1d25` |
| 変更前arm64 job log | `1e795e9af5e4ccede5f8eedf3c065d08cb95ce4e3bd284f37ba9e5d6d0ed21a8` |
