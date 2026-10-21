# CI 高速化 C1 の非 PPD 対照 build

- 状態: 完了（予備比較。採否は未決定）
- 日付: 2026-10-21
- 担当: Devin
- 関連: [開発環境と CI の調査](../research/dev-environment-and-ci.md)

## 目的と仮説

`BR2_PER_PACKAGE_DIRECTORIES=y` と top-level `make -j` を使う C1 が同じ commit の非 PPD build より短時間で完了するか、target tree が変わるかを調べます。非 PPD の対照 build は、PPD run2 と同じ commit、共有 DL_DIR、新規の空の ccache で実行しました。

## 採否の基準

この予備試行では採否を決める数値の閾値を事前に設定していません。依頼された各条件を 1 回ずつ測り、target の差を分類することが目的です。1 回の結果だけで C1 を採用しません。

## 条件

| 項目 | 値 |
|---|---|
| 非 PPD / PPD commit | `d64fa9188820d4e7875704ffdcd6c73db14064ac` |
| N の baseline commit | `39ccd23` |
| Buildroot submodule | `d6061d653d7fb215c2409c59e4bfad1b9d677215` |
| ホスト | Ubuntu 26.04.1 LTS、x86_64 |
| 開発コンテナー内 QEMU | 11.1.2 |
| target GCC | `aarch64-buildroot-linux-gnu-gcc.br_real` 14.3.0 |
| kernel | 6.18.57-v8 |
| 出力先 | 新規 clone の `output/`。再 configure はなし |
| ダウンロード cache | baseline と共有 |
| ccache | 各 clone に新規で空の `.ccache` |
| ccache 設定 | `BR2_CCACHE=y`、`BR2_CCACHE_DIR="$(BR2_EXTERNAL_MSD_PATH)/.ccache"` |
| 変えた条件 | PPD run2 は `BR2_PER_PACKAGE_DIRECTORIES=y`、base run3 は無効 |
| 固定した条件 | commit、defconfig、Buildroot submodule、DL_DIR、toolchain、make の順序 |
| 並列数 | 12 (`nproc`) |
| 繰り返し | 各条件 1 回。中央値・範囲は算出しない |

N は baseline commit `39ccd23` と base run3 の比較、P は base run3 と PPD run2 の比較です。N は commit が異なるため、純粋な A/A build 変動ではありません。

## 手順

非 PPD build は defconfig、`host-ccache`、top-level parallel make、`legal-info` の順に実行しました。build の間にほかの重い処理は実行していません。PPD run2 も同じ手順です。

```sh
BR2_DL_DIR="$SHARED_DL_DIR" docker/msd-dev bash -euo pipefail -c '
    make -C vendor/buildroot BR2_EXTERNAL="$PWD" O="$PWD/output" \
        msd_cardputerzero_defconfig
    make -C output host-ccache
    make -C output -j"$(nproc)"
    make -C output legal-info
'
OUTPUT_DIR="$PWD/output" docker/msd-dev board/cardputerzero/qemu/test-boot.sh
```

実際の計測ログ、make ごとの終了コード、manifest、比較 TSV は依頼された外部ログ directory に保存しました。defconfig は編集していません。

## 計測器の検証

1 秒の monotonic sleep は 1.000177 秒と計測されました。Buildroot `build-time.log` は全 start/end pair が対応し、未対応 pair は 0 件でした。

## 結果

生の計測値は [2026-10-21-ci8-ppd-control.csv](2026-10-21-ci8-ppd-control.csv) にあります。

### make の時間

| make | base run3 秒 | rc | PPD run2 秒 | rc |
|---|---:|---:|---:|---:|
| defconfig | 3.959 | 0 | 3.277 | 0 |
| `host-ccache` | 113.697 | 0 | 117.402 | 0 |
| top-level `make -j"$(nproc)"` | 3004.838 | 0 | 2298.974 | 0 |
| `legal-info` | 33.875 | 0 | 35.127 | 0 |

