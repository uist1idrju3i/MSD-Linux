# 保存領域・ファイルシステム・実行時検証の比較

[代替比較](README.md) / [更新framework](updates.md) / [署名と信頼境界](signing.md) / [RESEARCH](../../../RESEARCH.md)

## 基準と判断の範囲

rootfsの圧縮方式、書換え可能なデータ領域、設定の重ね合わせ、実行中の整合性検証は別々に選びます。read-only、圧縮、checksum、署名は同じ保護ではありません。cramfs、romfs、ext2/3、XFS、NILFS2、bcachefs、exFAT等を含む[候補の全景](../storage/filesystem-candidates.md)を踏まえ、ここでは現行構成からの移行と検証を詳しく扱います。

ext4、F2FS、Btrfs、LUKS2、dm-integrityのformat・mount・checksum等の個別optionは[filesystem option調査](../storage/filesystem-options.md)に分けました。

2026-11-02にMSD/Linuxの`c0214b380c046100592cd427ab3013347dff1758`、Buildrootの`8b238854d909c9cce32ef9671d968b03e323b55d`を基準に調べました。固定kernelは`b3495ea401d709af0701a85babcba5e3d788a602`です。新しいfilesystem構成のbuild・実行・サイズ測定は本リポジトリでは試していません。過去のQEMU試験は当時のrevision・binaryの証拠として参照します。

## 現行の保存と起動の契約

| 対象 | コードで確認した構成 | 置換で一緒に扱うもの |
|---|---|---|
| `/` | SquashFS + zstd。Buildrootのextreme compression、既定128 KiB block。fstabは`squashfs ro` | kernel組込み、image名、genimage、更新bundle、`S99msd-health`のfilesystem判定 |
| A/B | MBRのboot-a/bは各64 MiB、rootfs-a/bは各256 MiB。p1は共通bootsel、p4は拡張領域 | rootfsだけでなくboot payload・selector・状態の整合。共通p1まで冗長になったとはしない |
| `/data` | p7のext4。新規imageは4 KiB block。`noatime,nodev,nosuid,data=ordered,errors=remount-ro` | fsck、grow、更新journal、seedrng、設定保存、復旧tool |
| 初期化 | `S02msd-data`は空領域だけをformatし、未知の非空領域を拒否。fsckの終了値0/1だけを許す | F2FS等への変更時に既存媒体を誤formatしない判定とmigration |
| `/etc` | `/data/etc:/etc`がlower、`/run/etc-overlay`がtmpfs上のupper/work | lower先頭の永続設定が新版の既定値を隠す。設定schemaと信頼する鍵の置き場 |
| 揮発領域 | `/run`・`/tmp`・`/dev/shm`はtmpfs。`/data`は通常時もrw | RAM上限、電源断で失う状態、再起動後も必要な状態 |

根拠は[defconfig](../../../configs/msd_cardputerzero_defconfig)、[genimage](../../../board/cardputerzero/genimage.cfg)、[fstab](../../../board/cardputerzero/rootfs-overlay/etc/fstab)、[data初期化](../../../board/cardputerzero/rootfs-overlay/etc/init.d/S02msd-data)、[overlay](../../../board/cardputerzero/rootfs-overlay/etc/init.d/S03msd-etc-overlay)、[health](../../../board/cardputerzero/rootfs-overlay/etc/init.d/S99msd-health)です。指定値の確認であり、今回新しいimageを生成した結果ではありません。

## rootfsの候補

| 候補 | 機能と本機で比較する利点 | 背反・統合条件 | 提案 |
|---|---|---|---|
| SquashFS | read-only圧縮image。現行のtool・boot・更新試験を再利用できる | codec、block size、展開buffer、random readの費用。圧縮比だけで起動を順位づけない | 現行を比較の基準に残す |
| EROFS | read-only、圧縮、tail packing、fragment、dedupe、pclusterの調整 | kernelとmkfsのfeature・codecの組合せ、xattr、image metadata、展開RAMを照合する。現行fragmentは`CONFIG_EROFS_FS`を無効にする | SquashFSと同じrootfs corpusで実験候補 |
| ext4をro mount | 非圧縮のroot、既存e2fsprogsと共通化できる | sparse fileの見かけのサイズと配信・partition上のサイズは別。journal/recoveryの動作まで含めて評価する | 圧縮費用との比較対照 |
| Btrfs・snapshot型root | CoW、snapshot等を構成できる | snapshot単独では署名、古い版の拒否、boot切替を満たさない。kernel/tool、容量、復旧手順が増える | 機能が必要なら再検討。現行A/Bの単純な置換ではない |
| tmpfs / initramfs中心 | 永続rootへのruntime writeを減らせる | RAM圧迫と起動時の展開、電源断時の状態喪失。initramfsを増やすとboot payloadも変わる | 小さな復旧環境等の用途限定 |

