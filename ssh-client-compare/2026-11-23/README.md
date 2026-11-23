# SSH client比較（2026-11-23）の証拠

OpenSSH・Dropbear・PuTTYのclient-only比較です。要約と全生値CSVはcode branchの`docs/experiments/2026-11-23-ssh-client-compare.md`にあります。

`pack-02/evidence.tar.gz`には129 fileとmanifestの計130 memberを収録しました。build失敗、sort wrapperを使った容量試行、6回のruntime、正式な容量、option抽出物、入力hash、公開鍵を保存しています。全memberのbyte列を照合しました。

- archive SHA-256: `91f1c8e2467a13242a6b3eab9316e026493528f3ae1af14f5e86d3686a080139`
- archive size: 676,360 bytes
- `pack-02/manifest.json`: 元fileと公開copyのSHA-256・bytes・変更の有無
- `pack-02/verification.json`: member数とarchiveの照合結果

公開copyの5 fileはURL query・Set-Cookieを伏せました。元logは変更せず、元hashと公開copyのhashを分けています。秘密鍵・root tree全体・initramfs・SD image・実行binaryは収録していません。過去の事前試行はrunner hashのみのものもあり、当時のrunner本文をすべて保存したとは主張しません。guestの実行scriptは各rootの`init`から収録しています。

最初のpackは固定containerにzstd commandがなく、archive作成前に失敗しました。最初の`manifest.json`と`packing-01-failure.json`を保持し、Python標準libraryのgzipで別のpack-02を作りました。候補clientの試験結果とは別の準備失敗です。

正本の保存先は、merge・削除しない共有証拠branch `data/fs-compare-experiments`の`ssh-client-compare/2026-11-23/`です。初回の証拠commit `b47bc80e771debd276517bab4027d14c9a726ef0`からarchive・manifest・失敗記録をbyte単位でそのまま移しました。READMEの保存先案内だけを更新し、旧branch `devin/1795399034-ssh-client-evidence`は今回削除していません。実行中smokeと凍結cloneには触れていません。

取得後は`tar -xzf pack-02/evidence.tar.gz`で展開できます。fixture鍵は再生成するため、再実行時のhost fingerprintやserial全体のhashの一致は要求しません。測定binary・入力と容量imageのhashはmanifestと実験記録で区別してください。
