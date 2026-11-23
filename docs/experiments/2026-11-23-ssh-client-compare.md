# SSH client比較（#9）

- 状態: QEMUでのclient比較完了（製品導入・実機は未確認）
- 日付: 2026-11-23
- 関連: [既存の実装比較](../research/security/ssh-implementations.md)、[暗号と鍵](../research/security/ssh-vpn-and-keys.md)

## 目的と仮説

clientだけを追加する場合のOpenSSH、Dropbear、PuTTYを比較します。
利用者が希望するOpenSSHを第一候補とし、容量だけでなく鍵確認と暗号policyの適合を調べます。
server導入や製品設定の変更は行いません。#9は今回の依頼番号で、S9電源断試験とは別です。

## 採否の基準（測定前）

- Ed25519公開鍵認証での接続を5回中5回成功させ、別host keyを5回中5回拒否すること。
- server、server起動init、host key自動生成をpayloadへ含めないこと。
- 実験時にSDのfilesystemをmountしないこと。製品導入時の永続鍵保存は利用者の明示操作に限定する計画とし、今回実装しないこと。
- 共通rootfsへの追加容量は非圧縮3 MiB以下、SquashFS差分2 MiB以下を目安とします。
  第一候補が超える場合は不合格として記録し、採否を利用者へ戻します。
- 古いalgorithmがbuildに残ることと実際の許可を分けます。TLSのopenssl.cnfだけでSSHを制限できるとは判断しません。

## 条件と反復

基準はmainの82c72840215a287c06bf62828d8159d1aab78f6eです。
既存のoutput-integrityのtarget、kernel、DTBを読み取り専用の基準にします。
候補はそれぞれ新しいBuildroot O=を使い、recipeのclient-only実験overrideをmake変数で渡します。
4並列以下、niceで直列実行します。共通のccacheはwarmで、各package build directoryはcoldです。
構築可否は各1回とし、時間やRAM性能の比較には使いません。
容量は固定時刻でSquashFSを各5回作り、基準のA/A hashも照合します。
QEMUでの接続は正常・別host keyを各5回実行し、終了状態とserver logを照合します。
失敗・中止は保存し、新しいrun IDで再試行します。

## 未確認の点

実機のLCD、Wi-Fi、SD書き込み、処理時間・消費電力は未確認です。
source調査、build結果、algorithm一覧、実際に交渉したalgorithmを区別して記録します。

## 測定結果

上の基準は測定前に固定したものです。[全生値CSV](2026-11-23-ssh-client-compare.csv)、[集計・入力hash・algorithm JSON](2026-11-23-ssh-client-compare.json)、[採否表](../research/component-options/ssh-client.md)を参照してください。正式集計は容量`output-ssh-measure-02`、runtime `output-ssh-runtime-06`だけです。

| client | 追加file bytes | SquashFS全体 bytes | 基準との差 bytes | 正常終了0 | 別host key拒否 |
|---|---:|---:|---:|---:|---:|
| 基準 | 0 | 20,496,384 | 0 | 対象外 | 対象外 |
| OpenSSH 10.6p2 `ssh` | 797,448 | 20,824,064 | 327,680 | 5/5 | 5/5、終了255 |
| Dropbear 2026.94 `dbclient` | 476,400 | 20,701,184 | 204,800 | 5/5 | 5/5、終了1 |
| PuTTY 0.85 `plink` | 899,376 | 20,807,680 | 311,296 | 5/5 | 5/5、終了1 |

容量は各5回とも同じ値・hashで、中央値・最小・最大は上表の値です。OpenSSHは追加3 MiB・圧縮差2 MiBの基準内で、第一候補を維持します。Dropbearが最小ですが、差を性能の差へ読み替えません。PuTTYは非圧縮でOpenSSHより大きく、圧縮後は16,384 bytes小さくなりました。

追加fileはOpenSSHが`/usr/bin/ssh`だけ、PuTTYが`/usr/bin/plink`だけです。Dropbearは`/usr/bin/dbclient` 273,752 bytesと`/usr/lib/libcrypt.so.2` 202,648 bytesです。server・server init・host key自動生成をpayloadへ含めません。PuTTYのbuild対象はrecipeのCLI群で、install payloadをplinkだけに限定しました。

