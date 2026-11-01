# SSH サーバー・クライアントの実装比較調査

[SSH・VPN・鍵保管の調査](ssh-vpn-and-keys.md) の姉妹文書です。あちらは暗号方式の既定値・ポスト量子鍵交換・鍵の保管設計を扱い、こちらは**実装の選択肢そのもの**（サーバー、クライアント、ライブラリ、SSH を補完・代替する仕組み）を整理します。MSD/Linux は「SSH・VPN は調査対象にとどめ、実装しない」方針であり、この文書は将来の検討材料です。確認日は 2026-11-02 です。

## 1. サーバー実装

| 実装 | 形態 | ライセンス | Buildroot 収録 | 特徴 |
|---|---|---|---|---|
| OpenSSH | sshd + 付属一式 | BSD-3-Clause / BSD-2-Clause / PD 混在 | あり（10.6） | 事実上の基準実装。証明書・FIDO2/U2F 鍵・エージェント転送・SFTP など機能が最も揃います。依存として OpenSSL 系 libcrypto が要り、フットプリントは大きめです。 |
| Dropbear | サーバー + dbclient + dropbearkey | MIT / BSD-2-Clause / PD | あり（2026.94） | 組込み向きの小型実装。`localoptions.h` で機能を削れ、`PROGRAMS` でサーバーのみにもできます。xinetd/inetd モード（`-i`）で接続毎起動も可能で、常駐プロセスを持たない運用ができます。SCP は別実装に依存します。 |
| TinySSH | サーバーのみ | CC0-1.0 | あり（20240101） | NaCl 系プリミティブ中心の極小実装（リポジトリ記述で 10 万語未満のコード）。監査のしやすさを重視します。機能は意図的に最小（ポート転送などの扱いに制約があります）【要対象版の機能一覧確認】。 |
| wolfSSH | ライブラリ（C） | GPLv3 または商用デュアル | なし | 組込み・RTOS 向けに wolfSSL 上で構築。SCP/SFTP 対応をうたいます。商用ライセンスも提供されます。 |
| libssh | ライブラリ（C） | LGPL-2.1 | あり（0.12） | クライアント用途が中心ですがサーバー側の構築にも使えます。製品への組み込みに向きます。 |
| golang.org/x/crypto/ssh | ライブラリ（Go） | BSD-3-Clause | なし | Go の標準的な SSH ライブラリで、サーバー・クライアント双方を構築できます。Teleport・Gitea など多くの Go 製ツールの土台です。 |
| russh | ライブラリ（Rust） | Apache-2.0 | なし | thrussh 系からのフォークで、Rust の非同期 SSH ライブラリ。Warp 端末のコードから分離されて保守されています。 |
| Apache MINA SSHD | ライブラリ（Java） | Apache-2.0 | なし | Java 製のサーバー・クライアントフレームワーク。組み込み SSH サービスを自前で作る場合の選択肢です。 |
| AsyncSSH | ライブラリ（Python） | EPL-2.0 または GPL-2.0+ | あり（2.22.0） | asyncio ベースの完全実装。テスト用の簡易サーバーも作れます。 |
| Paramiko | ライブラリ（Python） | LGPL-2.1+ | あり（4.0.0） | Python で最も広く使われる SSH ライブラリ。クライアントが中心で、サーバーモードはテスト・ゲートウェイ用途です。 |
| Erlang/OTP ssh | OTP アプリケーション | Apache-2.0 | なし | Erlang VM に内蔵の SSH 実装（サーバー・クライアント）。 |
| Teleport | アクセス基盤（Go） | AGPL-3.0 | なし | sshd の代替というより SSH CA・証明書・セッション記録・RBAC まで含む統合アクセス基盤。単体デーモンとしては重いですが、複数ノード管理では別モデルになります。 |
| Bitvise SSH Server / Tectia / VanDyke VShell | 商用デーモン | 商用 | なし | Windows/商用サポートの選択肢。組込み Linux では実質対象外です。 |

## 2. クライアント実装・フロントエンド

| 実装 | 形態 | ライセンス | Buildroot 収録 | 特徴 |
|---|---|---|---|---|
| OpenSSH `ssh` | CLI | （同上） | openssh に同梱 | scp・sftp・ssh-agent・ssh-keygen・ssh-copy-id を含む標準セット。`ProxyCommand`・`-J`・ポート転送・証明書・FIDO 鍵まで揃います。 |
| Dropbear `dbclient` | CLI | （同上） | dropbear に同梱 | サーバーと同じコード基盤の小さなクライアント。鍵形式は dropbear 形式で、OpenSSH 形式との相互変換は `dropbearconvert` 系です。 |
| PuTTY 一式 | GUI/CLI | MIT | あり（0.85） | putty・plink・pscp・psftp・pageant・puttygen の一式。Buildroot ではターゲット向けにもパッケージ化されています。派生に KiTTY（機能拡張）、PuTTY CAC（スマートカード対応）。 |
| ターミナル統合クライアント | GUI | 各種 | なし | MobaXterm（Windows）、SecureCRT（商用）、Termius（商用フリーミアム）、Tabby（MIT）、electerm、WindTerm、SuperPuTTY、mRemoteNG、Remmina（RDP/VNC 統合）、ブラウザ拡張の Secure Shell など。ホスト側の作業環境としての選択肢です。 |
| libssh2 | ライブラリ（C） | BSD | あり（1.11.1） | クライアント専用の軽量ライブラリ。curl の SCP/SFTP バックエンドとして使われます。 |
| JSch → mwiede/jsch | ライブラリ（Java） | BSD 系 | なし | 古典的な Java クライアントの保守フォーク。JSch 本家は停止し、こちらが現行です。 |
| sshj | ライブラリ（Java） | Apache-2.0 | なし | Bouncy Castle ベースのもう一つの Java クライアントライブラリ。 |
| Net::SSH::Perl / php-ssh2 / perl-net-ssh2 | 言語バインド | Artistic/GPL-1.0+ / PHP-3.01 | あり | Perl・PHP からの SSH クライアント利用。 |
| Twisted Conch | ライブラリ（Python） | MIT | なし | Twisted フレームワークの SSH 実装。 |

