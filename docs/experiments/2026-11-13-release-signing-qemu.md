# 初回本番署名bundleのQEMU受入試験

- 日付: 2026-11-13
- 状態: QEMU受入・B指定起動を確認。実機未確認
- 入力: [release run 43331379685](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/43331379685)、commit `7a64c8563a7d72776886648d2bf12a549edf0c66`

## 目的と採否の基準（実行前）

管理者が取得した未署名build artifactのSD imageを起動し、同じrunの本番署名bundleをguest内の製品`msd-update`で検査します。秘密鍵は扱わず、製品codeを変更しません。

1. image内と起動中guestの公開鍵DER fingerprintが、repoのrelease-1公開鍵と一致すること。
2. 改変signatureと署名なしbundleをguestが拒否し、非稼働slotのhash・write counter・更新状態が不変であること。
3. 正常bundleは同一内部versionなので、通常installの実結果を記録すること。拒否なら理由を区別し、利用可能な文書化済みoptionだけで追加試験します。
4. 受理時はB slotへのwrite counter増加、payloadの読戻しhash、installed状態を確認すること。そのSD copyのB rootfsとboot payloadから起動し、version・鍵・slotを照合すること。

機能確認のため各条件1回です。性能の中央値や実機の信頼性は結論にしません。拒否条件と正常条件で計測器の反応を確認します。元artifactを変更せず、作業用SD copyだけに書き込みます。

## QEMUとの境界

既存`run-qemu.sh`を使いました。QEMUには実機firmwareのtryboot経路がないので、DTBの写しへ起動slot情報を与え、A終了後は同じSD copyのB payloadと`root=/dev/mmcblk0p6`で別に起動しました。これを実機のtryboot成功とは扱いません。実SD・電断・firmwareのslot選択・鍵移行は未確認です。

raw serial logはbyte列を変えずgzipで保存し、この実験記録と同じ`docs/experiments/`へ収録します。大きなartifact・SD imageはcommitせず、run URLとhashだけを残します。

## 固定した入力と条件

| 項目 | 値 |
|---|---|
| 実験checkout | `ff1a0bee68dbed40c08f6cdd270e3718a6c0b303`から分岐。変更は測定器・記録だけ。製品code・既存harness・vendorは無変更 |
| Buildroot gitlink | releaseとcheckoutとも`8b238854d909c9cce32ef9671d968b03e323b55d` |
| build状態 | 今回buildなし。CI artifactを再利用。cold/warmやccacheを比較した実験ではない |
| hostと実行環境 | Ubuntu 26.04.1 LTS、Linux 7.0.0-43-generic x86_64。開発用imageはDebian 13.7。準備はhost Python 3.14.4、測定器はcontainer Python 3.13.5 |
| guest binary | Linux 6.18.59-v8、build bannerのGCC 14.3.0 / binutils 2.43.1、OpenSSL 3.5.9。実際のbannerはraw logに保持 |
| QEMU | 開発用image内の11.1.2、`raspi3ap`、512 MiB、icountなし。SD copyを1 GiBへ末尾拡張 |
| 開発用image ID | `sha256:47cc0b8cfd878a4fb413c376d52a2b6a9199454c97b1d2aec8df7a3a1b4a8e7d` |
| QEMU binary SHA-256 | `c8cf5be13646711580e18346dcd036c0f2a210dd90f84bf784247c5838940410`（`/usr/local/bin/qemu-system-aarch64`） |
| 公開鍵DER SHA-256 | `ec181b24375d93e884e05888d8348900fd1bc6405e225696716dc9feeb7f1f42`。imageから抽出して照合。`key-origin=release` |
| 製品client SHA-256 | `a825fe84d748f4f9f8ad52697826e7e65cad0dfd3465dd26d2102e21082d0b16`。imageから抽出した本文とrelease commitの`usr/sbin/msd-update`が一致 |
| version | manifestとimageの`/usr/share/msd-update/version`とも`1794526865` |
| 搬送 | 正常・signature改変・未署名のtarをread-only仮想USB FATへ収録。guestでは`/dev/sda`全体を`/run/bundles`へro mount。製品rootfsに試験器を追加しない |

