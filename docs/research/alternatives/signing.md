# 更新署名・鍵・配信の信頼境界

[代替比較](README.md) / [暗号・TLS](crypto.md) / [RESEARCH](../../../RESEARCH.md)

## 何を同じに保ち、何を見直すか

現行のhost署名とtarget検証を、別の暗号libraryや更新frameworkへ移せるか調べるための比較条件です。新しいmanifest、鍵運用、anti-rollbackの採用決定ではありません。公開版はSemVerにする要求があります。SemVerと内部の単調増加番号の分離は承認済みです（内部番号はtag commitのcommit時刻。対応表は[Release対応表](../../releases/README.md)）。

2026-11-02にMSD/Linuxの`9f07c3b884ae4c63c22dc196fd02b6ee43932f6e`、Buildrootの`8b238854d909c9cce32ef9671d968b03e323b55d`を基準に読みました。代替verifierのbuild・実行、Release配信・鍵rotation・実機rollbackの試験は本リポジトリでは試していません。

## 現行処理で確認したこと

| 部分 | ソースで確認した動作 | この動作だけでは保証しないこと |
|---|---|---|
| host鍵 | [post-build](../../../board/cardputerzero/post-build.sh)が指定鍵、または自動生成する開発用Ed25519鍵から公開鍵を作り、`/etc/msd-update/update-key.pem`へ入れる。`key-origin`も記録する | 指定されたrelease鍵の算法・保管・権限・環境の承認、開発鍵でのRelease公開禁止 |
| host署名 | [post-image](../../../board/cardputerzero/post-image.sh)がversion行と2 imageのSHA-256をmanifestに書き、host OpenSSLの`pkeyutl -sign -rawin`で署名する | 自動的な鍵rotation、threshold署名、metadata期限、役割別の委任 |
| bundle検査 | [msd-update](../../../board/cardputerzero/rootfs-overlay/usr/sbin/msd-update)がtarのmember名・通常file・4件という構成を調べ、作業領域へ展開する | archive parserの安全性や資源上限の完全な証明。署名が有効でも、展開前の処理がすべて安全になるわけではない |
| target署名検証 | 展開後のmanifestと署名を、固定公開鍵で`pkeyutl -verify -pubin -rawin`に渡す | 正しいimageが正しいboard向けか、metadataの鮮度、改ざん可能な起動媒体に対するverified boot |
| image照合 | manifestの2 hashを検査し、`sha256sum -c`でimageを照合する | hashだけによる発行者の認証。攻撃者も置換imageのhashを計算できる |
| 版比較 | 実行中の版とbundleの十進数の版を比較し、古い版や版のないbundleは原則拒否する。明示した`--allow-downgrade`では許可する | SemVerの比較、永続的な最高到達番号、媒体を戻す攻撃に対するrollback防止。実行中と同じ番号も禁止する設計ではない |
| 書込みと確定 | 非active側への書込み、readback、永続化、tryboot、health後commit等の契約がある | 正当だが古い版の配信拒否、電源断・SD故障・実機firmware段階を含む全経路の成功 |

公開鍵は秘密ではありませんが、最初から信頼できる経路でimageへ入れる必要があります。bundleが持ち込む鍵を、そのbundleを認証する根拠にしてはいけません。また、秘密鍵は署名側にだけ必要です。targetへ入れない構成を維持します。

## 同じEd25519でも一致しないもの

現行で生成する開発鍵はEd25519です。置換時には、署名と同じ**manifestのbytesそのもの**を検証します。imageのSHA-256を計算することと、manifestを別途prehashして署名APIへ渡すことは別です。

