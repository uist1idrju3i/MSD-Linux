# OpenSSLの4機能を削るcold full build比較

- 状態: cold full build・回帰・容量比較は完了。4項目組の製品採用は見送り。
- 日付: 2026-11-23
- 関連: [全38 symbolと利用者の調査](../research/component-options/openssl-features.md)

## 目的と採否の基準

C1、algorithm、provider、性能設定を変えず、CMP、QUIC、SSL trace、compressionだけを落とす。
両者のfull buildと全回帰が成功し、SquashFSが少なくとも1 block（4,096 bytes）小さくなり、
要求された機能を失わなければ採用候補にする。差が1 block未満なら製品へ反映しない。
容量だけで自動採用せず、診断機能の喪失と将来consumerの制約を結論で評価する。
性能・起動時間の改善はこの比較の合格条件にせず、容量削減を起動短縮と表現しない。

## 条件

| 項目 | 固定する値 |
|---|---|
| 実行commit | `dd769c55044cbb3b9cf66032ba510890d5f10584`。runner本体はhashでも固定する |
| Buildroot commit | `bbbdab36565d4941b6b0449a0eedb5aac8a10c2e` |
| 比較元 | このcommitから新しく構築するbaseline。既存warm buildを使わない |
| `O=` | 両者とも`output-openssl-features-r1/cold-pair-01/work`。baseline完了後にtree全体を退避し、同じpathにcandidateを新規作成 |
| cache・並列数 | 両方ともcold tree、ccache無効、6 jobs。download cacheだけ共有 |
| 共通の測定条件 | `BR2_REPRODUCIBLE=y`、UTC、C locale。製品のREPRODUCIBLE/ccache設定の採用変更ではない |
| 変えるもの | candidateの`BR2_PACKAGE_LIBOPENSSL_ENABLE_{CMP,QUIC,SSL_TRACE,COMP}=n`だけ |
| 反復 | 各1回のfull build、前後A/Bの4 boot。構築・機能の可否を調べ、速度・統計的同等性には転用しない |
| C1 | MinProtocol TLSv1.2、SECLEVEL=2。CA/CSR節、DEFAULT groups、ML-KEM、既存providerを維持 |
| 失敗 | UUID、計画、終了状態、未実施行を残す。再試行は別の出力先とIDを使う |

環境はDebian 13.7の固定開発container、Linux 7.0.0-44-generic、x86_64、CPU 6個。
container image IDは`sha256:1aea11386e31cc82eff0807de3e372a0b4443c881f3bc3765a56810b32e2ca65`。
compiler実体はBootlin 2025.08-1のGCC 14.3.0、binutils 2.43.1、kernelは6.18.64-v8。
QEMUは11.1.3。起動logの行は両者とも次の値だった。

```text
run-qemu: sha256 8b5c759a21dd5d841d96b37be4e60e3b324869dff22250b581c856e36ac15b73  /usr/local/bin/qemu-system-aarch64
```

OpenSSLは3.5.9 LTS。Buildroot、kernel、compiler、container、実際に使用するQEMUとhost toolの
版・hash、正規化config、実Configure引数は証拠へ保存する。
kernel/moduleと開発用更新署名鍵はcold buildごとに生成され得る。
これらに起因する非OpenSSLの内容差と、OpenSSLの削減を分けて集計する。
生成した秘密鍵は証拠archiveへ収録しない。

## 手順

```sh
docker/msd-dev python3 board/cardputerzero/tools/bench/openssl-features-build.py \
  --out output-openssl-features-r1/cold-pair-01
ln -s baseline output-openssl-features-r1/cold-pair-01/work
docker/msd-dev python3 board/cardputerzero/tools/bench/openssl-features/probe.py \
  --pair output-openssl-features-r1/cold-pair-01 \
  --out output-openssl-features-r1/probe-01
docker/msd-dev python3 board/cardputerzero/tools/bench/openssl-features/analyze.py \
  --pair output-openssl-features-r1/cold-pair-01 \
  --out output-openssl-features-r1/analysis-01
```

build treeの退避後、絶対pathを持つSDK toolを使うときだけ、元の`work`へbaselineを指すlinkを置く。
candidateの構築前や途中には置かず、buildを再利用する用途にも使わない。
probeは製品imageの使い捨てcopyを起動し、script・鍵・volumeを`/run`に置く。
通常の製品imageへ試験用scriptをinstallしない。