この 1 回では、PPD の top-level build は base より 705.864 秒短く、base に対して約 23.5% の短縮でした。繰り返し測定ではないため、安定した短縮率とは判断しません。

### build-time.log の step 合計

| step | base run3 秒 | PPD run2 秒 |
|---|---:|---:|
| download | 4.827 | 123.992 |
| extract | 30.581 | 83.480 |
| patch | 6.278 | 36.482 |
| configure | 537.203 | 1014.364 |
| build | 2201.674 | 3177.778 |
| install-host | 20.399 | 38.591 |
| install-image | 1.334 | 3.149 |
| install-staging | 6.758 | 14.150 |
| install-target | 84.078 | 97.330 |
| install-* 合計 | 112.570 | 153.219 |
| 最初の start から最後の end | 3053.514 | 2336.285 |

step は並列に進むため、step 合計と最初の start から最後の end は一致しません。`build-time.log` の wall は外側の top-level make 計時とも別の値です。

### target manifest

| 比較 | 変更 path 数 |
|---|---:|
| N: baseline `39ccd23` -> base run3 | 1055 |
| P: base run3 -> PPD run2 | 1064 |
| P にあり N にない path | 10 |

baseline と base は各 2174 entries、PPD は 2173 entries でした。N は source commit 差も含むため、N と P の集合差は PPD の影響を確定するものではありません。P の完全な差分は外部ログの `target-diff-P-base-to-ppd.tsv`、P minus N は `target-diff-P-minus-N.tsv` にあります。

P minus N の path は次の 10 件です。

```text
usr/bin/cec-compliance
usr/bin/cec-follower
usr/bin/edid-decode
usr/bin/v4l2-compliance
usr/bin/v4l2-ctl
usr/lib/gconv/ARIB-STD-B24.so
usr/lib/gconv/EN300-468-TAB00.so
usr/lib/libstdc++.so.6.0.33-gdb.py
usr/sbin/v4l2-dbg
usr/share/locale
```

P の `lib/modules` 以外の 12 files は次のとおりです。

| path | 分類と根拠 |
|---|---|
| `bin/busybox` | `.note.gnu.build-id` はありません。`.rodata` の BusyBox version string の時刻だけが `02:38:41` から `01:40:40 UTC` に変わりました。path は N にも含まれます。 |
| `etc/msd-update/update-key.pem` | build ごとに生成された development Ed25519 公開鍵です。両 build の `post-build.sh` が development key の生成を記録しています。path は N にも含まれます。 |
| `usr/bin/cec-compliance` | ELF に build-id はありません。section 差分は `.data.rel.ro`, `.eh_frame`, `.eh_frame_hdr`, `.rela.dyn`, `.rodata`, `.text`。`strings` で GCC header path が global host から libv4l per-package host へ変わっています。 |
| `usr/bin/cec-follower` | build-id なし。`.data.rel.ro`, `.eh_frame`, `.eh_frame_hdr`, `.rela.dyn`, `.rodata`, `.text` が異なり、`bits/stl_tree.h` の embedded path が global host から libv4l per-package host に変わっています。 |
| `usr/bin/edid-decode` | build-id なし。`.data`, `.data.rel.ro`, `.eh_frame`, `.eh_frame_hdr`, `.rela.dyn`, `.rodata`, `.text` が異なり、`bits/stl_vector.h` の embedded path が変わっています。 |
| `usr/bin/v4l2-compliance` | build-id なし。`.data`, `.data.rel.ro`, `.eh_frame`, `.eh_frame_hdr`, `.rela.dyn`, `.rodata`, `.text` が異なり、`bits/basic_string.h` の embedded path が変わっています。 |
| `usr/bin/v4l2-ctl` | build-id なし。`.data`, `.data.rel.ro`, `.eh_frame`, `.eh_frame_hdr`, `.got`, `.rela.dyn`, `.rodata`, `.text` が異なり、`bits/basic_string.h` と `bits/stl_vector.h` の embedded path が変わっています。 |
| `usr/lib/gconv/ARIB-STD-B24.so` | build-id なし。`.dynstr` と `.text` などが異なり、`strings` では `X` 64 個の文字列が 83 個に変化しています。 |
| `usr/lib/gconv/EN300-468-TAB00.so` | build-id なし。`.dynstr` と `.text` などが異なり、同じ `X` 64 個から 83 個への変化があります。 |
| `usr/lib/libcrypto.so.3` | build-id なし。`.rodata` の `built on` 時刻のみが `02:37:23` から `01:43:18 UTC` に変わりました。path は N にも含まれます。 |
| `usr/lib/libstdc++.so.6.0.33-gdb.py` | text file。2 行の toolchain path が `/work/output/host/...` から `/work/output/per-package/toolchain-external-bootlin/host/...` に変わっています。 |
| `usr/sbin/v4l2-dbg` | build-id なし。`.data`, `.data.rel.ro`, `.eh_frame`, `.eh_frame_hdr`, `.rela.dyn`, `.rodata`, `.text` が異なり、`bits/stl_vector.h` の embedded path が global host から libv4l per-package host に変わっています。 |

