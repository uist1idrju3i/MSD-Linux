# Lynis による製品イメージの QEMU 監査

- 状態: 完了（QEMU のみ。指摘への対応は未実施）
- 日付: 2026-10-21
- 担当: Devin
- 関連: docs/research/simulation-plan.md の小項目「Lynis」、docs/research/security-hardening.md、docs/research/cpu-irq-and-sysctl.md

## 目的

いまの製品イメージを Lynis 3.1.7 で監査し、指摘を「当てはまる」「当てはまらない」「実機で確かめる」に分けます。製品に Lynis を入れるかどうかは、この記録では決めません。hardening index は参考値とし、目標にしません。

## 計画（結果を見る前に書く）

- Buildroot の `lynis` パッケージと同じ 3.1.7 を使う。tarball の SHA-256 は `vendor/buildroot/package/lynis/lynis.hash` の `48d829d0dc2c583a3e838cc09a7190b69a3af844bcb913c7cf9c0226b04b95c5` と一致させる。
- `LYNIS_INSTALL_TARGET_CMDS` と同じ配置で、試験用の rootfs にだけ入れる。BusyBox の設定は変えない（Buildroot のパッケージが select する `BUSYBOX_SHOW_OTHERS` なども入れず、製品のコマンド構成のまま監査する）。
- 試験用 hook（`S99zz-lynis-audit`）が `lynis audit system --quick --no-colors` を実行し、report の `warning[]`、`suggestion[]`、`hardening_index`、`tests_executed` を console に出す。
- 3 回（TCG、`raspi3ap`、512 MiB）。監査は決定的なはずなので、3 回で hardening index と warning・suggestion の集合が同じことを計測器の確認とする。
- 合否はない。完了の条件は、3 回とも report が出て `=lynis= finished` に届くこと。

予備試行のあと、本試行の前に hook を 1 か所直しました。log の集計が時刻付きの行を `uniq` していて役に立たなかったので、KRNL-6000 の対象の sysctl（`Result: sysctl key ... different`）と、飛ばされた試験の件数を出すようにしました。回数と完了の条件は変えていません。

## 条件

| 項目 | 値 |
|---|---|
| 基準の commit | `39ccd234761a76f818c128a19b97fe8af1cf207b` のビルド（[`/data` の `noexec` の試験](2026-10-21-qemu-data-noexec.md)と同じ出力。その後の main の変更は文書だけ） |
| ホスト | Ubuntu 26.04.1 LTS、Linux 7.0.0-38-generic、x86_64 |
| QEMU | QEMU emulator version 11.1.2、machine `raspi3ap`、RAM 512 MiB、TCG |
| 入力の SHA-256 | `Image`: `4bad7a2ed1d31272dbca4c716fc96cff3211ce16266f6713920a4275e98a2505`、`rootfs.squashfs`: `7bc7c5174ae81674ae130edc7583a435aad3e432166642ad948deddbb7b6ab57`、`sdcard.img`: `6cc795a97b2a4133717351b88b5f5006e24ee74e88a9ec5f5fb777b2b5700713` |
| 試験用 rootfs | hook `fe208042af785413f09aae822977232cb13ffe6c6ddec273354150a0f844e5e3`、rootfs `a691c36341a12991d9f23c06c5a8a52ba72ef3af1a64c79df05256df7bae253a`（A・B 両方のスロットに書く） |
| cmdline に足すもの | `msd.lynis=1`（hook はこれがあるときだけ動く） |
| 繰り返し | 本試行 3 回。予備試行 1 回（hook を直す前の版。集計の一致の確認にだけ使う） |

## 手順

```sh
curl -L -o lynis-3.1.7.tar.gz https://github.com/CISOfy/lynis/archive/3.1.7/lynis-3.1.7.tar.gz
sha256sum lynis-3.1.7.tar.gz   # 48d829d0... と一致すること
mkdir -p output/s27/lynis-src && tar -xzf lynis-3.1.7.tar.gz -C output/s27/lynis-src --strip-components=1
docker/msd-dev board/cardputerzero/tools/bench/lynis/make-variant.sh output/s27/lynis output/s27/lynis-src
docker/msd-dev board/cardputerzero/tools/bench/lynis/run-lynis.sh output/s27/lynis /work/output/s27/lynis-logs/run-r1.log
python3 board/cardputerzero/tools/bench/lynis/summarize-lynis.py <serial.log...> > docs/experiments/2026-10-21-qemu-lynis.csv
```

serial のログ（各 200 KiB 前後）はコミットしていません。CSV の `log_sha256` に SHA-256 を残しています。

## 結果

生の値は [2026-10-21-qemu-lynis.csv](2026-10-21-qemu-lynis.csv) です。

| 項目 | r1 | r2 | r3 |
|---|---|---|---|
| 終了値、`finished` | 0、あり | 0、あり | 0、あり |
| 実行した試験 | 204 | 204 | 204 |
| 飛ばされた試験 | 272 | 272 | 272 |
| hardening index | 60 | 60 | 60 |
| warning、suggestion | 1、24 | 1、24 | 1、24 |
| 監査の時間（QEMU を起動してから `finished` まで） | 435 秒 | 422 秒 | 420 秒 |

3 回で、実行した試験の ID の集合、warning、suggestion、sysctl の差分は同じでした（予備試行とも同じ）。

### 指摘の分類

分類は私の判断です。実機や製品の使い方が決まっていない項目は「実機で確かめる」にしています。