| 確認項目 | 誤って同一視しないもの | 移植条件 |
|---|---|---|
| 署名方式 | pure Ed25519、Ed25519ctx、Ed25519ph、独自のEdDSA/hash構成 | [OpenSSL 3.6 manual](https://docs.openssl.org/3.6/man7/EVP_SIGNATURE-ED25519/)と相手のAPIを照合する。現行のrawメッセージ署名を、prehash APIへ無言で変更しない |
| libsodium API | single-partのdetached検証と、multi-part検証 | [公式manual](https://libsodium.gitbook.io/doc/public-key_cryptography/public-key_signatures)はmulti-partをEd25519phとし、`Ed25519ph(m)`と`Ed25519(SHA512(m))`も異なると説明する。小さく上限を設けたmanifestにはsingle-partを比較する |
| Monocypher API | 基本EdDSAとoptional Ed25519、通常検証と`_ph_`検証 | [optional header](https://github.com/LoupVaillant/Monocypher/blob/907e90ddd4c78f02e0d49e90384e4197f7dcdf26/src/optional/monocypher-ed25519.h)とmanualを基準にする。`crypto_ed25519_check`の入力長を呼出し前に検査する |
| 鍵の表現 | PEM/DERの公開鍵、raw 32-byte公開鍵、32-byte seed、公開鍵を付加した64-byte秘密鍵、暗号化した秘密鍵 | 同じ鍵materialでもcontainerは違う。固定したhost toolで変換し、算法・長さ・指紋を検査する。PEMの末尾を固定offsetで切り出すような変換はしない |
| APIの成功値 | libraryの戻り値、検証結果の別引数、shellの終了status | libsodium・Monocypherの成功値と、BoringSSL/AWS-LCの`ED25519_verify`の成功値は異なる。wolfCryptは戻り値に加え`res`を持つ。helperは全失敗を非0で返し、異常系で検証する |
| manifest表現 | LF/CRLF、末尾改行、空白、field順序、UTF-8、署名対象と表示対象 | parseし直した内容ではなく、決めた正規形または取得bytesを検証する。署名後の整形をしない |
| 署名の妥当性 | 正しい署名の成功と、異常な点・scalar・非canonical表現等の拒否 | RFCの正例だけでなく、実装ごとの拒否条件を照合する。互換性のために不正署名の受理範囲を広げない |

PEMからraw公開鍵への変換をhostで行う案なら、target側のASN.1/PEM parserを減らせる可能性があります。ただし、変換tool・key fingerprint・imageへ組み込む処理は新たな信頼対象です。秘密鍵の形式まで変える必要があるとは限りません。host OpenSSLの署名を保ち、target verifierだけを変える比較も可能です。

## TLSとReleaseの署名を別々に検証する

HTTPSは配信先の認証と転送中の保護、bundle署名は配信物の発行者認証です。片方だけで代用しません。

- GitHub APIのtagやasset名、checksum file、ページに書かれたhashは、単独ではimageの信頼根拠にしません。認証したmetadataがboard識別、image hash・長さ、版、鍵の役割を結び付ける設計を比較します。
- CA trust store、hostname、SNI、証明書期限、時刻、redirectの検証はHTTPS clientの責務です。token等が必要な場合も、別hostへのredirectで送らない契約が要ります。公開Releaseの取得に常設の広い権限tokenを配備する案は避けます。
- mutableな`latest`やtagを見つけただけで書込みを始めず、署名・版・board・size・空き容量・非active slotを検査します。途中切断、誤ったContent-Length、圧縮後／展開後の上限、低速接続・timeoutも拒否条件に含めます。
- 取得・解凍・parser・署名検証・block device書込みを全部rootのnetwork processへ集めない設計を比較します。無権限の取得・検証側と、狭いIPCで非active slotだけを書く特権helperを分ける案です。単にsupervisorを追加するだけでは、この分離は実現しません。

これは自動更新clientの実装ではありません。現行の[build workflow](../../../.github/workflows/build.yml)がimageを構築・保存することと、安全なRelease署名・公開・端末自身の取得が完成していることも区別します。

## 鍵管理・anti-rollbackの比較条件

| 主題 | 比較する設計 | 残る費用・脅威 |
|---|---|---|
| online署名鍵 | GitHub Actions Secret + 保護された実行環境、または外部署名service/HSM | 実行時には鍵または署名権限を使える。Secretの暗号化保存だけで悪意あるworkflow、承認済み依存、ログ・artifactへの流出を防げるわけではない |
| offline rootと委任 | offlineで保管するroot、期限付きonline鍵、用途別role、threshold署名 | root保管、更新儀式、復旧・rotation試験が増える。TUF等の採用比較へ接続し、独自protocolへ同じ機能を安易に再実装しない |
| rootfsに固定した公開鍵 | 信頼する鍵と算法・key IDをimageへ固定 | 単一鍵が侵害された場合の失効、壊れた端末への回復、古いslotとの整合が必要。新鍵を同梱するだけでは、信頼の移行にならない |
| root鍵rotation | 旧信頼根から検証できる新metadata、必要なら旧／新側のthreshold、世代とrole | 古い鍵のreplay、未更新端末、鍵喪失、権限を奪われたonline鍵への耐性を設計・試験する。自動rotationが現行にあるとはしない |
| SemVer | 公開版のMAJOR.MINOR.PATCH、pre-release、build metadataを規定どおり扱う | 文字列の辞書順や日時順と同じではない。内部番号との対応は[Release対応表](../../releases/README.md)のとおり承認済みで、内部番号はtag commitのcommit時刻。manifest仕様は変更しない |
| rollback防止 | 単調増加metadata版／内部番号、必要なら期限・永続的な最高到達値、復旧経路 | 有効な古い署名だけでは鮮度を証明しない。書換え可能なSD上の番号は、媒体を戻す攻撃へのhardware保証ではない |
| A/B rollback | 新版が起動不能なら既知の正常slotへ戻す | セキュリティ上禁止した旧版へのdowngradeとは別。counter更新時点とhealth後commit、電源断、復旧許可の整合が必要 |
| verified boot | trust anchorからbootloader・kernel・rootfsを検証する別のchain | bundle署名やread-only rootfsだけでは成立しない。署名鍵の入ったimageごと差し替えられる物理脅威を含むか、boardの能力と費用を評価する |

GitHub Secretsへ入れる秘密値は、チャット・文書・repository・artifactへ出しません。利用者向けの段階的な設定手順とRelease保護の調査は別の成果物として残る作業です。この文書をその手順の完了とは数えません。

## 採用前に行う試験

これは事前の判定条件であり、実行済みの成績表ではありません。[現行のhost test](../../../tests/msd-update/run.sh)も残し、候補がその場の正例だけを通す実装にならないようにします。

1. 固定した現行host OpenSSLと候補verifierで、同じ公開鍵・manifest・signatureを相互照合します。必要なら逆方向の署名も照合します。RFC 8032等の既知のvector、空メッセージ、末尾改行、上限長も含めます。
2. 誤鍵、誤algorithm、1 byteの改変、0／短い／長い署名、異常な鍵・点・scalar、余分なbytes、壊れたPEM/DER、読み取り失敗を拒否することを確認します。APIの結果を無視する変異も検出します。
3. duplicate field・未知field・不正version・board違い・hash違い・size違い・期限切れ・古いmetadataを、書込み前に拒否する設計を検証します。まだ仕様を決めていない項目は、現行にある機能として数えません。
4. tarのduplicate member、symlink、hardlink、path traversal、特殊file、長い名前、size超過、圧縮bomb、disk-fullを試します。暗号検証より前に触る入力も、無制限に信頼しません。
5. network・parser側から任意のdeviceやactive slotへ書けないこと、IPCの引数・長さ・認証、再起動・timeout・fd受渡し・権限放棄を確認します。AppArmor等のpolicy名の存在だけで合格にしません。
6. key rotation・失効・紛失、metadata freeze、clock未確定、復旧用鍵、成功する更新と失敗する更新、health前後の電源断を比較します。QEMUが扱えないfirmware・SD・実機段階は実機で別に検証します。
7. サイズ・時間・RSS等は同じ条件で5回以上測り、tool・binary hash・設定・command・生の値・失敗も[実験一覧](../../experiments/README.md)から辿れる形で残します。

一次資料と取得の限界は[暗号比較の出典](crypto.md#一次資料と未確認範囲)と[sources.json](sources.json)を参照してください。TUF／Uptane、RAUC、SWUpdate等のframeworkがこの条件のどこを担うかは、保存・更新方式の比較で続けます。