ELF の差分は `.note.gnu.build-id` では説明できません。gconv 2 files の差がどの build option または link 入力に由来するかは未特定です。全 per-file diff と section/string の出力は外部ログの `non-module-diffs/` と `non-module-classification.tsv` にあります。

### module signature

両 config は `CONFIG_MODULE_SIG_ALL=y` です。3 件の module を xz 展開し、末尾の `~Module signature appended~` より後ろの署名を除いて比較しました。各々の署名は両 build で 681 bytes、署名前 payload は 3 件とも SHA-256 が一致しました。これは sample 3 件の結果で、全 module への一般化はしません。

| module | unsigned SHA-256 |
|---|---|
| `aes-arm64.ko.xz` | `51101c9280d54627f76e2fb3a6fa0bde402b8dbf00e84a708d08a3f11db22a53` |
| `af_alg.ko.xz` | `78d4d78f1086d0435674ee5849833ec8522e6d49e934de3929da26a94729c137` |
| `async_memcpy.ko.xz` | `bb3f4812a4a2548d87bc070354fb8d477fed1e3e257c2d3cf91903395d10b72c` |

### `usr/share/locale`

両 `.config` では `BR2_ENABLE_LOCALE=y`、`BR2_ENABLE_LOCALE_PURGE=y`、`BR2_SYSTEM_ENABLE_NLS` は無効、libv4l utils は有効です。`libv4l.mk` は `TARGET_NLS_DEPENDENCIES` を依存に加えますが、`package/Makefile.in` では system NLS が無効の場合に gettext 依存が設定されません。

非 PPD の共有 `output/host/bin` には、別 package が用意した `msgfmt` があり、Meson はそれを見つけて 9 個の `.mo` を install しました。PPD では libv4l の host `PATH` が `per-package/libv4l/host/bin` に限定され、そこには `msgfmt` がありません。Meson log は `Program msgfmt found: NO` と translation target を無視する warning を記録し、libv4l の per-package target に locale `.mo` はありません。

`target-finalize` はまず package target tree を per-package rsync で合成し、その後 `PURGE_LOCALES` を実行します。locale purge は `/usr/share/locale` の language subdirectory を消しますが親 directory は消しません。このため base には空の親 directory が残る一方、PPD では rsync の入力に locale tree 自体がなく、最終 target に directory が現れません。Buildroot の `vendor/buildroot/Makefile` 703-728 行、755-759 行、`package/pkg-utils.mk` 264-272 行、`package/libv4l/libv4l.mk` 56-59 行、`package/Makefile.in` 423-428 行が根拠です。

### QEMU smoke test

ホスト側には QEMU hosttools directory がなく、最初の直接実行は `qemu-system-aarch64: not found` で boot 前に終了しました。その後、開発コンテナーの QEMU 11.1.2 を使い `docker/msd-dev` 経由で 1 回実行し、34.161 秒で ready marker と login prompt を確認しました。終了コードは 0 です。この結果は QEMU の smoke test であり、実機の boot 性能を示しません。

