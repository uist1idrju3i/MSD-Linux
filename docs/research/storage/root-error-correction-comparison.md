# rootの破損検出と訂正の方式比較（dm-verity+FEC、btrfs DUPほか）

[保存領域の調査へ戻る](README.md)

rootパーティションの破損を、どの方式で検出し、どこまで訂正できるかを比べます。中心はdm-verity+FECとbtrfs DUP（dataとmetadataの両方）の比較で、ほかにrootへ使える方式も並べます。一次資料は2026-11-16に取得しました。この文書は調査と推論の記録で、製品の設定は変えていません。数値の例は資料のモデルから計算したもので、実測ではありません。

前提は次のとおりです。

- rootはRO SquashFSで、A/Bの2 slot（各256MB以下）に置きます（[rootfsの設計](rootfs-squashfs-verity-fec-design.md)）。
- 現行kernel（6.18.59）は `CONFIG_DM_VERITY=y`、`CONFIG_DM_VERITY_FEC=y`、`CONFIG_BTRFS_FS=y` で、EROFSは無効です（[linux.fragment](../../../board/cardputerzero/linux.fragment)）。
- `/data` は、LUKS2+btrfs（data・metadataともDUP、xxhash64）を設計中です（[`/data` の設計](data-luks-btrfs-design.md)）。この文書は `/data` の方針を変えません。

## 1. 結論

1. **検出の強さは、hashの選び方で決まります**。dm-verityは、すべてのblockをMerkle treeで確かめ、root hashまで連鎖させます。hashにSHA-256などの暗号学的hashを使い、root hashを署名などで認証すれば、意図的な改ざんも検出できます。ただし、[rootfsの設計](rootfs-squashfs-verity-fec-design.md)の現在の方針はcrc32cです（利用者の判断）。crc32cは暗号学的でないので、偶発的な破損は検出できますが、改ざんは検出できません。btrfsのchecksumも鍵を使わないので、btrfs単独では改ざんを検出できません。現在の方針どうしで比べると、検出はどちらも誤り検出で、強さの差はalgorithmで決まります。
2. **訂正の性質は違います**。btrfs DUPは、もう一方のcopyが健全であれば、壊れたblockがいくつあっても直せます。その代わり、容量と書き込みは2倍になります。dm-verityのFECは、RS符号をdevice全体にinterleaveして、少ない容量（roots=2で約0.8%）で長い連続した破損を直します。ただし、1つのinterleaveの組で `roots` 個を超えるblockが壊れると直せません。
3. **どちらも、同じSDカードの中での冗長性です**。カードの全損、controllerやFTLの故障には効きません。btrfsの上流の文書は、DUPの2つのcopyが、FTLによって同じphysical unitに置かれたり、同じ内容として統合されたりし得ると注意しています。FECのparityはdataと内容が違うので、統合される心配はありません。ただし、同じphysical unitに置かれ得ることは同じです。
4. **rootの推奨（案）**：今の設計どおり、SquashFS＋dm-verity＋FEC（roots=2から検討）とし、A/Bのもう一方のslotと、更新bundleからのslotの書き直しを、FECで直せない場合の回復手段にします。hashは現在の方針（crc32c）のままです。改ざんの検出が必要になったら、SHA-256とroot hashの認証へ移ることを、別の判断として扱います。rootにbtrfs DUPを使う案は勧めません。理由は、256MBのslotで容量が2倍になること、btrfsもROでmountできますが、そのときは壊れた側を書き直す自動修復が働かないと見込まれること（未確認）、SquashFS＋dm-verityなら将来SHA-256に移れば改ざんも検出できるのに対し、btrfsのchecksumは鍵を使わないので改ざんを検出できないことです。
5. **注意点**：現行kernelでは、panicモードのとき、hash treeの破損をFECで直せないことが多いと推論しています（[FECの上流動向](dm-verity-fec-upstream-2026-11.md)）。FECが救えるのは、主にdata blockの破損です。

## 2. dm-verity+FECとbtrfs DUPの比較

