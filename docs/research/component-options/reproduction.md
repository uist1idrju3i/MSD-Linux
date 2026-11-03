# 設定調査の採取元と再生成

[調査の入口](README.md)へ戻る。

## 版と入力の分離

入力のbytes・SHA-256と固定版は[provenance.json](provenance.json)に記録した。本文の主張は、次の別々の証拠に対応する。

1. MSD/Linux `641a6f5d1d31081832a5ea2da04ef89a6d681f4b`と固定Buildroot `8b238854d909c9cce32ef9671d968b03e323b55d`から、新しい作業領域でdefconfigを正規化した。製品のfull buildは行っていない。
2. `make show-vars`のraw/expandedを採取した。対象はconfigure/build/Kconfigのcommand、CONF_OPTS/CONF_ENV、MAKE_OPTS、CFLAGS/LDFLAGS、共通flagsとwrapper等。Makeの全変数ではなく、対象を実行しない展開では`PKG`や`$@`が未解決となる。
3. [CI run 41486595026のartifact](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/41486595026/artifacts/13163313182)から、SBOM、show-info、最終kernel config、legal-infoを読む。新しく正規化した設定と過去のartifactは同一buildの証拠ではない。3入力はzip内の元fileとSHA-256が一致することを確認した。
4. legal-info内のsource archive 56件をindex化し、archiveのhashを残した。SDKのhashはBuildrootの固定hashとも一致した。source・licenseの母集団とSBOM componentは一対一とは限らない。
5. 同じ固定SDKのGCC 14.3.0へ`-Q -Os -mcpu=cortex-a53 --help=common`等を実行。categoryはcommon、warnings、params、optimizers、targetの5つ。`-o`に出た一時出力先の絶対pathは`@GCC_OUTPUT@`に置換した。Buildroot wrapperを通さない照会なので、最終compileの実効値とは区別する。
6. 固定amd64 OCIからAPTの版・機能概要・upstream・実行file・設定・manualのpathを採取。直接導入binary、pip/Go、Actions、runnerは別の設定面として扱う。

使用したOCIは`ghcr.io/uist1idrju3i/msd-dev@sha256:c5beb4973cad6bef273fd0efc51deb89e334de5f5b1700de2f41980410d65d77`。help採取はnetworkなし・read-only rootfs・非rootで実行し、証拠の出力先だけを書込み可能にした。別のCIで後に生成したOCIを検証した結果とはしない。

## Sourceの展開と失敗した試行

最初は定義・help周辺だけをsource archiveから抽出した。28 sourceのconfigure helpは9件がexit 0、19件が非zeroとなった。Pythonの`Include/object.h`、util-linuxの`sys-utils/mount.c`、kmodの`libkmod/libkmod.c`等がないという失敗を確認した。option非対応や製品build失敗の証拠ではない。

失敗出力を残し、source全体をPythonの`tarfile`の`filter="data"`で展開し直した。SDK、Linux、Raspberry Pi firmware、`.tar.lz`のmtoolsを除く52 archiveを対象とした。全archiveの全設定を意味解析したわけではない。対象28 sourceのdirectoryで`sh configure --help`を再実行し、28件のexit 0を確認した。stdoutとstderrは別に保存し、CSVでは両方からoption行を採取した。zlibのhelpのようにstderrへ出る説明を落とさないためである。

`filter="data"`は展開時の安全策であり、取得sourceの任意codeを安全にするsandboxの代用ではない。helpでもscriptを実行するので、版・hashを確認したsourceに限り、network・mount・権限を制限する。

host toolのhelpも同じOCIで採取した。command、終了状態、出力hashはprovenanceにある。NinjaはそのOCIには存在せず、Buildrootの`host-ninja`が選択されていることとは矛盾しない。未導入を「optionなし」と扱わない。

## 変換の再実行

[collect.py](collect.py)は、用意した入力をCSV/JSONへ変換する部分である。download・source展開・ビルド・runtime試験を自動で行うscriptではない。元入力は公開artifact、固定source、同じ条件での照会から用意し、provenanceのhashと照合する。

repositoryのrootから、例えば以下を実行する。`INPUT`は採取済み入力のdirectory、`OUT`は変換先であり、秘密値を含む設定を公開入力へ置かない。

```sh
python3 docs/research/component-options/collect.py \
  --repository "$PWD" --output "$OUT" \
  --package-info "$INPUT/buildroot-show-info.json" \
  --sbom "$INPUT/sbom.cdx.json" \
  --variables "$INPUT/component-expanded-vars.json" \
  --configuration "$INPUT/buildroot.config" \
  --kernel-config "$INPUT/kernel.config" \
  --gcc-help-dir "$INPUT" \
  --configure-help-dir "$INPUT/configure-help" \
  --path-map '/evidence/component-config=@OUTPUT@' \
  --path-map '/work/vendor/buildroot=@BUILDROOT@' \
  --path-map '/work=@EXTERNAL@'
```

GCCの入力名は`component-sdk-gcc-CATEGORY-Os-a53.txt`、configureの入力は`status.json`と`SOURCE.txt`・`SOURCE.stderr`。statusには`source_directory`と`returncode`を記録する。show-infoの外部recipe pathは採取時の`/work/` mountに合わせている。別のmountで採取した場合はpathの対応を確認する。

Buildrootは単独cloneを使い、submoduleは固定commitのままにする。`--repository`のsourceと生成物の基準を変えて、行番号だけを古い版へ流用しない。`package-variables.json`等のpathは上記の記号に置換し、秘密値になり得るBuildroot symbolは`withheld`にした。これは任意の入力から秘密値を完全検出する仕組みではなく、追加する入力・出力ごとの確認も必要である。

## 検査と未確認範囲

```sh
python3 -m unittest discover -s docs/research/component-options -p 'test_*.py' -v
python3 -m py_compile docs/research/component-options/collect.py
```

7つの回帰試験は、target/hostの同名、外部recipe、rootfs/virtual除外、SBOMの重複・欠落拒否、無効・未記録・非公開の区別、path置換、stdout/stderr、GCCの5 categoryと空欄、kernelのmodule/無効行、同じ入力の再生成を確認する。製品のfull buildや実機の試験ではない。

固定入力の変換を5回繰返し、全7出力のbyte一致を確認した。[全35照合の値](verification.csv)にhash・bytes・一致判定を保存した。さらに、名前だけでのSBOM結合、重複見逃し、未記録を無効と解釈する変更、stderr欠落、path置換の無効化という5つの変異を加え、いずれも回帰試験が検出した。source、GCC、configureのhelp自体を5回実行した性能測定ではない。検査結果はこの台帳を更新したrevisionと入力の範囲に限定する。

## 出典とlicense

option名とhelpの説明は、各upstreamの固定sourceと実行ファイルに由来する。定義の場所はpackage台帳、出典archiveとhashは[source台帳](source-archives.json)、recipeのlicense指定は固定Buildroot、原文のlicense・copyrightは同CI artifactの`legal-info.tar.gz`にある。license未確認項目は[SBOMの限界](../operations/sbom-coverage.md)と分けて解決する。台帳の存在を全配布物のlicense審査完了とはしない。
