---
name: product-io-policy
description: MSD-Linux の製品（rootfs、init script、更新、暗号化、対話型ツール）で、SDカードへ書き込む処理、時間のかかる処理、利用者向けの画面の文言を設計・実装・確認するときに使う。AGENTS.md §10 の規則（意図しない時に書き込まない、2秒以上かかり得る処理ではprogressを表示する、画面は英日併記）を守るための手順と、docs/design/write-policy.md の台帳の更新方法を示す。
---

# product-io-policy（書き込み・progress・画面の文言）

AGENTS.md §10 の規則を、設計と実装のたびに確かめる手順です。規則の本文はAGENTS.mdにあり、例外と現行の不適合は [書き込みの台帳](../../../docs/design/write-policy.md) にあります。

## 1. 対象

- 製品のimageに入るもの：init script、daemon、`/usr/sbin` のtool、kernelとfile systemの設定、更新framework、暗号化、対話型ツール。
- 対象外：開発用OCI、CI、ホストのtest、`board/cardputerzero/tools/bench/` などの測定用のscript。ただし、測定用のhookを製品のimageに残さないことは確かめます。

## 2. 書き込みの設計

1. 永続storage（SDカードの全partition：FATのboot、A/Bのslot、`/data`）へ書き込む箇所を、新しく足す前に台帳で探します。
2. 書き込みは、次のどちらかの時機に限ります。
   - 利用者の操作の直後（確認の画面で同意した後など）
   - progressを表示している間
3. 起動のたび、停止のたび、一定間隔で書き込む処理は、原則として作りません。避けられない場合は、台帳に例外として登録し、理由、時機、量の目安、利用者への見え方を書きます。
4. log、cache、lock、一時fileはRAMに置きます。`/var/log`、`/var/cache` は `/tmp`（tmpfs）へのsymlinkです。圧縮したRAM（zram）を使うかは、まだ決まっていません。
5. kernelとfile systemが裏で行う書き込みも対象にします。例：ext4のjournal commitと `lazy_itable_init`、F2FSのcheckpoint・background GC・discard、btrfsのcommit・scrub・balance、dm-integrityのjournalとbitmap、LUKS2のheaderとkeyslot。optionを選ぶときは、[file systemのoption表](../../../docs/research/storage/README.md) の判断理由と台帳を合わせます。
6. Wi-FiのDHCP lease、SSHの `known_hosts`、shellのhistory、乱数のseed、更新の状態も、書き込み先と時機を台帳で確かめます。

## 3. progressの表示

- 2秒以上かかり得る処理では、開始前に何をするかを表示し、実行中は進み具合（割合、件数、bytesのいずれか）を表示します。
- 中断してよいかどうかを表示します。電源を切ってはいけない間は、そのことをはっきり書きます。
- 終わったら、成功か失敗かと、次に何をするかを表示します。失敗の表示を、成功と区別できる形にします。
- 割合を出せない処理（mkfsなど）は、経過時間と、止まっていないことが分かる表示を出します。
- 表示先は、対話型ツールの画面とconsoleです。LCDでの見え方は、実機で確かめるまで未確認として扱います。

## 4. 画面の文言

- 利用者向けの文言は、英語と日本語を併記します。どちらかが欠けた文言は、testで失敗にします（対話型ツールを実装するときに加えます）。
- 日本語の文字は、consoleのfontで表示できる範囲に収めます。かなに限る案と、使うfontは計画の段階です。
- 文書とマニュアルは日本語だけです（AGENTS.md §2）。

## 5. 確かめ方

1. 静的な確認：変更したscriptとtoolについて、書き込み先、呼ばれる時機、progressの有無を、台帳の該当する行と照らし合わせます。
2. QEMUでの確認：blockへの書き込みを時刻付きで記録し、idleの状態で一定時間待って、台帳にない書き込みが0件であることを確かめます。この試験はまだありません。加えるときは「experiment-record」スキルに従います。
3. 実機での確認：`/sys/block/mmcblk0/stat` の前後の差分を測ります。SDの中のFTLが行う書き込みは見えないので、未確認として扱います。
4. QEMUで書き込みが0件だったことを、実機のSDで書き込みがないことと扱いません。

## 6. 台帳の更新

- 書き込みを足す・消す・時機を変える変更では、同じPRで台帳を更新します。
- 規則に合わない現行の箇所は「未対応」と書き、直すPRで状態を変えます。
- 台帳の根拠には、リポジトリ内のファイルと公開URLを書きます。推測と未確認は、そのように書きます。
