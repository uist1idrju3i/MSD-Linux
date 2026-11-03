# filesystem共通mount flagとmount option

[保存領域の調査へ戻る](README.md) / [filesystem option一覧](filesystem-options.md)

## 範囲と出典

調査日は2026-11-04です。Linuxの固定版はRaspberry Pi Linux 6.18.59、最新版はmainline 7.4-rc1です。util-linuxは固定版2.41.5、最新版2.42.4、BusyBoxは固定版と最新版を1.38.0として照合しました。kernelの共通superblock flag、`mount(2)`と`mount_setattr(2)`のflag、util-linuxのfilesystem-independent option、BusyBoxのmount option tableを対象にします。filesystem固有のoptionは各filesystem表を参照してください。

| option | 意味 | 既定値 | 固定版で使えるか | 最新版の変化 | MSD/Linuxでの扱い | 理由 | BusyBox mount |
|---|---|---|---|---|---|---|---|
| `ro` `rw` `MS_RDONLY` `MOUNT_ATTR_RDONLY` | 読み書き可否 | mount構成による | 可 | 同 | 現行のまま | `/data`のread/write要件を保ち、保守時のread-only化は利用者が開始する操作に限る。 | `ro`,`rw`あり |
| `sync` `async` `MS_SYNCHRONOUS` | file dataの同期書き込み | async | 可 | 同 | 実験で比べる | `sync`は各writeを待つがSDへの書き込み量・回数とwearを増やす可能性がある。利用者操作中の耐久性試験で量と電断窓を測る。 | `sync`,`async`あり |
| `dirsync` `MS_DIRSYNC` | directory変更を同期する | 無効 | 可 | 同 | 実験で比べる | directory更新を同期する範囲と、無操作時に追加writeが起きない条件を実測する。 | あり |
| `lazytime` `nolazytime` | timestamp更新を遅延する/戻す | filesystem既定 | 可 | 同 | 実験で比べる | dirty timestampのflush時機を測り、無操作時のSD writeを生まない設定を選ぶ。 | 両optionあり |
| `atime` `noatime` `nodiratime` `diratime` `relatime` `norelatime` `strictatime` `nostrictatime` `MS_NOATIME` `MS_NODIRATIME` `MS_RELATIME` `MS_STRICTATIME` `MOUNT_ATTR_NOATIME` `MOUNT_ATTR_NODIRATIME` `MOUNT_ATTR_RELATIME` `MOUNT_ATTR_STRICTATIME` `MOUNT_ATTR__ATIME` | access time更新の頻度を選ぶ | filesystem/kernel既定 | 可 | 同 | 実験で比べる | accessによるmetadata writeを抑えつつ、利用者機能がatimeを要するか確認する。 | option: `atime`,`noatime`,`nodiratime`,`diratime`,`relatime`,`norelatime`,`strictatime`,`nostrictatime` |
| `iversion` `noiversion` | inode versionを更新/停止する | 無効 | 可 | 同 | 既定のまま | file change notification等の要件がなく、無操作時のmetadata更新を避ける。 | table外 |
| `mand` `nomand` | mandatory lockを有効/無効にする | 無効 | 可 | 同 | 既定のまま | 製品にmandatory lock利用がなく、互換性を変える理由がない。 | 両optionあり |
| `nosuid` `suid` `MS_NOSUID` `MOUNT_ATTR_NOSUID`、`nodev` `dev` `MS_NODEV` `MOUNT_ATTR_NODEV`、`noexec` `exec` `MS_NOEXEC` `MOUNT_ATTR_NOEXEC` | set-id、device node、実行の可否を制限/許可する | mount構成による | 可 | 同 | 現行のまま | `/data`から実行する必要のない領域は制限を維持し、起動・更新の実測で必要な範囲だけ選ぶ。 | option: `nosuid`,`suid`,`dev`,`nodev`,`exec`,`noexec` |
| `nosymfollow` `follow` `MS_NOSYMFOLLOW` `MOUNT_ATTR_NOSYMFOLLOW` | symlink追跡を禁止/許可する | 許可 | 可 | 同 | 実験で比べる | `/data`の参照互換性を確認し、symlink経由の意図しないアクセスを制限できる場合に使う。 | `nosymfollow`あり |
| `bind` `rbind` `remount` `move` `MS_BIND` `MS_REC` `MS_REMOUNT` `MS_MOVE` | mount treeをbind、再帰bind、再mount、移動する | 指定時のみ | 可 | 同 | 既定のまま | mount namespaceの構築に必要な場合だけ起動処理で使う。 | `bind`,`remount`,`move`あり |
| `shared` `private` `slave` `unbindable` `rprivate` `rshared` `rslave` `runbindable` `MS_SHARED` `MS_PRIVATE` `MS_SLAVE` `MS_UNBINDABLE` | mount propagationを設定する | kernel既定 | 可 | 同 | 既定のまま | namespace伝播の要件がなく、既定のmount treeを維持する。 | propagation optionあり |
| `defaults` `silent` `loud` `quiet` `noauto` `nofail` `user` `users` `loop` `swap` `sw` `comment` | util-linux mount/fstabの制御option | command/fstab指定による | 可 | 同 | 現行のまま | 起動時に不要なdeviceをmountしない。`nofail`等は失敗時の起動動作を変えるため、明示したfstab entryに限る。 | BusyBox table外。fstab専用項目は個別確認 |
| `MS_SILENT` | mount error messageの表示を抑えるAPI flag | 指定時のみ | 可 | 同 | 既定のまま | 診断を隠す必要がなく、起動時の失敗理由を確認できるようにする。 | table外 |
| `MS_BIND` `MS_MOVE` `MS_REMOUNT` `MS_REC` `MS_SHARED` `MS_PRIVATE` `MS_SLAVE` `MS_UNBINDABLE` `rec` | `mount(2)`のnamespace操作flag | API呼び出し時のみ | 可 | 同 | 既定のまま | kernel APIのflag名であり、fstab optionとは区別する。使用箇所が追加された時に呼び出し単位でレビューする。 | table外 |
| `MOUNT_ATTR_IDMAP` | mountにuser namespace id mappingを付ける | 無効 | 可 | 同 | 除外 | `/data`のowner mapping要件がなく、利用者・service間の権限境界は別に設計する。 | table外 |