固定Buildrootには`fs/erofs/`と`host-erofs-utils`があります。専用choiceは無圧縮、LZ4HC、LZMA、customです。専用のzstd symbolがなくてもcustom文字列を渡せますが、指定できることと固定host tool・kernelで読めることは別です。dedupe、fragments、all-fragments、ztailpacking、pcluster、圧縮hintも調整でき、再現build用に時刻・UUIDを指定する経路があります。[Config.in](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/fs/erofs/Config.in)と[recipe](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/fs/erofs/erofs.mk)を基準に、生成したsuperblockと実効設定を照合します。

既存の[S12 SquashFS試験](../../experiments/2026-10-25-s12-squashfs-codec.md)ではxzのサイズ削減と起動の遅延を記録し、lz4/lzo等の差が事前基準に届かなかった条件も残しています。差なしは同等性の証明ではありません。EROFS比較はその試験では実行していません。旧kernel・測定用rootfsのQEMU結果を、現行製品や実SDの速度として転載しません。

## `/data`と設定の候補

| 候補・方針 | 比較する効果 | 必要な条件・残る弱点 |
|---|---|---|
| ext4継続 | journal、fsck、growの現行手順を維持できる | applicationのatomic rename・fsync・directory fsync、SDのflush挙動、電源断を別に確認。`data=ordered`だけで任意の更新がatomicになるわけではない |
| F2FS | block flash向けのlog構造、checkpoint、roll-forward。`fsync_mode`等を比較できる | microSD内蔵FTLとGCの重なり、空き容量、書込み量、mount/fsck時間、tool/RAM。新しいという理由でも、警告があるという理由だけでも一律に採否を決めない |
| Btrfs | checksum、CoW、snapshotで設定の世代管理を構成できる | 単一SDでchecksumがあることは修復可能性や発行者認証を保証しない。容量・RAM・回復費用を測る |
| raw flash向けUBIFS/JFFS2等 | MTD上のeraseblockやbad blockを扱う | SDは通常block device + FTLであり、raw NAND向けの管理をそのまま適用する対象ではない。別のraw flashを追加するなら再評価 |
| `/data`を通常ro | 書込み窓とwriterを限定できる | seedrng、更新状態、設定、growを排他的に扱う設計が必要。失敗時にrwのまま残る経路、他writer、再起動を試す。現行には未実装 |
| `/etc`全体のoverlayを縮小 | 古い既定値による上書きを減らし、永続化する設定を列挙できる | 新旧schemaのmigrationとrollback。imageに固定するtrust anchorと利用者設定を分ける |

`noexec`追加も比較できますが、interpreterがデータを読むことまで一律に禁止する仕組みではありません。`nodev`・`nosuid`・`noexec`は所有者・mode・MAC policy・書込み権限の代わりにはしません。`/data/etc`が公開鍵等を隠せる構造についても、許可する永続設定を限定し、image側の信頼する情報を可変設定と同じ層へ置く必要があるか再検討します。

## tmpfs・zramとメモリーの費用

