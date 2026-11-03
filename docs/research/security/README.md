# OpenBSDの考え方を取り込む権限設計

[RESEARCH](../../../RESEARCH.md) / [物理アクセスと費用](threat-model.md) / [接続管理の比較](../alternatives/network.md)

## この調査の結論

OpenBSDから取り入れるのは、**危険な入力を扱う処理に大きな権限を渡さず、必要な初期化が済めば権限を捨て、不要な機能を既定で動かさない設計**です。小さいbinaryや少ないdaemonの数だけを安全性の基準にはしません。入力の解析、認可、deviceへの書き込みを分け、その境界を負の試験で確認します。

本稿は調査と設計提案です。専用user、権限分離した更新helper、AppArmor profile、seccomp filter、Landlock ruleset、nftables policyは、この変更では製品へ追加していません。Wi-Fiの実機接続、policyの強制、ログイン操作も今回の検証対象ではありません。既存の署名付きA/B更新とmodule署名の証拠を、新しい権限設計の検証結果へ転用しません。

| 読む目的 | 本文 |
|---|---|
| カード交換・bootの信頼点と対策費用 | [脅威モデル](threat-model.md) |
| 当時の候補・非採用理由と現在の注記 | [強化項目の履歴](history/README.md) |
| 原則をLinuxへどう適用するか | [OpenBSDとLinuxの違い](principles.md) |
| 現行のroot処理、可変設定、device・IPCの境界 | [処理ごとの権限設計](privileges.md) |
| Wi-Fi等を動かす前に何を強制するか | [通信開始と多層防御](network.md) |
| 何が拒否されればよいか、何から実装するか | [段階導入と検証](verification.md) |
| URL、取得状態、応答のhash | [出典台帳](sources.json) |

## 照合した範囲と限界

基準ソースはMSD/Linuxの[eead206](https://github.com/uist1idrju3i/MSD-Linux/commit/eead206a4fdacb2bb0b10933cebbe4c1b992baf3)、Buildrootの固定submoduleは`8b238854d909c9cce32ef9671d968b03e323b55d`です。rootfs-overlay、post-build、defconfig、kernel fragmentと、固定Buildrootのsystem設定定義を読みました。

最終kernel設定は[既存CI生成物の照合記録](../../experiments/2026-11-02-hardware-artifact-audit.md)と[入力JSON](../../experiments/2026-11-02-hardware-artifact-audit.json)に対応するものを再読し、SHA-256 `74d625a1c9dad65fd2999abd0b0a572874a39b32dbd1d685edcb3153ea8a0739`の一致を確認しました。これはcheckout `c96e5faf015c828a213c8ea64f613b4a429196c7`、PR head `84ca145032216b696a8944d54b4f820edc1ac565`の生成物で、今回のbranchを新規buildした結果ではありません。

| 層 | 確認したこと | そこからは言えないこと |
|---|---|---|
| ソースの設定 | BusyBox init/mdev、overlay、root更新処理、署名の呼出し | 新しい専用UID・policyが起動時に強制されること |
| 固定CIの最終kernel設定 | SECCOMP/FILTER、USER_NS/NET_NS、AUDIT、AppArmor、Landlockが有効。NF_TABLESはmodule。SELinuxは無効 | 現在のLSM一覧、AppArmor profile、Landlock ABI、seccomp filter、firewallの実効状態 |
| Buildroot設定の展開 | rootログイン有効、初期root password空、console getty、user table指定なし | 現物のshadow、実機ログイン、全packageが追加するuserの一覧。user table未指定でもpackageがuserを作る場合がある |
| 公開資料 | OpenBSDのsecurity方針・manual、Linux 6.18文書、Linux man-pages、nftables wikiの関連箇所 | MSD/Linuxの実装・性能・侵入耐性、全候補の全文精読・license監査 |

取得は25件を試み、23件成功、2件失敗でした。AppArmorの追加文書とBusyBoxの上流Config.inの404は台帳に残しています。成功した別資料で失敗を置き換えていません。本文の主張に使ったのは各文書の該当節で、巨大なsystemd manualを含む全取得物を全文精読したという意味ではありません。OpenBSD manual等の可変ページは取得時刻と応答hashで識別し、Linux 6.18の版付きURLとも区別します。

## 優先順位と未決定事項

1. 書ける場所、更新鍵・起動設定の正本、通常利用者と管理者の境界を先に決めます。rootfsがROでも、可変な`/etc`が鍵やpolicyを隠せる構成なら、そこも信頼対象です。
2. ネットワーク導入前にfirewallとserviceごとの権限制限を強制します。外部入力のparserをrootで動かし続ける構成を避けます。
3. 既存daemonの特権分離、[更新framework](../alternatives/updates.md)、既存sandboxの利用を先に評価し、自作のroot IPCや万能launcherを安易に増やしません。
4. 実装する機能に必要な制限と試験を定義し、QEMU・実機・配布の確認を通してから有効化します。

製品版の一般userと管理操作、初回設定・復旧方法は要件確認待ちです。無認証rootコンソールを製品版の安全な既定値として追認せず、開発用と分ける案を提示していますが、ログイン設定は変更していません。公開SemVerと内部更新番号の契約、更新鍵の運用も別の未決定事項です。

hardware secure bootの文書化された経路がないBCM2837を前提に、署名更新をsecure bootとは呼びません。カード全体を交換できる攻撃者、同じカード上の公開鍵・検証処理・root digest、rootを既に得た攻撃者に対する限界は[脅威モデル](threat-model.md)を参照してください。
