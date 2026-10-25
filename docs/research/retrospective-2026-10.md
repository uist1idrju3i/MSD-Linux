# 作業の振り返りと残タスク（2026-10-22）

2026-10-20〜22 の作業（PR #65〜#87）を振り返り、誤りから得た教訓、改善の提案、残っているタスクをまとめます。各実験の条件と生の値は [docs/experiments](../experiments/README.md) にあります。この文書は判断の材料をまとめたもので、新しい測定は含みません。

## 1. 実施したこと

| 分野 | 内容 | 記録・PR |
|---|---|---|
| 文書と運用 | yomiyasu の更新、大きな調査文書の分割、README と公式サイトの更新、CI・Issue・リポジトリ設定の点検 | #65、#66、#67、[点検結果](repo-operations-review.md) |
| QEMU の模型 | GPIO6 の電源断、watchdog のタイマー | #69、#86 |
| 起動時間 | 段階ごとの計測、K1・K2・U1 の比較、K2 の実機比較の計画 | #70〜#73、[起動時間の計測](boot-time-measurements.md) |
| 不具合の修正 | init script の `stop` で起動処理を再実行しない、ローカルソースのパッケージへのパッチ適用 | #68、#77 |
| 小項目の試験 | `/data` の `noexec`、zram、Lynis、BusyBox の静的リンクと applet 削減、dm-verity | #76、#79、#80、#84 |
| CI の高速化 | per-package directories（PPD）の比較と、成果物差の原因の確認 | #78、#81、#83、#85 |
| sysctl・panic・ramoops | hardening 候補、panic 後の再起動、ramoops の記録 | #87 |
| 網羅表 | QEMU で検証できる範囲の分類と実施順 | #74、[シミュレーション検証計画](simulation-plan.md) |

製品の設定を変えたのは #68 と #77 だけです。それ以外の結果は、どれも採否を決めていません（5 節）。

## 2. 誤りと教訓

| 起きたこと | 原因 | 教訓 |
|---|---|---|
| S11 v1 で、再起動後の ready を 0/5 と記録した | 観測を 40 秒で打ち切った。reboot の時点で、reset から ready まで約 29 秒かかると分かっていた | 観測の窓は、既に分かっている所要時間から決める |
| S11 v2 の QEMU が、commit した patch から build したものではなかった | 手で書き換えた source から build した QEMU を image にコピーしていた。commit した patch は QEMU 11.1.2 に当たらなかった | 測る前に、binary の出どころ（image の layer、binary の hash）と commit が対応しているかを確かめる |
| S21 の負の対照（`kernel.sysrq=0`）が、予想に反したように見えた | 判定に使った driver の行は、sysrq の gate より前に出る | 判定に使う行がどこで出力されるかを source で確かめ、負の対照で検証する |
| S21 で P0 のログを上書きした | `docker/msd-dev` は決まった環境変数しか渡さない。runner の選択が既定に戻った | 実験の選択は CLI 引数で渡す。ログや run_id が既にあれば止まるようにする |
| S21 の Y0 の判定が `fail` と記録された | 比較式が `Y0` と `0` を取り違えていた | 判定の結果は、事前登録の判定方法に照らして全列を読む |
| BusyBox の計測が 1 回目で失敗した | BusyBox の `date` が `%N` に対応していない | 対象機の道具の機能を確かめてから使う |
| dm-verity の起動が 2 度失敗した | partition の検出待ち（`dm-mod.waitfor`）と、inittab の `remount,rw` | 既定の設定が新しい構成で何をするかを、先に読む |
| zram の 1 試行を、構文エラーで失敗させた | 実行中に runner を編集した | 実行中の runner は編集しない |
| PPD の 2 回目の `make` が失敗した | `post-build.sh` の seedrng の改名が冪等でない | 採用前に、繰り返し build でも通るかを確かめる（#32） |

どの誤りも、失敗した試行として記録に残し、測定の前に追記（Amendment）を書いてから測り直しました。

## 3. 改善の提案

次の提案は、まだどれも実装していません。AGENTS.md とスキルを変える提案は、計画を確認していただいてから進めます。

