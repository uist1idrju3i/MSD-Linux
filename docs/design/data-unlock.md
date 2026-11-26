# /dataの初期設定・PIN解錠・復旧

[文書の案内](../README.md) / [storage調査](../research/storage/README.md) / [製品の決定](product-decisions.md) / [書き込みの台帳](write-policy.md)

## 状態と適用範囲

2026-11-26の利用者決定を固定するPR Aの設計であり、未実装である。コード、image、CIを変更した記録ではない。基準mainは`9abf1683e32820334e18a898f2a8b351ba259322`。実装と観測を区別し、[2026-11-15の調査・設計案](../research/storage/data-luks-btrfs-design.md)は当時の記録として残す。

正式release前のため、既存ext4からの移行・変換・data引継ぎは実装しない。未知の非empty領域を勝手にformatしない。「passwordなし」と共通の初期PINを廃止し、初回起動で端末ごとの設定を行う。初期実装のPIN変更はkeyslotの入替えだけであり、volume keyの交換・再暗号化は後続課題とする。これは2026-11-03の旧決定を置き換える。

| 項目 | 決定 |
|---|---|
| 保存領域 | p7初期容量512 MiB以上。LUKS2の上にBtrfsを作る |
| Btrfs | data・metadataともDUP、checksum xxhash64（mkfs指定は`--csum xxhash`）、zstd透過圧縮 |
| library | cryptsetup 2.8.9のlibcryptsetup。暗号処理を自作しない |
| keyslot | slot 0はPIN、slot 1はrecovery。他のslotを使わず、最後のslotは消さない |
| 暫定暗号設定 | AES-XTS、鍵長512 bit、Argon2id、iter-time 2000 ms、memory上限64 MiB |
| 最終選択 | AES-XTSかAdiantumか、Argon2idのcostは実機測定まで暫定。2000 msは指定値であり実測時間ではない |
| mount | `/dev/mapper/msd-data`を`/data`へ、`noatime,nodev,nosuid,compress=zstd:3` |

DUPは同じSD内の2copyであり別媒体の冗長化ではない。xxhash64と通常のAES-XTSは、悪意ある改変への認証やrollback防止を提供しない。これらを対策済みとしない。

## helperの責務と起動の停止

小さなC helperが入力、RAM内のcounter、slot番号、状態遷移、error分類を持つ。format・keyslot追加・解錠・削除はlibcryptsetupへ任せる。Buildrootのlocal generic-package方式を使い、cryptsetupへのbuild依存を明示してtargetのheader・libraryにlinkする。[msd-console package](../../package/msd-console/msd-console.mk)の構成を参考にするが、PINをmessageのargvへ渡さない。

S02は[early-io gate](../../board/cardputerzero/rootfs-overlay/usr/libexec/msd/early-io)成功後にだけhelperを呼ぶ。gate成功前にはPIN入力、format、解錠へ進まない。QEMUの`hardware-absent-qemu`は既存gateのhardware不在判定であり、PINの供給済み・認証済みを意味しない。

失敗時はS02からexitせず、その場で待つ。rcSはscriptの失敗だけでは後続を止めないためである。処理の停止後に`Boot stopped. Safe to power off.`と表示し、後続init、ready、loginへ進めない。既存dataが無傷であるという保証の表示ではない。PIN待ちに期限は設けない。S01のwatchdogは別processで給餌を続けるため、PIN待ちのtimeoutとしては使わない。

電源投入からinit完了までと起動失敗待機中の画面は、承認済み例外により英語だけとする。初回設定・PIN・recoveryの対話もこの起動中の範囲に含む。文書は日本語、起動完了後のtoolは従来どおり英日併記である。

PINの平文・入力列をargv、log、SDへ出さない。環境変数、kernel cmdline、PIN fileによる製品の入力経路も作らない。入力とcounterはRAMだけに置き、入力bufferの消去、core dump・debug出力の抑止、tty echoの復元をhelperの責務とする。暗号化keyslotに必要なKDF情報と保護されたvolume keyの保存は、PIN平文の保存とは区別する。

