# 未使用libgompのtarget配送削減

- 状態: 初回は旧構成の容量・前後A/Bを比較。追試で現行構成のCI build・削除後A/Bと184 ELFの参照を確認
- 日付: 2026-11-23
- 基準: `f4e1f65cf9a66aa4756675a926a7edaaf99d5377`
- 関連: [toolchain設定](../research/component-options/buildroot-toolchain.md)、[実験一覧](README.md)

## 目的・採否基準

外部Bootlin toolchainが配送するOpenMP runtimeを、製品で使わない場合にだけ省く。
仮説は、libgomp本体とそのsymlinkだけを削除し、通常file合計を302,440 bytes減らせること。
容量減少は起動時間の短縮と扱わない。
採用条件は、DT_NEEDED・literalなlibgomp参照・有効なOpenMP関連packageに利用者がないこと、削除後の変更が対象libraryだけであること、rootfsとSquashFSがともに小さくなること、前後のQEMU A/Bでready・loginとmodule読込みを維持すること。
利用者が見つかれば削除せず停止する。

## 条件と計画

比較元は既存`output-integrity`のimageとtoolを使う。full製品buildの代わりとなる検証ではない。
両側に採用済みのmodule binary index削除を適用し、libgompの配送だけを変える。
kernel、modules、text index、OpenSSL設定、圧縮条件、QEMUは同じにする。
展開・packは新規`output-libgomp-r1`で実施し、元のimageや過去の実験出力を変更しない。
製品buildのcold/warm比較ではなく、同じ既存imageの展開・再packであり、ccacheとreconfigureは使わない。
beforeのA/A packを1組、beforeとafterのQEMU A/Bを各1回行う。
構築可否と機能の試験なので5回の性能反復は行わず、時間の差から性能を結論しない。
異常な参照を与える負の対照と、SONAMEをDT_NEEDEDと誤認しない対照を設ける。
ホスト試験には削除・保持・空・冪等性・ELF参照・dlopen文字列・別名symlinkでの拒否を含める。

## 導入経路と利用者の監査

製品defconfigは外部Bootlin `aarch64 glibc stable 2025.08-1`を選ぶ。
同toolchainのKconfigが`BR2_TOOLCHAIN_HAS_OPENMP`をselectし、外部toolchain recipeが`libgomp.so.*`をtargetへcopyする。
既存package manifestでも所有者は`toolchain-external-bootlin`である。
内部GCC用の`BR2_GCC_ENABLE_OPENMP`は、この外部toolchainの配送を無効にしない。
toolchainの能力を偽って無効にする設定やtoolchainの交換は避け、external post-buildで削除する。
SDKとstagingのlibraryは残す。

監査の対象は既存imageの全通常fileとsymlink、および現在のdefconfigを固定Buildrootで正規化した設定。
libgomp自身のSONAMEと自身を指す配送用symlinkは利用者と数えない。
DT_NEEDEDに加え、他fileの`libgomp`文字列、`GOMP_`、dlopenを持つbinaryを調べる。
Buildroot recipeのOpenMP関連記述を抽出し、該当packageの有効・無効を照合する。
文字列を実行時に組み立てる未知のloaderまでの不使用証明ではない。
将来literalな利用者が追加された場合、post-buildはlibraryを削除する前に失敗する。

監査結果は146 ELFでDT_NEEDEDの利用者0、他fileのliteral参照0、非providerの`GOMP_`参照0。
dlopen文字列を持つ10 fileにもlibgompのliteral参照はなかった。
recipeの広い検索に該当した16 packageはすべて無効で、OpenMPTなど名前の似たものも含めて保守的に照合した。
自前でcompileしたOpenMP clientは`libgomp.so.1`へのDT_NEEDEDを持ち、dlopen clientは同NEEDEDなしでliteralだけを持つ。
どちらも削除器に拒否され、libraryが残ることを確認した。
libgomp自身のDT_NEEDEDは`libc.so.6`だけで、SONAMEを利用者と誤認しない対照にもなった。

## 実行環境・結果

| 条件 | 実際に使った値 |
|---|---|
| ホスト | Ubuntu 26.04.1 LTS、Linux 7.0.0-44-generic x86_64、glibc 2.43 |
| 今回のBuildroot source・正規化 | `bbbdab36565d4941b6b0449a0eedb5aac8a10c2e`。既存imageのconfigは旧`8b238854d90`系列であり、最新sourceからの製品buildではない |
| GCC | `aarch64-linux-gcc.br_real`、Buildroot 2021.11-18033-g83947c7bb6、14.3.0 |
| kernel | 6.18.59-v8、SHA-256 `45d52f6e148cebaee66ecbc9735c6260ec23ca8c9ad0b00032cf04d20f1420e8` |
| mksquashfs | 4.7.5、zstd level 22、128 KiB、2 processors、時刻0。sourceのsort指定を両側で共用 |
| QEMU | 11.1.3、raspi3ap、512 MiB、TCG、icountなし。Bluetoothを無効にした同じDTBを使用 |
| QEMUのOCI | `sha256:1aea11386e31cc82eff0807de3e372a0b4443c881f3bc3765a56810b32e2ca65` |
| QEMU binary | SHA-256 `8b5c759a21dd5d841d96b37be4e60e3b324869dff22250b581c856e36ac15b73` |

