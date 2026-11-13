# OpenSSL 3.5.9のPQC容量とTLS groups（判断資料）

## 計画・固定条件・採否基準（実行前）

基準は`121e9ae1878252a675efb6714bc36e91f488e331`。製品設定は変えず、PQCの採否は利用者が決めます。固定Buildrootの外部overrideが選ぶOpenSSL 3.5.9を使い、default、`no-ml-kem`、`no-ml-dsa`、`no-slh-dsa`、三つ全部の5構成を比較します。asm、Ed25519、CMS、CLIを維持します。

容量は同一toolchain・Configure基準引数・stripと固定rootfs内容で各1回構築します。容量測定を速度比較に転用しません。defaultのA/A圧縮を対照とし、同じsize/hashになることを確認します。各構成の実Configure引数とdisabled、ELFのsize/hash、正規化SquashFSのsize/hashを記録します。group設定だけを変える案はalgorithmを削除しないので、ELF容量削減とは別に扱います。

endpointは管理者の2026-11-13T04:18:53Zの原文を保存し、このVMのOpenSSL 3.5.5で6 host×2 groups条件を1回ずつ再確認します。接続先の将来の全edge、認証・公開配信の成功を証明しません。機能確認なので1回とし、成功・失敗・timeoutを区別します。

安価に実施できる場合だけQEMUでX25519とhybridの暗号演算またはlocal TLSを各5回測り、中央値・最小・最大を出します。実機速度やWAN latencyの根拠にしません。実行できなければ理由を残します。

判断材料の成立条件は、5構成の構築成功、指定optionが実際に効いたこと、Ed25519とCMS維持、endpointの正常／拒否の保存、A/A一致です。容量が何byteなら自動採用という閾値は設けません。性能・互換・HNDLと保守を併せた選択は未決定のままです。

## 結果・生データ

5構成のbuildとEd25519／RSA CMS確認が完了しました。採否は**未決定**です。一次資料・HNDL・consumer別の制限・推奨案は[研究本文](../research/component-options/openssl-pqc-groups.md)へ分けました。

| 構成 | libcrypto.so.3 | libssl.so.3 | openssl CLI | 正規化rootfs | defaultからのrootfs差 |
|---|---:|---:|---:|---:|---:|
| default | 5,205,008 | 929,464 | 959,608 | 20,705,280 | 0 |
| no-ml-kem | 5,131,120 | 929,464 | 959,608 | 20,680,704 | −24,576 |
| no-ml-dsa | 5,135,256 | 929,464 | 959,608 | 20,684,800 | −20,480 |
| no-slh-dsa | 5,061,528 | 929,464 | 959,608 | 20,680,704 | −24,576 |
| all-three | 4,909,696 | 929,464 | 959,608 | 20,631,552 | −73,728 |

単位はbyte。三つ全部の削減はlibcryptoで295,312 byte、SquashFSで72 KiB（約0.36%）です。libssl・CLI・legacy provider（124,744 byte）はsizeもhashも5構成で同じでした。rootの全file内容・symlinkを比較すると、差は各構成ともlibcryptoだけです。圧縮の配置と4 KiBのpaddingがあるため、単独削減量の合算を未測定の組合せの値としません。Groupsだけを制限してもalgorithm実装は残ります。

defaultのA/Aは2回とも20,705,280 byte、SHA-256は`7512efb105d76341100b46ed6ca4ba3060f63bf5e2e5328f02f80f48f3fd364e`でした。これは同じrootを再圧縮した対照で、独立した2回のcompileではありません。

## 入力・環境と測り方

