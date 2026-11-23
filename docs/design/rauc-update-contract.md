# RAUC導入の契約とPR分割

[文書の案内](../README.md) / [調査の入口](../../RESEARCH.md) /
[全optionの採否](../research/component-options/rauc.md) /
[書き込みの台帳](write-policy.md)

## 範囲と状態

利用者が承認したRAUC導入計画を、後続PR②〜⑦の受入条件として固定する。
本PR①は文書だけであり、製品のpackage、kernel、boot処理、署名、更新形式は変更しない。
固定対象はBuildrootが収録するRAUC 1.15.2である。
既存の[framework比較](../research/alternatives/updates.md)、
[配信比較](../research/alternatives/update-delivery.md)、
[adaptive調査](../research/alternatives/update-delta.md)を根拠として再利用する。
ここにある計画を、build・QEMU・実機で合格した結果とは扱わない。

## slotとRO設定

| 組 | 親slot・bootname | 子slot | bundle外 |
|---|---|---|---|
| A | `rootfs.0`、`A`、`/dev/mmcblk0p5` | `boot.0`、`parent=rootfs.0`、`/dev/mmcblk0p2` | 共通p1 bootsel、p7 `/data` |
| B | `rootfs.1`、`B`、`/dev/mmcblk0p6` | `boot.1`、`parent=rootfs.1`、`/dev/mmcblk0p3` | 同上 |

四つのslotは`type=raw`とし、完成したFAT boot imageとSquashFS rootfs imageを書き込む。
manifestのimage typeはbootが`raw`、rootfsが`squashfs`。
二つのimageを同じbundleに含め、active group、mount中のslot、容量超過は拒否する。
p1・p7のslot宣言やimage sectionは作らない。p7へのstatus保存まで禁止する意味ではない。

`system.conf`はRO rootの`/usr/lib/rauc/system.conf`に置く計画とし、
wrapperから`--conf`で固定して読む。可変な`/etc` overlayによるpolicyの隠蔽を避ける。
設定は`bootloader=custom`、`bundle-formats=verity`、
`data-directory=/data/rauc`、`activate-installed=false`、
一時mount点は`mountprefix=/run/rauc`とする。
rootfsの`bootname`に対応してkernel cmdlineへ`rauc.slot=A`又は`rauc.slot=B`を渡す。
cmdline、firmwareのDT情報、実際にmountしたroot partitionを照合し、
不一致・欠落・曖昧な場合は永続書込みとactivateの前に拒否する。
`--override-boot-slot`を製品経路へ公開しない。

## install・試し起動・確定

1. 利用者の同意後、RO設定・slot照合・空き容量・対象版を検査する。
   bundleのCMS署名、chain、compatibleの検査が失敗した場合、p1・全slot・`/data`のwriteを0にする。
   download buffer、検査log、lockはRAMに置く。
2. RAUC標準の入力検証とwriterを使い、inactiveのbootとrootfsを更新する。
   `adaptive=block-hash-index`を両imageに指定する。
   verityが保護するのは取得したbundleであり、installed rootのdm-verity policyとは別である。
   installed-root dm-verityの設計・変更は本計画の範囲外とする。
3. 両imageのwriteと同期の完了後、書いた長さの全体を再読取りし、
   署名されたmanifestのsize・SHA-256と照合する。
   RAUCのinstall成功だけでactivateせず、一方だけの成功・read-back不一致では試し起動しない。
4. その後の明示的なactivateで`set-primary`を呼び、候補を`trying`として保存する。
   これを確定済みprimaryへの昇格としない。
   firmwareの一回限りのtryboot要求と、p1の確定書換えを分離する。
5. 新slotの`S99msd-health`成功後にだけ`rauc status mark-good`を実行し、
   backendの`set-state <A/B> good`を通じてp1の`autoboot.txt`を書き換え、確定する。
   health失敗、slot照合失敗、状態保存失敗を成功へ読み替えない。

### custom backendの責務

