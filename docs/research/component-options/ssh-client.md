# SSH clientの比較条件と採否

[component option索引](README.md)へ戻ります。2026-11-23の[実験記録](../../experiments/2026-11-23-ssh-client-compare.md)、[機械抽出表](ssh-client-options.csv)、[source hash](ssh-client-inventory.json)を組にして読みます。実装全般の比較は[既存調査](../security/ssh-implementations.md)を再利用し、ここでは端末側のclientだけを扱います。**製品のdefconfig・鍵保存先・暗号設定は変更していません。**

## 候補の採否

| 候補 | 今回の判断 | 理由・条件 |
|---|---|---|
| OpenSSH 10.6p2 `ssh` | 第一候補を維持。後続の製品導入候補 | 利用者の希望、OpenSSH鍵とknown_hostsの互換性、設定・algorithm queryの明示性を重視します。追加797,448 bytes、圧縮差327,680 bytesで事前の容量基準内です。Ed25519認証と別host key拒否は各5/5。暗号と永続化の製品設定を決めたという意味ではありません |
| Dropbear 2026.94 `dbclient` | 今回は見送り。小容量が優先になった時に再検討 | 追加476,400 bytes、圧縮差204,800 bytesと最小。正常・負対照は各5/5ですが、秘密鍵変換、単純なhostname照合、known_hostsの書込みopenを考慮します。既定の小型構成にはOpenSSLへの依存がありません |
| PuTTY 0.85 `plink` | 今回は見送り | 追加899,376 bytes、圧縮差311,296 bytes。正常・負対照は各5/5。PPK変換と独自の保存形式が必要で、拒否時にもrandomseedが更新されました。OpenSSHに対する今回の利点が小さいためです |
| 既存調査のlibssh・libssh2・Go/Rust/Java/Python/Perl/PHP系 | このCLI比較ではbuildしない | libraryから対話clientを新設する作業は別です。完成したclientをvendor recipeから比較する今回の条件と一致しません |
| TinySSH、GUI端末、Mosh等の補完、独自実装 | 不採用 | 順にserver専用、端末側GUIや追加依存、別protocolまたは補助機能であり、同じclientの置換ではありません。独自SSH実装にはprotocol・暗号の保守負担があります。候補名・licenseは既存調査に残します |

OpenSSHはBSD系・MIT・Public domain等の混在、DropbearはMIT・BSD-2-Clause・Public domain等（small時はbundled libtomのlicenseも追加）、PuTTYはMITです。根拠は各recipeとsourceのlicense文書です。今回、CVE件数の網羅監査・RAM・速度・電力は測っていません。OpenSSH 10.6p2のrelease notesにはserver側のPAM無効時の認証問題への対処とclient等の修正があります。「sshdを入れない」ことを、clientと依存libraryの脆弱性がない証拠にはしません。

## 固定版と一次資料

