# B3 stage F：restart後のRESETと2回目banner

[実験索引](README.md) / [事前登録・amendment](2026-11-15-dm-verity-fec-followup-prereg.md) / [host全43入力](2026-11-15-dm-verity-fec-host-dry-resume.md) / [先行E](2026-11-16-dm-verity-fec-stage-e.md)

## 条件と実行

2026-11-16 UTC、F-resetの1 smoke後、正式5反復を実行しました。既登録の`restart-reset`期待は変更していません。同columnのdata 9 block（0,24,...,192）のbyte 0をXOR `0xff`で反転したcrc32c/roots8入力です。root hashは`3711f47a`、dataは5832 block、4 KiB/block。全offset・注入前後byte・column/symbolはarchiveのcase設定にあります。

standalone Docker cloneのbench sourceは`400ff62`から不変で、branchの実行前HEADはE結果の`4125a0e`です。QEMU 11.1.2、研究kernel 6.18.59-v8-b3trace、Buildroot/GCC・host OSは[正式B](2026-11-15-dm-verity-fec-stage-b.md)と同じです。kernel/rootfsはwarm artifactを再利用し、reconfigure・再build・ccache測定はしていません。

```text
run-qemu: sha256 c8cf5be13646711580e18346dcd036c0f2a210dd90f84bf784247c5838940410  qemu-system-aarch64
run-qemu: sha256 bdd129e84f953f65fa2cbedac957c4b28c55ccccc9f8521e37dca3dd608e3c69  Image
clean pack: fedf1abe7f222f719b2287885079e0bcfe052f351f266b6ecbd684e26ba0a205
Docker: sha256:47cc0b8cfd878a4fb413c376d52a2b6a9199454c97b1d2aec8df7a3a1b4a8e7d
```

binary hash行はserial実出力のパスだけ省略しました。全入力はhostで事前照合済みで、runnerもcaseごとにmanifestを照合しました。rootless Dockerのcontainer UID 0（hostのclone所有者へ写るUID）で、standalone cloneを`/work`、保存入力をread-onlyの`/prior`へmountしました。workdirは`/work`、`PYTHONDONTWRITEBYTECODE=1`です。正常化後のsmoke・正式ともfresh出力先を使いました。

```sh
python3 board/cardputerzero/tools/bench/dm-verity-fec/followup.py run \
  /prior/cases-f output-f4-smoke --runs 1
python3 board/cardputerzero/tools/bench/dm-verity-fec/followup.py run \
  /prior/cases-f output-f4-formal --runs 5
```

restart mode、`QEMU_WATCHDOG=1`、`-no-reboot`なし、600秒/trialです。watchdog有効化は実行前amendmentを継承します。QMP clientはcapabilitiesを有効にしてeventを受信するだけで、hostから`system_reset`を送っていません。成功には破損検出→restart→QMP RESET→2回目Linux bannerを要求し、ready・別slot選択は要求も検証もしていません。ここでの6 trialは完全起動12回を意味しません。

QEMU環境変数は固定source・case設定、実cmdlineはserialに保存しました。bootごとのPopen argv/env全体の独立snapshotは未保存です。入力不一致・clean失敗・未観測timeout・判断を要する計測器失敗で停止する規則を維持しました。F自体にclean条件はありません。

## raw結果

smokeは1/1、正式は5/5期待一致です。全6件の非丸め値は[CSV](2026-11-16-dm-verity-fec-stage-f.csv)、QMP受信時刻はarchiveの各`qmp.json`にあります。次表だけ小数第3位へ丸めています。全正式trialでbanner数2、guard hit 0、panic/readyなしでした。

| repeat | wall秒 | QMP RESET受信のhost経過秒 | 期待一致 |
|---:|---:|---:|---|
| 0 | 219.403 | 217.854 | 一致 |
| 1 | 246.847 | 245.294 | 一致 |
| 2 | 240.942 | 239.393 | 一致 |
| 3 | 218.427 | 216.873 | 一致 |
| 4 | 229.236 | 227.684 | 一致 |

