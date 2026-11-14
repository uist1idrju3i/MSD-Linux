# zramの `=y` と `=m` の起動時間比較

- 状態: 計画
- 日付: 2026-11-15
- 担当: Devin
- 関連: [seedrngの非保存とzram遅延有効化](2026-11-13-seedrng-zram.md)、引き継ぎメモ残タスク5

## 目的と仮説

`CONFIG_ZRAM=y`（現行）と `=m` の起動時間の差を測る。前回はbuilt-in化と遅延有効化を同時に入れたため、`=y` と `=m` だけを変えた比較はまだない。

仮説：`=m` はzram・zsmalloc・zstdのmoduleをrootfsからloadする分だけ遅くなるが、kernel Imageが小さくなる分だけfirmwareがImageを読む時間は短くなる。QEMUでの差は小さいと予想するが、符号は事前には断定しない。

## 採否の基準（計測前）

- 各変種で5回以上bootし、`t_ready`（login promptまで）の中央値・最小・最大を比較する。
- 副次指標：swapが有効になるまでの時間（`run-zram.sh` の `=zram= finished` が出るまで）と、kernel Imageのbyte数とgzip -11相当のbyte数。
- `=m` 変種では `modprobe zram` を S99msd-zram に加えた写しを使い、swapが実際に有効になることも確認する。`=y` 側は現行製品のまま。
- 結果は「`=y` と `=m` で、QEMUの `t_ready` 中央値の差が ● 秒」という形で書く。差がばらつきの範囲なら「差は観測できなかった」と書き、統計的同等の証明とはしない。

## 条件

| 項目 | 値 |
|---|---|
| 基準の commit | 733d27e（main）＋計測器の変更 |
| ホスト | Ubuntu VM（版は記録時に埋める） |
| QEMU | （記録時） |
| Buildroot / kernel | `8b238854d909c9cce32ef9671d968b03e323b55d` / （記録時） |
| 出力先と状態 | `O=output`、cold build後のlinux-reconfigureで変種を構築 |
| 変える条件 | linux.fragment の `CONFIG_ZRAM`、`CONFIG_ZSMALLOC`、`CONFIG_ZRAM_BACKEND_ZSTD` を `y`→`m`（`=m` 側のみ `S99msd-zram` に `modprobe zram` を追加） |
| 変えない条件 | kernel以外のdefconfig、rootfsの他の内容、QEMU引数 |
| 繰り返し | 各5回以上、中央値・最小・最大 |
| 入力とバイナリ | runごとの入力hashと `run-qemu:` 行 |

## 手順

（実施時の実コマンドを記録する。概形：linux.fragmentを一時変更 → `make -C output linux-reconfigure` → `make -C output` → 変種imageを保存 → run-boottime.sh / run-zram.sh で計測）

## 計測器の検証

- run-boottimeのicount/tcgモードの既存実績を使う。`msd-zram` のappend引数でalgを変えたときにprobeが別の値を返すことは前回確認済み。
- `=m` で /dev/zram0 ができない場合（module未配置・depmod失敗）は試行を無効とし、原因を記録する。

## 結果・捨てた試行・結論・未確認・ログ

（実施後に書く）
