# fs-compare v2の監視と判定

旧版の正式実験に使ったscriptを残し、driver・matrix・guest・build入口・設定定義をこのdirectoryへ分離しました。workloadのC sourceだけは一つ上の旧版と共有し、入力hashへ含めます。dm-verity/FECと共通QEMU起動検査器は変更しません。

## 現在の範囲

step 1の監視・判定だけを実装しています。全経路smoke、環境self-check、自動除外、容量見積り、cleanup前の自動archive、既定反復数の変更はまだありません。生成planの回数も旧版のままです。**正式測定にはまだ使いません。** QEMU・実機での試行は行っておらず、この変更の実験記録はありません。

- build: `fs-compare-build.sh`。既定出力は`output-fscmp-v2`です。旧版のBuildroot fragmentを使うtreeは拒否します。
- 単発: `QEMU_LOG_DIR=/永続的な絶対path fs-compare.sh E1 smoke run-id`。既存のrun directoryは上書きしません。
- matrix: `fs-compare-matrix.sh --runs-dir /永続的な絶対path plan.tsv`。旧版と混ぜず、v2で作ったmatrix directoryだけ再開します。

これらの入口は本書と同じdirectoryにあります。`run-qemu.sh`は既存のものを使い、exec後のQEMUをPython supervisorが直接waitします。`FS_COMPARE_V2_DRIVER`はhost試験で偽driverを渡すためのmatrix入口です。通常は指定しません。

## 成功条件

完了markerだけでは成功にしません。QMPのcapabilities交渉とquitが成功し、QEMUを回収して終了値0を確認し、全logに予期しないerrorがなく、driverも終了0の時だけ成功です。TERM/KILL fallback、SIGKILL、非zero、status不明、証拠欠損は失敗です。QMP socketは短い一時pathに置き、停止要求・回収結果はrun directoryへ残します。

T2/T3の最初のphaseだけは例外です。開始markerを確認し、cut意図を保存した後のSIGKILLを予定cutとして扱います。verify phaseのrecovery markerとQMP正常終了は別に必要です。予定外signalやrecovery marker後の異常終了は失敗です。

`summary.pending.csv`は中間値です。回収後に全logを再走査し、`summary.csv`をatomic置換してから、最後に`result.json`をatomic置換します。後者が最終判定の確定印です。matrixはschema・run識別・summary hash・phase結果も検査し、子processが非zeroならsummaryがokでも失敗です。子の終了値も保存し、再開で成功に変わることを防ぎます。これはhostの突然の電源断まで保証するものではありません。

## errorの保存

`host.log`にはdriverの準備・image加工のstdout/stderr、`qemu-run.log`と`qemu-verify.log`には各phaseのQEMU/guest出力を残します。`qemu.log`は回収後の結合logです。`phase-*.json`にはQMP、fallback、終了値、回収の有無、log hashを保存します。

`errors.jsonl`と`errors.txt`にはfile・行番号・phase・分類・原文・expectedの区別を保存します。process statusも記録します。guestのerror、kernel panic/Oops、QEMUのfatal、未知のerrorは成功markerより後でも失敗です。T1 replayとT6 corruptionのguestが明示した区間だけ、列挙したfilesystem診断・測定markerをexpectedとして残します。kernel panic、guestの失敗、SDのI/O errorは除外しません。区間が閉じない時も失敗です。未知の診断は保守的に失敗するため、後続のsmokeで分類の妥当性を確認する必要があります。

## host試験

repo rootで`python3 tests/fs-compare-v2/run.py`を実行します。偽QMP peerと小さいlogだけを使い、QEMUやnetworkは使いません。`run-host-tests.py`にも登録しています。実QEMUとの結合、全workloadの経路、再現性、性能、LCD表示は未確認です。
