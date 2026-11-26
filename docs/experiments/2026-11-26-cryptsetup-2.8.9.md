# cryptsetup 2.8.9への更新

- 状態: 製品構成のbuild・QEMU確認済み。実機未確認
- 日付: 2026-11-26
- 関連: [設定と採否](../research/component-options/cryptsetup-2.8.9.md)、[生の値とhash](2026-11-26-cryptsetup-2.8.9.csv)

## 目的と採否の基準

利用者が承認した2.8.7から2.8.9への更新である。将来のLUKS2+Btrfsの`/data`の前提を整える。今回、`/data`の形式、PIN入力、暗号方式、PBKDFの値は変更しない。

結果を得る前の基準は、製品buildの成功、targetの`cryptsetup --version`が2.8.9、QEMUのA/B起動、関連host試験の成功、sourceとlicense hashの一致である。最終kernel設定の差とlegal-info・SBOM/VEXの比較範囲も記録する。各1回の構築可否と機能確認であり、速度や耐久性の結論には使わない。

## 条件と手順

基準commitは`e478fde1c2dc5bbe459154418e9c79deef5ad8bb`。Buildroot gitlinkは`bbbdab36565d4941b6b0449a0eedb5aac8a10c2e`。基準は変更前の製品defconfigから新規の`O=/work/output-cryptsetup-289`で構築する。変更側も別の新規出力`O=/work/output-cryptsetup-289-new`で構築する。旧版のlibraryがtargetに残ることを避けるため、基準buildの完了前に増分再利用の計画を改めた。両方ともbuild treeはcold、download cacheと既存の共通ccacheは再利用する。実行順でcacheのwarm状態が異なるためbuild時間を性能比較しない。

同じhostのfs-compare-v2試行09とはclone・run・evidenceを分ける。その入力や実行中scriptは変更しない。重い処理にはcontainer内で`nice -n 19 ionice -c 3`を指定し、makeの並列数を4に制限する。

hostはUbuntu 26.04.1 LTS、開発containerはDebian 13。両buildとも開発image `sha256:1aea11386e31cc82eff0807de3e372a0b4443c881f3bc3765a56810b32e2ca65`を使った。target GCCはBootlin 2025.08-1の14.3.0、kernelは6.18.64、image生成時のmke2fsは1.47.4である。QEMUは11.1.3で、実際のserial logに次の行がある。

```text
run-qemu: sha256 8b5c759a21dd5d841d96b37be4e60e3b324869dff22250b581c856e36ac15b73  /usr/local/bin/qemu-system-aarch64
```

以下の`/work`は`docker/msd-dev`がrepositoryをmountする固定pathである。実行時にはstdout/stderrを`output-cryptsetup-review/`の別logに保存した。QEMUは元imageの写しを使い、Aはp5、Bはp6から起動する。version probeのevidence引数は新規directoryとし、既存directoryなら停止する。

```sh
docker/msd-dev nice -n 19 ionice -c 3 make -C vendor/buildroot \
  BR2_EXTERNAL=/work O=/work/output-cryptsetup-289 msd_cardputerzero_defconfig
docker/msd-dev nice -n 19 ionice -c 3 make -C output-cryptsetup-289 -j4
# 基準のimage・最終設定・legal-info・show-infoを別に保存してからoverrideを追加する。
docker/msd-dev nice -n 19 ionice -c 3 make -C vendor/buildroot \
  BR2_EXTERNAL=/work O=/work/output-cryptsetup-289-new msd_cardputerzero_defconfig
docker/msd-dev nice -n 19 ionice -c 3 make -C output-cryptsetup-289-new -j4
docker/msd-dev nice -n 19 ionice -c 3 make -C output-cryptsetup-289-new legal-info
OUTPUT_DIR="$PWD/output-cryptsetup-289-new" docker/msd-dev board/cardputerzero/qemu/test-boot.sh
OUTPUT_DIR="$PWD/output-cryptsetup-289-new" docker/msd-dev board/cardputerzero/qemu/test-ab.sh
docker/msd-dev python3 board/cardputerzero/tools/bench/cryptsetup-version.py \
  /work/output-cryptsetup-289-new /work/output-cryptsetup-review/target-new 2.8.9
```

