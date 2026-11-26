# data-unlock helperの接続契約とhost test

[現行の設計](data-unlock.md) / [書き込みの台帳](write-policy.md)

## 実装の境界

PR Bは[msd-data-unlock](../../package/msd-data-unlock/)のC helper、local package、defconfigとhost testを追加する。設計の仕様は変えず、起動への接続はしない。S02、image、fstab、grow、mkfs、mount、health、early-io gateの処理はPR Cのままである。helperがtargetに存在しても、製品が暗号化済み、PIN必須の起動になったとは扱わない。

`unlock.c`が状態遷移、`terminal.c`が固定端末の入力・表示、`crypt-backend.c`がlibcryptsetupを扱う。fake backendと本物のbackendが同じinterfaceを使う。暗号処理はlibraryへ委任し、乱数はkernelの`getrandom`から20 bytesを得る。乱数源の不備を時刻や疑似乱数で代用しない。

## CLIとPR Cの責務

```text
msd-data-unlock prepare --device DEVICE --io product|qemu --control-fd FD
msd-data-unlock unlock --device DEVICE --io product|qemu
```

mapping名は`msd-data`、PINはslot 0、recoveryはslot 1だけである。秘密を引数、環境変数、fileから受け取るoptionは無い。`product`は入出力とも`/dev/tty1`を開き、keymapを適用した内蔵キーボードのconsole入力を使う。`qemu`は入出力とも`/dev/ttyAMA1`だけを開く。探索も端末の代用もしない。内蔵キーボードからの入力が届くこと、外部機器を含む実機での入力経路は未確認で、PR Cの接続・実機確認の残件である。

PR Cの呼出し元がearly-io gateを確かめ、p7を固定長`N`とlabelで分類する。`prepare`を許可してよいのは設計の(a)又は(c)だけである。helper単独はzero確認・partition判定を行わず、`prepare`は指定deviceをformatする破壊的操作である。起動から無条件に呼ばない。

`prepare`の`FD`は呼出し元から継承するAF_UNIX・SOCK_STREAMの双方向socketであり、PIN用のfdではない。次の2段階だけをやり取りする。予期しない応答や切断では失敗し、次の段階へ進まない。

| helperからの要求 | 呼出し元が終える処理 | 成功時の応答 |
|---|---|---|
| `grow\n` | 初期化のPIN2回とrecovery照合又はskip再確認が済んでいる。partitionをdisk末尾まで広げ、kernelへ反映する | `grown\n` |
| `filesystem\n` | pendingのformat、両slot追加とopenが済んでいる。所定のmkfs・mount・directory作成・同期を終える | `synced\n` |

応答を受けるまで秘密を同じprocessのRAM内に保つ。最初の応答前にはformatせず、2番目の応答前にはreadyを書かない。呼出し元は別の処理の成功を推測して応答せず、各段階のprogress・中断可否を表示する。socketのmessageに秘密を載せない。再起動後に以前のsocketを再利用する契約ではない。

`synced`以後に`prepare`が失敗した場合、呼出し元のS02は同じ起動中に再試行せず、exitせずに停止の待機へ入る。mountとmappingの解除は要求しない。mount中のmappingは使用中のため解除できない場合があるが、helperはその解除errorで元の失敗理由を上書きしない。

次の起動では既存の状態判定に従い、labelがpendingなら初期化を最初からやり直し、readyなら解錠する。header等を識別できなければformatせず停止する。READYの書込み後に同期が失敗した場合、失敗を返してもreadyが残り得るため、次回のlabelが必ずpendingであるとは扱わない。

`unlock`はreadyとslot構成を検査してから対話する。slot 0が無ければrecoveryへ進む。APIの非負値は成功として扱い、PIN認証APIの`-EPERM`だけを数える。passphraseの検証とmapperのactivateを分け、後者の権限errorを誤PINに数えない。検証で得るvolume keyはlockした作業領域に置き、activate後に消す。同じPINでArgon2を2回実行する方式ではない。metadataの検査、表示の失敗等が`-EPERM`でもPIN誤入力にはしない。10回後のslot 0消去前と消去後、PIN再設定前後にslot構成を検査する。想定外slotや最後のslotの消去は許さない。

helperが開いたmappingは、PIN再設定の中断を含む失敗時に解除を試みてから返す。既に存在するmappingを開けなかった場合、そのmappingは閉じない。解除に失敗しても、返す値は元の処理errorを保つ。初期化のslot検査はreadyの前に終え、readyの書込みと同期成功を最後の失敗可能な操作とする。その後のprogress終了・端末復元のerrorでは、完了した初期化を失敗へ戻さない。

