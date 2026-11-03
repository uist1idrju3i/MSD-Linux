# filesystemの設定項目と候補

[保存領域の入口へ戻る](README.md) / [調査の索引](../../../RESEARCH.md)

## 前提

MSD/Linuxの基準は`origin/main` `83bd5cf599bb74d91da0332c2a8d9f25ff9946c6`、Buildrootは`8b238854d909c9cce32ef9671d968b03e323b55d`、調査日は2026-11-03です。固定版の一次資料と現行設定を比較しました。本リポジトリでは、候補設定のbuild、QEMU、実機試験をしていません。

固定版はLinux 6.18.59（Raspberry Pi Linux `b3495ea401d709af0701a85babcba5e3d788a602`）、e2fsprogs 1.47.4、f2fs-tools 1.16.0、btrfs-progs 6.10、cryptsetup 2.8.7です。最新版は同日確認時点のupstream mainline Linux 7.4-rc1（最新stable 7.3.1）、e2fsprogs 1.47.4、f2fs-tools 1.16.0、btrfs-progs 7.3、cryptsetup 2.8.8です。release tagの有無は上流のtag一覧で確認しました。kernelの「最新版」は開発版mainlineを指し、安定版の番号も併記します。

| 主題 | 固定版の比較表 | 表の対象 |
|---|---|---|
| ext4 | [format・feature](filesystem-options-ext4.md#formatとfeature)、[mount・永続設定](filesystem-options-ext4-mount.md)、[点検と調整](filesystem-options-ext4.md#点検と調整)、[formatter・保守tool](filesystem-options-ext4-tools.md) | e2fsprogsのmkfs、mke2fs.conf、tune2fs、e2fsckとkernelのfeature・mount option |
| F2FS | [F2FS](filesystem-options-f2fs.md)、[sysfs option](filesystem-options-f2fs-sysfs.md) | mkfs、feature、mount/sysfs、fsck、resize、f2fs_io |
| Btrfs | [Btrfs](filesystem-options-btrfs.md)、[progs追加option](filesystem-options-btrfs-progs.md) | mkfs、feature、mount option、checksum、single-device DUP |
| LUKS2・dm-crypt | [LUKS2とdm-crypt](filesystem-options-luks.md) | luksFormat、open、refresh、共有option、kernel target flag |
| dm-integrity | [dm-integrity](filesystem-options-dm-integrity.md) | integritysetup、kernel target argument、LUKS2との組合せ |

各表の「固定版で使えるか」は指定された固定版での可否です。「最新版だけ」は固定版で有効とは扱わず、`版上げで使える候補`と記します。MSD/Linuxでの扱いは`実験で比べる`、`現行のまま`、`既定のまま`、`除外`から選びます。選択肢のない項目や製品設定の未確認箇所は、未確認と明記します。

## 現行ext4設定

現行比較の基準は、[genimage.cfg](../../../board/cardputerzero/genimage.cfg)のdata image `-b 4096`、[S02msd-data](../../../board/cardputerzero/rootfs-overlay/etc/init.d/S02msd-data)の`mkfs.ext4 -F -b 4096 -L data`、`fsck.ext4 -p`、mount option `noatime,nodev,nosuid,data=ordered,errors=remount-ro`、および[/etc/fstab](../../../board/cardputerzero/rootfs-overlay/etc/fstab)の同じmount optionです。ext4の現行値は、反対の測定結果がない限り変更候補にしません。

kernel fragmentでは`CONFIG_EXT4_FS=y`、`CONFIG_BTRFS_FS`は無効です。defconfigではe2fsprogs、fsck、resize2fsが選択されています。F2FS、dm-crypt、dm-integrityを含む最終kernel `.config`は生成していないため、固定kernel sourceに機能があることと製品imageで使えることを同一視しません。

## dataの破損検出

| 方式 | 検出範囲と動作 | 限界 |
|---|---|---|
| Btrfs data checksum | 既定でdataとmetadataをchecksumする。`nodatasum`または`nodatacow`ではdata checksumを使わない。読み出した値が合わなければEIOを返し、scrubで検査する。 | scrubは検査であり、別の有効な複製があるDUP/RAID profileでなければ破損dataを修復できない。DUPの物理的な独立性は媒体依存。 |
| ext4 `metadata_csum` | filesystem metadataをchecksumする。 | file data blockは対象外。 |
| F2FS `inode_checksum`、`sb_checksum` | inodeおよびsuperblockのchecksum feature。`compress_chksum`は圧縮cluster内のraw data checksum検証を有効にする。 | `compress_chksum`はfilesystem全dataのchecksumではなく、圧縮clusterのraw dataに限定される。実機での検出範囲は未確認。 |
| LUKS2 / dm-integrity | sectorごとのtagでblock deviceのdataを検証でき、filesystem形式を問わない。dm-cryptと組み合わせたauthenticated encryptionでは、不一致をI/O errorとして返す。 | journalはwrite throughputをおよそ半分にするとのkernel資料の説明がある。検出機能であり、冗長コピーがなければ修復はしない。 |

## single-device DUPとQEMU

Btrfs upstreamの「DUP PROFILES ON A SINGLE DEVICE」は、論理blockを2か所に書いてもSSDの内部remapやdeduplication、FTLのwear levelingにより物理的な独立コピーが保証されないと説明しています。SD/USB flashではcontrollerが配置を決めるため、DUPは冗長性を保証せず、backupの代わりにもなりません。

QEMUの仮想block deviceでは、Btrfsのprofile作成、checksum不一致や別コピーからの読み出しなど、仮想device上の動作は確認できます。実SDのFTL、controllerのdeduplication、wear leveling、実際の電源断、物理的に独立したcopyの有無は示せません。本調査ではQEMUも実機も試していません。

## 上流の最新版資料

| 対象 | 最新版と出典 |
|---|---|
| Linux mainline / stable | [7.4-rc1 release](https://git.kernel.org/torvalds/h/v7.4-rc1)、[7.3.1 stable release](https://git.kernel.org/stable/h/v7.3.1) |
| e2fsprogs | [v1.47.4 tag](https://github.com/tytso/e2fsprogs/tree/v1.47.4) |
| f2fs-tools | [v1.16.0 tag](https://git.kernel.org/pub/scm/linux/kernel/git/jaegeuk/f2fs-tools.git/tag/?h=v1.16.0) |
| btrfs-progs | [v7.3 release notes](https://github.com/kdave/btrfs-progs/releases/tag/v7.3) |
| cryptsetup | [v2.8.8 tag](https://gitlab.com/cryptsetup/cryptsetup/-/tags/v2.8.8) |

固定版と最新版のoption差分は各subjectの文書に記録します。e2fsprogsとf2fs-toolsは調査時点の最新版が固定版と同じです。kernel 7.4-rc1のF2FS mount documentationでは、固定kernelにない`resizable_tail_secno=%u`を確認しました。これは固定版では利用可能とせず、`版上げで使える候補`として記録します。その他のsource記載の差を完全に機械照合したものではなく、本文で照合範囲を示します。

## 出典と網羅範囲

coverage数は、primary sourceから抽出したtoken、理由付き除外、option列で照合済みのtokenです。1行で複数tokenをまとめる場合があるため、文書行数とは異なります。表の`同`はoption tokenの追加・削除なしを示し、default値の全文比較は未確認です。

| 主題 | 固定版: extracted / excluded / covered | 最新版: extracted / excluded / covered | 出典の範囲 |
|---|---:|---:|---|
| ext4 | 225 / 17 / 208 | 225 / 17 / 208 | format/feature、mount、点検と調整、sysfs/ioctl section |
| F2FS | 212 / 2 / 210 | 226 / 2 / 224 | mkfs, mount, ABI sysfs, fsck/resize |
| Btrfs | 107 / 6 / 101 | 110 / 6 / 104 | mkfs, btrfstune, mount, checksum |
| LUKS2 / dm-crypt | 89 / 3 / 86 | 89 / 3 / 86 | cryptsetup action-scoped optionとdm-crypt target |
| dm-integrity | 51 / 3 / 48 | 52 / 3 / 49 | integritysetupとdm-integrity target |

索引: [保存領域の調査](README.md) / [filesystem候補](filesystem-candidates.md) / [filesystem代替案](../alternatives/filesystems.md)