### disk と既存 output

実験後の空き容量は 58 GiB、使用率は 74% でした。`s27-main/output` と PPD run2 の `ci8-ppd/output` は残してあります。

## 捨てた試行と経緯

ホスト側の直接実行は QEMU が見つからず、boot は開始していません。失敗ログを保持し、リポジトリで通常使う `docker/msd-dev` 内の QEMU で試験しました。Buildroot build は全 make が終了コード 0 でした。

## 結論

PPD run2 はこの 1 回の対照 build より top-level make が約 23.5% 短時間でした。一方、同一 commit の target manifest は 1064 paths が異なり、build ごとの時刻、development key、module signature に加え、embedded toolchain path と translation file の有無も異なりました。C1 の時間効果を一般化したり、成果物が同一と判断したりするには、同一 commit の追加反復と差分原因の調査が必要です。

## 未確認の点

- 1 回ずつのため、build time の変動幅は不明です。
- N は source commit が異なるため、純粋な build-to-build variation ではありません。
- `v4l2-compliance` と `v4l2-ctl` の `.rodata` に、埋め込み path の長さだけでは説明できない差が残っています。
- 3 module sample の結果は全 module を代表しません。
- QEMU smoke test は実機の性能、device driver、周辺機器を検証しません。

## ログ

大きなログと manifest は repository に含めず、依頼された `run3-base/` log directory に保存しました。以下の SHA-256 は保存したファイルの値です。

| ファイル | SHA-256 |
|---|---|
| `defconfig.log` | `a28dbe40b049083c5ae6ef470721be685b84d8938940b95c6189d6719d1b0255` |
| `host-ccache.log` | `de0c26c79c370579479e5c5ffed0b49b2280396818928023768004511035dd3d` |
| `build.log` | `7dc58d0d5a48e74a64d3c1036157089592312481f9bc5772256bf5b8c3bec8e9` |
| `legal-info.log` | `d9ee53c2a8b5e6ec22dc49e17c11ac9d83c9111350408cadd851720bc467b16a` |
| `make-timings.csv` | `fa846d015ddbabd10a8d01d174dd11ca556293bc7509a45d95b2453d5fba7078` |
| `build-time-run3-base.log` | `4d17a0d74f0ac68382a9b258ecef0c1cf7f0622a5ea39f3013e6049a69c00982` |
| `build-time-run3-vs-run2.tsv` | `af13372c93aade25dc494e51f29d0441abc78041cf8333a77d8dc6114181b7ba` |
| `test-boot-docker.log` | `8a57e19c5a4fe215141cc00fc6f8666fee795965eec5cc610f42d5629958366f` |
| `test-boot-docker-result.txt` | `35765b6e99bc1adcacdd36276d95d85262fadbd1d59fb6bf2b8631fd7236e584` |
| `target-run3-base.tsv` | `63dfb5ac96777747fd288bf3869676b21786d6953913153e900710bd4ba1a5f0` |
| `target-diff-P-base-to-ppd.tsv` | `ee8818a648f5ba578505f0c5342c772a957871a0f406f84ac20b5343cbdd7013` |
| `target-diff-P-minus-N.tsv` | `8ed43fe4860e8fe49b0e80960daf1003a4d89fdcf0ade8c907281abe667507d9` |
| `non-module-classification.tsv` | `574832037e7d20e250e3e20d03445e6dffa062a917dbfa9ec14e143a9432ef32` |
| `module-signature-comparison.tsv` | `ba706e09d97ef16bd780ed068327ced8f066981d8e59217e4eb419b615b6fa3c` |

N・P の再生成は保存済み manifest に対して比較スクリプトを実行し、Buildroot step 集計は保存済み `build-time-run3-base.log` の start/end pair を合計します。ログや manifest を含む外部 artifact の一覧は handoff report を参照してください。

