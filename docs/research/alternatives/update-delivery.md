# 更新経路、配信制約、差分方式

[代替比較](README.md) / [更新framework](updates.md) / [暗号・TLS](crypto.md) / [ネットワーク](network.md) / [署名](signing.md) / [build option](update-build-options.md) / [RESEARCH](../../../RESEARCH.md)

## 前提と現在の方針

2026-11-03に、MSD/Linuxの`origin/main` `94915bfef27f0d50ae0f4c6e24ffa98daf68a12e`と、固定Buildroot `8b238854d909c9cce32ef9671d968b03e323b55d`を基準に確認しました。暗号libraryはOpenSSLを採用する方針（2026-11-03 利用者決定）、差分更新は必須でnetwork依存可。記載したframework構成のbuild、QEMU、実機での更新は本リポジトリでは試していません。

## 更新fileを渡す4つの経路

| 経路 | 内容 | RAUC | SWUpdate |
|---|---|---|---|
| P1 | 本体によるonlineの差分更新 | adaptive（`block-hash-index`）とHTTP streaming、またはcasync | delta handler（zchunkとHTTP range要求）、または直前の版からのrdiff |
| P2 | 本体によるonlineのfull更新 | verity bundleのstreaming | `.swu`のdownload handler |
| P3 | 別端末で更新fileをSDに置き、本体が読む | local bundleをinstall | local `.swu`をinstall |
| P4 | 別端末でimageを書き直すclean install | frameworkは使わず`sdcard.img.xz`とSHA-256で検証 | 同左 |

P3の置き場所は、利用者の判断で`/data`に決めました（2026-11-03）。電源断の扱いと、信頼できないfile systemを読む危険も設計対象です。P4は工場出荷状態に戻す手段で、`/data`も消えます。

RAUCのadaptiveは4 KiB blockごとのSHA-256 index（imageの約0.8%）をbundleに含めます。install時に両slotの一致blockを再利用し、残りをHTTP range要求で取得します。上流の例ではext4上の1 packageを更新した場合、bundleの約10%の取得で済みました。block device限定で、SquashFSではblock size（例: `-b 64k`）により効果が変わります。

## 配信先の制約と確認結果

| 配信先 | 制約 | 2026-11-03の確認 |
|---|---|---|
| GitHub Releases | 1 assetあたり2 GiB未満、1 Releaseあたり1000 assetまで。合計容量と帯域の上限はない | `v0.0.0/sdcard.img.xz`へのrange要求は302でrelease-assetsへ転送され、206と`content-range: bytes 0-1023/57515900`が返った |
| GitHub Pages | site全体1 GB、月100 GBのsoft limit、rate limitあり | HTMLへのrange要求は`accept-ranges: bytes`を返したがHTTP 200。binary fileで206が返るかは未確認 |
| Cloudflare Pages | 1 fileあたり25 MiB、Free planで20,000 fileまで | 未確認。現行`sdcard.img.xz`は約57.5 MBのため、そのまま置けない。casyncのchunk storeなら置ける見込み（推測） |
| VPS上のIPFS | 自分で運用するP2P配信 | 未確認。端末から使うにはgatewayかIPFS clientが必要。peerのIP公開、RAMと常駐費用、可用性を自分たちで担う必要がある |

上限の出典は[GitHub Releasesの制限](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)、[GitHub Pagesの制限](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits)、[Cloudflare Pagesの制限](https://developers.cloudflare.com/pages/platform/limits/)です。range確認は2026-11-03に行ったもので、配信先の将来の動作を保証しません。

## 差分の作り方

| 方式 | 元にする版 | 配信側 | 条件と制約 |
|---|---|---|---|
| RAUC adaptive | 任意の版。端末の両slotから一致blockを探す | range要求に対応する静的配信 | block deviceに限る。SquashFSではblock sizeと圧縮率で効果が変わる |
| RAUC casync | 任意の版 | chunk store | bundleの変換が必要。RAUCのBuildroot recipeにcasyncがないという点は未確認 |
| SWUpdate zchunk | 任意の版 | range要求に対応する配信 | zchunk packageが必要 |
| SWUpdate rdiff | 直前の版 | 静的配信 | 2つ以上前の版からはfull更新か連続適用が必要 |
| 現行`msd-update` | - | full image | 差分更新なし |

SWUpdateのdelta handlerはzchunkとcurlを使い、chunk headerを比較して不足分をHTTP rangeで取得します。rdiff（librsync）は既知の版からの差分を適用します。microSDやUSBから更新する場合、差分化で減るnetwork取得量の利点はありません。

## 現行コードの検証範囲

`board/cardputerzero/rootfs-overlay/etc/init.d/S99msd-health`と`board/cardputerzero/rootfs-overlay/usr/sbin/msd-update`で確認した現行動作は次のとおりです。

- 起動時の検査はtrybootのときだけ動き、rootがSquashFSであること、`/data`がext4であること、`/run/msd-ready`があることを確認します。rootfsの中身は照合しません。
- install時はmanifestの署名、bundle内の各fileのSHA-256、書き込んだslotを読み直したときのSHA-256を照合します。
- `msd-update commit`でslotを切り替えた後は、firmwareのtrybootによる自動切り戻しは働きません。

## 上流と固定Buildrootの資料

- [RAUC v1.15.2 advanced.rst](https://raw.githubusercontent.com/rauc/rauc/v1.15.2/docs/advanced.rst)
- [SWUpdate 2026.05.1 delta-update.rst](https://raw.githubusercontent.com/sbabic/swupdate/2026.05.1/doc/source/delta-update.rst)
- [SWUpdate 2026.05.1 signed_images.rst](https://raw.githubusercontent.com/sbabic/swupdate/2026.05.1/doc/source/signed_images.rst)
- 固定Buildrootのpackage定義: `vendor/buildroot/package/rauc/Config.in`, `vendor/buildroot/package/rauc/rauc.mk`, `vendor/buildroot/package/swupdate/Config.in`, `vendor/buildroot/package/swupdate/swupdate.mk`
