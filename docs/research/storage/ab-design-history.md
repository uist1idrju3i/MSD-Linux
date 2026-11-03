# A/B更新方式の比較・設計履歴

[保存領域の入口へ戻る](README.md) / [調査の索引](../../../RESEARCH.md)

以下は主に2026-10-18に調べた更新方式・boot連携と、その後のS10の経緯です。引用版、未確認・未着手という記述は当時の条件として保持し、現在の採用版・未実装範囲へ読み替えません。実行する操作は[A/B更新手順](../../UPDATE.md)、現在の候補比較は[更新framework](../alternatives/updates.md)と[TUF/Uptane](../alternatives/update-metadata.md)が正本です。

現行の更新番号検証とS10の状態は[試験台帳](../verification/experiment-catalog.md)、端末がReleaseを確認する将来の設計は[自己更新](../release-client/README.md)を参照します。公開SemVerと内部更新番号の対応は承認済みです（内部番号はtag commitのcommit時刻。対応表は[Release対応表](../../releases/README.md)）。

## 7. OTA / A-B

### 7.1 2026-10-18時点の版の照合
| ツール(何の版か) | 版(日付) | 確認度 | 出典URL |
|---|---|---|---|
| RAUC | v1.15.2（2026-03-27） | 一次（公式 releases API、2026-10-18 に公開資料で確認） | https://api.github.com/repos/rauc/rauc/releases/latest |
| SWUpdate | 2026.05.1（2026-06-22） | 一次（公式 releases API、2026-10-18 に公開資料で確認） | https://api.github.com/repos/sbabic/swupdate/releases/latest |
| Mender Client（製品版） | **6.1.0**。mender.io のブログで 2026-10-16 に紹介されたとの情報は未確認です。supported-releases は「Mender Client 6.1 / 2026-10 / Supported」と記載します。mender-convert の README には officially supported 構成として **`raspberrypi3_bookworm_64bit_config`（Raspberry Pi 3、Raspberry Pi OS Bookworm 64-bit）** があります。方式は U-Boot で、tryboot ではありません。CM0 の構成は一覧になく、動作は未確認です。 | 一次（supported-releases、README）、2026-10-18 に確認、ブログ日付は未確認 | https://docs.mender.io/release-information/supported-releases<br>https://raw.githubusercontent.com/mendersoftware/mender-convert/4b3f04a2afc0518d154b58d72febb0c6969cbabc/README.md |
| mender-convert | 5.1.0 の変更履歴（changelog 日付 2025-12-01、GitHub release 公開 2025-12-02T10:38:33Z = 2025-12-02 19:38 JST）は「Remove raspberrypi3 jobs (MEN-8947)」で、RPi 3 の CI ジョブを削除し、RPi 5 対応時に onboarding image を RPi 4 / RPi 5 に集約したものです。README の対応表には `raspberrypi3_bookworm_64bit_config` が残るため、CI ジョブの削除は同構成の削除を意味しません。最新は 5.3.0（changelog 日付 2026-09-30、GitHub release 公開 2026-10-01T12:54:27Z = 2026-10-01 21:54 JST。日付の基準が異なります）。README の Core configurations には RPi 3 の U-Boot 構成があり、CM0 構成はありません。 | 一次（公式 changelog、releases、README） | https://docs.mender.io/release-information/release-notes-changelog/mender-convert<br>https://github.com/mendersoftware/mender-convert/releases<br>https://github.com/mendersoftware/mender-convert<br>https://raw.githubusercontent.com/mendersoftware/mender-convert/4b3f04a2afc0518d154b58d72febb0c6969cbabc/README.md |
| Mender の Buildroot パッケージ | **3.5.3**（Buildroot 2026.08 の `package/mender/mender.mk`、2026-10-18 に公開資料で確認）。古い系列です。 | 一次 | https://github.com/buildroot/buildroot/blob/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/package/mender/mender.mk#L7 |
| MCUboot | v2.4.0 | 未確認 | 出典URL未取得 |
| Rugix Ctrl | v1.3.0（2026-08-05） | 一次（公式 releases API、2026-10-18 に公開資料で確認。Bakery と Ctrl の区別は未確認） | https://api.github.com/repositories/642546697/releases |

