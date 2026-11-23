# RAUC 1.15.2 HTTP streamingのPhase A PoC

[実験索引](README.md) / [生の値](2026-11-23-rauc-streaming-poc.csv)

- 状態: hostのmetadata観測終了。Phase A全体は未完了
- 日付: 2026-11-23（日本時間。raw logはUTCの11月22日）
- 担当: Devin
- 基準: main `82c72840215a287c06bf62828d8159d1aab78f6e`
- 範囲: 実験runner・記録・索引だけ。製品設定・vendor・契約文書は変更しない

## 目的と事前の判定基準

実RAUC 1.15.2でHTTP streamingの正常系と異常系を調べる。
curlだけの成功をRAUCの成功と数えない。
containerにはnbd・loop deviceがなく、有効capabilityも0だったため、
host-raucの`info`でmetadata・CMS取得までを検査する。
install、全image転送、書込み、adaptiveのblock再利用の実証とは区別する。

実行前に次の基準を記録した。
正常206と302後206は、信頼した試験CAによる検証を伴う終了0を期待する。
Rangeを無視した200は非0で拒否し、自動全量fallbackしないことを合格条件とする。
期限切れ403、429、切断は、要求・応答・body byte数・再試行数・終了状態を記録する。
成功するなら署名検証済み、失敗するなら明示的な非0であることを条件とする。
429のRetry-Afterを守るか、URLを再解決するかは観測事項とし、保証しない。
どのシナリオでもactivateを0回とする。

各HTTP条件を5回、正常系のA/Aを追加で実行する。
構築と公開Release確認は構築可否・観測対象の確認であり、性能の統計には使わない。
同じ範囲要求の繰返しをretryとして数え、redirectのhop数とは分ける。
bytesはserverのsocketが受け付けたHTTP bodyであり、packet captureによる受信量ではない。

## 固定条件

| 項目 | 実測・固定値 |
|---|---|
| Buildroot | `bbbdab36565d4941b6b0449a0eedb5aac8a10c2e` |
| 開発image ID | `sha256:1aea11386e31cc82eff0807de3e372a0b4443c881f3bc3765a56810b32e2ca65` |
| host | x86_64、kernel `7.0.0-44-generic`、containerのglibc 2.41 |
| 実行したcompiler | Debian GCC 14.2.0-19、GCC 14.2.0 |
| Python / OpenSSL / mksquashfs | 3.13.5 / 3.5.9 / 4.7.5 |
| QEMU | image内は11.1.3。本実験では未使用 |
| RAUC | `rauc 1.15.2`、network=1、streaming=1、service=false |
| RAUC binary SHA-256 | `325059745ec4b736e8fd160d8605508b11101b62d7cc6912d4d709ca90d94f5e` |
| RAUC source archive SHA-256 | `127a24cde208c65b837ae978c695a00730f1094ee8b6c7d48cf58ef846eae340` |
| 専用出力 | `O=output-rauc-poc`、新規のcold出力。download archiveは再利用 |
| ccache | 有効、既存のrepo内cacheを再利用。build前後の差分統計は未取得 |
| 開始時の空き | build runnerで199,793,852,416 bytes |
| CPU上限 | BuildrootとNinjaは4並列、bundle作成は2並列 |
| 稼働中smoke | PID 1871398・凍結clone・実行中scriptに触れていない |

buildのdefconfig生成は6.886秒、host-raucと依存の構築は886.222秒で、ともに終了0。
coldなのは専用出力であり、ccacheまでcoldとは扱わない。build時間の比較はしない。
生成された`config.h`の`ENABLE_NETWORK 1`と`ENABLE_STREAMING 1`を確認した。

## 構築・再実行

runnerは通常のimageに入れない。
recipe既定のhost-raucはnetwork/streamingがfalseなので、
専用make呼出しの変数で有効化した。vendorは編集していない。
上書きした変数は次のとおり。完全なargvは証拠の`build-01/complete.json`にある。

```text
BR2_JLEVEL=4
NINJA_OPTS=-j4
HOST_RAUC_CONF_OPTS=-Djson=enabled -Dnetwork=true -Dstreaming=true -Dservice=false -Dtests=false -Dpkcs11_engine=false -Dgpt=disabled
HOST_RAUC_DEPENDENCIES=host-json-glib host-pkgconf host-openssl host-libglib2 host-squashfs host-libcurl host-libnl
```

