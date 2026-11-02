# Yocto 開発環境の構築手法の調査

Yocto のビルド環境を作る方法を、再現性、rootless での動作、キャッシュの置き場、CI との共用、保守状況の観点で比べました。確認日は 2026-11-02 です。kas は `055518846c`（5.5）、bitbake は `7412853`（2026-10-29）のソースを読んで確かめました。

## 1. 公式文書が示す前提

- ビルドホストは、ネイティブの Linux（推奨）、OCI コンテナ（Docker・Podman）、WSL 2 のいずれでもよいとされています【一次: dev-manual「Preparing the Build Host」】。
- 対応ディストリビューションとホスト要件は [releases-and-layers.md](releases-and-layers.md) §4 にまとめました。Wrynose 6.0.4 は Debian 13 と Ubuntu 26.04 を対応表に含めています【一次】。
- ホストのツールが古いときは、Git・tar・Python・make（extended 版は gcc も）を含む buildtools tarball を使えます。oe-core には `scripts/install-buildtools` があります【一次】。

## 2. 手法の比較

| 手法 | 層の固定 | 実行環境 | rootless | キャッシュ | 保守状況 |
|---|---|---|---|---|---|
| kas（ホストに pip で導入） | YAML の `repos` に `commit`・`branch`。`kas lock` が `<name>.lock.yml` を作る | ホストに Yocto の依存パッケージが必要 | 関係なし（ホストの利用者で動く） | `DL_DIR`・`SSTATE_DIR`・`BB_HASHSERVE` などを環境変数で渡せる | 活発（5.5、2026-08-31） |
| kas-container | 同上 | `ghcr.io/siemens/kas/kas:<版>`（Debian `trixie-slim` を基にする） | Podman 推奨。rootless Docker は「部分的に対応」 | 同上。`KAS_WORK_DIR` 外のディレクトリはコンテナに mount される | 同上 |
| bitbake-setup | 設定 JSON の `sources`（`uri`・`branch`・`rev`）。ソースの上書き JSON で版を差し替えられる | ホスト（Python） | 関係なし | 共有の設定ディレクトリと `top-dir` を持つ | Wrynose で導入、Blacksail で PyPI 配布 |
| CROPS（`crops/poky-container`） | なし（中で手作業） | ディストリごとの `crops/yocto` イメージ | workdir の uid に合わせて利用者を作る方式 | workdir に置く | 最終コミット 2024-09-07 |
| buildtools tarball + ホスト直接 | 別途（サブモジュールなど） | ホスト | 関係なし | 自由 | oe-core に同梱 |
| `docker/msd-dev` を拡張 | 別途（サブモジュールなど） | 現行の Debian `trixie-slim` 固定イメージ | 現行と同じ（`--user` で uid を渡す） | 現行と同じ | 自前で保守 |

確認した事実の詳細は次のとおりです。

- **bitbake-setup の既定設定はコミットを固定しません**。`default-registry/configurations/oe-nodistro-wrynose.conf.json` は `"rev": "wrynose"`、bitbake は `"rev": "2.18"` で、ブランチ名とタグ名を指します【一次】。MSD のようにコミットまで固定するには、自前の設定 JSON か、ソースの上書き JSON が要ります【推測】。レジストリには `poky-wrynose`、`oe-nodistro-wrynose`、`poky-blacksail` などの設定があり、Wrynose の設定には `"expires": "2030-05-31"` があります【一次】。
- **kas lock** は、ブランチやタグを解決した正確なコミットをロックファイルに書きます。更新の手順も備えています【一次: `kas/plugins/lock.py`】。kas 5.5 は、省略形コミットへの警告と、取得後の SHA 照合（GHSA-6p9r-86f2-f954）を加えました【一次】。
- **kas-container と rootless Docker**には、文書とスクリプトに次の制約があります【一次: kas の `kas-container` スクリプトと利用者向け文書の `kas-container-description.inc`】。
  - rootless Docker を検出すると「only limited functionality available」と警告します。
  - kas は作業ディレクトリの所有者を一時的に変えるため、呼び出し元とは別の `KAS_WORK_DIR` を推奨しています。kas が管理するファイルはホストから書き換えないこと、消すときは `kas-container purge` を使うことも求めています。
  - rootless Docker では、リポジトリを読み取り専用で mount する必要があります（`Docker rootless requires read-only repo.`）。`build`・`checkout` は既定で読み取り専用ですが、`shell` と `lock` は書き込み可能で mount するため、rootless Docker のままでは止まります【一次: スクリプトの分岐、推測: `lock` が止まること。実地では未確認】。
  - Ubuntu で `apparmor_restrict_unprivileged_userns=1` のとき、`/etc/apparmor.d/rootlesskit` があれば `--security-opt apparmor=rootlesskit` を自動で付けます。
  - 安全な rootless 運用の第一候補は Podman とされています。
