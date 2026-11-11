# 第1段T2 manifest追試

- 状態: 完了（QEMU、T2 60回、F5 W3追試、E1負対照）
- 対象: phase1-r2で観測したT2のW2 checker不一致とfscrypt keyの永続性、およびF5 W3末尾
- 目的: 修正後のT2を対象3構成で再測定し、T1負対照とW3末尾の判定を確認する

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

F5の`phase1-r2`とは別のrun `t2fix-check-T2-F5-r1-1794321334`では、`W3/append.log`のhashが一致しなかった。最後のmanifest markerは`w3-record-000-0700`で、expected hashは`7d80169450b9a6f5943a8cd7b020d5b057b2b6873cfaef555a05ce94132a3bc3`、actual hashは`b4057caae72728ca9ddf2632972b67865c23abc4ccae548b00f2bb4f3efd3d54`だった。actual hashは、workloadが生成する決定的なW3 record 1～750の内容と一致した。`run_w3`は50 recordsごとにfileをfsyncしてからmanifest markerを記録するため、最後のmarkerより後のbatchが残った結果と整合する。当該60回の追試ではW3 checkerを変更していなかったため、F5の`manifest_ok`は19/20であり、20/20には達していない。

T1負対照としてE1の`T1-negative-final`を1回実行した。run `t2fix-check-T1-negative-final-E1-1794323357`は177秒で`ok`となり、summaryは`loss_points=1`、logは`T1_NEGATIVE_CONTROL loss_detected=yes`を記録した。

## W3末尾の追加検証

保存済みF5 run `t2fix-check-T2-F5-r1-1794321334`の`sdcard.img`を複製し、複製のrootfs partitionだけを検証用rootfsに置き換えた。data partitionは再作成せず、両方のimageを`msd.fscmp.phase=verify`で起動した。T2 20回の再実行は行わず、保存済みimage 1件を検証した。

正例では、marker `w3-record-000-0700`のexpected hashが`7d80169450b9a6f5943a8cd7b020d5b057b2b6873cfaef555a05ce94132a3bc3`だった。logは`recovery_fsck=0`、`recovery_mount=ok`、`manifest_w3_tail_durable path=W3/append.log records=50`、`manifest_ok=yes files=202`を記録した。marker後の決定的な50 records、すなわちrecords 701-750が受け入れられた。

負例では別のimage copyの回復mount後、検証用guestが`W3/append.log`に4 byteの文字列`torn`を追記してから`sync`し、manifestを検証した。logは`manifest_hash_mismatch path=W3/append.log`と`reason=partial_record_tail`、`manifest_ok=no files=202`を記録した。

検証用guest scriptのSHA-256は`7f9241786d8fa930f91e75e993845618ee843313b56cff201e127f8b84f04bf9`、workload binaryは`e13a2b70718905af0ebb60c24728ca4d3c7c63acc98489e2b20daed142208310`だった。QEMU 11.1.2（binary SHA-256 `c8cf5be13646711580e18346dcd036c0f2a210dd90f84bf784247c5838940410`）、kernel image SHA-256 `33454149eb370971ee08cea85aed61a0a14bda6eb3b4b7cef762c56d64ebbdac`を使った。正例と負例のQEMU log SHA-256はそれぞれ`a72d900353e1e7a81667c396a266c95963b77acf4ae3d088e9f425412b92ec9c`と`5ac237b7dc4cfccc8644fb449a0d66f8763d682c9290aba81cc713a3b02bfc4b`だった。

追加のE1 `T1-negative-final` run `t2fix-check2-T1-negative-final-E1-1794324971`は194秒で`ok`となった。summaryの`loss_points=1`とlogの`T1_NEGATIVE_CONTROL loss_detected=yes`で、負対照がlossを検出した。QEMU起動時のimage SHA-256は`6c776e7e6880d329243b0e6a8c819276c39de91b64f23a25805db14c4a34f36a`、log SHA-256は`b8cbe9aecf1d56d7639fa1c9a648ba8e220e80ffc524b1dfd5abd31636062b5d`だった。

この1 image検証はT2 20回の再実行に含まれない。phase1-r2の集計値はrecovered 20/20、F5 `manifest_ok=19/20`である。

## 制約

phase1-r2のT2 `manifest_ok`とI2 T1未完了結果は[phase1-r3再測定](2026-11-11-phase1-t2-rerun.md)で置換する。phase1-r2のraw logは[data branch](https://github.com/uist1idrju3i/MSD-Linux/tree/data/fs-compare-experiments)の`fs-compare/phase1-r2.tar.zst`（SHA-256 `5138e019255284911bbee38a3cddcdf350b0c62c6d17f6cca4c206ea6a46aa79`）にある。

これらはQEMU上の結果であり、実SDカードのFTL、カード内write cache、物理的な電源断挙動を検証したものではない。
