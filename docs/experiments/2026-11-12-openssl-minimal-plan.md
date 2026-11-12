# OpenSSL削減の採取記録と比較実験計画

[実験一覧](README.md) / [調査草案](../research/component-options/openssl-minimal.md)。

## 状態と目的

2026-11-12。**保存済みoutputの静的採取だけを実施した。削減build、openssl.cnfの適用、QEMU起動、速度測定は未実施。** 将来の実験では、更新署名・module署名情報・承認したTLS認証を失わず、不要機能の除去が容量と負担にどう影響するかを比較する。効果の値はまだない。

## 今回の条件と採取値

| 項目 | 条件 |
|---|---|
| 調査checkout | `d7d9d622eae2f5f78dc0b891203f3641f334123b` |
| 対象output | `output-openssl-lts`。以前の[3.5 LTS実験](2026-11-12-openssl-3.5-lts.md)を再利用。新規構築でもreconfigureでもない |
| build当時の入力 | 元実験の基準`8a4f3cb37bf97db86b9e8c65ed5a60da64de6b8c`と未commitの外部override。現在の全製品fileから構築したという意味ではない |
| Buildroot | `8b238854d909c9cce32ef9671d968b03e323b55d` |
| SDK GCC | 実binaryの`--version`は14.3.0、Bootlin builder表示は`2021.11-18033-g83947c7bb6` |
| 採取host | Ubuntu 26.04.1 LTS、Linux 7.0.0-43-generic、GNU readelf 2.46 |
| 回数 | 静的fileのbyte数・hashを1回採取。performanceの反復ではない |
| 計測器の照合 | 4 fileの値を追跡済み旧file一覧と照合し、size/hash全て一致。ELF magicを判定してDT_NEEDEDを採取 |
| 非実施 | build cacheのcold/warm比較、実行時provider、RAM、QEMU／実機の新規実行 |

生の値は[CSV](2026-11-12-openssl-minimal-plan.csv)、入力hash・実Configure引数・CFLAGS・無効理由・直接ELF参照は[JSON](2026-11-12-openssl-minimal-plan.json)。通常fileの論理byte数であり、圧縮rootfsや実SD使用量ではない。

| file | byte |
|---|---:|
| libcrypto.so.3 | 5,200,792 |
| libssl.so.3 | 929,336 |
| openssl | 959,488 |
| openssl.cnf | 12,411 |

## 採取の再実行

元実験の手順で同じ版を構築し、最終targetを使用する。生成物がない場合は欠測とし、hostの`/usr/bin/openssl`へ代替しない。

```sh
docker/msd-dev perl -I/work/output-openssl-lts/build/libopenssl-3.5.9 \
  -Mconfigdata -MJSON::PP -e \
  'print JSON::PP->new->canonical->pretty->encode({disabled=>\%configdata::disabled,argv=>$configdata::config{perlargv},cflags=>$configdata::config{perlenv}{CFLAGS}})'
python3 - <<'PY'
from pathlib import Path
import hashlib
root = Path('output-openssl-lts/target')
for name in ('usr/lib/libcrypto.so.3', 'usr/lib/libssl.so.3',
             'usr/bin/openssl', 'etc/ssl/openssl.cnf'):
    data = (root / name).read_bytes()
    print(name, len(data), hashlib.sha256(data).hexdigest())
PY
readelf -d output-openssl-lts/target/usr/lib/libkmod.so.2.5.1
```

JSONの各ELF consumerは、全通常fileの先頭4 byteがELF magicなら`readelf -d`を実行し、NEEDEDの`libcrypto.so.3`／`libssl.so.3`を選んだもの。間接参照・shell・dlopenは別にsourceで調べた。symlinkは重複排除した。

## option表の照合

3.5.9の148 tokenと、4.1.0との差を表へ照合する手順。全CLIやGCC optionの網羅を意味せず、値指定・aliasは調査本文へ分ける。

```sh
python3 - <<'PY'
import csv, re
from pathlib import Path
s = Path('output-openssl-lts/build/libopenssl-3.5.9/Configure').read_text()
block = s.split('my @disablables = (', 1)[1].split(');', 1)[0]
expected = set(re.findall(r'"([\w+.-]+)"', block))
for kind in ('tls', 'dtls'):
    for token in re.search(r'my @' + kind + r'\s*=\s*qw\(([^)]+)\)', s)[1].split():
        expected.add(token)
        if token != 'tls1_3':
            expected.add(token + '-method')
with open('docs/research/component-options/openssl-minimal-options.csv') as stream:
    rows = list(csv.DictReader(stream))
actual = {r['option'] for r in rows if r['available_3_5_9'] == 'yes'}
assert actual == expected, (expected - actual, actual - expected)
assert len({r['option'] for r in rows}) == len(rows)
print(f'Configure 3.5.9 tokens={len(expected)} missing=0 extra=0')
PY
```

## 比較実験の計画（未実施）

### 固定する条件

着手時に利用者が承認したcommitを固定し、mainの清潔なtreeからA/A基準と各variantを別のO=へfull buildする。3.5.9、同一tarball/hash/patch、SDK、kernel、libc、strip、filesystem圧縮、公開鍵、SOURCE_DATE_EPOCHを揃える。3.5.10更新と最小化を同じ比較に混ぜない。ccacheは全て同じwarm状態にするか全て無効にし、download cacheとbuild時間を区別する。host用OpenSSLは変更しない。