| client | DT_NEEDED（直接参照） | 基準にない追加library |
|---|---|---|
| OpenSSH | libssl.so.3、libcrypto.so.3、libz.so.1、libc.so.6、ld-linux-aarch64.so.1 | なし |
| Dropbear | libcrypt.so.2、libc.so.6、ld-linux-aarch64.so.1 | libcrypt.so.2 |
| PuTTY | libm.so.6、libc.so.6、ld-linux-aarch64.so.1 | なし |

OpenSSHのlibssl依存は、このrecipe条件で得たbinaryの実測で、SSHでTLSを使ったという意味ではありません。共有libraryは既存rootfsにあるものを再利用した差分です。空のrootfsへ導入する総容量や、今後OpenSSLを削減した場合の値ではありません。

## 実行条件と計測器

- source基準commitは`82c72840215a287c06bf62828d8159d1aab78f6e`、Buildrootは`bbbdab36565d4941b6b0449a0eedb5aac8a10c2e`です。保存済みの3候補の`.config`は、いずれも`2026.08.1-245-gbbbdab36565`を記録しています。
- buildは固定`docker/msd-dev`、各`O=output-ssh-compare-01/{openssh,dropbear,putty}/buildroot`、GCC 14.3.0のBootlin 2025.08-1外部toolchain、`-Os`、4並列、nice 19で直列に行いました。初回package directoryはcoldで、ccacheは既存cacheを使用します。cache hit率・時間・RAMを比較した実験ではありません。
- 共通target・kernel・DTBは既存`output-integrity`を再利用しました。kernelは6.18.59-v8、OpenSSLは3.5.9です。この出力を現在のmainから新規buildしたとは主張しません。保存済み`.config`、binary hash、追加file hashを証拠に収録します。
- 圧縮toolは実binaryで確認したmksquashfs 4.7.5。zstd level 22、128 KiB block、2並列、全時刻0、全owner root、xattrなしです。最初のsort wrapperを外した中立な圧縮で各5回を比較しました。製品の既存imageとの圧縮条件を同一視しません。
- runtimeはUbuntu 26.04.1 LTS。固定containerのQEMU 11.1.3とloader・共有libraryをexportし、host userで実行しました。QEMU起動自体をcontainer内で行ったとは扱いません。host sshdはOpenSSH 10.2p1で、127.0.0.1の一時portだけでlistenし、外部公開しません。
- QEMU user-netとUSB NICを使い、guestは10.0.2.15から10.0.2.2のhost loopbackへ接続しました。rootは実験用initramfs、`/run`と`/tmp`はtmpfs、空のSD imageはsnapshotです。SDのfilesystemや`/data`をmountせず、製品initは実行していません。
- throwaway Ed25519のserver鍵・利用者鍵・誤ったserver鍵を生成しました。OpenSSH形式の利用者鍵をDropbear形式・PPKへ変換するtool、strace 7.1はfixtureだけです。straceは専用OpenSSH出力で追加buildしましたが、比較対象のroot treeは先に分離・hash固定してあり、追加toolを含めません。
- 同じ接続先・利用者・commandで、goodとwrongを交互に各5回実行しました。全正常試行でremoteの`SSH_REMOTE_OK`行と終了0、全負対照で固有のhost key拒否と非0を確認します。単なる接続切断・timeout・debugに含まれるcommand文字列では合格にしません。server logにもEd25519 publickey受理15件があります。
- marker後もQMP quit応答・終了0・fallbackなしを必須とし、最終serialを再判定します。deadlineはVM全体で900秒、異常時のTERM/KILLとserver cleanupはそれぞれ5秒で上限を付けます。末尾panic・既知鍵file変更・反復不足・重複も拒否するhost unit testを用意しました。

正式runtimeのprocess結果:

```json
{"qmp_quit": true, "returncode": 0, "fallback": [], "error": null}
```

