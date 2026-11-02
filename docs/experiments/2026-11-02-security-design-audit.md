# OpenBSDの原則とLinux権限設計の静的監査

[実験記録の一覧](README.md) / [調査の索引](../../RESEARCH.md) / [権限設計の本文](../research/security/README.md)

## 目的と条件

OpenBSDの最小特権、特権分離・放棄、多層防御、安全な既定値、単純さを、MSD/Linuxの実際の処理と権限へ対応づけました。設計案と製品の実装を区別し、既存の過大な保護の説明も訂正する静的監査です。新しいpolicyの性能比較やruntime試験ではありません。

- 基準commit: `eead206a4fdacb2bb0b10933cebbe4c1b992baf3`。変更対象はREADME、調査・訂正文書と記録のみです。
- 判定基準: 実装・設計・未確認を分け、各原則から処理別の境界と拒否試験へ辿れること。既存の文書検査・回帰試験・固定環境lintの終了値は0を要求します。取得失敗は成功へ含めず、kernel設定の存在をruntime強制の証明にしません。
- Python 3.12.13、固定開発OCIのactionlint 1.7.12とShellCheck 0.11.0、固定requirementsのzizmor 1.31.1を実際の出力で確認しました。
- 検査は各1回です。同じ入力の構造・終了値を確かめる検査であり、5回以上の性能測定やA/A比較を行ったという意味ではありません。cacheのwarm/cold別の性能は測っていません。

## 照合した内容

OpenBSDとLinux等の資料25件を取得し、23件が成功、2件が失敗でした。[出典の記録](../research/security/sources.json)にURL、取得時刻、status、取得できた応答のbytes/SHA-256、読んだ範囲の限界を保存しています。23件の応答をhashと照合し、AppArmor追加資料とBusyBox Config.inの404は残しました。全文精読・license audit・実機確認の完了とはしません。

固定CIのkernel設定のhashとprovenance、Buildroot設定にあるroot login、data/etc overlay、mdev、watchdog、powerfail、update、healthのコードを読みました。[基準と生成物](../research/security/README.md)で当時のCI artifactと現在のbranchを区別し、[処理別の表](../research/security/privileges.md)に必要な権限と分離案を記載しました。無認証root consoleの実機確認や変更はしていません。

## 再実行する検査

リポジトリのrootから実行します。最初の5コマンドは相互参照・文字・サイズ・skills・siteの静的検査です。新規文書も追跡対象に含めてください。

```sh
python3 .github/scripts/check-links.py
python3 .github/scripts/check-jisx0213.py
python3 .github/scripts/check-doc-size.py
python3 .github/scripts/check-skills.py
python3 .github/scripts/check-site.py
tests/check-doc-size/run.sh
tests/check-links/run.sh
tests/check-jisx0213/run.sh
tests/check-site/run.sh
tests/msd-update/run.sh
tests/check-pins/run.sh
docker/msd-dev actionlint .github/workflows/*.yml
docker/msd-dev python3 .github/scripts/shellcheck-tracked.py
"$HOME/.cache/msd-linux-zizmor/bin/zizmor" --offline --format=github .github/workflows/
```

## 結果と警告

文書検査と既存回帰試験、固定環境のlintは終了値0でした。[回帰・lintの生の終了値と出力hash](2026-11-02-security-design-audit.csv)を保存しています。新しい専用user・IPC・seccomp・Landlock ruleset・AppArmor profile・firewallの拒否試験を通した結果ではありません。既存msd-update host試験は20項目に成功しましたが、新しいsandboxの強制や実機A/B起動は対象外です。

既存のJIS文字警告9件と20,000 bytes超の文書の警告は残ります。今回の新しい権限本文は全て20,000 bytes未満です。日付付き強化項目と訂正記録を維持する理由は[文書map](../research/document-map.md)に記載しました。

yomiyasuのrun/verifyと本文・差分を照合しました。表・索引のリスト比率、説明の文末、誤解を避ける技術的な否定は役割があるため残しています。台帳は取得記録、正本は検証で信頼する版、入口は既存の索引を指すため保持しました。意味の変更候補には新規設計と意図した事実訂正が含まれ、[元の説明と訂正理由](../research/corrections.md)を照合しました。自動検査が技術的正しさを認定したわけではありません。

## 失敗した試行

1. check-linksへ個別pathを渡すと、対応しない引数のためusage errorとなりました。全体検査へ切り替えました。
2. 新規本文を追跡対象へ加える前の全体リンク検査は7 errorsでした。リンク先の作成だけでなく追跡状態も確認し、文書だけを追加して再実行しました。
3. yomiyasuで書き直す前の同一draftをmaterialとして渡した試行はcode 2でした。draftはsourceへ、別の計画資料はmaterialへ分けてやり直しました。

失敗を製品の脆弱性や拒否試験の失敗とは扱いません。失敗した取得や上記の試行を、成功した資料・検査でなかったことにはしていません。

## 結論と残件

原則・処理・通信・検証条件を文書へ反映しました。root login方針、鍵とpolicyの正本、SemVerと内部更新番号、鍵運用の決定が必要です。製品のUID/GIDや起動制御、Wi-Fi接続管理、firewall、profile/filter、特権writerの分離は未実装です。新規製品image、QEMU、CardputerZero実機の試験も今回行っていません。
