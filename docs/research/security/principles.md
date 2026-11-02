# OpenBSDの原則とLinuxでの適用条件

[権限設計の入口](README.md) / [処理と権限](privileges.md) / [出典台帳](sources.json)

## 原則から設計へ落とし込む

[OpenBSDのsecurity方針](https://www.openbsd.org/security.html)は、重要な構成要素を監査して基本的なbugを直すことと、不要なserviceを既定で無効にすることを説明しています。[innovations](https://www.openbsd.org/innovations.html)には特権分離と、raw socket等の必要な資源を保持して特権を放棄する手法が記録されています。MSD/Linuxでは次の設計規則にします。実装済み機能の宣言ではありません。

| 原則 | MSD/Linuxでの具体化 | 単純に置き換えないもの |
|---|---|---|
| 最小特権 | service単位のUID/GIDと必要なfile・device・FD・通信先を列挙する | rootからcapabilityを一つ減らせば十分という考え |
| 特権分離 | 危険なparserと、限定した書き込み・認可を行うhelperを分ける | root daemonが別のroot子processを作るだけの構成 |
| 特権放棄 | 初期化後に不要なUID/GID、補助group、capability、FDを不可逆に捨てる | 一時的なeffective UID変更だけ、または元へ戻せるsaved ID |
| 多層防御 | DAC、LSM、syscall制限、通信policy、署名、更新時のread-backを目的別に組み合わせる | 全てのLSM名を列挙することや、同じ検査の数を増やすこと |
| 安全な既定値 | 未設定なら通信・自動更新を始めない。不要listener・AP・pairing・debug経路を開かない | 制限の読込み失敗をwarningだけで無視する起動 |
| 単純さと監査可能性 | 小さな認可protocol、固定した操作、共通の試験・更新経路にする | binaryサイズ最小を理由にroot shellとhookの責務を増やすこと |

## pledgeとunveilの名前だけを移植しない

[pledge(2)](https://man.openbsd.org/pledge.2)は使うsubsystemを宣言し、後続の呼出しで権限を縮小できます。解除したsubsystemを再び有効にできず、違反の多くはprocess終了になります。exec後の契約には`execpromises`があります。

[unveil(2)](https://man.openbsd.org/unveil.2)はpathに対する読み書き・実行・作成等の可視性を狭め、設定後は追加のunveilをlockすることを推奨しています。directoryと個別fileの扱いに違いがあり、同manualは**execした新しいprogramはunveilなしで開始する**ことも明記しています。任意programから機械的にpathを隠すだけで安全になるとは説明していません。

Linuxのseccomp、Landlock、AppArmorは対象・継承・エラー・利用条件が異なります。Linuxでpledge/unveilと同じ保証が得られたとは呼ばず、必要な操作の成功と、不要な操作の拒否を個別に検証します。

## Linuxの仕組みと残る境界

| 仕組み・一次資料 | 制限するもの | 限界と設計条件 |
|---|---|---|
| [UID/GIDとcapabilities](https://man7.org/linux/man-pages/man7/capabilities.7.html) | fileのDACと、分割された特権操作 | 補助group、real/effective/saved ID、permitted/effective/inheritable/ambient/bounding setを別々に確認する。CAP_SYS_ADMINやCAP_SYS_RAWIOの安易な付与は避ける。block deviceの書き込みを一律にCAP_SYS_RAWIOが必要な操作と扱わず、deviceのDACと保持FDも確認する |
| [no_new_privs](https://docs.kernel.org/6.18/userspace-api/no_new_privs.html) | execによるsetuid/setgid・file capability等の昇格 | 既存のroot権限を捨てず、特権付きのsetuid操作やSCM_RIGHTSによるFD受領も一律には止めない。fork/clone/execへ継承し解除不可。LSMのexec時制限強化にも影響する場合があるため、profile遷移との順序を試験する |
| [seccomp filter](https://docs.kernel.org/6.18/userspace-api/seccomp_filter.html) | syscall番号と直接の引数によるkernel攻撃面の縮小 | BPFはpointerを参照できず、渡されたpath文字列やpacket内容の認可には使えない。architecture確認と対象ABIの試験が必要。単独のsandboxではなく、filterの継承、thread、exec、拒否時の終了も確認する |
| [Landlock](https://docs.kernel.org/6.18/userspace-api/landlock.html) | 非特権process自身のfile操作等の制限。network ruleはABI v4以降のTCP port | IP・domain・UDP・全device ioctlの一般的なfirewallではない。制限前に開いたFDや受領FDの権利を後から一括で取り消すものでもない。扱うaccess rightとABIを実行時に照合する |
| [AppArmor](https://docs.kernel.org/6.18/admin-guide/LSM/apparmor.html) | 読み込んだprofileに従うfile・capability等のアクセス | kernel optionだけではDACを超える制限をしない。profile、attachment・exec遷移、enforce状態、policy reloadとdeny試験が必要。complainは観測用で強制の証拠ではない |
| [LSMの構成](https://docs.kernel.org/6.18/admin-guide/LSM/index.html) | 有効なsecurity moduleと順序 | CONFIG_LSMに名前があっても未compileなら使えない。複数のmajor LSMを無条件に同時運用できるとはしない。起動引数と実行時の一覧を照合する |
| [namespaces](https://man7.org/linux/man-pages/man7/user_namespaces.7.html) | UIDやmount・network等の可視範囲を分ける | kernelを共有する。同じnamespace内の権限、UID mapping、外へ渡すFD、mount propagationを管理する。user namespaceを有効にすること自体を無条件な安全性向上と扱わない |
| [module署名](https://docs.kernel.org/6.18/admin-guide/module-signing.html) | 信頼したkernel鍵で署名されないmoduleのload拒否 | 署名済みmoduleのbug、driverへのioctl、kernel/image自体の交換を防ぐものではない。moduleのhotplugを保ちつつ未署名・別鍵・改変moduleの拒否を確認する |

[setresuid(2)](https://man7.org/linux/man-pages/man2/setresuid.2.html)等を使う場合、特権を持つ間に補助groupとGIDを整理し、real/effective/saved UIDも変え、全ての戻り値を確認します。capabilityの保持・exec時の変化は別の規則があるため、UID変更だけで完了とはしません。multi-thread化前の適用と、権限を再取得できないことの確認が必要です。一般のshell scriptをこの手順の代用品にはしません。

## 継承と失敗を契約にする

Landlockの資料は、古いkernelでも可能な範囲を強制するbest-effort方式を勧めています。一方、固定kernelを配布するMSD/Linuxで必須と決めた制限は、必要なABI・access rightを得られなければ対象serviceを開始しない案です。これは本調査の製品設計提案で、上流の推奨を実装済みの保証に読み替えたものではありません。

AppArmorのexec遷移、no_new_privs、capability drop、seccomp、Landlockには一律に使える万能な適用順序を定めません。対象daemonが自前で特権分離する場合は、その起動契約を壊さないことを先に確認します。必要FDの取得、不要FDのclose、profileへの移行、権限放棄、制限の適用が全て完了してから、非信頼入力を受け付ける設計を基本にします。

systemdの[systemd.exec](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html)にはserviceごとの既存のsandbox設定がありますが、現行BusyBox initへ設定名を足しても機能しません。[init比較](../alternatives/init.md)で、既存の実装を利用する費用と、BusyBoxで同等の要件を満たす実装・保守費用を比較します。initの移行や自作launcherの採用は、この文書では決定していません。
