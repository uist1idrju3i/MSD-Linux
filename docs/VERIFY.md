# 実機確認手順

CardputerZero 実機で行う確認の手順をまとめます。現時点で収録するのはカメラ（S2 の実機確認）のみで、IR（S7）や電源断（S9）の手順は実機が入手でき次第ここに追加します。

## 前提

- `output/images/sdcard.img` を microSD に書き込み、CardputerZero に装着してシリアルコンソールから root でログインできること。
- 対象のイメージには `v4l2-ctl`、`media-ctl`、`ir-keytable`、`ir-ctl` が含まれます。post-build で `libv4l-utils` のその他のツールと RC keymap は削除しています。
- 確認スクリプトは [board/cardputerzero/tools/hw/camera-check.sh](../board/cardputerzero/tools/hw/camera-check.sh) です。target 上で実行するため、次のどちらかでデバイスへ転送します。
  - シリアルコンソールで `cat > /tmp/camera-check.sh` を実行し、スクリプト本文を貼り付ける。
  - microSD の p7（`/data`、ext4）をホストにマウントし、`/data/camera-check.sh` として配置する。

## カメラ（IMX219）

実行は次のとおりです。

```sh
sh /tmp/camera-check.sh
# または /data に置いた場合: sh /data/camera-check.sh
```

結果は `/tmp/camera-check/` 以下に `dmesg.txt`、`media-topology.txt`、`formats.txt`、`stream.txt`、`frame.raw` などとして残ります。終了時に `RESULT pass=<n> fail=<n>` を表示し、fail が 0 なら終了ステータス 0 です。

Standard（IMX219 実装）で期待する結果は次のとおりです。

- `dmesg` に `imx219` の kernel message があり、sensor の検出を確認できる。
- `/proc/modules` に `imx219` と `bcm2835_unicam` がある。
- `media-ctl -p` の topology に `imx219` entity があり、CSI1 2-lane 経路が構成されている。
- `v4l2-ctl --set-fmt-video=width=3280,height=2464,pixelformat=RG10` が成功し、`--stream-mmap` で 30 frame 受信できる。
- `frame.raw` が 3280x2464 の RAW10 に相当するサイズ（約 10 MB）で採取される。

Lite（センサー未実装）で期待する結果は次のとおりです。

- sensor が存在しないため probe は失敗しますが、その際の実際の kernel message は未確認項目です。`dmesg.txt` を保存し、[hardware-spec.md](research/hardware-spec.md) の「Lite 版の probe failure は想定内」の行に記録される実際の message を追記してください。

確認が終わったら、出力ディレクトリの内容（特に `dmesg.txt` と `media-topology.txt`）を保存し、[simulation-plan.md](research/simulation-plan.md) の S2 行と hardware-spec.md の未確認項目を実測値で更新してください。