- **CROPS** は `docker run -v <workdir>:/workdir crops/poky --workdir=/workdir` で起動し、workdir の uid と gid でコンテナ内の利用者を作ります【一次: README】。最終コミットが 2024-09-07 で、Wrynose の対応ディストリへの追従は確認できませんでした。

## 3. 資源の制限

AgentCanvas と同居するような共用ホストでは、次の変数で負荷を抑えます【一次: dev-manual「Limiting the Host Resources Usage」、変数一覧】。

| 変数 | 内容 |
|---|---|
| `BB_NUMBER_THREADS` | 並列に走らせる BitBake タスクの上限。既定はコア数 |
| `PARALLEL_MAKE` | 各タスク内の make の並列数。`BB_NUMBER_THREADS` とは独立で、こちらを絞らないと資源の大半を使う |
| `BB_PRESSURE_MAX_CPU`・`_IO`・`_MEMORY` | カーネルの PSI が閾値を超えると新しいタスクを始めない |
| `BB_LOADFACTOR_MAX` | PSI がない環境での代替。PSI 系を設定すると効かない |
| `BB_DISKMON_DIRS` | 空き容量と inode を監視し、閾値でビルドを止める。既定は無効 |

## 4. MSD での選び方

- 再現性: 現行はサブモジュールと SHA で固定しています。kas のロックファイルなら、同じ粒度の固定を YAML 一つで持てます。bitbake-setup は、既定のままでは固定が弱いと考えます【推測】。
- 開発コンテナ: kas-container の公式イメージは Debian `trixie-slim` を基にしており、Wrynose の対応ディストリに入ります。現行の `docker/msd-dev` も同じ `trixie-slim` を基にしています。
- CI: kas はコンテナでも pip 導入でも同じ YAML を読むため、ローカルと CI の手順を揃えやすいと考えます【推測】。
- 以上から、フェーズ1の第一候補は kas（YAML + ロックファイル）とします。実行環境を kas-container にするか、`docker/msd-dev` に kas を入れるかは、VM での構築試験を見て決めます【推測】。

## 5. この VM での構築試験の前提

| 項目 | 値 |
|---|---|
| ホスト | Ubuntu 26.04.1 LTS、12 スレッド、RAM 30 GB、空き 432 GB |
| コンテナ | rootless Docker 29.9.2（sudo なし）。Podman は入っていない |
| AppArmor | `apparmor_restrict_unprivileged_userns=1`、`/etc/apparmor.d/rootlesskit` あり |
| 同居 | AgentCanvas。並列数と PSI の閾値を絞って試す |

構築試験の手順、判定基準、結果は `docs/experiments/` に別途記録します。

## 出典（確認日 2026-11-02）

- https://docs.yoctoproject.org/6.0.4/dev-manual/start.html 【一次】ビルドホストの種類、ネイティブ Linux の準備
- https://docs.yoctoproject.org/6.0.4/dev-manual/limiting-resources.html 【一次】並列数と PSI による制限
- https://docs.yoctoproject.org/6.0.4/ref-manual/variables.html 【一次】`BB_NUMBER_THREADS`、`PARALLEL_MAKE`、`BB_DISKMON_DIRS`
- https://github.com/openembedded/bitbake/blob/74128534302fbf8164ade07b200b90b731caa0ad/doc/bitbake-user-manual/bitbake-user-manual-environment-setup.rst 【一次】bitbake-setup の用語、レジストリ、ソースの上書き
- https://github.com/openembedded/bitbake/tree/74128534302fbf8164ade07b200b90b731caa0ad/default-registry/configurations 【一次】既定の設定 JSON
- https://github.com/siemens/kas/blob/055518846c3963114efbd0107bf3f2e59b4b3ba5/kas-container 【一次】rootless Docker の分岐、mount の既定、AppArmor の扱い
- https://github.com/siemens/kas/blob/055518846c3963114efbd0107bf3f2e59b4b3ba5/docs/userguide/kas-container-description.inc 【一次】rootless の推奨と制約
- https://github.com/siemens/kas/blob/055518846c3963114efbd0107bf3f2e59b4b3ba5/docs/userguide/environment-variables.inc 【一次】`KAS_WORK_DIR`、`DL_DIR`、`SSTATE_DIR`、`BB_HASHSERVE` など
- https://github.com/siemens/kas/blob/055518846c3963114efbd0107bf3f2e59b4b3ba5/kas/plugins/lock.py 【一次】`kas lock`
- https://github.com/siemens/kas/blob/055518846c3963114efbd0107bf3f2e59b4b3ba5/Dockerfile 【一次】公式イメージの基になる Debian の版
- https://github.com/crops/poky-container/tree/cad5d17d3bad6d105adda2be1e398f4fae70e282 【一次】CROPS の使い方と最終コミット
- https://github.com/openembedded/openembedded-core/tree/ae5a301091f5b0574ea7444aab40b309b6d9f3f2/scripts 【一次】`install-buildtools`