| ID | 内容 | 分類 | 理由・次の作業 |
|---|---|---|---|
| AUTH-9308（warning） | single user mode に password がない | 実機で確かめる | 実機のコンソールを誰が使えるかで決める |
| AUTH-9262 | PAM の password 強度の検査 | 当てはまらない | PAM を使っていない |
| AUTH-9328 | 既定の umask を 027 に | 当てはまる | 各 writer が作るファイルの権限を確かめてから |
| FILE-6310 | `/var` を別の partition に | 当てはまらない | rootfs は読み取り専用。`/var/log`、`/var/cache`、`/var/spool`、`/var/tmp` は `/tmp`（tmpfs）への symlink で、`/data` は別の partition |
| USB-1000、STRG-1846 | USB storage・firewire storage の driver を無効に | 実機で確かめる | 使う USB の機能を決めてから。S1・S14 の kernel option の sweep で扱う |
| NETW-3200 | dccp、sctp、rds、tipc が要るか | 当てはまる | 使わないなら kernel から外す。S1・S14 で扱う |
| FIRE-4590 | firewall | 実機で確かめる | ネットワークの使い方が決まってから |
| KRNL-6000 | sysctl が監査の profile と違う（下の表） | 当てはまる | タスク「sysctl 候補と ramoops」で 1 つずつ試す |
| FINT-4350 | file integrity の tool | 当てはまる | rootfs は dm-verity で扱う（小項目の dm-verity） |
| PKGS-7398 | package の脆弱性の監査 tool | 当てはまらない | 実機に package manager がない。ビルド時の確認で扱う |
| NAME-4028、TIME-3104 | DNS domain、NTP | 実機で確かめる | ネットワークと時刻の扱いが決まってから |
| LOGG-2146、LOGG-2154 | log の rotation、外部への転送 | 当てはまらない | `/var/log` は `/tmp`（tmpfs）への symlink で、再起動で消える。転送先もない |
| BANN-7126、ACCT-9622、ACCT-9626、ACCT-9628、TOOL-5002、HRDN-7230 | banner、process accounting、sysstat、auditd、構成管理 tool、malware scanner | 当てはまらない | 小さな機器で常駐させる利点がない |

KRNL-6000 で差があった sysctl を次の表に示します。「実測」は QEMU で読んだ値、「profile」は Lynis の監査の profile が期待する値です。

| sysctl | 実測 | profile | 分類 |
|---|---|---|---|
| `fs.protected_fifos`、`fs.protected_regular` | 0 | 2 | 当てはまる |
| `fs.protected_hardlinks`、`fs.protected_symlinks` | 0 | 1 | 当てはまる |
| `dev.tty.ldisc_autoload` | 1 | 0 | 当てはまる |
| `kernel.dmesg_restrict` | 0 | 1 | 当てはまる（開発中の調べやすさとの兼ね合いを決める） |
| `kernel.kptr_restrict` | 0 | 2 | 当てはまる（同上） |
| `kernel.unprivileged_bpf_disabled` | 2 | 1 | 当てはまる（2 でも非特権の BPF は使えない。1 は戻せない設定） |
| `net.core.bpf_jit_harden` | 0 | 2 | 当てはまる |
| `kernel.sysrq` | 502 | 0 | 実機で確かめる（電源断の処理が SysRq を使うので、調査文書の候補 32 と合わせて確かめる） |
| `kernel.modules_disabled` | 0 | 1 | 実機で確かめる（起動後にもモジュールを読み込むので、読み込みの終わりを決めてから） |
| `kernel.core_uses_pid` | 0 | 1 | 当てはまらない（core dump を残す設計ではない） |
| `net.ipv4.conf.all.accept_redirects`、`net.ipv4.conf.default.accept_redirects` | 1 | 0 | 当てはまる |
| `net.ipv4.conf.all.send_redirects` | 1 | 0 | 当てはまる |
| `net.ipv4.conf.default.accept_source_route` | 1 | 0 | 当てはまる |
| `net.ipv4.conf.all.rp_filter` | 0 | 1 | 当てはまる |
| `net.ipv4.conf.all.log_martians`、`net.ipv4.conf.default.log_martians` | 0 | 1 | 当てはまる |

## 結論

- 製品イメージを Lynis 3.1.7 で 3 回監査し、結果は 3 回とも同じでした（hardening index 60、warning 1、suggestion 24）。
- すぐに対応できそうなのは、sysctl の調整（KRNL-6000）、umask、使わないネットワークの protocol です。どれも、既存のタスク（sysctl 候補、S1・S14）で QEMU で試してから決めます。
- 製品に Lynis を入れる必要はないと考えます。この試験用の手順で、変更のたびに監査し直せます。

## 確認できていないこと

- 飛ばされた 272 件の試験の内訳（コマンドがないため、またはこの環境に当てはまらないため）。一覧は serial のログにあり、CSV には件数だけを残しています。
- 実機での結果（ネットワーク、USB、コンソールの構成は実機で変わります）。

## 失敗した試行と気づいたこと

- 予備試行の hook は、集計が役に立たなかったため上のように直しました。予備試行の結果は CSV に `pilot` として残していますが、表には入れていません。
- 最初の集計では、実行した試験の ID の集合が 3 回で違うように見えました。kernel の `ttyAMA ttyAMA1: tty_open: tty->count(2) != (#fd's(1) + #kopen's(0))` という行が、長い `=lynis=` の行の途中に割り込んでいたためです。`summarize-lynis.py` で割り込んだ行を取り除いてから比べると、3 回とも同じでした。
- この kernel の行は、Lynis を入れていない試験用イメージの起動でも 9 回出ていました。QEMU の console（`ttyAMA1`）の使い方によるものだと考えていますが、原因は調べていません。
