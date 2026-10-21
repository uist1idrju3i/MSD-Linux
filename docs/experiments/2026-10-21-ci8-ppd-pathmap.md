# CI #8 PPD 成果物の埋め込み path 残差

- 状態: 完了（CI #8 の成果物基準 3 を満たした）
- 日付: 2026-10-21
- 担当: Devin
- 関連: [CI 高速化 C1 の比較](2026-10-21-ci8-ppd-ci.md)、[非 PPD 対照 build](2026-10-21-ci8-ppd-control.md)

## 目的と事前登録

CI #8 の PPD（per-package directories）比較では、`v4l2-compliance` と `v4l2-ctl` の `.rodata` に、埋め込み host path とその NUL padding を取り除いた後も差が残った。この実験では、残差が build tree ごとの揺らぎではなく、libv4l の Meson build に埋め込まれる host path の長さだけで説明できるかを調べた。

事前登録 v1 は結果を見る前に作成された。元文書の SHA-256 は `f0347714c7f6236bc357029e0025cc70db90c8ad0cabd43feee7a75b3d4a7149` である。実験後に結論や基準を変更していない。

### 事前登録 v1

事前登録では、非 PPD の `/work/output/host` と PPD の `/work/output/per-package/libv4l/host` に埋め込まれる GCC header path の長さの差が、残差の原因かを問うた。末尾の `/` を含む prefix はそれぞれ 19 文字と 38 文字で、差は 19 文字である。元の登録では末尾の `/` を除いた長さを 18 文字と 37 文字と記した。

対象 tree は、非 PPD の `ci8-base`（HEAD `ce932cd0e83ebf10be853c51d9ae09116aea92bb`）と PPD の `ci8-ppd`（HEAD `d64fa9188820d4e7875704ffdcd6c73db14064ac`）である。HEAD 間の `configs`、`package`、`vendor` には差がない。Buildroot source の commit は両 tree とも `d6061d653d7fb215c2409c59e4bfad1b9d677215` である。`output/.config` の SHA-256 を各 run 前後で記録し、変更がないことを判定条件とした。

P0 は flags を変えずに両 tree で 2 回ずつ `libv4l-dirclean` と full `make` を行う sanity 条件とした。以前と同じ、変更していない残差解析 script で `v4l2-compliance` の未対応 interval 44 件 / 217 B、`v4l2-ctl` の未対応 interval 8,536 件 / 11,669 B が再現しなければ、P1 を始めず停止する計画だった。

P1 は両 tree で 2 回ずつ rebuild し、Meson cross file に flag が入り、対象 binary に map 前の host path が残らないことを確かめる計画だった。登録した flag は次のとおりである。

```sh
LIBV4L_CFLAGS='$(TARGET_CFLAGS) -ffile-prefix-map=/work/output/host=/HOST'
LIBV4L_CXXFLAGS='$(TARGET_CXXFLAGS) -ffile-prefix-map=/work/output/host=/HOST'
```

PPD tree では `/work/output/host` を `/work/output/per-package/libv4l/host` に置き換える。対象は `cec-compliance`、`cec-follower`、`edid-decode`、`v4l2-compliance`、`v4l2-ctl`、`v4l2-dbg` の 6 binary で、SHA-256、section 差分、同一 tree 内の repeat の一致を調べる計画だった。判定基準は、P1 の base と PPD の全 6 binary が byte-identical なら、残差は path length で説明でき、CI #8 の成果物基準 3 を満たすこととした。P1 が一致しても、製品 build 自体に map flag を入れない場合は製品 binary が path length に応じて異なることも、事前登録に含めた。

### Amendment 1（2026-10-21T14:51:23Z）

最初の PPD P0 full `make` は、`output/target/etc/init.d` に `S01seedrng` と `S05seedrng` が同時に存在し、`post-build.sh` の検査で失敗した。Amendment 1 は、失敗した log と `S01seedrng` の copy/hash を保存し、PPD target から既存の `S01seedrng` だけを除いて P0 を再試行する手順を定めた。この amendment の SHA-256 は `ab522fe5ae7459a3febc10afa7c16f5c7bd35eab05c736563f86634862f811c3` である。

この retry も失敗した。`target-finalize` が per-package staging から `S01seedrng` を再び target に merge したため、`S05seedrng` との重複が解消しなかった。両失敗試行は残し、P1 はまだ開始しなかった。

### Amendment 2（両 PPD P0 失敗後、P1 build 前）

