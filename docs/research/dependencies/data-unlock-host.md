# data-unlockのhost試験用header

[helperの契約](../../design/data-unlock-helper.md) / [開発依存の監査](development-and-ci.md)

## 対象と選択

2026-11-26のPR Bでは、開発imageの最終stageへ`libcryptsetup-dev`を追加する。既存の`cryptsetup`・`libcryptsetup12`と同じDebian snapshotから導入し、hostのlibraryとheaderをそろえる。snapshot、base digest、製品用cryptsetup 2.8.9は変更しない。製品へhostのheaderを転用する変更ではない。

| 候補 | 採否と理由 |
|---|---|
| 同じsnapshotの`libcryptsetup-dev` | 採用。通常のpackage依存解決でheaderとlibraryの版をそろえ、CIで実library試験を必須にできる |
| target stagingのheaderをhostへ指定 | 通常のCIには不採用。従来の局所試験には使ったが、host libraryとの版が異なる。指定用の試験環境変数は残す |
| host向けcryptsetupを別途source build | 不採用。今回必要なのは既存host libraryのheaderであり、別の固定版とbuild設定を増やさない |
| fake backendだけで検査 | 不採用。実LUKS2のslot操作・永続化を確認できない |

## 変更履歴・設定・license・監視

既存host libraryの新版への更新ではないため、旧版と新版の間の変更履歴はない。今回の追加は開発用headerとlink情報であり、upstreamの新機能・新option・既定値変更やcipher変更を採用するものではない。source buildのconfigure optionも変更しない。Debianのpackage依存が要求する追加開発packageは、製品rootfsには入らない。

根拠は[固定snapshotの設定](../../../docker/debian.sources)、[Dockerfile](../../../docker/msd-dev.Dockerfile)、[Debianのcryptsetup source](https://sources.debian.org/src/cryptsetup/)、[upstreamの公開API](https://gitlab.com/cryptsetup/cryptsetup/-/blob/v2.7.5/lib/libcryptsetup.h)である。licenseの確認元は同版Debian packageの`/usr/share/doc/libcryptsetup-dev/copyright`と`libcryptsetup12/copyright`。helperのGPL-2.0-onlyの宣言は変えない。

新しい版の固定値は増やさない。Debian snapshotとbase digestの既存の固定値検査、開発OCIの両archのSBOM・脆弱性監視を継続する。当時の[APT一覧](development-apt.csv)は過去の記録であり、この追加に合わせて書き換えない。

## 回帰試験と確認の境界

`tests/msd-dev/run.sh`でDockerfileへの導入指定を検査し、`tests/check-ci-scope/run.py`でhost runnerの必須化を検査する。`tests/msd-data-unlock/requirements.py`はheaderを見つけられない条件を作り、必須modeでskipせず失敗することを確かめる。実header試験は通常fileを使い、device-mapperのactivateを行わない。

製品側の依存・toolchain・kernel・image定義は変わらない。開発imageのbuild、host test、CIの結果を確認する。Buildrootの成果物サイズ、kernel config、legal-info、CVE件数、QEMU boot時間をこのheader追加の前後比較として測る試験ではない。実LCD・キーボード・SD・電断も未確認である。