出力先は`output-openssl-minimal-<variant>-<run>`。既存outputは上書き・掃除しない。実行したcompiler、QEMU、kernel、image、CLI、librariesの版とSHA-256を採る。製品外の試験用鍵を使い、本番秘密鍵は要求しない。

### 水準と仮説

| 水準 | 変えるもの | 期待と危険 |
|---|---|---|
| A/A | 同じ既定設定で独立full build | 非決定的fileを特定し、削減差に混ぜない。2構築は再現性点検用で、速度の統計比較にはしない |
| B1 | ssl3/weak cipherの明示無効、旧TLS、DTLS/QUIC/SRP/圧縮の削減 | 不要経路が減る可能性。既に無効のflagはbyte差0でも正常 |
| B2 | 利用者が承認したlegacy／algorithm削減 | 容量減の仮説。古いEAP認証や証明書が壊れ得る |
| B3 | no-deprecated／API level、no-module/no-dsoをそれぞれ別構成 | ABI／consumer build、providerのbuilt-in化を検査。一度に全flagを変えない |
| C | 承認されたopenssl.cnfだけ | TLS許可・拒否を検査。build削減の効果と分離する |
| D | `-Os`対`-O2` | 実機で容量／速度を比較。`-O3`・LTOはDの結果を見て別承認 |

### 採否基準（提案、実験前に承認する）

- 全variantでfull build終了0、未解決symbol 0。`perlargv`／configdataと生成headerが意図した条件に一致し、追加／欠落ELF依存を全件説明する。
- 正常署名・bundleは全件受理、改変manifest／payload・別鍵・切詰め・破損署名・未知鍵形式は全件拒否。拒否時の永続書込みは0。`tests/msd-update/run.sh`に加え、target binaryで同じ正常／負の対照を行う。host試験だけで代用しない。
- kmodの署名付き／未署名／破損moduleのmodinfo結果を基準と照合する。module loadの可否と署名強制はkernel側の試験として分離する。
- QEMU A/B両slotで5回ずつ起動し、全てlogin／readyへ到達。kernel・rootfs・CLI版を照合し、署名と拒否を実行する。QEMUの新config構文誤りもfail closedになることを試す。
- TLS実験は利用者が選んだEAP methodとpeerのmatrixを先に固定する。TLS 1.2/1.3、RSA/ECDSA chain、再接続／resumptionは全件成功。TLS 1.0/1.1、期限切れ・不正CA・hostname不一致・弱い鍵・禁止cipherは全件拒否。検証時刻を固定し、証明書期限の偶然に依存しない。
- no-legacy構成では明示legacy loadも失敗し、default／Ed25519は動くこと。configだけの構成では「自動loadなし」と「明示load不能」を混同しない。採用したEAPで必要な拒否・成功の両方を実行する。
- 現行専用の削減profileは、上記機能基準を満たした上で3 ELF合計とrootfs.squashfsの両方が基準より小さいことを容量面の採用基準とする。削減byteは事前に予測しない。安全上不要な機能を明示無効にする変更は、差0でも性能改善とは称さず別理由で判断する。
- -O2等の速度案は、実機の更新署名検証中央値を10%以上短縮し、3 ELF合計の増分を5%以下にすることを**提案閾値**とする。値は利用者承認前で、既存の製品要求ではない。冷起動中央値・peak RSSが基準より5%を超えて増える場合は採否を再検討する。

### 計測器・反復・実機

byte数とSHA-256を既存toolとのA/Aで照合し、破損署名／禁止protocolの負の対照が必ず失敗することを先に確かめる。実機の待ち時間・CPU／RSSは各条件5回以上で、生の全値、中央値、最小・最大を保存する。初回cold起動とwarm実行を分ける。timeout・欠測・失敗を成功の中央値に混ぜず、run IDを残す。

CM0のSoC/revision、64-bit HWCAP、周波数／governor、温度、電源とthrottlingを採取する。署名検証とTLS throughputを優先し、補助の`openssl speed`を使うなら実機・同一条件でのみ比較する。**QEMUのopenssl speedはA53の実性能の根拠にしない。** QEMU起動はfirmware tryboot、実SD電源断、LCD、keyboard、Wi-Fi実無線の検証でもない。

試験payload・鍵・ログはRAMへ置く。重い試験は進捗と中断可否を表示し、idle時の永続書込みを追加しない。実験でのSD書込み条件は実行前に製品I/O規則と照合する。今回はrunnerやprogress UIを実装していない。

## 失敗した採取と限界

hostでconfigdataをimportした最初の2試行は、記録された`/work`のmodule探索pathがhostにないため失敗した。sourceを変更せず、元のDocker mount環境で読み直すと成功した。OpenSSLやPerlの依存不足とは判定しない。

Raspberry Pi文書の直接fetchは403、推測したGitHub文書path／branchは404だった。Arm TRMの今回の直接再取得も成功確認できていない。これらを一次確認済みと扱わず、取得できたRaspberry Pi EngineerのBCM2837B0回答と既存の出典付き調査を分けた。CM0個体のHWCAPは未取得。

4.1.0 Configureはdisablable配列を3分割しており、3.5用parserをそのまま使う初回照合は失敗した。配列名を区別して再抽出し、3.5.9の148／4.1.0の154 tokenを数えた。token差は意味・既定policyの完全比較ではない。

実build用の削減flag注入、cnf適用、容量のA/B差、RAM・起動・署名速度、Wi-Fi／TLS、QEMU、実機は全て今後の試験である。新規build logは存在しない。採取値はhash付きJSON/CSVに保存し、過去のログを今回の実行ログとして流用しない。