成功時は終了値0、処理失敗時は1、CLIの不備は2である。S02の待機loopは実装しない。PR Cの呼出し元は非zero終了時にS02からexitせず待機し、後続initへ進ませない。製品LCDを開けない場合はconsole・kernel logへ停止通知だけを試み、対話をserialへ移さない。LCDには表示できない制約は残る。

## 入力と秘密の扱い

PINの長さと文字、blocklist、recoveryの規則は[正本](data-unlock.md#pinとrecovery-keyの入力)に従う。blocklistは本repoで管理する手書きの共通例であり、NISTの一覧や流出集合を称するものではない。弱いPINも警告後に受理する。

端末のechoとcanonical入力を止め、受理した1文字につき`*`を出す。単独のBS・DEL byteで直前の文字を消せる。過長や範囲外の行は改行まで読み捨て、短く切って認証しない。Ctrl-DはEOF、Ctrl-C・単独Escapeは中断とする。SIGINT・SIGTERM・SIGHUP・SIGQUIT・SIGTSTPでも失敗して端末設定を復元する。SIGKILLや電断では復元処理を実行できない。PIN待ちの期限は無い。端末への出力は非block fdと期限付きpollを使い、出力不能を無期限に待たない。

単独Escapeは後続byteを100 msだけ待って区別する。CSI・SS3のsequenceは最後まで読み捨て、矢印・Home・End・Delete等をPINへ入れたり、中断と扱ったりしない。Linux consoleのDelete sequenceは文字を削除せず無視する。出力には`OPOST|ONLCR`を設定し、改行をCRLFにする。

秘密の作業領域はpage単位で`mlock`し、`MADV_DONTDUMP`を設定する。失敗時は入力前に止める。core limitとdumpableを0にし、環境変数をclearする。認証後や終了時のbufferを`explicit_bzero`で消す。Argon2用の64 MiB全体をhelperの`mlockall`で固定する方式ではなく、libraryの内部bufferはlibcryptsetupに委ねる。

秘密をstdout・stderrへ出さず、libraryのlog callbackも抑止する。recovery keyの初回表示は意図した秘密の表示であり、選択した対話端末にだけ出す。QEMU harnessが端末出力を保存するなら、設計どおりkey表示を保存前に除外する必要がある。helper単独では外部のserial記録を防げない。

metadata検査・format・slot操作・解錠・ready書込み中は、公開の処理名と経過秒、中断不可を端末へ出す。`crypt_load`は読取り専用とは限らず、片方のheaderの損傷をもう片方から自動復旧して書き込む場合があるため、検査もprogressで囲む。進捗用threadの生成や出力に失敗しても認証失敗回数へまとめない。cipher等は正本の暫定値で、Argon2idのparallel threadsは1とし、memoryを64 MiB以内に制限する。metadata操作後にはdeviceのfsync成功も必要とする。

## 検査と残件

```sh
docker/msd-dev tests/msd-data-unlock/run.sh
```

fake backendはPINの範囲・境界、誤入力0〜10回、非負のAPI成功値、空Enterと取消し、固定slot、recovery照合とskip再確認、回数無制限のrecovery、PIN再設定の中断、各段階のI/O等の失敗、buffer消去を検査する。PTY試験は全印字可能ASCII、mask、過長・不正byte、EOF・中断signal、termios復元、実際の対話とsocketの順序、stdout・stderrへの非出力を検査する。

hostのlibcryptsetup headerを使い、同じbackendで通常fileにLUKS2 headerを作り、slot追加・削除・passphrase検証・ready・片側headerの自動復旧・未知label/slotの拒否を調べる。dmのactivateはしない。[開発image](../../docker/msd-dev.Dockerfile)に`libcryptsetup-dev`を含め、CIのhost runnerは`MSD_TEST_REQUIRE_CRYPTSETUP=1`を設定する。この場合はheader不在を失敗とする。個別の`run.sh`では既定で追加試験だけをskipできる。試験専用の`MSD_TEST_CRYPTSETUP_INCLUDE`でheader directoryを指定できる。製品helperはこれらの環境変数を読まない。[依存追加の確認範囲](../research/dependencies/data-unlock-host.md)も参照する。

target buildには製品のcryptsetup 2.8.9のstaging header・libraryを使う。full image build、mapperのactivate、S02以降の順序、LCD・内蔵キーボードの入出力、実機のArgon2時間、SDの電断はPR Bのhost testで確認済みとしない。hostのlibrary版が2.8.9と異なる場合も区別して報告する。