## 結果

### build・target・起動

新旧の製品構成のbuildはともに終了値0。新版のdownload時に外部hashの一致を確認した。

```text
cryptsetup-2.8.9.tar.xz: OK (sha256: 8667085a4f59174928948b501b4a2a68f7f1cce1cfe46170b8f40fa6534742b3)
ok - QEMU target cryptsetup 2.8.7; status=0; QMP quit; exit=0
ok - QEMU target cryptsetup 2.8.9; status=0; QMP quit; exit=0
```

新版guestの実出力は`cryptsetup 2.8.9 flags: UDEV BLKID KEYRING KERNEL_CAPI`、`CRYPTSETUP_STATUS=0`。dev imageのcryptsetupをtargetの版として扱っていない。libraryのSONAMEは`libcryptsetup.so.12`を維持した。

| 確認・指標 | 基準2.8.7 | 新版2.8.9 |
|---|---:|---:|
| Aのtest-boot終了値 / readyまでの秒数 | 0 / 46 | 0 / 43 |
| Bのtest-ab終了値 / readyまでの秒数 | 0 / 44 | 0 / 46 |
| Image（bytes） | 19,286,528 | 19,286,528 |
| rootfs.squashfs（bytes） | 24,023,040 | 24,027,136 |
| sdcard.img（bytes） | 771,751,936 | 771,751,936 |
| targetのusr/sbin/cryptsetup（bytes） | 224,112 | 228,208 |

4回の起動と2回の成功したversion probeはいずれもQMP quit後に終了値0、fallbackなし。rootfsは4,096 bytes増えた。kernel設定は同じだが、build時刻や版情報を含む独立buildなのでimageのhashは異なる。容量差のすべてをcryptsetup単独の差とはしない。各1回、別の負荷と並行した測定であり、起動性能の優劣は結論しない。

ccacheの終了時累計は、基準が110,616 cacheable calls中58,056 hits、新版が127,549中73,787 hits。cache上限は5 GiBで、保存量は各約1.2 GiB。基準の開始前統計は未採取で、途中と終了時だけを保存した。buildの総時間も未計測であり、これらをbuild時間の比較には使わない。

### 最終設定・license・CVE

最終kernel `.config`はコメントを除き、無効項目も`CONFIG_NAME=n`として全項目をsortして比較した。6,845 symbolの差は0、正規化SHA-256は両側とも`a020fa0b8957ba82b54695c555a7c1f06e8a02e12a4e975aebe3b6983450cf2b`。Buildrootの3,360項目は`BR2_EXTERNAL_MSD_VERSION`だけが`v0.0.0-128-ge478fde`から末尾`-dirty`付きへ変わった。基準defconfig後に本変更を書き、新版を構成したためであり、featureの削除や無効化ではない。

新旧ともsource展開済みの出力先で`legal-info`が終了値0。cryptsetupのlicense 5 fileはすべてhash一致で、対象のhash欠落・ERRORはない。target manifestとshow-infoのpackage版差はcryptsetup 2.8.7から2.8.9だけで、license宣言と依存は変わらなかった。

一方、両側に次の既存WARNINGが残った。Buildroot source未収録と外部toolchainのlicense指定不足は配布前の残件であり、今回の検査を配布物全体の許諾確認完了とは扱わない。toolchainの出典は`https://toolchains.bootlin.com/downloads/releases/toolchains/aarch64/tarballs`の`aarch64--glibc--stable-2025.08-1.tar.xz`である。

```text
WARNING: the Buildroot source code has not been saved
WARNING: toolchain-external-bootlin-2025.08-1: cannot save license (TOOLCHAIN_EXTERNAL_BOOTLIN_LICENSE_FILES not defined)
```