## 回帰と計測器

release-signingのC1・Ed25519試験、実msd-updateの正常受理・不正署名拒否とslot不変、
target OpenSSLのEd25519、CMS署名・検証・改変拒否、X.509の信頼・不信頼CA、
TLS 1.2/1.3とhostname不一致拒否を実施する。
Argon2idのLUKS2 format/open/closeをRAMのloop fileで動かし、metadataのKDFも読む。
QEMUのA/B起動、module名・サイズ・依存・状態を前後で比較する。
負の対照がtimeoutした場合は成功にしない。空・欠損・重複・失敗markerもhost試験で拒否する。
hostのopenssl-c1 endpoint probeはtargetのlocalhost試験と区別して記録する。
providerは暗黙のdefaultだけを読む試験と、default/legacyを明示loadする試験を分ける。
9種類のalgorithm一覧を前後で照合し、PQC、KDF、cipher、署名等が変わっていないことも確かめる。

容量runnerの`rootfs_regular_bytes`はBuildrootの`target/`にある通常fileの合計で、
配送されない1336-byteの`THIS_IS_NOT_YOUR_ROOT_FILESYSTEM`も含む。
生CSVの値は保存し、公開CSVの注記で範囲を示す。実imageを展開した
`rootfs_image_regular_bytes`を別に求め、結論には後者を使う。
圧縮はimageのpadded sizeとsuperblockのbytes usedを分ける。
さらにbaselineの展開treeを同じmtime・root所有者・hardlink無視の条件で2回再packし、
A/A hashを照合する。そのtreeの4 ELFだけをcandidateへ交換した値も別に測る。
この補助比較は署名鍵等の差を除くためで、full build値を置き換えない。

## 結果・採否

### 容量

| 対象 | baseline | candidate | candidate - baseline |
|---|---:|---:|---:|
| 実imageの通常file合計 | 45,605,558 bytes | 45,006,834 bytes | -598,724 bytes |
| SquashFS（padding込み） | 24,018,944 bytes | 23,805,952 bytes | -212,992 bytes（208 KiB） |
| SquashFS bytes used | 24,016,246 bytes | 23,804,436 bytes | -211,810 bytes |
| OpenSSL 4 ELF合計 | 7,214,240 bytes | 6,615,960 bytes | -598,280 bytes |
| libcrypto.so.3 | 5,200,792 bytes | 5,020,472 bytes | -180,320 bytes |
| libssl.so.3 | 929,336 bytes | 622,136 bytes | -307,200 bytes |
| openssl CLI | 959,488 bytes | 848,728 bytes | -110,760 bytes |
| legacy.so | 124,624 bytes | 124,624 bytes | 0 bytes |

4 ELFだけを交換した補助比較も、SquashFSは24,018,944から23,805,952 bytesになった。
A/Aの2回はともに24,018,944 bytesで、SHA-256は
`90b74ee4631a91f7c3b7a333b76727f979e3864af42d67a7ac1391e81e5bac53`で一致した。
これは補助再pack同士の一致であり、full build imageとのhash一致ではない。

full build間で内容が変わった通常fileは1,051個。内訳はOpenSSLの3 ELF、
kernel module 1,047個、開発用更新公開鍵1個だった。file集合は一致し、C1設定のhashも一致した。
非OpenSSLの合計差は-444 bytesで、module署名等を含むcold buildの差がある。
4 ELF交換の補助比較と切り分け、全差をOpenSSLへ帰属させない。

正規化configには4機能のほか、自動生成の`BR2_EXTERNAL_MSD_VERSION`に
clean/dirtyの差があった。baseline設定時の`v0.0.0-121-gdd769c5`に対し、
candidate設定時は同じcommitへ`-dirty`が付いた。
途中の文書・計測器編集によるもので、製品sourceの変更ではない。
固定Buildrootではこの変数を`support/scripts/br2-external`が出力するだけで、
recipe・rootfs・board側に参照はなかった。両imageの`usr/lib/os-release`も同じhashだった。
機能option以外も完全に同じconfigだった、とは主張しない。

### 回帰

