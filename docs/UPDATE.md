# A/B 更新と書き込み領域

## パーティション構成

SD カードは MBR 形式です。p4 を拡張パーティションにし、p5 以降を論理パーティションとして配置します。

| 番号 | 用途 | 内容 |
|---|---|---|
| p1 | 起動選択、FAT 16 MiB | `autoboot.txt` と `bootcode.bin` |
| p2 | ブート A、FAT 64 MiB | firmware、`kernel8.img`、DTB、overlay、A 用 `cmdline.txt` |
| p3 | ブート B、FAT 64 MiB | firmware、`kernel8.img`、DTB、overlay、B 用 `cmdline.txt` |
| p4 | 拡張パーティション | p5〜p7 を格納 |
| p5 | rootfs A、SquashFS 256 MiB | A 用 rootfs |
| p6 | rootfs B、SquashFS 256 MiB | 初期イメージでは A と同一 |
| p7 | `/data`、ext4 64 MiB | 更新状態と永続データ |

p1 を初期ブートパーティションとして使い、`autoboot.txt` を置く構成です。BCM2837 のブートフロー資料では ROM が SD などのブート元から `bootcode.bin` を探すと説明されているため、これも p1 に含めます。公式資料の A/B 例は、p1 に `autoboot.txt`、p2/p3 に firmware と kernel を置いています。ブート可能な FAT パーティションには `start.elf` が必要とされるため、p2/p3 に `start_cd.elf` と `fixup_cd.dat` を配置する設計です。

p1 には `autoboot.txt` と `bootcode.bin` の2ファイルだけを置きます。公式資料は p1 に追加の firmware ファイルが必要とは明記していません。p1 に bootcode を置く根拠と資料の限界は上記のとおりで、実機での確認が必要です。

初期の `autoboot.txt` は次のとおりです。

```ini
[all]
tryboot_a_b=1
boot_partition=2
[tryboot]
boot_partition=3
```

資料では `boot_partition` は 1 始まりで、`autoboot.txt` は初期ブートパーティションに置く仕様です。`tryboot_a_b=1` でも p2/p3 の `config.txt` と `kernel8.img` を使い、rootfs は各 `cmdline.txt` の `root=` で指定します。A は `/dev/mmcblk0p5`、B は `/dev/mmcblk0p6` を指す設定です。

参照資料は Raspberry Pi の [autoboot.txt と A/B 更新](https://www.raspberrypi.com/documentation/computers/configuration.html#autoboot-txt) と、リポジトリ外にある `documentation/asciidoc/computers/raspberry-pi/bootflow-legacy.adoc` です。後者は BCM2837 の ROM がブート元を調べて `bootcode.bin` を読み込む流れを説明していますが、「最初の FAT パーティション」と明記した記述は確認できませんでした。p1 への配置は、初期ブートパーティションを selector とし、SD の先頭に置く構成として採用しています。実機での起動確認が必要です。

## 更新の流れ

`msd-update status` は `/proc/device-tree/chosen/bootloader/partition` と `tryboot` を読み、現在の A/B スロットと試験起動中かどうかを表示します。値は 32 bit big-endian です。BusyBox の `od` には `--endian=big` がないため、`od -An -v -t x1` でバイト列を読み、16 進数として変換します。

更新 bundle は、次の 3 ファイルをルートに含む tar アーカイブです。manifest は `sha256sum` と同じ形式で、各イメージの SHA-256 を記載します。

```text
rootfs.squashfs
boot.vfat
manifest
```

`boot.vfat` はインストール先スロット用に作成します。p2 に入れる場合は `cmdline.txt` の root を p5、p3 に入れる場合は p6 に指定してください。`install` はブートイメージの中身を書き換えず、イメージ全体を非アクティブパーティションへ転送します。

実行コマンドの例です。

```sh
msd-update status
msd-update install /data/update.tar
msd-update try
```

`install` は稼働中の rootfs/boot を維持し、非アクティブスロットを更新先にする処理です。bundle のメンバー名と SHA-256 を確認後、`dd conv=fsync` でイメージを転送します。同じバイト数を読み戻し、ハッシュが一致することを確かめます。双方の検証後、`/data/msd-update/installed` に試験対象を記録する流れです。電子署名の検証は未実装です。

`try` は検証済み更新の状態ファイルと `autoboot.txt` のスロット指定が一致する場合だけ、`reboot '0 tryboot'` を実行します。firmware は p1 の `[tryboot]` で指定されたブート領域を一度だけ選びます。次回の通常起動では tryboot が解除されるため、試験中に再起動しても未コミットの更新へ固定されません。

tryboot 中に rootfs が SquashFS、`/data` が ext4 でマウント済みか、`MSD-Linux ready` marker があるかを確認するのが `S99msd-health` の役割です。条件成立後は `msd-update commit` が p1 を読み書き可能でマウントし、`autoboot.txt.new` を書いてから `autoboot.txt` への rename を実行します。BusyBox の `fsync` applet で新しいファイルと p1 のディレクトリを同期し、rename 後に p1 と更新状態のディレクトリを同期します。確認に失敗すると設定を変えずに通常再起動し、旧スロットに戻る設計です。早期起動が停止した場合に備え、BusyBox watchdog を `-T 15 -t 5` で起動します。

## 書き込み可能な領域

rootfs は Zstandard 圧縮 SquashFS で読み取り専用です。`/tmp`、`/run`、`/var` は tmpfs です。起動時に p7 の ext4 を `fsck.ext4 -p` で確認します。ext4 の superblock magic がなく、パーティション全体がゼロの場合だけ `mkfs.ext4` で初期化します。未知の非空パーティションはフォーマットせず、起動を停止する設計です。初期化または fsck の後に `/data` へマウントします。マウントオプションは `noatime,data=journal,errors=remount-ro` で、`commit=` は kernel の既定値を使います。

`/etc` は overlayfs で構成します。`/etc` と `/data/etc` を lower layer、`/run` 上の tmpfs を upper/work layer とするため、通常の `/etc` への変更は再起動で消えます。再起動後も残す設定ファイルは `/data/etc` に保存してください。サービスがその場所を直接参照しない場合は、個別の bind mount などを追加します。

p7 は初期イメージで 64 MiB です。初回起動時の自動拡張は未実装で、後続課題です。

## 検証範囲

| 方法 | 確認する内容 | 制約 |
|---|---|---|
| `tests/msd-update/run.sh` | DT 値の読み取り、commit の拒否条件、2↔3 の切り替え、bundle の SHA-256 検証、非アクティブスロットへの書き込み | 一時ディレクトリ上のホストテスト。実デバイスの電源断耐性は確認しない |
| `board/cardputerzero/qemu/test-ab.sh` | QEMU で p6 を rootfs として起動し marker を確認 | 追加したスクリプト。QEMU は Raspberry Pi GPU firmware の tryboot を実行しないため、firmware の A/B 選択や自動フォールバックを確認しない |
| CardputerZero 実機 | firmware tryboot、rootfs 起動、watchdog、更新中の電源断、LCD・キーボード | 実機での検証が必要 |

## 電源スイッチに関する未対応事項

`vendor/m5stack-linux-dtoverlays/modules/CardputerZero/cardputerzero-v5-overlay.dts` の `powerfail` node は GPIO 6 の falling-edge IRQ を `cardputerzero,powerfail-suo` driver に渡します。確認した overlay には gpio-keys または userspace input event の定義がありません。driver の `powerfail_suo.c` は SysRq-U を実行し、backlight と disabled GPIO を扱います。既存 IRQ と競合する userspace handler は追加せず、入力イベントの仕様が確認できるまで TODO とします。