security workflowと同じ`generate-cyclonedx`、`set-kernel-version.py`、`cve-monitor.py cve-check --no-nvd-update --include-resolved`を使った。公式NVD feedから新たに取得し、両側を同じsnapshot `2503f54c59a86876fdc686059b0943915e8e0adff5d48c52b449d5cfee77407a`で判定した。同期は2026-11-26 05:23:13 UTC、432,459件。CVEとcomponentの組で数えたexploitableは両側ともtarget 145、host 4、追加・減少0。hostのin_triageも2件のままである。これはCPEによるscanner判定であり、全件の実到達性・悪用可能性の確認や、2.8.9の修正がすべてCVE登録済みであることの証明ではない。

再生成する場合は各build後の`show-info`を入力にする。新版もbuild時のHEADは基準の40桁SHAで、未commitの入力差はCSVのsource hashで識別する。

```sh
docker/msd-dev make -s -C output-cryptsetup-289-new show-info > show-info.json
docker/msd-dev python3 vendor/buildroot/utils/generate-cyclonedx \
  --in-file show-info.json --project-name msd-linux \
  --project-version e478fde1c2dc5bbe459154418e9c79deef5ad8bb > sbom.cdx.json
docker/msd-dev python3 .github/scripts/set-kernel-version.py sbom.cdx.json \
  --show-info show-info.json --project-version e478fde1c2dc5bbe459154418e9c79deef5ad8bb
docker/msd-dev nice -n 19 ionice -c 3 python3 .github/scripts/fetch-nvd.py \
  --nvd-path dl/buildroot-nvd/current
docker/msd-dev nice -n 19 ionice -c 3 python3 .github/scripts/cve-monitor.py cve-check \
  --nvd-path /work/dl/buildroot-nvd/current --no-nvd-update --include-resolved \
  --in-file /work/sbom.cdx.json --out-file /work/vex.cdx.json
```

再取得したNVDは別snapshotになり得る。CSVには今回のimage、入力、設定、licenseとtext logのhashを収録した。大きなbuild logやimage本体はcommitしない。上記の構築・起動・監査commandで再実行できるが、build時刻、開発用鍵、版情報、NVDの更新があるため同じhashになる保証はない。

### host試験・失敗した初回

関連host試験はcheck-pins、qemu-boot 13件、msd-update、msd-data-grow、fs-compare-v2 74件が成功した。version parserは空出力、誤版、rc、欠落・重複、非0 status、echoやprompt付きの偽行を拒否する。pin監視はstable系列、override撤去、rc除外、不正・重複・欠落・offlineを試験した。実際のupstream照合でも固定2.8.9が最新、固定Buildroot 2.8.7ではoverrideを維持する結果だった。

初回の失敗も残す。

- pin試験の「全て最新」fixtureに旧recipe 2.8.7と新index 2.8.9を混在させて失敗した。既存のassertは変えず、基準fixtureと追加した更新fixtureを分け、再試験は成功した。
- 最初の基準version probeは、echoを止めたshellの`# `に正常なversion出力が続き、全文一致が拒否した。guestのversionとstatusは正常だった。実行前に改行を出し、別evidence directoryで再試験した。最初のfallback SIGTERMは判定失敗後のcleanupであり、host中断とは分類しない。
- 新版SBOMにcommit以外のproject-versionを渡してhelperが拒否した。生成し直し、実際の40桁HEADで検査した。buildや起動を再実行したものではない。
- 集計の初回はvirtual packageにversionがないため停止し、次にBuildrootの`-dirty`差を検出した。virtual packageを区別し、差を消さずに上記のmetadata差1件として記録した。kernel設定差を見逃す例外は加えていない。
- リンク検査は未stageの新規文書で停止し、stage後は上流source内のlicense pathを本リポジトリの文書と誤認して停止した。原文は変えず、既存のallowlistにfileとtokenが完全一致する8組を追加した。検査器本体やlicenseの検査は変えていない。

以上の範囲でcryptsetup 2.8.9を採用する。`/data`のformat・暗号設定、S02前のearly-I/Oの順序や制御は変えない。

## 未確認の範囲

QEMUでLCD・keyboard、実SD、FTL、電源断、CM0でのArgon2時間や暗号性能は確認できない。`/data`のLUKS2+Btrfsへの移行自体も今回の対象外である。
