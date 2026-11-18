# fs-compare-v2第4段Aの軽量smoke

## 目的と事前条件

利用者が承認した第4段Aをv2内に実装した。通常測定と旧版を変えず、851 probeの経路確認を短いworkloadで実行する。正式な性能・durability測定ではない。実機のSD書込み、FTL、電断、LCDは対象外とする。

初回のcode保存時点ではbuild・QEMUは未実施。後続の結果を本記録と[CSV](2026-11-19-fs-compare-v2-stage4.csv)へ追記する。[実装と保存仕様](../../board/cardputerzero/tools/bench/fs-compare-v2/README.md)を参照。

## 固定条件と判定基準

- freshな`OUTPUT_DIR=output-fscmp-v2`を既存の`fs-compare-build.sh`で構築する。製品defconfig・overlay・旧workload・dm-verity/FECは変更しない。download cacheは再利用する。build treeはcold、ccacheの事前状態は不明として記録し、速度比較には使わない。
- `smoke-profile.json`のW1=2 file、W2=2更新、W3=51 record、W4=64 KiB、T4=3秒、quiesce=3連続sample、T7=256 MiBを使う。T5は84352 logical byte。通常profileの値はhostで別途照合する。
- 20 baseの16経路、130 variantの標準経路を保つ。851 probe／1021 phaseが要求され、限定除外だけを認める。各1回なのは機能経路の確認であり、5回反復の性能比較に代用しない。
- QMP終了・回収、全logの最終scan、profile hash、全phase、T2/T3のcutとverify、非画像archiveの全参照読戻し、cleanup完了が必要。未知errorや未完了を成功にしない。
- 代表診断はE1の全replay・cut・T4 control・T5/T7、各filesystem系統のmountとI2/T6。E1/mountのA/Aを2回、T1-negativeとnegative-finalを負対照にする。negative-finalのloss検出は既存driverの必須条件を維持する。
- SD imageと再pack rootfsはhash・sizeのみ保存する。失敗画像も保存しない。log・manifest・source・生成config・展開rootfsは共有objectと参照manifestで保存し、欠損・改変・ENOSPC時にはcleanupしない。

## 再実行

repo rootで次を順に実行する。各stageは既存directoryを上書きせず停止する。最初にhost試験・文書検査を通し、codeをcommit・pushしてからbuildする。

```sh
OUTPUT_DIR="$PWD/output-fscmp-v2" docker/msd-dev python3 board/cardputerzero/tools/bench/fs-compare-v2/stage4.py build --runs-dir /work/fscmp-v2-stage4
OUTPUT_DIR="$PWD/output-fscmp-v2" docker/msd-dev python3 board/cardputerzero/tools/bench/fs-compare-v2/stage4.py representative --runs-dir /work/fscmp-v2-stage4
OUTPUT_DIR="$PWD/output-fscmp-v2" docker/msd-dev python3 board/cardputerzero/tools/bench/fs-compare-v2/stage4.py smoke --runs-dir /work/fscmp-v2-stage4
```

`stage4.py`はcommit、実QEMUのversion・hash、Buildroot commit、OS、command、時刻、df、終了状態を保存する。build後は生成済みconfig、kernel・DTB・rootfs・SD・workloadのhash、compiler情報も保存する。代表診断はcoverage証明にはならず、全smokeの成功前に本測定を開始しない。再開では`preflight.py gate PLAN DIRECTORY --smoke-only`へ同じplan・環境を渡す。

## 結果と限界

実装中のhost試験は初回1件失敗した。workloadのhost fixtureにroot directoryがなく、実guestには存在するmountpointを再現できていなかった。fixtureを修正し、通常full／t1-reducedとsmokeのfile数・byte数、rename、fsync境界を照合した。これは製品やQEMUの失敗ではない。

buildとQEMUの成否、A/A・負対照、初期probeの秒数・使用量、残時間の推定は実行後に追記する。QEMUのblock統計や短いidle窓から実SDの耐久性・無書込みを断定しない。