1. `run-qemu.sh` が、使った QEMU binary と DTB・image の SHA-256 をログの先頭に出すようにする。測定ごとの出どころを、手作業なしで残せます。
2. 実験の runner を共通の作りにする。選択は CLI 引数で受け取り、既存のログと run_id は上書きしない。S21 の runner と `test-powerfail.sh` には、この作りを入れました。
3. `test-powerfail.sh` の判定（`remount_seen` など）に、保存したログを入力にしたホストテストを足す。いまは parser の単体テストがありません。
4. experiment-record スキルに、次の 2 つの確認項目を足す。
   - 測った binary が commit と対応していること
   - 判定に使う行を、負の対照で検証したこと
5. 製品の採否を決める項目（5 節）を Issue にし、実機で確かめる手順を書く。

## 4. 残っているタスク

### QEMU で検証できるもの

| 項目 | 内容 |
|---|---|
| 温度 | QEMU に温度の property を足し、高温時の動作を試す |
| S15 | QEMU 11.0.2 と 11.1.2、`raspi3b` と `raspi3ap`、plugin の命令数を正式に比べる |
| S10 | 不正・破損・古い bundle で、非 active slot と状態が変わらないことを確かめる |
| S12 | SquashFS の圧縮方式と block size、EROFS。2026-10-25 に圧縮方式と block size を [QEMU で測った](../experiments/2026-10-25-s12-squashfs-codec.md)。差があったのは xz だけで、EROFS は未着手 |
| S1・S14 | カーネル option の本番 sweep（S6 tier B、`quiet`・`lpj=`・PREEMPT、カーネルの圧縮方式を含む） |
| ドライバー | 任意機能のドライバーのモジュール化を icount で比べる |
| S13 | ユーザーランドの `-O2`・`-Os`・LTO |
| ファイルシステム | S16 → S4・S5・S17 |
| ファイルアクセス | 起動時のファイルアクセスを観測し、`mksquashfs -sort` を試す |
| tty の警告 | QEMU の console で出る `tty_open: tty->count` の警告の原因を調べる。2026-10-25 に [原因を確かめた](../experiments/2026-10-25-qemu-tty-count.md)。QEMU 用の DTB で Bluetooth を無効にする案は判断待ち |

### 保守と小さな修正

| 項目 | 内容 |
|---|---|
| 固定版の確認 | check-pins の Trivy の誤検知の修正、Go 1.27.3 とカーネルの pin の更新 |
| seedrng | `post-build.sh` の seedrng の改名を、PPD の繰り返し build でも通るようにする（#32） |
| inittab | 意味のない `mount -o remount,rw /` を外すかを、`/var` の扱いと合わせて決める |
| devcontainer | 計画を出す（実装はしない） |
| 網羅表 | 結果が出るたびに [シミュレーション検証計画](simulation-plan.md) の状態を更新する |

### 実機で確かめるもの

| 項目 | 内容 |
|---|---|
| K2 | ftrace の有無による起動時間の差を、実機で比べる |
| S11 | 実機の watchdog と、watchdog reset 後の slot の選択 |
| ramoops | 実機の watchdog reset のあとも記録が残るか。予約領域と `gpu_mem` が重ならないか |
| `panic_on_oops` | oops を起こす手段（LKDTM）を入れた build で試す |

## 5. 採否の判断を待っている項目

| 項目 | QEMU での結果 | 判断に必要なこと |
|---|---|---|
| PPD | CI の Buildroot step が中央値で 31.7 % 短い。成果物差は埋め込み path の長さだけ | seedrng の修正（#32）。ユーザーの判断で保留中 |
| K2（ftrace を無効にする） | icount の ready が 38 % 短い | 実機での比較 |
| `/data` の `noexec` | 直接の実行だけを防ぐ | 実機と、使うアプリでの確認 |
| zram | zstd・lz4 とも動作した | 実機のメモリの使い方 |
| BusyBox の applet 削減・静的リンク | ready の差は基準未満。静的リンクで busybox は 2.1 倍 | 残す applet の範囲 |
| dm-verity | 改ざんを 5/5 で拒否した | 更新の仕組みと、信頼できる boot の経路の設計 |
| sysctl の hardening（Y1） | 起動、A/B、電源断が通った。`kernel.sysrq=32` で emergency remount は保たれる | 実機での確認 |
| `panic=` の値 | `panic=0` は watchdog による reset、`panic=5` は kernel による再起動 | どちらの経路にするかの方針 |
| ramoops の予約 | QEMU では reset のあとも記録が読めた | 実機での保持と、メモリ配置 |