| 入力 | bytes | SHA-256 |
|---|---:|---|
| `release-unsigned-43331379685-1.zip` | 86216160 | `29884ddef8072dedd7dd7af979045121d7b5ee75bafb7c17bb162e6d1723d981` |
| `release-signed-1.zip` | 28904777 | `b52936f9178a43ee350b46bb2bba09a4b3850156f9ca2be43ebd604fc57048d4` |
| `unsigned/sdcard.img.xz` | 57416204 | `886e548c52713edad346700afa72613760699b95a42e65192a9b8fa8b909a420` |
| 展開後の元SD | 771751936 | `5d95661f0a392f3fb0dab90df9b9e96a2abd8065050ccccdad5938ffd91e2ce6` |
| 正常`msd-update-bundle.tar` | 87797760 | `c17daf7316dd38624c5ce7e85e46efcebf52fac3fb5b54064bec54f7adf37b0a` |
| `msd-update-bundle.unsigned.tar` | 87797760 | `5afcbe696e88920dfe345bf869700faf76ab23db579d744c7cbe14e14c9642b7` |
| signature改変tar | 87797760 | `6715bce1c848241045776b76f4f9cd43e191ccfb55387556b21a6da08e4a735d` |

signed zipとsign jobのupload digest一致、host上の署名・改変manifest拒否は管理者の先行確認です。今回は受領fileのhashを独立に再採取しましたが、job logのdigestを直接再照会していません。上記runのartifactであり、immutable Release全assetの検証という意味ではありません。

## 再実行手順

`INPUT`は管理者が取得・展開した入力directoryです。次のhost側処理は元入力を読むだけで、未使用の`output-release-signing-qemu/`へ作業用fileを作ります。offsetとpayload長はこの固定artifact専用です。

```sh
export INPUT=/absolute/path/to/release-run-43331379685
python3 - <<'PY'
import io, lzma, os, shutil, tarfile
from pathlib import Path
s = Path(os.environ['INPUT'])
p = Path('output-release-signing-qemu')
p.mkdir(exist_ok=False)
for d in ['images', 'transfer']:
    (p / d).mkdir()
with lzma.open(s / 'unsigned/sdcard.img.xz') as src, (p / 'original.img').open('xb') as dst:
    shutil.copyfileobj(src, dst)
with (p / 'original.img').open('rb') as src:
    for name, sector, size in [('original-boot.vfat', 40960, 67108864),
                               ('original-rootfs.squashfs', 311296, 20676608)]:
        src.seek(sector * 512)
        (p / name).write_bytes(src.read(size))
shutil.copyfile(s / 'signed/msd-update-bundle.tar', p / 'transfer/signed.tar')
shutil.copyfile(s / 'unsigned/msd-update-bundle.unsigned.tar', p / 'transfer/unsigned.tar')
with tarfile.open(p / 'transfer/signed.tar') as src, tarfile.open(p / 'transfer/tampered.tar', 'w') as dst:
    for member in src:
        stream = src.extractfile(member)
        if member.name == 'manifest.sig':
            data = bytearray(stream.read())
            data[0] ^= 1
            stream = io.BytesIO(data)
        dst.addfile(member, stream)
PY
docker/msd-dev bash -c '
  set -eu
  p=output-release-signing-qemu
  unsquashfs -cat "$p/original-rootfs.squashfs" usr/share/msd-update/update-key.pem |
    openssl pkey -pubin -outform DER | sha256sum
  mcopy -i "$p/original-boot.vfat" ::kernel8.img "$p/images/Image"
  mcopy -i "$p/original-boot.vfat" ::bcm2710-rpi-cm0.dtb "$p/images/base.dtb"
  cp "$p/images/base.dtb" "$p/images/a.dtb"
  fdtput -p -t x "$p/images/a.dtb" /chosen/bootloader partition 2
  fdtput -p -t x "$p/images/a.dtb" /chosen/bootloader tryboot 0
  truncate -s 512M "$p/transfer.vfat"
  mformat -i "$p/transfer.vfat" -F ::
  mcopy -i "$p/transfer.vfat" "$p"/transfer/*.tar ::/
'
docker/msd-dev python3 board/cardputerzero/tools/bench/release-signing-qemu/run.py \
  --prepared output-release-signing-qemu --run-dir output-release-signing-qemu/a2 --stage a
```