## PINとrecovery keyの入力

| 場面 | 入力と遷移 |
|---|---|
| PIN設定 | 4〜64文字の印字可能ASCII（0x20〜0x7E、空白を含む）。数字4桁も受け付ける。先頭・末尾の空白もPINの一部とし、trimしない。2回入力して一致を確認する |
| PIN表示 | ttyのechoを止め、有効な1文字につき`*`を1つ表示する。入力の平文は表示しない |
| 弱いPIN | 6文字未満、またはblocklistに一致する場合は英語で警告するが拒否しない。例：`Warning: This PIN is weak against offline guessing if the SD card is removed.` |
| 通常のPIN画面 | 常に`Forgot PIN? Press Enter on an empty line to use the recovery key.`を表示する |
| 空Enter | recovery keyを使うか確認する。空Enterは誤入力に数えない。取り消せばPIN画面へ戻る |
| recovery生成 | 初回設定時に端末の暗号学的乱数源から160 bitを生成し、base32の英数字32文字として4文字×8組で表示する。表示の区切りは鍵のentropyに含めない |
| recovery保管 | 紙などへ書き写し、SDの外に保管するよう案内する。SDへ平文keyfileを保存しない |
| recovery照合 | 表示後に1回入力して照合する。照合不一致を成功扱いにしない |
| 照合skip | 利用者がskipを選べる。`If you copied this key incorrectly, recovery will be impossible.`と警告し、もう一度確認してから進む。再確認しなければskipを確定しない |
| recovery解錠 | 正しいrecovery keyで解錠した後、新しいPINを2回入力して再設定するまで起動を完了しない |

blocklistの内容・由来と、recovery入力の区切り・大文字小文字の受理規則はPR Bで固定し、設定時の照合と復旧時の解錠で同じ規則を使う。未決定の規則をこのPRで補わない。入力範囲外、長過ぎる入力、EOF、中断を正しい入力と扱わず、PIN bufferの切詰めによって別のPINを受け付けない。

## p7の判定と初期化

S02は読取り失敗・metadata破損を空領域と誤認しない。LUKS2のlabel（またはsubsystem）に`pending`と`ready`を記録し、初期化の途中と完了を区別する。識別に使うfield・値はPR Cで固定し、境界を試験する。

LUKS2 headerが無いときだけ、grow前のp7全体を読み、imageが作ったp7の範囲すべてがzeroであることを確認する。先頭の一部だけでは初期化を許可しない。全体の読取りは数秒〜数十秒かかり得るため、読取り済みbytes・総bytes又は割合と経過時間を表示する。読取りだけであることを示し、`Checking that the entire data partition is empty. Read-only check; safe to power off.`と表示する。読取り失敗はzeroと扱わず停止する。通常のLUKS2起動ではこの全体確認を行わない。

| 状態 | 判定 | 動作 |
|---|---|---|
| (a) 未初期化 | LUKS2 headerがなく、grow前のp7全体（imageが作った範囲すべて）がzero | 初回設定から初期化する |
| (b) 完了 | LUKS2として認識でき、labelが`ready` | slot構成を検査して解錠する。slot 0が無ければrecovery入力から始める |
| (c) 初期化中断 | LUKS2として認識でき、labelが`pending` | 利用者dataはまだ無いものとして初回設定からやり直す。新しいrecovery keyを生成する |
| (d) 不明・異常 | その他の非empty内容、未知のlabel、判定不能な破損やI/O error | formatせず、その場で起動を止める |

(c)では`Initialization was interrupted. Initialization will restart with a new recovery key. The previous recovery key will no longer work.`と伝える。PINも2回入力し直す。`pending`の間は通常の利用へ進めず、利用者dataを作らせない。

headerの初回書込み自体が切れ、LUKS2や`pending`として認識できなくなった場合は(d)で止める。すべての電源断位置から必ず自動でやり直せるとは保証しない。labelだけで電断耐性を実証したことにせず、各書込み境界を後続PRで検査する。

初期化の順序を次に固定する。途中の失敗では次へ進まず、`ready`を先に書かない。

