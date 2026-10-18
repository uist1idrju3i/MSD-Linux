# 調査の前提・ハードウェア・候補

# 引継ぎページ(H)— 最初にここだけ読めば全体が分かるように書いています

> 読み方:H.1〜H.9 は要約で、根拠・出典 URL・確認度は各章(括弧内の章番号)にあります。「確認済み」は一次情報(コミット固定のソース、公式文書、API)を GET して確認したもの、「推測」「見立て」は作成者の推論です。**ここで「確定」と書くのは事実だけで、設計・方針・名前はすべて山城さんの判断待ち** です。

## H.1 目的と要件
- **目的**:M5Stack CardputerZero(Raspberry Pi CM0 = BCM2837、RAM 512MB、microSD)向けに、**超高速起動・突然の電源断への耐性・A/B OTA・CLI 専用**のカスタム Linux(「ファームウェア」)を作るための**開発着手前の調査**(1.1 節)。実機は未入手、ビルドは未実施。
- **要件**:ユーザー発言を番号付きで整理した **R1〜R27(0 章の表)**。主なもの:R1 超高速起動(数秒)/ R2 電源断耐性(完全読み取り専用が安全という認識)/ R3 CLI のみ / R4 常に 2 つ以上のイメージ(A/B)と失敗時復旧 / R5 M5 公式ドライバを使う / R6 まだコンパイルしない / R10 最新カーネルも比較(速くなるなら LTS にこだわらない。リアルタイム要件なし)/ R11〜R13 カーネル極小化と LCD・キーボードの遅延読込可、回復モード・ブートメニュー不要 / R14 カーネルログを SD に残す / R18 全機能維持(BusyBox・init・systemd)、将来 SSH/VPN / R21 名前は調べてから(決めるのは山城さん)。
- **R 同士の緊張関係(未決)**:R12(LCD・キーボードも遅延読込可)と、v4 が置いた「終点=LCD にプロンプト+キー入力可」の定義は**両立しません**(15.1 に A/B 両案、11.4 に決定待ち事項)。

## H.2 一次情報で確認済みの事実(設計の決定ではない)
| # | 事実 | 章 |
|---|---|---|
| 1 | 公式イメージの「2.1 秒」は M5 の自己申告で、**227KB の独自小型カーネルを読む構成の「ARM 起動まで」**。公式イメージ全体の起動時間ではない | 1.8, 5.1 |
| 2 | `powerfail_suo` が実行するのは **`handle_sysrq('u')` のみ**。`'i'`/`'s'` と `kernel_power_off` はコメントアウト | 6.3, 16.2 |
| 3 | **M5 の既定 DT(公式 DT `bcm2710-rpi-cm0.dts`)では `serial0` は mini-UART(`uart1`)を指す**:`serial0 = &uart1`、`serial1 = &uart0`(PL011、GPIO30〜33=BT)。**GPIO14/15(EXT 14P の物理ピン 12/14)に実際に出る UART の種別は M5 の overlay と config.txt で変わりうるため未確認(UN-19)**。公式 pi-gen はビルド時に `console=serial0,115200` を除去し、`enable_uart=1` は M5 の Makefile 経由で設定(最終 config.txt は未検査) | 19.1 |
| 4 | **mender-convert の README は「Raspberry Pi 3(64bit bookworm)」を公式サポート構成(Core)に載せている**。Mender Client 6.1(2026-10)はサポート中。v4 の Mender に関する対象外という記述は**誤り**(CM0 自体の記載・実機動作は未確認) | 7.1, 7.4 |
| 5 | **OpenSSH の既定暗号は `chacha20-poly1305@openssh.com` が先頭**(AES-GCM ではない)。OpenVPN 2.7 の `--data-ciphers` 既定は `AES-256-GCM:AES-128-GCM:CHACHA20-POLY1305`(ChaCha20-Poly1305 が使える場合) | 21.2, 21.3 |
| 6 | **PQ 鍵交換**:OpenSSH 10.5p1 の既定 KEX 先頭は `mlkem768x25519-sha256`、Dropbear 2026.94 は MLKEM768・SNTRUP761 が既定で有効(GCM は無効)、マニュアル上の OpenVPN 2.7 `--tls-groups` 既定には ML-KEM が無いが、OpenSSL 3.6.4(Buildroot 2026.08)の既定グループは先頭が X25519MLKEM768(t1_lib.c L209)で、実効既定は OpenSSL 版依存・実接続は未確認、WireGuard は任意の事前共有鍵のみ | 21.5 |
| 7 | **alias unmap**:導入と revert はともに v7.2-rc1、**再適用は v7.3-rc1**(v7.2 には入っていない)。`rpi-7.2.y` は影響なし、`rpi-7.3.y` は再適用後のコードを含む | 20.5 |
| 8 | `mksquashfs -sort`:**優先度が高いファイルほど先に書かれる**(通常ファイルのみ対象)。`mkfs.erofs --sort` は**tar 入力用** で、ディレクトリ入力の読込順最適化には使えない。EROFS は **`-z` を指定したときだけ圧縮**(FAQ の「既定 LZ4」は「圧縮する場合」の話) | 16.4 |
| 9 | M5 の `panel-mipi-dbi-m.c` は `drm/clients/drm_client_setup.h` を include し、このヘッダは **rpi-6.12.y に無く rpi-6.18.y にある**(raw GET 404/200) | 5.7 |
| 10 | SR9900A は USB ID `0fe6:9900` が `r8152.c` の ID 表にある(sr9700/sr9800 の表には無い)。ただし SR9900A の実 ID が 0fe6:9900 かは公式資料で未確認 | 14.3 |
| 11 | Canonical の「Zephyr 26.04 LTS」発表は **2026-09-21**(ubuntu.com ブログ。対象は MCU 級デバイス)。CM0 で動く根拠は見つかっていない | 3, 4 章 |
| 12 | 最新状態(2026-10-18 20:59 JST):M5 main **7551854**、pi-gen(cardputerzero_v1.0)**791a985**、rpi-6.18.y **2341883(6.18.57)**、rpi-7.2.y **61d3371(7.2.11)**、rpi-7.3.y **6634f17(7.3.0-rc7)**。**kernel.org の mainline は 7.3-rc7(2026-10-12)で、7.3 final は未公開** | 8, 20 章 |
| 13 | 外部の遅い起動報告は原因が別:CachyOS の遅延は**BIOS で TPM を無効化して解消**(投稿者報告)、Omarchy #6996 は **Omarchy 4.0.0-1 / Linux 7.1.8** で `initramfs_async=0` と約 266MiB の initramfs が絡む x86 の事例。いずれも CM0 に外挿不可 | 20.1 |

## H.3 推奨案と選択肢(暫定。方針は山城さんの合意待ち)
- **推奨(見立て)**:Linux ベース、Buildroot を第一候補・Yocto を代替、カーネルは rpi-6.18.y をコミット固定、rootfs は SquashFS(または EROFS)ro + overlayfs + 小さな ext4 RW、A/B は MBR + tryboot/autoboot.txt + RAUC custom(**tryboot の CM0 動作は未検証**)(11.1)。
- **二者択一・未決の設計論点**(**どれも「確定」ではない**。11.3 に一覧):
  1. 起動の終点:(A)LCD+キー入力可まで / (B)userspace の init 到達までを終点とし LCD・キーボードは終点後に遅延読込(15.1)
  2. rootfs:SquashFS か EROFS(16.4。実機で 2 構成を比較する案)
  3. init:systemd 最小化 / BusyBox init+eudev / 自作 init(16.2)と libc:glibc / musl(17.5)
  4. A/B 方式:tryboot+RAUC custom / U-Boot 系(Mender・RAUC)/ Rugix(7 章)
  5. カーネル:6.18.y(PREEMPT=y・VOLUNTARY 選択可)か 7.2/7.3(LAZY/FULL のみ)(20.2〜20.3)
  6. 開発中ログ:案 3(ext4 に書き、電断試験時は専用領域/pstore へ切替)(19.2〜19.3)
- **着手前に山城さんの判断が要る事項**は 11.4 に集約。