| 呼出し | 契約 |
|---|---|
| `get-primary` | 確定済みprimaryのbootnameを返す。p1・slot・`/data`へのwrite、修復、mkdir、log保存を行わない |
| `get-state <A/B>` | `good`又は`bad`を返す。判定不能は非0終了とし、読取りのついでに修復しない |
| `set-primary <A/B>` | `trying`だけを保存する。p1の確定primaryを変更せず、両imageのread-backを前提条件にする |
| `set-state <A/B> bad` | 認証済み更新中又は明示した失敗処理で候補の不良を保存する。旧primaryを無条件に書き換えない |
| `set-state <A/B> good` | health済みの試し起動に限り確定する。通常起動で毎回同じ状態を書き直さない |
| `get-current` | cmdline識別を使うため通常は不要。追加するなら同じ三者照合を守り、書込みは禁止する |

状態は`/data/rauc/bootstate`に置き、同じdirectory内の一時fileへ書く。
内容の`fsync`、`rename`、directoryの`fsync`を行い、失敗を伝える。
RAUC自身の`central.raucs`とbackendのbootstateは役割を分ける。
FAT上の`autoboot.txt`と`/data`の間に原子性は仮定しない。
どちらか片方の更新直後に電源が切れる条件を含め、次回起動で両方と実bootを照合する。
不一致時は確定済み旧slotを勝手に捨てず、状態不明を表示して通常更新を止める。
復旧にwriteが必要ならprogress付きの回復処理として行い、get操作に隠さない。
具体的な記録形式・遷移順と再実行の冪等性は③で試験可能な形に固定する。