1. PINを2回入力する。
2. recovery keyを生成・表示し、入力照合、または警告後のskip再確認を終える。
3. partitionをdiskの最後まで広げる。MBRのp4とp7を扱い、kernelへ反映する。
4. `pending`を指定してLUKS2をformatし、slot 0へPINを登録する。
5. slot 1へrecovery keyを追加する。
6. mapping `msd-data`をopenする。
7. mapper上に所定のDUP・xxhash64でBtrfsを作る。
8. 所定のoptionで`/data`へmountする。
9. `/data/etc`と`/data/msd-update`など必要なdirectoryを作る。未導入RAUCの状態を実装済みとは扱わない。
10. filesystemの変更を同期する。
11. slot構成と各処理の成功を確認し、LUKS2のlabelを`ready`へ更新して、その永続化の成功を確認する。

growはこの初期化処理の中だけで行い、`ready`の通常起動では行わない。後から大きなSDへ複製した場合の自動拡張も行わない。既存の毎起動の`resize2fs`相当経路は無くす。

genimageの`empty=true`なext4はsuperblockを持ち、zero imageではない。PR Cで生成方法を変更する。p7のtable上の容量だけでなく、raw imageの論理終端をp7の終端まで確保する。zero領域にはsparse fileを利用できるが、copy後の実block数と圧縮artifactの量は別に確認する。

## 誤入力10回とPINの再設定

PIN解錠ではslot 0、recovery解錠ではslot 1を明示し、他slotを探索して成功扱いにしない。libcryptsetupの成功値はslot番号を含む非負の値であり、0だけを成功と判定しない。

PINの認証処理が「passphraseが違う」を表す`-EPERM`を返した場合だけ、連続誤入力counterを増やす。headerの読取り・検証など別段階のerrorを誤PINへまとめない。metadata破損、I/O、OOMなどはcounterを増やさず、その場で止める。空Enter、確認の取消し、入力範囲外は認証失敗回数に含めない。PIN成功で連続回数を0に戻す。counterはRAMだけに置き、電源を入れ直すと0である。

10回目の誤入力後はslot 1を残してslot 0だけを消す。削除成功を確認して自動でrecovery入力へ移り、削除失敗なら起動を止める。slot 1不在など想定外のslot構成で最後のslotを消さない。他のslotを使うことも、全slot消去も行わない。

recovery keyの誤入力には回数制限を設けない。これは160 bitの乱数であり、利用者が選ぶ短いPINとは区別する。ただし、recovery中でもI/O・metadata・OOM等の障害は無制限に再試行せず停止する。

recovery解錠後は新PINを2回入力する。slot 0が残っていればslot 1を保ったままslot 0を消し、slot 0へ新PINを追加する。slot 0が無ければその状態から追加する。完了まで通常の起動へ進めない。この間に電源が切れてslot 0が無ければ、次回は`ready`かつrecoveryだけが残った状態としてrecovery入力から始める。slot 1を消してPINを変更する実装は認めない。volume keyはこの操作では交換しない。