QEMUのserial冒頭には`run-qemu: sha256`として上記binaryとkernelのhashが記録されている。
入力SquashFSのSHA-256は`b68236f9612b010d42a0a9227d59332d94b2b84d19a593dc16ea9f269e2ea885`。
通常file合計は、共通のmodule index削除後、測定用inventory markerを入れる前の値である。
markerは両側へ同じように挿入し、製品のpost-buildには追加していない。
sortからlibgompのentryも除いて両側へ使っているため、前回のmodule実験と同じ容量でもpackのhashは異なる。

| 対象 | before | before A/A | after | 差 |
|---|---:|---:|---:|---:|
| rootfs通常file合計（bytes） | 36,110,243 | 36,110,243 | 35,807,803 | −302,440 |
| SquashFS（bytes） | 20,332,544 | 20,332,544 | 20,197,376 | −135,168 |

beforeとA/AのSquashFS SHA-256はどちらも`38ea3a21a99cee7835881827bb66dba96795c3a4c335bb30bd7922062b1debe5`。
afterは`720e723724e233e9a65339b2f90a59cad7b3635c0f157b529270c1751bb8229b`。
通常fileの削除は`usr/lib/libgomp.so.1.0.0`だけで、残したfileのhash変更は0。
配送用の`usr/lib/libgomp.so.1`も削除し、他libraryを維持した。

QEMUはbefore A/Bとafter A/Bがすべてready・loginへ到達し、QMP quit後に終了0、fallback signalなしで回収できた。
beforeとafterを並列に実行し、各variant内のA、Bは順次実行した。性能比較ではない。
`/proc/modules`は各19件で、名前・サイズ・依存先・状態の比較で差分0。addressと参照数は比較から外し、生の行はserialに保存した。
比較器は1 moduleを欠く負の対照では差分を検出した。
容量とbootの採用条件を満たしたため、製品のpost-build削除を採用する。

## 失敗・未実施と再実行

失敗させる対照は、OpenMP client、dlopen client、既存出力先の計3件。
前2件は削除を拒否して終了1、既存出力先も`FileExistsError`で終了1となり、上書きしなかった。
正常のpack・bootとこれらの負の対照、full製品buildのnot_runは[CSV](2026-11-23-libgomp-prune.csv)で分けた。
初回はfull Buildroot buildをCIへ残し、既存imageだけを使った。現行構成の追試は末尾に分けて記す。
初回の結果を現在のHEADの製品imageのA/B成功や、実機での改善とは報告しない。

比較元には、削除前のlibgompとhost toolsを含むbuild出力を指定する。
現在のpost-buildでlibgompを削除済みのimageは比較元に使えない。
出力名は未使用のものに変え、repository rootで実行する。

```sh
docker/msd-dev make -s -C vendor/buildroot BR2_EXTERNAL=/work \
  O=/work/output-libgomp-config msd_cardputerzero_defconfig
python3 board/cardputerzero/tools/bench/libgomp.py \
  --reference output-integrity --config output-libgomp-config/.config --out output-libgomp-r1
docker/msd-dev env OUTPUT_DIR=/work/output-libgomp-r1/before \
  QEMU_LOG_DIR=/work/output-libgomp-r1/before/logs board/cardputerzero/qemu/test-boot.sh
docker/msd-dev env OUTPUT_DIR=/work/output-libgomp-r1/before \
  QEMU_LOG_DIR=/work/output-libgomp-r1/before/logs board/cardputerzero/qemu/test-ab.sh
docker/msd-dev env OUTPUT_DIR=/work/output-libgomp-r1/after \
  QEMU_LOG_DIR=/work/output-libgomp-r1/after/logs board/cardputerzero/qemu/test-boot.sh
docker/msd-dev env OUTPUT_DIR=/work/output-libgomp-r1/after \
  QEMU_LOG_DIR=/work/output-libgomp-r1/after/logs board/cardputerzero/qemu/test-ab.sh
```

