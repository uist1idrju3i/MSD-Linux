# RAUC 1.15.2のoption棚卸し

[component option索引](README.md) / [導入契約](../../design/rauc-update-contract.md) /
[代替framework](../alternatives/updates.md) / [既存build調査](../alternatives/update-build-options.md)

## 対象・一次資料・最新版

PR #282の[配信・adaptive調査](../alternatives/update-delta.md)を引き継ぐ。
比較本文は複製せず、本書は全optionと採否、導入契約は製品の不変条件と後続PRを扱う。
基準mainは`82c72840215a287c06bf62828d8159d1aab78f6e`、
Buildroot gitlinkと実checkoutはともに`bbbdab36565d4941b6b0449a0eedb5aac8a10c2e`。
[recipe](https://github.com/buildroot/buildroot/blob/bbbdab36565d4941b6b0449a0eedb5aac8a10c2e/package/rauc/rauc.mk)はRAUC 1.15.2を固定している。
製品への導入・build・性能測定は本PRでは行っていない。

上流tag `v1.15.2`のcommitは`4fb7c798d6ae412344fb8f8d310d773046af3441`。
2026-11-23の[latest release API](https://api.github.com/repos/rauc/rauc/releases/latest)応答は
`v1.15.2`、公開時刻は`2026-03-27T10:47:01Z`だった。
したがって固定版と最新stableのoption差・既定値差は0である。
開発masterを最新stableと読み替えず、将来の更新時は再採取する。
原本のhash・識別子一覧・件数は[照合記録](rauc-inventory.json)にある。

| 一次資料 | 用途 |
|---|---|
| [meson_options.txt](https://github.com/rauc/rauc/blob/v1.15.2/meson_options.txt)、[meson.build](https://github.com/rauc/rauc/blob/v1.15.2/meson.build) | RAUC固有build option、既定値、依存、使用するMeson共通option |
| [reference.rst](https://github.com/rauc/rauc/blob/v1.15.2/docs/reference.rst) | system.conf、manifest、hook環境変数の定義 |
| [config_file.c](https://github.com/rauc/rauc/blob/v1.15.2/src/config_file.c)、[manifest.c](https://github.com/rauc/rauc/blob/v1.15.2/src/manifest.c) | parserと文書の照合、旧alias、既定値・生成値 |
| [main.c](https://github.com/rauc/rauc/blob/v1.15.2/src/main.c) | 全CLI定義。非表示互換optionと条件compileの両分岐を含む |
| [integration.rst](https://github.com/rauc/rauc/blob/v1.15.2/docs/integration.rst) | kernel Kconfig、cmdline、custom backend |
| [advanced.rst](https://github.com/rauc/rauc/blob/v1.15.2/docs/advanced.rst)、[hash_index.c](https://github.com/rauc/rauc/blob/v1.15.2/src/hash_index.c) | adaptive、4 KiB index、保存と再利用 |
| [Config.in](https://github.com/buildroot/buildroot/blob/bbbdab36565d4941b6b0449a0eedb5aac8a10c2e/package/rauc/Config.in)、[Config.in.host](https://github.com/buildroot/buildroot/blob/bbbdab36565d4941b6b0449a0eedb5aac8a10c2e/package/rauc/Config.in.host) | target全6 symbolとhost symbol、depends/select |

## 採否表と母集団

全295行の[採否表CSV](rauc-options.csv)に、面・scope・option token・意味・既定値・
固定版での利用可否・最新stableとの差・計画値・採否・理由・一次資料の行を記載した。
採用109、不採用181、保留5である。署名時刻と内部版の採用決定を反映した計画であり、製品への適用は未実施。
「採用」は計画上の使用又は明示的な制限値の維持であり、製品設定への反映済みを意味しない。
targetで使わず署名hostだけで使う項目も、理由欄で区別した。

| 設定面 | token数 | 抽出元と数え方 |
|---|---:|---|
| RAUC固有Meson | 18 | `option()`の全宣言。RAUC自体のKconfigは存在しない |
| RAUCが参照・既定指定するMeson共通option | 8 | 全meson.buildの`get_option()`とprojectの`default_options`。toolchain全般の調査は[host・image](host-image.md)を再利用 |
| Buildroot | 7 | target 6と`BR2_PACKAGE_HOST_RAUC`。上流build optionとは別の面 |
| system.conf | 68 | 文書66とparserに残る非推奨alias 2。sectionごとに別token |
| bundle manifest | 24 | 文書の全keyとrolloutの自由key枠。生成keyも除外しない |
| CLI option | 70 | `GOptionEntry`の全long optionと短縮6件。group別に数え、同名でも結合しない |
| command | 17 | 14 commandとstatusのmark-good/mark-bad/mark-active |
| Kconfig | 30 | integration資料の全`CONFIG_*` token。別bootloaderや他SoCの例も不採用理由を記載 |
| kernel cmdline | 5 | integration資料のboot slot識別。`rauc.external`・NFS経由の保護解除も拒否対象 |
| 環境変数 | 48 | 全srcの`g_getenv()` 10件とreferenceのhandler出力38件。同名出力は一つに正規化 |

`system.conf`のslot・artifact・logger名、manifestのimage名・variant・artifact名・
metaのlabel/keyは無限に増やせるため、文書のparameter表記を一つのpatternとして数える。
自由metadataやrolloutがRAUCの安全検査を増やすと解釈しない。
section名自体、設定例の値、Cの内部変数、任意のcompiler flagは独立optionから除外した。
Mesonの全共通CLI、依存libraryの全設定、kernel全体のKconfigをRAUC固有optionへ混ぜない。
必要なkernel optionと`rauc.slot`は契約と後続②で最終configを照合する。

## Buildrootから渡せる範囲

| 面 | 採用計画・制約 |
|---|---|
| 公開Kconfig | `BR2_PACKAGE_RAUC=y`、`NETWORK=y`、`STREAMING=y`、`JSON=y`、`DBUS=n`、`GPT=n`、`BR2_PACKAGE_HOST_RAUC=y` |
| 常に選ぶ依存 | threads/MMU/wcharが前提。GLib、OpenSSL、`OPENSSL_FORCE_LIBOPENSSL`、`LIBOPENSSL_ENGINES`、target squashfsをselect |
| 条件付き依存 | networkはlibcurl、streamingはlibnl、JSONはjson-glib。GPTならutil-linux-libs、serviceならD-Busだが今回は選ばない |
| host recipe | host-json-glib・pkgconf・OpenSSL・GLib・squashfs。network/streaming/service/testsはfalse、jsonはenabled。host-libp11は選択条件付き |
| recipeが公開しないoption | target `create=false`、target/host `pkcs11_engine=false`、mount/配置等の上流optionは専用BR2 symbolがない |
| vendorを編集しない渡し方 | br2-externalのpackage `.mk`で`RAUC_CONF_OPTS += -Dcreate=false -Dpkcs11_engine=false`、`HOST_RAUC_CONF_OPTS += -Dpkcs11_engine=false`を追加する計画 |

[Buildroot Makefile](https://github.com/buildroot/buildroot/blob/bbbdab36565d4941b6b0449a0eedb5aac8a10c2e/Makefile#L543-L557)はpackageの後に
external.mkを読み、本repoの[external.mk](../../../external.mk)は`package/*/*.mk`を読む。
[pkg-meson.mk](https://github.com/buildroot/buildroot/blob/bbbdab36565d4941b6b0449a0eedb5aac8a10c2e/package/pkg-meson.mk#L139-L191)はconfigure実行時に`*_CONF_OPTS`を展開する。
この順序を根拠に上記の追加を計画した。実際の展開値・最終Meson値・build成功は未検証で、
②で`printvars`とconfigure logを照合する。それまではrecipe公開optionと同じ検証済み状態にしない。
`*_OVERRIDE_SRCDIR`はsource差替えであり、未公開optionの指定の代用にしない。

**注意:** `pkcs11_engine=false`をRAUCへ渡しても、固定recipeの
`BR2_PACKAGE_LIBOPENSSL_ENGINES`強制selectは消えない。
OpenSSL 4.0互換性・ENGINE削減は[既存調査](../alternatives/update-build-options.md)の別件として扱う。
本PRでOpenSSLの依存・configure値・監視を変更しない。

## 選択値の理由と意外な境界

- serviceはfalse。`src/main.c`のservice起動処理はboot IDとsystem statusを保存し得る。
  常駐なしを選んだだけでwrite 0とはせず、署名失敗時を含め⑥でblock traceを採る。
- `--progress`はservice有効時専用。serviceなしのinline installの進捗出力を
  ⑤のwrapperで英日表示し、中断を実測する。
- CLI表の`global`は共通、`signing`はbundle/resign/convertに追加される署名group、
  `bundle_access`はnetwork構成のinstall/infoへ追加されるgroup。
  `replace`、`extract_signature`、`write_slot`はそれぞれ対応commandのgroupである。
  `install`のhandler-args/keyring/override-boot-slotと`status`のoverride-boot-slotは非service側。
  非表示のglobal cert/key/keyring/intermediateも互換引数として採取したが、端末の任意鍵指定を許可しない。
- `--no-check-time`はinfo/resignだけであり、install用ではない。
  製品では使わず、[署名時刻と単調版](../../design/rauc-update-contract.md#採用決定-署名時刻と単調版)を採用する。
  `use-bundle-signing-time=true`と、署名済みtag commitの`%ct`・永続下限の比較を組み合わせる。
  `min-bundle-version`のSemVer比較で内部版の保存を代用しない。
- PKIはoffline root CAで手動発行し、GitHub Secretにはrelease鍵と証明書だけを置く。
  1年案・1か月前更新、公開証明書の週次期限検査とIssue通知、失効・鍵交換は④で具体化する。
- `bundle-formats`の既定はplain/verity/cryptだが、製品は`verity`を明記する。
  manifestのformat既定は別にplain。両方を明記しないと採用契約を満たさない。
- `install-same=true`を維持する。statusのhash一致だけで更新を省かず、
  両imageのadaptive block照合と全長read-backを行う。
- `perform-pre-check=false`を維持し、入力の必要blockをverityで検証する。
  これを「全payloadをwrite前に読み終えた」という保証にしない。
- `data-directory`未指定時のper-slot statusはRO rootに不向き。
  共有p7を選ぶが、index/status/bootstateのwriteを[台帳](../../design/write-policy.md#rauc導入で追加する計画)の操作・確定区間へ限定する。
- bootloaderのbarebox/grub/uboot/efi/noop、plain/crypt、casync/desync、
  composefs/artifact、bundle同梱の任意hookと全install置換handlerは採用しない。
  `bootloader-custom-backend`とは別の機能である。

## 費用・保守と未測定

RAUC上流licenseはLGPL-2.1-or-later、recipe表記はLGPL-2.1。
追加するGLib・OpenSSL・curl・libnl・JSON・squashfsのlicenseとSBOMを②で照合する。
版監視は既存のBuildroot更新監視を使い、上流の署名・network・NBD関連修正も追う。
現時点で既知CVEなしという判定は行っていない。
代替品・保守・自前実装との比較は[既存のframework表](../alternatives/updates.md)を参照する。
移行先を無断で変更せず、RAUCでtryboot・PKI・配信PoCが不成立なら利用者へ報告する。

容量、RAM、起動時間、取得量は実測する。indexがimageの約0.8%という上流の説明を実SD write量と混同しない。
製品build・QEMUの数値測定は未実施。別の[host PoC](../../experiments/2026-11-23-rauc-streaming-poc.md)では
`info`によるHTTP取得とretryだけを観測しており、installやadaptiveの合格とは扱わない。
[QEMU測定の行列](../../design/rauc-update-contract.md#qemu測定の試験行列)でfull/adaptive各5回とA/A、
cold/warm/corruptを比較し、生値と失敗を保存して採否を再確認する。

## tokenの機械照合を再実行する

repo rootで次を実行する。製品をbuildせず、sourceと表を読み取る検査である。
tag commitとhashが合わなければ先へ進めない。
APIのlatestは将来変わるので、記録時の応答と更新時の照会を区別する。

```sh
git clone --depth 1 --branch v1.15.2 https://github.com/rauc/rauc.git output/rauc-reference-v1.15.2
RAUC_SRC=output/rauc-reference-v1.15.2 python3 - <<'PY'
import collections
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

root = Path(os.environ["RAUC_SRC"])
base = Path("docs/research/component-options")
record = json.loads((base / "rauc-inventory.json").read_text())
assert subprocess.check_output(
    ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
).strip() == record["source_commit"]
for url, digest in record["sha256"].items():
    name = url.split("/v1.15.2/", 1)[1]
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, name
with (base / "rauc-options.csv").open() as stream:
    rows = list(csv.DictReader(stream))
actual = {(r["surface"], r["scope"], r["option"]) for r in rows}
assert len(actual) == len(rows)
expected = set()
def token(surface, scope, name):
    expected.add((surface, scope, name))
meson = (root / "meson_options.txt").read_text()
for name in re.findall(r"option\(\s*'([^']+)'", meson):
    token("meson", "project", name)
own = {name for surface, scope, name in expected}
for file in root.rglob("meson.build"):
    for name in re.findall(r"get_option\('([^']+)'\)", file.read_text()):
        if name not in own:
            token("meson-builtin", "used-by-rauc", name)
for name in ("c_std", "warning_level"):
    token("meson-builtin", "used-by-rauc", name)
ref = (root / "docs" / "reference.rst").read_text()
scope = None
for n, line in enumerate(ref.splitlines(), 1):
    if n > 1050:
        break
    match = re.match(r"^``\[([^]]+)\]`` Sections?", line)
    if match:
        scope = match[1]
    match = re.match(r"^``([^`]+)`` \(", line)
    if match and scope:
        token("system.conf" if n < 740 else "manifest",
              scope, match[1].split("=")[0])
for name in ("force-install-same", "ignore-checksum"):
    token("system.conf", "slot.<slot-class>.<idx>", name)
token("manifest", "rollout", "<key>")
for surface, file in (("system.conf", "config_file"), ("manifest", "manifest")):
    text = (root / f"src/{file}.c").read_text()
    keys = set(re.findall(r'(?:key_file|keyfile),\s*[^,\n]+,\s*"([^"]+)"', text))
    assert not keys - {name for kind, scope, name in expected if kind == surface}
for file in ("Config.in", "Config.in.host"):
    text = (Path("vendor/buildroot/package/rauc") / file).read_text()
    for name in re.findall(r"^config (BR2_PACKAGE_\w+)", text, re.M):
        token("buildroot", "package", name)
main = (root / "src/main.c").read_text()
for match in re.finditer(
        r"(?:static )?GOptionEntry entries(_\w+)?\[\] = \{(.*?)\n\s*\};",
        main, re.S):
    scope = (match[1] or "_global")[1:]
    for name, short in re.findall(r'\{"([^"]+)",\s*\x27([^\x27]*)\x27', match[2]):
        token("cli", scope, "--" + name)
        if short and not short.startswith("\\"):
            token("cli", scope, "-" + short)
commands = main.split("RaucCommand rcommands[] = {", 1)[1].split("\n\t};", 1)[0]
for name in re.findall(r'\{[A-Z_]+, "([^"]+)"', commands):
    token("command", "rauc", name)
for name in re.findall(r"  (mark-[a-z]+) \[booted", commands):
    token("command", "rauc", "status " + name)
integration = (root / "docs" / "integration.rst").read_text()
for name in re.findall(r"\bCONFIG_[A-Z0-9_]+(?:\*)?", integration):
    token("kconfig", "integration", name)
section = integration.split("Explicit Identification via Kernel Commandline", 1)[1]
section = section.split("\nBarebox\n~~~~", 1)[0]
for value in re.findall(r"``([^`\n]+)``", section):
    if "=" in value or value == "rauc.external":
        token("kernel-cmdline", "boot-identification", value.split("=")[0])
for file in (root / "src").glob("*.c"):
    for name in re.findall(r'g_getenv\("([^"]+)"\)', file.read_text()):
        token("environment", "input", name)
for line in ref.splitlines()[1439:1710]:
    match = re.match(r"^``(RAUC_[^`]+)``", line)
    if match:
        token("environment", "handler-output", match[1])
missing, extra = expected - actual, actual - expected
print("missing=", len(missing), "extra=", len(extra), "rows=", len(rows))
assert not missing and not extra, (missing, extra)
assert expected == {(r["surface"], r["scope"], r["option"])
                    for r in record["identifiers"]}
assert dict(collections.Counter(r["decision"] for r in rows)) == record["decisions"]
counts = dict(collections.Counter(r["surface"] for r in rows))
assert counts == record["surfaces"]
print(json.dumps(counts, ensure_ascii=False, sort_keys=True))
PY
```

parserの全key名との追加照合により、文書から落ちていた旧aliasも表へ含める。
照合はtokenの欠落を検出するもので、採否理由の正しさ、権限分離、
電断耐性、LCDの可読性や実機trybootを証明しない。