## 3. SSH を補完・代替する仕組み

「SSH の再接続性」「SSH 経由のファイルアクセス」「SSH の代替トランスポート」は本体とは別のツールが担います。

| ツール | 形態 | ライセンス | Buildroot 収録 | 役割 |
|---|---|---|---|---|
| Mosh | 別プロトコル（UDP） | GPL-3.0+（例外付き） | あり（1.4.0） | SSH でログイン・起動だけを行い、その後は独自の UDP トランスポートでローミング・断線耐性を提供するモバイルシェル。サーバー側に mosh-server が要ります。SSH-2 の完全互換ではなく補完です。 |
| Eternal Terminal | 別プロトコル（TCP） | Apache-2.0 | なし | 切断後にセッション状態を復帰するリモートシェル。tmux との併用前提で、Mosh とは異なり TCP 上で動きます。 |
| tmux / screen | ローカル多重化 | ISC / GPL-3.0+ | あり | SSH セッション内でセッションを持続させる従来の方法。Mosh/ET との組み合わせでも使います。 |
| tmate | ターミナル共有 | BSD 系（NOASSERTION） | なし | tmux フォークに SSH リレーを組み合わせた画面共有。ペア作業用です。 |
| autossh | ラッパー | BSD | あり（1.4g） | ssh プロセスを監視し切断時に再接続します。トンネル維持用です。 |
| sshuttle | VPN（SSH 経由） | LGPL-2.1+ | なし | ssh 接続だけを使った転送型 VPN。サーバー側の設定不要が特徴です。 |
| corkscrew | ProxyCommand | GPL-2.0 | あり（2.0） | HTTP CONNECT プロキシ越しに ssh を通す道具。同用途に connect-proxy があります。 |
| sshfs | FUSE | GPL-2.0 | あり（3.7.6） | SFTP 経由でリモートをマウント。サーバー側の追加設定が要りません。 |
| sshpass | 補助 | GPL-2.0+ | あり（1.10） | パスワード認証を非対話化します。秘密情報が露出しやすいため検証用途に留めます。 |
| rssh / scponly | 制限シェル | 各種 | なし | sftp/scp 専用などにログインを制限する古いアプローチ。OpenSSH の `internal-sftp` + `ChrootDirectory` で代替できることが多いです。 |
| gitolite | Git 管理層 | GPL-2.0 | なし | 1 つの OS アカウントに ssh 公開鍵で複数ユーザーの Git アクセスを与える層。Gitea 等の内蔵 SSHD も同じ発想です。 |
| sshguard / fail2ban | ブルートフォース対策 | ISC/BSD 混在 / GPL-2.0+ | sshguard あり | ログ監視で攻撃元をブロック。公開サーバー運用時の補完です。 |
| smallstep `step-ca` | CA | Apache-2.0 | なし | SSH 証明書の CA・更新基盤。sshd の代替ではなく鍵運用の代替です。 |

## 4. プロトコルとセキュリティ上の要点

- SSH-1 は廃止され、現行実装は SSH-2 のみを話します。OpenSSH 10.x・Dropbear 2026.94 の既定暗号・鍵交換（ML-KEM/sntrup ハイブリッド、ChaCha20-Poly1305 優先）は[ssh-vpn-and-keys.md](ssh-vpn-and-keys.md)の節 21.5 に整理済みです。
- OpenSSH の DSA 署名は 10.0 で削除され、SSH-1 系の機能は消えています。古いクライアントとの互換を気にする場合は `ssh-rsa`（SHA-1 署名）の扱いが残る注意点です。
- Terrapin 攻撃（CVE-2023-48795）：ハンドシェイクのパケット改変で暗号強度を下げられる問題が 2023 年末に公表され、strict KEX 拡張で対策されました。主要実装は対応版に更新されています。
- regreSSHion（CVE-2024-6387）：OpenSSH のシグナルハンドラ競合で root 権限の RCE の可能性が報告された件。特定の glibc 環境の sshd が対象で、速やかな版更新が推奨された事例です。
- xz/liblzma バックドア（CVE-2024-3094）：sshd が間接的に liblzma を読む構成を狙った供給連鎖型の事例。SSH 本体の欠陥ではありませんが、sshd の依存ツリー全体が攻撃面になることを示しました。

