# ロスレス再圧縮ツールの調査（2026-11）

デコーダ側を一切変えずに、同じフォーマットのまま圧縮率だけを上げる手法（zopfli 型アプローチ）を網羅的に調査しました。依頼の参考記事（Qiita「丁寧なzip/gzip」）が扱う deflate 系に加え、PNG・JPEG・PDF などのコンテナ別最適化、前処理フィルタ、さらに zstd/xz/brotli 等の「別フォーマットだが同思想」の比較対象まで調べました。調査のみで、採否・実装の決定は行いません。

## 1. アプローチの分類

| 系統 | 説明 | 代表 |
|---|---|---|
| A. deflate 再圧縮 | LZ77 パースとハフマン符号化を最適解に近づける（optimal parsing＋ブロック分割）。出力は gzip/zlib/zip 互換 | zopfli、ECT、kzip、7-Zip deflate、libdeflate |
| B. ストリーム後処理 | 既存 deflate ストリームを読み、ハフマン表だけ組み直す等の微細最適化 | deflopt、defluff、huffmix、kzipmix |
| C. コンテナ別最適化 | PNG の予測フィルタ試行、JPEG のハフマン最適化・プログレッシブ化など、フォーマット固有の再エンコード | oxipng、pngcrush、jpegtran、mozjpeg、ECT、pdfsizeopt |
| D. 前処理・再構成 | deflate ストリームを「どう圧縮されたか」まで解析し、再圧縮に有利な形へ可逆的に戻す | preflate、precomp |
| E. 高圧縮エンコーダの再実行 | 同一コーデックでより重い探索モードを使う（zstd -22、xz -e、flac -8ep など） | 各コーデック付属ツール |

A〜D はすべて「出力を既存デコーダがそのまま読める」点が共通です。E はフォーマットが異なるため厳密には別物ですが、「エンコード時間と引き換えにデコーダ変更不要の率向上」という思想は同一です。

## 2. deflate 系（zip/gzip/zlib）ツール

| ツール | ライセンス | 特徴 | 本機との関係 |
|---|---|---|---|
| zopfli（Google） | Apache-2.0 | 最適パースを反復しブロック分割も試行。zlib -9 より数％高い率を出す定番。非常に低速 | 実装は pigz -11 経由で導入済み（後述） |
| pigz -11 | zlib 系 | gzip 並列実装。`-11` は zopfli の deflate を呼ぶモード | `post-image.sh` が kernel8.img 生成に使用中【一次】 |
| ECT（Efficient Compression Tool） | Apache-2.0 | zopfli 系の改良。PNG/JPEG/GZIP/ZIP を扱い、多くの場合 zopfli より速く高率【一次: fhanau/Efficient-Compression-Tool】 | 未導入。Buildroot パッケージもなし。host ツールなら実装候補 |
| 7-Zip deflate | LGPL+unrar条項 | `-tzip -mm=Deflate -mx=9` で zlib より高率な zip | zip 生成向け。gzip 単体は別ツールが楽 |
| KZIP | フリーウェア（ソース非公開） | Ken Silverman 作。古代から高圧縮 zip の頂点 | 再配布不可・バイナリのみ → 対象外 |
| zopfli KrzYmod | フォーク | 本家より多くの設定を追加した改良版（記事紹介。GitHub 上の正規リポジトリは未確認） | 未確認 |
| libdeflate | MIT | 高速で zlib -9 よりわずかに高率。zopfli 級ではないが実用域 | Buildroot に `BR2_PACKAGE_LIBDEFLATE` あり |
| AdvanceCOMP（advzip/advdef/advgzip/advpng） | GPL-3.0 | 7-Zip 系 deflate ＋ オプションで zopfli | zip/png/gz 再圧縮の定番ツール群 |
| Leanify | MIT | zopfli を内蔵し PNG/JPEG/SVG/XML 等を再帰的に最小化 | 入れ子コンテナの再圧縮に強い |
| deflopt / defluff | フリーウェア | deflate ストリームの符号割り当てを後から最適化 | 補助的。ソース非公開 |
| huffmix / kzipmix | フリーウェア | 複数 deflate 出力から最良ブロックを混ぜる荒技 | 同上 |
| ツンデレ Zipper | フリーウェア | vector 系の実験的ツール（記事紹介） | 未確認・参考 |

## 3. コンテナ別の最適化

### 3.1 PNG

