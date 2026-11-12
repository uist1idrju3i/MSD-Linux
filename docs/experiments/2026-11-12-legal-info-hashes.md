# Linux・M5のlegal-info license hash照合

[実験一覧](README.md) / [Buildrootの依存監査](../research/dependencies/buildroot.md)

## 目的と条件

2026-11-12、`main`の`1ffccae4d0ed5c2a3dc9ccc03cee4fbb46865169`を基準に、#225で観測したLinuxのlicense hash欠落3行とM5のCOPYINGに対するWARNING 1行を解消します。採否は、固定原文の一致、同じ出力で対象4行が消えること、manifestが不変であること、改変した各licenseを拒否することで決めます。性能測定ではなく決定的なhash検査なので、`legal-info`は前後各1回とします。

- Buildroot：`8b238854d909c9cce32ef9671d968b03e323b55d`。
- Linux：`b3495ea401d709af0701a85babcba5e3d788a602`の固定archive。M5：`37b42d9451495b5597dd7e50cab502da8028f9c2`のlocal submodule。
- Docker image ID：`sha256:47cc0b8cfd878a4fb413c376d52a2b6a9199454c97b1d2aec8df7a3a1b4a8e7d`。
- 出力は既存の`output-openssl-lts`を再利用しました。host/target OpenSSLは3.5.9の構成です。source、toolchain、設定、binaryは変更せず、reconfigure・full build・QEMUは行いません。
- 変更後の入力は[linux.hash](../../board/cardputerzero/patches/linux/linux.hash)と[M5のhash](../../package/m5stack-cardputerzero/m5stack-cardputerzero.hash)の追加分です。vendor内は編集しません。

両側で実行したコマンドは同じです。`legal-info`は自身で前回のlegal-info出力を作り直すため、変更前のlogとmanifestは変更後の実行前に別途保存しました。

```sh
docker/msd-dev make -C output-openssl-lts legal-info
```

## 固定sourceと検査経路

Linux archiveのSHA-256は既存の`d3857e3906878c52719da06328a2db27784f6fb8055b570e8d8207eef3a12a14`と一致しました。そのarchive内の3 file、既存build tree、固定commitの上流raw fileはbyte単位で一致します。M5は固定submodule、既存build tree、上流raw fileが一致しました。新しいSHA-256の値は上記のhash fileに記載しています。

