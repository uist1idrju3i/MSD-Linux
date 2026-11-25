# 実験記録

- [収録監査](2026-11-13-research-audit.md)：12主題、raw保全・fs-compareのhash照合・未保存image一覧。

[文書案内](../README.md) / [調査索引](../../RESEARCH.md)。「完了」は記載条件下の実験終了で、製品採用・実機確認とは別です。Yoctoは見送り。[Buildroot還元](../research/yocto-migration/buildroot-lessons.md)に再点検範囲を記載。

手順は`.agents/skills/experiment-record/SKILL.md`。1件1ファイル、名前は`YYYY-MM-DD-sNN-<short>.md`、生の値は同名CSVです。S1〜S17以外は`sNN-`を省き、全件を載せます。覆った結論は消さず「置換」で新記録へリンクします。

[2026年10月の実験記録](2026-10-index.md)は月別の索引に収録。以下は2026年11月分。

| ID | S 番号 | 日付 | 状態 | 結論 |
|---|---|---|---|---|
| [S02前のI/O gate](2026-11-25-early-io.md) | [CSV](2026-11-25-early-io.csv) | 2026-11-25 | host 17試験・既存image再packのQEMU A/Bと失敗対照 | A/BはQMP timeout後の単独再試行で成功。4 marker、guestの3秒期限、/data前の停止を確認。製品full build・実機は未確認 |
| [v2 Wi-Fi SDIO診断](2026-11-24-s04-fs-compare-v2-wifi-sdio.md) | [CSV](2026-11-24-s04-fs-compare-v2-wifi-sdio.csv) | 2026-11-24 | 試行06の誤分類を修正・別出力で再判定 | 原log 206/206に同じ診断。旧fatal 1から新0、原結果は失敗のまま保持。新しい代表21件・851件・mainは未実施 |
| [OpenSSL 4機能](2026-11-23-openssl-features.md) | [CSV](2026-11-23-openssl-features.csv) | 2026-11-23 | 同一commitのcold full build・QEMU A/B完了 | rootfs -598,724 bytes、SquashFS -212,992 bytes。19 moduleと暗号algorithm一覧一致。証明書圧縮の未利用を証明できず4項目組の製品採用は見送り |
| [SDIO firmware配送](2026-11-23-sdio-firmware.md) | [CSV](2026-11-23-sdio-firmware.csv) | 2026-11-23 | 現行CI再pack・QEMU比較完了 | CYW43439とCM0専用43436sを併存保持。rootfs −1,759,026 bytes、SquashFS −1,069,056 bytes。前後A/Bの19 module一致。SDIO・BTの実機読込みは未確認 |
| [kbd tool配送の最小化](2026-11-23-kbd-tools.md) | [CSV](2026-11-23-kbd-tools.csv) | 2026-11-23 | 現行CIの再pack・QEMU比較完了 | rootfs −532,908 bytes、SquashFS −147,456 bytes。前後A/Bのloadkeys終了0・19 module一致、失敗対照を拒否。実機keyboard未確認 |
| [libgomp配送削減](2026-11-23-libgomp-prune.md) | [CSV](2026-11-23-libgomp-prune.csv) | 2026-11-23 | 旧構成の容量・前後A/Bと現行CIの再監査完了 | 旧構成: rootfs −302,440 bytes、SquashFS −135,168 bytes、19 module一致。現行184 ELFに参照未検出、削除後A/B成功。現行の前後比較は未実施 |
| [module index削除](2026-11-23-module-index-prune.md) | [CSV](2026-11-23-module-index-prune.csv) | 2026-11-23 | 既存image再pack・QEMU比較完了 | rootfs −938,282 bytes、SquashFS −167,936 bytes。前後A/Bの19 module一致。測定器は自前indexでlibkmod load成功。最新製品buildはCI待ち |
| [module binary index](2026-11-23-module-binary-index.md) | [CSV](2026-11-23-module-binary-index.csv) | 2026-11-23 | 削除前に停止 | 既存5 fileは938,282 bytes。通常起動はBusyBoxだがOpenSSL測定器にlibkmod利用あり。製品変更・新規build・QEMU・圧縮差は未実施 |
| [OpenSSL C1採用](2026-11-23-openssl-c1.md) | [CSV](2026-11-23-openssl-c1.csv) | 2026-11-23 | host接続確認完了 | TLS最低版1.2・SECLEVEL=2をpost-buildで適用。外部TLS13接続、A/A、hostname不一致の計16 caseが期待どおり。製品build・A/B・実機は未確認 |
| [SSH client比較（#9）](2026-11-23-ssh-client-compare.md) | [CSV](2026-11-23-ssh-client-compare.csv) | 2026-11-23 | QEMU比較完了・製品未導入 | 3候補でEd25519認証・別host key拒否を各5回。OpenSSHの追加797,448 bytes・圧縮差327,680 bytes。失敗試行・暗号・RAM内writeは本文 |
| [RAUC streaming](2026-11-23-rauc-streaming-poc.md) | [CSV](2026-11-23-rauc-streaming-poc.csv) | 2026-11-23 | host metadata各5回・Phase A未完 | 206・302成功、200拒否、403/429/切断のretry観測。Retry-Afterは待たない。実Releaseはassetなし。install・QEMU・adaptive再利用は未実施 |
| [deps一括更新](2026-11-22-deps-update.md) | [CSV](2026-11-22-deps-update.csv) | 2026-11-22 | build・icount gate・kernel .config差分確認 | snapshot不整合をsnapshot更新で解消。QEMU 11.1.3は現行11.1.2比1.09xでgate成立。kernel差分は新規moduleのみ。実機・bq27220未確認 |
| [RAID6 PQ](2026-11-19-raid6-pq.md) | [CSV](2026-11-19-raid6-pq.csv) | 2026-11-19 | QEMU各5回とA/A完了 | PQ benchmarkだけを省略。Btrfs mount・scrub成功。実機時間・algorithm未確認 |
| [v2第4段A](2026-11-19-s04-fs-compare-v2-stage4.md) | [CSV](2026-11-19-s04-fs-compare-v2-stage4.csv) | 2026-11-19 | 試行05はsmoke 85件目、06は代表10件目で停止 | 06のWi-Fi SDIO誤分類を修正し別出力で再判定。原結果は失敗のまま保持。851件完了・mainは未実施 |
| [v2負対照のsentinel](2026-11-23-s04-fs-compare-v2-negative-sentinel.md) | [CSV](2026-11-23-s04-fs-compare-v2-negative-sentinel.csv) | 2026-11-23 | 同期済みsentinelでF1・E1・E2の単独診断成功 | host 68試験成功。全smokeとmainは未実施。事前確認失敗3件も保全 |
| [cnf](2026-11-18-openssl-cnf.md) | [CSV](2026-11-18-openssl-cnf.csv) | 2026-11-18 | QEMU各3回 | C1/C2成功・未適用 |
| [syncfs](2026-11-18-data-syncfs.md) | [CSV](2026-11-18-data-syncfs.csv) | 2026-11-18 | QEMU各5回・完了 | idle 88から0。通常起動は同期省略 |
| [idle残量](2026-11-17-data-idle-residual.md) | なし | 2026-11-17 | QEMU 5回 | 88 sectorはmetadataの遅延writeback |
| [NVD公式feed](2026-11-17-nvd-official-feed.md) | [CSV](2026-11-17-nvd-official-feed.csv) | 2026-11-17 | local単回 | 426,444 CVE。CI cache・Release未確認 |
| [同期初期化](2026-11-17-data-sync-itable.md) | [CSV](2026-11-17-data-sync-itable.csv) | 2026-11-17 | QEMU各3回・idle基準未達 | table同期化。boot 16,848、idle1 88。progress・既存SD未対応 |
| [B3追試B〜F総括](2026-11-16-dm-verity-fec-followup-summary.md) | 各段階のCSV | 2026-11-16 | 43条件・215正式trial | 正式195一致。BのEIO10件とCのlower hash10件は反証。QEMU限定 |
| [2026-11-16-dm-verity-fec-stage-f](2026-11-16-dm-verity-fec-stage-f.md) | [CSV](2026-11-16-dm-verity-fec-stage-f.csv) | 2026-11-16 | 1 smoke＋5正式trial | 全期待一致。guest-resetと2回目bannerを観測。初回launch失敗0 bootも保存。実機A/B復帰ではない |
| [2026-11-16-dm-verity-fec-stage-e](2026-11-16-dm-verity-fec-stage-e.md) | [CSV](2026-11-16-dm-verity-fec-stage-e.csv) | 2026-11-16 | 4 smoke＋20正式boot | 全期待一致。9/24 blockとも同column集中はpanic、異column分散は訂正read成功。総block数だけの保証・実機検証ではない |
| [2026-11-16-dm-verity-fec-stage-d](2026-11-16-dm-verity-fec-stage-d.md) | [CSV](2026-11-16-dm-verity-fec-stage-d.csv) | 2026-11-16 | 18 smoke＋90正式boot | 全期待一致。roots2超過はRS正値後のhash不一致で拒否。全誤訂正・実機への保証ではない |
| [2026-11-16-dm-verity-fec-stage-c](2026-11-16-dm-verity-fec-stage-c.md) | [CSV](2026-11-16-dm-verity-fec-stage-c.csv) | 2026-11-16 | 10 smoke＋50正式boot | 正式40一致、lower hash両端10 panicは正常読取り期待への反証。parity単独で修復を主張せず、実機未確認 |
| [2026-11-15-dm-verity-fec-stage-b](2026-11-15-dm-verity-fec-stage-b.md) | [CSV](2026-11-15-dm-verity-fec-stage-b.csv) | 2026-11-15 | 10 smoke＋50正式boot | clean成功、正式40一致・EIO10反証。再入guard→fatal方針を支持、EIOでは訂正後全read成功。実機未確認 |
| [2026-11-15-dm-verity-fec-host-dry-resume](2026-11-15-dm-verity-fec-host-dry-resume.md) | [CSV](2026-11-15-dm-verity-fec-host-dry-resume.csv) | 2026-11-15 | D18入力完了・全43入力照合 | CLIと回復判定を分離。完全一致12・別codeword2・拒否4、中間値を即時保存。boot結果は別記 |
| [2026-11-15-dm-verity-fec-host-dry](2026-11-15-dm-verity-fec-host-dry.md) | [CSV](2026-11-15-dm-verity-fec-host-dry.csv) | 2026-11-15 | 37/43入力生成・boot前停止 | alias閉包とB/C/E/Fはhost成功。Dの容量超過対照がCLI終了0・hash失敗表示となり停止。B clean再試行・正式B以降は未実行 |
| [2026-11-15-dm-verity-fec-stage-b-resume-smoke](2026-11-15-dm-verity-fec-stage-b-resume-smoke.md) | [CSV](2026-11-15-dm-verity-fec-stage-b-resume-smoke.csv) | 2026-11-15 | 通常clean成功・RAM clean停止 | 明示的shellのreadall markerは実bootで観測。RAMはlibrary探索失敗でinit終了panic、lib64 alias欠落を強く支持。正式B・C〜F未実行 |
| [2026-11-15-dm-verity-fec-stage-b-smoke](2026-11-15-dm-verity-fec-stage-b-smoke.md) | [CSV](2026-11-15-dm-verity-fec-stage-b-smoke.csv) | 2026-11-15 | 初回clean smoke停止 | ready/loginは出たがreadall markerなし。BusyBox initのexec変換と整合。利用者承認後の試行は上の再開記録へ分離 |
| [2026-11-15-dm-verity-fec-stage-a](2026-11-15-dm-verity-fec-stage-a.md) | [CSV](2026-11-15-dm-verity-fec-stage-a.csv) | 2026-11-15 | amendment後35 boot | v3期待35/35一致。F3はFEC内hash検査からpanicが5/5、F6はdriver有効で自然終了0が5/5。readall独立marker/login・module署名・実機は残件 |
| [2026-11-15-dm-verity-fec-stage-a-smoke](2026-11-15-dm-verity-fec-stage-a-smoke.md) | [CSV](2026-11-15-dm-verity-fec-stage-a-smoke.csv) | 2026-11-15 | 計測器smoke | v3の位置記録・既知消失復号・F3 mode対照とF6自然終了/reset分離。各1 bootのみで、正式反復・原因確定ではない |
| [2026-11-15-dm-verity-fec-followup-prereg](2026-11-15-dm-verity-fec-followup-prereg.md) | なし | 2026-11-15 | 事前登録・B〜F結果は総括参照 | 当初48条件・240 boot、Bの実行前amendmentで同一pack対照2条件追加。RSは研究限定、製品出荷は禁止 |
| [2026-11-15-boot-slot-banner](2026-11-15-boot-slot-banner.md) | なし | 2026-11-15 | host fixture・最終QEMU A/BとA sweep各1回 | DT優先とcmdline fallback。QEMU serialでslot行とready直前の順序を照合。初回rawも保存。English-onlyは限定承認、LCD/firmwareは実機待ち |
| [2026-11-15-storage-options-prereg](2026-11-15-storage-options-prereg.md) | なし | 2026-11-15 | 事前登録（実行前） | SquashFS圧縮matrix、verity(crc32c)+FEC+破損注入、LUKS cipher、btrfs dup+xxhash64+zstd圧縮、zram/zswapのoption全測定の計画。B1のhost速報は取得済み、正式記録は反復後。 |
| [2026-11-15-dm-verity-fec-corruption](2026-11-15-dm-verity-fec-corruption.md) | [結果](2026-11-15-dm-verity-fec-corruption.csv) | 2026-11-15 | 限定条件の35 boot | 1 byte反転の訂正・panicを観測。F3は旧ready期待と不一致。再入依存は有力な説明で原因未確定、F6はhost SIGTERMでrestart完了未確認。次回v2期待表を別に保存。 |
| [storage option分類](../research/storage/storage-option-coverage.md) | source監査 | 2026-11-15 | 未測定範囲を分類 | 固定版のhelp・parser・Kconfig入力、hash、全token分類CSVと照合fixture。性能の新規測定ではない。 |
| [2026-11-15-data-first-boot-writes](2026-11-15-data-first-boot-writes.md) | [測定](2026-11-15-data-first-boot-writes.csv) | 2026-11-15 | QEMU測定・原因特定 | 初回bootのp7への16,952 sectorは約97%がresize2fsの新規groupへのext4lazyinit。sfdiskはdisk側に16 sectorのみ、実処理は約570 sector。 |
| [2026-11-15-zram-builtin-vs-module](2026-11-15-zram-builtin-vs-module.md) | [測定](2026-11-15-zram-builtin-vs-module.csv) | 2026-11-15 | 完了（QEMU・icount、各6回） | zram `=y`と`=m`のt_readyはほぼ同じ（warm中央値1.645対1.640秒）。ただし`=m`はmodalias自動loadの対象外でswapが無効のまま。`=y`維持が妥当。実機は未測定。 |
| [2026-11-15-mksquashfs-matrix](2026-11-15-mksquashfs-matrix.md) | [測定](2026-11-15-mksquashfs-matrix.csv) | 2026-11-15 | 完了（host、138 run） | zstd 1M/l19=22.37MB、128K/l22比 -5.6%。l19/l22はサイズ一致だけで同じimageではない。build時間を採否理由にせず、条件付き22を保持。 |
| [2026-11-15-squashfs-boot-read-bench](2026-11-15-squashfs-boot-read-bench.md) | B2 | 2026-11-15 | 限定条件の40 boot | 全file読み出し・ready・RAMを観測。kernel約135 KB差、途中の計装追加、0.5秒RAM samplingがあり、l22に悪影響なしとは断定しない。random read p95・実機は未測定。 |
| [2026-11-13-cloudflare-analytics](2026-11-13-cloudflare-analytics.md) | [結果](2026-11-13-cloudflare-analytics.csv) | 2026-11-13 | production取得・ローカルCSP検査 | root 200と404の応答にbeaconを観測せず。公式の自動注入は同一origin送信なのでselfを追加。実送信と新CSPのproduction配信は未確認。 |
| [2026-11-13-release-signing-qemu](2026-11-13-release-signing-qemu.md) | [結果・hash](2026-11-13-release-signing-qemu.csv) | 2026-11-13 | QEMU受入・B指定起動 | run 43331379685の本番署名を同一versionで通常受理。改変signature・未署名を拒否しstandby不変。Bのversion・health commit確認。初回測定器timeoutを保存。実機firmware tryboot・実SDは未確認。 |
| [2026-11-13-pqc-groups](2026-11-13-pqc-groups.md) | [測定](2026-11-13-pqc-groups.csv) | 2026-11-13 | 判断資料・維持を決定 | OpenSSL 3.5.9のPQC 5構成の容量、VMの6 hostとQEMUを比較。同日利用者がDEFAULTとML-KEM維持を決定。ML-DSA／SLH-DSAは署名移行時に判断。実機・将来consumerは未確認。 |
| [2026-11-13-legal-info-supplement](2026-11-13-legal-info-supplement.md) | [採取値](2026-11-13-legal-info-supplement.csv) | 2026-11-13 | 実legal-info・hash照合 | 固定Buildroot archiveとBootlinの41 license fileを補足。原261 fileと警告2件は不変、A/A全50 fileが一致。23 source archive・patch・builder tree・Linux headers licenseは未収集。 |
| [2026-11-13-seedrng-zram](2026-11-13-seedrng-zram.md) | [測定](2026-11-13-seedrng-zram.csv) | 2026-11-13 | 実装・QEMU確認 | seed自動保存を停止し、built-in zramをconsole開始後に有効化。boot各5回、crng時刻、圧縮可能な負荷でswap使用を確認。実機と`=y`対`=m`の単独比較は未実施。 |
| [2026-11-12-write-inventory](2026-11-12-write-inventory.md) | [測定](2026-11-12-write-inventory.csv) | 2026-11-12 | QEMU測定、idle基準は未達 | 初回idleにp7の8320 sector増加。RAM配置を確認し既定timezoneをTokyoへ変更。拡張済み再bootも64 sector増え、原因の寄与と実機は未確認。 |
| [2026-11-12-pages-headers](2026-11-12-pages-headers.md) | [結果](2026-11-12-pages-headers.csv) | 2026-11-12 | 描画・preview応答確認 | 画素差0。pages.devでヘッダー配信確認。Analytics注入・実送信は未確認。 |
| [2026-11-12-openssl-minimal-plan](2026-11-12-openssl-minimal-plan.md) | [採取値](2026-11-12-openssl-minimal-plan.csv) / [入力](2026-11-12-openssl-minimal-plan.json) | 2026-11-12 | 静的採取・比較は計画 | 保存済み3.5.9の実引数・4 fileのhashとサイズ・ELF参照を照合。削減build、TLS、QEMU、実機の比較は未実施。 |
| [2026-11-12-release-signing-job](2026-11-12-release-signing-job.md) | [結果](2026-11-12-release-signing-job.csv) | 2026-11-12 | host・増分build確認済み | 公開鍵をSquashFSから照合。独立署名と負試験に成功。本番鍵・Environment job・実機は未確認。 |
| [2026-11-12-dev-image-snapshot](2026-11-12-dev-image-snapshot.md) | [測定](2026-11-12-dev-image-snapshot.csv) / [全APT差分](2026-11-12-dev-image-snapshot-packages.csv) | 2026-11-12 | amd64のローカル検証 | apt・zlib修正版の最初のsnapshotを署名付きindexで選択。QEMU builderと最終stageの差分・変更履歴・旧新gateを記録。arm64実行と実機は未検証。 |
| [2026-11-12-legal-info-hashes](2026-11-12-legal-info-hashes.md) | [測定](2026-11-12-legal-info-hashes.csv) | 2026-11-12 | legal-info・hash確認済み | Linuxのlicense 3 fileとlocal M5のCOPYINGを固定上流原文と照合。変更前後で対象4行が消失し、4 fileの改変を拒否。Buildroot source未保存とBootlin license file未定義は残す。 |
| [2026-11-12-openssl-3.5-lts](2026-11-12-openssl-3.5-lts.md) | [測定](2026-11-12-openssl-3.5-lts.csv) / [file一覧](2026-11-12-openssl-3.5-lts-files.csv) | 2026-11-12 | QEMU・署名確認済み | Buildroot固定版のままhost/targetを外部overrideで3.5.9へ変更。両側のfull build・A/B起動に成功。既存legal-info警告と実機未確認を残す。 |
| [2026-11-12-phase2-option-variants](2026-11-12-phase2-option-variants.md) | なし | 2026-11-11 - 2026-11-12 | 完了（QEMU） | 125 variantのT3/T4/T5/T6結果、失敗と再測定を記録。QEMUのみで、実SDのdurabilityや採否は未確認。 |
| [2026-11-09-phase0-filesystem-compare](2026-11-09-phase0-filesystem-compare.md) | なし | 2026-11-08 - 2026-11-09 | 完了（QEMU、phase-0） | T1-final、mode=all、計測器の制御結果と失敗runを統合。B2の16 failuresをsetup phaseに分類。L3非同期mark待ちとF1 manifest境界を修正。L3 mode=allは未完了、残る14構成のmode=allと実SD電源断は未実施。 |
| [2026-11-09-phase1-pilot](2026-11-09-phase1-pilot.md) | なし | 2026-11-09 | 完了（QEMU、6構成） | T2/T3/T4-sync/T5/T6/T7の36最終plan entriesが成功。T6 mapping、4 GiB T7 setup時間、mapper統計、retryを記録。全20構成の620-row matrixと実SD電源断は未実施。 |
| [2026-11-10-phase1-matrix-r2](2026-11-10-phase1-matrix-r2.md) | なし | 2026-11-09 - 2026-11-10 | 完了（QEMU、20構成、I2 T1 retryは運用停止） | 620 plan rowsを実行し、最終attemptは619成功、I2 T1だけ既知timeoutのためretryを運用停止。全T1-T7 metrics、失敗attempt、部分summaryの注意点を記録。実SD電源断は未実施。 |
| [2026-11-10-phase1-t2-manifest-recheck](2026-11-10-phase1-t2-manifest-recheck.md) | なし | 2026-11-10 | 完了（QEMU、T2追試） | E5/F5/F3でrecoveredは各20/20。manifest_okはE5/F3が20/20、F5が19/20。保存済みF5 imageではmarker 700以降の50 recordsを受け入れ、4 byteのtorn tailを拒否した。E1 T1負対照はlossを検出。実SD電源断は未実施。 |
| [2026-11-11-phase1-t2-rerun](2026-11-11-phase1-t2-rerun.md) | なし | 2026-11-10 - 2026-11-11 | 完了（QEMU、T2 20構成、I2/E1 T1） | 全20構成でrecoveredとmanifest_okが20/20。W2 inflight 27件、W3 tail 4件、hash mismatch・missing・fscrypt policy failureは0。I2 T1 attempt 2完了。実SD電源断は未実施。 |
| [2026-11-15-fs-compare-matrix](2026-11-15-fs-compare-matrix.md) | [集計42群](2026-11-15-fs-compare-matrix.csv) | 2026-11-14 - 2026-11-15 | 成功174=120 T5+54 T4、別に中断4 | T5はbase 6+variant 18を各5回。17/18で差を反復しP136は非再現。f2fs F3/P044の遅いwriteとI2/L3の追い書きを観測。B2のidle 0を新設計の§10適合とはしない。 |
| [2026-11-03-ci-cache-and-parallel](2026-11-03-ci-cache-and-parallel.md) | なし | 2026-11-03 | host回帰・実Dockerの機能検証 | 文書のみのskip、製品・未知・失敗時のbuild、完全一致archive、2並列runnerと負対照を確認。GitHub cacheの長期hit率・総費用・短縮率は未測定。 |
| [2026-11-03-maintenance-followup](2026-11-03-maintenance-followup.md) | なし | 2026-11-03 | host・静的回帰 | 3 suite各5回、署名300 command、分類5改変の検出。OpenSSLの版と保守期限・取得失敗・週次通知を分離。製品の依存版は変更していない。 |
| [2026-11-03-sbom-cve-monitor](2026-11-03-sbom-cve-monitor.md) | なし | 2026-11-03 | OCI pipeline・CPython・PR gate比較 | depth-1 NVD clone 5回の中央値156.062秒でcacheなし。SBOM 67件、VEX 16,047件。CPython 3.11とのsemantic tuple 16,421件が一致。PR gateのbase/headは各149 findingsで差分0、終了コード0。 |
| [2026-11-03-init-comparison-plan](2026-11-03-init-comparison-plan.md) | なし | 2026-11-03 | 計画のみ | 現行・systemd・s6系・OpenRC等の固定条件、資源・権限・A/B復旧、QEMU/実機の分離。[計測器と故障試験](2026-11-03-init-comparison-protocol.md)も未実装の仕様。 |
| [2026-11-03-init-roadmap-validation](2026-11-03-init-roadmap-validation.md) | なし | 2026-11-03 | 静的照合 | 残件・原Q/R・S1–S17・要求・出典のID/参照/依存を確認。OSのbuild・実測・実機の合格ではない。 |
| [2026-11-03-alternative-coverage](2026-11-03-alternative-coverage.md) | なし | 2026-11-03 | 母集団の静的照合 | 67 Buildroot、231 APT/129 source、11 Action、859 npm名/1574組、11 Go moduleを比較先へ対応。5回一致と4負対照。全license・実bundle・代替実行の確認とは別。 |
| [2026-11-03-ci-scope](2026-11-03-ci-scope.md) | なし | 2026-11-03 | 固定判定の照合・履歴観察 | path・markerの117行成功と改変対照。CI成功5 runの152 stepを観察し、echoによる初回誤分類53行も保存。新しい性能実験・製品buildではない。 |
| [2026-11-03-userspace-security-layout](2026-11-03-userspace-security-layout.md) | なし | 2026-11-03 | 本文の静的照合済み | 3原文の26範囲、原文要約4行、基準CSV72件を5回照合。10対照を検出。初回の対照対象の誤りとリンクの失敗は別CSVへ保存。製品build・実機試験とは別。 |
| [2026-11-02-storage-document-layout](2026-11-02-storage-document-layout.md) | なし | 2026-11-02 | 本文の静的照合済み | 4原文の全範囲を11ブロックで保存し、5回照合と4改変対照を確認。基準のCSV59件は未変更。初回の改変対象の誤りも保持。 |
| [2026-11-02-verification-document-layout](2026-11-02-verification-document-layout.md) | なし | 2026-11-02 | 静的照合 | 79件の問いを31主題へ統合。9本文と原記録154行を5回照合し、4改変を拒否。過去の測定CSV51ファイルは未変更。 |
| [2026-11-02-boot-document-layout](2026-11-02-boot-document-layout.md) | なし | 2026-11-02 | 静的照合 | 8本文を5回照合し、4種の改変を拒否。旧案内を削除して主題別に配置。製品設定・過去の測定CSVは未変更。 |
| [2026-11-02-alternatives-followup-audit](2026-11-02-alternatives-followup-audit.md) | なし | 2026-11-02 | 追加調査・静的照合 | 出典225件中210取得と88 Git blobを5回照合し、3負対照を毎回拒否。代替build・実機は未試験。 |
| [2026-11-02-release-client-audit](2026-11-02-release-client-audit.md) | なし | 2026-11-02 | 静的調査・提出前検査 | TUF実装4候補と公開側tool、Release配信・時刻・A/B復旧を比較。client実行・製品組込み・実機更新は未実施。 |
| [2026-11-02-install-update-audit](2026-11-02-install-update-audit.md) | なし | 2026-11-02 | 静的照合・回帰検査 | CI成果物・自動拡張・自動commit・DTの状態を操作手順と照合。実カードと実機は未確認。 |
| [2026-11-02-release-key-audit](2026-11-02-release-key-audit.md) | なし | 2026-11-02 | host手順確認・本番運用は未実装 | 試験鍵5回・60コマンドで導出、署名、改変と別鍵の拒否を確認。Secret登録・設定変更・実機移行は未実施。 |
| [2026-11-02-security-design-audit](2026-11-02-security-design-audit.md) | なし | 2026-11-02 | 静的監査・設計保存 | OpenBSD原則を処理・IPC・通信・拒否試験へ対応づけ、設定と強制の混同等を訂正。新policyと実機は未試験。 |
| [2026-11-02-dev-image-scan](2026-11-02-dev-image-scan.md) | なし | 2026-11-02 | 報告器の確認完了・OCIは未更新 | 2184件中の公開ゲート対象1件が従来の本文では省略されていた。改修後のA/A 5回で全件JSONと本文のhashが一致。 |
| [2026-11-02-sbom-generation](2026-11-02-sbom-generation.md) | なし | 2026-11-02 | 静的試験完了 | 通常buildのLinux版・CPEを補正し、show-infoと構成要素・依存を照合。5回同じhash。VMと開発用OCIのhost-tar差による失敗も保存。 |
| [2026-11-02-hardware-artifact-audit](2026-11-02-hardware-artifact-audit.md) | なし | 2026-11-02 | 静的照合完了・実機未確認 | 固定CI生成物のDTBO、16 M5 modules、firmware、権限、最終configとA/Bログを照合。DTC 1.7.2で合成成功、1.6.1の失敗も記録。 |
| [2026-11-01-jobs-wallclock](2026-11-01-jobs-wallclock.md) | なし | 2026-11-01 | 完了 | `--jobs` の壁時計測定。jobs1=10421s、jobs2=1452s（ccache 温存で比較不可）。cold 推定は約 2 倍速。linux-custom 不在時に worker 全滅する欠陥を発見し preflight を追加。 |
| [2026-11-01-s17-dmlw-blkdebug](2026-11-01-s17-dmlw-blkdebug.md) | S17 | 2026-11-01 | 完了（QEMU のみ） | dm-log-writes は 5 回とも replay 後イメージとゲスト計測 SHA-256 が完全一致（書き込み列の完全再生を確認）。blkdebug は注入範囲どおりに発火したが、QEMU の SD モデルがホスト側エラーをゲストに伝播しないことを確定（ゲスト観測型のストレージ障害検証は実機依存）。 |
| [2026-11-02-buildroot-yocto-boottime](2026-11-02-buildroot-yocto-boottime.md) | なし | 2026-11-02 | 完了（QEMU のみ、各 5 回） | 同じ rootfs に載せた C3/C4 の差は事前の閾値を超えなかった。同等性や実機の差がないことは未証明。イメージ全体は内容が異なり、モードで差の向きが逆になる。 |
| [2026-11-02-buildroot-yocto-artifacts](2026-11-02-buildroot-yocto-artifacts.md) | なし | 2026-11-02 | 完了（ビルドと QEMU、各 1 回） | Buildroot の完成イメージを cold で 3,280.65 s でビルドし、QEMU の A/B 試験に合格。Yocto の最小イメージは 7,444 s。同じ defconfig と fragment でもカーネルの `.config` は 544 項目違い、`CONFIG_THERMAL` が Yocto では `n`。 |
| [2026-11-02-yocto-qemu-boot](2026-11-02-yocto-qemu-boot.md) | なし | 2026-11-02 | 完了（QEMU のみ） | Yocto の最小イメージが、getty を `ttyAMA1` に 1 行足した写しで、開発用 QEMU の `raspi3ap` と標準 QEMU の `raspi3b` のどちらでもログイン画面まで起動した（各 5 / 5）。標準 QEMU の `raspi3ap` は ASB が未実装で止まる。 |
| [2026-11-02-yocto-wrynose-probe](2026-11-02-yocto-wrynose-probe.md) | なし | 2026-11-02 | 完了（ビルドのみ） | kas-container と rootless Docker で、仮置きの Wrynose 6.0.4 の最小イメージと M5 BSP（.ko 16 個、dtbo 3 個）がビルドできた。MSD のカーネル 6.18.59 と fragment でも通った。起動は未確認。 |
| [2026-11-02-zizmor-wheel-cache](2026-11-02-zizmor-wheel-cache.md) | なし | 2026-11-02 | 完了（開発用OCI） | 同版の両CPU wheelを固定し、不要cache除去後のoffline監査とnative scanを確認。cache由来38 blockingは0件になり、延期したBrotliの1件で両CPUとも公開は阻止。 |
| [2026-11-03-dev-image-security-update](2026-11-03-dev-image-security-update.md) | R25 | 2026-11-03 | 完了（amd64/arm64 CI、attestation確認） | snapshotを`20261103T023120Z`へ更新。Brotliだけの初回は45 blockerが残ったが、Linux headersも含む2 package更新後はTrivy 0.76.1 gateが0件。merge後のmain CIで両archのgateとSBOM、multi-arch indexのprovenance、Buildroot buildを確認。 |