[NIST SP 800-63B-4 §3.2.10](https://pages.nist.gov/800-63-4/sp800-63b/authenticators/#s-5-2-10)を参考にした案Aとして、10回後のPIN slot無効化と復旧経路を採用する。SDを抜かれた場合、RAM counterはoffline総当たりを制限できない。電源の入れ直しで回数が戻ること、弱いPINは警告だけで許容することを、利用者が受け入れたリスクとして明記する。headerの複製・復元やrollbackへの対策、NIST全体への適合を達成したとは主張しない。

## progress・mount・health

解錠、format、mkfs、partition拡張、同期では、開始前に処理と中断可否を示し、実行中は進捗を表示する。割合を出せない処理では経過時間を更新する。初期化中は`If power is lost, initialization will restart on the next boot.`と表示する。ただし、headerを認識できない破損時は前述の(d)で止まる。通常の解錠待ちと、書込み処理中に電源を切ってよいかを混同しない。約2秒を想定したArgon2idも実測で上限時間と扱わない。

mapperのnodeはlibdevmapperが作る経路を使う。mdevはS10なのでS02の前提にしない。healthでは`/data`が`/dev/mapper/msd-data`上のBtrfsであることを検査する。`/dev/dm-N`等の表記差はdeviceの同一性で確認し、無関係なBtrfs mountを受け入れない。tryboot時の確定はこの検査と既存のready条件を満たした後に限る。

LUKS2 header、keyslot、Btrfsのmetadata・transaction・log replayを含め、書込みは[台帳](write-policy.md)に登録する。解錠しただけで永続書込み0になったとは仮定しない。

## PRの分割と受入条件

| PR | 範囲 | 必須の確認 |
|---|---|---|
| A | この設計、旧決定の置換、書込み台帳、索引だけ | 文書検査。実装・build・QEMU成功と扱わない |
| B | C helper、libcryptsetup連携、host test | 正常設定、PINの長さと全ASCII範囲・空白・mask、弱PIN警告、2回不一致、空Enter・取消し・EOF、recovery照合・skip再確認、各slotとAPIの成功値、10回境界、error分類、削除失敗、PIN再設定中断、秘密の非出力を検査 |
| C | 512 MiB以上のzero image、S02、fstab、初期化限定grow、health、serial harness、CI | (a)〜(d)、先頭はzeroで後ろにdataがあるp7を初期化しないこと、全体zero確認のprogress・読取り失敗時停止・通常のLUKS2起動での全体確認省略、gate失敗前の無書込み、失敗時S02停止、各初期化境界の中断、recoveryのみの再起動、実容量とsparse性、mount同一性、healthを検査。ext4前提のimage検査・command在庫を更新 |
| 以後 | benchmark追従 | fs-compare-v2、旧fs-compare、write-inventory、s17系、S3、boottime、noexec、watchdog・panic・更新/署名probe等を個別に追従し、比較条件と証拠を更新 |

PR Bはhost上で検査可能な単位を扱い、製品起動の接続はPR Cまで完了扱いにしない。ext4/e2fsprogsの製品経路を置換しても、内側のext4を比較するbenchmarkのtoolsや過去の証拠を一括削除しない。

### QEMUの範囲

製品にPINを飛ばす経路を作らない。harnessがserial `ttyAMA1`を双方向に接続し、試験ごとのPINを通常の画面へ入力する。製品にcmdline・fileでPINを渡す仕組みを入れない。再起動する試験では起動のたびに入力する。guestはechoを止め、harnessも送信した秘密をlogへ記録しない。初回設定のrecovery key表示も、harnessが読む場合は証拠logの保存前に秘密部分を除外する。

既存のboot testはready/login待ち、S3のserialはfile出力だけなので追従が必要である。GPIO6 smokeはPIN解錠後のreadyを待ってから動かす。QEMUで確認するのは順序、失敗時停止、入力の流れまでであり、cipherやArgon2idの実機性能を決めない。

外側の`/data`がLUKS2+Btrfsになるため、fs-compare-v2等の以前の結果を同条件と扱わない。fs-compare-v2の試験diskはp7上の`test.img`をloop接続したものであり、内側のFSだけが同じでもbacking FSは異なる。write-inventoryのext4/JBD2指標、s17のp7先頭への故障注入とdebugfs抽出等は別PRの残件である。

### 実機と後続設計の残件

実機は無い。LCDでの英語・mask・progress、keyboardの全ASCIIと空白入力、entropyの品質・待ち時間、AES-XTS対Adiantum、Argon2idの実時間・64 MiB上限とOOM、実SDのFTL・耐電断性、DUPと圧縮の容量・速度、Btrfsの解錠後・idle・shutdownの書込み、firmware trybootとhealthは未確認である。

初回header・slot・mkfs・同期・ready更新、10回後のslot削除、PIN再設定の各境界で実電源断を確認する。QEMUのprocess停止でその保証を代用しない。volume keyの再暗号化、既存SDからの移行、後日の容量拡張、認証付き暗号やrollback対策は初期実装に含めない。
