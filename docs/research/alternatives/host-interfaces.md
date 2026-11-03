# XML・FFI・翻訳とPython構築部品

[比較の入口](README.md)へ戻る。

## 何を入れ替える比較か

対象は主に構築時の依存です。hostで動くPythonやXML parserを置換しても、端末のruntimeを削減したことにはなりません。小さなlibraryを選ぶ前に、その呼出し元が同じAPIを受け付けるかを調べます。以下は資料と固定Buildrootのrecipeの照合であり、代替構成のbuild・実行は本リポジトリでは試していません。

## XML: Expatとlibxml2

| 比較 | Expat | libxml2 |
|---|---|---|
| 主な役割 | event型のXML parser。呼出し元が状態やtreeを管理する | XML toolkit。tree、reader、XPath、schema等も扱う |
| 確認した版の意味 | GitHubの公開releaseは`R_2_10_0` | 取得した開発HEADの`VERSION`は`2.16.0`。これだけでは公開安定版と認定しない |
| 代表license | `COPYING`のMIT系許諾 | `Copyright`のMIT系許諾。ファイルごとの著作権表記にも注意 |
| 単独置換の制約 | CPython等のExpat APIの利用者を確認する | Expatの同名APIではない。link先だけを変える置換ではない |
| 主な再評価条件 | parserを必要としない構成なら親側で機能を無効化する | XPath・schema等を製品が本当に必要とするときに比較する |

固定Buildrootの`python3.mk`はhost Pythonに`--with-expat=system`を渡します。target側は選択条件により`system`と`none`が分かれ、`Config.in`にもExpatの選択条件があります。したがって、host依存の削除、target Pythonの機能選択、アプリのparser選定は別の変更です。libxml2を導入してExpatも残れば、機能を増やす一方で依存は増えます。

安全性はDOMの有無だけでは順位づけできません。採用する呼出し方で、入力長・深さ・entity展開・外部entity・外部URLへのアクセス・処理時間・allocationを制限し、通常の文書と拒否すべき入力を別々に試験します。検証対象はlibrary名ではなく、指定したoptionとその利用者です。全ての文書をrootの補助処理へ渡す方式は避けます。

