# 開発用OCIのセキュリティ更新

- 状態: 完了（amd64ローカル検証まで）
- 日付: 2026-11-03
- 担当: Devin
- 関連: [R25](../research/pending-work.csv)、[開発用OCIの脆弱性調査](../research/development-image-security.md)、[開発環境とCIの依存監査](../research/dependencies/development-and-ci.md)

## 目的と仮説

開発用OCIにある`libbrotli1`の`CVE-2026-111497`と、同じTrivy DBで確認した他の45件の公開ゲート対象を、Debian snapshotの更新で解消できるか確かめる。snapshotやbase imageのdigest、Go stage、Trivyの版、gateの閾値と例外は変更しない。

## 採否の基準

依頼時に指定された基準は、amd64 OCIのbuildが成功し、固定Trivy 0.76.1の公開ゲート対象が0件になること。1件でも残れば除外や閾値変更をせず、残件を分類して停止する。

## 条件

| 項目 | 値 |
|---|---|
| 基準commit | `d4312cbbae26407356c29455eb2a46656528340b`（origin/main） |
| 作業branch | `devin/1793676513-brotli-security` |
| host | Ubuntu 26.04.1、x86_64 |
| OCI build | amd64、`msd-dev:local` |
| Buildroot / 製品kernel | 製品buildは実施せず |
| OCI内の確認版 | QEMU 11.1.2、GCC 14.2.0-19、Python 3.13.5、Go 1.27.3 |
| Trivy | 0.76.1、`sha256:790fd66d1697395d8693d1acaa1ea702406a20f109b6fc7bac8db623eca6c06c` |
| Trivy DB | version 2、UpdatedAt `2026-11-03T01:30:30Z` |
| 旧snapshot | `20261019T190000Z` |
| 初回snapshot | `20261023T210712Z` |
| 最終snapshot | `20261103T023120Z` |
| 繰り返し | buildとgateは各1回。性能測定ではなく、build可否とgateの合否を確認するため |
| 変えない条件 | Debian/Golang base digest、Go stage、QEMU source版、Trivy digest、gate基準 |

## snapshotの選択