| 観点 | dm-verity+FEC | btrfs DUP（data・metadata） |
|---|---|---|
| 検出の単位 | data block（4 KiB）ごと。hash treeでroot hashまで連鎖する | data：sector（4 KiB）ごとのchecksum（checksum tree）。metadata：tree nodeごとのchecksum |
| 検出のalgorithm | 現在の方針はcrc32c（研究用formatterで生成）。veritysetupではsha256などの暗号学的hash | crc32c（既定）、xxhash（64 bit）、sha256、blake2 |
| 改ざんの検出 | 暗号学的hashでroot hashを認証すれば可能（`root_hash_sig_key_desc` など）。crc32cでは不可 | できない（鍵がなく、checksumを計算し直せる） |
| 検出の時機 | readのたび（`check_at_most_once` を付けると初回だけ） | readのたびと、利用者が始めるscrub |
| 訂正の仕組み | RS(255, 255−roots)をdevice全体にinterleave。hashで壊れたblockの位置が分かるので、消失として扱い、訂正できる量が2倍になる | もう一方のcopyを読み、checksumが合えばそれを返す。書き込めるmountなら、壊れた側も書き直す |
| 訂正できる範囲 | 1つのinterleaveの組（roots=2なら253 block）で、壊れたblockがroots個以下 | 同じ論理blockの2つのcopyのうち、片方が健全なら直せる |
| 容量の追加 | roots/(255−roots)。roots=2で約0.8%、roots=24で約10.4%。これにhash tree（SHA-256・4 KiBで約0.8%）が加わる | data・metadataとも約100% |
| 書き込み | なし（rootは読み出しだけ） | 書き込みが2倍（RO rootなら書き込みは更新のときだけ） |
| 直したblockの確かめ方 | kernelが、訂正したblockをhashで確かめてから使う。誤訂正はEIOになる | 読んだcopyをchecksumで確かめる |
| 訂正の記録 | 6.18.59ではなし。`fec_corrected_blocks` はv6.19以降のstatus | `btrfs device stats`、scrubの結果、kernel log |
| 両方が壊れたとき | EIO、またはpanic/restart（error modeによる） | EIO |
| 現行kernelの注意 | 再帰FECの無効化により、hash treeの破損はpanicモードで直せないことが多い（推論） | 上流の文書は、FTLがcopyを同じphysical unitに置いたり統合したりし得ると注意している |

### 2.1 連続した破損への強さ（計算の例）

256 MiBのrootを4 KiBのblockにすると、65,536 blockです。roots=2では1つのRS codewordが253 blockから1 byteずつ取るので、interleaveの組の数（ずらし幅）は 65,536÷253の切り上げで260 です。隣り合うblockは別の組に入るため、連続した破損は組ごとに散らばります。roots=2なら、1つの組で2 blockまで消失を直せるので、連続した破損は最大で約520 block（約2 MiB）まで直せる計算です。実際には、hash treeとFEC自身の領域の配置、破損の位置で変わります。B3の段階E（FECの境界）が、この境界を確かめる試験です。

btrfs DUPでは、2つのcopyは別のchunkにあります。片方のcopyで連続して壊れても、もう一方が健全なら長さに関係なく直せます。ただし、両方のchunkが同じ消去単位に置かれていると、両方が同時に失われ得ます。この配置はFTLが決めるので、hostからは制御も確認もできません。

### 2.2 偶発的な破損の種類ごとの見込み

| 破損の種類 | dm-verity+FEC | btrfs DUP |
|---|---|---|
| 少数のbitの化け（data） | 検出し、FECで訂正 | 検出し、copyで訂正 |
| 1 blockの読み出し不能（カードがEIOを返す） | FECで訂正（消失として扱う） | copyで訂正 |
| 連続数MiBの破損 | roots=2で約2 MiBまで（計算例）。それを超えると直せない | もう一方のcopyが健全なら訂正 |
| hash tree・metadataの破損 | 検出はする。panicモードでは訂正できないことが多い（推論） | metadataのcopyで訂正 |
| 広い範囲に散らばった破損 | 組ごとにroots個を超えると直せない | 同じblockの両方のcopyが壊れなければ訂正 |
| 意図的な改ざん | 暗号学的hashでroot hashを認証した場合だけ検出。crc32cでは検出できない | 検出できない |
| カードの全損・FTLの故障 | どちらも直せない（A/Bの別slotも同じカード） | 同左 |

## 3. rootに使えるほかの方式

