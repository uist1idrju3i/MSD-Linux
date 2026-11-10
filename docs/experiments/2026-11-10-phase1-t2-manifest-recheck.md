# 第1段T2 manifest追試

- 状態: 完了（QEMU、E5/F5/F3各20回）
- 対象: phase1-r2で観測したT2のW2 checker不一致とfscrypt keyの永続性
- 目的: 修正後のT2を対象3構成で再測定し、T1の負対照を再確認する

## 条件

| 項目 | 値 |
|---|---|
| 基準commit | `8b5daefb43ebcb980eb84b0455f3336cf74d4014` |
| workload binary SHA-256 | `e13a2b70718905af0ebb60c24728ca4d3c7c63acc98489e2b20daed142208310` |
| test | T2、E5/F5/F3各20 invocation。各invocationで電源断・再起動1回 |
| run ID接頭辞 | `t2fix-check` |
| plan SHA-256 | `53e1cad4c7eb60ccd38d94aa6c50478fc56f5ef39a85f479c2056bce6288caac` |
| raw CSV | [60 attempts](2026-11-10-phase1-t2-manifest-recheck.csv)、SHA-256 `107519ac84893cbdc7277413accc836b15bce04d0784110e3f9eb0235c6a26c3` |

T2のmatrixは60 plan rowsを各1 attemptで完了した。全attemptのdriver statusは`ok`で、recoveredは全構成20/20だった。

## 結果

| 構成 | recovered | manifest_ok | `manifest_w2_inflight_durable` |
|---|---:|---:|---:|
| E5 | 20/20 | 20/20 | 2 |
| F5 | 20/20 | 19/20 | 2 |
| F3 | 20/20 | 20/20 | 3 |
| 合計 | 60/60 | 59/60 | 7 |

recovery logに`fscrypt_policy_failed`はなかった。phase1-r2のW2不一致に対するin-flight hash受け入れは、対象3構成で計7回記録された。

F5の`phase1-r2`とは別のrun `t2fix-check-T2-F5-r1-1794321334`では、`W3/append.log`のhashが一致しなかった。最後のmanifest markerは`w3-record-000-0700`で、expected hashは`7d80169450b9a6f5943a8cd7b020d5b057b2b6873cfaef555a05ce94132a3bc3`、actual hashは`b4057caae72728ca9ddf2632972b67865c23abc4ccae548b00f2bb4f3efd3d54`だった。actual hashは、workloadが生成する決定的なW3 record 1～750の内容と一致した。`run_w3`は50 recordsごとにfileをfsyncしてからmanifest markerを記録するため、最後のmarkerより後のbatchが残った結果と整合する。W3 checkerは依頼の範囲どおり変更していない。このためF5の`manifest_ok`は19/20であり、20/20には達していない。

T1負対照としてE1の`T1-negative-final`を1回実行した。run `t2fix-check-T1-negative-final-E1-1794323357`は177秒で`ok`となり、summaryは`loss_points=1`、logは`T1_NEGATIVE_CONTROL loss_detected=yes`を記録した。

## 制約

これらはQEMU上の結果であり、実SDカードのFTL、カード内write cache、物理的な電源断挙動を検証したものではない。全run directoryとQEMU logはrun保存先に保持している。