Amendment 2 は、原因が libv4l ではなく、PPD で `target-finalize` が既存 `output/target` に per-package target を merge することと、`board/cardputerzero/post-build.sh` の seedrng 改名処理が再実行に対して冪等でないことにあると整理した。単一ファイルを手作業で除く方法をやめ、各 PPD full `make` 前に `output/target` の file list と SHA-256 を保存し、`output/target` 全体を削除して target-finalize に per-package directory から再構築させる手順へ変更した。非 PPD tree は target 全体を削除しない。Amendment 1 の試行は失敗として保持し、残りの P0 と P1 の条件は変更しない。

Amendment 2 の SHA-256 は `1e20ba35a9cbe04560ae1b51d5feb23e12a1a0dbeb2c0f44a3eff452dbe0256b` である。Amendment 2 で初めて PPD P0 の r1/r2 が成功し、事前登録の P0 gate を通過した。

## 条件と環境

| 項目 | 条件 |
|---|---|
| 非 PPD tree | HEAD `ce932cd0e83ebf10be853c51d9ae09116aea92bb` |
| PPD tree | HEAD `d64fa9188820d4e7875704ffdcd6c73db14064ac` |
| Buildroot | 2026.08、submodule commit `d6061d653d7fb215c2409c59e4bfad1b9d677215` |
| target GCC / G++ | 14.3.0 |
| 対象 package | libv4l / v4l-utils 1.32.0 |
| build 実行 | `docker/msd-dev` 内で output を `/work/output` として使用 |
| QEMU | 使用していない |
| 変えた条件 | P1 のみ C/C++ flags に `-ffile-prefix-map` を追加 |
| 固定した条件 | HEAD、Buildroot submodule、`.config`、libv4l version、対象 binary |
| repeat | P0 と P1 を各 tree で 2 回。SHA-256 による完全一致を比較 |

実験時の host OS version は保存記録に含まれていないため、ここでは補完しない。

`output/.config` の SHA-256 は base が `cbf7336ea92ece2417e9e1f7d53b1410c1b18e6e5070c3836594af6b29efb848`、PPD が `8f4a98b9684b5210950d53dcff2ee094a5d9f8f78a69e7d48f171fc18ee2675e` であり、開始時、P0、P1、復元後でそれぞれ不変だった。PPD 設定の `BR2_PER_PACKAGE_DIRECTORIES=y` は実験前から存在した。

Buildroot の `toolchain/toolchain-wrapper.mk:27` では、`BR2_REPRODUCIBLE=y` の GCC 8 以降に `-ffile-prefix-map=$(BASE_DIR)=buildroot` を加える。これは `BASE_DIR` を map するだけであり、PPD の suffix `per-package/libv4l/host` は残る。そのため、この flag だけでは今回の tree 間 path length の差をなくさない。

## 手順

各条件・repeat で `libv4l-dirclean` の後に full `make` を行った。P0 と復元では map flag を渡さず、P1 では次の環境変数を使った。

```sh
# 非 PPD P0、または P0 復元
docker/msd-dev bash -c 'unset LIBV4L_CFLAGS LIBV4L_CXXFLAGS; make -C /work/output libv4l-dirclean && make -C /work/output'

# PPD P0、または P0 復元。各 full make の前に target の file list と
# SHA-256 を保存し、output/target を丸ごと削除する。個別 file は削除しない。
: "${RUN_DIR:?set RUN_DIR to a unique, writable host directory}"
{
  docker/msd-dev bash -c 'cd /work/output && find target -type f -printf "%P\n" | sort'
  docker/msd-dev bash -c 'cd /work/output && find target -type f -print0 | sort -z | xargs -0 sha256sum'
  docker/msd-dev bash -c 'cd /work/output && find target -type l -printf "%P -> %l\n" | sort'
} > "$RUN_DIR/pre-target-manifest.txt"
docker/msd-dev bash -c 'rm -rf /work/output/target && unset LIBV4L_CFLAGS LIBV4L_CXXFLAGS && make -C /work/output libv4l-dirclean && make -C /work/output'

# 非 PPD P1。flags は docker/msd-dev の内側で full make に渡す。
docker/msd-dev bash -c "make -C /work/output libv4l-dirclean && \
  LIBV4L_CFLAGS='\$(TARGET_CFLAGS) -ffile-prefix-map=/work/output/host=/HOST' \
  LIBV4L_CXXFLAGS='\$(TARGET_CXXFLAGS) -ffile-prefix-map=/work/output/host=/HOST' \
  make -C /work/output"

# PPD P1。target manifest を保存後、target 全体を削除してから実行する。
{
  docker/msd-dev bash -c 'cd /work/output && find target -type f -printf "%P\n" | sort'
  docker/msd-dev bash -c 'cd /work/output && find target -type f -print0 | sort -z | xargs -0 sha256sum'
  docker/msd-dev bash -c 'cd /work/output && find target -type l -printf "%P -> %l\n" | sort'
} > "$RUN_DIR/pre-target-manifest.txt"
docker/msd-dev bash -c "rm -rf /work/output/target && \
  make -C /work/output libv4l-dirclean && \
  LIBV4L_CFLAGS='\$(TARGET_CFLAGS) -ffile-prefix-map=/work/output/per-package/libv4l/host=/HOST' \
  LIBV4L_CXXFLAGS='\$(TARGET_CXXFLAGS) -ffile-prefix-map=/work/output/per-package/libv4l/host=/HOST' \
  make -C /work/output"
```

