# 公開鍵buildと独立署名job

- 状態：host試験と増分build完了。本番job・実機は未確認
- 日付：2026-11-12
- 基準：main `530d91d6ffbc1624a7c05ffc845bd1d811f98a86`上の未commit変更
- 関連：[署名手順](../RELEASE-SIGNING.md)

## 目的と採否の基準

通常buildに本番秘密鍵を渡さず、公開鍵だけをrootfsへ収録します。試験鍵の正常bundleを端末clientで受理し、鍵の欠落・型・不一致、fingerprint、manifest、payload、tar hash、member異常を拒否することを採用条件とします。public-key modeは未署名tarだけを生成し、開発鍵・互換入力も維持します。

機能の成立を確認する試験なので各suiteは1回とし、修正で入力が変わったsuiteだけ再実行します。速度・再現性・実機の結論には使いません。負試験を検査器の対照とします。本番秘密鍵は使いません。

## 条件と手順

`tests/release-signing/run.sh`、`tests/msd-update/run.sh`を開発用Dockerで実行します。既存の`output-openssl-lts`を再利用できる場合は、過去のimagesと開発鍵を別に保存してから、公開鍵modeの増分buildを1回試します。packageのreconfigureや版変更は行いません。

```sh
docker/msd-dev tests/release-signing/run.sh
docker/msd-dev tests/msd-update/run.sh
MSD_UPDATE_PUBLIC_KEY=/work/board/cardputerzero/keys/release-1-public.pem \
    docker/msd-dev make -C output-openssl-lts
```

指定のworkflow・shell・文書検査も行います。採否は終了値だけでなく、rootfsの公開鍵一致、`key-origin=release`、署名済みtarの不在、未署名tarの3 memberを確認して決めます。

## 環境と入力

開発imageは`sha256:47cc0b8cfd878a4fb413c376d52a2b6a9199454c97b1d2aec8df7a3a1b4a8e7d`、内部はDebian 13です。Buildrootは`8b238854d909c9cce32ef9671d968b03e323b55d`、GCC 14.3.0、Linux 6.18.59-v8、genimage 20を再利用しました。packageの再compileはなく、host/target finalize、post-build、rootfsとpost-imageの再生成を行ったwarm出力です。

実際のhost OpenSSLは3.5.9、binary SHA-256は`40c37aa60e4bf41f6cb6701769a397c8cb2017e47d55022f759581371e0bb50d`です。rootfsの確認にはunsquashfs 4.7.5を使用し、そのbinary SHA-256は`8f002a8d695e777618023f55e953f4a042eca78417b58f86dd6584a9b81ccee3`でした。入力diffは実行前に保存し、本番公開物ではなく基準commit上の変更を確認しています。

## 結果

[生の値](2026-11-12-release-signing-job.csv)に増分buildの終了値と生成物のbytes・hashを記録します。署名済みtarと開発鍵は生成されず、未署名tarは`rootfs.squashfs`、`boot.vfat`、`manifest`の通常file 3件だけでした。manifestの内部番号は基準commitの`1794489751`です。各payloadのhashを再計算し、一致を確認しました。

target treeだけでなく、生成したSquashFSから公開鍵と`key-origin`を取り出しました。鍵はcommit対象のPEMとbyte単位で同じで、由来は`release`でした。署名scriptの正例は試験鍵で作り、変更していない端末clientの`install`で署名検証・非active slotへの書込み・読戻し照合まで確認しました。

`tests/release-signing/`は10試験で、欠落・非Ed25519・別鍵、固定公開鍵との不一致、fingerprint、manifest・payload、tar hash、余分・欠落・link等を拒否します。workflowの署名step本文も、公開鍵とfingerprintだけを試験用に置き換えて実行し、0600、削除、PEM fileと秘密鍵headerの検出を確認しました。本番鍵は使っていません。

既存の`msd-update`、`msd-dev`、`version-info`、host-test runnerの7試験も成功しました。actionlintとShellCheckは終了値0、zizmor 1.31.1は新規workflowを含む8本のoffline監査を終了値0で完了しました。

## 初回の失敗と修正

- 初回のpublic-key負試験は、Ed25519秘密鍵PEMを公開鍵入力に指定しても終了値0でした。公開鍵headerの確認と秘密鍵headerの拒否を追加し、同じ負試験で拒否を確認しました。
- actionlintは、Docker内で展開する単一引用符のshellについてSC2016を報告しました。既存buildと同じ明示的な抑制を付けました。workflowの行継続の誤りもdiffで修正し、署名step本文を実行する試験を追加しました。
- host-test runnerの既存試験はsuite集合の追加を検出して失敗しました。新suiteを期待集合へ追加し、既存suiteを除かず再検査しました。
- build後のmetadata採取は最初にshellの引用を誤って実行前に停止しました。引用を直して確認し直し、増分buildは再実行していません。

## 記録と未確認

増分buildログは22,771 bytes、SHA-256は`3b44c58d80b817b1b88037f114d6a99171a3967d98a8de9e9508768ab9e9ae14`です。大きな生成物とログはcommitせず、上記手順で再生成できます。ただし日時等を含む出力hashの再現性を示す試験ではありません。再利用前のimagesと開発鍵は別に保存し、過去の実験記録は変更していません。

GitHub Environmentの承認・Secret読取り、本番署名、Release公開、QEMUと実機の鍵移行は試していません。Environmentの保護は設定確認が必要で、コードの存在や静的検査だけで有効とは扱いません。SD image全体の署名・鍵失効も対象外です。