測定器はserialでroot loginし、`guest.sh`だけを`/run`へbase64で転送します。製品clientを`MSD_UPDATE_*`で差し替えず、鍵・version・block deviceは製品の既定pathを使います。改変signatureは64 byte中の先頭1 byteだけをXORし、payloadとmanifestはそのままです。未署名は管理者が取得した未署名tarそのものです。

実行するguest commandは次の3つです。戻り値、全p3・全p6のSHA-256、statの生の全欄、installed状態を各条件の前後に出します。statの7欄目は512-byte sectorの累積write数です。正常install後はmanifestのpayload長でも再度読戻します。

```sh
msd-update install /run/bundles/tampered.tar
msd-update install /run/bundles/unsigned.tar
msd-update install /run/bundles/signed.tar
```

次の処理で、書き込み後の同じSDからB bootを抽出します。Aと同じhost fileを単に再指定するのではなく、実際のp3のkernel・DTBを使います。`run-qemu.sh`の既定処理により、DTB copyのBluetooth nodeも無効になります。

```sh
dd if=output-release-signing-qemu/working.img \
  of=output-release-signing-qemu/b-written.vfat bs=512 skip=172032 count=131072 status=none
docker/msd-dev bash -c '
  set -eu
  p=output-release-signing-qemu
  mcopy -i "$p/b-written.vfat" ::kernel8.img "$p/images/b-Image"
  mcopy -i "$p/b-written.vfat" ::bcm2710-rpi-cm0.dtb "$p/images/b.dtb"
  fdtput -p -t x "$p/images/b.dtb" /chosen/bootloader partition 3
  fdtput -p -t x "$p/images/b.dtb" /chosen/bootloader tryboot 1
'
docker/msd-dev python3 board/cardputerzero/tools/bench/release-signing-qemu/run.py \
  --prepared output-release-signing-qemu --run-dir output-release-signing-qemu/b1 --stage b
```

`msd-update try`のfirmware reboot命令は実行せず、この別bootをQEMUのnext-boot相当とします。QEMUが自律的にBを選んだ証拠でも、firmwareへのreboot引数が伝達した証拠でもありません。

## 失敗した試行・測定器の確認

- A初回`a1`は正常installの終了値0・B installed出力・p3 write増加までは観測しましたが、最後のp6全域hash中に測定器の900秒deadlineへ達しました。全体の成功へ振り替えず、途中logとdriverの`TimeoutError`を保存します。
- `a1`の製品変更や負試験条件の緩和はせず、終了後に測定器の完了待ちだけを2400秒へ延長。元imageから新しいSD copyとrun ID `a2`を作りました。初回のSD copyは残しています。
- USB FATはsuperfloppyです。kernelがsector 0をpartition tableとしても解釈し、`sda: p1 size ... extends beyond EOD`を出します。`/dev/sda1`を使わずwhole deviceをro mountし、3 tarのguest hashがhostと一致することを確認します。製品SDのpartitionエラーとは区別します。
- 新規parserの正常・空・欠損・不正結果・hash変化・write変化・B情報欠損をhost unit testで確認しました。正常installでwrite増加を検出し、拒否条件では0を検出することが測定器の対照です。

## 結果

完了したA試行`a2`とB試行`b1`は、測定器の終了値がともに0でした。A初回`a1`は未完了として別に保持します。[CSV](2026-11-13-release-signing-qemu.csv)の`valid=0`が未完了試行で、成功回へ混ぜません。

| 条件（`a2`） | install終了値 | p3 write sector | p6 write sector | installed |
|---|---:|---:|---:|---|
| 前 | — | 0 | 0 | なし |
| signature先頭1 byte改変後 | 1 | 0 | 0 | なし |
| 未署名tar後 | 1 | 0 | 0 | なし |
| 本番署名tar後 | 0 | 131072 | 40384 | `3`（B） |

改変signatureは`msd-update: bundle signature verification failed`、未署名tarは`msd-update: bundle must contain exactly four files`で拒否しました。後者には`manifest.sig` memberがなく、署名検証に入る前の構造検査で拒否されています。両拒否後のp3全64 MiBとp6全256 MiBのhashは、試験前と一致しました。