`docker/msd-dev` は任意の host 環境変数を container に渡さないため、P1 の flags は container 内の full `make` に直接設定する。各 run の `.config` と 6 binary の SHA-256 を保存した。PPD run では target manifest を先に保存し、manifest の後で target 全体を削除した。P1 の cross file で C/C++ 両方の flag を確認し、各 binary の `strings` 出力から map 前の host path を検索した。P0 の残差解析では、事前登録で指定した `analyze_residuals.py` と `trace_references.py` を実験時点の内容のまま使った。

残差解析で使った section 抽出は `aarch64-linux-objcopy -O binary --only-section=.rodata/.data/.data.rel.ro`、ELF 情報は `aarch64-linux-readelf -W -S -d --dyn-syms -W`、disassembly は `aarch64-linux-objdump -d --no-show-raw-insn` によるものだった。解析時は instruction address と symbol offset、hex address/immediate を正規化した。decimal immediate は正規化せず、別途 `ldr` の bracket operand にある decimal offset を mask して差分が残るかを調べた。

### 変更後 script による P0 再解析

VM 固有 path を除くため、記録に添付する 2 script では `ROOT` と `OUT` の設定だけを環境変数対応にした。解析関数と判定処理は変更していない。元の script と添付版の SHA-256 は次のとおりである。

| script | 元の SHA-256 | 添付版 SHA-256 |
|---|---|---|
| `analyze_residuals.py` | `91b5890a1316d251f95aabf8292351f6211e30fe64d1ddeb7d3dddc6537d0ea8` | `3a4e8935ce71f4a8dc9296ed6b30da28992e583c73686caabea7308670e4fcc1` |
| `trace_references.py` | `482193bb617fd48a468a8fb555a766b61f07fecea4f1a57fae36f42674c3ce1a` | `16832e8ae60f6ffe9838890fc839857349e38ffba514f347db03f7b478642a01` |

変更行の差分は次のとおりである。元の `ROOT` に設定されていた VM 固有の絶対 path は、この記録には含めない。両 script に `import os` を追加し、`ROOT` と `OUT` の設定を同じ方法で変更した。

```diff
+import os
-ROOT = Path("<VM 固有の絶対 path>")
-OUT = ROOT / "rodata-residual"
+ROOT = Path(
+    os.environ.get(
+        "PPD_PATHMAP_ROOT", str(Path(__file__).resolve().parent / "inputs")
+    )
+)
+OUT = Path(os.environ.get("PPD_PATHMAP_OUT", str(ROOT / "rodata-residual")))
```

添付した `run-analysis.py` driver を P0 の保存済み `.rodata` inputs と、同じ binary に対応する保存済み `readelf` / disassembly inputs で実行した。変更後 script の出力と元の `analysis-output` の 10 file を `diff -ru` で比較した結果、差は 0 file で、終了 status は 0 だった。再解析でも `v4l2-compliance` の 44 interval / 217 B と `v4l2-ctl` の 8,536 interval / 11,669 B が得られた。出力は `p0/amendment2/reanalysis-output/` に保存した。driver は再現用に今回追加したものであり、元の P0 / P1 build の実行には使っていない。Buildroot build は再実行していない。

## 結果

### P0 gate

変更していない解析 script で、事前登録どおりの残差が再現した。`v4l2-compliance` は common interval 69 件のうち 25 件が mapped、44 件が未対応で、未対応 byte は 217 B だった。`v4l2-ctl` は common interval 8,614 件のうち 78 件が mapped、8,536 件が未対応で、未対応 byte は 11,669 B だった。P0 gate は **PASS** であり、P1 へ進んだ。

