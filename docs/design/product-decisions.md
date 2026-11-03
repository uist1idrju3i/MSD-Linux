# 利用者が決めた製品の方針

利用者がチャットで決めた方針の記録。実装済みかどうかを「状態」に書く。設計の詳細は各リンク先。

| 決めた日 | 方針 | 状態 | 関連 |
|---|---|---|---|
| 2026-11-03 | RAUCまたはSWUpdateへ移行した後は、公開の`msd-update` commandを残さず、bundleの検証とslotへの書き込みをframeworkに任せます。 | 未実装（frameworkは比較中） | [更新frameworkの比較](../research/alternatives/updates.md) |
| 2026-11-03 | framework移行後の更新処理と暗号実装にはOpenSSLを使います。 | 未実装 | [更新frameworkと暗号libraryのbuild option](../research/alternatives/update-build-options.md) |
| 2026-11-03 | 配信先はGitHub Releasesを候補とし、IPFSは今回のPoCに含めません。 | 調査済み | [更新経路と差分配信](../research/alternatives/update-delivery.md) |
| 2026-11-03 | 更新経路は4つです。P1は端末から差分を取得し、P2は端末から全体を取得します。P3は別端末が更新fileを`/data`の決まったdirectoryに置き、端末が読みます。P4は別端末からimage全体を書き直します。 | 未実装 | [更新経路と差分配信](../research/alternatives/update-delivery.md) |
| 2026-11-03 | 起動時の表示とos-releaseに、版、commit時刻（JST）、commit IDを表示します。例：`MSD/Linux v0.1.0-rc.1 (2026-11-03 21:34:56 JST, commit 1234567)`。tagのないbuildは`unreleased`、dirtyなbuildは`-dirty`を付けます。 | 実装済み（PR #209）。QEMUのserial logでの表示は未確認 | [版情報の生成](../../board/cardputerzero/tools/write-version-info.sh) |
| 2026-11-03 | `/data`のfilesystem候補としてext4、F2FS、Btrfs（dataのDUPとchecksumの種類を含む）、LUKS2、dm-integrityを電源断・破損試験で比べ、最終判断は利用者が行います。Btrfsのdata checksumによる破損検出を重視します。 | 比較中（option表は作成済み） | [filesystem optionの比較](../research/storage/filesystem-options.md) |
| 2026-11-04 | `/data`は頻繁に書き換えないため、速さより電源断への強さを優先します。同期書き込みなど遅い設定も候補から外さず、書き込み量を測って判断します。 | 比較の基準に反映済み | [filesystem optionの比較](../research/storage/filesystem-options.md) |
| 2026-11-03 | 操作していない時やprogressを表示していない時は永続storageに書き込みません。2秒以上かかり得る処理ではprogressと中断可否を表示します。画面の文言は英語・日本語を併記します。 | 規則は制定済み（AGENTS.md §10）。現行の未対応箇所は台帳に記録 | [書き込みの台帳](write-policy.md) |
| 2026-11-03 | 文書とユーザーズマニュアルは日本語だけにし、英語版は作りません。 | 規則は制定済み（AGENTS.md §2） | [AGENTS.md](../../AGENTS.md) |
| 2026-11-03 | `/data`は初回起動から暗号化する方向で設計します。鍵は端末ごとに作り、build時に共通鍵を作りません。既定passwordの間も起動を止めません。passwordまたはPINを設定する時は、既定でvolume keyを替え、替えないoptionも用意します。解錠方式はpasswordなし・PIN・passwordから利用者が選びます。 | 計画のみ | （リンクなし。計画はリポジトリに入れていない） |
| 2026-11-03 | 一般userの初期名は`muromi`、UID/GIDは1000、homeは`/data/home/muromi`にします。 | 未実装 | R02の設計に反映予定 |
| 2026-11-03 | Wi-Fi、`/data`暗号化、boot image検証などを行う対話型toolをRubyまたはmrubyで作ります。画面は英語・日本語を併記します。かなだけの日本語表示案とfbcon、fbterm、kmsconなどを比べます。 | 計画のみ | [フォントとコンソールの調査](../research/presentation/fonts.md) |
| 2026-11-03 | timezoneの既定値はAsia/Tokyoにする方向です。現行はtzdataがなくUTC表示で、`timedatectl`はありません。 | 未実装 | [CardputerZeroのdefconfig](../../configs/msd_cardputerzero_defconfig) |
| 2026-11-03 | 部品を採用する前に代替品、build option、実行時の設定項目を調べます。更新時には新機能、新しいoption、既定値の変更を検討します。 | 規則は制定済み（PR #212） | [component-optionsスキル](../../.agents/skills/component-options/SKILL.md) |