### 7.2 RPi firmware の tryboot
- 【一次】公式資料には `tryboot`、`autoboot.txt`（`[all]` / `[tryboot]`）、`reboot "0 tryboot"`、`tryboot_a_b=1`、`os_prefix`、`boot_ramdisk` が記載されています。U-Boot を使わずに A/B を構成する仕組みです。https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/autoboot.adoc#L5-L60
- 【一次】Raspberry Pi の文書は tryboot を全モデル対応と記載しています。一方、`autoboot.txt` の注記は rpi-image-gen を案内しています。CM0（BCM2837）の SD 起動（bootcode.bin / start.elf）で実際に動作するかは未確認で、実機検証が必要です。https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/raspberry-pi/bootflow-eeprom.adoc<br>https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/autoboot.adoc#L5-L60
- 【一次（フォーラム投稿）】2025-11-28 の RPi フォーラム投稿は、Pi 3 では `autoboot.txt` に加え空の `config.txt` も必要で、FAT12 は使えないと述べています。RPi エンジニアは Pi 3 以前の A/B では bootcode.bin がパーティション 1 のみで冗長性がないこと、OTA の注力が Pi 4 以降であることを述べています。CM0 への適用は未確認です。https://web.archive.org/web/20260218015810/https://forums.raspberrypi.com/viewtopic.php?t=394171
- 【未確認】「Pi 3 / Zero 2 は tryboot 非対応」とする検索要約には裏付けがありません。Ubuntu 25.10 以降の piboot-try が Zero 2 W 対応表にあるものの、autoboot 方式ではないとの情報も確認できていません。

