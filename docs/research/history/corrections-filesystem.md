# filesystem比較の訂正記録

[訂正一覧](corrections.md)へ戻る。

## 2026-11-22 v2第4段Aの停止状況と計測元

2026-11-22: [v2第4段A](../../experiments/2026-11-19-s04-fs-compare-v2-stage4.md)の全smokeは20件成功後、21件目の`E2/T1-negative-final`で停止した。カタログとfilesystem候補の継続中という記述を訂正した。「中間13点のうち9点で欠損」は試行とlogを特定できず、未確認とした。旧結果は保持し、判定修正後は新しい出力先で851件を最初から再実行する。

## 2026-11-11 phase1-r2のT2/T1結果訂正

phase1-r2でT2 `manifest_ok`が不足した原因は、W2のack markerとrename/fsyncの順序差、fscrypt keyfileの非永続化、最後のW3 marker後に残る有効tailを扱わない判定にあった。raw値は[phase1-r2記録](../../experiments/2026-11-10-phase1-matrix-r2.md)に保持し、修正後の[phase1-r3再測定](../../experiments/2026-11-11-phase1-t2-rerun.md)ではT2全20構成がrecovered/manifest_okとも20/20となった。I2 T1の未完了結果もtimeout延長後の再試行で完了した。いずれもQEMUの結果であり、実SDのFTL・物理電源断は未確認である。