- cold baseline/candidateのfull buildは各終了0。
- QEMUは前後A/Bの計4 bootがready・loginへ到達。全てQMP quit・reap終了0。
- A-slotでは各21 caseが終了0。Ed25519、実msd-updateの正常受理と不正署名拒否・slot不変、
  Argon2idのLUKS2 format・metadata確認・loop open/close、CMS・X.509の正負の対照を含む。
- TLS 1.2/1.3は両者とも`Verification: OK`。両protocolのhostname不一致を拒否した。
- 各19 moduleの名前・サイズ・依存・状態が、機能試験前の4 bootで一致。
  参照数とload addressは比較から除く。
- 暗黙のdefaultとdefault/legacyの明示loadを確認。9種類の暗号algorithm一覧は前後でhash一致。
- host C1 endpoint probeは16/16、release-signingは39試験が成功。
  host試験とtarget試験を混同しない。

### 採用しない理由

容量の数値基準は満たしたが、4項目組は採用しない。削減はSquashFS全体の約0.89%だった。
特に`no-comp`の「利用者なし」という根拠が足りない。
curlの`SSL_OP_NO_COMPRESSION`はTLS record圧縮を禁じる設定で、TLS 1.3証明書圧縮とは別である。

実targetのTLS 1.3 ClientHelloを読むと、baselineには拡張27（compress_certificate）があり、
bodyは`02 00 01`（zlib）だった。candidateでは同拡張が消えた。
固定sourceの既定値・拡張構築処理と合わせ、明示的なAPI呼出しがなくても圧縮を広告することを確かめた。
暗号algorithmの9一覧が同じでも、この能力が同じとは限らない。
これは広告の有無の観測であり、圧縮certificateを実際に転送した、という結果ではない。

RAUC/curlはまだ未導入で、契約のTLS・CMS・X.509は今回の部品試験で壊れていない。
ただし、将来のHTTPSで証明書圧縮が通信量・遅延へ与える影響は未測定で、
208 KiBの容量削減だけを理由に不要とは決めない。SSL traceの診断能力も失う。
性能設定を残す方針と、根拠が弱い機能を削らない条件を優先し、製品defconfig・recipeは変更しない。
CMP・QUIC・SSL traceだけを採用する判断にも、この4項目組の値を流用しない。
3項目だけなら別のcold full buildと回帰が必要で、今回は未実施である。

### 参考artifact

CI artifact `14813627892`は参考値で、正式なbaselineに混ぜない。
同artifactはrootfs通常file合計45,600,308 bytes、SquashFS 24,018,944 bytes、
OpenSSLの4 ELF合計7,214,240 bytesだった。

## 証拠と公開CSV

[CSV](2026-11-23-openssl-features.csv)は89行。build 6行、QEMU 50行、image解析17行、
host C1 16行を含む。全行validで、正式測定の失敗・欠損は0行だった。
生CSVのrun ID・値・有効性は変えず、staging-byteの2行に範囲の注記を加えた。
公開値は`export.py`で全列、ID、計画行数を照合して生成した。
公開する2つのCSVは行終端だけLFへ統一した。証拠archive内の生CSVは変更していない。

初回の出力directoryや測定imageは不要である。公開archiveの測定記録と当時のrunnerを、
未使用の出力先へまとめて展開する。再実行時は出力先名を変え、以下の全pathへ反映する。

```sh
mkdir output-openssl-features-replay-01
tar -xzf docs/experiments/2026-11-23-openssl-features.tar.gz \
  -C output-openssl-features-replay-01
docker/msd-dev python3 output-openssl-features-replay-01/runners/export.py \
  --pair output-openssl-features-replay-01/cold-pair-01 \
  --probe output-openssl-features-replay-01/probe-01 \
  --host output-openssl-features-replay-01/c1-host-probe-01 \
  --analysis output-openssl-features-replay-01/analysis-01 \
  --out output-openssl-features-replay-01/reexport.csv
python3 -c 'from pathlib import Path; p = Path("output-openssl-features-replay-01/reexport.csv"); p.write_bytes(p.read_bytes().replace(b"\r\n", b"\n"))'
cmp docs/experiments/2026-11-23-openssl-features.csv output-openssl-features-replay-01/reexport.csv
sha256sum docs/experiments/2026-11-23-openssl-features.csv output-openssl-features-replay-01/reexport.csv
```

