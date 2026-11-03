# 起動の終点定義と測定手法

[調査の索引](../../../RESEARCH.md) / [構築手順](../../BUILD.md)

以下は公開資料と過去の検証の記録です。数値の測定条件と未確認事項を保ち、現在の配備設定や実機での検証とは区別します。

## 15. 起動の終点定義と測定手法

### 15.1 終点の定義
主指標は **T_shell**（LCD にプロンプトが表示され、キー入力できる時点）、副指標は **T_init**（init / PID 1 が完了マーカーを書く時点）とします。両方を記録し、T_shell をユーザー向け起動時間として扱います。

| 案 | 終点 | 利点 | 欠点・衝突 |
|---|---|---|---|
| **A / T_shell** | LCD にシェルのプロンプトが表示され、かつキー入力が受け付けられる時点 | 主指標。体感に直結します。 | M5IOE1 → backlight → LCD → keyboard の依存を終点前に読み込む必要があります。 |
| **B / T_init** | init（PID 1）が終点マーカー（例: `/run/boot-done`）を書く時点 | 副指標。起動処理を一貫して比較できます。 | プロンプトが表示される時刻とはずれるため、T_shell と併記します。 |
| **C** | T_shell と T_init の両方を測り、差を遅延読込の効果として記録 | 両指標を比較できます。 | 測定の手間が増えます。 |

【推測・未実施】T_shell は内蔵 keyboard の `/dev/input/event*` 出現時刻と getty / shell が tty を開いた時刻を `/proc/uptime` で記録します。prompt の描画完了は LCD 更新遅延を内部時刻で捉えられないため、高速撮影で電源投入から表示までを外部測定します。T_init は完了マーカーの `/proc/uptime`、GPIO toggle、UART の時刻記録を照合します。printk のタイムスタンプも各起動段階の観測に使う案です。内部時刻と外部測定の差は LCD 描画遅れとして記録します。KittenLabs も GPIO toggle で測定しています。
どの案でも、測定条件(始点=電源投入、`console=`・quiet の有無)を固定する。

### 15.2 測定ツール

| 手法 | 事実 | 出典URL | 確認度 |
|---|---|---|---|
| `initcall_debug` | カーネルパラメータ。initcall 実行をトレース | https://docs.kernel.org/admin-guide/kernel-parameters.html | 一次 |
| `printk.time=1` / `CONFIG_PRINTK_TIME` | printk 各行に時刻を付ける(bcm2711_defconfig は `PRINTK_TIME=y`) | https://docs.kernel.org/admin-guide/kernel-parameters.html / https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L1778 | 一次 |
| `scripts/bootgraph.pl` | `dmesg \| perl scripts/bootgraph.pl > out.svg`。`initcall_debug` を付けた dmesg から initcall の SVG を作る | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/scripts/bootgraph.pl#L13-L33 | 一次 |
| `systemd-analyze` | `blame` / `critical-chain` / `plot`（SVG）。man page は、`blame` が並列起動のため待ち時間を反映しないと注意しています。`Type=simple` のサービスは即時起動扱いのため blame に出ず、キュー待ちも含まれません。 | https://man7.org/linux/man-pages/man1/systemd-analyze.1.html | 一次 |
| bootchart(ユーザー空間) | systemd-bootchart の man7 ページは 404(今回取得できず)。**bootchart の一次情報は未取得** | (取得失敗:https://man7.org/linux/man-pages/man1/systemd-bootchart.1.html → HTTP 404) | 未取得 |
| strace | 実使用のシステムコール/ファイル open の洗い出しに使う(man) | https://man7.org/linux/man-pages/man1/strace.1.html | 一次 |
| ブート時 ftrace | カーネルパラメータ/bootconfig でブート時から tracing を有効化できる | https://docs.kernel.org/trace/boottime-trace.html / https://docs.kernel.org/admin-guide/bootconfig.html | 一次(存在)/ CM0 での有効性は未確認 |
| RPi 公式の区間分割 | EEPROM → GPU FW → カーネル展開・初期化 → initramfs → rootfs mount → systemd。CM0 には EEPROM がないため区間が異なります。 | https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-010196-WP-1-Optimising%20boot%20time%20on%20Raspberry%20Pi%20single-board%20computers.pdf | 一次 |

### 15.3 再現性（推測・未実施）
- 固定:同一個体・同一 SD・同一 firmware/bootcode・同一 cmdline。変えるのは 1 要素だけ。
- コールドブート N≧15、**1 回目は別扱い**、中央値と p90 を記録。電源は同一(バッテリ残量・USB 給電の別を固定)。
- 測定ビルドと量産ビルドの差(printk/initcall_debug の出力量自体が時間を伸ばす)を明記。シリアル出力はコンソール速度が起動時間に影響するため、**測定時のコンソール設定を固定**(`console=` と quiet の有無)。
- 数値の条件（機種・カーネル・始点終点）を必ず併記し、異なる条件の値を合成しません。