| ツール | ライセンス | 仕組み |
|---|---|---|
| optipng | zlib/libpng 系 | zlib レベルとフィルタを総当たり |
| pngcrush | libpng 系 | 全フィルタ組み合わせを brute force |
| oxipng | MIT | zopfli 系 deflate ＋フィルタ試行＋マルチスレッド |
| advpng（AdvanceCOMP） | GPL-3.0 | 7-Zip deflate ＋ zopfli オプション |
| ECT | Apache-2.0 | 独自改良 zopfli ＋フィルタ探索 |
| zopfliPNG | Apache-2.0 | zopfli リポジトリ付属の PNG 版 |
| pngwolf / pngwolf-zopfli | 派生 | 遺伝的アルゴリズムでフィルタ列を探索（zopfli フォーク版あり）【一次: hoehrmann/pngwolf】 |
| PNGOUT | シェアウェア | KZIP ベース。クローズド → 対象外 |
| pngquant / pngnq | GPL/独自 | 減色による劣化圧縮（不可逆）→ 対象外（参考） |

### 3.2 JPEG（再エンコード・不可逆なしの枠組み）

| ツール | ライセンス | 仕組み |
|---|---|---|
| jpegtran -optimize / -progressive | IJG 系 | ハフマン表最適化・スキャン構成変更。DCT 係数は無変更 |
| jpegoptim | フリー | jpegtran と同系の最適化＋削減オプション |
| jpegrescan | フリー（Perl） | プログレッシブ・スキャン構成の総当たり |
| mozjpeg | BSD-3-Clause | 量子化・トレリス最適化で高率なエンコーダ（出力は標準 JPEG） |
| Guetzli | Apache-2.0 | 知覚品質を保つ再エンコード（係数が変わるため厳密には非可逆） |
| jpegli | BSD-3-Clause（libjxl 内） | Google の新エンコーダ。標準 JPEG を出力 |

jpegtran 系と mozjpeg は「デコーダに変更なし」。Guetzli/jpegli は見た目を保つ近似（実用上の可逆）で厳密な byte-同一ではない点に注意します。

### 3.3 その他コンテナ

| ツール | ライセンス | 対象 |
|---|---|---|
| gifsicle -O3 | GPLv2 | GIF の LZW 再最適化・フレーム差分 |
| pdfsizeopt | GPL-2.0 | PDF 内の deflate/jbig2 等を jbig2enc+zopfli で再圧縮 |
| Leanify | MIT | SVG/XML/woff 等の入れ子を再帰最適化 |
| mksquashfs / mkfs.erofs | — | ブロックサイズ・`-Xcompression-level`・フィルタ・`-sort` で同コーデック高率化（§5） |

## 4. 前処理・再構成系

| ツール | ライセンス | 仕組み |
|---|---|---|
| preflate | Apache-2.0 | deflate ストリームを解析し「元データ＋再現パラメータ」へ可逆展開。後で任意の deflate で byte 同一を再生成できる |
| precomp | Apache-2.0 | 圧縮済み領域を展開→より重い設定で再圧縮し、差分情報で byte 同一を保証（失敗時は元データを残す安全設計） |
| xz BCJ フィルタ | 公有/LGPL | 実行ファイルの分岐アドレスを絶対値化し LZ の hit 率を上げる前処理（mksquashfs xz でも `-Xbcj` で同等） |

preflate/precomp は「zip-in-zip 問題」（PNG 内 IDAT、zip 内圧縮メンバなど、コンテナ内の deflate をさらに重ね圧縮する場合）に効く前処理です。MSD の更新バンドルや CI 成果物の入れ子を詰める際の選択肢になります【推測】。

## 5. 同思想の別フォーマット（参考比較）

厳密にはデコーダが違うため本題の対象外ですが、「エンコードを重くして率を上げる」という目的では同じ設計空間です。

| コーデック | 高率化の手段 | 備考 |
|---|---|---|
| zstd | `--ultra -22` / `btultra2` 最適パーサ、window/dictionary 設定 | squashfs -Xcompression-level 22 が該当（§6） |
| xz / lzip | `-9e`（最適化パース）、辞書サイズ、BCJ フィルタ | LZMA の optimal モード |
| brotli | `-q 11`、静的辞書 | Web 前提。別フォーマット |
| 7z / LZMA2 | `-mx=9`、辞書・フィルタ | |
| zpaq | `-m5`、コンテキスト混合 | アーカイブ用途 |
| lz4hc | `-12` 高率モード | erofs の `-zlz4hc` 相当 |
| FLAC | `-8 -e -p`（全探索） | 音声。decode は同一 |