正常tarは`rootfs.squashfs: OK`、`boot.vfat: OK`、`Installed slot B (boot partition 3).`を出しました。**同一versionを通常installで受理し、`--allow-downgrade`は使っていません。** このreleaseの`check_version()`が拒否するのは厳密に小さい番号だけです。観測とsourceが一致し、追加optionでの受理試験は不要でした。

正常時のwrite増加はbootの67,108,864 byteとrootfsの20,676,608 byteに一致します。既存Bも同じpayloadだったため、正常時も全partition hashは変わりません。**hashが変わらないことだけでwriteなしとは判定せず、counter増加・製品の読戻し検査・installed状態を合わせて確認しました。** payload長での追加読戻しもmanifestと一致しました。

| 対象 | SHA-256 |
|---|---|
| rootfs payload 20676608 byte | `1eaa81c3cd3dfb1c6c458122f8d0cfa504f76725055bd60cf46f4fd51ead0d4a` |
| p3全体＝boot payload 67108864 byte | `1d00199d1b9977efc739a26fab9a92ae39af4af595bf963c205ff6eb6154c234` |
| p6全体256 MiB（末尾を含む） | `f5cc5c8348ce111f1aa68a4e6354d07e25e9570490822271411be8b6f3864cc8` |

B試行ではkernelが`VFS: Mounted root (squashfs filesystem) readonly on device 179:6.`を出し、`root=/dev/mmcblk0p6`から起動しました。guestは内部version `1794526865`、commit表示`7a64c85`、同じrelease鍵、`slot=B partition=3 tryboot=1`を報告しました。既存`S99msd-health`が`Committed slot B (boot partition 3).`を出し、installed状態は消え、p1の`autoboot.txt`はdefault `3`・tryboot `2`へ変わりました。

`tryboot=1`は与えたDTBの固定値なので、commit後もそのbootのstatusに残ります。実際のfirmware選択やreboot引数の伝達は確認していません。

### 保存した生ログ

| 試行 | raw serial | driver |
|---|---|---|
| `a1`（未完了） | [gzip](2026-11-13-release-signing-qemu-a1-serial.log.gz) | [timeout](2026-11-13-release-signing-qemu-a1-driver.log.gz) |
| `a2`（完了） | [gzip](2026-11-13-release-signing-qemu-a2-serial.log.gz) | [結果](2026-11-13-release-signing-qemu-a2-driver.log.gz) |
| `b1`（完了） | [gzip](2026-11-13-release-signing-qemu-b1-serial.log.gz) | [結果](2026-11-13-release-signing-qemu-b1-driver.log.gz) |

[初回測定器の写し](2026-11-13-release-signing-qemu-a1-runner.py.gz)も保存しました。現在の測定器との差は900秒から2400秒への完了待ち延長だけです。CSVには元byte列とgzipのhash、元byte数、全stat欄、3回のharness入力hash・環境、測定器・guest hookのhashを収録しました。gzipを展開したbyte列と元logを照合し、原文を整形していません。

```sh
gzip -dc docs/experiments/2026-11-13-release-signing-qemu-a2-serial.log.gz
python3 tests/release-signing-qemu/run.py
```

rawには仮想USBのgeometry警告のほか、aux-uartのprobe失敗、存在しないmmc1の初期化失敗、初回`/data`拡張時のpartition table再読込失敗が残っています。Aは拡張完了とloginへ進み、Bもlogin・health commitまで到達しました。これらを消していませんが、実機driverの正常動作を確認したとも扱いません。

このreleaseは後続mainとは異なる固定commitです。`Saving 256 bits of creditable seed for next boot`や`/data`拡張もrawにあり、後続のseed非保存実装をbackportしていません。非稼働p3/p6と更新状態の負試験であり、SD全体のidle writeが0という試験ではありません。

## 作業メモ・残件

今回の作業範囲は配備された本番公開鍵に対するartifactのguest受理、同一versionの挙動、仮想SDへのwrite、手動指定したBの起動です。実SD・FTL、実機firmware tryboot・watchdog fallback・電断、LCD・keyboard・I2C、開発鍵からの移行、失効とanti-rollback全体、GitHub取得client、immutable publish・attestation・SD image全体の署名は未確認です。製品codeの修正、clean rebuild、性能比較は行いません。
