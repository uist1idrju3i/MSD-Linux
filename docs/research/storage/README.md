# 保存領域・電源断・A/B更新の調査

[調査の索引へ戻る](../../../RESEARCH.md)

現在のコード、資料を取得した時点の比較、過去の実験、未実施の案を分けて読みます。SDカードへ書き込む操作は[導入手順](../../INSTALL.md)、既存の更新操作は[A/B更新手順](../../UPDATE.md)が正本です。この調査の再配置で製品設定・更新形式は変更していません。

## 現在の実装と、まだ確かめていないこと

| 対象 | コードで確認できる内容 | 確認の限界 |
|---|---|---|
| SDの配置 | [genimage.cfg](../../../board/cardputerzero/genimage.cfg)はMBR、`align = 4M`。p1 selector、p2/p3 boot、p4の中のp5/p6 rootfs、p7 dataを配置する。 | 指定だけでは実カードのerase/AU、FTL、速度改善を確認したことにはならない。 |
| filesystem | rootfsはSquashFS。新規のdata imageはext4を`-b 4096`で作る。 | 既存カードの割当単位を変換する処理とは別。実カードの電断・耐久性は未確認。 |
| 可変領域 | [fstab](../../../board/cardputerzero/rootfs-overlay/etc/fstab)は`/data`をext4、`data=ordered`で定義する。[S02msd-data](../../../board/cardputerzero/rootfs-overlay/etc/init.d/S02msd-data)が検査・mountし、[msd-data-grow](../../../board/cardputerzero/rootfs-overlay/usr/sbin/msd-data-grow)が拡張を扱う。 | 通常起動で`/data`をread-onlyにするpolicyは未実装。手順を保存したことを実機試験としない。 |
| 設定のoverlay | [S03msd-etc-overlay](../../../board/cardputerzero/rootfs-overlay/etc/init.d/S03msd-etc-overlay)は`/data/etc`をlower、`/run/etc-overlay`をupper/workにする。 | 永続設定が新imageの既定値を隠す問題と信頼境界は[権限設計](../security/README.md)で扱う。 |
| 更新 | [msd-update](../../../board/cardputerzero/rootfs-overlay/usr/sbin/msd-update)がinactiveなA/B payloadと`/data/msd-update`の状態を扱う。[S99msd-health](../../../board/cardputerzero/rootfs-overlay/etc/init.d/S99msd-health)が試行起動を自動commitする。 | GitHub Releasesの発見・TUF検証clientは未実装。firmwareのtryboot・電断からの復帰は実機未確認。 |

古い配置の表にある「現行（整列なし）」と開始セクター32,769は、引用しているCI imageを調べた時点の記録です。上の`align = 4M`とは時点が異なり、過去の値を書き換えていません。生成物を調べた範囲は[ハードウェア・BSPの確認記録](../../experiments/2026-11-02-hardware-artifact-audit.md)、試験の現在地は[S1–S17台帳](../verification/experiment-catalog.md)を参照します。

## 読む目的から選ぶ

| 確かめたいこと | 本文 |
|---|---|
| partitionとFATの位置、FTLとの境界 | [配置とフラッシュ境界](layout-and-flash.md) |
| ext4 formatter、割当単位、小さいファイルの測定 | [割当単位と小さいファイル](allocation-and-small-files.md) |
| discard、SDバス、実カードで測る条件 | [媒体と測定計画](media-measurements.md) |
| mountとwriter、未実装の書き込み窓、S3の条件と結果 | [書き込みpolicyとS3](write-policy-and-s3.md) |
| Linux 6.18のFS候補と他OSの設計例 | [filesystem候補](filesystem-candidates.md)。最新の採否比較は[代替技術](../alternatives/filesystems.md) |
| format、feature、mount、checksumなどの個別option | [filesystem option調査](filesystem-options.md)。ext4の[mount option](filesystem-options-ext4-mount.md)と[formatter・保守tool](filesystem-options-ext4-tools.md)、F2FSの[sysfs option](filesystem-options-f2fs-sysfs.md)、Btrfsの[progs追加option](filesystem-options-btrfs-progs.md)も参照 |
| K/P/S17系列のURL・逐語抜粋・適用範囲 | [共通の出典表](filesystem-sources.md) |
| 故障注入で何を模擬し、何を確認できないか | [S17の当初計画](fault-injection-s17.md)と[試験台帳](../verification/experiment-catalog.md) |
| FTL、電源遮断、FS耐性、powerfailの資料 | [電源断耐性の調査](power-loss.md) |
| RAUC等の過去の比較とS10の経緯 | [A/B設計の履歴](ab-design-history.md)。現在の比較は[更新framework](../alternatives/updates.md)と[TUF/Uptane](../alternatives/update-metadata.md) |
| 回復案の未実装部分、watchdog、S11の成功・失敗条件 | [復旧案とwatchdog](recovery-and-watchdog.md) |
| 端末がReleaseを確認する将来の方式 | [自己更新の設計](../release-client/README.md)と[Release・署名鍵](../release-client/release-security.md) |

## 記録を残す単位

配置・割当・電断・A/Bを読む目的ごとに分け、表・コード・必須条件・否定・失敗記録は途中で切っていません。K/P/S17の出典表は一つに保ち、元から参照していたFS比較表との関係を明示しました。更新frameworkの当時の版や「未着手」の記述を、現在の採用版・実装状況へ読み替えません。

再配置の判断、基準commitからの本文全範囲の照合、過去のCSVの保存確認と改変対照は[保存性の検証記録](../../experiments/2026-11-02-storage-document-layout.md)へ記録します。これは文書の照合であり、過去の性能実験やQEMU・実カード試験の再実行ではありません。