## 6. MSD/Linux への適用メモ

| 箇所 | 現状 | 残る余地 |
|---|---|---|
| kernel8.img | `pigz -11 -n`（zopfli deflate）＋ `gunzip|cmp` 検証済み【一次: board/cardputerzero/post-image.sh】 | ECT -9/-gzip でさらに数％余地の可能性。実測要。zopfli --i（反復数）増加も選択肢 |
| rootfs.squashfs | `SQUASHFS4_ZSTD` ＋ `EXTREME_COMP`（= `-Xcompression-level 22`、Buildroot 定義で最高水準）【一次: vendor/buildroot/fs/squashfs/Config.in】 | 既に最高設定。ブロックサイズの既定（128K）を上げる案はランダムアクセスとのトレードオフ要検討 |
| 起動順ローカリティ | `board/cardputerzero/squashfs-sort.txt` でファイル順を制御済み | 圧縮効率としても寄与する前処理（同種データの近接化） |
| msd-update バンドル | plain tar（rootfs.squashfs + boot.vfat + manifest + sig） | 既に圧縮済みの squashfs を内包するため tar はほぼ非圧縮で妥当。圧縮するなら gzip/zstd はデコーダ互換不要（自前バンドル） |
| public_html の画像 | 未最適化かどうか未確認 | ECT/oxipng での lossless 削減が候補（サイト表示品質を変えずに軽量化） |
| CI 成果物（artifact の zip） | actions/upload-artifact の既定 | 再圧縮の余地は小さい。対象外寄り |
| host ツールの整備 | `BR2_PACKAGE_HOST_PIGZ=y` で導入済み | ECT は Buildroot にないため host ツールを追加する場合は vendor 追加か docker 側で |

## 7. 未確認事項

- kernel8.img への ECT -9 / zopfli --i 効果の実測（pigz -11 との差分）。期待は数％程度。
- ECT の Buildroot 収録なしを確認したが、導入形態（vendor package 追加 or docker 内ツール）は未検討。
- public_html 内画像の現状サイズと最適化履歴。
- KrzYmod・ツンデレ Zipper の配布状況とライセンス詳細（記事に名前のみ）。
- pngwolf-zopfli の完成度（開発停止気味か）。
- xz/lzma・brotli を squashfs/erofs の代替として比較した記録は boot-and-kernel 系文書側にあるか照合が必要。

## 8. 主な出典（2026-11-02 確認）

- https://qiita.com/mashuel/items/75b8257d3b8084f5866e（「丁寧なzip/gzip」：7zip/kzip/zopfli/pigz/KrzYmod/ECT/libdeflate/ツンデレ Zipper の紹介）
- https://github.com/google/zopfli（Apache-2.0）
- https://github.com/fhanau/Efficient-Compression-Tool（Apache-2.0、PNG/JPEG/GZIP/ZIP 対応）
- https://github.com/ebiggers/libdeflate（MIT）
- https://github.com/amadvance/AdvanceCOMP（GPL-3.0）
- https://github.com/JayXon/Leanify（MIT）
- https://github.com/schnaader/precomp-cpp（Apache-2.0）
- https://github.com/deus-libri/preflate（Apache-2.0）
- https://github.com/hoehrmann/pngwolf（PNG フィルタの遺伝的探索）
- https://github.com/shssoichiro/oxipng（MIT）
- https://github.com/mozilla/mozjpeg（BSD-3-Clause）
- https://github.com/google/guetzli（Apache-2.0）
- https://github.com/libjxl/libjxl（jpegli、BSD-3-Clause）
- `vendor/buildroot/fs/squashfs/{squashfs.mk,Config.in}`（EXTREME_COMP = zstd -Xcompression-level 22）
- `vendor/buildroot/package/{pigz,libdeflate,brotli,lzip,pixz,python-zopfli,xz,zstd,lz4}`（収録確認）
- `board/cardputerzero/post-image.sh`（pigz -11 + 検証）、`board/cardputerzero/squashfs-sort.txt`
- `configs/msd_cardputerzero_defconfig`（SQUASHFS4_ZSTD / EXTREME_COMP / HOST_PIGZ）
