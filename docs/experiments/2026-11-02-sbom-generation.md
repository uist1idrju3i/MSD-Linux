# SBOMのLinux版と生成元の照合

## 目的・判定条件

通常buildのSBOMに残るLinux `custom` を直し、週次securityと同じ版・CPE補正を行う。製品設定や依存の版は変更しない。

成功条件は、同じ入力の5回の補正で出力hashが一致すること、67 componentの名前・版・host/targetと依存参照を確認できること、誤った入力を拒否して元のJSONを変えないこととした。これは静的な生成処理の検査であり、起動性能や実機動作の比較ではない。

## 条件

| 項目 | 値 |
|---|---|
| 改修元 | [916a45e](https://github.com/uist1idrju3i/MSD-Linux/commit/916a45e) |
| 元SBOM | [run 41477653658](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/41477653658)、artifact 13160230834、`images/sbom.cdx.json` |
| 元SBOMのSHA-256 | `8173ae3f8d26ccc6cb932dd39fce9e505cec3eb825a5fe63a8078a1cebf0092a` |
| 元SBOMのproject version | `c96e5faf015c828a213c8ea64f613b4a429196c7`。PR headではなくmerge checkout |
| Buildroot | `8b238854d909c9cce32ef9671d968b03e323b55d` |
| kernel | 固定commit `b3495ea401d709af0701a85babcba5e3d788a602`、Makefileの版6.18.59 |
| kernel MakefileのSHA-256 | `cd22685a313cf843d94e9131c35662393d685d7f76165fdee9914741463d2eff` |
| 開発用OCI | `ghcr.io/uist1idrju3i/msd-dev@sha256:c5beb4973cad6bef273fd0efc51deb89e334de5f5b1700de2f41980410d65d77` |
| OCI内の確認値 | Python 3.13.5、GNU tar 1.35 |
| 補正スクリプトのSHA-256 | `ac7bd58d020089c4d7d3ef493ff5bb2af64f6b8ec8309adb154fc813fa52b59c` |

## 入力を取り違えた試行

最初はVMのGNU tar 1.34環境で作ったshow-info 79項目と、CIの67 componentを比べた。検査は `missing=['host-tar']` で停止した。開発用OCIのtarは1.35で、同じ製品設定のshow-infoは78項目だった。差はhost-tarだけであり、製品の依存欠落を示す結果ではない。

元のrunはshow-infoを保存していないため、開発用OCIで同じ製品設定の構成情報を作り直した。これを元runの入力そのものとは扱わない。構成情報とSBOMは同じ実行環境・同じ呼び出しのものを一緒に保存すべきという検査条件は緩めず、今回のCI変更に含めた。

## 結果

- OCIの構成情報からvirtualとrootfsを除くと67 componentになり、元SBOMの名前・版・host/target・package間の依存と一致した。Linuxの版・CPEだけを6.18.59へ補正し、固定source commitのpropertyを追加した。
- 5回とも終了値0、出力SHA-256は `aeb1af7a213ad1cb9ca7e2611259e48c12880565379dfccf97a79805f953fde4` で一致した。元SBOMのファイルは変更していない。
- 回帰テスト11件が成功した。local Makefileと固定URL取得の同値性、冪等性、virtual provider、過不足・重複、古いproject version、誤ったhost/target・CPE・graphを確認した。URL取得のテストはmockであり、外部サービスの到達性を試したものではない。
- actionlint、ShellCheck、zizmor offlineとPythonの構文検査を実行した。新しいCI生成物の検査はこのローカル静的試験とは別に確認する。

生の値は[CSV](2026-11-02-sbom-generation.csv)、集計と入力hashは[JSON](2026-11-02-sbom-generation.json)にある。SBOM全体の読解と監視の限界は[SBOMの確認範囲](../research/sbom-coverage.md)を参照。

## 再確認

artifactを取得し、`AUDIT_DIR`をその保存先に設定する。元ファイルは書き換えず、別名に写してから試す。既存の同名出力がある場合は別の保存先を使う。

```sh
DEV=ghcr.io/uist1idrju3i/msd-dev@sha256:c5beb4973cad6bef273fd0efc51deb89e334de5f5b1700de2f41980410d65d77
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD:/work" -w /work "$DEV" \
  make -s -C vendor/buildroot BR2_EXTERNAL=/work O=/work/output-sbom-audit \
  msd_cardputerzero_defconfig
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD:/work" -w /work "$DEV" \
  make -s -C output-sbom-audit show-info > "$AUDIT_DIR/show-info.json"
curl --fail --location \
  https://raw.githubusercontent.com/raspberrypi/linux/b3495ea401d709af0701a85babcba5e3d788a602/Makefile \
  > "$AUDIT_DIR/Makefile"
cp "$AUDIT_DIR/images/sbom.cdx.json" "$AUDIT_DIR/sbom-copy.json"
python3 .github/scripts/set-kernel-version.py "$AUDIT_DIR/sbom-copy.json" \
  --kernel-makefile "$AUDIT_DIR/Makefile" \
  --show-info "$AUDIT_DIR/show-info.json" \
  --project-version c96e5faf015c828a213c8ea64f613b4a429196c7
tests/check-sbom/run.sh
```

show-infoにはsource_dirなど生成場所の文字列も含まれる。JSONのhash一致だけでなく、componentと依存関係を比べる。新しいCIでは同じ呼び出しのshow-infoがartifactに入るため、作り直さず保存されたものを使う。