Buildrootは`8b238854d909c9cce32ef9671d968b03e323b55d`です。2026-11-23に[OpenSSH release notes](https://www.openssh.com/releasenotes.html)、[Dropbear配布一覧](https://matt.ucc.asn.au/dropbear/releases/)、[PuTTY最新版](https://www.chiark.greenend.org.uk/~sgtatham/putty/latest.html)を取得しました。観測した最新版は順に10.6p2、2026.94、0.85で、固定版と同じです。この比較に版を上げる変更や、それに伴うoption差はありません。取得本文・hashは実験の証拠に収録します。

recipeは`vendor/buildroot/package/openssh/openssh.mk`、`vendor/buildroot/package/dropbear/dropbear.mk`、`vendor/buildroot/package/putty/putty.mk`と各`Config.in`です。固定commitのsubmodule内fileで、各hashは抽出JSONに収録しています。上流sourceの取得とhash検査は各Buildroot recipeに従いました。

| 抽出する面 | 一次資料・範囲 | 既定値と今回の扱い |
|---|---|---|
| Buildroot | 3 packageの`Config.in`全14 symbol | 条件付きdefaultは原文と区別。server・key utilityの非導入はpayloadで確認します |
| recipe | package prefixの変数58件 | `*_CONF_OPTS`だけでなくinstall・hook・dependencyも列挙します。Makeの代入宣言と実展開を混同しません |
| configure | OpenSSH・Dropbearの`configure --help`全token | 共通Autoconf optionも含みます。helpに既定の記載がないものは未記載とします |
| CMake | PuTTYのsource `cmake/`と`CMakeLists.txt`のCACHE・option宣言 | Windows用も区別。Unixの`PUTTY_GSSAPI`は上流DYNAMIC、実buildではrecipeのOFFです |
| compile macro | Dropbear `src/default_options.h`の全宣言 | CSVは宣言値で、全条件の解決後の値ではありません。`localoptions.h`、Make引数、`-Q`を別に確認します |
| CLI・client設定 | OpenSSH `ssh.c`・`readconf.c`、Dropbear `cli-runopts.c`、PuTTY `cmdline.c`・`unix/plink.c`・`doc/plink.1` | OpenSSHの実効値は測定binaryの`-G`から採取。alias・非対応・条件付きで非出力の項目も残します |
| session・環境 | PuTTY `conf.h`全CONF_OPTION、3 sourceのliteral `getenv` | CONFのdefault式・custom load・空mappingを区別。環境変数の候補にはserver・GUI・他OSのみの参照も含み、clientでの到達性を一律に断定しません |

依存libraryの全option、Autoconf内部のcache変数、`sysoptions.h`の導出macro、CMakeの検査用INTERNAL cacheは、この部品の利用者向け設定とは分けて対象外にします。新しいkernel parameterやsysctlは追加せず、networkは既存kernelのUSB NICを実験用に使いました。

CSVの「採用」は**比較時の明示指定**、「不採用」は上書きを指定せずrecipe・上流既定を維持する意味です。機能をbuildから消したという意味ではなく、製品採用の判断は冒頭の表に分けます。既定値の全条件の解決、全環境変数の到達性、全algorithmとの交渉は未確認です。抽出tokenのmissing=0は、これらの確認済みを意味しません。

## vendorを変えずに渡す条件

専用`O=`へのmake引数で`OPENSSH_MAKE_OPTS=ssh`、`DROPBEAR_PROGRAMS=dbclient`と各packageのinstall command・post-install hook・init hookを上書きしました。OpenSSHのserverとkey utilityはKconfigでも無効にし、`sshd`等の実行fileをpayloadへ入れません。PuTTYのrecipeはCLI群をbuildし、そのうち`plink`だけをpayloadへ入れます。PuTTY初回のinstall path誤りとwarm再試行は実験記録に残しました。

`*_CONF_OPTS`をMake引数で上書きすると、recipeの引数を丸ごと置換し得ます。今回はその上書きをせず、将来の機能削減を渡せるというbuild済みの保証にはしません。Dropbearの`BR2_PACKAGE_DROPBEAR_LOCALOPTIONS_FILE`はrecipeが公開する別の入口ですが、今回は独自fileを指定していません。

## 暗号の能力・既定・実交渉

全query値とELF内ID候補は[集計JSON](../../experiments/2026-11-23-ssh-client-compare.json)にあります。OpenSSHは`-Q kex/cipher/mac/key/key-sig`、Dropbearは`-Q kex/cipher/mac/sig`の出力です。PuTTYは同等のqueryを使わず、ELF内IDと`ssh/transport2.c`、`ssh.h`、cryptoの登録表を参照しました。PuTTYのID列は全実行可能algorithmを保証する一覧ではありません。

| 面 | 観測とOpenSSL方針との関係 |
|---|---|
| KEX | OpenSSH・DropbearはML-KEM/Curve25519、sntrup/Curve25519、ECDH、DHの候補を列挙しました。OpenSSHの実交渉はML-KEM/Curve25519です。DEFAULT・ML-KEM維持の[製品方針](openssl-pqc-groups.md)と矛盾しませんが、TLSのgroup設定をSSHへ流用した結果ではありません |
| cipher・MAC | OpenSSHはChaCha20-Poly1305を実交渉。PuTTYはAES-256 CTR・HMAC-SHA-256を表示しました。OpenSSHの能力には3DES/CBC/MD5/SHA-1も残り、実効default MACにもHMAC-SHA-1があります。現代的な方式を交渉できることと、旧方式の不許可は別です |
| host key・署名 | 3候補ともEd25519 host keyを確認し、Ed25519利用者鍵で認証しました。OpenSSHの`key`にあるRSA鍵種別と、`key-sig`のRSA-SHA2/SHA-1署名IDは区別します。PQC署名のquery表示を実交渉済みとはしません |
| provider・依存 | OpenSSHのDT_NEEDEDにはlibsslもありますがSSHはTLSではありません。DropbearとPuTTYはOpenSSLをリンクしません。`openssl.cnf`のTLS MinProtocol・CipherString・Groupsだけでは3候補のSSH policyを統一できません |

新しい製品既定へ旧方式を許可する判断はしません。導入時にはclient側のKexAlgorithms・Ciphers・MACs・HostKeyAlgorithms・PubkeyAcceptedAlgorithmsと上流defaultの差を決めてから、許可・拒否を実交渉で再検証します。今回の実験は[OpenSSL削減草案](openssl-minimal.md)を製品へ反映する変更ではありません。

## 鍵・known_hosts・保存

| 候補 | 既定の保存経路・観測 | 製品導入前の扱い |
|---|---|---|
| OpenSSH | `~/.ssh/known_hosts`、systemの`/etc/ssh/ssh_known_hosts`、`~/.ssh/id_*`。実験では明示した既存known_hosts・利用者鍵だけを使用し、HOMEの内容は不変 | `StrictHostKeyChecking=yes`、`UpdateHostKeys=no`等は実験条件。鍵登録・更新を利用者の明示操作に限定する設計が必要です。永続pathは未決定です |
| Dropbear | `~/.ssh/known_hosts`、既定の`~/.ssh/id_dropbear`。`-i`で変換済み鍵を使用。既存known_hostsにも`a+`でopenしますが、実験のhashは不変 | 今回の版はhostname文字列を直接比較し、非標準portの`[host]:port`だけでは一致しません。OpenSSHの全known_hosts書式との互換を仮定しません。readonly fallbackはsourceにあります |
| PuTTY | `PUTTYDIR`または`~/.putty`、`sshhostkeys`、sessions、randomseed。`-i`でPPKを指定し、`-hostkey`でpinを指定 | pin拒否時にもrandomseedの変更を確認しました。RAMへ置くか、永続化の時機と表示を設計する必要があります |

OpenSSHのagent・PKCS#11・FIDO helper、scp/sftp、serverのhost key生成は導入していません。実験用の鍵変換toolとstraceは測定用initramfsだけに追加し、容量比較に含めません。鍵の生成・輸入・変更、初回接続の登録には、[write-policy](../../design/write-policy.md)と§10のprogress・中断可否・英日表示の設計が残っています。例外を承認したり、実機で適合を確認したりした記録ではありません。

## 再照合

```sh
python3 board/cardputerzero/tools/bench/ssh-client-compare/inventory.py \
  --build output-ssh-compare-01 --serial output-ssh-runtime-06/serial.log \
  --check docs/research/component-options/ssh-client-options.csv
```

母集団はsourceから毎回抽出し、CSVの`variant/category/option`と比較します。CSVは原文のdefault式とhelpを残すため、数値の実効値がない項目を推測で補完しません。製品導入時の設定契約には追加確認が必要です。

複数行のCSV cellだけは`json:`に続くJSON文字列で表します。`json.loads(cell[5:])`で元の改行・空白を復元でき、原文の空白行をgit diff検査に合わせて削除しません。通常のcellは文字列のままです。configureの大文字も保持し、`--with-Werror`などの完全なtokenを列挙します。