以下はrepo rootで実行する。出力が存在したら新しい名前を使い、上書きしない。

```sh
docker/msd-dev python3 board/cardputerzero/tools/bench/rauc-streaming-poc-build.py \
  --output output-rauc-poc --evidence output-rauc-poc-evidence/build-01
chmod 0777 output-rauc-poc-evidence
MSD_DEV_ROOTLESS=0 docker/msd-dev python3 board/cardputerzero/tools/bench/rauc-streaming-poc.py \
  --host output-rauc-poc/host --run output-rauc-poc-evidence/http-new --repetitions 5
docker/msd-dev python3 board/cardputerzero/tools/bench/rauc-github-observe.py \
  --tag v0.0.0 --output output-rauc-poc-evidence/github-new.json
```

条件選択のCLIはreview後に追加した。`--scenarios`に1個以上の条件名を渡す。
省略時はA/Aを含む全11条件、`--repetitions`省略時は各5回を実行する。
未知の条件名、値のない`--scenarios`、1未満の反復数は実行前に拒否する。
同じ条件を重複指定した場合は最初の指定だけを残す。
たとえばredirectとRange拒否だけを各5回調べる場合は次のとおり。

```sh
MSD_DEV_ROOTLESS=0 docker/msd-dev python3 board/cardputerzero/tools/bench/rauc-streaming-poc.py \
  --host output-rauc-poc/host --run output-rauc-poc-evidence/http-selected \
  --scenarios redirect ignore-range --repetitions 5
```

条件名の一覧は`--help`で確認でき、選択した条件を`metadata.json`にも記録する。
保存済みの`http-01`・`http-02`はCLI追加前の全条件runであり、
その結果・runner hash・生logは変更していない。このCLI追加後の測定は未実施。

今回のDockerはrootlessだった。既定のcontainer内uid 0からは、
RAUCのsandbox用setgroups・setuidに必要なcapabilityがない。
そこでHTTP試験はwrapperの`MSD_DEV_ROOTLESS=0`でuid/gid 1001を使った。
sourceの`nbd_server_child_prepare()`はuid/gidがともに非0なら権限降格を行わない。
capability追加、特権container、sandbox無効化patchは使っていない。
`chmod`は使い捨て証拠directoryをそのuidから作成可能にするためで、
鍵はrun配下のmode 0700の`private`に作る。

runnerが試験CAとRSA-2048のrelease証明書を生成する。製品PKIの採用判断ではない。
leafのEKUはcodeSigning、keyringは`check-purpose=codesign-rauc`。
試験用boot 262,144 bytes、rootfs 524,288 bytesをseed 20261123から生成し、
両imageに`adaptive=block-hash-index`を指定したverity bundleを作る。
作成logでは64・128 chunkのindex生成を観測した。端末でのindex生成・再利用ではない。
`system.conf`はcustom backend、4個のraw file slot、activate-installed=false。
実行するRAUC commandは全て`info`であり、`install`やmark-goodは呼ばない。

正式run `http-02`のbundleは808,843 bytes、
SHA-256は`36d734458716681c3603838e34fe8f155703ccc78c3bab3915ff8079124bfb4b`。
runnerのSHA-256は`dcb392d1b637ff1d9df1d81943152f317bb4c19c64659209edfd6b5ffb3ed2be`。
再生成時は新しい鍵・証明書を使うため、bundleのhashは変わる。
CA・CMSの検査は有効で、`--no-verify`や期限検査の無効化は使っていない。

## 計測器と異常注入

Python serverはcontainer内の127.0.0.1の一時portだけで待ち受ける。
HTTPのpath、Range、status、時刻、送出byte、client portをJSONへ記録する。
全応答はConnection: closeとし、keep-aliveの比較には使わない。

- 正常/A/A: 同じbundleで206を返す。独立に各5回。
- redirect: `/download`から偽の署名query付きobjectへ302。その後206。
- 200: Rangeを無視して全bodyを返そうとする。clientの切断までsocketのsendを数える。
- 期限切れ: 初回4 bytes取得後、またはserver開始0.25秒後から、次のRangeへ403。
  時間条件では初回bodyを0.35秒遅らせる。
  既に206を開始した応答の途中でHTTP statusを403へ変える試験ではない。