[tmpfs](https://docs.kernel.org/6.18/filesystems/tmpfs.html)はvirtual memory上のfilesystemで、swapがあれば退避され得ます。[zram](https://docs.kernel.org/6.18/admin-guide/blockdev/zram.html)は圧縮RAM上のblock deviceで、filesystemそのものではありません。zramをswapとして使う案と、zram上へfilesystemを作る案も別です。いずれも電源断後の永続化には使えません。

tmpfsのsize・inode上限、zramの`disksize`・`mem_limit`・codec、OOM、圧縮しにくい入力、CPU時間と実使用RAMを一緒に比較します。圧縮RAMが無制限に増やせるわけではなく、SDへのbacking/writebackを使うなら「RAMだけでSDへ書かない」という評価を引き継ぎません。rootfs展開、page cache、更新download、署名検証との同時負荷で測ります。既存の[zram・zswap検討](../storage/power-loss.md#66-追加質問-q1完全-read-only-でも-zramzswap-は使えるか)は過去の設定案であり、今回の有効化・実行の証拠にはしません。

## dm-verityとfs-verityの違い

| 機構 | 検証する対象 | MSD/Linuxで残る契約 |
|---|---|---|
| bundle署名とSHA-256 | 配信時のmanifestとimage全体 | 書込み後や次回起動以降の読取りを監視するものではない |
| dm-verity | read-only block deviceのhash tree。読んだblockを検証 | root hashをどこから信頼するか、slot別tree・offset、boot引数、kernel組込み、破損時の停止・rollback |
| fs-verity | 対応filesystem内の個々のread-only file | 認証したfile digestと、そのfileを必ず使うpolicy。未保護fileへの差替え・rename・pathの扱い |
| filesystem checksum | metadata/dataの破損検出等。方式ごとに範囲が違う | 発行者の署名やtrusted root hashを自動では提供しない |

[Linux 6.18のdm-verity](https://docs.kernel.org/6.18/admin-guide/device-mapper/verity.html)と[fs-verity](https://docs.kernel.org/6.18/filesystems/fsverity.html)を別に読みました。fs-verityのbuiltin署名はkernelが扱える方式とPKCS#7/X.509の制約があり、資料はEd25519のuserspace検証を別案として説明しています。現行raw Ed25519をkernelのbuiltin検証へ無変換で渡せるとはしません。

既存の[dm-verity QEMU試験](../../experiments/2026-10-21-qemu-dm-verity.md)は正常起動と改変拒否、初回の失敗・誤検知・追試を記録しています。ただし未署名のboot引数を変えられる攻撃者はroot hashも差し替えられます。RAUCの`verity` bundleも配信bundleの検証方式であり、製品rootfsのverified bootを自動で完成させるものではありません。

## 採用順と試験条件

1. root、data、設定、鍵、更新状態の所有者とwriterを決めます。SD上の全状態を巻き戻せる物理攻撃まで守るかを、boot chain・hardwareの限界とともに定めます。
2. SquashFSとEROFSを独立したclone・出力先で作り、同じfile corpus・owner・mode・xattr・device node・symlink・licenseを保持します。変えるcodec等と採否の閾値を先に登録します。
3. hostサイズ・hash・再現性、QEMUの全slot起動、上限RAM、アプリのrandom read、実SDの起動・書込み・電源断を別々に測ります。5回以上の反復、A/A、負の対照、失敗を[実験一覧](../../experiments/README.md)から辿れる形で残します。
4. image名・fstab・kernel・health・更新manifest・partition上限・復旧を一つの変更として試します。filesystemのmount成功だけで更新移行を合格にしません。
5. dm-verityを選ぶ場合は、tree・root hashの認証、古いslot、破損検知とrollback、読み出されない破損、誤ったoffset・salt、FEC有無を試験条件へ加えます。`ignore_corruption`等で成功に見せません。

当面の比較基準はSquashFS + ext4のままです。EROFSと、設定overlayの縮小、dm-verityを別々の実験候補として残します。上流の機能説明は本機の性能保証ではなく、採用決定でもありません。

## 出典・license・監視

Linuxの[SquashFS](https://docs.kernel.org/6.18/filesystems/squashfs.html)、[EROFS](https://docs.kernel.org/6.18/filesystems/erofs.html)、[overlayfs](https://docs.kernel.org/6.18/filesystems/overlayfs.html)、[ext4](https://docs.kernel.org/6.18/filesystems/ext4/overview.html)、[F2FS](https://docs.kernel.org/6.18/filesystems/f2fs.html)、[EROFS mkfs](https://erofs.docs.kernel.org/en/latest/mkfs.html)の必要な節と固定Buildroot recipeを照合しました。kernel 6.18資料と最新mkfs資料は同じ版ではありません。取得時刻・原文hashは[sources.json](sources.json)に残します。

kernel、filesystem tool、圧縮library、image生成toolは別の配布物です。Buildrootの`legal-info`とfile単位のlicense、static link、host再配布、SBOMを確認します。kernelの監視だけでe2fsprogs・erofs-utils・squashfs-tools・codecの更新を網羅したとはしません。候補を採用する変更では、[依存監視の限界](../operations/sbom-coverage.md)も同時に解消する必要があります。
