# openssl.cnf限定のQEMU機能実験

- 状態: QEMU機能実験完了。製品は未変更
- 日付: 2026-11-18
- 関連: [設定草案](../research/component-options/openssl-minimal-runtime.md)

## 目的と仮説

OpenSSL 3.5.9のbinaryを変えず、設定だけで古いTLSを拒否し、更新署名、LUKS2、署名付きmoduleの利用を維持できるか調べる。製品defconfigとoverlayは変更しない。採用は別判断とする。

## 採否の基準

結果を見る前に次を固定する。C0は保存済み設定、C1はMinProtocol=TLSv1.2、CipherString=DEFAULT:@SECLEVEL=2、default provider明示有効化、config_diagnostics=1。C2はC1のCipherStringをECDHE+AESGCM:ECDHE+CHACHA20:!aNULL:!eNULL:!PSK:@SECLEVEL=2へ変更し、TLS 1.3のAES-GCMとChaCha20-Poly1305、Groups=DEFAULTを明示する。C2もTLS 1.2は残す。CA/CSR節は全条件で維持する。

各条件3回の独立bootと、同じC0画像を使う別名A/Aを3回実行する。時間の性能比較ではなく機能確認なので3回とする。正常Ed25519署名は受理、不正署名は拒否し、拒否時はRAM上の模擬slot/stateを変更しない。Argon2idとPBKDF2のLUKS2 format/open、署名付きmodule load、loopbackのTLS 1.2/1.3成功を要求する。C1/C2はTLS 1.0/1.1拒否、C2はTLS 1.2 CBC拒否も要求する。弱いpeer同士の対照で古いTLS自体が試験可能か確認する。壊れた設定は成功扱いにしない。

一時file、秘密鍵、試験volume、TLS logはguestのRAMへ置く。試験前後とidleのp7 block統計、mount、data内容hashを保存する。p7のwriteが0でない場合、設定変更が原因とは断定せずC0/A/Aと区別して記録する。起動処理の書込みは別範囲とする。実機SD内部のwriteは検証しない。

## 条件と手順

基準checkoutはd337ff1ed4626f883af2a94d6f9d661b390b91f7。保存済みoutput-openssl-ltsのrootfs/kernel/SDを入力とし、mainからのfresh full buildではない。各variantのrootfsは独立したoverlayコピーで再packし、設定以外の通常file内容が一致することを照合する。OpenSSLの版、build feature、ELFは変更しない。実binaryの版/hash、生成config、Configure設定、QEMU・toolchain・Buildroot情報を出力へ保存する。既存build/download/cacheはwarmで、compile時間は測らない。

```sh
docker/msd-dev python3 board/cardputerzero/tools/bench/openssl-cnf/run.py --reference output-openssl-lts --out output-openssl-cnf-r1 --runs 3
```

raw logと欠測・失敗を保持し、新しい試行は別の出力先を使う。未完了serialや非zeroのprobeを成功扱いにしない。結果は同名CSVへ集計し、画像ではなく設定・測定器・raw log・入力hashを小さい証拠archiveへ保存する。製品へ測定hookを残さない。

## 測定器と実行範囲

loopbackのserver側とclient側を分け、試験対象側は既定の`/etc/ssl/openssl.cnf`を使う。相手側だけはSECLEVEL=0の専用設定とする。相手同士ならTLS 1.0/1.1が接続できることを確認し、機能削除や証明書の不備による失敗と区別する。TLS 1.2はAEADとCBCを別に試す。TLS 1.3ではX25519MLKEM768の選択もlogへ残る。

`msd-update install`を実際に呼ぶが、公開鍵、DTの模擬値、入力bundle、inactive slot、version、stateはRAMへ向ける。正常署名の後はpayloadとstateを照合し、不正署名は固有のerror文とslot/state不変を要求する。firmware trybootや本物のslot更新の試験ではない。既存`tests/msd-update/run.sh`もhost回帰で実行する。

LUKS2 volumeはRAM上の64 MiB file。Argon2idはmemory上限65,536 KiB、parallel 1、強制iteration 4、PBKDF2は強制iteration 1,000を使う。これらはKDF機能の確認用で、製品向け費用やPIN強度の提案ではない。format/open各回のdebug、luksDump、statusを保存し、open成功だけからKDFを推測しない。

