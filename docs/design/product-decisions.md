# 利用者が決めた製品の方針

利用者がチャットで決めた方針の記録。実装済みかどうかを「状態」に書く。設計の詳細は各リンク先。

| 決めた日 | 方針 | 状態 | 関連 |
|---|---|---|---|
| 2026-11-13 | seedrngのseedを永続保存せず、起動・停止時を含め`/data/seedrng`へ書き込みません。内蔵hwrng（`CONFIG_HW_RANDOM_BCM2835=y`）とjitterに依存する方針です。seed保存のための定期的なSD書き込みと、暗号化されていない`/data`へのseed残存を避けます。一方、hwrngが弱い場合に保存seedのbackupがありません。 | 未実装。early bootのcrng初期化時間、jitterの供給経路と起動時の保証はQEMU・実機とも未確認 | [書き込みの台帳](write-policy.md)、[既存の棚卸し](../experiments/2026-11-12-write-inventory.md) |
| 2026-11-13 | 初回起動からzram swapを使い、login prompt表示後にbackgroundで有効化します。容量はRAMの約50%、圧縮はzstdまたはlzo-rleを候補とします。built-in（`CONFIG_ZRAM=y`）を方針とし、現行の`=m`との差を測ります。圧縮のCPU負荷、小さいmetadata用RAM、早いOOMの代わりにthrashする可能性を受け入れます。 | 未実装。圧縮方式の選定、built-inとの差・RAM不足時の挙動・起動時間の測定は未実施 | [書き込みの台帳](write-policy.md)、[過去のQEMU実験](../experiments/2026-10-21-qemu-zram.md) |
| 2026-11-13 | `/data`のrw・journal・commit方針は、S03 ext4書き込み・電断、S4 fs-compare、rootfs-stay-ro、GPIO6 powerfailの既存実験から判断します。実機の耐電断性を優先する従来方針は維持し、追加実験を計画します。 | 具体的な設定値は未決定。既存結果の適用範囲の整理と追加実験待ち。現行mountは変更しない | [既存証拠と追加計画](write-policy.md#dataのmount方針を決めるための資料と追加計画) |
| 2026-11-13 | Wi-Fiではlegacy EAP（MSCHAPv2等）とTLS-PSKの互換性を維持しません。対応するOpenSSL機能を削減候補にします。WPAのPSKとTLS-PSKは区別します。 | 方針決定済み、削減・接続確認は未実施 | [OpenSSL最小化](../research/component-options/openssl-minimal.md)、[ネットワーク比較](../research/alternatives/network.md) |
| 2026-11-13 | RAUCのような標準更新frameworkへ移り、公開の`msd-update`を廃止します。ただしRAUCとSWUpdateの比較完了後に移行先を決めます。それまではOpenSSLのCMSを残し、CLIも`msd-update`が存在する間は維持します。移行後に`no-apps`を再検討します。 | 未実装。移行先の選定・比較は未完了。CLIの恒久利用は決定していない | [更新framework比較](../research/alternatives/updates.md)、[OpenSSL最小化](../research/component-options/openssl-minimal.md) |
| 2026-11-13 | 機器の速度を容量より優先し、速度のためにrootfsが大きくなることを許容します。OpenSSLのasmを維持します。boot時間への影響は小さい見込みですが、測定で確かめます。 | 方針決定済み。asmは現行でも使用。容量・実機速度・boot時間への影響は未測定 | [OpenSSLの測定方針](../research/component-options/openssl-minimal.md#実験と残る判断) |
| 2026-11-13 | PQCとhybrid Groupsの採否は未決定とし、容量・相互運用性・実機速度・保守上の利点と負担を比較する判断資料を準備します。 | 未決定、資料作成待ち | [OpenSSL設定案](../research/component-options/openssl-minimal-runtime.md) |
| 2026-11-13 | legal-infoは選択肢Aの補足資料collectorを採用します。固定Buildroot sourceと外部treeの対応、Bootlinのlicense原文とsource・patchへの参照を補足し、原警告を保持します。警告ゼロや完全な対応sourceの収集・配布許諾確認を主張しません。全source収集の選択肢Bは今回の範囲にしません。 | 未実装。Buildroot source未保存・Bootlin license file未定義の警告は残る | [SBOMとlegal-infoの確認範囲](../research/operations/sbom-coverage.md) |
| 2026-11-12 | Buildroot 2026.08.xを維持し、host/targetのOpenSSLを外部treeで3.5.9 LTS（保守期限2030-04-08）に固定します。2026.11.x、その後2027.02 LTSへの更新は後日行います。12月1日予定の3.5.10は別作業とし、11月10日のadvisory修正は自前backportしません。 | 外部overrideと週次監視を実装。検証範囲は実験記録に記載。基盤更新と3.5.10は未実施 | [保守判断](../research/dependencies/openssl-maintenance.md)、[実験記録](../experiments/2026-11-12-openssl-3.5-lts.md) |
| 2026-11-03 | RAUCまたはSWUpdateへ移行した後は、公開の`msd-update` commandを残さず、bundleの検証とslotへの書き込みをframeworkに任せます。 | 未実装（frameworkは比較中） | [更新frameworkの比較](../research/alternatives/updates.md) |
| 2026-11-03 | framework移行後の更新処理と暗号実装にはOpenSSLを使います。 | 未実装 | [更新frameworkと暗号libraryのbuild option](../research/alternatives/update-build-options.md) |
| 2026-11-03 | 配信先はGitHub Releasesを候補とし、IPFSは今回のPoCに含めません。 | 調査済み | [更新経路と差分配信](../research/alternatives/update-delivery.md) |
| 2026-11-03 | 更新経路は4つです。P1は端末から差分を取得し、P2は端末から全体を取得します。P3は別端末が更新fileを`/data`の決まったdirectoryに置き、端末が読みます。P4は別端末からimage全体を書き直します。 | 未実装 | [更新経路と差分配信](../research/alternatives/update-delivery.md) |
| 2026-11-03 | 起動時の表示とos-releaseに、版、commit時刻（JST）、commit IDを表示します。例：`MSD/Linux v0.1.0-rc.1 (2026-11-03 21:34:56 JST, commit 1234567)`。tagのないbuildは`unreleased`、dirtyなbuildは`-dirty`を付けます。 | 実装済み（PR #209）。fs-compare runのQEMU serial logでlogin前の表示を確認済み。観測したのはdirtyな開発buildで、tag付きrelease build（`vX.Y.Z` / `-rc.N`）の表示は未確認 | [版情報の生成](../../board/cardputerzero/tools/write-version-info.sh)、下記の保存済み証拠 |
| 2026-11-03 | `/data`のfilesystem候補としてext4、F2FS、Btrfs（dataのDUPとchecksumの種類を含む）、LUKS2、dm-integrityを電源断・破損試験で比べ、最終判断は利用者が行います。Btrfsのdata checksumによる破損検出を重視します。 | 比較中（option表は作成済み） | [filesystem optionの比較](../research/storage/filesystem-options.md) |
| 2026-11-04 | `/data`は頻繁に書き換えないため、速さより電源断への強さを優先します。同期書き込みなど遅い設定も候補から外さず、書き込み量を測って判断します。 | 比較の基準に反映済み | [filesystem optionの比較](../research/storage/filesystem-options.md) |
| 2026-11-03 | 操作していない時やprogressを表示していない時は永続storageに書き込みません。2秒以上かかり得る処理ではprogressと中断可否を表示します。画面の文言は英語・日本語を併記します。 | 規則は制定済み（AGENTS.md §10）。現行の未対応箇所は台帳に記録 | [書き込みの台帳](write-policy.md) |
| 2026-11-03 | 文書とユーザーズマニュアルは日本語だけにし、英語版は作りません。 | 規則は制定済み（AGENTS.md §2） | [AGENTS.md](../../AGENTS.md) |
| 2026-11-03 | `/data`は初回起動から暗号化する方向で設計します。鍵は端末ごとに作り、build時に共通鍵を作りません。既定passwordの間も起動を止めません。passwordまたはPINを設定する時は、既定でvolume keyを替え、替えないoptionも用意します。解錠方式はpasswordなし・PIN・passwordから利用者が選びます。 | 計画のみ | （リンクなし。計画はリポジトリに入れていない） |
| 2026-11-03 | 一般userの初期名は`muromi`、UID/GIDは1000、homeは`/data/home/muromi`にします。 | 未実装 | R02の設計に反映予定 |
| 2026-11-03 | Wi-Fi、`/data`暗号化、boot image検証などを行う対話型toolをRubyまたはmrubyで作ります。画面は英語・日本語を併記します。かなだけの日本語表示案とfbcon、fbterm、kmsconなどを比べます。 | 計画のみ | [フォントとコンソールの調査](../research/presentation/fonts.md) |
| 2026-11-03 | timezoneの既定値はAsia/Tokyoにする方向です。`timedatectl`は導入しません。 | 2026-11-12にtzdataのasiaと既定localtimeを実装。QEMUのdateはJST +0900。RTC・NTP・実機は未確認 | [CardputerZeroのdefconfig](../../configs/msd_cardputerzero_defconfig)、[採用範囲](../research/component-options/timezone.md)、[実験](../experiments/2026-11-12-write-inventory.md) |
| 2026-11-03 | 部品を採用する前に代替品、build option、実行時の設定項目を調べます。更新時には新機能、新しいoption、既定値の変更を検討します。 | 規則は制定済み（PR #212） | [component-optionsスキル](../../.agents/skills/component-options/SKILL.md) |
| 2026-11-12 | Wi-Fiにはwpa_supplicant（OpenSSL）+ dhcpcdを使い、udhcpcとの比較は残します。iwdは不採用とします。主な利点だったOpenSSLの回避はOpenSSL採用後の利点にならず、SAE/EAPの処理に使うELL TLSは第2の暗号・TLS実装になります。実行時D-Busとkernel暗号APIの設定（DES/MD5/SHA1等）も必要で、内蔵DHCPを使ってもDNS処理は別途必要です。 | 方針決定済み、実装・実機確認は未実施 | [ネットワークの比較と計画](../research/alternatives/network.md)、[iwdの暗号と実行時依存](../research/alternatives/update-build-options.md#iwdの暗号と実行時依存) |

版表示の証拠は、orphan branch `data/fs-compare-experiments` のcommit `586d7e49a17fa3df8ce769c6c60404c5c5ffc1c2` にある [fs-compare/phase2-j8-check.tar.zst](https://github.com/uist1idrju3i/MSD-Linux/blob/586d7e49a17fa3df8ce769c6c60404c5c5ffc1c2/fs-compare/phase2-j8-check.tar.zst) に保存されています。archive内の `phase2-j8-check-T4-sync-P010-r1-1794370142/qemu.log` に次の表示があり、`msd login:` より前に出ています。

```text
MSD/Linux unreleased (2026-11-11 09:40:04 JST, commit a84b12a-dirty)
```