この再集計にはarchiveの当時のexporterを使う。保守版は実際に起動したkernelのhashも要求するため、
そのfieldがない過去のrecordを受理しない。欠けたfieldを生のmetadataへ後付けしない。

full buildの実行IDは`openssl-features-f40c3733458d44df99deb13b180973ab`、
QEMUは`openssl-probe-f389737e241940f2b6d3b05e924bd281`。
実行したrunnerのSHA-256は次のとおり。実行中のscriptは変更していない。

| script | SHA-256 |
|---|---|
| openssl-features-build.py | `8c41be139cba6dcf3b82d78941c8922aa1ef7d6e22076739c76d29587c4d0320` |
| probe.py | `780e2acbebf86a5685a144078f44ca3c7ff9bb08657542c05851f52f24745cd4` |
| guest.sh | `cf5f3af98a586857c26f34a3a6ba075c8b35129e05b8955d8e723f65fc66a904` |
| analyze.py | `e8ba6f496f04648dfe59ca8e58c6ea2a005dc65b9e29902b8e536a8c595b5715` |

再試行は全て別の出力先を使う。上表は初回の実行版で、現在の保守版とはhashが異なる。
初回コードの照合にはarchiveの`runners/`を使い、新規の追試には下記の保守修正を含むrunnerを使う。
測定commitには新規runnerが未収録なので、初回コードを復元するときだけarchiveから戻す。
`openssl-features-build.py`は`board/cardputerzero/tools/bench/`直下へ、
残りは同directoryの`openssl-features/`へ置く。
build treeとimageは`output-openssl-features-r1/`に残し、commitしない。
[証拠archive](2026-11-23-openssl-features.tar.gz)は443,323 bytesで、SHA-256は
`89eecdcf5be03ab856aedac7b08dc5e00b950e9e022adc321d05a12abc243e9e`。
全92 fileを保存元のhashと照合した。
archiveには計画、CSV、metadata、正規化config、sourceと入力のhash、serial・guest log、
module/algorithm一覧、consumer監査、計測器の試験logを収録する。
秘密鍵・volume・fixtureのbundle本体は収録しない。
full build logは計約16 MiBのため収録せず、末尾160行ずつと完全版のbyte数・SHA-256を
`manifest.json`へ残した。完全版は上のfull build手順で再生成する。

準備中は内部symbolの未出力、計測器fixtureのAPI・型の誤り、ShellCheck SC2251を修正した。
これらは正式なimage測定の失敗ではなく、準備logとして残す。
補助集計ではTLS log名の仮定違いとcontainerへの標準入力未転送で一度止まり、
実際のlog名・`python3 -c`で読み直した。生の測定結果は書き換えていない。
展開時の所有者変更warningは非root実行によるもので、内容の読取り後に`-all-root`で再packした。

## 計測器の保守追試

PR #299のReviewを受け、初回の生CSV・証拠archive・容量の結論は変えず、計測器を修正した。
build・probe・exportの変更であり、製品設定やvendorの変更ではない。
mainへの取り込みcommit `0ca3cef99dbdf92288245ed1b9fac0fa2eeffaf1`のtreeはPRの`e84d5fb`と一致した。
以下の7指摘の修正は含まれていなかったため、最新のmainから別branchへ移植した。表は移植後のcommitを示す。

| 指摘 | 修正と試験 | commit |
|---|---|---|
| 1 出力先の親がない | 親directoryも作る。計画・結果の保存と既存出力先の拒否を試験 | `711a639b` |
| 2 環境から直接起動を継承 | `QEMU_COPY_IMAGE=1`を強制し、driveの上書き環境変数も除く。書き込むfake QEMUで元のSD image・DTBが不変と確認 | `e30c20dd` |
| 3 exec後の複製が残る | probe所有の一時領域を`TMPDIR`へ渡す。正常・早期終了・spawn失敗で回収を確認 | `f7d8b4b0` |
| 4 makeの失敗終了値が欠ける | 失敗したcommandの終了値をinvalid行へ保存。baseline・candidate・設定段階の終了7を試験 | `d682bdab` |
| 5 深い出力先でQMP pathが長い | 3と共通の短い一時領域にsocketを置く。深い出力先と継承`TMPDIR`でも108 bytes未満 | `f7d8b4b0` |
| 6 別buildの測定が混ざる | buildのkernel・SD・rootfs・configのhashをprobeと、rootfsのhashを容量解析と照合。不一致・欠損・不正hash・variantの取違えはCSV作成前に拒否 | `2ee9406f` |
| 7 signal後にQEMUが残る | TERM・INT・HUPをcleanupへつなぐ。別sessionの子processへ必要ならTERM/KILLを送り、reapと一時領域の回収後にhandlerを戻す | `3495ca76` |

