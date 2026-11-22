# RAUC Phase Aのtext証拠

`streaming-phase-a-2026-11-23.tar.zst`は、RAUC 1.15.2のhost build、
HTTP streamingのmetadata試験2 run、公開Release API観測のtext証拠です。
実験の条件・解釈はmain側の
`docs/experiments/2026-11-23-rauc-streaming-poc.md`に記録します。

- 487 file。各memberのhashは同名`.files.sha256`。
- 初回HTTP runのpurpose不一致による失敗55試行を保持します。
- 公開用のbuild log 1 fileだけ、署名付きURLのqueryを伏せています。
  変更前後のhashと除外した公開binary 20 fileは同名`.selection.json`。
- 秘密鍵のdirectoryは内容・hashとも収録しません。
- bundle、slot imageは除外します。再生成時は新しい試験CAを作るため、
  入力imageが同じでも証明書・bundleのhashは変わります。
- このbranchは削除・mergeしません。