[証拠archive](2026-11-23-libgomp-prune-evidence.tar.gz)にはauditの全DT_NEEDED、正規化config、対照のsource・ELF・拒否log、A/A結果、全serial・process結果、source hashを保存した。
archive SHA-256は`f194d5a1d6797f93b6ffc2c8fa488221009bf1043500091843183f6fcd60c78c`。
大きいimageはarchiveに含めず、入力hashと上の再生成手順を記録した。

## 製品I/Oと未確認

変更はbuild時のtarget配送だけであり、製品の画面や実行時の永続writeを追加しない。
修正後HEADの製品build、実機、LCD、keyboard、I2C、firmware tryboot、SD電源断は未確認。
QEMUの成功を実機の証拠としない。

## Review後の現行設定の再監査

初回の既存imageには、現在の正規化設定で有効なbtrfs-progsとcryptsetupが入っていなかった。
146 ELFの不使用という観測は初回imageだけの結果であり、現在の製品構成全体の結果ではない。
この条件差を見落とさないよう、測定器は有効な両packageのELFが欠けたimageの監査を拒否する。

再監査の計画は、現行CI成果物で両ELFの存在と全ELFのDT_NEEDED・literalなlibgomp・GOMP_を調べることとした。
削除済みの製品imageでも`--audit-root`で参照を監査できる。新しい`output-libgomp-current-r2`を使い、初回archiveを変更しなかった。

| 項目 | 追試の条件・結果 |
|---|---|
| source | PR #296のHEAD `126cc57fe5324f710f6ec75024b34d94284ffe12`。defconfigは手元の正規化元とbyte一致 |
| CI | [run 45128825802、build job 137539472527](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/45128825802/job/137539472527)はsuccess |
| 入力 | [artifact 14798117190](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/45128825802/artifacts/14798117190)、`msd-cardputerzero-build` |
| artifact ZIP SHA-256 | `22c12c8647170234ed4540b874c0446fc0a45679bbac79258f8b82de9674d23a`。APIのdigestと照合 |
| sdcard.img.xz SHA-256 | `913eb4986bf8890420d464b4baef2d1d9ca704ee9304845f9e0883d1cf75d84f` |
| kernel SHA-256 | `6a615f51ef32e0f981227197df1ff7474734193dd2efe6d21201739ae7a8de46`。初回のkernelとは異なる |
| btrfs | `usr/bin/btrfs`、1,003,208 bytes、ELFを収録。DT_NEEDED・literal・GOMP_に該当参照なし |
| cryptsetup | `usr/sbin/cryptsetup`、224,112 bytes、ELFを収録。DT_NEEDED・literal・GOMP_に該当参照なし |
| 全体監査 | 184 ELF。DT_NEEDEDの利用者0、他fileのliteral参照0、非providerのGOMP_参照0 |
| 負の対照 | 初回imageと現行設定の組合せは、両ELFの欠損を検出して終了1 |
| CIの削除後A/B | 両slotがready・loginへ到達。QMP quit、終了0、reaped、fallbackなし。GPIO6 power-fail smoke stepもsuccess |

初回ZIP取得は300秒でtimeoutし、507,822,080 bytesで中断した。Rangeで再開し、全体digestの一致後に展開した。
取得は`https://nightly.link/uist1idrju3i/MSD-Linux/actions/artifacts/14798117190.zip`を使った。
`images/sdcard.img.xz`を展開し、sfdisk JSONの5番目のpartitionのstartを512倍したoffsetからunsquashfsでslot Aを取り出した。
非rootの所有者設定だけの警告はextract.logに残し、それ以外の展開失敗は許容しなかった。
監査は次のCLIを使用した。正規化configは初回と共通だが、今回のimageには両packageのELFが存在することを追加検査している。

```sh
python3 board/cardputerzero/tools/bench/libgomp.py \
  --audit-root output-libgomp-current-r2/root \
  --config output-libgomp-current-r2/normalized.config \
  --out output-libgomp-current-r2/audit
```

[追試の証拠archive](2026-11-23-libgomp-current-audit-evidence.tar.gz)にはaudit JSON、全184 ELFのhash、両toolのELF、正規化config、使用source、CI metadata・全serial・process結果、負の対照log、8行のtemplate形式CSVを保存した。
SHA-256は`7fc6b11e95b6326e8e81ea5436a35732647d2f6b8ed447f4fa021024ee76b465`。
CIのserialとprocess結果はartifact `14797469336`から取得した。
初回146 ELFの結果と同じ標本ではないため、初回の容量値やQEMU module数を現行構成の値に置き換えない。
現行CI成果物はlibgomp削除後であり、対応する削除前製品imageは未取得である。
現行構成の前後4 boot比較・容量比較、修正後HEADのCI結果は、この追試では未確認。取得後のQEMUも再実行していない。