## 6. 保守項目の状態（2026-10-25）

4 節の「保守と小さな修正」と 3 節の提案について、2026-10-25 に行ったことと、提案にとどめたことをまとめます。

| 項目 | 状態 | 根拠と次の手順 |
|---|---|---|
| 提案 1（QEMU などの SHA-256） | [PR #95](https://github.com/uist1idrju3i/MSD-Linux/pull/95) | `run-qemu.sh` が、QEMU、Image、DTB、image の SHA-256 を先頭に出す |
| 提案 3（電源断の判定のホストテスト） | [PR #97](https://github.com/uist1idrju3i/MSD-Linux/pull/97) | `classify_trial_logs` を足し、保存したログで 7 つの場合を試す |
| 提案 2、4、5 | 未着手 | 提案 4 はスキルを変えるので、計画をお見せしてから進める |
| check-pins の Trivy の誤検知 | [PR #93](https://github.com/uist1idrju3i/MSD-Linux/pull/93) | YAML の引用符を外してから比べる |
| Go 1.27.3 | [PR #96](https://github.com/uist1idrju3i/MSD-Linux/pull/96) | 開発用イメージの actionlint の builder だけを上げる |
| seedrng（#32） | [PR #94](https://github.com/uist1idrju3i/MSD-Linux/pull/94) | 同じ内容のファイルが両方にあるときだけ、古い側を消す。PPD を採るかどうかは別に決める |
| カーネルの pin | 提案にとどめる | 固定している 2341883 は 6.18.57（2026-10-16）。`rpi-6.18.y` の先頭 aeadd6e は 6.18.58（2026-10-18）で、78 commit 先にある。`rpi-6.18.y` は raspberrypi/linux の既定ブランチのまま。上げるときは vendor-update の手順で変更履歴を読み、ビルド、test-boot、test-ab、電源断の試験を通す |
| inittab の `remount,rw` | 外すことにした（2026-10-25 の利用者の判断） | 下に書く。前後の比較は [2026-10-25-rootfs-stay-ro.md](../experiments/2026-10-25-rootfs-stay-ro.md) |
| devcontainer | 計画をチャットで共有した | 計画はリポジトリに置かない |

### 6.1 inittab の `remount,rw`

- 行を足しているのは Buildroot です。`BR2_TARGET_GENERIC_REMOUNT_ROOTFS_RW` の既定は `y` で、defconfig はこの値を書いていません。`system/system.mk` は、`y` なら `/etc/inittab` の `mount -o remount,rw /` を有効にし、`n` ならコメントにします。
- root は SquashFS です。dm-verity の実験（[2026-10-21-qemu-dm-verity.md](../experiments/2026-10-21-qemu-dm-verity.md)）では、通常の SquashFS root ではこの行は何も変えず、read-only の dm device では `-EACCES` で失敗しました。
- `/var` の下は、`/var/lib` の中も含め、すべて `/tmp` か `/run` へのリンクです。どちらも fstab で tmpfs を mount します。root を書き込み可能にしなくても、`/var` に書けます。

提案: defconfig に `# BR2_TARGET_GENERIC_REMOUNT_ROOTFS_RW is not set` を足します。製品の起動の手順が変わるので、採るかどうかを決めていただいてから進めます。採る場合は、test-boot、test-ab、電源断の試験、起動時間（icount の 5 回）で前後を比べ、`docs/experiments/` に記録します。

結果: 利用者の判断で外しました。QEMU では、test-boot、test-ab、電源断の smoke と integrity、icount の起動時間（5 回）に差は見られませんでした。実機では試していません。記録は [2026-10-25-rootfs-stay-ro.md](../experiments/2026-10-25-rootfs-stay-ro.md) にあります。