| 方式 | 検出 | 訂正 | 改ざんの検出 | rootへの適合 | 判断（案） |
|---|---|---|---|---|---|
| SquashFS単独 | 形式にchecksumはない（kernel文書の構造にchecksum欄がない）。伸長の失敗で一部を検出し得る | なし | なし | 現行 | dm-verityと組み合わせる前提。`errors=panic` は検討の余地あり |
| EROFS | superblockのchecksum（CRC32C、mkfs.erofsの `-E nosbcrc` で無効にできる）。dataのchecksumは持たない | なし | なし（dm-verityと組み合わせる） | kernelで無効 | SquashFSとの比較は別の課題。誤り訂正の観点では差がない |
| dm-integrity（単独） | sectorごとのtag（crc、hash、HMAC）。不一致はEIO | なし | HMACなら可能 | 書き込めるdevice向け（journalで書き込みが2倍） | RO rootには不要。dm-verityで足りる |
| dm-integrity＋RAID1（lvmraidの `--raidintegrity`） | sectorごとのtag | 別のimageから読み、壊れた側を書き直す | crcでは不可 | 同じカードに2つのpartitionが必要。容量は2倍以上 | btrfs DUPと同じく、同じカードの中の冗長性。RO rootには過大 |
| fs-verity | fileごとのMerkle tree。不一致のreadは失敗する | なし | digestを認証すれば可能 | ext4、f2fs、btrfsだけ。SquashFS・EROFSは対象外 | rootには使えない。`/data` のfileの保護で検討 |
| ext4の `metadata_csum` | metadataだけ | なし | なし | rootをext4にする案だけ | 不採用（RO SquashFSを使う） |
| btrfs single＋checksum | checksum | なし（copyがない） | なし | 書き込めるroot | 不採用 |
| A/Bの別slotへの切り戻し | 検出は他の方式に頼る | image全体を別slotで置き換える | 別slotも検証すれば可能 | 現行の設計（Phase Cで試験） | 採用。FECで直せないときの手段 |
| 更新bundleからの書き直し | bundleの署名を確かめる | 壊れたslotを丸ごと書き直す | 可能 | RAUC・SWUpdateの比較で扱う | 採用の候補。利用者の操作とprogressの表示が必要（AGENTS.md §10） |
| image単位のparity file（par2など） | 検出は他の方式に頼る | userspaceでslotを直す | なし | 書き直しはslotへの書き込みになる | FECと役割が重なる。不採用の候補 |
| SDカード内部のECC | カードの中だけ。hostからは見えない | カードの中だけ | なし | 常にある | 前提として扱う。直せないとEIOが返る |
| UBI・UBIFS | 対象外 | 対象外 | 対象外 | raw NAND向けで、SDカードには使えない | 対象外 |

## 4. MSDで確かめること

1. B3の段階D（rootsの違い）と段階E（FECの境界）で、§2.1の計算と実際の境界を比べる。
2. Phase Cで、error mode（panic、restart、EIO）とFECの組み合わせ、A/Bの切り戻しを比べる。
3. `/data` のbtrfs DUPで、片方のcopyへ破損を入れ、read repairとscrubの動きをQEMUで確かめる（ROのmountで壊れた側を書き直さないかも含む）。QEMUでは、FTLによるcopyの配置や統合は再現できない。
4. 実機（SDカード）で、読み出し不能のblockが出たときにカードが返すerrorの種類を確かめる。

## 5. 一次資料

| 資料 | 使った内容 |
|---|---|
| [kernel文書 dm-verity](https://docs.kernel.org/admin-guide/device-mapper/verity.html) | FECのinterleave、roots、容量、訂正後のhashの検査 |
| [btrfs Checksumming](https://btrfs.readthedocs.io/en/latest/Checksumming.html) | checksumのalgorithmと性質 |
| [btrfs Scrub](https://btrfs.readthedocs.io/en/latest/Scrub.html) | 複製のあるprofileでの自動修復、書き込めるmountでのread repair、scrubは複製からしか直せないこと |
| [mkfs.btrfs(8)](https://btrfs.readthedocs.io/en/latest/mkfs.btrfs.html) | DUP、metadataの既定、hardwareによる重複排除の注意 |
| [kernel文書 dm-integrity](https://docs.kernel.org/admin-guide/device-mapper/dm-integrity.html) | journal・bitmap、crcとHMAC、EIO |
| [lvmraid(7)](https://github.com/lvmteam/lvm2/blob/main/man/lvmraid.7_main) | RAIDとdm-integrityを組み合わせた検出と訂正、容量 |
| [kernel文書 fs-verity](https://docs.kernel.org/filesystems/fsverity.html) | fileごとのMerkle tree、対応するfilesystem |
| [kernel文書 SquashFS](https://docs.kernel.org/filesystems/squashfs.html) | 形式の構造、`errors=` option |
| [mkfs.erofs(1)](https://git.kernel.org/pub/scm/linux/kernel/git/xiang/erofs-utils.git/tree/man/mkfs.erofs.1) | superblockのchecksum（`nosbcrc`） |
| [Btrfsのformat、mount、checksum](filesystem-options-btrfs.md) | DUPとQEMUの限界（既存の調査） |

## 6. 未確認

- §2.1の計算は、kernel文書のinterleaveのモデルによるもので、実測していない。
- btrfsをROでmountしたときに、read repairがcopyを返すだけで書き直さないかを確かめていない。
- SquashFSの伸長器（zstd、xz）が、frameのchecksumで破損を検出するかを確かめていない。
- SDカードのFTLが、DUPのcopyやFECのparityをどこに置くかは、hostから確かめられない。