P0 の base r1/r2 は全 6 binary で一致し、開始時の hash とも一致した。PPD r1/r2 も全 6 binary で一致し、開始時の hash と一致した。現在の P0 `v4l2-compliance` と `v4l2-ctl` から新たに抽出した `.rodata` は、解析に使った既存入力と byte-for-byte で一致した。

### P0 section 比較（base と PPD）

以下の `unequal positions` は section 内で異なる byte 位置の数である。`.rodata` raw `cmp -l` は path と padding を除く前の件数である。

| binary | `.rodata` サイズ base → PPD、raw差分、path 除去後 | `.data` サイズ、差分位置数 | `.data.rel.ro` サイズ、差分位置数 |
|---|---|---:|---:|
| `cec-compliance` | 49,299 → 49,315 B（+16）、raw 14,780、path/padding 除去後は一致 | 2,056 B、0 | 5,984 B、209 |
| `cec-follower` | 26,400 → 26,416 B（+16）、raw 16,193、path/padding 除去後は一致 | 640 B、0 | 47,472 B、1,179 |
| `edid-decode` | 113,737 → 113,753 B（+16）、raw 87,479、path/padding 除去後は一致 | 5,968 B、636 | 5,328 B、391 |
| `v4l2-compliance` | 96,668 → 96,684 B（+16）、raw 87,561、common prefix に 217 B 差と 8 B tail 差 | 1,256 B、59 | 3,872 B、229 |
| `v4l2-ctl` | 116,500 → 116,532 B（+32）、raw 93,244、common prefix に 11,669 B 差と 8 B tail 差 | 10,392 B、286 | 7,968 B、656 |
| `v4l2-dbg` | 22,458 → 22,474 B（+16）、raw 17,383、path/padding 除去後は一致 | 712 B、43 | 11,000 B、514 |

shared library `ARIB-STD-B24.so` と `EN300-468-TAB00.so` では `.rodata` と `.data` が一致し、`.dynstr` だけが path length と同じ 19 B 増えた。全対象で `NEEDED` set と dynamic symbol name set は一致した。正規化した disassembly は `ldr` の decimal offset だけに差が残り、その offset を mask すると差は 0 行になった。

### P1

P1 の base r1/r2、PPD r1/r2 の SHA-256 は、6 binary 全てで同じだった。したがって、P1 の base と PPD は binary 全体が一致し、section 単位でも差はない。P0 から P1 への変更は両 tree の全 6 binary で確認された。hash の全 run 一覧は同名 CSV と一致する。

4 つの P1 cross file の `c_args` と `cpp_args` には登録した tree 別の `-ffile-prefix-map` が入った。base r1/r2 と PPD r1/r2 のそれぞれで 6 binary を `strings` 検査し、未 map path は見つからなかった。証拠は `p1/{base,ppd}/{r1,r2}/cross-file-flag-evidence.txt` と `strings-check.txt` に保存した。

PPD の P0・P1 各 repeat では `output/target/etc/init.d` に `S05seedrng` だけがあり、その内容は base 側と一致した。両方の SHA-256 は `8cf53d7f3533b38b420f998dae1087ca3ac51579fe10baaf53f5614941a10c8b` だった。

### P0 と P1 の binary SHA-256

CSV は P0/P1 の全 repeat について、6 binary と `.config` の SHA-256 を 1 行ずつ記録する。P0 の同じ tree 内 r1/r2 は一致し、P1 は base/PPD ともに r1/r2 が全て一致した。

## 失敗した試行と副次の発見

PPD の最初の P0 full `make` と Amendment 1 の retry はどちらも `target-finalize` の duplicate guard で終了コード 2 となった。両 log は削除せず、後述の hash とともに保持している。Amendment 2 の手順で target 全体を作り直した P0 r1/r2、P1 r1/r2、最終復元は成功した。

`board/cardputerzero/post-build.sh:76-84` は `S01seedrng` があれば `S05seedrng` に改名する一方、両方があれば失敗する。PPD の2回目以降の full `make` では、per-package staging から `S01seedrng` が再 merge され、既存の `S05seedrng` と重なって失敗する。CI は毎回新しい build tree から build するため、この incremental build の問題は CI の今回の run には影響しなかった。PPD を採用する前に post-build 処理を修正する必要がある。

## 復元

両 tree で flags なしの full `make` を行い、P0 の状態に戻した。復元後の base/PPD の 6 binary と `.config` はそれぞれ P0 r1/r2 と完全一致した。復元した PPD target にも `S05seedrng` だけがあり、base 側と byte-for-byte で一致した。復元の確認は `restore/restoration-verification.txt`、PPD seedrng の証拠は `restore/ppd/seedrng-check.txt` にある。