## 製品での選択

BuildrootのBusyBox設定は`CONFIG_MOUNT=y`と`CONFIG_FEATURE_MOUNT_FLAGS=y`です。Buildroot defconfigは`BR2_PACKAGE_UTIL_LINUX_MOUNT`を選択していません。BusyBoxのmount option tableとutil-linuxの共通option一覧は同一ではないため、BusyBoxで表にないoptionを使う実装にはしません。optionの実機対応は最終imageとmount結果で確認します。

`sync`等の同期指定は利用者の操作中に完了するためAGENTS.md §10に合う場合があります。一方、SDへのwrite回数・量とwearを増やす可能性は推測です。performanceだけで候補を除外せず、write量と電断窓を測ります。

## 出典

- [Linux固定版 fs_context.c](https://git.kernel.org/pub/scm/linux/kernel/git/raspberrypi/linux.git/tree/fs/fs_context.c?id=b3495ea401d709af0701a85babcba5e3d788a602)、[namespace.c](https://git.kernel.org/pub/scm/linux/kernel/git/raspberrypi/linux.git/tree/fs/namespace.c?id=b3495ea401d709af0701a85babcba5e3d788a602)
- [Linux v7.4-rc1 fs_context.c](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/fs/fs_context.c?h=v7.4-rc1)、[namespace.c](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/fs/namespace.c?h=v7.4-rc1)
- [util-linux v2.41.5 mount(8)](https://github.com/util-linux/util-linux/blob/v2.41.5/sys-utils/mount.8.adoc)、[v2.42.4](https://github.com/util-linux/util-linux/blob/v2.42.4/sys-utils/mount.8.adoc)
- [BusyBox 1.38.0 mount.c](https://git.busybox.net/busybox/tree/util-linux/mount.c?h=1_38_stable)
