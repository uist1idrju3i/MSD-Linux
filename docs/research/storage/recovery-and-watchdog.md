# 自動復旧の設計履歴とwatchdogの確認範囲

[保存領域の入口へ戻る](README.md) / [調査の索引](../../../RESEARCH.md)

冒頭のスロット・boot counter・判定条件は過去の設計案で、全項目が現在の実装を表すわけではありません。現行の自動commit条件は[A/B更新手順](../../UPDATE.md)と[S99msd-health](../../../board/cardputerzero/rootfs-overlay/etc/init.d/S99msd-health)、現在の回復設計は[自己更新の信頼と復旧](../release-client/trust-and-state.md)で確認します。

後半のwatchdogはコード・QEMU試行・実機未確認を分けた記録です。v1の基準未達、v2の異なる入力、v3の反復結果を一括して成功にせず、同じ本文に残します。QEMUでresetを観測してもfirmwareのtryboot・実機の復帰を証明しません。

## 18. 失敗検知と自動復旧（A/B）

| 要素 | 事実(一次) | 出典URL | CM0 適合 |
|---|---|---|---|
| `autoboot.txt` + `tryboot` | `[tryboot]` フィルターと `tryboot_a_b=1` により、通常の config.txt / boot.img を使いながらパーティション単位で切り替えます。`reboot "0 tryboot"` で 1 回試行し、成功時は autoboot.txt を更新して確定します。再起動した場合は tryboot フラグが自動クリアされ、元のパーティションに戻るとの記載があります。 | https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/autoboot.adoc#L36-L83 | BCM2837 / CM0 での動作は未確認です。CM0 は EEPROM を持たず SD の bootcode / start.elf で起動します。 |
| カーネルウォッチドッグのハンドオーバー | `kernel_watchdog_timeout` はブート時にハードウェアウォッチドッグを OS に引き渡し、OS が給餌しない場合にリセットします。`systemd` の `watchdog.open_timeout` を cmdline で設定します。`BOOT_WATCHDOG_TIMEOUT`（EEPROM）は Pi 4 / Pi 5 のみです。 | https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc#L242-L255 | EEPROM 設定は CM0 対象外です。`kernel_watchdog_*` が BCM2837 firmware で有効かは未確認です。 |
| `kernel_watchdog_partition` | カーネルウォッチドッグが発火した場合、リセット後に指定パーティションから起動します（自動フェイルオーバー）。 | https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc#L262-L271 | BCM2837 / CM0 での動作は未確認です。 |
| bcm2835 内蔵 WDT ドライバ | RPi Linux ツリーに `drivers/watchdog/bcm2835_wdt.c` があります。 | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/watchdog/bcm2835_wdt.c | ファイルの存在を確認しています。 |
| WDT ユーザー空間 API | `CONFIG_WATCHDOG_NOWAYOUT` / magic close により、ウォッチドッグデバイスを close しても停止しない設計が可能です。 | https://docs.kernel.org/watchdog/watchdog-api.html | 一次 |
| systemd との連携 | `RuntimeWatchdogSec` と `sd_notify` の WATCHDOG 通知が利用できます。 | https://www.freedesktop.org/software/systemd/man/latest/systemd-system.conf.html#RuntimeWatchdogSec=<br>https://man7.org/linux/man-pages/man3/sd_notify.3.html | 一次 |

### 18.1 人手の回復モードを設けない設計案（推測、未実装・未測定）
起動完了条件は未決です。LCD にプロンプトを表示してキー入力を受け付ける時点、PID 1 が完了マーカーを書く時点、または両方を使う案では判定条件が異なります。[起動時間の終点](../boot/measurement-methods.md)も参照してください。