## 結論

P1 では map 前の host path が 6 binary から消え、base と PPD の全 6 binary が repeat 間・tree 間で byte-identical になった。P0 で再現した `v4l2-compliance` の 217 B と `v4l2-ctl` の 11,669 B の残差は、埋め込まれる host path の長さだけで説明できる。**CI #8 の事前登録にある成果物基準 3（差が全て説明できること）を満たした。**

製品 build には今回の `-ffile-prefix-map` を入れない。そのため PPD を使う場合、製品 binary は埋め込まれる path length に応じて異なる byte 列になる。`BR2_REPRODUCIBLE` の `$(BASE_DIR)=buildroot` map では per-package 部分が残り、この問題は解消しない。PPD の採否は利用者が判断する。判断に先立ち、前述の post-build seedrng 処理を修正する必要がある。

## 限界

- P1 は対象の libv4l build に `-ffile-prefix-map` を足した診断条件であり、製品 build の条件ではない。
- 結果は指定した 6 binary と関連 shared library の比較である。全 package や全 root filesystem の再現性を証明しない。
- QEMU と実機の性能・機能試験は行っていない。
- CI が毎回 clean build であることは、この実験の local incremental failure が既存 CI run に影響しないという範囲の確認であり、別の CI 再利用方式には適用しない。

## ログと再生成

大きな build log と target manifest は repository に含めない。保存先での相対 file name、SHA-256、および条件は次のとおりである。各 build は上記の `libv4l-dirclean` と full `make` のコマンドで再生成できる。PPD 条件では Amendment 2 の manifest 保存と target 全体の削除を先に行う。

| 条件 / run | log file | SHA-256 |
|---|---|---|
| P0 base r1 | `p0/amendment2/base/r1/build.log` | `ff9ed28e0b5f98d8fb7ffb5dfce324ff27c480ce25322cc21fbfe48a7c9f63ce` |
| P0 base r2 | `p0/amendment2/base/r2/build.log` | `9e8274d6769754edb303ba9482c3f82c8de9193d7b4b7630679cc22c9034953a` |
| P0 PPD r1 | `p0/amendment2/ppd/r1/build.log` | `972470d4be717c8fe72eae4c194ce73016205bf414b01e0a1519dc8af0df1d55` |
| P0 PPD r2 | `p0/amendment2/ppd/r2/build.log` | `fa87a21d2252c4afd74eb44dab69720b34301f1978854fb61f87c6fe988aa2a1` |
| P1 base r1 | `p1/base/r1/build.log` | `d0c0fc52b942c758629dab2837c5b692cdaa4a11ae758a1bad5ed415eefce8f0` |
| P1 base r2 | `p1/base/r2/build.log` | `b9c0559f2ae155f08ca08a729919363fe887fbed19fc97a226ca8223ff90d9b6` |
| P1 PPD r1 | `p1/ppd/r1/build.log` | `1d31372f59692a737a699aae4c5573611d7a110136d3fd7efc363b2ee649acd7` |
| P1 PPD r2 | `p1/ppd/r2/build.log` | `3213d4e318656b2fbdc83e535fd9b87fdf5be15df6436f5e740a0981374dfdbb` |
| P0 failed PPD initial attempt | `p0/ppd/r1/build.log` | `74a7b748d1fc60e0285d795fff503153646ce9f537861c211c58b26d57b939c7` |
| Amendment 1 failed PPD retry | `p0/ppd/r1-amended/build.log` | `eec42aae0f0567d81034f338430e7e0cb7d3cc619ee015a717d00778ad016813` |
| P0 base restore | `restore/base/build.log` | `a4ed91d2c4d6135e5dd87252441cb27d884d945e8c78dd607afc7419bac518f9` |
| P0 PPD restore | `restore/ppd/build.log` | `b90ce2c50c0e9ff1e80c2295813c73c52101c873edfa213748a04a071ef7f3f0` |
| P0 residual analysis | `p0/amendment2/residual-analysis.log` | `2457769fee5d8a6ae190c1423675e650bc63c54159b47cda1dca45ef97678da9` |

再現用の script は `board/cardputerzero/tools/bench/ppd-pathmap/` に置いた。P0/P1 の比較を再実行する場合は、必要な raw `.rodata`、path-stripped `.rodata`、`readelf`、disassembly inputs を用意してから、[README の手順](../../board/cardputerzero/tools/bench/ppd-pathmap/README.md)に記した driver を使う。分析出力の比較には元の解析出力 directory と別の `--out` を指定する。
