# TUF・Uptaneと更新metadataの比較

[代替比較](README.md) / [更新framework](updates.md) / [署名・鍵](signing.md) / [RESEARCH](../../../RESEARCH.md)

## 署名だけでは解決しない問題

有効なbundle署名は発行者とbytesの対応を確認します。それだけでは古い正規bundleのreplay、更新がないように見せるfreeze、鍵の失効・更新、異なる世代のmetadataの混在まで解決しません。HTTPS、GitHubのtag・asset名、checksumの掲載も代用にはしません。

2026-11-02にMSD/Linuxの`c0214b380c046100592cd427ab3013347dff1758`、TUF仕様の`e2bc7d83d0740aaae8dd7133dd4f237ce3d86b16`、Uptane標準の`a02f9cace9e842dbc33f2151b47620a50ccc9151`を基準に確認しました。metadata client・repository・鍵rotation・Release配信のbuild/実行試験は本リポジトリでは試していません。現行manifestの仕様は変更しません。

## 別々に決める版と状態

| 値・状態 | 目的 | 混同しないもの |
|---|---|---|
| 公開SemVer | 利用者へリリースの互換性・変更を示す | 単純な辞書順、metadata版、boot試行回数 |
| 更新の内部番号 | 許可するimage世代の順序を定める案 | SemVerのbuild metadataやtag名。分離案は確認待ち |
| TUFのrole別metadata版 | 各metadataのrollback等を検出する | OSのSemVerと一対一である必要はない |
| expiryと信頼できる時刻 | 古いmetadataのfreezeを検出する | 単調な番号だけでは現在時刻や鮮度を証明できない |
| 取得済み・試行中・commit済み | 更新transactionと既知の正常slotを区別する | 新metadataを見た時点と、新imageが正常に起動した時点 |

TUFの新metadataを受理しても、そのimageで正常にbootできた保証にはなりません。最高到達番号をどの時点で永続化するかによって、失敗時のA/B復旧を妨げる可能性があります。networkから古い版を新規導入する拒否と、既に保持する正常slotへの障害復旧を別に設計します。SD上の状態を丸ごと戻せる物理攻撃に対するhardware anti-rollbackは、通常のfile保存だけでは提供できません。

## TUFが扱うroleと信頼移行

