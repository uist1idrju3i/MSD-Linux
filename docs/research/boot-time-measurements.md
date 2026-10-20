# 起動時間（実測値と分析）

RESEARCH.md から分割した節です。

## 起動時間（実測値と分析）

CM0 上の Buildroot / MSD/Linux の起動時間は未測定です。下表は対象・条件・計測終点が異なるため、数値を合算・平均しません。

| 数値 | 対象・条件 | 確認度と解釈 | 出典 |
|---|---|---|---|
| GPU firmware 2,112 ms、画面点灯 2.26 s | CardputerZero、M5 の独自 227 KB bare-metal splash。電源投入から ARM 開始まで | M5 自身のベンチマーク記載。Linux 全体の起動時間ではない。一次（Devin が 2026-10-18 に公開資料で確認） | [BENCHMARK.md](https://github.com/CardputerZero/circle-boot-splash/blob/b80d7c6a537c09c1ca233aeffa9c2e8601b113df/app/cardputerzero-splash/BENCHMARK.md#L14-L21) |
| 約 7〜9 s | 同じ M5 資料の「Linux 可用」値 | 実測と概算の合算で終点定義がない。値の信頼性は低い。一次（Devin が 2026-10-18 に公開資料で確認） | [BENCHMARK.md](https://github.com/CardputerZero/circle-boot-splash/blob/b80d7c6a537c09c1ca233aeffa9c2e8601b113df/app/cardputerzero-splash/BENCHMARK.md#L14-L21) |
| ARM 開始 約 6.79 s | Raspberry Pi 3B+。既定 firmware、11.7 MB initramfs、約 10.2 MB kernel8.img | Raspberry Pi の公式 white paper のログで、CM0 にそのまま当てはめられません。一次（Devin が 2026-10-18 に公開資料で確認） | [RP-010196-WP-1](https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-010196-WP-1-Optimising%20boot%20time%20on%20Raspberry%20Pi%20single-board%20computers.pdf) |
| 5.38 → 4.75 → 4.47 s | Zero 2 W + HQ camera。検出機能を無効化し、さらに initramfs を削除した個人ブログの自己申告 | 条件固有の二次情報。kernel 読込のログ差から約 1.54 s と算出した記載には、ログのタイミングが読込完了後である可能性がある。二次 | [KittenLabs](https://kittenlabs.de/blog/2024/09/01/extreme-pi-boot-optimization/) |
| 3.5 s 未満 | Zero 2 W、Buildroot 2024.02.1、GPIO トグルまで。非圧縮 kernel、initramfs なし、USB / sound 等多数を無効、KASLR / Spectre 緩和も無効 | 個人ブログの自己申告。CardputerZero の機能を含まず、条件を同等に比較できない。二次 | [KittenLabs](https://kittenlabs.de/blog/2024/09/01/extreme-pi-boot-optimization/) |
| 約 5.5 s | 古い buildroot-quickpi の README にある値 | 対象・条件が限られ、2018 年から更新停止。参考値のみ。二次 | [README](https://github.com/johschmitz/buildroot-quickpi/blob/2f62ac8b7a1d2edb29aad7008f2c5f38aa5195a5/README.md#L15-L16) |

M5 の約 2.1 秒は小さな bare-metal カーネルの GPU firmware 段であり、通常の Linux kernel / initramfs 読込の下限ではありません。GPU 段が kernel サイズに比例するかは未確認です。Pi 3B+ と Zero 2 W の kernel 読込値は機材・ログ区間が違うため比例関係を推定できません。最初に公式イメージの同一個体で計測し、始点・終点・カーネル・SD を記録します。

### QEMU での段階ごとの測定（2026-10-20）

QEMU（`raspi3ap`、TCG と icount）で、`MSD/Linux ready` までの時間を段階ごとに測りました。QEMU の秒数は実機の秒数ではなく、版どうしの比較にだけ使います。条件、生の値、捨てた試行は [2026-10-20-qemu-boottime](../experiments/2026-10-20-qemu-boottime.md) にあります。計測ハーネスは `board/cardputerzero/tools/bench/boottime/` です。

| 条件 | 通常起動の `t_ready`（icount） | 同（TCG） | 判定 |
|---|---:|---:|---|
| 基準（baseline-a） | 3.037890 s | 24.327573 s | 基準。A/A の差は icount で 0.85 %、TCG で 0.74 % |
| K2: `CONFIG_FTRACE` を無効にする | 1.887120 s（−37.88 %） | 22.944577 s（−5.68 %） | 両モードで基準を満たした。製品の設定は未変更 |
| U1: mdev の起動時の走査を `/sys/devices` に限る | 2.943922 s（−3.09 %） | 23.585238 s（−3.05 %） | 5 % に届かず、改善とはみなさない |
| K1: `CONFIG_KPROBE_EVENTS` を無効にする | 3.067266 s（+0.97 %） | 25.115355 s（+3.24 %） | 不採用。時間が `init_blk_tracer` に移った |

- icount の基準では、カーネルの initcall の合計 1.650 秒のうち `init_kprobe_trace` が 1.102 秒を占めていました。ftrace を無効にすると、initcall の合計は 0.544 秒になりました。
- K2 のあとに icount で残る大きな処理は、`S10mdev`（0.785 秒）と `dwc_otg_driver_init`（0.402 秒）です。
- TCG でだけ長い区間（init の起動直後、swapon、fsck、`msd-data-grow`）は、icount ではどれも 0.07 秒以下でした。QEMU が SD カードなどを模倣する時間だと考えます。TCG の秒数でユーザー空間の I/O の速さを判断しません。
- ftrace を無効にすると、kprobe、blktrace、ブート時の tracing が使えなくなります。製品で無効にするかどうかは、実機で測ってから決めます。

以下に、実機で行う未実施の計測案を示します。

- 主指標は LCD にプロンプトが出てキー入力を受け付ける時点、副指標は init の終点マーカー時点とする。
- GPIO トグル、UART 時刻、`printk.time=1`、`initcall_debug`、`scripts/bootgraph.pl`、ハイスピード撮影を組み合わせる。
- 同じ個体・SD・firmware・cmdline で一度に一要素だけ変更し、コールドブート 15 回以上の中央値と p90 を記録する。初回は別扱いにする。
- 測定用ログは起動時間に影響する。量産ビルドと測定ビルドを区別する。systemd を使う場合、`systemd-analyze blame` は並列起動待ちを反映せず、`Type=simple` のサービスも測れない。

出典: [kernel parameters](https://docs.kernel.org/admin-guide/kernel-parameters.html)、[bootgraph.pl](https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/scripts/bootgraph.pl#L13-L33)、[systemd-analyze](https://man7.org/linux/man-pages/man1/systemd-analyze.1.html)、[Raspberry Pi boot-time white paper](https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-010196-WP-1-Optimising%20boot%20time%20on%20Raspberry%20Pi%20single-board%20computers.pdf)。