QEMU本体のSHA-256は`8b5c759a21dd5d841d96b37be4e60e3b324869dff22250b581c856e36ac15b73`です。起動wrapperのhashとは区別します。`run-qemu`出力はpathだけを相対表記にしています。原文は証拠archiveにあります。

```text
run-qemu: sha256 7b0b7c001845d0664d5c4c37b087236365eb09d33d61319caa03cd6c3a81a5a6  output-ssh-runtime-06/qemu-launch
run-qemu: sha256 45d52f6e148cebaee66ecbc9735c6260ec23ca8c9ad0b00032cf04d20f1420e8  output-integrity/images/Image
run-qemu: sha256 211465fc4c8d0da8657daacbc0fea9ed4d4aff91f7d9c2059a0fe05caa0190a5  output-ssh-runtime-06/qemu.dtb
run-qemu: sha256 3b6a07d0d404fab4e23b6d34bc6696a6a312dd92821332385e5af7c01c421351  output-ssh-runtime-06/unused-sd.img
```

## file書込みと暗号の観測

straceのfile syscallとHOME内file hashを各試行の前後に採りました。3候補とも既存known_hostsの内容は不変です。OpenSSHのHOME内fileに変更はなく、書込みopenは`/dev/null`だけでした。Dropbearは既存known_hostsを`O_RDWR|O_CREAT|O_APPEND`で開き、`/dev/urandom`も書込みopenしました。PuTTYは正常時・拒否時とも`~/.putty/randomseed`を書込みopenし、前後hashが変わりました。実験ではすべてRAM内です。

これは全write syscall・metadata・SD sector・実機FTLのゼロ書込みの証明ではありません。特にDropbearのhash不変と、書込みopenがないことは同義ではありません。製品導入時には鍵・known_hosts・PuTTYのseedの置き場所と書込み時機を[write-policy](../design/write-policy.md)に従って設計する必要があります。

暗号の全queryはJSON、比較は[採否表](../research/component-options/ssh-client.md)にあります。OpenSSHの実交渉はML-KEM/Curve25519とChaCha20-Poly1305、PuTTYの表示はNTRU Prime/Curve25519とAES-256 CTR・HMAC-SHA-256でした。3候補のhost key・利用者鍵はEd25519です。OpenSSHの能力には旧方式が残り、既定MACにもSHA-1があります。TLSのopenssl.cnfだけをSSH制限とは扱わず、製品用の許可・拒否設定は未実装です。PuTTYの全IDはELF・sourceの候補列であり、全方式のruntime queryや全交渉の成功を表しません。

## 失敗・除外した試行

| run | 実際の結果 | 集計での扱い |
|---|---|---|
| build/容量01 | OpenSSH・Dropbearは成功。PuTTYはcompile後にinstall先を`buildroot-build/plink`と誤り失敗 | 元CSV・logを保持。PuTTYは同じ専用Oをwarm再利用し、正しい`plink`からinstallだけを再試行して成功。新しいlogへ記録しました |
| 容量01 | 既存mksquashfs wrapperが以前のsort listを追加し、存在しないmoduleへの警告を出しました | 正式容量から除外。入力を保持し、`.orig`で別出力02へ再測定。module listを新しいものに書き換えて成功扱いにはしません |
| runtime01 | NICをeth0と仮定して失敗。serialはusb0の登録を記録 | 計測器の準備失敗。NICを検出する形へ修正し、新しいrunへ進みました |
| runtime02 | targetのBusyBoxにtimeout appletがなく、正常・負対照とも127 | clientの拒否成功とはしません。targetの設定を確認し、不要なapplet依存を外しました。VM全体のdeadlineは維持します |
| runtime03 | OpenSSHだけの事前試行、正常0・負対照255 | 各1回なので正式反復と分離します |
| runtime04 | Dropbearが`[host]:port`の行を一致とせず、未知hostの確認待ち。計測器だけをSIGINTで中止 | OpenSSHの完了10試行も正式集計から分離。中止要求とTERM fallbackを保持。以後はplain hostname行も用意し、BatchMode・StrictHostKeyCheckingを明示しました |
| runtime05 | 全client commandは終了。PuTTYの負対照文言をparserが認識せずrun全体を失敗と判定 | 古いCSVのvalidを成功へ変更しません。固有文言のunit testを足し、新規run06で全30試行を反復しました |
| runtime06 | 正常15・負対照15が期待どおり、QMP終了も合格 | 正式runtimeです |