[TUF仕様](https://github.com/theupdateframework/specification/blob/e2bc7d83d0740aaae8dd7133dd4f237ce3d86b16/tuf-spec.md)と[roleの公式説明](https://theupdateframework.org/docs/metadata/)は、四つのtop-level roleと、必要に応じたtargetsの委任を定めています。

| role | 主な責務 | 運用上の費用 |
|---|---|---|
| root | roleごとの鍵・threshold・信頼する鍵の移行を定める | 初期rootの安全な組込み、offline保管、署名儀式、紛失時の回復 |
| targets | target fileのhash・length、必要なら用途を限定した委任 | board・channel・imageの対応をapplication policyへ結び付ける |
| snapshot | targets metadataの版等を結び付け、世代の混在を検出する | repositoryの一貫した公開と、clientの永続状態 |
| timestamp | snapshotへ結び付く短命metadataでfreeze検出を支える | 定期的な再署名・配信、online鍵、端末の時刻とoffline期間 |

root更新では、信頼済み版から順に新rootを取得し、旧側・新側のthresholdを満たす署名等を検査します。「新しい公開鍵をdownloadして置く」だけでは信頼の移行になりません。同じ鍵の署名を重複してthresholdへ数えないこと、metadataの長さ・取得回数・期限・版の上限も仕様と実装で照合します。

TUFはimageを書き込むframeworkではありません。targetのhash/lengthを検証しても、boot-aとrootfs-aの対応、boardの許可、slot上限、device path、healthはMSD/Linux側の契約です。署名対象外のRelease説明からboardや書込み先を決めません。JSONを使う場合もcanonicalization・重複key・数値範囲・未知field・署名対象を曖昧にした独自parserへ縮小しません。

## Uptaneを同じものとして扱わない

[Uptane標準](https://github.com/uptane/uptane-standard/blob/a02f9cace9e842dbc33f2151b47620a50ccc9151/uptane-standard.md)は、Image repositoryとDirector repository、Primary/Secondary ECU、端末側のversion manifest、侵害される組合せを含む脅威モデルを扱います。単にTUFへ名前を付け替えたものでも、A/B writerでもありません。

CardputerZero単体のOSをGitHub Releasesから取得する用途では、車両・複数ECU向けの全運用を持ち込む費用を正当化できるか未確認です。将来、複数の周辺MCU・moduleへ端末別に更新を指示し、OSと周辺firmwareの対応を管理するなら再検討します。周辺ICが多いという理由だけで、全てをUptaneのECUとして扱う設計にはしません。

## 現行・独自拡張・標準実装の比較

| 方式 | 得られること | 残る責務・費用 | 提案 |
|---|---|---|---|
| 現行のmanifest署名 | 小さな形式と既存Ed25519検証を使う | 鮮度、role、rotation、委任等は現行に揃っていない | 比較の基準 |
| 独自に期限・key ID・番号等を追加 | 用途に絞った小さな形式を設計できる | parserだけでなく信頼移行、offline、freeze、復旧を長期保守する。標準と似たfield名だけでは同じ保証にならない | 一部概念の参照は可能だが「TUF対応」と称さない |
| 既存TUF実装を利用 | 仕様に沿ったmetadata更新・検証を再利用できる | runtime/toolchain、crypto provider、I/O、永続状態、test suite、配信運用 | 独自protocol再実装より先に実験候補 |
| Uptane構成 | 複数ECUと端末別指示の信頼を分けて管理する | 二つのrepositoryやmanifest、時刻、ECU間連携、key provisioning | 多端末・周辺firmwareの要件が出た時に再評価 |

取得した[Python-TUF README](https://github.com/theupdateframework/python-tuf/blob/e6cdfc90789a35f37addfc8c8ece0e637a5ec2cc/README.md)はmetadata API、`ngclient`、repository libraryを分け、repository libraryをstable APIの一部とはしないと記します。Python-TUFをhostのrepository生成・相互運用の比較対照に使い、target実装は別に選ぶこともできます。targetへPython一式を無条件で入れる提案ではありません。

追加の[端末自己更新の調査](../release-client/README.md)では、Python-TUF、go-tuf、tough、rust-tufと公開側tuf-on-ciの固定版・依存・検証／保存処理を静的に比較しました。metadataの仕様と実装、配信、時刻・永続状態・A/B復旧を分けて検討しています。全機能のconformance、Buildroot統合、最終サイズ・性能は未検証で、特定実装の採用決定はまだしません。

## GitHub Releasesへ結び付ける条件

以下は設計候補で、実装済みの自動更新手順ではありません。

1. 信頼する初期rootや検証鍵、board/channel policyをimageへ組み込みます。可変な`/etc` overlayが信頼する情報を隠せる構造も[保存領域の比較](filesystems.md)と一緒に見直します。
2. Release APIで候補を発見し、認証済みmetadataが許可したtargetのhash・長さと照合します。tag、asset名、HTTPのContent-Lengthだけを信頼しません。公開取得に広い常設tokenを配りません。
3. TLSのCA・hostname・期限、redirect、timeout、bytes/metadata数の上限、途中切断を検査します。metadataが正しくても無制限の取得を許しません。
4. 有効期限とoffline期間の方針を決めます。RTCが存在することと、保持時刻が信頼できることは別です。時刻未確定時に期限検査を黙って無効にしません。online署名鍵が必要なroleは、有効期限より短い間隔で再署名する運用も必要です。
5. 検証・版・board・空き容量・inactive slotの確認後、狭い特権writerへ渡します。metadata clientに任意deviceの書込み権限を与えません。
6. 新metadata・取得済みimage・boot試行・health・commitの状態を、電源断しても矛盾しないよう保存します。正常slotへ戻る例外と、禁止した古い更新の拒否を試験します。

## 採用前の試験とlicense

正しい署名だけでなく、誤鍵、threshold不足・重複、root飛越し、途中root欠損、古いtimestamp/snapshot/targets、expiry、mix-and-match、board違い、過大length、parser差、書込み中断、未更新端末、鍵紛失・rotationを試します。署名・時刻・永続状態を壊す負の対照も必要です。

TUF仕様とUptane標準の取得原文はCommunity Specification License 1.0です。仕様文書のlicenseを実装codeのlicenseへ読み替えません。Python-TUF READMEはMIT/Apache-2.0の二重licenseを示します。採用するclient、暗号provider、repository tool、test vectorの実物についてfile単位の条件とSBOMを確認し、版・脆弱性監視を追加します。

取得時のGitHub latest応答はTUF仕様v1.0.37、Python-TUF v7.0.1、Uptane標準2.1.0でした。仕様版と実装版は別です。開発HEADとRelease、取得成功と仕様全体の精読、仕様への準拠と本機での動作成功を分け、URL・ref・hash・時刻を[sources.json](sources.json)に保存します。