## CI 本番の後の追加調査

対象は base run3 と PPD run2 の target にある gconv shared object 2 件と v4l-utils binary 6 件です。結果の比較には PR [#81](https://github.com/uist1idrju3i/MSD-Linux/pull/81) と PR [#82](https://github.com/uist1idrju3i/MSD-Linux/pull/82) の CI 記録も参照しました。

### gconv shared object

`usr/lib/gconv/ARIB-STD-B24.so` と `usr/lib/gconv/EN300-468-TAB00.so` の所有 package は libv4l です。raw build 出力の RPATH は、非 PPD では `/work/output/host/aarch64-buildroot-linux-gnu/sysroot/usr/lib64/gconv`、PPD では `/work/output/per-package/libv4l/host/aarch64-buildroot-linux-gnu/sysroot/usr/lib64/gconv` でした。最終 target の dynamic section に RPATH/RUNPATH はなく、`patchelf --print-rpath` も空でした。

host-patchelf は削除した RPATH の領域を `memset(rpath, 'X', rpathSize)` で埋めます。最終 `.dynstr` の `X` は非 PPD が 64 byte、PPD が 83 byte で、`.dynstr` のサイズ差も各ファイルで +19 byte でした。`.rodata` と `.data` は一致し、NEEDED と dynamic symbol 名の集合も一致しました。disassembly の差は `ldr` の offset で、offset を伏せた比較では差が 0 行でした。観測した差は RPATH の長さの差で説明できますが、`X` を最初に書き込んだ install 段階は特定していません。

### v4l-utils binary

対象は `usr/bin/cec-compliance`、`usr/bin/cec-follower`、`usr/bin/edid-decode`、`usr/bin/v4l2-compliance`、`usr/bin/v4l2-ctl`、`usr/sbin/v4l2-dbg` です。埋め込み GCC header path は `/work/output/host/` の 18 文字から `/work/output/per-package/libv4l/host/` の 37 文字へ変わり、差は 19 文字でした。path 1 件の binary では `.rodata` が +16 byte、path 2 件の `v4l2-ctl` では +32 byte でした。

指定の正規化後の disassembly は、`v4l2-ctl` が 0 行差、残る 5 binary は `ldr` の offset 行だけでした。さらに `ldr` の offset を伏せると 6 binary とも差は 0 行です。NEEDED と dynamic symbol 名の集合は 6 件すべて一致しました。`.data` と `.data.rel.ro` には 8 byte の語の address 差があり、語ごとのずれは +16、+24、+32、+40 byte でした。`cec-compliance`、`cec-follower`、`edid-decode`、`v4l2-dbg` は、埋め込み path と後続 padding を除いた `.rodata` が一致しました。

一方、`v4l2-compliance` の共通部分 217 byte（69 区間）と `v4l2-ctl` の 11,669 byte（8,614 区間）は、path と padding を除いた `.rodata` にも差が残りました。8 個の jump table、計 218 entry は、C0/C1 で表の byte 列が一致し、計算した分岐先 218/218 が同じ関数内位置の同じ正規化命令を指しました。残る区間は `adrp`+`add` による address 形成、直接 load、jump table の検索では参照元を対応づけられず、原因は未特定です。legal-info の package と version の組は 13 組すべて一致しました。

### 比較方法

- `aarch64-linux-objdump -d --no-show-raw-insn` の出力から行頭 address と symbol offset を除き、16 進即値を `IMM` に置換して比較しました。別途 `ldr` の offset も伏せて比較しました。
- `objcopy -O binary --only-section` で `.rodata`、`.data`、`.data.rel.ro` を取り出し、`cmp -l` と `strings -t x` で byte と文字列を比較しました。
- `readelf -S` で section size、`readelf -d` で NEEDED/RPATH、`readelf --dyn-syms` で dynamic symbol 名を比較しました。
- `.rodata` 残差は連続区間と int8/int16/int32 の little-endian 差に分け、保存済み disassembly の address 参照と jump-table branch target を照合しました。
