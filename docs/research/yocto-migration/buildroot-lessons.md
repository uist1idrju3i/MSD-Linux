# Yocto 検討を Buildroot に活かす

[検討の索引](README.md) / [総まとめ](summary-2026-11.md) / [文書案内](../../README.md)

Buildroot 維持の判断は変えません。Yocto で作りやすいことは、製品への採用理由とは別です。ここでは、検証と監査へ取り込む事項、比較候補として残す事項を分けます。

## 証拠を読み直した範囲

対象は本ディレクトリの検討文書と、下表の実験本文・CSV です。CSV は状態・失敗理由を含む全列を照合しました。これは過去の値の再集計で、新しいビルドや起動試験ではありません。

| 証拠 | 保存された行と確認結果 | 読めない範囲 |
|---|---|---|
| [Wrynose 構築試験](../../experiments/2026-11-02-yocto-wrynose-probe.md)・[CSV](../../experiments/2026-11-02-yocto-wrynose-probe.csv) | 7 行。成功 3、失敗 4。rootless 検出、層の path、patch QA の失敗を成功と分けた。`Upstream-Status` 追加直後も失敗した B1-3 の原因は未特定 | 元の構築ログ全文 |
| [QEMU 起動確認](../../experiments/2026-11-02-yocto-qemu-boot.md)・[CSV](../../experiments/2026-11-02-yocto-qemu-boot.csv) | 17 行。成功 11、その他 6。成功のうち 1 は準備確認 Q7、正式な反復は P1–P5 と S1–S5。修正した写しの起動であることを維持 | シリアルログ全文と元イメージ |
| [成果物比較](../../experiments/2026-11-02-buildroot-yocto-artifacts.md)・[CSV](../../experiments/2026-11-02-buildroot-yocto-artifacts.csv) | 7 行。BR1 の worktree 由来の失敗を分離。cold 時間は各 1 回で、完成度とツールチェーンの違いが残る | 元の build・legal-info ログ全文 |
| [設定差分](../../experiments/2026-11-02-buildroot-yocto-kconfig-diff.csv) | 544 行。THERMAL と BCM thermal を含む。fragment にない項目も変わり、原因は未特定 | 両側の最終 `.config` 全文 |
| [起動時間比較](../../experiments/2026-11-02-buildroot-yocto-boottime.md)・[CSV](../../experiments/2026-11-02-buildroot-yocto-boottime.csv) | 54 行すべて pass。初回 9、通常 45。通常起動は 9 組とも 5 回。初回を除いた中央値・最小・最大を再計算し、旧集計出力と一致 | 正式 54 本と失敗した run1 のログ全文 |

元の保管先候補は読み取りを拒否され、ログ全文を取得できませんでした。本文の抜粋、CSV、記録済み SHA-256 と、ログそのものの再確認を区別します。記録に hash があるだけで入力を取得・照合済みとはしません。生ログの保存状態や取得したものの hash 照合は未確認です。

入力の版・hash は各実験の条件表を正本とします。構築試験の E は空の DL/sstate から、BSP の後続試験はその環境を使います。Buildroot の cold build、Yocto の E の cold build、キャッシュを使う後続試験を混ぜません。失敗行に時刻の欠損がある場合は、そのまま欠損として扱います。固定 SHA や `BR2_REPRODUCIBLE` は、独立した 2 ビルドの bit 単位一致の証明ではありません。

## 今回取り込む検証・監査