参照: [Expatのsource](https://github.com/libexpat/libexpat)、[libxml2の公式資料](https://gnome.pages.gitlab.gnome.org/libxml2/)。libxml2の取得sourceはGNOMEのGitHub mirrorであり、公式入口のGitLab repositoryと区別します。

## FFI: libffiとdyncall

| 候補 | 機能・API | 版とlicenseの確認範囲 | MSD/Linuxでの判断 |
|---|---|---|---|
| libffi | runtimeに決まる引数型・戻り値・calling conventionを扱う。closureも提供する | GitHub公開版`v3.8.0`。取得した`LICENSE`はMIT系 | CPython等の呼出し元を含めた基準。独立して削れるとみなさない |
| dyncall | `DCCallVM`へ引数を積む別API。dyncallback・dynloadは別の役割 | 公式downloadの公開版`1.4`。licenseはISCを基にした許諾文 | 独自の小さなFFI利用者なら実験候補。CPythonのlibffiへ無改変で差し替える候補ではない |
| FFIを使わない設計 | 必要なC APIを静的に呼ぶ、または機能を持たせない | 新たな汎用FFIは不要。ただしwrapperやその依存は残る | 呼出し先を固定できる小さなhelperで検討する。汎用Python機能と同等とは呼ばない |

libffiの[公式入口](https://www.sourceware.org/libffi/)には`3.4.5`の案内が残っていますが、そこから辿れるrepositoryのreleaseは上記のとおりです。入口の更新時刻だけで最新・保守中の版を判定しません。[dyncall](https://dyncall.org/)の対応表も開発先端を対象とするため、公開版の全ABI対応と同一視しません。AArch64というCPU名の一致だけでは、aggregateの値渡し、varargs、callback、alignmentの同等性を保証できません。

libffiの取得したsecurity policyは、呼出し元が型記述・function pointer・buffer長・寿命を正しく与えることを前提にします。未信頼な型記述をFFIへ直結する設計は保護しません。また、closureの実行可能memoryとW^Xの実現方法はplatformによります。AppArmorやseccompを厳格化するときも、実際のallocator、実行可能mapping、callbackの必要性を確認します。FFIという名称だけでW^Xを満たすとは記しません。

## gettext: 構築用toolと翻訳runtimeを分ける

GNU gettextは、message抽出・catalogの検査や生成と、翻訳を参照するruntimeを含む系統です。`gettext-tiny`や翻訳を無効化する案は、全tool・全言語・全formatの等価な代替ではありません。

1. 固定Buildrootの`gettext-tiny.mk`と親packageを調べ、hostで要求される実行ファイル・macro・引数を列挙する。
2. `msgfmt`等が生成するcatalogと、plural・encoding・format検査を、実際の入力で比較する。
3. targetの翻訳を無効にする場合、hostの生成器も不要になるかを別に調べる。`NLS`を無効にしたという一つの条件から両方の削除を推論しない。
4. GNU全体のlicenseを一つにまとめず、利用するtool、runtime、同梱macro、生成物をそれぞれ確認する。

採用判断は、翻訳機能を維持したbuild結果と、削減できるhost依存・保守費用の比較後とします。[GNU gettext](https://www.gnu.org/software/gettext/)の公式入口とarchiveを出典に保存しましたが、配布物全体のlicenseを閉じた監査は別です。

## Python: interpreter・frontend・backend・installer

固定Buildrootの`pkg-python.mk`は、PEP 517系で`python -m build -n -w`を呼びます。`-n`は隔離環境の自動作成を使わず、recipeで用意した依存を利用する指定です。生成したwheelはBuildrootの`pyinstaller.py`を介して配置します。host/targetの環境、sysconfig、compiler、配置先も分かれています。`pip install`で全体を置換すると、network取得、依存解決、hostとtargetの混同という別の責務が入ります。

| 部品と観測版 | 責務 | 代表license・置換条件 |
|---|---|---|
| PyPA build `1.6.1` | PEP 517 frontend。指定backendを呼ぶ | MIT。interpreterやbackendを不要にはしない |
| installer `1.1.0` | wheelの展開・配置とscript生成 | MIT。依存resolverやbuild backendではない |
| pyproject-hooks `1.3.3` | frontendからbackendへのhook呼出し | MIT。backendの実装ではない |
| packaging `26.3` | version・requirement・tag等の共通処理 | Apache-2.0またはBSD-2-Clause。別parserへ変えるなら利用APIの移植が要る |
| setuptools `84.2.1` | backendと既存projectの拡張build等 | MIT系。古い`setup.py`利用者も含めて比較する |
| wheel `0.48.0` | wheel形式を扱うtool | MIT。wheel形式そのものや全backendと同義ではない |
| flit-core `4.2.0` | 小さなPython package向けのbackend | BSD-3-Clause。全C拡張をそのまま構築するbackendではない |
| hatchling `1.33.0` | extensibleなbackend | MIT。Hatch frontendの`hatch-v1.18.2`とは別のpackage・版 |
| uv / uv-build `0.13.6` | uvはfrontend等、uv-buildはbackend | MITまたはApache-2.0。取得したbackend資料ではpure Pythonが対象。C拡張には別backendが要る |
| meson-python `0.22.1` | Mesonを利用するbackend | MIT。Meson側のbuild定義とcross file等を移植する費用がある |
| scikit-build-core `1.1.2` | CMakeを利用するbackend | Apache-2.0。CMake toolchainとtarget Pythonの検出・wheel tagをそろえる |

版はGitHubのrelease応答とPyPIのpackage情報で観測した値です。取得した開発HEADのlicense・設定と、公開wheel/sdistの内容を完全照合した値ではありません。Flit、Hatch、Meson等はmonorepo・frontend・backendの版を混ぜません。`latest`のmanualも開発版を指す場合があり、scikit-build-coreの取得資料は`1.1.2.dev11`と記されています。

PEP 517の共通hookがあることは、どのbackendでも既存projectを無改変でbuildできる意味ではありません。projectの`build-system.requires`、`build-backend`、backend固有設定とbootstrap依存を先に読みます。native拡張では、hostのPythonでbuildを動かすことと、AArch64向けの`.so`を生成することを区別し、header・SOABI・EXT_SUFFIX・sysroot・link先・wheel tagを照合します。上流のx86_64→macOS ARM向け手順を、本機のcross build成功へ読み替えません。

## 保守と再検討の順番

公開版の存在、privateな脆弱性窓口、固定版のbackport、期限付きsupportは別々に確認します。例えばFlitの取得したpolicyは最新の非prereleaseのみをsupport対象としますが、これを他のPyPA projectへ一般化しません。期限が見つからない候補をEOLとも無期限supportとも呼びません。

まず親packageの不要optionを減らす案、次に小さなhelperでのAPI置換、最後に全体の構築方式の移行を比較します。API移植・catalogやwheelの差・license通知・脆弱性監視を含めても効果が残ることを採用条件とします。実際の生成物、内包依存、全license、全ABI、性能の確認は採用前に残ります。

一次資料と取得失敗は[sources.json](sources.json)へ保存します。資料を取得した事実と、配布binaryの検査や実行試験を区別します。
