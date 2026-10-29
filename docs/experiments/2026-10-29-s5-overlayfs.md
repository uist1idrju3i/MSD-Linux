# S5: OverlayFS の振る舞い（現行 `/etc` overlay 構成）の QEMU 検証

現行の `/etc` overlay（`lowerdir=/data/etc:/etc`、`upperdir=/run/etc-overlay/upper`=tmpfs、`workdir=/run/etc-overlay/work`）で、write・whiteout・rename・lower 直接書き込みの 4 点を QEMU で確認した。製品構成の変更はなし。

## 条件

- QEMU 11.1.2、`raspi3ap`、512 MiB、`QEMU_COPY_IMAGE=0`、1 GiB padding 済みの複製 image。
- ゲスト内でシリアルコマンドを実行し、結果をログに記録。

## 手順と生の値

| 操作 | 結果 |
|---|---|
| `touch /etc/aaa-s5` | `/run/etc-overlay/upper/aaa-s5` が生成（write → tmpfs upper） |
| `rm /etc/hostname` | upper に `c--------- 0,0` の whiteout（`hostname`）が生成 |
| `mv /etc/fstab /etc/fstab.bak` → 復元 | `rename-ok`（merged 内 rename は upper で完結） |
| `echo lowerwrite > /data/etc/lower-test` → `cat /etc/lower-test` | `lowerwrite` と読めた（lower への直接書き込みが merged view に反映） |
| `findmnt -no FSTYPE,OPTIONS /etc` | `overlay rw,relatime,lowerdir=/data/etc:/etc,upperdir=/run/etc-overlay/upper,workdir=/run/etc-overlay/work` |
| `/proc/filesystems` | `nodev overlay` |

## 結論

- 現行構成で whiteout・rename・新規作成はすべて tmpfs upper で完結し、lower（squashfs `/etc` と `/data/etc`）は起動中に書き込まれない。
- `/data/etc` への直接書き込みは稼働中の merged view に即時反映された。永続設定の書き込み経路として機能するが、Linux の overlayfs 文書は「マウント中の lower の変更は未定義」としているため、運用時の書き込みは maintenance window 中など参照がないタイミングに限定するのが安全。
- 永続化が必要な設定は「`/data/etc` への書き込み + merged への即時反映」で実現可能。A/B 更新で image 側 `/etc` の既定値が `/data/etc` の同名ファイルに隠される問題は、schema/version migration か個別管理の設計判断が残る（[調査文書](../research/readonly-data-and-fs.md) の【推測】項目）。
- xattr の挙動は BusyBox に `setfattr`/`getfattr` がなく未検証。

## 失敗した試行・注意

- xattr 系はツール不在で試せず。必要なら attr パッケージの追加が必要。
- QEMU のみで実機は未確認。tmpfs upper の内容は電断で失われる（設計どおり）。

## 未検証

- xattr、opaque ディレクトリ、A/B 更新時の lower 差し替え（`lowerdir` の先頭変更）の挙動。
- full-root overlay・`/data` bind/symlink 案との比較は構成変更を伴うため別途。