生成imageのmodprobeはBusyBoxで、kmod CLIとmodinfoはない。そのため小さい測定用C programから既存libkmodを呼び、configs moduleをloadする。libraryやmoduleは置換しない。load後の`/proc/config.gz`でMODULE_SIG_FORCE=yを確認する。署名の実検証はkernelで行われるので、この結果だけでuserspace OpenSSLがmodule署名を検証したとは扱わない。

一時fileとlogは`/run`、更新の展開先も明示したTMPDIRを使う。`/data`はext4、rw/noatime/noinit_itableである。`sync`と10秒待機後に3秒idleを測り、caseごとにuptimeとp7のwrite I/O数・512 byte sector数の差を保存する。終了後も3秒idleとdata内容hashを照合する。個々のblock発行時刻やworkerの追跡ではなく区間集計であり、case間やbootのwriteを0と主張するものではない。

## 固定環境

| 項目 | 実際の条件 |
|---|---|
| 開始日・記録 | 2026-11-18。JSTで翌19日まで実行 |
| checkout | d337ff1ed4626f883af2a94d6f9d661b390b91f7 |
| vendor Buildroot | 75f325ad84251ee9d903467f84d3683e3bcf3fd5。今回の実効値であり、古い調査文書の8b238854とは区別する |
| builder kernel | Linux 7.0.0-43-generic、x86_64 |
| host userspace | Ubuntu 26.04.1 LTS |
| builder userspace | Debian GNU/Linux 13、固定msd-dev image |
| QEMU | 11.1.2、raspi3ap、512M、TCG、icountなし、CM0 DTB |
| guest kernel | 6.18.59-v8、MODULE_SIG_FORCE=y、RSA/SHA-256 |
| cross compiler | aarch64-linux-gcc 14.3.0。表示はBuildroot 2021.11-18033-g83947c7bb6 |
| target | OpenSSL 3.5.9、cryptsetup 2.8.7 |
| binary対照 | 全variantのopenssl/libcrypto/libssl/legacy.so/updaterは同じhash |

全variantを同じzstd/128 KiB block、all-root、xattrなし、時刻0で再packした。元imageからのmetadata完全再現やboot性能の比較ではない。展開時はcontainerの権限によりchownだけが失敗するため、その診断だけを許可する。別の展開errorは拒否する。保存済みmksquashfs wrapperには古いsort entryが残っており、存在しない16 pathを無視する警告が各variantで出た。Docker環境とwrapperを確認し、機能の欠落や環境未読込とは区別した。設定以外の通常fileとsymlink、file modeの一致をmanifestで照合した。

## CA/CSRとprovider

製品scriptで確認した署名consumerは[msd-update](../../board/cardputerzero/rootfs-overlay/usr/sbin/msd-update)のpkeyutlで、[post-image](../../board/cardputerzero/post-image.sh)もbuild時にpkeyutlを呼ぶ。これらはCA database/serialを使わない。ただし対話CLIや将来consumerまで未使用とは証明できないので、`ca`、`CA_default`、`req`、extension等の節は全て残した。今回のTLS証明書生成はreqを実際に使う。

cryptsetup 2.8.7の`lib/crypto_backend/crypto_openssl.c`は専用library contextへdefaultとlegacyをtry-loadする。debugの`[default][legacy][threads][argon2]`をformat/open両方で照合する。一方、CLIのprovider一覧にlegacyがないことも確認する。legacyを全applicationへ自動有効化した実験ではなく、旧式暗号の全互換性を検証したものでもない。

## 試行の履歴

| 出力 | 状態・扱い |
|---|---|
| r1 | 展開のchown失敗で停止。機能結果なし |
| r2 | guestにmodinfoがなく停止。BusyBoxとlibkmodの構成を確認し、測定用libkmod callerへ変更 |
| r3 | guestにtimeoutがなくTLS対照が失敗。shellのwatchdogへ変更 |
| r4 | 25 caseは通過したがtarの`-z`が未選択で証拠回収に失敗。成功には数えず、非圧縮tarをhost側で圧縮する形へ変更 |
| r5/run 1 | C0/C1/C2/C0-AAのpilot。計器の正の対照前なので正式反復には数えない |
| r5/calibration | C0の独立copyへ64 KiBを書き、同期・削除も実行。p7で240 sectorの増加を確認 |
| r5/run 2以降 | calibration後の正式試行。全条件を同じ測定器で反復 |

