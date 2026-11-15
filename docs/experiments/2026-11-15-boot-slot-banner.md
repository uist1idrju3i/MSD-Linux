# 起動slot表示の検証

[実験一覧](README.md) / [03914の判断](../research/verification/session-decisions-2026-11-15.md#03914の判断と最終slot表示) / [画面・書込み方針](../design/write-policy.md#ramに置いているもの)

## 対象・条件・判定

2026-11-15、main `c024b75acecee989ec8217e0648f454b4097b2f3`を基点に`S98msd-ready`へ表示を追加しました。`msd-update status`のDT判定を優先し、失敗時だけcmdlineのroot p5/p6をA/Bへ対応させます。未知は`?`、DTで試し起動を確認できた場合だけ` (try)`を付けます。別init scriptは追加せず、`/etc/issue`は変更しません。

合格条件は、serialの`MSD/Linux ready`直前に正しいslot行が1行あることです。host fixtureでは、正常DT A/Bとtry、cmdline fallback、空・不正入力、未知、tty1欠落、sweep時のkmsg経路、stopを検査します。QEMUでは最終版のA/BとAのsweepを各1回、既存のboot testと追加のserial照合で確認します。性能測定ではなく、QEMUでfirmware trybootやLCD表示を確認したとは扱いません。

standalone cloneで開発OCIの`docker/msd-dev`を使います。既存の`output-integrity`を独立した写しへコピーしてbuildを継続し、defconfigを再適用します。clean buildの所要時間比較ではありません。作業中の元outputや旧rawは変更しません。

## 再現手順

通常のstandalone cloneでsubmoduleを初期化した後に実行します。

```sh
python3 tests/msd-ready/run.py
tests/msd-update/run.sh
docker/msd-dev make -C vendor/buildroot BR2_EXTERNAL=/work O=/work/output-integrity msd_cardputerzero_defconfig
docker/msd-dev make -C output-integrity
OUTPUT_DIR="$PWD/output-integrity" QEMU_LOG_DIR="$PWD/results-slot" docker/msd-dev board/cardputerzero/qemu/test-boot.sh
OUTPUT_DIR="$PWD/output-integrity" QEMU_LOG_DIR="$PWD/results-slot" docker/msd-dev board/cardputerzero/qemu/test-ab.sh
OUTPUT_DIR="$PWD/output-integrity" QEMU_LOG_DIR="$PWD/results-slot-sweep" QEMU_EXTRA_APPEND=msd.sweep=1 docker/msd-dev board/cardputerzero/qemu/test-boot.sh
python3 - <<'PY'
from pathlib import Path
import re
for directory, partition, slot in [("results-slot", 5, "A"), ("results-slot", 6, "B"), ("results-slot-sweep", 5, "A")]:
    raw = Path(f"{directory}/serial-mmcblk0p{partition}.log").read_text().splitlines()
    lines = [re.sub(r"^\[\s*[0-9.]+\]\s*", "", line) for line in raw]
    banner = f"Boot from slot {slot}"
    assert lines.count(banner) == 1
    assert lines[lines.index(banner) + 1] == "MSD/Linux ready"
    print(f"ok - root p{partition}: {banner}, immediately before ready")
PY
```

## 結果・限界

host fixtureは8 tests成功、既存msd-update host testsも成功しました。standalone cloneのDocker内でtracked ShellCheckとbuildが終了値0となり、QEMUで次を確認しました。

| 条件 | 観測 |
|---|---|
| 最終版A、root p5、1回 | ready/login到達26秒、`Boot from slot A`が1回だけready直前に出現 |
| 最終版B、root p6、1回 | ready/login到達26秒、`Boot from slot B`が1回だけready直前に出現 |
| 最終版A、sweep、1回 | ready/login到達26秒、kernel時刻を除いたslot Aとreadyの順序・1回の出現を照合 |
| OCI / QEMU | image ID `sha256:47cc0b8cfd878a4fb413c376d52a2b6a9199454c97b1d2aec8df7a3a1b4a8e7d` / 11.1.2 |
| Buildroot | `75f325ad84251ee9d903467f84d3683e3bcf3fd5`。cached outputへdefconfigを再適用して不足packageをbuild |
| 試験imageの版表示 | `c024b75-dirty`。基点commitに表示変更を重ねた写しであり、最終文書commitをbuildしたと偽らない |

初回版でも通常A/Bは33/34秒で成功しました。その後の差分確認で、kmsgへは行ごとに別のprintfで書く形へ改修し、最終版を再buildして上記3条件を並列実行しました。1回のwriteへ複数のpriority prefixを混ぜず、既存readyのkmsg経路を保つためです。初回版のsource・serial・hashも消さず、archive内の`initial-evidence.tar.gz`へ残しました。

最終表示scriptのSHA-256は`61dc3afc4930ef16c520fa6ca2f23537cdbb49cc64a1fc343739c280a7000a22`で、変更元・build target・生成SquashFSから抽出した内容が一致しました。[証拠archive](2026-11-15-boot-slot-banner/evidence.tar.gz)に、入力metadata・config/image hash、変更script・patch、host出力、3条件のserial原本、boot test出力と内部SHA256SUMSを保存しました。archiveのSHA-256は`7241ac507be590ec0c4962c62abcd47ec1acfa0332bcc4899b9593dc3ebcca04`です。image binaryは収録していません。

最初のDocker内ShellCheckはworktreeの`.git`参照先がmount外となって失敗しました。完全な`.git`を持つstandalone cloneへ移して成功しています。buildには依存由来のconfigure/compiler警告と開発署名鍵の警告があり、無警告buildや製品Releaseとは扱いません。

DT fixtureは本物の`msd-update status`を呼びますが、LCDの読める表示や実firmwareのDT内容を保証しません。実機LCDとfirmware trybootは未確認です。追加処理は読取りとconsoleへの表示だけで、新しい永続writeはありません。block I/Oの測定は行っていません。到達秒数は今回の記録であり、並列実行の条件もあるため、性能の改善・悪化を比較する値ではありません。
