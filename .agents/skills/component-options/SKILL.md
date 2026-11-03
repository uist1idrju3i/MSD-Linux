---
name: component-options
description: 部品の採用・追加・置換や、更新で新しいoptionが加わったときの調査に使います。
---

# component-options（部品の選定とoption調査）

部品（application、library、toolchain、kernel、CI tool）を採用・追加・置換する前に、代替品、build option、実行時の設定項目を調べて採否を決めます。部品の更新で新しいoptionや設定項目、既定値の変更が見つかったときも使います。

## 調査手順

1. **対象と制約を決めます。** 部品の役割、利用環境、固定版、製品の要件を記録します。製品の永続storageへの書き込みやprogress表示などは、`AGENTS.md` §10 と「product-io-policy」スキルに照らします。
2. **代替品を調べます。** 同じ役割の候補を新しいものも含めて挙げ、自前実装も比較します。機能、保守状況、セキュリティ、license、将来計画への適合を比べます。既存の[代替品比較](../../../docs/research/alternatives/README.md)を確認します。
3. **build optionを分けて調べます。** 一次資料の全option（`configure --help`、`meson_options.txt`、Kconfig、CMakeの`option()`など）、Buildroot recipeが公開するoption（`Config.in`、`.mk`の`*_CONF_OPTS`など）、recipeが公開しないoptionを`vendor/`を編集せず渡せるかを別々に記録します。渡せない場合は、その事実と代替手段を書きます。
4. **実行時の設定を調べます。** 設定file、環境変数、command line引数、sysctl、kernel parameterと、その既定値を確認します。build時optionと実行時設定を混同しません。
5. **版の差を記録します。** 固定版と上流の最新版を確認し、optionの追加・廃止、既定値の変更を分けて、版番号と一次資料のURLを記します。
6. **網羅を機械照合します。** 上流のhelp、文書、Kconfigなどからoption tokenを機械的に抽出し、表のoption列と比較してmissing=0にします。抽出物ではないと判断した項目だけを理由付きで除外します。関連するoptionをまとめる場合も、表のoption列に全tokenを列挙します。行数を網羅の証拠にしません。
7. **採否と測定を記録します。** 表にはoption、意味、既定値、固定版で使えるか、最新版での変化、MSD/Linuxでの扱い、理由を記します。理由は製品要件との関係を具体的に説明し、未確認や推測を区別します。容量、RAM、起動時間、CVEと保守状況、licenseなどを比較し、数値測定は「experiment-record」スキルに従います。
8. **置き場所と索引を決めます。** 代替品比較は`docs/research/alternatives/`、option表は`docs/research/component-options/`または主題のdirectoryに置き、索引からたどれるようにします。既存の[component option調査](../../../docs/research/component-options/README.md)を参照します。

## 更新時

「vendor-update」スキルの確認で新しいoption・設定項目や既定値の変更を見つけたら、採否と理由を決め、役立つものは同じ変更で採用します。見送る場合は理由と再確認の条件を残し、新しいoptionを同じPRのcomponent-options表へ反映します。

## Rubyの例

代替品としてCRuby、mruby、mruby/cを比べます。固定BuildrootにはCRuby packageがあり、mrubyとmruby/cのpackageは見つかりません。現在のrecipeは`ruby.mk`でRuby 4.0.5を指定しています（Buildroot submodule commit `8b238854d909c9cce32ef9671d968b03e323b55d`）。`RUBY_CONF_OPTS`はtarget Ruby向けで、`--disable-install-doc`、`--disable-rpath`、`--disable-rubygems`、`--disable-yjit`、`--disable-zjit`を渡します。GMPが有効なら`--with-gmp`とdependencyを加え、無効なら`--without-gmp`を加えます。libffiがない場合は`--with-out-ext=fiddle`も加えます。別の`HOST_RUBY_CONF_OPTS`では`--with-out-ext=curses,readline`と`--without-gmp`を使います。

CRubyの`configure.ac`には`AC_ARG_WITH([jemalloc], ...)`があり、`--with-jemalloc`はjemallocをallocatorとして使うoptionです（既定は無効）。固定版のRuby 4.0.5にも、この定義があります。Buildrootの`ruby.hash`と同じSHA-256のsource tarballで確かめました。Buildrootにはjemalloc packageがあり、このrecipeではversion 5.3.1です。固定した`ruby.mk`の`RUBY_CONF_OPTS`には`--with-jemalloc`がありません。`RUBY_CONFIGURE_OPTS`はruby-buildが認識する環境変数ですが、Buildrootのrecipeでは`RUBY_CONF_OPTS`を使います。recipeにないoptionを`vendor/`を編集せずtarget Rubyへ渡す方法は未確認です。Buildroot側のoverride方法を一次資料と実際のbuildで確かめるまでは、利用可能とは判断しません。

出典: [Ruby v4.0.5のconfigure.ac](https://github.com/ruby/ruby/blob/v4.0.5/configure.ac#L1458-L1460)、[ruby-build README](https://github.com/rbenv/ruby-build/blob/master/README.md#environment-variables)、[固定Buildrootのruby.mk](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/package/ruby/ruby.mk)、[固定Buildrootのjemalloc package](https://github.com/buildroot/buildroot/tree/8b238854d909c9cce32ef9671d968b03e323b55d/package/jemalloc)。

比較時はjemallocとglibc mallocのRAM使用量、image容量、起動時間、ARM64でのYJIT利用可否、`--with-out-ext`による拡張library削減を検討します。実測していない差は推測または未確認と記します。