正式wallの中央値は229.236秒、最小218.427秒、最大246.847秒。smokeは228.500546071009秒、RESET受信は226.9460310510185秒でした。smokeを正式反復の統計へ混ぜていません。

全6件のserialで、最初のbanner→data corruption→restart marker→2回目banner→hostのsignal 15を確認しました。QMPは全件で`after_restart_marker=true`のRESETが1件、`guest=true`、`reason=guest-reset`です。代表のsmokeから、共通prefix・版の後半・timestampを省略した抜粋です。

```text
Linux version 6.18.59-v8-b3trace ...
data block 0 is corrupted
reboot: Restarting system with command 'dm-verity device corrupted'
Linux version 6.18.59-v8-b3trace ...
qemu-system-aarch64: terminating on signal 15 from pid 1 (python3)
```

```json
{"event":"RESET","data":{"guest":true,"reason":"guest-reset"},"host_elapsed_seconds":226.9460310510185,"after_restart_marker":true}
```

**F6のRESET継続観測を、この入力・QEMU・watchdog有効条件で5回支持**しました。機能判定時はprocess継続中で`exit_status=null`、`stop_reason=observed`です。2回目bannerを観測してからhost停止しており、host SIGTERMや最終exit 0を成功根拠にしていません。段階A/Bの`-no-reboot`下の自然終了観測とは別です。2回目のreadall・login、異なるslotからの復旧、実機firmwareの選択・watchdogを検証した結果ではありません。

## 失敗・環境設定の訂正

最初のlaunchは出力directory作成時に次の例外で終了しました。QEMUは起動せず0 boot、出力先も生成されず、driver wallは0.575秒です。smokeや正式5回に含めていません。

```text
PermissionError: [Errno 13] Permission denied: '/work/output-f4-smoke'
```

host UID 1001をcontainerへそのまま指定したのが原因です。Dockerの`name=rootless`とUID mappingを確認すると、container UID 0がhost UID 1001へ写り、containerの1001は別の従属UIDへ写ります。cloneはhost UID 1001所有・0755で、container UID 0では所有者write権限が得られる対照を確認しました。UID指定だけを合わせ、権限・所有者・入力・期待・scriptは変更していません。実験条件を変えるamendmentではなくlaunch環境の訂正として記録します。

初回のstderr・wallは別保存してから再実行し、archiveの`raw/smoke/setup-failure.log`、`setup-failure-time.log`、`setup-failure-note.md`へ収録しました。以降の全6 trialは成功し、入力不一致・timeout・中断はありません。

## 保存・検査・予算

[archive](2026-11-16-dm-verity-fec-stage-f/evidence.tar.gz)はhash対象58 memberと`MANIFEST.json`、275,773 byte、SHA-256 `0e4fb7eca1866542491b82da8c6a66b718c719a2391a99eb711834087b3aa70f`です。manifestに列挙された58 memberを再読込みしてhash照合しました。全6件のserial/QMP/判定、case設定・入力manifest・注入位置、固定source、driver log・wall、collector・summaryと上の失敗証拠を保存しています。

```text
ok - stage F: 6 trials, 5 formal, 5 formal matches; 58 members hash-verified
formal_boot_wall_sum=1154.854771015991
wall_seconds=1158.255
```

smoke driver wallは231.619秒、正式は1158.255秒（19分18.255秒）です。終了時の保守的累積時計は約23時間34分。追加bootの予定はなく、保存・検査に1時間を見ても約24時間34分で、deadline 2026-11-17 00:17:52 UTC・36時間上限の延長は不要です。wallはhost資源の記録で、実機性能ではありません。

文書検査とyomiyasuの結果はcommit・報告に添付します。bench sourceはhost fixture後から不変で、追加ShellCheckは不要です。実機SD/LCD/firmware tryboot/電断/A-B復旧は未確認。RS研究限定・製品出荷禁止、03914台帳同期保留を維持します。
