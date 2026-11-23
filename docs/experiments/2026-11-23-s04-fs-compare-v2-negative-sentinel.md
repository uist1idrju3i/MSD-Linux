# S4参考: T1-negative-finalの同期済みsentinel診断

## 目的と採用範囲

[第4段Aの試行05](2026-11-19-s04-fs-compare-v2-stage4.md#試行05の全smoke停止)で、F2FSの復旧後にfsyncしていない2 fileがともに消え、負対照を作れず停止した。負対照を専用sentinelへ固定する。同期していない通常fileはそのままにして、消失の観察を続ける。

これは試験器の回帰診断であり、性能・容量・実機durabilityの比較ではない。製品設定とvendorは変更しない。試行05の失敗を成功へ書き換えず、修正後の全851件とmain runは未実施として残す。[CSV](2026-11-23-s04-fs-compare-v2-negative-sentinel.csv)も参照。

## 実装と事前の判定基準

実行commitは`3a27872d9d6f3a44a9838b00d03698c187d3f795`。`fs-compare-guest`は`T1-negative-final`の準備時だけ、workload root直下に`.t1-negative-sentinel`を作り、fileと親directoryを順にfsyncする。期待hashは書き込むpayloadから求め、`/data/fs-compare/<RUN_ID>/T1-negative-sentinel.tsv`へ記録する。`/data`は[S02msd-data](../../board/cardputerzero/rootfs-overlay/etc/init.d/S02msd-data)がext4でmountするデータ領域（既定は`/dev/mmcblk0p7`）で、RAMではない。期待値は[guest](../../board/cardputerzero/tools/bench/fs-compare-v2/fs-compare-guest)の`RUN_PATH`直下、再生対象のfilesystemをmountする`RUN_PATH/mount`の外に保存するため、そのfilesystemの再生対象には含まれない。通常workloadを始める前に完了し、通常fileの`--no-fsync`は維持する。

復旧後は元の期待値を使って、同じ`check_t1_manifest`でsentinelの存在とhashを先に確認する。欠損・破損、期待値の欠損・空・不正を成功やskipにしない。成功した場合だけ、期待値の写しのhash先頭を変更し、同じ判定器が`hash_mismatch`で拒否することを要求する。元の期待値とsentinelは変更しない。対照の拒否をdata消失件数へ加えない。

事前に3構成各1回とし、`preflight.py diagnose`がすべて終了値0、`mount=yes fsck=0 negative_control=yes`になることを基準にした。元のsentinelが不正、または改変した写しを判定器が受理した場合は失敗とする。繰返しは機能経路の確認だけを目的とするため各1回で、性能比較の5回反復を代替しない。

## 入力と手順

- 構成は[構成表](../../board/cardputerzero/tools/bench/fs-compare-v2/fs-compare-configs.tsv)のF1・E1・E2。`smoke-profile.json`のW1=2、W2=2、W3=51、W4=65536 byteを変更しない。
- SDKは試行05のbuild commit `12b5c744bb62714284e038ca67f57cb0cface785`、Buildroot `bbbdab36565d4941b6b0449a0eedb5aac8a10c2e`を再使用した。kernel releaseは`6.18.64-v8`。fresh full buildはしていない。
- SDKの`.config`、Image、rootfs.squashfs、sdcard.img、workload、replay-logの6入力は、試行05と3診断でhash一致を確認した。guestを含むharnessは実行commitから採り、SDKの6入力は変更していない。各診断の`environment.json`に入力hashとtool版、`inputs.sha256`とharnessの写しに実行内容がある。
- 3診断は独立した出力先とcontainerで並行実行した。経過秒はsetupを含み、速度の優劣には使わない。既存出力は上書きしない。

最初の`diagnose-F1`・`diagnose-E1`・`diagnose-E2`は、すべて約1.3秒で事前確認に失敗した。SDKのmksquashfs wrapperが`/work/output-fscmp-v2-05/host/bin/mksquashfs.orig`を固定参照し、移動先から解決できなかったためである。QEMU起動前の失敗として保存した。SDKを変更せず、診断用checkout内の未使用の`output-fscmp-v2-05`をSDKへのsymlinkにして、元のcontainer内pathを復元した。再試行は`diagnostics-02/`以下の新しい出力先とした。

保持したSDKを使う場合の呼出しは次のとおり。`SDK`は取得したSDKの絶対pathにする。固定wrapperがある場合は先に上述のsymlinkを作る。`OUTPUT_DIR`を渡すと`docker/msd-dev`がSDKを同じ絶対pathへbind mountする。

```sh
OUTPUT_DIR="$SDK" docker/msd-dev python3 \
  board/cardputerzero/tools/bench/fs-compare-v2/preflight.py \
  diagnose F1 T1-negative-final output-fscmp-sentinel-replay-01/F1
```

E1・E2も構成名と新しい出力先を指定する。plan、3本の正確なcommand、時刻、終了値は証拠内の`verification/run-diagnostics-02.py`と`diagnostics/diagnostics-02/diagnostic-plan.json`、各host JSONに残した。

## 結果

```text
Ran 68 tests in 14.830s
OK
```

host試験は通常fileが全部消失、一部残存、sentinelの欠損・破損、期待値の欠損・空・不正、改変を受理する壊れた判定器を含む。fileと親directoryのfsync順序、fsync失敗時に期待値を公開せず停止することも確認した。

| 構成 | 終了値 | mount | fsck | 通常manifest | loss_points | 負対照 | 経過秒 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| F1 | 0 | yes | 0 | no | 1 | yes | 312.90877524600364 |
| E1 | 0 | yes | 0 | no | 1 | yes | 342.6786937269935 |
| E2 | 0 | yes | 0 | yes | 0 | yes | 346.15983709799184 |

3構成とも、元のsentinelのhashは`a41bd44cc8a0b3cee64e09c35f1a62460045eca3c6d7763cf2e9cbcbc16032be`。改変した写しの`041b...`は、`context=negative_control path=.t1-negative-sentinel reason=hash_mismatch`で拒否された。通常manifestの欠損を許容する負対照の意味は変えていない。3本ともQMP quit、process回収、終了値0、fallbackなしだった。

## 証拠の取得と照合

orphan branch `data/fs-compare-experiments`のcommit `03b03956647fbc4eb5a8ae07ad914ff5e65811fd`に、試行05のtext、host PIDと終了値、修正後の診断、事前確認失敗、host試験、実行scriptを保全した。このbranchはmergeも削除もしない。

| `fs-compare/`以下のfile | SHA-256 |
| --- | --- |
| `stage4-negative-sentinel-01.tar.zst` | `2129bcac5b560635833015ac8869e3dd4b34a6e654695f232b037eedc7abd6d0` |
| `stage4-negative-sentinel-01.files.sha256` | `b8901cbac424c523d6dcb80103e5601fd7b3b962f622120c56218577866cff3d` |
| `stage4-negative-sentinel-01.selection.json` | `030c9e98674229e633646dd1ee07b395bb74aff493ae176daecb29421dd02b15` |

原本tarのSHA-256を照合してからUTF-8のtextを選び、圧縮後に5291 fileのhashと長さを再照合した。98個のbinary・非UTF-8 entryを除外した。新診断のbuild tree、storage archive、disk image、key fileも収録しない。除外と選択の規則、原本hashはselection JSONにある。private key・TLS session keyのscanも行った。圧縮にはhostのZstandard 1.5.7を使用した。固定開発containerにzstd CLIが無く、圧縮の呼出しだけhost toolへ切り替えた。

```sh
git fetch origin data/fs-compare-experiments
mkdir output-fscmp-sentinel-evidence-01
git archive 03b03956647fbc4eb5a8ae07ad914ff5e65811fd fs-compare \
  | tar -x -C output-fscmp-sentinel-evidence-01
cd output-fscmp-sentinel-evidence-01/fs-compare
sha256sum -c SHA256SUMS
tar --zstd -xf stage4-negative-sentinel-01.tar.zst
sha256sum -c stage4-negative-sentinel-01.files.sha256
```

## 未確認

修正後の851件の全smoke、main run、full buildは未実施。実機のSD・FTL・物理電断、LCD・keyboard・I2Cは未確認であり、今回のQEMU成功で代替しない。