| 上流原文 | UTC取得時刻（2026-11-12） | bytes | HTTP |
|---|---|---:|---:|
| [Linux COPYING](https://raw.githubusercontent.com/raspberrypi/linux/b3495ea401d709af0701a85babcba5e3d788a602/COPYING) | 13:22:48.317228 | 496 | 200 |
| [Linux GPL-2.0](https://raw.githubusercontent.com/raspberrypi/linux/b3495ea401d709af0701a85babcba5e3d788a602/LICENSES/preferred/GPL-2.0) | 13:22:48.545352 | 18,600 | 200 |
| [Linux-syscall-note](https://raw.githubusercontent.com/raspberrypi/linux/b3495ea401d709af0701a85babcba5e3d788a602/LICENSES/exceptions/Linux-syscall-note) | 13:22:48.775508 | 1,258 | 200 |
| [M5 COPYING](https://raw.githubusercontent.com/m5stack/m5stack-linux-dtoverlays/37b42d9451495b5597dd7e50cab502da8028f9c2/COPYING) | 13:23:22.847576 | 423 | 200 |

初回のM5取得ではrepository名を取り違えて404になりました。`.gitmodules`のURLへ訂正し、上表の固定commitで照合しました。404の取得先を根拠には使いません。

`BR2_GLOBAL_PATCH_DIR`は既存の`board/cardputerzero/patches`です。固定Buildrootの[pkg-patch-hash-dirs](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/package/pkg-utils.mk#L163-L164)と[HASH_FILES](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/package/pkg-generic.mk#L502-L509)により、Linuxは既存の外部`linux.hash`、M5はpackage隣接の`m5stack-cardputerzero.hash`を読みます。

[pkg-generic.mk:1134-1144](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/package/pkg-generic.mk#L1134-L1144)はlocal/overrideにもlicense収集を適用し、[legal-license-file](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/package/pkg-utils.mk#L323-L331)が`check-hash`を呼びます。source archiveの通常ダウンロードを省くことと、license hash検査を省くことは同じではありません。hash欠落の終了値3はこのhelperで許容されますが、hash不一致の終了値2は失敗します。

## 結果

[測定CSV](2026-11-12-legal-info-hashes.csv)に終了値、ERROR/WARNINGの行数、logのbyte数とSHA-256を記録しました。変更前後とも終了値0ですが、変更前の終了値0をhash確認済みとは扱いません。

変更前：

```text
ERROR: No hash found for COPYING
ERROR: No hash found for LICENSES/preferred/GPL-2.0
ERROR: No hash found for LICENSES/exceptions/Linux-syscall-note
WARNING: no hash file for COPYING
WARNING: the Buildroot source code has not been saved
WARNING: toolchain-external-bootlin-2025.08-1: cannot save license (TOOLCHAIN_EXTERNAL_BOOTLIN_LICENSE_FILES not defined)
```

変更後：

```text
COPYING: OK (sha256: fb5a425bd3b3cd6071a3a9aff9909a859e7c1158d54d32e07658398cd67eb6a0)
LICENSES/preferred/GPL-2.0: OK (sha256: 8780e78a1a737e127f25a65f6d95269bffd36158dc261114de7859b490bfc5aa)
LICENSES/exceptions/Linux-syscall-note: OK (sha256: 8e378ab93586eb55135d3bc119cce787f7324f48394777d00c34fa3d0be3303f)
COPYING: OK (sha256: ee5808b032a67f587d3541099d46de34f5bec8cd5976114ba07f1299ee6001ff)
WARNING: the Buildroot source code has not been saved
WARNING: toolchain-external-bootlin-2025.08-1: cannot save license (TOOLCHAIN_EXTERNAL_BOOTLIN_LICENSE_FILES not defined)
```

target manifest全体は変更前後でbyte単位に一致しました。対象2行から次の列を抜粋します。M5のLICENSE列は改行せず一つの値です。unknownをCOPYINGのhashで解消したという意味にはしません。

| PACKAGE | VERSION | LICENSE | LICENSE FILES | SOURCE ARCHIVE |
|---|---|---|---|---|
| linux | custom | GPL-2.0 | COPYING LICENSES/preferred/GPL-2.0 LICENSES/exceptions/Linux-syscall-note | linux-b3495ea401d709af0701a85babcba5e3d788a602.tar.gz |
| m5stack-cardputerzero | 37b42d9451495b5597dd7e50cab502da8028f9c2 | GPL-2.0 (kernel modules), unknown (cardputerzero,st7789v_lcd.bin), unknown (bmi270-init-data.fw), unknown (tca8418_keypad_m5stack_keymap.map) | COPYING | m5stack-cardputerzero-37b42d9451495b5597dd7e50cab502da8028f9c2.tar.gz |

同じDocker内で4 fileを一つずつ`support/download/check-hash FILE NAME HASH_FILE`へ渡し、原文が終了値0になることを確認しました。別の作業用copyの末尾へ`\nchanged\n`を追加すると、4 fileとも終了値2で拒否されました。実sourceやvendorの原文は改変していません。

## 残す警告と範囲外

- Buildroot source未保存は[Makefile:874](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/Makefile#L874)で無条件に通知します。単純なconfig変更では閉じません。固定Buildrootのsource、適用patch、外部tree・設定等の構築資料を別途収集し、配布物と対応付けて保存する必要があります。
- Bootlinは固定archiveに対応するlicense原文と内包物の対応付けが必要です。[公式source・licenseの経路](../research/dependencies/buildroot.md#ライセンス脆弱性の残件)を調べ、収集・展開した実fileとhashに基づいてLICENSE_FILESを定義する作業であり、存在を確認していないCOPYINGを設定して警告だけ消すことはしません。
- M5のfirmware等のunknown、全license・対応ソース・再配布条件、実binaryの完全SBOMは未解決です。今回のhash成功は法的認定や実機動作の確認ではありません。