一次資料の取得でPython urllibが403を受けたため、同じ公開配布元のcurl取得を使用しました。install再試行の最初の呼出しはcontainerへ標準入力が渡らず未実行で、終了0をbuild成功の根拠には使いません。記録されたinstall log・追加fileの存在とhashで実行を確認しました。既存smokeと凍結cloneは変更・停止していません。

## 再実行

以下の出力先は空である必要があります。既存の記録を消して実行しません。candidateは`--variants openssh dropbear putty`、反復は`--repetitions 5`で選べます。容量だけなら`--measure-from`で固定済みのclientと依存を再利用し、指定した`--reference`のtargetへ組み直せます。旧基準のroot全体は再利用しません。Buildrootが下記の実験時commitと違う場合は止め、専用cloneのsubmoduleを基準commitへそろえてから実行します。

```sh
test "$(git -C vendor/buildroot rev-parse HEAD)" = \
  bbbdab36565d4941b6b0449a0eedb5aac8a10c2e || exit 1
docker/msd-dev python3 board/cardputerzero/tools/bench/ssh-client-compare/build.py \
  --reference output-integrity --out output-ssh-compare-new
docker/msd-dev python3 board/cardputerzero/tools/bench/ssh-client-compare/runtime.py \
  export --out output-ssh-tools-new
# straceが必要な場合は、fixture用の専用Oでvendor recipeからbuildする
docker/msd-dev make -C vendor/buildroot O=/work/output-ssh-compare-new/openssh/buildroot \
  BR2_EXTERNAL=/work BR2_JLEVEL=4 -j4 strace
python3 board/cardputerzero/tools/bench/ssh-client-compare/runtime.py run \
  --build output-ssh-compare-new --tools output-ssh-tools-new --out output-ssh-runtime-new \
  --strace output-ssh-compare-new/openssh/buildroot/target/usr/bin/strace
python3 board/cardputerzero/tools/bench/ssh-client-compare/test_runner.py
```

共通targetを別の保存出力にする時は`--reference`も明示し、差分容量を同じ数値とは見込みません。QEMUのexportは同じarchitectureのhost用で、localhost sshdの起動権限と空きportが必要です。fixtureの秘密鍵・initramfs・root treeは公開しません。

## 集計器と版表記の訂正

PR #292のreviewを受け、保存済みの入力から派生CSV・JSONとoption表を再生成しました。QEMU・client build・容量測定は再実行せず、生の証拠archiveは書き換えていません。変更前の抽出表・要約もarchive内に履歴として保持します。

- Buildrootを`8b238854`とした本文は誤記でした。archive内の3つの`.config`、source基準commitのsubmodule参照、保存したrecipe 6 fileのhashを照合し、上記の`bbbdab36565`へ訂正しました。vendorは変更していません。
- `--measure-from`で基準を変えると旧root全体が混入する不具合を修正しました。第2回reviewでは集計側にも旧`build/files.json`を読む箇所が残っていたため、追加file・依存・ELFの参照を容量測定先へ統一しました。新基準に既存のlibraryは追加bytesへ含めません。今回の正式容量では、3候補の基準file内容が共通targetと一致し、この条件は発生していません。追加bytes・圧縮差・hashは元のままです。
- 正式集計はQMP quit・終了0・fallbackなし・errorなしを満たす最終runだけを許可します。準備段階の`failure.json`も失敗として保持します。今回の正式run06は元からこの条件を満たしており、正常15・負対照15の判定は変わりません。
- straceがないrunの書込みopenは`null`（未観測）とし、空のtraceとは区別します。正式runの`trace_available`は各候補10/10です。
- configureの大文字を保持し、`--with-Werror`等を完全名で再抽出しました。option表は896件から897件へ変わりました。`ssh -G`の`identityfile`は最後の1件だけでなく、出力順の6候補をJSON配列とCSVの複数行cellに保持します。
- Windows宣言にUnix cacheの`build=OFF`を割り当てず、非対象platformとしました。`BR2_PACKAGE_DROPBEAR_SMALL=y`は明示指定ではなく既定維持へ分類を訂正しました。build条件・binary・製品の採否は変えていません。