### 7.3 RAUC（custom bootloader backend）
- 【一次・2026-11-02追記】custom backendの`get-primary` / `set-primary` / `get-state` / `set-state`と終了値を、固定した公式integration資料で確認しました。契約と本機の未確認範囲は[更新framework比較](../alternatives/updates.md#rauc-解消できた未確認と残る範囲)にまとめています。https://github.com/rauc/rauc/blob/e1b95d538c41178d3ac19069a2602988fe339fb8/docs/integration.rst
- 【未確認】Rtone の raspberrypi-firmware-rauc-bootloader-backend は tryboot 用ですが、試行回数カウンターがなく、primary が起動できない場合に他スロットへフォールバックしないとの情報があります。HAOS の `rpi-tryboot.sh` は RPi 5 向けとの情報もあります。出典URLは特定できていません。
- 【一次】RAUC の PR #1599「bootchooser: add Raspberry Pi firmware initial support」は、2026-10-18 に open（未マージ、merged=false）と確認されています。https://api.github.com/repos/rauc/rauc/pulls/1599<br>https://github.com/rauc/rauc/pull/1599
- 【一次】`meta-rauc-community` の公開ツリーには RPi 向けの U-Boot 方式があります。tryboot の実装がないとの検索結果は未確認です。https://github.com/rauc/meta-rauc-community/tree/4d666ae4956f1cfacbd1a844f2e1794cb7784e2a
- 【推測】自前の custom backend で試行カウンターとフォールバックを補う案があります。

### 7.4 SWUpdate / Mender / MCUboot / boot-mbr-switch
- 【未確認】SWUpdate に Raspberry Pi firmware（tryboot）用の bootloader 連携がなく、利用できるのは fake / EFI Boot Guard / U-Boot / GRUB との情報があります。`diskpart` は GPT / DOS を扱えるとの情報もあります。出典URLは特定できていません。
- 【一次】Buildroot の `package/mender` は Mender 3.5.3 です。Mender Client 6.1 は supported-releases で Supported（2026-10）とされ、mender-convert の公式構成には RPi 3（64-bit）の U-Boot 方式が含まれますが、CM0 自体の構成はありません。`meta-mender` の Yocto Wrynose 対応と `mender-mcu`（Zephyr 向け）の存在は未確認です。https://github.com/buildroot/buildroot/blob/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/package/mender/mender.mk#L7<br>https://docs.mender.io/release-information/supported-releases<br>https://raw.githubusercontent.com/mendersoftware/mender-convert/4b3f04a2afc0518d154b58d72febb0c6969cbabc/README.md
- 【推測】MCUboot は VideoCore 起動の最初段にはなれず、tryboot での切替が必要と考えられます。arm64 での実績は未確認です。
- 【未確認】boot-mbr-switch はブートローダー領域の A/B 用で、rootfs 用ではないとの情報があります。

### 7.5 Zephyr 案での OTA
- 【未確認】CM0 上で Zephyr を動かせるかは確認できていません。このため Zephyr 案の OTA が CM0 で成立するかも未確認です。MCUboot と Mender-MCU の組合せが存在するとの情報も未確認です。

### 7.6 rpi-image-gen の A/B レイアウト
【一次】rpi-image-gen の公開コード（commit d7616a2、2026-10-16）を Devin が 2026-10-18 に確認しました。https://github.com/raspberrypi/rpi-image-gen/blob/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/image/gpt/ab_userdata/image.yaml#L2-L11<br>https://github.com/raspberrypi/rpi-image-gen/blob/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/image/gpt/ab_userdata/image.d/hooks/preimage05-templates#L40-L42<br>https://github.com/raspberrypi/rpi-image-gen/tree/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/device<br>https://github.com/raspberrypi/rpi-image-gen/tree/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/image/mbr/simple_dual<br>https://github.com/raspberrypi/rpi-image-gen/blob/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/config/trixie-minbase-ab.yaml

- `image/gpt/ab_userdata/image.yaml` は immutable GPT A/B レイアウトの `image-rota` layer（層バージョン 6.1.0）です。`X-Env-VarRequires-Valid: regex:^(cm4|pi4|cm5|pi5)$` は cm4 / pi4 / cm5 / pi5 のみを許可します。https://github.com/raspberrypi/rpi-image-gen/blob/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/image/gpt/ab_userdata/image.yaml#L2-L11
- `preimage05-templates` は `tryboot_a_b=1` と `[tryboot]` を含む `autoboot.txt` を生成します。rootfs の既定は EROFS（`rootfs_type: erofs`、`-z zstd,3`）で、ext4 も選択でき、永続データ領域があります。https://github.com/raspberrypi/rpi-image-gen/blob/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/image/gpt/ab_userdata/image.d/hooks/preimage05-templates#L40-L44<br>https://github.com/raspberrypi/rpi-image-gen/blob/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/image/gpt/ab_userdata/image.yaml#L34-L41
- `device/` 層には Pi 3 と Zero 2 W が含まれますが、`image-rota` の許可クラスには含まれません。MBR の `image/mbr/simple_dual`（layer 名 `image-rpios`、ext4 / btrfs）は A/B 構成ではありません。https://github.com/raspberrypi/rpi-image-gen/tree/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/device<br>https://github.com/raspberrypi/rpi-image-gen/tree/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/image/mbr/simple_dual
- `config/trixie-minbase-ab.yaml` の例は `device: rpi5` です。https://github.com/raspberrypi/rpi-image-gen/blob/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/config/trixie-minbase-ab.yaml
- 【一次】Issue #153 は BCM2837 に MBR が必要で `image-rota` は GPT と述べ、2026-02-18 に closed となっています。現行コードでは device class の制約を確認できます。https://api.github.com/repos/raspberrypi/rpi-image-gen/issues/153
- 【未確認】CM0（BCM2837）向けの公式 A/B 構成は確認できていません。同 layer の対応 device class は EEPROM 機種（Pi 4 / Pi 5 系）のみです。MBR + tryboot + RAUC custom は公式コードに裏付けられていない自前構成案です。
- 【未確認】Zero 2 W / Pi 3 で `image-rota` 相当を使った場合の挙動は未確認です。
- 【一次】rpi-image-gen の最新リリースは v2.8.0（2026-08-13）です。Devin が 2026-10-18 に公開資料で確認しました。https://api.github.com/repos/raspberrypi/rpi-image-gen/releases
- 【未確認】firmware の GPT 対応は 2020 年頃に追加されたとの情報がありますが、GPT + hybrid MBR の不具合とともに出典を特定できていません。
- 【未確認】CM0 での GPT の挙動は確認できていません。公式 A/B の GPT 例は EEPROM 機種のもので、BCM2837 の根拠にはなりません。
- 【推測】BCM2837 は ROM 由来の MBR を前提とする方が安全側と考えられます。ただし 6 パーティション構成は MBR のプライマリパーティション 4 つの上限を超えます。回避案として拡張パーティション、`os_prefix` でのスロット分離、スロットごとの `boot.img` への集約がありますが、いずれも未検証です。

### 7.7 関連する最新リリース
Devin が 2026-10-18 に公開資料で確認しました。

- 【一次】rpi-6.18.y は 6.18.57（2026-10-16、Makefile、HEAD 234188315）です。https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/Makefile#L2-L4<br>https://github.com/raspberrypi/linux/commit/234188315037848e5b07d65b85d38edc64095caa<br>https://www.kernel.org/releases.json
- 【一次】Buildroot 2026.08（2026-09-04、commit d5180309）の GCC 既定は 15.3.0 です。16.2.0 は選択可能な候補です。https://github.com/buildroot/buildroot/commit/d5180309b1b66ef3b8eaccca70ad69be8e0729a1<br>https://github.com/buildroot/buildroot/blob/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/package/gcc/Config.in.host#L6
- 【一次】raspberrypi/linux の既定ブランチは rpi-6.18.y です。https://github.com/raspberrypi/linux/tree/rpi-6.18.y
- 【未確認】rpi-eeprom の 2026-05-13 の項目には A/B bootloader update の記載があり、2712（Pi 5 系）向けとの情報があります。「Pi 5 stable 2026-09-25」とする日付は確認できていません。2026-10-15 の更新と firmware 1.20260915 も CM0 とは無関係との情報です。2026-10-18 に API と release notes の HTTP 200 のみを確認し、内容は未確認です。https://api.github.com/repos/raspberrypi/rpi-eeprom/releases<br>https://raw.githubusercontent.com/raspberrypi/rpi-eeprom/master/firmware-2712/release-notes.md
- 【一次】Pi OS 2026-10-06 版は Debian 13、kernel 6.18.50 です。公式 release notes の 2026-10-06 項には `Linux kernel 6.18.50 - cff533aec2fa601846766b32ff57204e0a61bed7` とあり、Imager 一覧にも同日版があります。https://downloads.raspberrypi.com/raspios_arm64/release_notes.txt<br>https://downloads.raspberrypi.com/os_list_imagingutility_v4.json
- 【一次】kernel.org の LTS は 6.18.57（EOL 予定 2028-12）、stable は 7.2.11（2026-10-15）、mainline は 7.3-rc7 です。https://www.kernel.org/releases.json
- 【一次・一部未確認】raspberrypi/linux の `rpi-6.12.y` は 6.12.113、`rpi-7.2.y` は 7.2.11 との情報があります。`rpi-6.12.y` の HEAD SHA は branches API で確認でき、6.12.113 は kernel.org の longterm 値です。https://www.kernel.org/releases.json<br>https://api.github.com/repos/raspberrypi/linux/branches/rpi-6.12.y
- 【一次】Mender Client 6.1.0 は supported-releases で 2026-10 時点の Supported です。https://docs.mender.io/release-information/supported-releases

### 7.8 bundle の検証と巻き戻し（S10）

`msd-update install` は、bundle の 4 ファイルの構成、`manifest.sig` の Ed25519 署名、`manifest` の SHA-256 の順に確かめてから、非 active スロットに書きます。S10 で、署名なし、別の鍵、改ざん、途中で切れた bundle を QEMU のゲストとホストで 5 回ずつ与えました。どれも書き込みの前に拒否され、非 active スロットと状態ファイルは変わりませんでした（[記録](../../experiments/2026-10-25-s10-update-rejection.md)）。

S10 の時点では、`manifest` にバージョンや通し番号がなく、`msd-update` はバージョンを比べませんでした。同じ鍵で署名した bundle なら、古いものでも受け入れました。署名済みの古い bundle を入手した人は、既知の不具合があるバージョンへ戻せました。

2026-10-25 に、利用者は次の 3 案から (b) を選びました。

| 案 | 内容 | 利点 | 欠点 |
|---|---|---|---|
| (a) | いまのまま、古い bundle も受け入れ、方針として文書に書く | 壊れた更新から、古い bundle ですぐ戻せる | 脆弱性のある古いバージョンを、黙って入れられる |
| (b) | `manifest` に番号を入れて署名する。稼働中より小さい番号は既定で拒否し、`--allow-downgrade` を付けたときだけ受け入れる | 戻す手段を残したまま、意図しない巻き戻しを防ぐ | 操作する人が `--allow-downgrade` を付ければ戻せるので、攻撃者が端末を操作できる場合は防げない |
| (c) | 番号が下がる bundle を常に拒否する | 巻き戻しを最も強く防ぐ | 壊れた更新から戻るには、新しい番号で作り直した bundle が要る |

実装では、post-build が番号を rootfs の `/etc/msd-update/version` に書き、post-image が同じ番号を `manifest` の `version` 行に入れて署名します。`msd-update install` は署名と SHA-256 を確かめた後、番号を稼働中のものと比べます。番号の決め方と書式は [UPDATE.md](../../UPDATE.md) にあります。比べる相手は稼働中の rootfs の番号で、`/data` には記録しません。そのため、A/B のどちらから起動しても同じ規則になります。書き換えられない領域（OTP など）は使っていないので、`--allow-downgrade` を付ければ、だれでも古い署名済み bundle に戻せます。

ホストテスト（`tests/msd-update/run.sh`）では、次のことを確かめました。番号が同じ bundle は入ります。古い bundle と番号のない bundle は、`--allow-downgrade` がなければ書き込みの前に拒否され、付ければ入ります。`version` 行が 2 つある、数字でない、先頭が 0、19 桁以上の bundle は、`--allow-downgrade` を付けても拒否されます。署名の後に番号を書き換えた bundle は、署名の検証で拒否されます。稼働中の番号が読めないときは、install を拒否します。比較の行を無効にすると、試験が失敗することも確かめました。QEMU のゲストで番号を比べる試験は、まだ行っていません。

---