- 実行checkoutは基準commitと今回の測定器のdirty差分。製品のConfigure引数・openssl.cnf・公開鍵・更新形式は変更しません。実行時の測定器と入力hashは[JSON](2026-11-13-pqc-groups.json)、詳細は[raw archive](2026-11-13-pqc-groups-evidence.tar.gz)に保存しました。
- OpenSSL archiveは`603f5602e2eef00d77fbd429d34dcd5822bb301757a1bc9cdb24c670f1eb859a`で、外部hash fileと一致。Buildrootはgitlinkの`8b238854d909c9cce32ef9671d968b03e323b55d`。recipeの既存patch 2件も同じ内容です。
- `output-openssl-lts`の既存toolchain・configdata・target・imageを対照にし、各OpenSSL buildは新しいdirectoryへ展開しました。既存download・toolchainはwarm、各variantのobjectは新規。compiler cacheを消去したcold build時間の比較ではありません。
- Docker image IDは`47cc0b8cfd878a4fb413c376d52a2b6a9199454c97b1d2aec8df7a3a1b4a8e7d`。Debian 13、Python 3.13.5、GCC 14.3.0、binutils 2.43.1、mksquashfs 4.7.5、QEMU 11.1.2を使いました。host情報と実Configureの全`perlargv`・disabledはJSONとarchiveにあります。
- 既存Configureの引数とCFLAGSへ各no-*だけを追加し、`make -j8 build_sw`、`install_sw`、同じtarget stripの`--strip-unneeded`を実行しました。asm・EC/ECX・CMS・appsが無効化されていないこと、各指定がdisabledへ入ることを検査しました。host OpenSSLの再buildや製品のfull buildではありません。
- 保存targetの写しへ3 ELFとlegacy providerを置換し、zstd level 22、128 KiB block、2 processor、all-root、時刻0、xattrsなしでSquashFS化しました。これは比較用の正規化rootfsで、配布imageの再生成ではありません。out-of-tree配置・strip・正規化条件が過去の測定と異なるため、古い容量値との差をPQCの効果とは扱いません。

### 再実行

同じ基準出力を用意し、既存runを上書きしない新しい出力名を選びます。compilerとimageのhashが違う場合は別条件として記録します。

```sh
docker/msd-dev python3 board/cardputerzero/tools/bench/pqc-groups/run.py --reference output-openssl-lts --out output-pqc-new
docker/msd-dev output-openssl-lts/host/bin/aarch64-linux-gcc -Os board/cardputerzero/tools/bench/pqc-groups/hello.c -lssl -lcrypto -o output-pqc-new/hello
docker/msd-dev python3 board/cardputerzero/tools/bench/pqc-groups/qemu.py --reference output-openssl-lts --variants output-pqc-new --hello output-pqc-new/hello --out output-pqc-qemu-new
python3 board/cardputerzero/tools/bench/pqc-groups/probe.py --out output-pqc-probe-new.log
python3 tests/pqc-groups/run.py
```

`probe.py --help`で出力指定を確認してください。endpointは将来同じ結果になる保証がありません。defaultのコンパイル済みCLI・libの転送はread-only USB、鍵・payload・CMSの一時fileはguestの`/run`です。

## QEMU機能確認・暗号演算

`raspi3ap`、512 MiB、icount offで既存imageをbootしました。kernelは6.18.59-v8、imageのbannerは`0d86c84-dirty`。今回のmainをclean full buildしたimageではなく、保存済みの対照を使っています。kernel・DTB・SD・転送ELFのhashはrawにあります。各variantの3 ELFのhashをguest内でも採取し、loaderへ`LD_LIBRARY_PATH`を渡しました。

5構成すべてでEd25519の署名・検証、改変payloadの拒否、RSA CMSの署名・CAfileによる検証と内容一致を観測しました。list出力のprovider登録は、指定したML-KEM／ML-DSA／SLH-DSAだけが消える5通りの期待値と一致しました。CMSのこの局所試験はRAUC／SWUpdate全体の受理形式やmodule署名の検証ではありません。

defaultのCLIで`openssl speed -seconds 1 -mr X25519 X25519MLKEM768`を同じboot内で5回、常に同じ順序で実行しました。`+DTP`のalgorithm順と`+F9`の3列（keygen・encaps・decaps）を対応付けました。**guestのCPU計時による演算/sであり、TLS handshake/s、WAN latency、実機性能ではありません。**

| algorithm | 処理 | 中央値 | 最小 | 最大 |
|---|---|---:|---:|---:|
| X25519 | keygen | 1244.262 | 968.182 | 1447.619 |
| X25519 | encaps | 538.806 | 514.063 | 577.612 |
| X25519 | decaps | 1186.486 | 1143.860 | 1344.304 |
| X25519MLKEM768 | keygen | 386.486 | 323.944 | 451.563 |
| X25519MLKEM768 | encaps | 342.647 | 236.667 | 370.690 |
| X25519MLKEM768 | decaps | 367.164 | 316.438 | 379.104 |

