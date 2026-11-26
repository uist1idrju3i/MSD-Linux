# cryptsetup 2.8.7から2.8.9の変更と採否

## 範囲と一次資料

利用者承認済みの版更新であり、暗号化製品の置換や`/data`の実装ではない。既存のBuildroot recipeを維持し、OpenSSLと同じ`BR2_PACKAGE_OVERRIDE_FILE`と`BR2_GLOBAL_PATCH_DIR`による版・hashの上書きを使う。`vendor/`は編集しない。

[基準2.8.7](https://www.kernel.org/pub/linux/utils/cryptsetup/v2.8/v2.8.7-ReleaseNotes)、[2.8.8](https://www.kernel.org/pub/linux/utils/cryptsetup/v2.8/v2.8.8-ReleaseNotes)、[2.8.9](https://www.kernel.org/pub/linux/utils/cryptsetup/v2.8/v2.8.9-ReleaseNotes)の全release noteを読んだ。以下はその全節を分類したもので、security修正を任意のoptionと混同しない。新旧sourceのconfigure・Meson・CLI宣言とlicenseも別に照合する。

## 変更の分類と採否

| 版・分類 | 変更 | 採否・理由 |
|---|---|---|
| 基準2.8.7 互換性・security | AF_ALG非依存のfallback、keyringの寿命、PBKDF2衝突時のkey長検証、OpenSSL境界値、JSON解放、reencrypt名、tries overflow | 既に基準へ含まれる修正を維持する。既存のOpenSSL backendを変えず、AF_ALGの将来の制限を暗号性能の確認済み事項とはしない |
| 基準2.8.7 option・build・test | libgcryptのAria/Camellia、Mbed TLSのpkg-config、API flagの説明、legacy HMACのformat/open双方指定、jq試験 | 既に基準へ含まれる。別backendやlegacy integrityを新しく使わず、API・testの修正は維持する。新版で追加されたoptionとは数えない |
| 2.8.8 security | LUKS header restoreのTOCTOU、BITLK metadataのbuffer長・無限loop、32-bit AF長のoverflow、16を超えるkeyslot/tokenでのreencrypt初期化のメモリ破損 | 新版の修正をすべて採用。管理用処理や細工したmetadataをfail-closedにする。製品で現在呼んでいない経路まで実行確認済みとはしない |
| 2.8.8 新機能 | standalone integrityのkeyed discards | codeは更新するが有効化しない。kernel 7.3以上が必要で、製品は6.18系列。superblockの不可逆な更新を伴い、将来のLUKS2にも無条件でTRIMを許可しない |
| 2.8.9 高severity | OPAL segment digestの認証追加、LUKS2 PBKDF2 digest完全性、他user所有keyring keyの拒否 | 修正を採用。特にLUKS2 digest検証は通常unlockに関係する防御であり、再暗号化CLIを使わないことだけを理由に除外しない |
| 2.8.9 security | null cipherの検出、最小key長、integrityとのkey分割、OPAL/BITLKのkey長 | すべて採用。細工したheaderによる弱いkeyや境界外の値を拒否する |
| 2.8.9 security | backup segmentの重複・順序・requirement、cipher文字とmultikey、integrityなし認証algorithm、OPAL消去範囲、datashift、JSON ID・深さ、linear segment | metadata検証の強化をすべて採用。既存の不正metadataが拒否されることを互換性の注意点として残す |
| 2.8.9 security | 平文残留と一時headerの消去、offline log、FECとhash検証結果、plain可変hash、短いimageの拒否、hotzone境界 | すべて採用。永続storageへ新たな自動処理を追加せず、明示的に呼ばれた既存処理の修正だけを取り込む |
| 2.8.9 security | 同UUID keyring衝突、LUKS1 PBKDF2 reset、suspend/deactivate時のkey無効化、OPAL PINとTCRYPT headerの保護、double free、再open時の同一device確認、token失敗、dm table消去、BITLK欠損key、変換時salt長 | すべて採用。keyの寿命と異常系を強化する。LUKS1の問題は特定API順序で、通常CLIがその順序を呼ぶと断定しない |
| 2.8.9 通常修正 | offset計算、partial I/O、key payload長、errno符号、未初期化領域、verity salt・context・root hash、integrity付き変換とreencrypt拒否、keyslot領域、空keyslot、FVAULT2/TCRYPT/BITLK/LoopAES、PBKDF2寿命、labelとheader salt、解放済みpointer | すべて採用。個別の暗号方式を新しく製品用途へ採用する意味ではない |
| 2.8.9 build・test | clang/cppcheck警告の抑制、integrity parser、AF_ALG依存testの削除 | 上流の変更を保持。AF_ALGを製品で新しく有効化したり、こちらの検査を省略したりしない |
| 2.8.9 互換性 | 新しくformatするOPALはrequirement v2となり旧cryptsetupでは開けない。`repair`でmetadata更新が可能 | software dm-cryptを予定するSDの`/data`にはOPALを導入しない。既存deviceへのrepairやformatは今回行わない |
| 2.8.9 ABI | 既存symbolと後方互換、新symbol `crypt_repair_opal` | libraryを更新しsymbolを保持。OPALを扱う製品consumerは追加しない |

## 新しいoptionと既定値

| Option・API | 上流の既定値・変化 | MSD/Linuxでの扱い・理由 |
|---|---|---|
| `--allow-discards-keyed` | 2.8.8で追加。指定するとstandalone integrityのsuperblockを不可逆に更新し、以後は`--allow-discards`でもkeyed方式 | 有効化しない。必要kernelと実機確認が揃い、standalone integrityを選ぶ場合に再検討 |
| `--enable-enforce-opal-segment-digest` | 2.8.9で追加。未指定では旧OPAL metadataも受理。2.9では強制が既定になる予定 | 今回は既定を維持。SDのsoftware暗号化にOPALは不要で、OPAL deviceの互換性を変える設定は採用しない。OPALを製品要件に含める際に強制と移行を再検討 |
| `-Denforce-opal-segment-digest=true` | Mesonでの同じ設定。既定はfalse | BuildrootはAutoconfを使うため渡さない。上記と同じ理由で現時点では有効化しない |
| `crypt_repair_opal` | 新しいlibrary symbol | 使用しない。対象hardwareもmetadata移行要件もなく、呼出側を追加しない |

security修正そのものはすべて採用する。一方、上流のOPAL設定の既定変更予定を、2.8.9で既に変更済みと記録しない。既存のOpenSSL backend、libargon2、LUKS/PBKDFの設定、CLIの呼出側は維持する。Argon2の本番値はQEMUで決めない。

## source照合

2.8.9のtarballのSHA-256は`8667085a4f59174928948b501b4a2a68f7f1cce1cfe46170b8f40fa6534742b3`で、[上流のchecksum](https://www.kernel.org/pub/linux/utils/cryptsetup/v2.8/sha256sums.asc)と一致した。Buildroot recipeが列挙するlicense 5 fileは2.8.7とbyte単位で一致し、Apache-2.0、CC-BY-SA-4.0、GPL-2.0+とLGPL-2.1+、OpenSSL例外の宣言を維持する。

sourceの`configure.ac`の`AC_ARG_ENABLE`/`AC_ARG_WITH`、`meson_options.txt`の`option`、`src/utils_arg_names.h`のCLI名を抽出して集合差を照合した。件数は順に30から31、58から59、162から163。追加は上表のAutoconf・Mesonの同名設定とCLIの1件だけで、削除は0、表の不足は0だった。既存configure/Meson optionの宣言と既定値の変更はなかった。libraryのversion-infoは`23:0:11`から`24:0:12`で、SONAMEのmajorは12のままである。

## 監視と撤去

`check-pins.py upstream`でoverrideの実値、固定series内のstable archive、固定Buildroot recipeを照合する。rcは候補にせず、取得失敗や不正・重複した版は未確認とする。固定Buildrootのcryptsetupが2.8.9以上になったら、override撤去を「更新あり」で通知する。新しいseriesの採用とBuildroot全体の更新は別判断とする。

build・target・QEMU・licenseの結果は[実験記録](../../experiments/2026-11-26-cryptsetup-2.8.9.md)に残す。