1. **スロット:** A / B に加え、必要なら C を工場イメージとして設けます。回復モードとブートメニューは設けず、自動で前のスロットへ戻す案です。
2. **試行:** 新スロットを tryboot（または自前の試行フラグとカウンター）で 1〜N 回だけ起動します。選択した完了条件への到達とアプリの健全性確認を満たした場合に確定し、autoboot.txt を更新します。完了条件は未決です。
3. **失敗検知は 3 段です。** (a) カーネル panic は `panic=N` で再起動します（kernel-parameters に記載）。(b) hung にはウォッチドッグを使います。`kernel_watchdog_timeout` が CM0 で使えない場合に備え、init が `bcm2835_wdt` を直接 open して給餌する経路を用意する案です。(c) 起動後の機能不全は確定前の自己診断で検知します。判定条件が未決で、LCD / キー入力または PID 1 の完了マーカーを使う案があります。ヘッドレスでの判定は困難です。https://docs.kernel.org/admin-guide/kernel-parameters.html
4. **boot counter:** RW の小領域（別パーティション）に連番と CRC を 2 面書きします。N 回連続で完了条件に到達しなければ旧スロットを既定に戻します。確定時だけ書き込み、SD への書き込み回数を最小化する案です。
5. **電源断との整合:** 試行中の電断は未確定状態での再起動となり、最大 N 回の試行後に旧スロットへ戻す想定です。tryboot と再起動による復帰が BCM2837 で動くかは未確認で、必ず戻せるとは言えません。確定時に更新する FAT 上の autoboot.txt も電断で破損する可能性があります。
6. **弱点:** A/B 用 boot パーティション（FAT）は単一障害点です。更新を 1 セクター内に収める方法や検証用コピーを持つ方法は軽減案ですが、FAT 上での有効性は未検証です。firmware（start.elf / bootcode.bin）は A/B 化されないとの情報がありますが、裏付ける公開資料は未確認です。CM0 で firmware を A/B 化する公式手段も未確認です。
7. CM0 向けの公式 A/B 構成は確認できておらず、tryboot は BCM2837 で未検証です。最初の実機試験では tryboot と `kernel_watchdog_*` の動作を確認します。動作しない場合は、段数が増える U-Boot または RAUC custom backend を代替案として検討します。
8. **更新記録の原子性:** 更新物を一時ファイルへ書いて fsync し、rename 後に親ディレクトリも fsync する案です。tryboot=1、選択中のパーティション一致、インストール記録の検証がそろってから更新を確定します。FAT 上の更新動作と実装は未検証・未着手です。

### 現行 watchdog init script の動作

Raspberry Pi の文書は全モデルが `tryboot` を使えると説明しています。これは一度だけ alternate boot を選ぶ再起動ベースの仕組みで、OS が停止したことを自ら検知する機能ではありません。hang から戻すには watchdog による reset か人手の再起動が別に必要です。BCM2837/CM0 の実機での動作は未確認です。【一次】【未確認】[tryboot 文書](https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/raspberry-pi/bootflow-eeprom.adoc)／[autoboot.txt の one-shot 手順](https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/autoboot.adoc)

Raspberry Pi は `kernel_watchdog_timeout` を、ハードウェア watchdog を OS に引き渡す設定として説明しています。OS 側で watchdog を開いて給餌するサービスが必要であり、設定名やドライバーがあることだけでは CM0 でのリセットを証明しません。【一次】【未確認】[watchdog boot option](https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc#L242-L271)

現在の [`S01msd-watchdog`](../../../board/cardputerzero/rootfs-overlay/etc/init.d/S01msd-watchdog) は `watchdog -T 15 -t 5 /dev/watchdog` を実行します。スクリプトにはアプリケーションの健全性判定やログ記録はありません。タイムアウト・給餌周期を含む実際のリセット動作、init script が起動時に実行されること、CM0 watchdog の挙動は実機で確認します。【一次】【未確認】[現行 init script](../../../board/cardputerzero/rootfs-overlay/etc/init.d/S01msd-watchdog)／[BCM2835 watchdog driver](https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/watchdog/bcm2835_wdt.c)

QEMU 11.1.2 TCG の v3 では、commit `c01f6e7` の patch から build した QEMU で 6 mode × 5 回を実施しました。stop / kill9 の marker→reset 中央値は 14.528 秒、17.064 秒であり、reset 後 120 秒以内の second boot ready は各 5/5 回でした。reboot も restart message、reset、ready が各 5/5 回そろい、poweroff は QEMU が status 0 で 5/5 回終了しました。`TERM` は 5 試行とも 60 秒以内に reset せず、BusyBox が magic close `V` を使うという仮説と整合しますが、close の方式自体は確認できていません。v1 は観測窓が不足して基準未達でした。v2 の結果は commit されていない source から build した別 QEMU の参考値として残し、invalid とはしていません。これらは QEMU の結果であり、実機 watchdog の動作は未確認です。QEMU では GPU firmware / tryboot を使えず、watchdog reset 後の slot selection も検証できません。【実験】[S11 QEMU watchdog 実験](../../experiments/2026-10-20-s11-qemu-watchdog.md)