同じguestではhybridの演算rateが低い結果ですが、順序反転・独立bootの性能A/A・CPU固定をしていません。CPU flagはQEMUが示す`OPENSSL_armcap=0xbd`で、対象機のhardware特性を代用しません。速度優先の採否には実機測定を残します。local TLS／s_timeは追加実施していません。

### offline ClientHello

補助Cプログラムはdefault libsslをmemory BIOへ接続し、SNI `example.test`で最初の出力byte数を測ります。serverにもnetworkにも接続しません。protocol・cipher等を固定する追加設定はせず、groupsだけを変えました。

| groups list | BIO出力byte |
|---|---:|
| DEFAULT | 1552 |
| X25519 | 318 |
| X25519MLKEM768 | 1494 |
| ?X25519MLKEM768:DEFAULT | 332 |

この条件でDEFAULTはX25519単独より1234 byte大きく、TLS record header 5 byteを含みます。差の内訳はkeyshare 1220 byteとsupported_groupsの14 byteです。空groupと不正groupが失敗する負対照も採りました。このhelperは実際のTCP segmentation・MTU・firewall動作を測っていません。

## endpointと保存データ

[管理者の原文](2026-11-13-pqc-groups-user-probe.log)は2026-11-13T04:18:53Zのfileをbyte copyし、[再確認の原文](2026-11-13-pqc-groups-confirmation.log)にVMのOpenSSL version、UTC時刻、全12 command、終了値を保存しました。両方ともhost OpenSSL 3.5.5です。

- github.com、api.github.com、codeload.github.comは、hybrid＋X25519候補からX25519を選択。hybridのみでは終了値1、alert 40。
- objects.githubusercontent.com、release-assets.githubusercontent.com、muromi.moeは両条件でX25519MLKEM768、終了値0。
- timeoutはありませんでした。hybridのみという条件はclassical X25519も含むhybrid groupを一つ許す意味で、単独ML-KEMではありません。

### 失敗した試行・検査器

容量r1はdefaultの4 ELFまで測った後、`SOURCE_DATE_EPOCH`とmksquashfsの明示時刻の競合で終了値1。明示時刻を残し、圧縮commandだけ同環境変数を外したr2が完了しました。r1を消さず、集約CSVでは未完了trialの行をvalid=0としています。

QEMU r1は測定shellの余分な`+`を`req`が拒否し、機能・速度測定前に終了値1。終了後に3 commandを修正し、新しいr2を実行しました。r1のshellとserialをarchiveに残しました。成功後にparserへ欠損・重複・非有限rate等の拒否を追加し、保存rawを再解析しました。archiveの`runner.py`は実行時の写しです。

host testsは正常・空・欠損・command失敗・serial不完了・不正rateの7 test。rawから5機能結果、5 repeat×2 algorithm、4 ClientHelloを検査しました。再build・QEMU再実行を意味するものではありません。

[CSV](2026-11-13-pqc-groups.csv)は72行。各ELF／rootfs hash、30演算rate、ClientHello、機能結果、失敗trialを含みます。[raw archive](2026-11-13-pqc-groups-evidence.tar.gz)は35 file・466,559 byteで、元のbyte列と展開後を照合しました。SHA-256：

```text
f27c40920f33e419423af950458fb3acd2c18eb8a4b6e176f647fc065d00c7bb
```

## 結論と未確認

事前条件の5構成build・option反映・Ed25519／CMS維持・endpointの成功／拒否保存・A/A圧縮一致を満たしました。容量削減だけで自動採用する閾値はなく、[利用者の判断](../design/product-decisions.md)は未決定です。

実機CPU・電力・boot時間・SD／FTL・長期運用、将来のwpa_supplicant／RAUC／SWUpdate／SSH／API、企業proxy・middlebox・他edge、鍵rotationとPQC署名の製品実装は未確認です。QEMUのKEM演算を実機・完全なTLS handshakeの性能と扱わず、endpoint観測を署名・更新の完全性や公開配信の証明に使いません。