- 429: 初回の正常取得後、一度だけ、または以後常に429。Retry-Afterは3秒。
- 切断: footerの8-byte要求に4 bytesだけ返して切る。一度だけと毎回の2条件。
- 負対照: 別CAをkeyringに指定。HTTP取得は成功させ、CMSの検証失敗を確認する。

正式runで全55件の終了状態が期待と一致した。
正常とA/Aは各5件とも1935 bytes、retry=0、署名検証済みで終了0。
別CAは各5件とも`unable to get local issuer certificate`で終了1。
計測値が正常と異常で変わること、誤ったCAでは成功しないことを確認した。
4個のslot、autoboot.txt・bootstateの計6個の架空fileを前後でhash照合し、全件不変。
backendのset-primary/set-state呼出しは0回。実p1・実/dataのwrite計測ではない。

`body_bytes`はエラー応答も含むserverのsocket受入量で、TCP headerを含まない。
`rauc_body_bytes`はRAUCの`nbd dl_size`のsumである。
捨てた部分転送・再試行の全byteを含むとは限らず、総wire量とは扱わない。
200拒否時のRAUC集計は得られず、CSVは空欄。server値で置き換えていない。
`seconds`にはserver停止待ち約0.5秒が含まれ、通信性能の比較には使わない。

## 正式runの結果

全条件5回。byteはserverの値。範囲表示以外は5回とも同じ。
retryは初回要求を含まない。同じRangeを再要求した回数とRAUCのretry logを照合した。

| 条件 | 観測したHTTP列 | byte | retry | RAUC終了 | 事前基準との比較 |
|---|---|---:|---:|---:|---|
| 206 | 206を3回 | 1935 | 0 | 0 | 合格、CMS検証済み |
| 302後206 | 302を1回、206を3回 | 1935 | 0 | 0 | 合格、CMS検証済み |
| Range無視200 | 200を6回 | 131072〜225280 | 5 | 1 | 合格、全量fallbackせず拒否 |
| 4 bytes後403 | 302、206、403を6回 | 172 | 5 | 1 | 明示失敗の基準に合格。回復はしない |
| 0.25秒後403 | 302、206、403を6回 | 160 | 5 | 1 | 明示失敗の基準に合格。回復はしない |
| 一度だけ429 | 206、429、206を2回 | 1947 | 1 | 0 | 検証済みで回復。ただしRetry-After不遵守 |
| 継続429 | 206、429を6回 | 76 | 5 | 1 | 明示失敗の基準に合格。ただしRetry-After不遵守 |
| 一度だけ切断 | 206を4回、2回目は途中切断 | 1939 | 1 | 0 | 同じRangeを再接続・再取得しCMS検証成功 |
| 毎回切断 | 206を7回、2回目以後は途中切断 | 28 | 5 | 1 | 上限後に明示失敗 |
| 別CA | 206を3回 | 1935 | 0 | 1 | 負対照として合格 |
| 正常A/A | 206を3回 | 1935 | 0 | 0 | 正常とbyte・retry・終了が一致 |

200のbyte中央値は180224。無駄な受信をゼロにする保証ではない。
RAUCは`range requests not supported by server`で拒否し、成功へfallbackしなかった。
403時は最初の302を1回だけ通り、同じobject URLを再試行した。
元URLの再解決や、新しい署名queryの取得は観測していない。
429後の次要求までの時間は最小1.001202・中央値1.001344・最大1.001384秒。
3秒のRetry-Afterを待っていないので、その遵守を受入条件にする場合は不合格である。
切断後は同じ8-byte Rangeを再要求し、残り4 bytesからのresumeではなかった。

RAUC source `src/nbd.c`の`r_nbd_run_server()`はエラー時に最大5回、
`sleep(1)`後に`start_request()`を呼ぶ。HTTP logの5 retry・約1秒間隔と整合する。
単にsourceが存在するだけでなく、stderrの`retrying 1/5`〜`5/5`と
同一Rangeの要求列を根拠とした。

### 所要秒数（最小 / 中央値 / 最大）

