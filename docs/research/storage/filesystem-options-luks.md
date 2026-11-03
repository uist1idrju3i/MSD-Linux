# LUKS2とdm-cryptの設定

[保存領域へ戻る](README.md) / [option調査の索引](filesystem-options.md) / [dm-integrity](filesystem-options-dm-integrity.md) / [調査の索引](../../../RESEARCH.md)

## 範囲と出典

固定版cryptsetupは2.8.7、調査時点の最新版は2.8.8です。kernelはRaspberry Pi Linux 6.18.59とmainline 7.4-rc1を比較します。出典は[cryptsetup v2.8.7 `luksFormat`](https://gitlab.com/cryptsetup/cryptsetup/-/blob/v2.8.7/man/cryptsetup-luksFormat.8.adoc)、[`open`](https://gitlab.com/cryptsetup/cryptsetup/-/blob/v2.8.7/man/cryptsetup-open.8.adoc)、[`refresh`](https://gitlab.com/cryptsetup/cryptsetup/-/blob/v2.8.7/man/cryptsetup-refresh.8.adoc)、[共有option](https://gitlab.com/cryptsetup/cryptsetup/-/blob/v2.8.7/man/common_options.adoc)、[v2.8.8 `luksFormat`](https://gitlab.com/cryptsetup/cryptsetup/-/blob/v2.8.8/man/cryptsetup-luksFormat.8.adoc)、[`open`](https://gitlab.com/cryptsetup/cryptsetup/-/blob/v2.8.8/man/cryptsetup-open.8.adoc)、[`refresh`](https://gitlab.com/cryptsetup/cryptsetup/-/blob/v2.8.8/man/cryptsetup-refresh.8.adoc)、[v2.8.8共有option](https://gitlab.com/cryptsetup/cryptsetup/-/blob/v2.8.8/man/common_options.adoc)、[固定kernel dm-crypt documentation](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/Documentation/admin-guide/device-mapper/dm-crypt.rst)、[mainline v7.4-rc1 dm-crypt documentation](https://github.com/torvalds/linux/blob/v7.4-rc1/Documentation/admin-guide/device-mapper/dm-crypt.rst)です。

製品のdata filesystemはext4で、defconfigにcryptsetup package選択は見当たりません。最終kernel `.config`を生成していないため、dm-crypt kernel featureの搭載状態は未確認です。LUKS2や暗号設定のbuild、QEMU、実機試験はしていません。

## /data鍵のライフサイクル

決定済み方針は、初回boot時にdeviceごとのvolume keyを生成して`/data`を暗号化し、PIN/password設定時にvolume key自体をrotationすることです。鍵生成・format・rotation・recoveryは利用者が開始し、長時間処理には進捗を表示します。idle中のtimerやbackground jobで再暗号化、header更新、discardを行いません。乱数の準備完了条件、PIN設定前の認証・recovery経路、rotation中断後のatomic recovery、header backup保管場所は未確認であり、実装前に定めます。plaintext volume keyを永続領域へ残さない前提でkey sourceとkeyslot設計を比較します。

## `luksFormat`とLUKS2 persistent metadata

最新版との差分列は、option tokenの追加・削除を固定版と比較する。`同`はoption token差分なしを示し、defaultの全文比較は未確認。

| option | 意味 | 既定値 | 固定版で使えるか | 最新版の変化 | MSD/Linuxでの扱い | 理由 |
| --- | --- | --- | --- | --- | --- | --- |
| `--type luks2` | LUKS metadata format | luks2 | 可 | 同 | 実験で比べる | LUKS2 metadataとkeyslot/token構造を維持する方法、header backupからの復旧、cryptsetup/kernel相互運用を確認してから採用する。 |
| `--cipher` | data cipher | `aes-xts-plain64` | 可 | 同 | 実験で比べる | CardputerZeroで暗号化read/write throughputとCPU時間を測り、AES accelerationの有無と要求性能を満たすcipherを選ぶ。 |
| `--key-size` | cipher key size | cipher依存 | 可 | 同 | 実験で比べる | 選択cipherの標準key sizeと速度を組み合わせて評価し、仕様上のsecurity levelを下げずにthroughput要件を満たす値だけ候補にする。 |
| `--hash` | PBKDF2 hash | sha256 | 可 | 同 | 実験で比べる | PBKDF2を選ぶ場合に、cryptsetupが許すdigest、互換性、unlock時間を比較する。Argon2系では別途algorithm/parameterを選ぶ。 |
| `--pbkdf` | password KDF | LUKS2は`argon2id` | 可 | 同 | 実験で比べる | unlock latency、peak RAM、CPU時間を実機相当で測り、boot-time budget内でoffline guessing costを高められる設定を選ぶ。 |
| `--pbkdf-memory` | Argon2 memory | cryptsetup既定 | 可 | 同 | 実験で比べる | early bootで利用可能なRAM量とunlock時間を測り、kernel/initramfsのmemory余裕を残せる範囲で設定する。 |
| `--pbkdf-parallel` | KDF parallelism | cryptsetup既定 | 可 | 同 | 実験で比べる | target core数、peak RAM、unlock時間を測り、boot中の他処理を妨げずKDF時間を短縮できる場合に変える。 |
| `--iter-time` | KDF target time | 2000 ms | 可 | 同 | 実験で比べる | 複数回unlockの時間分布と起動budgetを測り、遅い個体でも利用者が許容する時間内に収まる値を選ぶ。 |
| `--sector-size` | encryption sector size | 512 byte | 可 | 同 | 実験で比べる | underlying logical block size、filesystem alignment、暗号化read/write throughputを測り、全toolとkernelで互換な値にする。 |
| `--integrity` | dm-integrityを使うalgorithm | 無効 | 可 | 同 | 実験で比べる | algorithmごとにtag容量、read/write throughput、CPU時間、破損検出とauthenticationの違いを比較する。詳細は[dm-integrity](filesystem-options-dm-integrity.md)に記す。 |
| `--integrity-no-journal` | integrity journalを無効化 | journal使用 | 可 | 同 | 実験で比べる | crash時tag不整合のriskを含めて測る。 |
| `--integrity-no-wipe` | integrity format時のdata wipeを抑止 | wipeする | 可 | 同 | 除外 | 未初期化tagを使える状態にしない。 |
| `--label` / `--uuid` | LUKS header識別子 | 自動UUID / labelなし | 可 | 同 | 既定のまま | UUIDはformatごとに生成し、複製volumeの衝突を避ける。現行`/data`の識別はpartition label `data`で行い、LUKS layerを採用するまでは追加labelを設けない。 |
| `--header` | detached header file/device | data device内 | 可 | 同 | 除外 | headerの保管・復旧・一貫性設計がない。 |
| `--offset` / `--align-payload` | encrypted data領域の位置調整 | tool計算 | 可 | 同 | 既定のまま | raw layoutの互換性を変えない。 |
| `--key-file` | key input file | terminal prompt | 可 | 同 | 実験で比べる | 初回bootでdevice固有volume keyを生成する手段、PIN/password設定時にvolume keyをrotationする手順、暗号化保管と中断後のrecoveryを比較する。plaintext keyを永続領域へ書かない。 |
| `--keyfile-size` | keyfileから読むbyte数 | file依存 | 可 | 同 | 既定のまま | key-file形式を採用するなら固定長とencodingを明記し、読み込み値が想定どおりか検査する。現行はkey-file方式を使わない。 |
| `--key-slot` | keyslot選択 | 空slotを選択 | 可 | 同 | 既定のまま | passphrase/key rotation、recovery key、slot revoke手順を設計した場合にslot割当を固定する。 |
| `--token-id` | tokenからkeyを取得 | tokenなし | 可 | 同 | 除外 | PIN/passwordでkeyslotを管理する方針であり、token providerがない。PIN設定前のrecovery要件がtokenを必要とする場合は、providerの信頼・更新・失効を先に設計する。 |
| `--disable-locks` | lockを使わない | lock有効 | 可 | 同 | 除外 | 同時実行制御を弱める。 |
| `--batch-mode` | promptを省略 | 無効 | 可 | 同 | 既定のまま | image build/initで対話promptを使わないprovisioning pathを採用する場合にだけ有効化し、失敗時の明示的なreturn codeとsecret inputを試験する。 |
| `--verify-passphrase` | passphraseを再入力 | 無効 | 可 | 同 | 既定のまま | 手動formatでは入力誤りを減らせるが、自動provisioningでは確認入力を供給できない。どちらの初期化経路を採用するかで選ぶ。 |
| `--force-password` | 短いpassword警告を無視 | 無効 | 可 | 同 | 除外 | 弱いpassphraseを許容しない。 |
| `--use-random` / `--use-urandom` | key generation source | tool/kernel既定 | 可 | 同 | 既定のまま | device固有key生成前にentropy readinessを確認し、初回bootの待ち時間とkey生成動作を測る。低entropy状態でkeyを生成しない。 |

## `open`、`refresh`とdm-crypt target flags

| option | 意味 | 既定値 | 固定版で使えるか | 最新版の変化 | MSD/Linuxでの扱い | 理由 |
| --- | --- | --- | --- | --- | --- | --- |
| `--readonly` | mappingをread-onlyでopen | read/write | 可 | 同 | 実験で比べる | read-only modeと更新処理の整合性を測る。 |
| `--allow-discards` / `allow_discards` | discardを暗号mappingへ通す | 省略時無効 | 可 | 同 | 実験で比べる | discardはfree-block patternをobserverへ漏らす一方、SD FTLへ空き領域を通知できる。発行時機、write量、情報露出を比較する。 |
| `--persistent` | 許可されたmapping flagをLUKS headerに保存する | 無効 | 可 | 同 | 既定のまま | `common_options.adoc`は保存可能なflagを限定する。header移行後もpolicyが残るため、明示的な永続化要件がある場合だけ使う。 |
| `--perf-same_cpu_crypt` / `same_cpu_crypt` | submit CPUでcryptoを実行する | 省略時無効 | 可 | 同 | 実験で比べる | CPU locality、write latency、未操作時writeを測る。 |
| `--perf-submit_from_crypt_cpus` / `submit_from_crypt_cpus` | crypto workerからwriteをsubmitし、別threadへのoffloadを止める | 省略時無効 | 可 | 同 | 実験で比べる | worker scheduling、SD queueの時機、未操作時writeを測る。 |
| `--perf-no_read_workqueue` / `no_read_workqueue` | read requestのinternal workqueueを迂回する | 省略時無効 | 可 | 同 | 実験で比べる | read latencyとCPU負荷を比較する。 |
| `--perf-no_write_workqueue` / `no_write_workqueue` | write requestのinternal workqueueを迂回する | 省略時無効 | 可 | 同 | 実験で比べる | write completion、CPU負荷、未操作時writeをtraceする。 |
| `--perf-high_priority` / `high_priority` | dm-crypt worker/threadを高優先度にする | 省略時無効 | 可 | 同 | 実験で比べる | foreground latencyとCPU starvationを測り、有効な場合だけ選ぶ。 |
| `--sector-size` | target sector size | 512 byte | 可 | 同 | 実験で比べる | cipher/mapping alignmentを測る。 |
| `--iv-large-sectors` | large sector IV generation | 無効 | 可 | 同 | 実験で比べる | sector sizeと組み合わせて互換性を検証。 |
| `--key-file` / `--key-slot` | key sourceとslot | prompt / default slot | 可 | 同 | 実験で比べる | first-boot keyslot provisioningとPIN/password設定時のvolume-key rotationを実装し、rotation中断・reboot後のunlockとrecoveryを試験する。 |
| `--header` | detached headerを指定 | embedded header | 可 | 同 | 除外 | header recovery planがない。 |
| `--offset` / `--size` | mapping範囲を変更 | header値 | 可 | 同 | 既定のまま | raw mapping layoutを変えない。 |
| `--test-passphrase` | mappingを作らずkey検査 | open時だけ | 可 | 同 | 除外 | runtime mount optionではない。 |
| `--refresh` / `refresh` | active mapping flagを更新 | 現在値を維持 | 可 | 同 | 実験で比べる | active mapping変更後のlatency/throughputとreboot後のmapping policyが一致するかを確認し、運用上のreconfigure手順が必要な場合だけ使う。 |

kernel dm-cryptのtarget flagsは`allow_discards`、`same_cpu_crypt`、`high_priority`、`submit_from_crypt_cpus`、`no_read_workqueue`、`no_write_workqueue`、`sector_size`、`iv_large_sectors`、`integrity`、`integrity_key_size`です。cryptsetupの`--allow-discards`は`allow_discards`、`--perf-*`は対応するperformance flagへ写像されます。optional discard/performance flagはtarget parserで指定時だけ有効になり、省略時は無効です。

cryptsetup v2.8.7/2.8.8の`common_options.adoc`は、`--persistent`で保存できるflagを`--allow-discards`、`--perf-same_cpu_crypt`、`--perf-submit_from_crypt_cpus`、`--perf-no_read_workqueue`、`--perf-no_write_workqueue`、`--integrity-no-journal`に限定します。`--perf-high_priority`は対象外です。

固定版と最新版の[dm-crypt.c parser](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/drivers/md/dm-crypt.c)、[mainline parser](https://github.com/torvalds/linux/blob/v7.4-rc1/drivers/md/dm-crypt.c)は、指定されたoptionだけflagを設定します。両sourceに`submit_from_queue_ids`はなく、`submit_from_crypt_cpus`が近い機能です。

## keyslot・integrity・compatibility option

| option | 意味 | 既定値 | 固定版で使えるか | 最新版の変化 | MSD/Linuxでの扱い | 理由 |
| --- | --- | --- | --- | --- | --- | --- |
| `--keyslot-cipher` | keyslot暗号を指定 | 未確認（資料でdefault未整理） | 可 | 同 | 実験で比べる | keyslot unlock時間、CPU負荷、kernel/cryptsetup相互運用をCardputerZeroで測り、data cipherとは別に必要な場合だけ設定する。 |
| `--keyslot-key-size` | keyslot encryption key size | 未確認（資料でdefault未整理） | 可 | 同 | 実験で比べる | metadata容量、unlock時間、security requirementを比較し、暗号方式の標準sizeを下げずにboot budgetを満たす値を選ぶ。 |
| `--luks2-metadata-size` | LUKS2 metadata area size | 未確認（資料でdefault未整理） | 可 | 同 | 実験で比べる | keyslot/token数、header backup容量、開閉時間を測り、recovery keyやtoken追加の運用容量を見積もって決める。 |
| `--luks2-keyslots-size` | keyslot area size | 未確認（資料でdefault未整理） | 可 | 同 | 実験で比べる | 許容keyslot数とPBKDF metadata、data offsetへの影響を確認し、SD上の固定layout・`msd-data-grow`と両立する値を選ぶ。 |
| `--integrity-inline` | integrity tagをinline layoutに置く | 未確認（資料でdefault未整理） | 可 | 同 | 実験で比べる | tag overhead、sector alignment、random/sequential I/O throughput、dm-integrity recoveryを通常layoutと比較する。 |
| `--integrity-key-size` | integrity key size | 未確認（資料でdefault未整理） | 可 | 同 | 実験で比べる | algorithmのkey requirement、CPU時間、tag検証結果を比較する。暗号化とintegrity detectionを同一視しない。 |
| `--integrity-legacy-padding` | legacy integrity metadata paddingを使う | 未確認（資料でdefault未整理） | 可 | 同 | 除外 | 旧formatとの互換要件がなく、tag layoutを新規設計で選ぶ。existing headerを扱うmigration試験で互換性が必要な場合だけ検討する。 |
| `--pbkdf-force-iterations` | PBKDF2 iteration数を強制 | 未確認（資料でdefault未整理） | 可 | 同 | 実験で比べる | unlock latencyの分布、boot budget、offline guessing costを測り、Argon2系との条件を揃えて決める。 |
| `--serialize-memory-hard-pbkdf` | memory-hard KDF処理を直列化 | 未確認（資料でdefault未整理） | 可 | 同 | 実験で比べる | peak RAMと同時unlock時間を測る。圧縮RAM上のlog/cacheを含めearly boot memory budgetを超えない場合だけ有効化する。 |
| `--keyfile-offset` | keyfile内の開始offset | 未確認（資料でdefault未整理） | 可 | 同 | 既定のまま | first-boot provisioningで固定keyfile formatを使う場合にだけ、secret delivery、offset、file permission、recoveryを明示する。 |
| `--key-description` | kernel keyring内key description | 未確認（資料でdefault未整理） | 可 | 同 | 除外 | 現行imageでkeyringによるkey delivery/rotation/revocation手順がない。 |
| `--volume-key-file` / `--volume-key-keyring` / `--link-vk-to-keyring` | volume keyをfileまたはkernel keyringへ渡しlinkする | 未確認 | 可 | 同 | 除外 | plaintext volume keyをfile/keyringへ常置しない。LUKS2 keyslotで保護し、PIN/password設定時にvolume keyをrotationする。暗号化recoveryは別途設計する。 |
| `--token-only` / `--token-type` / `--disable-external-tokens` / `--external-tokens-path` | token-only unlock、token type/plugin path、external tokenの許可を制御 | 未確認 | 可 | 同 | 除外 | PIN/password keyslot方針にtoken providerはない。providerの信頼・更新・失効設計がない状態でpluginを読み込まない。 |
| `--disable-keyring` | kernel keyring integrationを無効化 | 未確認（資料でdefault未整理） | 可 | 同 | 除外 | keyring pathを採用する場合の機能を外すoptionで、現行のsecret delivery/recovery設計がない。 |
| `--hw-opal` / `--hw-opal-only` | OPAL self-encrypting driveを使う/限定する | 未確認 | 可 | 同 | 除外 | SDのOPAL supportは未確認。device lock/recovery設計もないためsoftware LUKS2の代替にしない。 |
| `--tcrypt-backup` / `--tcrypt-hidden` / `--tcrypt-system` / `--veracrypt` / `--veracrypt-pim` / `--veracrypt-query-pim` / `--disable-veracrypt` | TrueCrypt/VeraCrypt互換動作 | 未確認 | 可 | 同 | 除外 | 既存containerのimport要件がなく、新規`/data`はLUKS2 keyslot方針とする。 |
| `--disable-blkid` / `--device-size` / `--shared` / `--unbound` / `--skip` / `--timeout` / `--tries` | signature scan、mapping範囲、keyslot、prompt制御 | 未確認 | 可 | 同 | 既定のまま | unlock対象・失敗動作を変える。`data` label、grow後size、keyslot復旧とprompt動作を測り、必要な項目だけ指定する。 |
| `--debug` / `--progress-frequency` / `--progress-json` | debug・progress表示形式/頻度 | 未確認 | 可 | 同 | 既定のまま | format・integrity初期化・key rotationのprogressを利用者に表示する。idle logは圧縮RAMへ送り、diskへ書かない。 |
| `--sector-size` / `sector_size` | encryption/dm-crypt sector size | 未確認（資料でdefault未整理） | 可 | 同 | 実験で比べる | filesystem block alignment、device logical block、dm-integrity tag layout、crypt throughputとの互換値を確認する。 |
| `--iv-large-sectors` / `iv_large_sectors` | large-sector IV numbering | 未確認（資料でdefault未整理） | 可 | 同 | 実験で比べる | sector-sizeと組み合わせたmapping compatibility、known-answer test、reopen後のdata読み出しを確認して設定する。 |
| `integrity` / `integrity_key_size` | dm-crypt authenticated/integrity modeとkey size | 未確認（資料でdefault未整理） | 可 | 同 | 実験で比べる | tag overhead、authentication failure時のI/O error、journal modeのwrite cost、鍵保管をdm-integrity表に沿って評価する。 |

## 最新版との差分とoption件数

cryptsetupの最新版tagはv2.8.8です。v2.8.7とv2.8.8の`common_options.adoc`ではoption名116件が一致し、追加・削除は検出していません。command-specific LUKS2 default・意味の全文差分は未確認です。LUKS2 `--integrity`と関連optionの詳細は[dm-integrity](filesystem-options-dm-integrity.md)にまとめます。

上表はformat/open/refreshの利用候補を示すもので、共有man pageにある全optionを列挙していません。help、version、debug、output-format、LUKS1 compatibility、token administration、erase/repair/re-encryption等のsource tokenもcoverage照合の対象として残し、未掲載のoptionを単に無視しません。