2026-11-03にsnapshot.debian.orgの[debian](https://snapshot.debian.org/archive/debian/?year=2026&month=11)で最新の記録`20261103T023120Z`を確認した。同日の[debian-security](https://snapshot.debian.org/archive/debian-security/?year=2026&month=11)の最新記録は`20261103T013555Z`だった。選んだ時刻のURLで、次の3つの署名済みindexを取得できることを確認した。

- [debian trixie](https://snapshot.debian.org/archive/debian/20261103T023120Z/dists/trixie/InRelease)
- [debian trixie-updates](https://snapshot.debian.org/archive/debian/20261103T023120Z/dists/trixie-updates/InRelease)
- [debian-security trixie-security](https://snapshot.debian.org/archive/debian-security/20261103T023120Z/dists/trixie-security/InRelease)

いずれもHTTP 200で、snapshotのapt sourceを使ったbuildも3 suiteから取得できた。

## 手順

```sh
docker/msd-dev build
docker run --rm --entrypoint dpkg-query msd-dev:local \
  -W -f='${binary:Package}\t${Version}\n' | LC_ALL=C sort
docker save --output output/msd-dev.tar msd-dev:local
docker run --rm --volume "$PWD/output:/work" \
  --volume "$PWD/output/trivy-cache:/root/.cache/trivy" \
  ghcr.io/aquasecurity/trivy:0.76.1@sha256:790fd66d1697395d8693d1acaa1ea702406a20f109b6fc7bac8db623eca6c06c \
  image --input /work/msd-dev.tar --scanners vuln,secret,misconfig \
  --format json --output /work/trivy.json
docker/msd-dev python3 .github/scripts/trivy-gate.py report \
  output/trivy.json --findings-json output/trivy-findings.json \
  > output/trivy-report.md
docker/msd-dev python3 .github/scripts/trivy-gate.py gate output/trivy.json
```

実際の走査は固定OCIをtarに保存し、digest固定Trivy containerで行った。gateのreportとgateはリポジトリの`.github/scripts/trivy-gate.py`を使った。

## 初回のBrotliだけの試行

最初は`20261023T210712Z`を選び、`libbrotli1`だけを更新した。snapshotの`20261023T210711Z`にあるtrixie-security amd64 Packages indexには修正版のstanzaがなく、`210712Z`には`1.1.0-2+deb13u1`が載っていた。旧imageと初回imageはいずれも231 packageで、変更は次の1件だった。

| package | 旧版 | 初回 |
|---|---|---|
| `libbrotli1:amd64` | `1.1.0-2+b7` | `1.1.0-2+deb13u1` |

同じTrivy DBで旧imageは46件、Brotliだけ更新したimageは45件の公開ゲート対象となり、gateは失敗した。残った45件の修正がDebianのsnapshotにあると利用者が判断したため、R25を「開発用OCIの公開ゲート解消」へ広げた。この試行では閾値や例外を変更していない。

## 導入済みpackageの差分と変更履歴

旧image（`20261019T190000Z`）と最終imageはいずれも231 packageだった。全差分は次の2件である。

| source package | binary package | 旧版 | 最終版 | Debian changelogの評価 |
|---|---|---|---|---|
| `brotli` | `libbrotli1:amd64` | `1.1.0-2+b7` | `1.1.0-2+deb13u1` | Security Teamの完全なentryは不正streamを早く検出・報告する`CVE-2026-111497`修正で、通常の圧縮streamの形式は変えない。 |
| `linux` | `linux-libc-dev` | `6.12.113-1` | `6.12.115-2` | `6.12.115-1`のupstream stable updateと多数のsecurity・bug fix、および`6.12.115-2`のs390x向けrevertを含む。UAPI headersを使うhost-native buildに影響する可能性がある。 |

Brotliのchangelogは[Debian source](https://sources.debian.org/data/main/b/brotli/1.1.0-2+deb13u1/debian/changelog)、Linuxのchangelogは[Debian snapshot source package](https://snapshot.debian.org/package/linux/6.12.115-2/)で、旧版`6.12.113-1`から新しい`6.12.115-2`までの全entryを確認した。変更されたのは既存の2 packageで、`gcc`、`binutils`、`make`、`python3`、`qemu`、`git`、`curl`、`openssl`、`perl`、`gawk`の版は変わらなかった。

`linux-libc-dev`は開発用containerのhost headersである。Buildrootのtarget sysrootや製品kernel sourceを置き換える変更ではないが、host側でLinux UAPIをincludeするbuildには影響し得る。製品Buildroot buildは行っていないため、影響がないとは断定しない。Brotliの更新は不正streamの扱いを早く報告する変更である。製品buildへの具体的な影響は未確認である。

## gateの結果

最終image IDは`sha256:47cc0b8cfd878a4fb413c376d52a2b6a9199454c97b1d2aec8df7a3a1b4a8e7d`、architectureはamd64、QEMUは11.1.2だった。Trivyは脆弱性1,575件を報告したが、公開ゲート対象は0件、秘密情報0件、設定不備0件で、gateは成功した。脆弱性の総件数は、公開ゲート対象数や製品rootfsの検出数を意味しない。

## 回帰検証

- `docker/msd-dev tests/msd-update/run.sh`: 成功。
- `tests/check-pins/run.sh`: 初回はsnapshotの古さを検査するfixtureの日付が新snapshotから30日未満で失敗した。fixtureの日付を`2026-12-04`に直して再実行し、成功。
- `check-links.py`、`check-jisx0213.py`、`check-doc-size.py`、各`tests/*/run.sh`、yomiyasu lint: 最終文書更新後に実施する。

Buildroot製品build、QEMU boot、arm64 build、CI、attestationは未確認である。

## 結論

amd64の開発用OCIはsnapshot更新後にbuildでき、指定されたTrivy gateの対象は0件となった。閾値や除外は変更していない。公開前に同一commitのCIでarm64とattestationを確認する。QEMUの起動成功、実機、Buildroot製品の動作をこの試験の結論に含めない。

## ログと保存範囲

build log、旧・新imageのdpkg inventoryと差分、Trivyの選別済みfinding、report、gate出力、image tarは作業領域に保存した。raw Trivy JSONはreport作成後に削除した。再生成時は上記コマンドを使う。artifactのSHA-256は作業記録と最終報告に示す。これらの未加工artifactはリポジトリに含めない。
