# IDS・監査・AV等を見送った調査の履歴

[強化項目の案内へ戻る](README.md) / [現在の段階導入と検証](../verification.md)

以下は元の11節です。各候補の役割、RAM等の条件、license・提供形態、当時の見送り理由を保存します。「導入しない」はこの調査の前提であって永久の除外ではありません。MSD/Linuxの512 MiB機での性能や全候補の現行版の監査を完了した記録ではなく、再評価ではhost側のscanと端末runtimeの検知を区別します。

## 11. 導入しないが調査だけ残す項目

### Falco（eBPF ランタイム検知）

- Buildroot には `BR2_PACKAGE_FALCOSECURITY_LIBS`（Falco 本体ではなく検知ライブラリ群）が存在する。依存は grpc、abseil-cpp、protobuf、lua 5.1、tbb（要 glibc、本ツールチェーンは glibc なのでビルド要件は満たせる）と重い。eBPF syscall 監視は kernel BTF・libbpf・膨大なユーザーランドが要り、本機は 512 MiB / BusyBox で常駐させる実用的選択ではない。**調査のみ・非採用**。
- kernel 側は `CONFIG_BPF_SYSCALL=y`、`CONFIG_CGROUP_BPF=y` があるが `CONFIG_DEBUG_INFO_BTF` が確認できておらず、BTF 不在なら CO-RE 系の Falco driver は動かない。
- 同等の目的で将来使える軽量手段: `kernel.dmesg_restrict` 等の観測制限、audit（`CONFIG_AUDIT`）の限定的導入。

### Suricata（IDS/IPS）

- Buildroot に `BR2_PACKAGE_SURICATA` は存在する（要 rust host、jansson、libhtp、libpcap、libyaml、pcre2）。ただしネットワーク未導入・常駐重い・ルール更新運用が要る。組み込み最小構成では過剰。**調査のみ・非採用**。必要になった場合は nftables の ct/ログ + ホスト側分析のほうが適合する。

### debsums（ファイル整合性）

- deb 系がないため対象外。同等目的は dm-verity（tier B、QEMU 検証済み）で rootfs 側を担保し、`/data` 側は `msd-update` の署名・read-back 設計を流用する方向が合う。**対象外**。

### Lynis（監査スクリプト）

- POSIX sh ベースで BusyBox でも動く可能性が高い。Buildroot に `BR2_PACKAGE_LYNIS` があり、監査用途で**導入ではなく CI/一時実行として評価可能**。セキュリティ監査の定期実行を設計に組み込むかは別途判断。
- このリポジトリには既に vendor の Lynis 調査や hardening 実験（S6 tier B）があるため、Lynis の指摘は記録として残し、実装上の採否は別途決める整理が合う。

### Zenarmor（次世代ファイアウォール/アプリケーション制御）

- Sunny Valley Networks の商用 NGFW。主な展開先は OPNsense/pfSense CE のプラグイン、または Linux（Ubuntu/Debian/RHEL 系）ゲートウェイ。**Buildroot パッケージなし、プロプライエタリなバイナリ**。
- ハードウェア要件（公式）: 最小でも x86_64 デュアルコア + **1 GB RAM**（インストーラが 1 GB 未満を拒否）、レポート用 Elasticsearch がメモリを大量に消費し、推奨は 8 GB。本機は ARM64（BCM2837）+ 512 MiB のため**アーキテクチャ・RAM 両面で対象外**。【一次: [Zenarmor hardware requirements](https://www.zenarmor.com/docs/introduction/hardware-requirements)】
- 管理面はクラウド（SaaS コンソール）前提で、本機のエアギャップ/最小構成と相性が悪い。
- **効能（もし使えたら何を得るか）**: L3/L4 では識別できない「アプリケーション層」の可視性とポリシー（L7 DPI によるアプリ識別・ブロック）、カテゴリベースの Web フィルタリング、TLS SNI ベースのフィルタ（完全 MITM なしで接続先ドメイン単位の制御）、脅威インテリジェンス、詳細なレポート/可視化。
- **本機で検討する代替策**: 悪性domainをfilterするresolverは候補で、Quad9等を使う接続・DNS設定は製品で稼働確認していません。domain filterとL7 DPIは別の保証です。SNI制御やlog集約も、必要性・暗号化通信での限界・RAMと運用費用を調べてから判断します。**非採用・調査のみ**。

### ClamAV（シグネチャ型マルウェア検知）

- Buildroot に `BR2_PACKAGE_CLAMAV` あり（要 libstdcpp、rust host、json-c、libcurl、libmspack、libxml2、openssl）。
- 実用面: `clamd`/`clamscan` はシグネチャ DB（main+daily cvd）をメモリに展開して動く設計で、常時 1 GB 級の RAM を要する傾向がある。**512 MiB ではデーモンも単発スキャンも現実的でない**。【推測、実測要】
- **効能**: 既知マルウェアのシグネチャ検知、on-access スキャン（fanotify 経由）、フィッシング/PUA 検出、freshclam による日次シグネチャ更新。
- **本機での整理**: 署名更新とRO rootfsはありますが、dm-verityは製品未導入です。noexecを加えてもinterpreterやetc overlayを経由する処理は止められず、dataが必ず実行されない保証にはなりません。[既存QEMU試験](../../../experiments/2026-10-21-qemu-data-noexec.md)を参照してください。配布・持込み前のhost側scanは端末の負担を抑える候補ですが、device実行時の検知と同じ効果とはしません。対象・検知漏れ・更新経路・費用を分けて判断します。**非採用・調査のみ**。

### Proofpoint ET Pro / ET Open（IDS ルールセット）

- Emerging Threats（ET）は Proofpoint の IDS ルールセットで、Snort/Suricata 系エンジンに流し込む**ルール供給源**であって製品そのものではない。ET Open（無償コミュニティ版、更新に遅延・件数制限あり）と ET Pro（有償サブスクリプション、フルセット・日次更新）に分かれる。【推測、価格・条項は要検証】
- **効能**: マルウェア C2 通信、エクスプロイト試行、スキャン・ブルートフォース、ポリシー違反系の既知パターンを IDS が検知できるようになる。Quad9 が DNS 層で遮断する悪性ドメインとは別経路（パケット内容・挙動）の防御層になる。
- **本機への適用可否**: 前提の Suricata/Snort エンジン自体が非採用（11 節・RAM と運用負荷）のため、ルール単体の導入意義はない。**非採用・調査のみ**。将来 Suricata を別のホスト/ゲートウェイ側に置く構成になった場合、ルール源として ET Open → ET Pro の順で評価するのが順当。
- ルール更新の運用（`suricata-update`/`pulledpork` による日次取得）も記録しておく。