## 環境の補足

固定containerのimage IDは`sha256:1aea11386e31cc82eff0807de3e372a0b4443c881f3bc3765a56810b32e2ca65`です。共通ccacheの終了後statsはcacheable 93,683・hit 48,361・miss 45,322で、他のbuildも含みます。開始時statsは未採取なので、このclient比較のhit率としては使いません。

## 生証拠の保存

[証拠commit c54603a](https://github.com/uist1idrju3i/MSD-Linux/tree/c54603a2bcd2fdaf7de099b04abda377f12449ed/ssh-client-compare/2026-11-23)を共有証拠branch `data/fs-compare-experiments`の`ssh-client-compare/2026-11-23/`に保存しています。このbranchはmerge・削除せず保持します。初回の`devin/1795399034-ssh-client-evidence`から移しましたが、旧branchも今回は削除していません。`pack-02/evidence.tar.gz`は676,360 bytes、SHA-256は`91f1c8e2467a13242a6b3eab9316e026493528f3ae1af14f5e86d3686a080139`のままです。

push後、既存のobjectを共有しない新しいbare repositoryへremoteから取得して照合しました。保存した6 fileすべてが移行用copyとbyte単位で一致し、うちarchive・manifest・metadataの5 fileは旧保存先とも一致しています。READMEは保存先の案内だけを更新しました。archive内の130 memberも旧archiveとbyte単位で一致し、公開file 129件のhashとbytesはmanifestと一致しました。

Git作業treeの未使用の取得先に展開します。固定SHAを取得するため、共有branchに後続の証拠が追加されても同じ内容を参照できます。

```sh
evidence_sha=c54603a2bcd2fdaf7de099b04abda377f12449ed
git fetch origin "$evidence_sha"
git archive "$evidence_sha" ssh-client-compare/2026-11-23 | tar -xf -
printf '%s  %s\n' \
  91f1c8e2467a13242a6b3eab9316e026493528f3ae1af14f5e86d3686a080139 \
  ssh-client-compare/2026-11-23/pack-02/evidence.tar.gz | sha256sum -c -
mkdir ssh-client-compare/2026-11-23/raw && \
  tar -xzf ssh-client-compare/2026-11-23/pack-02/evidence.tar.gz \
    -C ssh-client-compare/2026-11-23/raw
```

129 fileとmanifestの130 memberをbyte照合しました。公開copyの5 fileはURL query・Set-Cookieを伏せ、元fileと公開copyのhashをmanifestで分けています。秘密鍵・root tree全体・initramfs・SD imageは公開しません。古い事前試行のrunner本文は未保存のものもあり、hashだけの記録と区別します。guestの実行scriptは各rootのinitから保存しました。正式測定の後にgenerated settings用のshellcheck注釈と、集計CSV・option表出力のLF化を加えました。runtime動作・CSV field値は変更しておらず、測定時のsourceはarchiveのものです。

archive作成の初回は固定containerにzstd commandがなく失敗しました。最初のmanifestを保持し、Python標準libraryのgzipで別のpack-02へ保存しました。環境を入れ替えた結果ではありません。候補clientの失敗とは別の準備失敗です。

## 制約と残件

実機LCD・Wi-Fi・鍵入力・SD書込み・電力・対話PTY・forwarding・agent・PKCS#11/FIDO・全algorithm交渉は未確認です。計測用straceの影響、既存rootfsの共有library、同一VM内での反復を含むため、速度やメモリの優劣には使えません。PuTTYのalgorithm候補列と条件付きoptionの到達性にはsource確認だけの項目が残ります。製品の永続鍵保存・host確認UI・英日progress・実行時の暗号制限は後続の設計・検証事項です。