## H.4 未決・未確認(理由付き)
| 項目 | 理由 | 章 |
|---|---|---|
| BCM2837(CM0)で tryboot/autoboot.txt/`kernel_watchdog_*` が動くか | 実機未入手。RPi 文書は Pi 4/5 を主に記述 | 7.2, 18 |
| 起動時間(ベースライン・各最適化の効果)、SquashFS vs EROFS、無圧縮 vs gzip カーネル | 実機未測定。公表値は条件が違い合成不可 | 5.2, 10.2 |
| BCM2837 が AES/SHA 命令を載せていないことの一次仕様、SSH/VPN の CM0 実測(PQ 鍵交換の実行時間を含む) | A53 の Crypto Extension がオプション(追加ライセンス)であることは Arm DDI 0501F で確認済み(v9)。BCM2837 の実装有無の一次仕様は未取得で、実機未測定 | 21.1, 21.5 |
| 7.2/7.3 を CM0 で起動できるか(alias unmap 再適用の影響) | コミットメッセージからは RPi3/4 の起動不能が再適用で解消したか読み取れない | 20.5 |
| M5 の名称・ロゴの第三者利用ルール | 公式ガイドラインのページを特定できず | 24.3 |
| Kickstarter の期間・金額・更新、一部 SNS | Kickstarter は HTTP 403、X は一部のみ | 9 章, 13.2 N1 |
| OpenVPN 2.7.6 + OpenSSL 3.6.4 の実接続で ML-KEM(X25519MLKEM768)が使われるか(ソース読みのみ。UN-27) | 実機・実接続を未実施 | 21.5 |
| WP-1 の Pi 3B+ ログで kernel の `Loaded` から `Device tree loaded` までの 2.63 s の内訳と、GPU 段のサイズ依存(【推測】。UN-28) | 実機未測定 | 5.2, 14.2 |
| Newlib に Linux 用の sys ディレクトリが無いか(UN-29) | sourceware が bot 防御ページで取得できず | 17.2 |

- **18.1 は D1(終点の定義)が未決のため保留**:失敗検知・確定の判定に使う「終点」は D1 が決まるまで決めない(18.1 冒頭)。
- **前提の注意**:カーネルの PREEMPT は VOLUNTARY か NONE が前提(R10)だが、7.x の arm64 では両方選べない(LAZY/FULL のみ。20.2)。**R3(CLI のみ)と R6(コンパイルしない)の出所はプロフィールのメモで、ユーザー発言ログ上の番号は無い**(0 章)。

## H.4b 未決の設計論点 D1〜D8(一覧。**どれも未決**。選択肢は 11.3 の全文)
| # | 論点 | 選択肢(11.3 の全文) | 関連要件 | 詳細(章) | 状態 |
|---|---|---|---|---|---|
| D1 | 起動の終点の定義 | **A**:LCD にプロンプト+キー入力可まで(体感に直結。ただし M5IOE1→LCD/キーボードの鎖を早期に読む必要=R11/R12 と相反)/ **B**:init(PID1)が終点マーカーを書くまでを終点とし、LCD・キーボードは終点後に遅延読込(R12 に沿う。体感指標として「プロンプト+キー可」までの時間を別に併記)/ **C**:両方を測る | R1, R11, R12 | 14.3, 15.1 | 未決 |
| D2 | rootfs の読取専用 FS | **SquashFS**(`-sort` で優先度の高いファイルを先頭へ)/ **EROFS**(`-z` を指定すれば圧縮、`--sort` は tar 入力のみ)。実機で 2 構成を比較する案。どちらが速いかは未測定 | R2, R7, R17 | 16.4 | 未決 |
| D3 | init と libc | systemd 最小化+glibc(M5 の udev ルール・unit をそのまま使える)/ BusyBox init+eudev+musl 静的(軽いが udev ルール移植と NSS 非対応を負う)/ 自作 init(最終手段)。**17 章と 16.2 の結論は同じ向き(全機能維持なら glibc+systemd)だが、起動時間は未測定** | R1, R15, R18 | 16.2, 17.5 | 未決 |
| D4 | A/B 方式 | MBR+tryboot/autoboot.txt+RAUC custom(U-Boot なしで GPU 段後の遅延を避けられるが **BCM2837 の tryboot は未検証**)/ U-Boot 系(Mender の mender-convert は RPi3 64bit を公式構成に持つ。RAUC も可。段が増える)/ Rugix(Pi 3=rpi-tryboot、Zero 2 W=rpi-uboot)。**「必ず前の面へ戻せる」とは言えない**(tryboot・WDT が CM0 で効くことが前提で未検証。FAT の boot 領域は単一障害点) | R4, R13 | 7 章, 18 章 | 未決 |
| D5 | カーネル版 | **6.18.y**(VOLUNTARY 選択可、M5 モジュールの前提に合う)/ **7.2.y・7.3.y**(PREEMPT は LAZY/FULL のみ。7.1 で DRM API が変わり M5 の `panel-mipi-dbi-m.c` は未ビルド確認。7.3 は alias unmap の再適用を含み CM0 での起動が未確認)。同一構成での比較はあり | R5, R10 | 20.2, 20.3, 20.5 | 未決 |
| D6 | 開発中ログの置き場 | 案 3:開発中は ext4 に書き、電断試験時は専用領域/pstore へ切替(R14)。R2(完全 ro)との緊張は「モード切替でビルドを分ける」ことで扱う案。測定条件が変わる点は記録が要る | R2, R14 | 19.2, 19.3 | 未決(ユーザーは t59u「案3で良いのでは？」と疑問形で案 3 を支持する発言をしたが、同意の確定ではない。実装方式も未決) |
| D7 | SSH 実装 | Dropbear(小さい。PQ 既定有効)/ OpenSSH(標準的。依存大。PQ 既定有効)。VPN は WireGuard(カーネル内蔵。ChaCha)/ OpenVPN(要 `--data-ciphers` 設定)。**終点の後に socket activation で起動**する案 | R18 | 21.3, 21.5 | 未決 |
| R21 | イメージに名称を付けたいという要件。名称の由来は RESEARCH.md を参照 | t69u〜t76u | 24 | 名前の決定は山城さん |

## H.5 次のステップ
1. **山城さんの判断**:11.4 の事項(終点の定義、名前、SquashFS/EROFS の比較方針ほか)。
3. **実機到着後**:10.2 の測定順(公式イメージのベースライン → tryboot → arm_64bit/kernel8.img → 無圧縮 vs gzip → vc4 除去 → Wi-Fi chip ID → GL852G → 電源断試験)。同時に 19.1 の UART 配線(G14/G15)を確認。
4. **設計書の作成**(11.2 の①:Buildroot 設計案。ビルドはまだ行わない=R6)。