calibration logの終了はJST 2026-11-19 00:10:11、最初の正式C0/run 2のserial作成は00:10:53。run 1を正式3回へ混ぜず、追加run 4を実行した。追加と校正のdriverは証拠archiveに含める。run 4は他のQEMUと一部並列に動いたが、時間の性能比較は行わない。

## 結果と未確認

正式run 2・3・4の12 boot、計300 caseが期待どおり終了した。別にpilot 4 bootの100 caseも保存した。A/AはC0と同じ画像から独立copyを作り、C0-AAの別名で正式3回繰り返した。値は[CSV](2026-11-18-openssl-cnf.csv)、入力・生log・校正と追加driverは[証拠archive](2026-11-18-openssl-cnf-evidence.tar.gz)に収録した。

| 条件 | 更新署名とLUKS2 | TLS 1.0/1.1 | TLS 1.2/1.3 AEAD | TLS 1.2 CBC | p7の各case差 |
|---|---|---|---|---|---|
| C0 | 正常受理・不正拒否、両KDF成功 | 両方向で拒否 | 両方向で成功 | 両方向で成功 | 全て0 sector |
| C1 | C0と同じ | 両方向で拒否 | 両方向で成功 | 両方向で成功 | 全て0 sector |
| C2 | C0と同じ | 両方向で拒否 | 両方向で成功 | 両方向で拒否 | 全て0 sector |
| C0-AA | C0と同じ | 両方向で拒否 | 両方向で成功 | 両方向で成功 | 全て0 sector |

全bootで壊れたconfigだけがexit 1となり、正常configのprovider/cipher列挙とreqが成功した。cryptsetupは全条件でdefault/legacyを自らloadし、CLIの一覧はdefaultだけだった。libkmodからconfigsのloadも全てrc=0で、署名強制有効のkernelにより受理された。

正式・pilotのidle区間も全て0 sectorで、data内容hashは各bootの前後で一致した。ただし更新のstateと模擬slotはRAMへ向けている。この0を製品のinstallが永続storageへ書かない証拠には使わない。正の対照では64 KiBのpayloadに対しmetadata等を含む240 sectorを検出した。boot、case間の全時間、SD内部FTL、電断後の動作は未確認である。

全条件の再pack済みSquashFSは25,706,496 byteだった。SD imageは入力771,751,936 byteを各variantで1,073,741,824 byteへ拡張し、bootごとに独立copyを使った。容量削減や起動高速化は示していない。C0でも古いTLSは拒否されたため、C1による新たな拒否効果を観測したとはいえない。C1は方針の明記、C2は今回のCBC対照を拒否した追加制限として区別する。applicationがSSL_CONFを上書きする場合まで禁止を保証しない。

| cnf | SHA-256 |
|---|---|
| C0 | `a65a2cb9f4ee8ffdc7ef4f0ac600c0bdafb95b7b1ab457188ac610a62f5ad6b3` |
| C1 | `b9128b9141384ac84c0895ad38f4407664226ede58e41606ee41f1da2b9599e3` |
| C2 | `ebf639af6182de035cf4149eaa4b8f65a3537ac8c9685daf37346992e6090549` |

共通openssl CLIは`4bce4eb8984a47841dd439e077e06d39aa1a514fa0acd5d55e133dccc530d0a2`。rootfs、SD image、kernel、DTB、library、生成config、測定器のhashと全fileの比較はarchive内のinputs.jsonを参照する。archiveは83 file、1,613,599 byte、SHA-256は`cc77a7c23d9be0657909479440e4229f77de61adf230dbd7fe932503172a94bf`。展開後はevidence-sha256.jsonの82項目を照合できる。image本体と秘密鍵は収録していない。

同梱した設定の原文はOpenSSL 3.5.9の[openssl.cnf](https://github.com/openssl/openssl/blob/openssl-3.5.9/apps/openssl.cnf)。C1/C2の変更は本記録のとおりで、Apache License 2.0のLICENSE.txtをarchiveへ同梱した。測定用module callerが動的linkするkmod 34.2のCOPYINGも同梱した。libkmodのbinary自体は再配布していない。

## 結論

C1/C2とも今回の機能基準を満たした。製品defconfigとoverlay、OpenSSLの版・build featureは変更していない。C2の互換性制限はC1と別の選択肢として残し、どちらも自動採用しない。CA/CSR節は維持する。

実機のLCD、SD、KDF費用、TLSの外部server、EAP、RAUC/SWUpdate、旧volumeの全互換性は対象外。dm-verity/FECやrollbackの方針、fs-compare-v2第4段は変更していない。
