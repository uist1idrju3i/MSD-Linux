# PPD path-map 残差解析

`analyze_residuals.py` と `trace_references.py` は、#30 の P0 残差解析に使った script である。解析処理には手を入れず、VM 固有の入力 path を環境変数から受け取る形にした。変更前後の SHA-256 と変更行は [実験記録](../../../../../docs/experiments/2026-10-21-ci8-ppd-pathmap.md) に記録した。

`run-analysis.py` は 2 つの解析 script を順に実行する driver である。Buildroot の build は行わない。

## 入力形式

`--root` directory には、`v4l2-compliance` と `v4l2-ctl` の各 binary について、`c0` と `c1` の raw `.rodata.bin`、`.rodata.path-stripped.<side>.bin`、`.readelf-sections.txt`、`.disasm.txt`、`.disasm.normalized.txt` を置く。必要なファイルは計 20 件となる。

`.rodata.path-stripped.*.bin` は、解析 script が raw `.rodata` から再生成し、保存済みの file と一致するか検査する。出力 directory は `--out` で指定する。元の解析出力と比較する場合は、別の空 directory を指定する。

## 実行

```sh
python3 board/cardputerzero/tools/bench/ppd-pathmap/run-analysis.py \
  --root /path/to/p0-analysis-inputs \
  --out /path/to/reanalysis-output
diff -ru /path/to/original-analysis-output /path/to/reanalysis-output
```

同じ指定は `PPD_PATHMAP_ROOT` と `PPD_PATHMAP_OUT` の環境変数でも渡せる。両解析 script を単独で実行する場合も、同じ環境変数を使う。`ROOT` の既定値はこの directory の `inputs`、`OUT` の既定値は `ROOT/rodata-residual` である。
