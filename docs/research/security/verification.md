# 権限設計の段階導入と検証条件

[入口](README.md) / [原則](principles.md) / [処理別設計](privileges.md) / [通信設計](network.md)

## 導入順序と採用条件

以下は未実装部分の実施計画で、試験が通った一覧ではありません。製品機能・ログイン・復旧方式の判断を済ませてから対象を実装します。小さい対策も、実効性と復旧可能性を検証して採用します。

| 段階 | 成果物 | 次へ進む条件 |
|---|---|---|
| 1 信頼境界 | user/service/device表、可変設定と鍵・policyの正本、初回設定と復旧仕様 | 通常user・downloaderが管理設定やtrust anchorを変えられない設計。ログイン方式の要件確認 |
| 2 最小構成 | 不要listener・protocolの無効化、必要なmountとdevice mode、初期化の失敗伝播 | 必要な周辺機能が成功し、不要な操作は拒否。data・etcの準備失敗を成功扱いしない |
| 3 外部入力の分離 | 上流daemonのprivsepと専用user、最小helper/IPC、必要なprofile/filter | capability・FD・環境・IPCの認可を試験。自作より既存実装を優先し、必要な初期化を壊さない |
| 4 通信開始 | firewall、IPv4/IPv6、秘密の設定、DNS・時刻・HTTPSの起動順 | policy失敗・再起動・hotplugでも未制限で通信しない。正しい接続も壊さない |
| 5 更新・配布 | signed metadata、特権writerとの結合、鍵運用、A/B healthとの整合 | exact bytes、認可、rollback、電断・中断・競合・期限・鍵更新の試験と復旧手順 |
| 6 継続確認 | CIでの静的検査、image検査、QEMUと実機の記録、policy更新時の回帰 | 検証revisionと生成物hashを固定し、拒否試験・実機範囲・警告を追跡可能にする |

## 正の試験と負の試験

serviceが起動したこと、`aa-status`や`Seccomp: 2`等の値だけでは目的の制限が効く証拠になりません。実際に対象processから必要な操作が成功し、禁止した操作が拒否されることを確認します。

| 対象 | 成功させる操作 | 拒否・異常系と見るべき結果 |
|---|---|---|
| UID/GID/capability | 指定した専用userで必要なdeviceを使う | real/effective/saved ID、補助group、全capability set、子process・exec後を確認。UID 0の再取得、不要なfile・device・capability取得が失敗 |
| no_new_privs | 必要なexecと通常処理 | setuid/file capabilityで昇格できない。既に持つ権限やFDは別検査。AppArmorの意図したexec遷移も成立 |
| seccomp | 固定binary/libc/ABIで通常起動・処理・終了 | 禁止syscall、別ABI経路、fork/exec/thread後の漏れを試験。filterなしの対照では禁止操作が可能なことも確認 |
| Landlock | 許可pathと必要なTCP操作 | 禁止path、rename/link、truncate、必要に応じdevice ioctl、inherit/受領FDを試験。ABI不足・無効化時は必須serviceを開始しない。UDP/IP/DNS制限の代用品にしない |
| AppArmor | profileに付いたdaemonが通常処理 | 未読込・complain・不適切attachment・exec遷移・profileなし子process、data/etc経由の変更を試験。禁止file/device/socketを実操作してdenyを確認 |
| deviceとhotplug | LCD・入力・音声・sensor・IR等、必要なnodeを操作 | 別input、全I2C/GPIO、raw disk等を不要なuserが開けない。remove/add・node再作成でmodeが緩まない |
| firewall | 必要なDHCP/DNS/時刻/HTTPS、IPv6 ND/必要ICMP、切替 | 未許可受信・転送、出力制限が必要なserviceの外向き通信を拒否。起動途中・reload失敗・新interfaceにも穴がない |
| 更新入力とIPC | 正しい機種・署名・hash/lengthの更新がinactive slotへ書ける | 不正署名、過大入力・展開、symlink・特殊member・path差替え・処理中変更・FDの種類、別peer、未知message、重複要求、並行installを拒否 |
| 信頼する状態 | 正本の鍵・policy・versionを使い、正規の更新で変更 | 可変etc・環境・PATH/TMPDIR・state・deviceの差替えで認可を迂回できない。downgrade権限、壊れた状態、古いsigned metadata、復旧との整合も確認 |
| A/B health | 必須policy・local機能が健全ならofflineでも所定の動作 | policy未稼働や起動失敗は未制限のままcommitしない。外部server切断を本体不良と混同せず、tryboot/rollback・電断・再起動を検証 |

負の試験は機器を壊す攻撃コードの配布ではなく、隔離した試験用構成で権限境界を確認するものです。生のdevice・ネットワーク・外部serviceを無断で操作せず、使い捨てのimageと試験用interfaceを使います。

## 証拠を層ごとに保存する

1. **静的な設定**: defconfig、最終Buildroot/BusyBox/kernel設定、ELF、所有者・mode・file capability、起動順、profile/filter/ruleset、packageのuser作成を記録します。
2. **実行時**: 同じbinaryでUID/GID、`/proc/PID/status`のcapability・NoNewPrivs・Seccomp、LSM一覧・profile attachment/enforce、LandlockのABI問合せ、mount/device状態、実効rulesetを記録します。存在確認だけで終わらず、前表の正負の操作結果と結び付けます。
3. **故障時**: policy読込み失敗、必須module不足、daemon crash、staging満杯、network中断、初期時刻異常、更新中の電断・再起動を別のrunとして保存します。
4. **QEMUと実機**: QEMUでprocess/file/network namespace等の試験ができても、Wi-Fi認証、実deviceのioctl、USB Ethernet、driver、電断、GPU firmwareのtrybootの実機確認を代替しません。

比較・性能の試験は[実験記録スキル](../../../.agents/skills/experiment-record/SKILL.md)に従い、基準commit、実binary・imageのhash、tool版、commands、事前基準、生CSV、失敗・除外理由を残します。性能は原則5回以上で、起動時間だけでなくPSS/RSS、image size、CPU、SD書込み、復旧時間、policyの保守量も比べます。静的な同じbyte列の照合や単発の構築可否は、回数と理由を書き、性能の結論へ流用しません。今回、新しい権限設計の性能測定はしていません。

## 今回確認したことと残件

今回の検証は[基準と範囲](README.md)にあるコード読取り、既存最終kernel設定のhash一致と設定確認、出典の取得状態・bytes/hash照合、文書の相互参照です。既存更新処理のhost回帰試験を走らせても、新しいprivsep・policyを検証したことにはなりません。

検査の条件・commands・終了値・警告・失敗試行は[静的監査の記録](../../experiments/2026-11-02-security-design-audit.md)に保存しています。自動の文書検査と、設計した権限制限のruntime拒否試験は別です。

未実装の専用user・helper・policy・通信開始制御と、上記のruntime拒否試験・新規image/QEMU・実機試験は残っています。製品版のログイン方式、SemVerと内部番号、鍵運用の決定も別途必要です。これらが済む前に「最小特権化済み」「AppArmorで保護済み」「Wi-Fi利用可能」とは報告しません。
