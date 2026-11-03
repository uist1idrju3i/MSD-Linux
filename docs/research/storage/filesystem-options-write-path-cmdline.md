# kernel command lineのwrite-path関連項目

[保存領域の調査へ戻る](README.md) / [filesystem option一覧](filesystem-options.md)

## 抽出範囲

Linux固定版6.18.59とmainline 7.4-rc1の`Documentation/admin-guide/kernel-parameters.txt`から、次のregexに一致する定義行を抽出しました。regexは依頼どおり固定し、category一致後の第1 tokenをoption名として照合します。

```regex
^\s+(root|rootflags|rootfstype|rootwait|rootdelay|ro|rw|mmc_|sdhci|block|dm_mod|dm-|elevator|ext4|f2fs|btrfs|nfsroot)\b
```

| option | 意味 | 既定値 | 固定版で使えるか | 最新版の変化 | MSD/Linuxでの扱い | 理由 |
|---|---|---|---|---|---|---|
| `root` `rootflags` `rootfstype` `rootwait` `rootdelay` `ro` `rw` `block` `nfsroot` | root device、filesystem、mount option、device待機、read-only起動、network root | bootloader/kernel config依存 | 可 | 同 | 現行のまま | `/data`ではなくroot boot pathを制御する。rootfsは既存のboot contractを保ち、data mountを変更する必要がある場合は別の明示的な設定とする。 |

上のregexで抽出されたtokenは9件です。このsource scopeでは`mmc_`、`sdhci`、`dm-`、`ext4`、`f2fs`、`btrfs`、`elevator` prefixに一致する独立した定義行はありません。これはkernel全体のboot argumentが9件だけという意味ではありません。

## 出典

- [固定版 kernel-parameters.txt](https://git.kernel.org/pub/scm/linux/kernel/git/raspberrypi/linux.git/tree/Documentation/admin-guide/kernel-parameters.txt?id=b3495ea401d709af0701a85babcba5e3d788a602)
- [Linux v7.4-rc1 kernel-parameters.txt](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/Documentation/admin-guide/kernel-parameters.txt?h=v7.4-rc1)