## 5. Buildroot 収録状況まとめ

vendor/buildroot（2026.08 系）での確認結果です。

- 収録あり：openssh 10.6、dropbear 2026.94、tinyssh 20240101、libssh 0.12、libssh2 1.11.1、putty 0.85、mosh 1.4.0、autossh 1.4g、corkscrew 2.0、sshfs 3.7.6、sshpass 1.10、sshguard 2.5.1、python-paramiko 4.0.0、python-asyncssh 2.22.0、perl-net-ssh2 0.74、php-ssh2 1.4。
- 収録なし：wolfSSH、russh、Apache MINA SSHD、golang.org/x/crypto/ssh、JSch、sshj、Eternal Terminal、tmate、sshuttle、teleport、step-ca、gitolite、fail2ban。
- MSD の `msd_cardputerzero_defconfig` ではいずれも現在有効化されていません（方針上 SSH は未実装）。

## 6. MSD/Linux への適用メモ

- 現行方針どおり「調査のみ」が前提です。保守用に将来 SSH を入れる場合の順序感だけメモします。
- **サーバーの第一候補は Dropbear** です。Buildroot 収録、単一バイナリでサーバーとクライアントを兼ねられ、ChaCha20-Poly1305 と sntrup/ML-KEM ハイブリッドが既定で有効です。inetd/socket 起動で常駐を避けられます。SFTP が要る場合は OpenSSH の sftp-server か別手段が要ります。
- **監査最小性を取るなら TinySSH** も Buildroot にありますが、機能が意図的に絞られており、ポート転送などの扱いは対象版のドキュメント確認が要ります。
- **証明書・FIDO2/U2F 鍵・詳細な設定が要るなら OpenSSH** です。サイズと依存は最大ですが機能は全部揃います。
- **実装しない選択の代替**もあります：シリアルコンソール・UART での保守、ADB 風の独自デーモン、あるいは SSH そのものを載せず msd-update 側の署名付き OTA で回す運用です。
- クライアント側（開発者 PC）の選択はホスト環境の話なので本機には影響しません。PuTTY 系・OpenSSH 系どちらでも接続できます。

## 7. 未確認事項

- Dropbear / TinySSH の静的ビルドの実サイズ（公式の確定値ではなく推測で数 KB〜数百 KB の幅）。実機で `size`・`ldd` を測る必要があります。
- TinySSH の機能範囲（SFTP サブシステムの有無、ポート転送の扱い）— 対象版の man/README を要確認。
- russh の現行の上流リポジトリ位置とライセンス表記（fork が複数あり、追跡が要確認）。
- Teleport の組込み向き度合い（AGPL-3.0・常駐エージェント・CA 管理が前提なので MSD の規模では非現実的と推測）。
- BSD 系ライセンス表記の細かい内訳（OpenSSH の複数表記、PuTTY の MIT）はパッケージの LICENSE フィールドの値です。配布形態ごとの適用範囲は個別確認が要ります。

## 8. 主な出典（2026-11-02 確認）

- OpenSSH: https://www.openssh.com/ 、 https://github.com/openssh/openssh-portable
- Dropbear: https://matt.ucc.asn.au/dropbear/dropbear.html 、 https://github.com/mkj/dropbear
- TinySSH: https://github.com/janmojzis/tinyssh 、 https://tinyssh.org/
- wolfSSH: https://github.com/wolfSSL/wolfssh
- libssh: https://www.libssh.org/ 、 libssh2: https://libssh2.org/
- russh（Warp 系 fork）: https://github.com/warpdotdev/russh （参照先の確認は要フォロー）
- Apache MINA SSHD: https://github.com/apache/mina-sshd
- AsyncSSH: https://asyncssh.readthedocs.io/ 、 Paramiko: https://www.paramiko.org/
- golang.org/x/crypto/ssh: https://pkg.go.dev/golang.org/x/crypto/ssh
- Teleport: https://github.com/gravitational/teleport
- Eternal Terminal: https://github.com/MisterTea/EternalTerminal 、 https://eternalterminal.dev/
- Mosh: https://mosh.org/
- tmate: https://tmate.io/
- sshuttle: https://github.com/sshuttle/sshuttle
- sshfs: https://github.com/libfuse/sshfs
- smallstep step-ca: https://smallstep.com/docs/step-ca/
- PuTTY: https://www.chiark.greenend.org.uk/~sgtatham/putty/
- Bitvise: https://www.bitvise.com/ 、 Tectia: https://www.ssh.com/products/tectia-ssh/
- Terrapin: https://terrapin-attack.com/
- regreSSHion: https://blog.qualys.com/vulnerabilities-threat-research/2024/07/01/regresshion-remote-unauthenticated-code-execution-vulnerability-in-openssh-server
- xz backdoor: https://nvd.nist.gov/vuln/detail/CVE-2024-3094
- Buildroot パッケージ定義: vendor/buildroot/package/ 以下の各 `*.mk`（当該リポジトリ内の一次資料）