3と5は一時領域の所有を共通原因として同じcommitにまとめた。
signalの最初の試験では、`InterruptedError`が`selectors.select()`内部で吸収され、3 signalともtimeoutした。
handlerの例外を`RuntimeError`へ変え、実processを使う3 signalの試験で停止・reap・複製回収を確認した。
release-signingは追加6試験を含む45試験が成功した。初回89行もhash照合後に再exportし、全列の一致を確認した。
この照合は記録されたhash同士を比べるもので、metadataの真正性を保証するものではない。
hashの欠損でexportを拒否しても、元の失敗・未実施行を含む生CSVは残す。

保守版の実QEMU追試は移植前のlocal commit `5c2ca4beb20c6e8b851d001b9153f52f6d9aef22`で実行した。
そのtreeは移植後の`2ee9406f794d1bc4e569030c38e78771c2898289`と一致する。
archive内の実行commitや生logは移植先のSHAへ書き換えず、当時の記録を保つ。
full buildは再実施せず、初回cold pairのimageを再利用した。
`QEMU_COPY_IMAGE=0`を明示しても複製だけを起動する負の対照を兼ね、次のコマンドで新規の50行を記録した。

```sh
docker/msd-dev env QEMU_COPY_IMAGE=0 python3 board/cardputerzero/tools/bench/openssl-features/probe.py \
  --pair output-openssl-features-r1/cold-pair-01 \
  --out output-openssl-features-review-01/probe-01
```

実行IDは`openssl-probe-b6656f8e11dd459481b74e75f3c04026`。
前後A/Bの4 boot、A-slot各21 case、各19 moduleと9種類のalgorithm一覧が成功・一致した。
全4回がQMP quit・reap終了0で、fallback・errorはなかった。
実行後にも両者のSD・kernel・rootfs・configの8入力をhash計算し、初回buildとprobe開始時の記録との一致を確認した。
初回の公開89行にこの新規50行を混ぜず、追試の計画・結果・metadata・log・runnerを
[保守追試archive](2026-11-23-openssl-features-review.tar.gz)へ分けた。
26 file、146,561 bytes、SHA-256は
`5588898ecf3d3ed1609c950cd08df8b0324eb6f09cfc9c892c21d1327c276809`。
全fileを保存元と照合し、秘密鍵・TLS session keyを含まないことも検査した。

### PR #300の追加修正

- 子processの生成から`Popen`の戻り値とPIDの保存まで、TERM・INT・HUPをhandler内で保留する。
  参照の保存後に中断例外へ変え、通常の停止・reapへ進む。子へsignal maskを継承させない。
  実processを生成した直後、constructorが戻る前に3 signalを送る試験で回収を確認する。
- `KERNEL_IMAGE`を指定した場合はそのfile、空または未指定なら比較元の`images/Image`を一時領域へ複製する。
  そのcopyを`KERNEL_IMAGE`へ明示し、SHA-256・元path・起動pathを各bootの`process.json`へ保存する。
  比較元imageのhashとは別の記録である。exportでは前後A/Bの4記録をbuildの`Image`のhashと照合し、
  不一致・field欠損を拒否する。同じ内容の別pathは許可し、別内容のkernelでは回帰が成功しても集計を拒否する。
- probeの出力先は親directoryも作る。上の追試commandをfresh checkoutで使えるようにし、
  入力欠損時も計画と未実施50行を保存する。既存の出力先は上書きせず拒否する。

## 未確認

OpenSSH、curl、RAUCは現行製品に未導入。source上の要求とtarget OpenSSLの部品試験は、
RAUC全体のbundle install・streamingの受入試験や、製品OpenSSH接続の代わりではない。
QEMUは実機の暗号速度、LCD、実機keyboard、SDIO/BT、電源断の検証ではない。
