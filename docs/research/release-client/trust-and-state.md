# 信頼・時刻・A/B状態と復旧の設計

[自己更新の設計](README.md) / [実装の比較](implementations.md) / [配信と取得](transport.md) / [権限設計](../security/privileges.md)

## 何を守るか

公開network、CDN、Release候補、download cacheは未信頼とします。正規の古い応答の再送、metadataの混在、署名者の誤配布、clock後退、download処理の侵害、同時更新、電源断を扱います。root権限の完全侵害や、microSD全体を置換できる物理攻撃まで、TUFや通常fileの番号で防げるとは扱いません。ハードウェアの信頼起点・secure boot・耐改ざんcounterは本機で確認できていません。

TUFの検証順とroot移行は[固定した仕様](https://github.com/theupdateframework/specification/blob/e2bc7d83d0740aaae8dd7133dd4f237ce3d86b16/tuf-spec.md)と既存clientへ委ねます。ここではMSD/Linuxが追加で負う責務を定めます。以下のpath・field・状態は設計案で、現行manifestや製品設定へ追加したものではありません。

## 初回の信頼と鍵更新

初期imageへ、検証済みのroot bytes、機種・channel policy、metadata配布先を組み込みます。最初にnetworkから拾ったrootを、その場で信頼する方式にはしません。現在の`/etc`は可変lowerとtmpfsのoverlayなので、単に公開鍵を`/etc`へ置くだけでは不変の信頼起点になりません。信頼するbytesをread-only rootfsの専用pathへ置き、一般ユーザーやdownload処理が隠蔽・差替えできないmount・所有者・権限を設計します。

ただしread-only rootfsも、最初のSD imageが正しいと認証する手段を代替しません。[image署名の未実装範囲](release-security.md)と初回導入時の検証を先に整えます。物理置換を含む保証がないことを、利用者へ明示します。

rootはofflineで保管する鍵とthresholdを検討し、targets・snapshot・timestampの鍵を役割別に分離します。2-of-3等の値は候補で、maintainer数・独立した保管場所・復旧能力を確認せずに必須にしません。同じ端末の同じSecretへ複数鍵を置くだけでは独立性を得られません。

更新時は既知のrootから連続したrootを検証し、旧・新thresholdを満たして移行します。payloadのEd25519鍵をTUF rootと別に保つ場合は、その更新・失効・writerへの伝達も必要です。TUF rootだけ更新して既存`msd-update`の公開鍵を放置する設計にはしません。鍵紛失・失効・署名不足・長期offlineからの移行を、正常時と同じfixtureで試します。

全ての信頼鍵を失った場合、新しい鍵を無認証downloadして回復しません。既に信頼する別の回復鍵を設ける案と、物理操作による検証済みSD再導入を比較します。後者にはdata消去・退避・復旧費用があり、前者には別鍵の長期管理が増えます。

## 版とschemaを分ける

| 値 | 提案する責務 | 避ける扱い |
|---|---|---|
| schema版 | updaterがfield・署名対象・状態を理解できるかを示す | 未知schemaを旧形式として解釈する |
| board・architecture | CM0/CardputerZero用の許可対象を認証済みmetadataから制限する | file名やRelease説明だけで判定する |
| channel・公開SemVer | 利用者向けの互換性と配信系列を表す | 文字列順、tagの先頭`v`、build metadataをanti-rollback番号にする |
| 内部更新番号 | 古いimageのnetwork再投入を拒否する案 | 公開SemVerとは分離済み（内部番号はtag commitのcommit時刻。対応表は[Release対応表](../../releases/README.md)）。現行整数parserへSemVer文字列を渡さない |
| role別metadata版 | TUFの信頼更新と世代混在・rollback検出に使う | OSのSemVerや内部番号と同一にする |
| 最低updater版 | parser、鍵、永続stateの互換性を要求する | 読めない更新を先にinstallしてから旧slotが壊れることを知る |
| payloadの名前・length・hash | 選んだbytesを固定し、TUF targetまたは認証済みdescriptorへ結び付ける | 未署名の別fieldで書込み先やhashを上書きする |

timestampの再署名だけでOSの内部番号を増やす必要はありません。SemVerのbuild metadata違いはprecedenceを変えないので、同じ公開版の再buildをどこまで許すかも別の契約です。schema確定時には重複key、数値範囲、空値、未知critical field、文字コード、署名対象bytesを定義し、別parser間の不一致を拒否試験へ入れます。

## 時刻未確定・後退・長期offline

[回路の照合](../hardware/hardware-wiring-audit.md)では、U19はRX8130CE:B3、I2C1の`0x32`、BAT1はNC表記です。RTCの存在だけで、電池保持・正確さ・耐改ざん性を仮定しません。NTP、HTTPSのDate、署名済みの古いmetadataだけでも、攻撃者が遅延・再送できる条件で現在時刻を自動的に証明しません。

既知の時刻下限を永続化し、clockの後退を検出する案を検討します。ただし下限だけでは、長いoffline期間中のfreezeを検出できません。誤って未来時刻を受け入れると全metadataやTLSが使えなくなるため、異常な前進も通知・復旧対象とし、信頼する時刻源と初回設定を決めます。TLSの時刻検証にも同じbootstrap問題があります。

| 状態 | 推奨する動作 | 背反 |
|---|---|---|
| 信頼できる時刻が未確定 | network更新を止め、稼働OSは維持する。認可された時刻設定・復旧経路を案内する | 初回の自動更新ができず、操作が必要になる |
| 時計が保存した下限より後退 | 更新を拒否し、原因と復旧操作を通知する | RTC故障・電池切れでも更新が止まる |
| timestamp/targetsが期限切れ | 新たな導入を止め、root更新等は仕様の順で検査する。期限を黙って無効化しない | 長期offlineから戻った端末はpublisherの再署名や復旧を要する |
| offlineのまま起動 | 既に確定済みのOSを継続する。metadata失効を起動不能に結び付けない | 最新の失効情報を受信できず、旧OSのriskが残る |

「期限切れなので永久に起動禁止」と「期限切れでも更新を受理」の二択にはしません。稼働継続と新規導入の認可を分け、例外が必要なら物理操作・利用者認可・別の回復手段を設計します。

## 永続状態とA/B transaction

TUFの最高受理metadata版、回転後のroot、時刻の下限、OSの導入状態を区別して保存します。libraryの一時directoryやslot内だけに置くと、再起動・A/B復帰で信頼が巻き戻るため不十分です。共有`/data`の専用領域へ、owner・mode・quota・schema・同期・復旧規則を設ける案を比較します。全てを一般ユーザー可変の設定へ混ぜません。

| 段階 | 永続化と不変条件 | 障害時の試験 |
|---|---|---|
| metadata受理 | root履歴とrole別の到達版をclientの契約に沿って保存する。OS成功とは別 | rename前後、file/親directory同期の前後、容量不足・破損・同時起動 |
| 候補認可・取得完了 | board、OS版、payload hash/lengthとtransactionを対応付ける | 同名fileの差替え、FD受渡し後の変更、再取得・resumeの混在 |
| 非稼働slotへの導入 | 書込み中は試行可能にせず、完了後の読み戻し・同期後にpreparedとする | boot/rootfsの片方だけ完了、SDの書込み破棄、active slot誤指定 |
| tryboot準備 | 完成した候補だけを試行対象にし、旧正常slotとtransactionを保持する | selector更新中の電源断、既存tryboot中の再導入、同時実行 |
| health・commit | 機種・更新内容に必要な条件を期限付きで確認し、default slotと確定stateを整合させる | health遅延・失敗、commit途中の電源断、再boot時の重複処理 |
| 復旧 | 失敗した更新から、保持済みの正常slotへ戻す。信頼stateは低い版へ戻さない | 旧updaterが新stateを読めない場合、data migration後の旧OS、同じ候補の再試行 |

networkから新規取得する古いimageの拒否と、保持済み正常slotへの障害復帰は別に認可します。高いOS番号の候補を見ただけで正常slotを起動禁止にせず、かといって失敗後にTUF metadataのfloorを消しません。受理済み番号、導入済み番号、確定済み番号、許可する復旧slotを分け、同じ番号の再試行を同じdigestに限るかも契約に含めます。これらの採番規則は確認待ちです。

共有`/data`はOSを戻しても元へ戻りません。旧・新OSの両方が読める段階的schema変更、copy-on-writeの世代管理、退避と容量予算を比較し、復旧時に危険なdataを旧OSへ黙って渡しません。新rootやstate formatを旧slotが読めない場合も、旧slotの起動は許しつつ更新機能を止める等の互換契約が必要です。

## 権限を狭めても残る責務

download、metadata検証、policy、writerを別の責務にし、networkを扱うプロセスへblock deviceやboot selectorへの書込みを許しません。検証器は信頼の一部であり、一般ユーザー権限で動かせば侵害されても安全という意味ではありません。[権限設計](../security/privileges.md)の実行者と拒否試験に対応付けます。

writerは機種、固定したpartition map、現在slot、tryboot、署名、hash/length、版と容量を再確認し、任意path・任意offset・任意commandを受け取らない小さなAPIにします。IPCではpeerを認可し、transactionとdigestを結び、同時実行をlockします。pathで受け取る場合のsymlink/TOCTOUを避けるだけでなく、FDでも受渡し後に元の書き手が内容を変更できない所有権・封印・再検証が必要です。

現行`msd-update`は展開・検証・書込みが一つの処理です。TUFで取得したfileをそのまま呼び出すだけでは、この境界は完成しません。payload署名とTUFの二重検証を残す案は鍵移行も増やし、TUF検証器の判定だけをwriterが信じる案は検証器侵害時の境界が広がります。どちらも明示して実験し、独自の信頼判定をrootへ肥大化させない設計を選びます。

現行`S99msd-health`はSquashFS root、ext4 `/data`、`/run/msd-ready`等の最小条件後に自動commitし、LCD・keyboard・通信等の確認を待ちません。networkだけを必須healthにすると、APや外部回線の障害で正常OSまで失敗扱いになる背反があります。端末内の必須機能、更新ごとの要求、外部到達性の診断を分け、commit条件とwatchdog・復帰期限を実機で確かめます。

## 実装前に固定する拒否試験

改変、別鍵、threshold不足、重複署名、rootの飛越し、期限切れ、role別rollback、snapshot/targetsの混在、委任外target、未知schema、機種/channel違い、低いOS番号、容量超過・path逸脱を試します。正しい入力を受理する対照と一つずつ組み合わせます。

さらに、時刻未設定・後退・異常な前進、長期offline、404/429/redirect loop、途中切断、同じ版の別bytes、metadata保存やslot更新中の電源断、commit途中の停止、壊れたstate、旧slotからの起動、data migrationを試します。hostのfixture、QEMUのstate試験、実SD/実機の電源断は別の証拠として残し、一つの合格で他を代用しません。