mark-goodと必要な起動時reconcileは、利用者が始めた更新を完結するための計画である。
自動writeの理由・時機・量・表示を[台帳の計画行](write-policy.md#rauc導入で追加する計画)へ登録した。
これは実装済み、計測済み又は現行の未対応解消を意味しない。

## 配信・adaptive・Phase A

GitHub Releasesへbootとrootfsを含むfull `.raucb`を置き、
RAUC自身のstreamingで必要部分を取得する。
RAUCへ渡す前にcurlで全量downloadする構成を、streamingの合格と数えない。
署名CAとHTTPSのTLS CAを分け、redirect先へ認証情報を漏らさない。

Phase A PoCは⑤の最初に行い、**実RAUC 1.15.2**で次を確かめる。

| 条件 | 必須の観測と判定 |
|---|---|
| Release assetのredirect | 初期URLからassetまでの経路、TLS検証、Rangeと再要求、headerの伝播を記録 |
| HTTP 206 | 実際のRAUC要求と応答範囲・byte数を取得。以前のcurl観測で代用しない |
| signed URLの期限切れ | 転送途中で失効させ、再解決・再接続又は明示失敗を観測。壊れた候補をactivateしない |
| 429 | Retry-After、再試行の回数と上限、中断表示を記録。無限retryや黙った成功は禁止 |
| 切断・再接続 | 認証・入力verityを維持した再開又は明示失敗を観測。再起動後の再開と同じ保証にしない |
| Range拒否・200応答 | 既定は失敗。full-downloadへ自動変更しない |

full-download fallbackは、全量と一時領域の容量検査、保存先の書込み規則、
利用者の明示同意、異常時の非activateを満たす別経路としてだけ許す。
現時点でfallbackを実装済みとは扱わない。

### Phase Aの観測済み事項と残件

[2026-11-23のstreaming PoC](../experiments/2026-11-23-rauc-streaming-poc.md)では、
host上の実RAUC 1.15.2の`info`とlocalhostの模擬HTTP serverを使い、各条件を5回試した。
`install`は実行していないため、製品のinstall経路全体の合格とは扱わない。

| 条件 | 観測した事実 | Phase Aの状態 |
|---|---|---|
| Range拒否・200 | RAUCは非0で失敗し、full-downloadで成功するfallbackは行わなかった | 既定失敗の契約に適合。ただし拒否までの受信量は0ではない |
| redirect・206 | 302後に206を取得し、CMS検証済みで終了0 | 模擬serverで確認済み。実GitHub assetの観測とは分ける |
| 切断・再接続 | 一度の切断後に再接続し、同じ8-byte Rangeを再要求して検証成功。毎回切断では上限後に失敗 | 確認済み。残り4 bytesからのresumeや再起動後の再開は未確認 |
| 429・Retry-After | 指定3秒に対し次要求は約1.0秒後。一度だけなら回復、継続時は5回retry後に失敗 | OPEN。Retry-Afterを遵守していない |
| 期限切れsigned URL・403 | 同じobject URLを5回retryして失敗。元URLの再解決や新しい署名queryの取得は観測せず | OPEN。再解決による回復は未実装 |
| activation | 全試行でbackendのset-primary/set-state呼出し0、架空slot・状態fileのhash不変 | `info`試験で確認。実slotや実/dataへのwrite量の証明ではない |

429への対応は、wrapperによるbackoff、RAUCへのpatch、現挙動を制約として受容する案から選ぶ。
403への対応は、wrapperがURLを再解決して処理を再開する案と、RAUCへのpatchを比較する。
いずれも未決定であり、wrapperの停止・再実行やpatchの安全性を確認済みとはしない。

Phase Aには`install`、adaptiveのblock再利用、端末側index生成・再生成のwrite量、
実GitHub Release assetのredirect・206・期限切れ挙動の観測が残る。
bundle作成時のindex生成を、端末での再利用やwrite量の測定に読み替えない。

hash indexは4 KiB blockごとのSHA-256を持ち、RAUCの
`data-directory`配下、すなわち`/data/rauc`内へ置く。
index生成・再利用・破損時の再生成に伴うread/write量を別々に測る。
hash一致の候補blockも読取り検証し、古いindexだけを根拠に信用しない。
backgroundのindex再生成や起動ごとの再生成は行わず、同意された更新のprogress区間内に限る。
adaptiveは転送を減らす仕組みであり、SD writeも同率で減ると仮定しない。

## CMS・PKI・橋渡し

CMS/X.509を使い、offline root CA、issuing CA、短命release証明書のchainを採る。
まずECDSA P-256を評価し、host生成、chain・用途検査、target検証の相互運用を④で確かめる。
端末に置くのは公開CAだけであり、署名秘密鍵は置かない。
再現可能なbuild成果物と、鍵を持つ署名処理を別環境・別権限に分ける。

橋渡しreleaseは旧Ed25519方式で署名する。
旧方式でRAUC本体とkeyringを導入し、旧方式のhealth・確定を完了してから、
RAUCを唯一の更新writerへ切り替える。
旧writerと新writerを同時に走らせず、相互排他と復旧経路を④で試す。
移行完了後の⑦で公開`msd-update`、旧tar形式、旧公開鍵と旧署名経路を撤去する。
橋渡し前の端末まで更新不能にする削除を先に行わない。

### OPEN: 利用者の決定待ち

| 論点 | 選択肢と条件 | 状態 |
|---|---|---|
| PKI責任者 | 鍵保管、CA発行、release署名、失効、復旧の担当者と承認分離を決める | OPEN。人・組織を本PRで割り当てない |
| 信頼できない時計と期限 | 案1: 信頼できる時刻を得るまで更新を保留する。短命証明書とCRL運用が可能だがoffline更新を制限する | OPEN |
| 同上 | 案2: 期限検査を無効化し、署名済みの単調版と永続下限でrollbackを拒否する。盗難・失効済み鍵の悪用を時刻で制限できなくなる | 利用者への提案であり未承認。1.15.2の`install`には`--no-check-time`がなく、そのまま指定して実現できない |
| 同上 | 案3: `use-bundle-signing-time=true`で署名時刻を評価する。証明書期限の完全無効化とは違い、古い署名のreplay対策が別途必要 | OPEN。既定falseを変更しない |

`min-bundle-version`は設定されたSemVer下限との比較であり、
現在までの最大内部版を自動的に永続更新する機能ではない。
単調版の比較・保存・橋渡し時の初期値・失効後の回復を、承認なしに決定済みとしない。
期限無効化の可否が確定するまで、そのためのRAUC patchや独自検証器は追加しない。

## progress・中断・書込み

2秒以上かかり得る取得、認証、index生成、write、read-back、状態同期、確定・回復は、
開始前に対象を示し、bytes又は割合と経過時間を表示する。
RAUC標準の英語出力だけを§10適合とせず、製品wrapperでconsoleと対話画面を英日併記する。

| 段階 | 表示の例 | 中断条件 |
|---|---|---|
| 取得・認証 | `Verifying update / こうしんを けんしょうちゅう` | cancelを受け付け、非activateで終了する。streamingはwriteと重なるため段階名を正確に出す |
| slot書込み・read-back | `Writing inactive slot / たいきスロットに かきこみちゅう` | cancelは処理の停止確認後に完了表示する。部分更新slotは不良として扱う |
| 状態同期・mark-good | `Do not power off / でんげんを きらないでください` | 原子的でないp1と/dataの更新が完了するまで通常cancelを遅延し、電源断後はreconcileする |
| 失敗 | `Update failed / こうしん しっぱい` | 原因、使用可能な旧slot、次の操作を表示。失敗を完了成功へ変更しない |

LCDと日本語fontの可読性は実機未確認である。
service=false構成にはCLIの`--progress`がないため、
inline installの進捗出力をwrapperで扱う実現性と中断境界を⑤で確認する。
表示が取れない場合を無表示で許容せず、⑤の受入条件未達として止める。

## PR②〜⑦の範囲と受入条件

| PR | 範囲 | 受入条件 |
|---|---|---|
| ② Buildroot統合 | 固定RAUC、host-rauc、network・streaming・JSON、非常駐構成、必要kernel設定、RO設定と公開CAの配置準備 | Meson最終値・依存・uid・NBDのconfigを採否表と照合。vendorを編集せずbuild。license/SBOM、常駐なし、defaultのidle writeを確認。ENGINE強制はOpenSSL削減と別件 |
| ③ custom backendとhealth | slot三者照合、read-back gate、trying、mark-good、bootstate、reconcile、S99連携 | get-primary/get-stateのwrite 0、照合異常の拒否、各保存失敗、冪等な再実行、health失敗時非確定をhost試験。実firmware trybootは実機待ちと明示 |
| ④ PKI・橋渡し・署名 | CMS chain、P-256評価、build/sign分離、旧方式での橋渡し、排他 | 悪署名・誤CA・用途違い・期限条件・旧版・橋渡し中断を試験。OPENの利用者判断を得て文書を更新し、未決のまま本番署名へ進まない |
| ⑤ streaming・adaptive・表示 | Phase Aを先行、full asset取得、index、英日progress/cancel | RAUC自身でHTTP異常を検証。Range拒否の既定失敗、無断fallbackなし、indexのbackground writeなし、cancel失敗を成功表示しない。LCDは実機待ち |
| ⑥ QEMU測定 | 下表の比較と故障注入、証拠保存 | baselineと候補の同条件・各5回・A/A、生値と失敗を実験記録へ保存。容量・RAM・時間・取得量・write量を比較し、未測定を埋めず利用者へ報告 |
| ⑦ 旧方式撤去 | 橋渡し完了後に旧command・tar・鍵・CI経路・操作文書を撤去 | RAUCだけがwriterであることと旧入力拒否を検査。未移行端末の救済経路を確認してから削除。tryboot・実SD電断の実機証拠をQEMU結果で代用しない |

### QEMU測定の試験行列

| 条件 | 必須の測定・不変条件 |
|---|---|
| full対adaptive | 同じboot/rootfs、配信経路、圧縮、機種・版で各5回。変更なしA/Aを含める。順序・cache条件を記録 |
| index cold / warm / corrupt | create・reuse・破損拒否又は再生成を分け、index自身とslot/statusのwrite byte数を測る |
| 悪署名・誤CA | p1、p2/p3、p5/p6、p7 `/data`のwriteが全て0。RAUC service起動など事前writeと混ぜず、認証開始前からblock traceを採る |
| 境界ごとの中断 | 認証前後、index保存、各image write中・同期後、両read-back間、trying保存、tryboot要求、health前後、p1と/dataそれぞれの確定直前直後を注入点にする |
| HTTP異常 | redirect、206、期限切れURL、429、切断・再接続、Range拒否・200をRAUC自身で再現。取得byte・再試行・非activateを記録 |
| 状態異常・領域不足 | bootstate/status/index破損、p7満杯、fsync/rename失敗、slot容量不足、cmdline/DT/root不一致。曖昧な成功を返さない |
| 費用とidle | binary・image・依存容量、peak RAM、起動時間、経過時間、読取り・取得・block writeを分ける。background writerの有無も観測 |

QEMUのblock traceとprocess停止による故障注入は、実SDのFTL・flush・物理電断ではない。
GPU firmwareのtryboot、LCD、実SDでの電源断・復旧は実機専用の受入試験とする。
実験は[experiment-record手順](../../.agents/skills/experiment-record/SKILL.md)に従い、
commit・設定・入力hash・binary・反復・失敗試行・証拠取得方法を保存する。