| 条件 | 秒 |
|---|---|
| 206 | 0.519464 / 0.520967 / 0.527212 |
| 302後206 | 0.520353 / 0.521550 / 0.521638 |
| 200 | 5.525241 / 5.526323 / 5.527325 |
| bytes期限 | 5.527096 / 5.527614 / 5.528065 |
| 時間期限 | 5.877633 / 5.879323 / 5.893056 |
| 一度429 | 1.521496 / 1.521878 / 1.522161 |
| 継続429 | 5.525400 / 5.526904 / 5.528332 |
| 一度切断 | 1.519732 / 1.520742 / 1.522253 |
| 毎回切断 | 5.525656 / 5.527250 / 5.527454 |
| 別CA | 0.519892 / 0.520907 / 0.523746 |
| A/A | 0.516609 / 0.519064 / 0.520455 |

## 失敗・欠測と実GitHub観測

`http-01`はkeyringのpurpose指定漏れにより、正常対照が成立しなかった。
55件ともRAUC終了1で、うち正常期待の25件はHTTP取得後に
`Verify error: unsuitable certificate purpose`となった。
他はHTTP拒否等を含む。このrun全体を正式集計から外し、CSVとrawは残した。
実行終了後に`check-purpose=codesign-rauc`を加え、新規`http-02`で再試験した。
旧runnerも`http-01/runner-01.py`に保全した。失敗を成功へ変更していない。
RAUC 1.15.2の`signature.c`が登録するpurpose名は`codesign-rauc`である。

公開APIの`releases/tags/v0.0.0`はasset 0件を返した。
初回observerは空listのminで終了1。空list処理を加えた再確認は
`status=no-assets`をJSONへ保存して終了2とした。
公開release一覧の最初の100件を求めた応答もv0.0.0の1件だけで、assetはなかった。
releaseの公開時刻は2026-11-03T16:38:02Z。
実asset GET、redirect chain、206、署名URLの期限parameterは未観測である。
upload、release・tagの作成はしていない。

## 証拠の保管・取得

- branch: `data/fs-compare-experiments`（orphan。merge・削除しない）
- commit: `6cf6bcc6d9098c2a3114d7498c84a6917b89c319`
- 配置: `rauc/streaming-phase-a-2026-11-23.tar.zst`
- archive SHA-256: `3cd96166937b313499f1b2882c6f8f10a8f5967aecb3ae1320ef3bc93e898a42`
- 同名`.files.sha256`は487 memberのhash、`.selection.json`は除外と変更範囲。

build log 1 fileの署名URL queryだけ、公開用の写しで伏せた。
変更前後のhashをselectionへ記録し、原本は変更していない。
秘密鍵は収録しない。公開binary等20 fileは除外し、hashとsizeを残した。
bundle・slot image自体は含まない。公開CA・manifest・source・logで条件を追えるが、
同一bundleを公開証拠だけから復元できるという意味ではない。

repo rootから次を実行する。出力directoryが存在しないことを先に確認する。

```sh
git fetch origin data/fs-compare-experiments
data_sha=6cf6bcc6d9098c2a3114d7498c84a6917b89c319
git archive "$data_sha" rauc | tar -x
(cd rauc && sha256sum -c SHA256SUMS)
mkdir rauc-unpacked
tar --zstd -xf rauc/streaming-phase-a-2026-11-23.tar.zst -C rauc-unpacked
(cd rauc-unpacked && sha256sum -c ../rauc/streaming-phase-a-2026-11-23.files.sha256)
```

## 結論とPhase Aの残件

hostのmetadata経路では、redirect・206・Range拒否・期限切れ・429・切断を
実RAUCで観測した。全件activateなし。429のRetry-After待機と、
期限切れURLの自動再解決は確認できず、後者は今回の要求列にはなかった。

次はstreaming有効の専用targetをQEMUで構築し、全image取得からslot書込み、
中断、activation抑止を調べる。既存smokeと並行する本PoCでは、
target再構築・QEMU installまで範囲を広げず、未実施の残件とした。
metadata経路の403・切断を、slot image転送途中の検証とは扱わない。
adaptiveのcold/warm/index破損、4 KiB indexの端末側write量も未測定。
実GitHub assetが公開された後のread-only再観測も必要である。
実機のtryboot・SD電断・LCDは未確認で、契約文書のPhase A状態は変更していない。