| 項目 | 採用する扱い | 根拠と確認方法 |
|---|---|---|
| 最終 `.config` の全体監査 | fragment の合否に加えて全 symbol の差を読む | 544 項目の差。[設定監査の手順](../../BUILD.md#最終カーネル設定の監査)で版・入力・出力を保存する |
| fragment の重複・矛盾検出 | 同値の重複も診断する。EROFS の最後の `n` を維持して先行 `y` を除く | [検証基盤の変更](https://github.com/uist1idrju3i/MSD-Linux/pull/177)。設定値の変更ではなく、矛盾の解消 |
| runner と集計の証拠保護 | 既存出力を拒否。失敗・欠損・初回を分離し、成功した通常起動だけを集計 | 同 PR。Buildroot 同士にも再利用可能。模擬 QEMU の異常系テストと実起動を区別する |
| patch の由来 | 目的、適用元、上流へ未提出であることを記す | 同 PR。固定 Buildroot の [patch-policy](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/docs/manual/patch-policy.adoc) は `Upstream:`、Yocto は `Upstream-Status:`。QA 無効化で回避しない。パッチ本体と適用後のコードは変えない |
| legal-info と SBOM | 生成成功と監査・許諾の確認を分ける | 下の監査範囲に従う。unknown を推測で埋めない |
| 再試行と証拠の保存 | commit、実際のツール版・binary hash、cold/warm、失敗理由を残す | [experiment-record](../../../.agents/skills/experiment-record/SKILL.md)。実行中スクリプトを編集せず、削除前にコピーと hash を照合する |

検証基盤のコードは別 PR です。この文書だけでは検査器の変更が適用されたことにはなりません。利用する版に上の変更が入っているかを確認します。

## 製品設定を変えずに残す候補

| 候補 | 今回の判断 | 再検討に必要な根拠 |
|---|---|---|
| dm-verity | 製品への導入は保留 | [S15 の記録](../../experiments/README.md)と[脅威モデル](../security/threat-model.md)。破損検出、root hash の信頼点、A/B 復帰、実機の時間・メモリ費用を別々に検証する。カード全体交換への対策とはしない |
| systemd | BusyBox init を維持 | [init の調査](../userspace/README.md)。必要な機能、同じサービスを含むイメージ、起動・RAM・保守コストを比較する |
| musl | 現行ツールチェーンを維持 | [libc の調査](../userspace/README.md)。全パッケージ・BSP の互換性と実機でのサイズ・起動・機能を検証する |
| RAUC / SWUpdate / Mender | `msd-update` と tryboot を置き換えない | [更新方式](../storage/README.md)。RPi の既成例が U-Boot 前提である点と、CM0 tryboot の実機検証を解決する |
| Yocto の `read-only-rootfs` / overlay | クラスや init 処理をそのまま移植しない | [現行の書き込み経路](../storage/write-policy-and-s3.md)と実コードを照合し、seedrng・鍵・ログ・更新の永続性と電断を試す |
| EROFS | 現行 SquashFS を維持 | [FS 比較](../storage/filesystem-candidates.md)。同じ内容・圧縮条件でのサイズ、起動、RAM、実機電断を比較する。ビルドシステムの変更は採用根拠にしない |
| cramfs | 従来の不採用を維持 | [構築・起動の記録](../../experiments/2026-10-31-cramfs-rootfs.md)。サイズとファイル・gid・時刻の制約を覆す新しい根拠はない |
| 任意ドライバーのモジュール化 | 一律に変更しない | [ハードウェア対応表](../hardware-spec.md)と[縮小の調査](../boot/kernel-size.md)。LCD・入力・rootfs の起動依存と各 driver の built-in/module 制約を確かめる |
| SPDX | CycloneDX を形式だけ置き換えない | 配布先の要求と、target/host/firmware/外部ツールチェーンの収録範囲を先に定義する |
| 再現ビルド | 達成済みとはしない | 同じ固定入力を独立した clean 出力で 2 回構築し、成果物 hash を比較。差があれば時刻・署名・生成物を調査する |

## ライセンスと SBOM の監査範囲

現行 [build workflow](../../../.github/workflows/build.yml) は `make -C output legal-info` を実行し、`show-info` を `generate-cyclonedx` へ渡します。[固定 Buildroot の説明](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/docs/manual/legal-notice.adoc)も、生成内容はレシピの宣言に依存し、配布者の確認が必要としています。SPDX の文書数と CycloneDX の component 数を同じ尺度にはしません。

配布する commit・構成と結び付けて、次を確認します。

1. `output/legal-info/README`、target/host の manifest、ソース、ライセンス文を読む。warning、unknown、再配布対象外を列挙する。
2. Bootlin の外部ツールチェーンは取得した版と配布元の対応するソース・ライセンスを照合する。実験の manifest の `unknown` を、許諾済みや GPL だと読み替えない。Buildroot 自体と外部ツールチェーンのソースなど、legal-info に自動収録されない範囲を補う。
3. [M5 パッケージ](../../../package/m5stack-cardputerzero/m5stack-cardputerzero.mk)の kernel module の GPL-2.0 と、`cardputerzero,st7789v_lcd.bin`、`bmi270-init-data.fw`、keymap の unknown を区別する。COPYING があるだけで全ファイルの配布許諾を確認したことにはしない。
4. Raspberry Pi firmware、Wi-Fi/Bluetooth firmware、overlay、独自スクリプト、適用パッチを実イメージと照合する。`PROPRIETARY` は拒否とも許諾確認済みとも同義ではなく、個別の条件を読む。
5. `sbom.cdx.json` の対象 component と実際の rootfs・boot 領域・更新 bundle を照合する。SBOM、ソース提供物、ライセンス文、監査上の未解決事項を一緒に保存する。

この整理では新しい legal-info/SBOM の生成や配布許諾の確定はしていません。新形式への変更より、まず収録範囲と unknown の解消根拠が必要です。
