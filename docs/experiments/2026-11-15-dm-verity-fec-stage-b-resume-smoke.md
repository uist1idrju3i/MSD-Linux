# B3 stage B再開smoke: 通常経路成功、RAM clean停止

[実験索引](README.md) / [事前登録・再開前amendment](2026-11-15-dm-verity-fec-followup-prereg.md) / [初回停止](2026-11-15-dm-verity-fec-stage-b-smoke.md)

## 結果と状態

2026-11-15 UTC。利用者の承認を受けてreadall専用script・新pack・initcall_debug復元を先に固定し、clean smokeから再開しました。**通常経路はreadall完了→ready→loginを観測して成功しましたが、次のRAM経路はlibresolvのload失敗でinit終了panicとなり、再停止しました。**

新しいclean失敗の停止規則に従い、後続8条件、B正式5反復、C〜Fには進んでいません。期待・判定は変更せず、RAM用aliasの修正・再試行も未実施です。これはFECやverityによるpanicではありません。

## 実行前の固定

| 項目 | 条件 |
|---|---|
| 実行前amendment | [2b1a227](https://github.com/uist1idrju3i/MSD-Linux/commit/2b1a22731c7df59b993e59760e5bbde879030845)。修正・再packより前にcommit・push |
| 計測器source | [fe913e4](https://github.com/uist1idrju3i/MSD-Linux/commit/fe913e4)。host fixtureとstandalone DockerのShellCheck後にcommit・push |
| 基準 | stage A結果と初回B停止を含むstack。同じ6.18.59-v8-b3trace kernel、QEMU raspi3ap、icount shift=0、512M |
| Docker | 固定image `sha256:47cc0b8cfd878a4fb413c376d52a2b6a9199454c97b1d2aec8df7a3a1b4a8e7d`。standalone clone内で生成・QEMU |
| kernel | SHA-256 `bdd129e84f953f65fa2cbedac957c4b28c55ccccc9f8521e37dca3dd608e3c69`。再buildなし、前回の計装binaryをhash照合して再利用 |
| QEMU | 11.1.2、SHA-256 `c8cf5be13646711580e18346dcd036c0f2a210dd90f84bf784247c5838940410`。版・build/compiler情報は環境JSONへ保存 |
| 通常readall | inittabから`/bin/sh /usr/libexec/b3-readall.sh`。dd失敗時はset -eで終了し、成功時だけ完了markerを/dev/kmsgへ出す |
| cmdline | initcall_debugを復元。ignore_loglevel/loglevel=8、msd.sweep=1、msd.boottime=1を維持 |
| mode/上限 | cleanはpanic・watchdog無効・no-reboot。600秒/boot、各条件1 smoke、その後正式5反復の予定 |
| RAM | 同じ未破損data/verity/FECを未mountのdm-0から読む研究用initramfs。今回はscript開始前に失敗 |

host fixtureはBusyBox initの特殊文字判定と先頭exec追加を再現します。旧inittab行ではddが終了値0でも末尾markerが出ず、新しい明示的shell呼出しでは出ることを確認しました。存在しない入力deviceでは非0終了・markerなし、空/重複inittabは拒否します。cmdlineのinitcall_debugにもassertを追加しました。

### 新packと入力照合

| 項目 | 値 |
|---|---|
| 元pack SHA-256 | `35bbf54e436ca45f678809a6a561b6a04c7e50bca8f5b901daf18736ced8c6e0` |
| 新pack SHA-256 | `fedf1abe7f222f719b2287885079e0bcfe052f351f266b6ecbd684e26ba0a205` |
| SquashFS SHA-256 | `5f100eb815b6032d3fce3b56b8a54764efaab6b69bea12783de6fc91a6151b43` |
| 新root hash | crc32c `3711f47a`。旧A/Bの94ffe4cbとは別 |
| 配置 | D=5832、H=5833、hash 7 block、fec_start=5840、roots8、fec_bytes=786432 |
| pack設定 | zstd、block 131072、noappend/all-root/no-xattrs、mkfs epoch=1794763837 |
| RAM initramfs SHA-256 | `95aa45499badb5ba6952062eb4e903fe7239c438133777dcebcead6e3421d8b7` |

元seed manifestとformatter binary/sourceを照合してから、元treeの写しだけへhelperとinittabを適用しました。SD p5読戻し、既知消失decoderによる検査を行い、生成後に全10 manifestを別のhash計算で再照合しました。BのF3全6条件の破損bytes・注入offsetが同じこと、全cmdlineへのinitcall_debug復元も開始前に確認しています。caseはread-only mountし、実行器も各case開始時に照合します。

## raw値と停止

[CSV](2026-11-15-dm-verity-fec-stage-b-resume-smoke.csv)のvalidは機能期待との一致です。boot0を含む2試行を両方残し、成功・失敗のwallをまとめた性能比較はしません。

| case/repeat | wall秒 | 独立完了marker | 結果・停止 |
|---|---:|---|---|
| B-clean-normal/0 | 233.07458338499418 | readall→ready→loginあり | 合格・observed |
| B-clean-ram/0 | 213.33907512100996 | B3_RAM_BEGIN/ENDともなし | 不合格・unexpected-terminal、generic panic |

2試行のwall合計は446.41365850600414秒です。どちらも観測後にhostが停止し、最終status 0を自然終了成功とは数えていません。timeoutではありません。

```text
[    1.689883] verity-readall-complete
[    2.699633] MSD/Linux ready
...
msd login:
```

RAM側は次のエラーで終了しました。

```text
/bin/busybox: error while loading shared libraries: libresolv.so.2: cannot open shared object file: No such file or directory
[    1.797173] Kernel panic - not syncing: Attempted to kill init! exitcode=0x00007f00
```

## RAM失敗の原因切り分け

最有力原因は、元treeにある`lib64 -> lib`と`usr/lib64 -> lib`をinitramfsが保存しなかったことです。**library本体の収録漏れという説明は反証されました。** 実CPIOを解析するとlib/libresolv.so.2は55,360 byteあり、SHA-256は`f12e4378881a6de7651dcaaa5de7b611d755d29b629b8864e469d018ecb58715`で元treeと一致しました。BusyBox・interpreter本体も元treeと一致します。

一方、実CPIOにはlib64とusr/lib64がありません。実loaderには独立した既定dir文字列`/lib64/`と`/usr/lib64/`があり、`/lib/`と`/usr/lib/`はありません。BusyBoxの実DT_NEEDEDはlibresolv.so.2/libc.so.6/ld-linux-aarch64.so.1で、RPATH/RUNPATHはありません。kernelが示したinit環境はHOME/TERMだけで、LD_LIBRARY_PATHも渡していません。

反証として、aliasなしでも探索できる別経路を調べました。この静的検査では/lib等のfallbackは確認できず、RPATHもありません。ld.so.cacheは元treeにもCPIOにもないため、cacheの除外だけでは通常経路との差を説明できません。通常rootfsにはaliasがあり、同じBusyBoxで起動できています。よってalias欠落による探索先不一致を強く支持します。ただしloaderのopenat動的traceは未取得です。修正後の起動成功はまだ観測していません。

初期fixtureはlib/usr/lib内のpayloadを検査しましたが、lib64 aliasと実loaderの探索先まで検査していませんでした。今回の失敗はその検査不足も示しています。

## 仮説評価・予算・再開待ち

- 旧readall marker省略: exec変換のhost負対照と、新helperでの実boot成功が修正を支持します。単発なので成功率・性能の結論は出しません。旧Aや初回Bの値も遡って成功へ変えません。
- F3再入guard・mode・RAM読取り仮説: 破損条件もRAM読取りも未実行で未判定です。clean2回のguard hit 0は反証ではありません。EIOの訂正成功を反証として残す期待も変えません。
- F6自然終了/reset、C〜F: 新たな測定なし。正式Bは0/50、C〜Fも0回です。

保守的時計は11/15 12:17:52 UTC開始、deadlineは11/17 00:17:52 UTCのままです。今回の停止時点で約5時間半が経過しました。新たに全43 smokeと正式215 bootを行うと仮置きし、240秒/bootで17.2時間、準備4時間を加えると累積約27時間の見込みです。36時間停止ではなくclean失敗による停止ですが、未測定条件が多く、再開時に再見積りします。空きは新生成後158 GiBでした。

**次の提案は、元treeのlib64 aliasを研究用initramfsへ保存し、DT_NEEDED・実loader探索先の依存閉包を検査するfixtureを追加することです。** SD packは変えず、新initramfs hashと日付付きamendmentを先に固定してからclean smokeを再開する承認を待ちます。現在は修正・再bootしていません。

## 証拠・再現・検査

[evidence.tar.gz](2026-11-15-dm-verity-fec-stage-b-resume-smoke/evidence.tar.gz)は152,684 byte、SHA-256は`7e07d0604854f6f4f93222ea9c592bbb71b2aa798258e7356d6c9705057bbe46`です。82 fileをhash照合し、別にMANIFEST.jsonを含みます。全serial/QMP/判定JSON、全10入力manifest/params/注入位置/独立検査、再pack設定、実行source、CPIO全117 entryのmode/hash/link、ELF dynamic情報、host検査・初回失敗logを保存しました。大きなbinaryは永続保管し、公開archiveにはhashを収録しています。

環境JSONのkernel build欄は前回のbuild記録を引き継いでいます。今回の再buildを示すものではありません。空き容量も旧free_gib欄は参考値160のままなので、今回採取したfree_bytes欄を使います。raw metadataを事後に修正せず、この区別を明示しています。

生成前の環境設定で2件の問題がありました。rootless Dockerのbind ownerがcontainer内では0なのにbuilder/1001で実行し、Gitのdubious ownershipでShellCheckが止まりました。runtimeのuidとownerを照合し、repo wrapperと同じcontainer uid 0を使って解消しました。Git configは変更していません。最初のpackはSDK wrapperが要求する固定prefixへのmountがなく、mksquashfs.origを見つけられず終了値127でした。SDKを/work/output-integrityへread-only mountして解消し、新しい生成先へ切り替えました。失敗先も保持しています。

再現は固定image・standalone cloneで、SDKを/work/output-integrity、元seedを/seed、trace kernelを/kernelへread-only mountします。

```sh
python3 board/cardputerzero/tools/bench/dm-verity-fec/followup.py prepare-b +  /seed/F0-A3 /kernel/arch/arm64/boot/Image /seed/seed/F0-A2/rootfs-tree +  output-b3-cases-b3 --host /work/output-integrity/host
python3 board/cardputerzero/tools/bench/dm-verity-fec/followup.py run +  /cases output-b3-smoke-b3 --runs 1 --timeout 600
```

/casesは生成済みcaseのread-only mountです。既存の出力先は拒否するため、再実行では新しい名前にします。実行中のscriptは変更していません。

実行前のstandalone Docker検査では、既存format suiteがPASS、新fixtureは7件OK、rootless設定修正後のtracked ShellCheckは終了値0でした。提出対象はlinks/JIS/doc-sizeと各検査器test、変更文書のyomiyasuも含みます。旧raw/CSV/期待、RS研究限定・製品出荷禁止、03914台帳同期保留を維持します。実機・LCD・firmware tryboot・電断・A/B復旧は未確認です。