## H.6 検証できなかったこと
- **実機は無く、ビルドもしていない**(起動時間、tryboot、電源断耐性、各種ドライバ動作はすべて未検証)。
- **Kickstarter の本文は HTTP 403**(取得できず)。RPi フォーラム t=207888・t=263234、Arm の ID_AA64ISAR0_EL1 ページも HTTP 403(取得できず)。`man7.org` の systemd-bootchart は 404。GitHub の `CardputerZero/cardputer-zero-os` は 404(Wayback のみ)。
- URL の確認件数は母数つきで 13.4B〜13.4D に記載(本文の URL 総数 346 件 = 13.4B 205 件 + 13.4A 63 件 + 13.4C 59 件 + 13.4D 19 件。式は 13.4D の冒頭)。HTTP 200 の多くは「到達のみ」で、本文の該当文まで確認したものは 13.4A に限る。bot 防御ページ(「Making sure you're not a bot!」等)は 200 でも「取得できず」に数える。

## H.7 用語集
| 用語 | 意味 |
|---|---|
| CM0 | Raspberry Pi の Compute Module 0。CardputerZero の SoC は BCM2837(Cortex-A53)で、DT 名は `bcm2710-rpi-cm0` |
| tryboot / autoboot.txt | RPi ファームウェアの「次回 1 回だけ別パーティションから起動」機能と、その設定ファイル(A/B の土台) |
| A/B OTA | 2 面のシステム領域を交互に更新し、失敗時に前の面へ戻す更新方式 |
| MBR / GPT | パーティション表の方式 |
| SquashFS / EROFS | 読み取り専用の圧縮ファイルシステム(`mksquashfs` / `mkfs.erofs` で作る) |
| overlayfs | 読み取り専用の下層に書込み可能な上層を重ねる仕組み |
| M5IOE1 / TCA8418 | M5 基板の IO エキスパンダ(LCD の RST/BL、LED 等の親)/ キーボードコントローラ |
| SW_DET / powerfail_suo | 電源スイッチ検知(G6)/ それを使う M5 のカーネルモジュール(SysRq 'u' を実行) |
| SysRq | カーネルの緊急操作(s=sync、u=ro 再マウント、o=電源断) |
| mini-UART / PL011 | BCM283x の 2 種類の UART(前者はコアクロック依存、後者は BT に割当) |
| KEX / ML-KEM / sntrup761 | SSH の鍵交換 / NIST 標準の耐量子 KEM(mlkem768)/ OpenSSH 系で先行した耐量子 KEM。いずれも x25519 とのハイブリッド |
| alias unmap | arm64 でカーネル data/bss の線形マップ上の別名を unmap する変更 |
| pstore / ramoops | 再起動後にクラッシュログを読む仕組み(RAM または専用領域) |
| pi-gen / rpi-image-gen | RPi OS イメージの作成ツール / RPi 公式の新しいイメージ生成ツール(A/B の image-rota を含む) |
| RAUC / SWUpdate / Mender / Rugix | OTA 更新フレームワーク |
| Buildroot / Yocto | 組込み Linux のビルドシステム |
| glibc / musl | C ライブラリ |

## 0. ユーザー要件(前提)

> v5 で、会話ログ(ユーザー発言 t0u〜t76u)から**要件になる発言を番号付きで整理**しました(t0u・t1u などの前置き・参照 URL や、同意の回答は要件に入れていません。0 章末の脚注)。「発言」列の tNNu はユーザー発言の通し番号(作業用ログ 事前資料)です。R1〜R6 は v4 から番号を維持し、R7 以降を追加しました。**要件同士が衝突する場合は「衝突」列に書き、設計は 11.3 で選択肢として示します(「確定」にしません)**。

| # | 要件(ユーザーの言い方に近い形) | 発言 | 反映先(章) | 衝突・注意 |
|---|---|---|---|---|
| R1 | **超高速起動**(「数秒で boot したい」) | t7u, t20u, t21u | 5, 14〜17 | — |
| R2 | **突然の電源断への耐性**(「完全読み取り専用が安全」) | t7u, t23u | 6, 18 | 完全 ro と R14(ログを SD に残す)は緊張関係 → 11.3 |
| R3 | 起動後は **CLI のみ**(GUI 不要) | **出所=プロフィールのメモ(CardputerZero 開発の前提条件)。ユーザー発言ログ上の番号は無い**(参考:t11u の「RPi の Linux は CLI でも使いこなす」は技能の話で、要件の根拠ではない) | 1.3, 11.1 | — |
| R4 | **A/B OTA**:常に 2 つ以上のイメージを保持し、失敗時に復旧できること(Zephyr 案・Linux 案の両方) | t14u, t15u(GPT/MBR の意向は R26/t16u) | 7, 18 | R13(回復モード不要)と併せ「人手の回復なし・自動で前の面へ」(18.1)。BCM2837 の tryboot は未検証 |
| R5 | 前提:**M5 公式ドライバ(m5stack-linux-dtoverlays)を使用** | t35u(t27u:公式イメージ/ドライバは参考になるか) | 5.7, 14.3 | M5 ドライバは 6.12 では include が解決しない(5.7)。7.1 以降は API 変更あり(20.2) |
| R6 | **コンパイルはまだしない** | **出所=プロフィールのメモ(「コンパイルはしない」)。ユーザー発言ログ上の番号は無い** | 1.7 | — |
| R7 | 圧縮方式の検討(カーネル/initramfs の LZ4・LZO・ZSTD、btrfs 透過圧縮。ReadOnly なら高圧縮率も使える) | t10u, t28u, t29u, t31u | 5.4, 6.1, 14.2, 16.4 | arm64 の Image は gzip か無圧縮のみ受理(14.2) |
| R8 | 完全 read-only でも zram/zswap は使えるか | t23u | 6.6 | — |
| R9 | **エンジニア向け開発キット**想定。microSD も対象。他の候補チップも調査 | t17u(ESP32 で Linux が動くか)、t18u(nRF9151 単体+Zephyr)、t19u(microSD) | 2, 4 | — |
| R10 | **最新カーネルも比較**(LTS にこだわらない。速くなるなら)。リアルタイム要件なし(PREEMPT_RT は不採用)。6.18 以降の高速化情報 | t44u, t46u, t50u, t52u | 20 | 6.18 は VOLUNTARY 選択可、7.2 は LAZY/FULL のみ(20.3) <br>**注記:プロフィール由来の前提「PREEMPT は VOLUNTARY か NONE」と「最新カーネルも可」は 7.x では両立しない(7.2 arm64 は NONE/VOLUNTARY とも選べず LAZY/FULL のみ。D5・20.2)** |
| R11 | カーネルを**極限まで小さく**(遅延読込も) | t53u, t45u | 14, 20.4(printk) | — |
| R12 | LCD・TCA8418(少なくともキーボード)も**遅延読込** で良い。開発中も先読み不要。**splash は必須でない**。後で使えるまでの時間が伸びても体感が速ければ良い | t54u, t55u, t57u | 14.3, 15.1 | **「終点=LCD+キー入力可」の定義と両立しない** → 15.1 に A/B 両案、11.4 に決定待ち |
| R13 | **回復モードやブートメニューは不要** | t56u | 18.1 | R4 と併せて自動復旧のみ |
| R14 | **カーネルログを SD に残す**(案 3:開発中は ext4 に書き、電断試験時は専用領域/pstore へ切替) | t58u, t59u | 19.2〜19.3 | R2(完全 ro)と緊張。案 3 は t59u(疑問形)に基づく提案で確定ではない(D6 は未決) |
| R15 | libc(Newlib・musl 等)と jemalloc などアロケータの調査 | t60u, t61u, t63u | 17 | glibc か musl かは未決(17.5, 11.3) |
| R16 | **ユーザー領域**も徹底的に高速化(不要物の除去と遅延読込) | t64u | 16 | — |
| R17 | SquashFS で**読み込み順を最適化** | t66u | 16.4 | — |
| R18 | BusyBox・init・systemd のうち **CardputerZero の全機能を維持** できる構成。行く行くは **SSH・VPN** も | t67u | 16.2, 21 | — |
| R19 | 比較対象に Android 等・BSD 系・Debian・Arch・OpenBIOS 以外も含める。Linux ベース候補は Ubuntu Core 26.04 / Minimal Ubuntu / Buildroot / BusyBox / Yocto | t7u, t36u〜t40u | 3, 4 | — |
| R20 | **一次情報の URL を添える**。未調査をなくし、漏れのない報告にする。実機到着後すぐ開発できるようアイデアを多く | t33u, t34u, t47u, t48u, t49u, t62u, t65u, t68u | 13, 22, 25 | — |
| R21 | イメージに名称を付けたいという要件。名称の由来は RESEARCH.md を参照 | t69u〜t76u | 24 | 名前の決定は山城さん |
| R22 | **ユーザーが特定の資料を除外し、公式の CardputerZero/cardputer-zero-os(github.com/CardputerZero/cardputer-zero-os)を基準にする**(除外された資料の名前は本書に書かない) | t2u, t12u, t13u, t25u | 8.2 | t13u の原文には除外対象の名前が含まれるため転記しない |
| R24 | 表形式で整理(Zephyr 26.04 LTS/upstream main/Ubuntu Core/Buildroot/Yocto/その他)。詳細レポート(除外理由込み)。実機が届いたらすぐ開発したい | t24u, t25u, t30u, t32u, t33u | 3, 4, 10.2 | — |
| R25 | **自作案(自作 OS/ファームウェア)も徹底的に調査・検討する**。ユーザーは nRF54L15 等に習熟し、M5Stack/ESP32/RPi の Linux(CLI)も使いこなせる | t11u | 3, 4, 16.2(自作 init は最終手段=11.3 D3)、22 | — |
| R26 | **パーティション表は MBR より GPT が良いか**(ユーザーの質問・意向確認。要件というより問い) | t16u | 7, 11.3 D4 | image-rota は GPT 前提で対象は cm4/pi4/cm5/pi5 のみ(13.1 ROTA)。**CM0 の GPT 起動可否は未確認**(UN-03)。未決 |
| R27 | **Zephyr 26.04 LTS(Canonical 配布)が CM0 と CardputerZero の実装デバイスに対応しているかを、確実に調べる**。t4u「2つの方向性を考えています。」(Zephyr 26.04 LTS / Linuxベース)は前置き、t5u「Zephyer 26.04 LTSはCanonicalからつい最近公開されましたので確認してください。」、t6u「まずはZephyr 26.04 LTSがCM0の対応状況と、CardPuterZeroで実装されているデバイスへの対応状況を、確実に調査してください。」 | t4u, t5u, t6u | 3, 4(Zephyr の行) | Zephyr 26.04 LTS の行は題名・日付のみ確認済みで、CM0 対応の記載は未確認。R24(表形式)と併せて読む |

※ t41u〜t43u と t51u はユーザー発言ログにありません。t0u は依頼の前置き、t1u は参照 URL、t3u・t61u は同意の回答です。t59u「案3で良いのでは？」は疑問形のため案3への同意確定ではなく、D6 は未決です。t26u「Bです。」は旧メニューへの回答です。旧メニューの B は Ubuntu Core / Yocto の調査を指し、R14 の根拠ではありません。

## 0.1 凡例(事実と見立ての区別)

| 表記 | 意味 | 出典URL |
|---|---|---|
| 【**確認済み**】(対象/方法/コミット等/取得日) | 一次情報(clone 済みリポジトリの grep、公式ページ、API の GET、公式 docs)を自分で確認した事項。確認元を括弧に書く | 出典なし(ユーザー指示/作成者の判断) |
| 【**確認済み・二次**】 | 検索要約、第三者記事、SNS など。内容が存在することは確認したが真偽は未検証 | 出典なし(ユーザー指示/作成者の判断) |
| 【**報告による・未確認**】 | 他の調査(事前資料 配下のファイル、監査報告)に記載があるが、今回の改訂では一次情報を取り直していない事項 | 出典なし(ユーザー指示/作成者の判断) |
| 【**未確認**】 | 調べたが裏付けが取れなかった、または実機検証が必要な事項 | 出典なし(ユーザー指示/作成者の判断) |
| **取得できず** | URL を GET したが HTTP 403/404/タイトルのみ/接続不可で本文を確認できなかったもの。一次/二次のラベルは付けない(13.4B) | 出典なし |
| 【**推測**】 / 【**作成者の見立て**】 | 事実から導いた推論・設計案。検証していない | 出典なし(ユーザー指示/作成者の判断) |

※ 数値には対象 SoC・条件(測定の始点/終点)を併記し、条件の異なる数値は**合成しません**。各項目には「何の版か(製品/コンポーネント/ブランチ)」と日付を付けます。
※ 日付のない【確認済み】は、基準日 2026-10-18 の確認です。
※ **URL の読み方(v3):** コミット固定 URL(`blob/<hash>/path#Lnn`)は、そのハッシュの時点のファイルを指します(ブランチの先頭ではありません)。「URL到達のみ確認」は HTTP 200 を得たが本文は今回読んでいないことを意味し、内容の確認度は元のラベルのままです。「URL未取得」は、一次情報の URL を実在確認できなかったことを意味します(内容が偽という意味ではありません)。表の「出典なし」はユーザー指示・凡例・作成者の判断で、一次情報の対象外です。取得日はすべて 2026-10-18(JST)です。

### 0.2 調査範囲

| 区分 | 内容 | 出典URL |
|---|---|---|
| v5 で再確認・訂正したもの | 12.5 に列挙(Mender、powerfail_suo、UART、SSH/VPN の既定暗号、alias unmap、CachyOS/Omarchy、KittenLabs、mksquashfs/EROFS、終点定義、GPIO6、libc 章の矛盾ほか)。**未確認は 10.1 と 25.3 に残る(「すべて解消」ではない)** | 出典なし(作成者の判断) |
| 実機未検証 | 起動時間、tryboot/autoboot.txt、電源断耐性など、実機挙動はすべて未検証(実機は未入手) | 出典なし(ユーザー指示/作成者の判断) |

---

## 1. 目的と調査依頼

### 1.1 目的
- 発売間近の **M5Stack CardputerZero** 向けに、カスタム「ファームウェア」を開発したい。
- ここでいう「ファームウェア」の実体は **Linux システム(または OS イメージ)** です。MCU 向けファームウェアではありません。CM0 は Cortex-A53 の Linux 級 SoC です。

### 1.2 方向性(2 案)
1. **Zephyr 26.04 LTS** 案
2. **Linux ベース**案

### 1.3 Linux 案の要件(0 章 R1〜R4 の抜粋。R5〜R27 は 0 章の表)
| # | 要件 | 出典URL |
|---|---|---|
| R1 | **超高速起動** | 出典なし(ユーザー指示/作成者の判断) |
| R2 | **突然の電源断への耐性** | 出典なし(ユーザー指示/作成者の判断) |
| R3 | 起動後は **CLI(シェル)**。GUI は不要 | 出典なし(ユーザー指示/作成者の判断) |
| R4 | **OTA**:常に 2 つ以上のイメージを保持し、失敗時に復旧できる方式(A/B) | 出典なし(ユーザー指示/作成者の判断) |
| (補足) | OTA 要件(R4)は **Zephyr 案・Linux 案の両方** に適用する。前提として M5 公式ドライバ(m5stack-linux-dtoverlays)を使う(0 章 R5) | 出典なし(ユーザー指示/作成者の判断) |

### 1.4 Linux ベース候補(ユーザー指定)
Ubuntu Core 26.04 / Minimal Ubuntu / Buildroot / BusyBox / Yocto

### 1.5 調査依頼事項
- 超高速起動
  - techfeed 記事(Boot Naked Linux)
  - johschmitz/buildroot-quickpi
  - カーネル圧縮(LZ4/LZO/ZSTD)
  - ブート ROM → GPU ファーム → kernel8.img の段を高速化または省略できるか
- 電源遮断技術:btrfs、UBIFS、ext3、ext4、overlayfs、Yocto read-only-rootfs、SquashFS、tmpfs
- 公式の CardputerZero / cardputer-zero-os の確認
- MBR より GPT が良いか


- 補足(名称):正式名称は **Ubuntu Core 26**(Ubuntu 26.04 LTS ベース)です。【**報告による・未確認**】(監査報告 2026-10-18。Imager 一覧には「Ubuntu Core 26 (2026-06-05)」が pi3-64bit 向けに存在、【**確認済み**】 事前資料、取得 2026-10-18)。本レポートでは「Ubuntu Core 26(26.04)」と書きます。(出典: https://downloads.raspberrypi.com/os_list_imagingutility_v4.json)

### 1.6 ユーザーからの追加質問
- Q1:完全 read-only boot の場合、zram/zswap は使えるか(→ 6.6 節)
- Q2:LCD のみにすれば起動は速くなるか(→ 5.6 節)
- Q3:DisplayPort(実際は **HDMI**)ドライバを遅延ロードできるか(→ 5.6 節)

### 1.7 制約
- コンパイル等には**まだ着手しない**。

### 1.8 これまでに訂正した前提
| ユーザーの認識 | 訂正内容 | 根拠 | 出典URL |
|---|---|---|---|
| 映像出力は DisplayPort | **HDMI** です(DisplayPort は回路図にも docs にも無い) | 回路図 V0.6.1 P10 J5 | https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf<br>(ページ P10 J5 の再照合は今回未実施) |
| UBIFS を microSD で使う | UBIFS は**生 NAND/MTD+UBI 専用** で、microSD/eMMC では使えません | カーネル docs | URL未取得 |
| 公式イメージは約 2.1 秒で起動する | 2.1 秒は M5 が自己申告した「ARM 起動まで」の値で、しかも**独自の小型カーネル(227KB)を読む構成** での値です(5.1 節)。公式イメージ全体の起動時間ではありません | circle-boot-splash BENCHMARK.md | https://github.com/CardputerZero/circle-boot-splash/blob/b80d7c6a537c09c1ca233aeffa9c2e8601b113df/app/cardputerzero-splash/BENCHMARK.md#L14-L21 |
| 「powerfail_suo は S→U→O を実行する」(旧 osA.md の記述) | 実行されるのは **'u'(ro 再マウント)のみ** です | 6.3 節 | https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/powerfail_suo.c#L93 |


---

## 2. ハードウェア仕様

出典:【**確認済み**】 公式 docs en/ja(2026-10-18 確認)、回路図 V0.6.1(2026-07-02)。docs には「packaging and software development not yet complete」との注記があります。

### 2.1 搭載チップ・主要部品

| 区分 | 部品 | 接続/備考 | 出典URL |
|---|---|---|---|
| SoC モジュール | **CM0**(RP3A0 / BCM2837、Cortex-A53 ×4、1GHz、aarch64) | DTS 名は bcm2710-rpi-cm0 | https://docs.m5stack.com/en/CardputerZero<br>https://docs.m5stack.com/ja/CardputerZero<br>https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf |
| メモリ | LPDDR2 512MB | CM0 内蔵 | https://docs.m5stack.com/en/CardputerZero |
| ストレージ | microSD | 標準版 C154 は 32GB 付属、Lite 版 C155 は付属なし | https://docs.m5stack.com/en/CardputerZero<br>https://docs.m5stack.com/en/products/sku/C154 |
| Wi-Fi/BT | CYW43439(CM0 の**無線搭載版** に搭載。RP-009251-DS は CM0 のデータシート Release 3 で、無線は「オプション」、CM0Lite は eMMC なしで SDIO を持つ版。CM0Lite の無線の有無はデータシートに明記がなく未確認。M5 の実機がどの版かも未確認) | RPi 配布ファームには 43430/43436s/43439 がすべて含まれる。**実機の chip ID は【未確認】** | https://docs.m5stack.com/en/CardputerZero<br>RP-009251-DS: https://pip-assets.raspberrypi.com/categories/1286-raspberry-pi-compute-module-zero/documents/RP-009251-DS-3-cm0-datasheet.pdf(v9 で取得。13.4A V9A-001) |
| LCD | ST7789V3、320×170、SPI | MOSI G10、SCLK G11、DC G25、CS G8、TE G5、RST=M5IOE1 PYG12、BL=PYG10(PWM) | https://docs.m5stack.com/en/CardputerZero<br>https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf |
| キーボード | TCA8418 @0x34 | INT G27、46 キー+LED(SHIFT/FN/SYM) | https://docs.m5stack.com/en/CardputerZero<br>https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf |
| オーディオコーデック | ES8389 @0x10 | I2S G18〜21 | https://docs.m5stack.com/en/CardputerZero<br>https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf |
| アンプ | AW8737A | EN G24、1W スピーカー | https://docs.m5stack.com/en/CardputerZero<br>https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf |
| マイク | MEMS マイク | — | https://docs.m5stack.com/en/CardputerZero<br>https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf |
| ヘッドホン | TRRS | HP_DET G17、PYG6 で CTIA/OMTP を切替 | https://docs.m5stack.com/en/CardputerZero<br>https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf |
| IMU | BMI270 @0x68、BMM150 @0x10(docs 記載。ES8389 と同じ値) | **Lite 版には IMU・カメラ・microSD が無い**(公式 docs の比較表) | https://docs.m5stack.com/en/CardputerZero<br>https://docs.m5stack.com/en/products/sku/C154 |
| RTC | RX8130CE @0x32 | — | https://docs.m5stack.com/en/CardputerZero<br>https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf |
| 燃料計 | BQ27220 @0x55 | — | https://docs.m5stack.com/en/CardputerZero<br>https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf |
| 充電 | IP2315 | バッテリ 1750mAh | https://docs.m5stack.com/en/CardputerZero<br>https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf |
| 電源系 | TPS2116、SY7088、SY8003 等 | — | https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf |
| IO エキスパンダ | M5IOE1 @0x4F | NRST G16 | https://docs.m5stack.com/en/CardputerZero<br>https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf |
| USB ハブ | GL852G(4 ポート) | リセットは **PYG3_KB_HUB_RST(TCA8418 キーボードと GL852G で共用)**(公式 docs に明記)。USB1=SR9900A(10/100M Ethernet)、USB2=USB-A、USB3=Type-C 左、USB4=HAT | https://docs.m5stack.com/en/CardputerZero<br>https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf |
| USB モード | Host/Slave 物理スイッチ | Slave 時はハブを切断 | https://docs.m5stack.com/en/CardputerZero |
| 右 Type-C | CM0 直結 | — | https://docs.m5stack.com/en/CardputerZero |
| カメラ | IMX219(Lite 版を除く) | CSI | https://docs.m5stack.com/en/CardputerZero<br>https://docs.m5stack.com/en/products/sku/C154 |
| 電源状態検出 | PYG5_PWR_DET | 公式 docs の Power Status に記載あり(詳細な意味は本レポートでは未整理) | https://docs.m5stack.com/en/CardputerZero |
| IR | TX G12 / RX G13 | — | https://docs.m5stack.com/en/CardputerZero<br>https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf |
| 拡張 | HY2.0-4P、EXT 14pin | Cap はホットスワップ不可 | https://docs.m5stack.com/en/CardputerZero |
| スイッチ検知 | SW_DET = G6 | powerfail_suo が使用(6.3 節) | https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf<br>https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/powerfail_suo.c#L93 |
| 映像出力 | **HDMI**(回路図 P10 J5、19pin、HDMI-001) | コネクタ形状(Type A か D か)は【**未確認**】。DSI/CVBS は未使用 | https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf<br>(ページ P10 J5 の再照合は今回未実施) |

### 2.2 ソフト開発上の留意点
- 【**確認済み**】 PYG3 は TCA8418 キーボードと GL852G ハブの**共用リセット** です(公式 docs の記載)。したがってハブのリセットはキーボードにも波及する可能性があります。【**推測**】(出典: https://docs.m5stack.com/en/CardputerZero)
- 【**報告による**】(否定。範囲:HEAD 7551854 の `modules/tca8418-1.0` に対する `grep -rnE 'rest-gpios|rest_gpio|rest-gpio'` が 0 件、`modules` 配下の `*.c` に対する `grep -rniE 'gl852|hub.?rst|usb.*reset'` が 0 件。2026-10-18 22:08 JST に再実行)tca8418 ドライバは rest-gpios を使っておらず、Linux から USB ハブ(GL852G)をリセットするコードも見つかりません。**肯定の確認**:overlay 側には `rest-gpios = <&m5ioe1 2 1>` の記述がある(cardputerzero-v5-overlay.dts L100、v3 は L90)。HEAD 7551854(2026-09-23)。(出典: https://github.com/m5stack/m5stack-linux-dtoverlays/tree/75518549a2640486f5d13ea72ca4935b198d7c20<br>https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v5-overlay.dts#L100)
- 【**報告による・未確認**】 v3/v5 overlay の tca8418 ノードに `rest-gpios = <&m5ioe1 2 1>`(reset の誤記と見られる)があるが、ドライバは読まない。v3 と v5 の差の詳細は未整理(監査報告 2026-10-18)。(出典: https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v3-overlay.dts#L90<br>https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v5-overlay.dts#L100)
- 【**推測**】 Linux 側からの GL852G の制御方法は、実機で確認する必要があります。

---

## 3. 候補 OS 別の対応状況と起動時間

> **起動時間の扱い:** CM0 でのベースライン実測値はまだありません。下表の「起動時間の根拠」には**条件の異なる既存数値を併記するだけ** で、足し算や平均はしていません(5.2 節の台帳を参照)。「予想」は【**作成者の見立て**】であり、根拠が弱いものは「根拠なし」と書きます。

| 候補(何の版か) | CM0 対応状況・版 | 要件への適合(所見) | 起動時間の根拠/見立て | 出典URL |
|---|---|---|---|---|
| Zephyr(Canonical Zephyr 26.04 LTS) | 【**確認済み**】 発表ページの題名と日付(2026-09-21、ubuntu.com ブログ。13.4A)。【**報告による**】 upcoming release、upstream 4.4 ベース(監査報告。本文は読んでいない)。フォーク内容(Launchpad)は【**未確認**】。公式 RPi 対応の記載は【**報告による**】(否定。範囲:発表ページの題名・日付のみ。本文は読んでいない)見当たらない | CM0 では動作する根拠なし | 評価不能 | https://ubuntu.com/blog/zephyr-lts-announcement |
| Zephyr v4.4.0 | 【**報告による**】(否定。範囲:ローカル z44 のタグ v4.4.0 で `find . -path ./.git -prune -o ( -iname '*rpi_zero_2w*' -o -iname '*bcm2710*' ) -print` が 0 件。2026-10-18 22:09 JST に再実行)Zephyr upstream に `rpi_zero_2w`/`bcm2710` のボード定義は見当たらない | 非対応 | 評価不能 | https://github.com/zephyrproject-rtos/zephyr/tree/684c9e8f32e4373a21098559f748f06915f950c9/boards/raspberrypi<br>https://github.com/zephyrproject-rtos/zephyr/releases/tag/v4.4.0 |
| Zephyr upstream main | 【**確認済み**】 zmain(a915b2f12、2026-10-16)に `boards/raspberrypi/rpi_zero_2w` あり(PR #110189、2026-08-17 マージは【**確認済み**】(API GET、2026-10-18。v3 で格上げ))。単コア+ミニ UART のみ、SDHCI 未対応=microSD 不可(【**報告による・未確認**】) | microSD が使えず R4 以前に実用不可 | 評価不能 | https://github.com/zephyrproject-rtos/zephyr/tree/a915b2f12675b48b16d56653ea145dcd8f20cbbf/boards/raspberrypi/rpi_zero_2w<br>https://api.github.com/repos/zephyrproject-rtos/zephyr/pulls/110189 |
| 公式 OS(CardputerZero/pi-gen、branch cardputerzero_v1.0、HEAD 791a985、2026-10-08。Debian trixie) | 【**確認済み**】 カーネルは 6.18.39-1+rpt1 を sha256 検証・apt pin・hold で固定(8.1 節)。GUI(labwc) | read-only/overlayfs/tryboot/RAUC/Mender の記述は【**報告による**】(否定。範囲:ローカル clone 791a985 の追跡 128 ファイル、`grep -rniE 'overlayfs\|read-only\|tryboot\|rauc\|mender' . --exclude-dir=.git` のテキスト行が 0 件。バイナリの `start.elf` は一致表示があり内容は未検査。2026-10-18 22:08 JST) | 実測なし。M5 BENCHMARK.md は「Linux 可用 ~7〜9s」(自己申告・終点定義なし・実測と概算の合算)。【**作成者の見立て**】 GUI 込みの公式 OS はそれより長い可能性が高いが根拠は弱い | https://github.com/CardputerZero/pi-gen/commit/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc<br>https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage0/02-firmware/files/kernel.pref#L3<br>https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage0/02-firmware/01-run.sh#L32<br>https://github.com/CardputerZero/circle-boot-splash/blob/b80d7c6a537c09c1ca233aeffa9c2e8601b113df/app/cardputerzero-splash/BENCHMARK.md#L14-L21 |
| Buildroot 2026.08(2026-09-04、d5180309) | 【**確認済み**】 raspberrypi3_64/zero2w_64 defconfig は 6.12.61 固定、【**報告による**】(否定。範囲:Buildroot d518030 の `configs/` に `cm0` を含むファイル名が無い。v8 で再実行せず、監査 5.1 の再現による)CM0 専用 defconfig は見当たらない(5.7 節)。GCC 既定は **15.3.0**(既定が `BR2_GCC_VERSION_15_X` なのは `package/gcc/Config.in.host` L6、14.4.0/15.3.0/16.2.0 の版は `package/gcc/gcc.hash`) | 【**作成者の見立て**】 R1〜R4 を設計で満たせる見込み(未検証) | 根拠: KittenLabs(Zero 2 W、Buildroot)<3.5s は「電源→独自 userspace の GPIO」、非圧縮 8.5MiB カーネル、USB/HDMI/sound 無効、KASLR/Spectre 無効の条件(【**報告による・未確認**】)。CM0・M5 ドライバ・LCD は含まない | https://github.com/buildroot/buildroot/commit/d5180309b1b66ef3b8eaccca70ad69be8e0729a1<br>https://github.com/buildroot/buildroot/blob/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/package/gcc/Config.in.host#L6<br>https://github.com/buildroot/buildroot/blob/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/configs/raspberrypizero2w_64_defconfig#L11-L12<br>https://github.com/buildroot/buildroot/blob/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/configs/raspberrypi3_64_defconfig#L12-L13<br>KittenLabs: https://kittenlabs.de/blog/2024/09/01/extreme-pi-boot-optimization/ |
| BusyBox 単独(BusyBox 1.38.0 は【**報告による・未確認**】) | BusyBox は userland であり OS ではない。Buildroot の最小構成(既定 init が BusyBox)と同等の組み方になる | 【**作成者の見立て**】 カーネル+ファーム段は Buildroot と共通 | 独立した根拠なし | URL未取得(BusyBox 1.38.0 は URL 未確認) |
| Yocto(meta-raspberrypi、branch wrynose) | 【**確認済み**】 `conf/machine/raspberrypi0-2w-64.conf` あり。【**報告による**】(否定。範囲:GitHub API の tree/ファイル一覧に `cm0` を含むパスが 0 件。2026-10-18、v7 で未再実行)CM0 専用 machine は見当たらない。`LAYERSERIES_COMPAT=wrynose`、`linux-raspberrypi_6.18.bb` あり(GitHub API/raw、2026-10-18)。Wrynose 6.0 は LTS(2030-04 まで、【**報告による・未確認**】) | read-only-rootfs 機能あり。meta-rauc-community の RPi は U-Boot 方式(7.3 節)。【**作成者の見立て**】 構成次第で Buildroot 並み | 根拠なし。t26(Yocto 調査)の個別結果ファイルは /workspace 内で見つからず | https://github.com/agherzan/meta-raspberrypi/blob/919588393f41b48cb6c5d832aa35e58a19b6762d/conf/machine/raspberrypi0-2w-64.conf<br>https://github.com/agherzan/meta-raspberrypi/blob/919588393f41b48cb6c5d832aa35e58a19b6762d/conf/layer.conf#L12<br>https://github.com/agherzan/meta-raspberrypi/tree/919588393f41b48cb6c5d832aa35e58a19b6762d/recipes-kernel/linux<br>Wrynose LTS 期間:URL なし(【報告による】の部分) |
| Minimal Ubuntu / Ubuntu Server 26.04.1 | 【**確認済み**】 Imager 一覧に「Server 26.04.1」pi3 対応(osA_imager_oslist、2026-10-18) | systemd 標準構成。A/B 機構が標準で無いかは【**未確認**】(否定は確認していない) | 根拠なし。【**作成者の見立て**】 標準構成では GUI なしでも公式 OS 並みかそれ以上 | https://downloads.raspberrypi.com/os_list_imagingutility_v4.json |
| Ubuntu Core 26(2026-06-05) | 【**確認済み**】 Imager 一覧に pi3-64bit 向けで存在(2026-10-18)。最小 RAM 512MB・最小ストレージ 1GB・NAND 非対応・「Optimise boot speed」の how-to あり(【**報告による・未確認**】)。Pi 4/5 が公式テスト対象という点も【**報告による・未確認**】 | snap の A/B 相当機構(recovery/seed)の有無は【**未確認**】 | 根拠なし(snapd 初期化を含むが秒数の根拠は取れていない) | https://downloads.raspberrypi.com/os_list_imagingutility_v4.json<br>最小 RAM・how-to:URL なし(【報告による】の部分) |
| rpi-image-gen(公式、master d7616a2、2026-10-16 / 最新リリース v2.8.0、2026-08-13 は【**報告による・未確認**】) | 【**確認済み**】 device 層に pi3/zero2w/cm4/cm5/pi4/pi5 あり。【**報告による**】(否定。範囲:`device/` 配下のディレクトリ名に cm0 が無い。監査 5.1 の再現による)CM0 専用の device は見当たらない。**ただし A/B 層 image-rota は cm4/pi4/cm5/pi5 のみ**(7.6 節) | zero2w/pi3 で A/B は公式には成立しない | 公式ホワイトペーパー RP-010196-WP の値(5.2 節) | https://github.com/raspberrypi/rpi-image-gen/blob/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/image/gpt/ab_userdata/image.yaml#L2-L11<br>https://github.com/raspberrypi/rpi-image-gen/tree/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/device<br>https://api.github.com/repos/raspberrypi/rpi-image-gen/releases<br>https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-010196-WP-1-Optimising%20boot%20time%20on%20Raspberry%20Pi%20single-board%20computers.pdf |
| Alpine 3.24.2(2026-09-17) | 【**報告による・未確認**】 wiki の互換表に cm0 明記、linux-rpi 6.18.52。diskless(RAM 常駐)は 512MB では厳しい可能性 | A/B は標準にない | 実測なし | URL未取得(wiki.alpinelinux.org は HTTP 403 で確認できず) |
| piCore64 17.0(2026-08-02、kernel 6.18.37) | 【**報告による・未確認**】 RAM 展開型 | A/B は標準にない | 実測なし | URL未取得(tinycorelinux.net へ接続できず) |
| Rugix Bakery/Ctrl(v1.3.0、2026-08-05) | 【**確認済み・v4 で訂正**】 Rugix の対応表(2026-10-18 取得)は Pi 4 = rpi-tryboot、CM4 = rpi-tryboot、**Pi 3 = rpi-tryboot(🥈)**、**Zero 2 W = rpi-uboot(🥈)**、Pi 2/1/Zero = rpi-uboot。v3 の「Pi 3/Zero 2 W は U-Boot 方式」は不正確(CM0 自体は表に無い=【**報告による**】・否定。範囲:当該表。v7 で未再実行) | U-Boot が GPU 段の後に入る | 実測なし | https://api.github.com/repositories/642546697/releases<br>https://rugix.org/docs/bakery/devices/ |


---

## 4. 除外・保留した項目と理由

| 項目 | 判定 | 理由 | 出典URL |
|---|---|---|---|
| Zephyr 26.04 LTS(Canonical) | **除外** | 根拠は「v4.4.0 に BCM2710/rpi_zero_2w が無い(ローカル確認)」こと。Canonical フォークの中身は未確認 | https://github.com/zephyrproject-rtos/zephyr/tree/684c9e8f32e4373a21098559f748f06915f950c9/boards/raspberrypi<br>Canonical: URL未取得 |
| Zephyr upstream main(rpi_zero_2w) | **保留(将来監視)** | 単コア+UART のみ、SDHCI 未対応(報告)で microSD 不可 | https://github.com/zephyrproject-rtos/zephyr/tree/a915b2f12675b48b16d56653ea145dcd8f20cbbf/boards/raspberrypi/rpi_zero_2w<br>https://api.github.com/repos/zephyrproject-rtos/zephyr/pulls/110189 |
| UBIFS | **除外** | 生 MTD 専用で microSD では使えない | URL未取得(kernel docs の URL は今回取得せず) |
| ext3 | **独立候補から除外** | CONFIG_EXT3_FS が 6.18 で削除され、ext4 ドライバに統合済み | URL未取得(6.18 での削除は v2 の旧確認。今回 URL 未取得) |
| btrfs | **保留** | microSD 上で COW の電源断保証を示す資料が見つからない | URL未取得 |
| F2FS | **保留** | RPi 公式ホワイトペーパーが電源断後の破損報告が多いと警告 | https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-003610-WP-3-Making%20a%20more%20resilient%20file%20system.pdf<br>https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L1641 |
| ext4 data=journal | **除外** | 非推奨(2028-01 削除予定)。この記述は docs.kernel.org(最新版)と **v7.3-rc7**・rpi-7.3.y の ext4.rst にあり(L175-176、L422-423)、**v7.2・rpi-7.2.y・v6.18・rpi-6.18.y の ext4.rst にはありません**(否定は【**報告による**】:raw の `grep -c 'January 2028'` が 0、ファイルサイズは 27,676 B で同一。22:06 JST) | https://docs.kernel.org/admin-guide/ext4.html(200、本文に「removed in January 2028」が 2 か所)/ https://raw.githubusercontent.com/torvalds/linux/v7.3-rc7/Documentation/admin-guide/ext4.rst |
| Boot Naked Linux | **手法のみ参考** | QEMU 上の測定のみ | URL未取得(techfeed 記事の URL を特定できず) |
| buildroot-quickpi | **手法のみ参考** | 2018 年で更新停止。Pi1 と 32bit Pi3 のみ | https://github.com/johschmitz/buildroot-quickpi/commit/2f62ac8b7a1d2edb29aad7008f2c5f38aa5195a5<br>https://github.com/johschmitz/buildroot-quickpi/blob/2f62ac8b7a1d2edb29aad7008f2c5f38aa5195a5/README.md#L15-L16 |
| カーネルの LZ4/ZSTD/LZO 圧縮 | **標準構成では不可(armstub/TF-A で展開する余地は未検証)** | arm64 に HAVE_KERNEL_* 圧縮選択肢なし。start.elf(VPU)が読めるのは非圧縮か gzip。rpi-eeprom #541 は Pi4 の話で、timg236 は「カスタム ARM スタブや TF-A なら展開できる」と述べている(監査報告)。実績は【**未確認**】 | https://github.com/raspberrypi/rpi-eeprom/issues/541<br>https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc#L26-L52 |
| MCUboot | **除外** | VideoCore 起動では最初段になれない | URL未取得 |
| boot-mbr-switch | **除外** | ブートローダ領域の A/B 用で rootfs の A/B 用ではない | URL未取得 |
| SWUpdate / Mender | **次点** | RPi firmware(tryboot)との連携なし。Mender Client 6.1.0 は製品版だが、mender-convert は RPi3(64bit)を公式構成に持つ(U-Boot 方式。CM0 自体は未確認。7.1・7.4 節) | https://api.github.com/repos/sbabic/swupdate/releases/latest<br>https://docs.mender.io<br>https://github.com/buildroot/buildroot/blob/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/package/mender/mender.mk#L7 |
| rpi-image-gen の image-rota | **CM0 では不採用(公式 A/B は Pi4/5 クラスのみ)** | 7.6 節 | https://github.com/raspberrypi/rpi-image-gen/blob/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/image/gpt/ab_userdata/image.yaml#L2-L11<br>https://github.com/raspberrypi/rpi-image-gen/tree/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/device |
| GPU 段スキップ(rpi-open-firmware / lk-overlay) | **除外** | 実験的で対応 SoC・安定性が不明 | URL未取得 |
| Ubuntu Core / Minimal Ubuntu / BusyBox 単独 / Yocto | **3 章で整理済み(除外ではなく優先度低)** | A/B 機構と起動時間の根拠が取れていない。Yocto は有力な代替(3 章) | https://downloads.raspberrypi.com/os_list_imagingutility_v4.json |
| DisplayPort | **除外** | 存在しない(HDMI に訂正) | https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf<br>https://docs.m5stack.com/en/CardputerZero |

---

## 8. 公式 OS・公式リポジトリの状況

### 8.1 CardputerZero/pi-gen(branch cardputerzero_v1.0、HEAD **791a985**、2026-10-08)
- 【**確認済み**】(ローカル pi-gen、git log/grep、2026-10-18)(出典: https://github.com/CardputerZero/pi-gen/commit/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc)
  - Debian trixie arm64、labwc/Wayland、systemd
  - **カーネルは 6.18.39-1+rpt1 に固定**:`stage0/02-firmware/files/kernel.pref` に「Pin: version 1:6.18.39-1+rpt1」(Pin-Priority 1001)。`kernel-packages.sha256` の sha256 で検証し、`apt-mark hold`(`01-run.sh`。hold は監査報告)(出典: https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage0/02-firmware/files/kernel.pref#L3<br>https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage0/02-firmware/files/kernel-packages.sha256<br>https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage0/02-firmware/01-run.sh#L32)
  - ドライバは **M5 dtoverlays を毎回 `--depth=1` で最新追従 clone**(コミットは /etc/cardputerzero-dtoverlays.commit に記録)。`CONFIG_CARDPUTERO_V0_5=y`(同 01-run.sh L31・L32。回路図は V0.6.1)(出典: https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage2/05-cardputerzero/01-run.sh#L20)
  - read-only 化、overlayfs、tryboot、RAUC、Mender の記述は 0 件(grep)(出典: https://github.com/CardputerZero/pi-gen/commit/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc(『0 件』の否定は clone 内 grep による。URL では示せない))
  - ローカルは浅い clone のため、ピンがいつ追加されたかは不明。「2026-10-18 時点の HEAD にある」と読んでください
- 【**報告による・未確認**】 既定アカウント pi/raspberry と ENABLE_SSH=1 は pi-gen の **CI ワークフロー(.github/workflows/build.yml)の値** で、配布イメージ全体の「出荷時」既定とまでは確認できない。first-boot ウィザード(piwiz/LaunchWizard)があり、OOBE は export 時に無効化(監査報告)。Pi OS 本家は 2022-04 に pi ユーザー廃止、2026-04-13 から passwordless sudo も既定無効。(出典: https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/.github/workflows/build.yml#L52-L54(今回、build.yml の値そのものは確認済み。出荷物での既定は未確認))
- 【**作成者の見立て**】 CI の値のままイメージに入っていれば SSH 有効+既定パスワードはセキュリティ上好ましくありません(実際の出荷物は未確認)。

### 8.2 cardputer-zero-os / cardputer-zero-shell
- 【**確認済み**】 2026-10-18 時点で github.com の URL は 2 件とも **404**(curl で確認)。【**報告による**】(否定。範囲:org の API 一覧に当該リポジトリ名が無いこと。v7 で未再実行)(出典: https://github.com/CardputerZero/cardputer-zero-os)
- 【**確認済み・一次(Wayback)・v4 で更新**】 Wayback の cardputer-zero-os スナップショット https://web.archive.org/web/20260623195631/https://github.com/CardputerZero/cardputer-zero-os (取得時刻 2026-06-24 04:56 JST):Star 12 / Fork 2 / 14 commits、About=「system profile for running Raspberry Pi OS / Debian as a Cardputer Zero appliance」、**Topics = `community`・`third-party`**、MIT。README:内蔵画面は panel-mipi-dbi-spi → DRM/KMS → labwc → Wayland greeter。cardputer-zero-shell の Wayland 側は https://web.archive.org/web/20260527131053/https://github.com/CardputerZero/cardputer-zero-shell にスナップショットあり(内容未読)。**404 の原因【推測】**:作者 liu weikai(vicliu624)の個人リポジトリ https://github.com/vicliu624/cardputer-zero-os が 2026-07-23T10:25:33Z(JST 19:25)に作成(fork ではない、HEAD 7d9b078 = 2026-06-08)されており、org 配下の第三者(community/third-party)リポジトリが org から外れ作者個人に移った可能性が高いが、GitHub の削除・移管ログは公開 API では得られず原因は未確認。**【報告による】(以下は v3 の監査報告の記述)**Wayback(cardputer-zero-os は 2026-06-23、cardputer-zero-shell は 2026-05-27)の説明文:**OS イメージではなく、Raspberry Pi OS/Debian 向けの「システムプロファイル」**(greeter→PAM→labwc→ZeroShell。内部 LCD は `panel-mipi-dbi-spi`+`cardputerzero,st7789v.bin`、HDMI は seat0/LightDM で別系統)。【**報告による**】(否定。範囲:org の .github README(2026-08-11)の本文。再確認していない)記載は見当たらない。fork(vicliu624、stanley-fork)が残っているが**中身は未読**。(この後半の記述はアーカイブ API が 429 を返したため v5/v6 では再確認しておらず、出典 URL なし)
- 【**未確認**】 404 の原因(削除/非公開/改名のいずれか)。「作成→公開→削除または非公開→README から撤去」までは確認できる(報告)。
- 第三者のミラー cz-os-vic(ローカル)を参考にしました。【**未確認**】 最新の公式版と一致しているか。(出典: https://github.com/vicliu624/cardputer-zero-os)

### 8.3 更新機構・周辺ツール
- 【**確認済み**】 更新は .deb の apt リポジトリ(CardputerZero/packages、m5stack/CardputerZeroRepository)と launcher の updater、書込みは M5 Imager。【**報告による**】(否定。範囲:pi-gen 791a985 の追跡ファイルに対する `grep -rniE '\b(rauc|swupdate|mender|tryboot|bootc)\b|A/B' . --exclude-dir=.git` のテキスト行が 0 件。バイナリの `start.elf`・`template.zip` は一致表示があり内容は未検査。2026-10-18 22:08 JST)OS イメージやカーネルの A/B OTA は見つかっていません。(出典: https://github.com/CardputerZero/packages)
- 【**確認済み**】 そのほか:AppBuilder、Template(LVGL/SDL3)。(出典: https://github.com/CardputerZero/Template https://github.com/m5stack/CardputerZero-AppBuilder)
- 【**報告による**】 dev.cardputer.cc、cardputer.cc(Hub)(URL なし)。

---

## 9. 最新動向(2026-10-18 時点)

### 9.1 公式
- 【**報告による**】 Kickstarter(期間 2026-05-26〜07-03、支援者 13,644 人、HK$14,960,226 〈目標 HK$78,500〉、更新 13 件・最終 2026-10-16)。数値は WebSearch・BackerKit・BackerLens 等の二次情報に由来し、Kickstarter 本体は HTTP 403(Cloudflare)で読めていない。(出典: https://www.kickstarter.com/projects/m5stack/cardputerzero/posts/4829886(X の短縮 URL の転送先。本文は未読))
  - 通常版:Super Early Bird $89 / Early Bird $104 / KS Special $119 / MSRP $149。Lite 版:$59 / $69 / $79 / MSRP $99。2 台セット $238
  - 出荷目標は 2026 年 11 月頃
- 【**確認済み・二次**】 **Update 13「CardputerZero Update: The First 3,000 CM0s Are Here — Production Software Is Ready!」(Kickstarter posts/4829886)は公式更新** で、X のリンクカード本文の引用に依拠します。**Kickstarter 本文全体は読めていません(13.4B)**。引用:"the first 3,000 CM0 units have finally arrived! The second batch of 12,000 units is currently expected to arrive by the end of October… We plan to begin shipping the first batch in November. The second batch will also begin shipping in November once the CM0 modules arrive and production is completed."(旧版は「3,000/12,000」を SNS の未検証情報として 9.2 に置いていたが、公式情報)。「Production Software Is Ready!」の中身は不明です(直接読む価値あり)。(出典: https://x.com/saitotetsuya/status/2111008950107910198<br>Kickstarter の更新ページ: https://www.kickstarter.com/projects/m5stack/cardputerzero/posts/4829886(本文は読めていない))
- 【**確認済み**】 @M5Stack の投稿:2026-10-16「The first batch of CM0 arrived.」(CM0 入荷。製品出荷開始ではない)。(出典: https://x.com/M5Stack/status/2110949681601871946)
- 【**報告による**】 2026-09-28 マニュアル公開(投稿は特定できていない。docs 側の PDF は https://m5stack.oss-cn-shenzhen.aliyuncs.com/resource/docs/static/pdf/static/en/CardputerZero.pdf )。
- 【**確認済み**】 GitHub の CardputerZero org は公開リポジトリ 33 件(旧版の取得値)。主な更新:packages(10/17)、cardputerzero.github.io(10/17)、Template(10/12)、pi-gen(10/08)、launcher(09-28、60★)、AppBuilder(52★)。circle-boot-splash は ARCHIVED、org に u-boot(2026-06-11、報告)。(出典: https://api.github.com/orgs/CardputerZero<br>https://api.github.com/repos/CardputerZero/circle-boot-splash<br>https://github.com/CardputerZero/u-boot)

### 9.2 コミュニティ・SNS(**未検証**)
- 【**報告による**】 日本にも発送(@Tokagetchi、10/16)、11 月に届く可能性(@k2kkrm、10/17)(投稿 URL なし)。
- 【**確認済み・二次**】 Klipper 動作(@Rw7DVtscPX、10/17。KlipperDeckZero)。(出典: https://x.com/Rw7DVtscPX/status/2111293684952289420)
- 【**報告による**】 新規アプリ:PocketJS 移植(@pocket_js、2026-09-11)、ZeroRadio が CardputerZero Store に登場(2026-10-17)、Dirtywave M8 風トラッカー(開発中)、OpenELAB のカメラデモ(2026-09-28)(いずれも監査報告による)。(ZeroRadio について: https://x.com/HarrisonXu1998/status/2111387043775512697。他は URL なし)
- 【**報告による**】 openboardsguide の試用記事:Debian 13.6、パッケージ取得中のフリーズや Wi-Fi 切断(試作機)。(出典なし)
- 【**報告による**】 TELEC の遅延(gearinhere、2026-09-16)。【**未確認**】 FCC/CE/TELEC の取得状況。(出典なし)
- 【**報告による**】 見つからなかったもの(否定。検索の正規表現・範囲は記録なし=【**未確認**】。v7 で再検索していない):CNX/Hackaday の 10 月記事、**第三者による CardputerZero の起動時間実測**、電源断や OTA の話題。(M5 自身の BENCHMARK.md は存在する。5.1 節)(出典: 出典なし(ユーザー指示/作成者の判断)(不在の確認であり URL は無い))

---
