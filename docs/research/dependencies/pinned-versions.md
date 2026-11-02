# 固定値チェッカーの取得結果

2026-11-02 UTCの取得結果。kernel-hardening-checkerのRelease取得失敗は最新版と扱わない。タグによる追加照合と各行の意味は[開発環境・CIの監査](development-and-ci.md)を参照する。

| 依存 | 固定値 | 最新 | 状態(最新・更新あり・確認できず・参考・Buildroot 安定版待ち) | 参照URL |
|---|---|---|---|---|
| Raspberry Pi Linux | `b3495ea401d709af0701a85babcba5e3d788a602` | `b3495ea401d709af0701a85babcba5e3d788a602` | 最新 | https://github.com/raspberrypi/linux |
| Raspberry Pi Linux series | `rpi-6.18.y` | `rpi-7.3.y` | 参考 | https://github.com/raspberrypi/linux/branches |
| Buildroot | `2026.08.x` | `2026.08.x` | 最新 | https://gitlab.com/buildroot.org/buildroot/-/branches |
| Buildroot LTS | `2026.08.x` | `2026.02.x` | 参考 | https://gitlab.com/buildroot.org/buildroot/-/branches |
| Bootlin toolchain (aarch64 glibc stable) | `2025.08-1` | `2026.08-1（安定版の Buildroot では未提供）` | Buildroot 安定版待ち | https://toolchains.bootlin.com/releases_aarch64.html |
| Buildroot point release | `8b238854d909c9cce32ef9671d968b03e323b55d` | `2026.08.1` | 参考 | https://gitlab.com/buildroot.org/buildroot/-/tags |
| actionlint | `1.7.12` | `v1.7.12` | 最新 | https://github.com/rhysd/actionlint/releases |
| ShellCheck | `0.11.0` | `v0.11.0` | 最新 | https://github.com/koalaman/shellcheck/releases |
| hadolint | `2.15.1` | `v2.15.1` | 最新 | https://github.com/hadolint/hadolint/releases |
| kernel-hardening-checker | `v0.6.17.1 (afc376f2a935994793343cfeb05953583cc30191)` | `確認できず` | 確認できず | https://github.com/a13xp0p0v/kernel-hardening-checker/releases |
| QEMU | `11.1.2` | `11.1.3` | 更新あり | https://download.qemu.org/ |
| Debian snapshot date | `20261019T190000Z` | `-` | 最新 | https://snapshot.debian.org/ |
| Trivy | `0.76.1` | `v0.76.1` | 最新 | https://github.com/aquasecurity/trivy/releases |
| Go toolchain | `1.27.3` | `1.27.3` | 最新 | https://go.dev/dl/ |
| Go builder image digest | `sha256:c65ecfe613b539ac74c62a4c3b2c27e8f8a6076384c8f27e8a3c0f3be17cc385` | `sha256:c65ecfe613b539ac74c62a4c3b2c27e8f8a6076384c8f27e8a3c0f3be17cc385` | 最新 | https://hub.docker.com/_/golang?tab=tags&name=1.27.3-trixie |
| Debian base image digest | `sha256:f6b08b09a05725f9431502d3b5714f5c4576e82c1a84fa1debe0c24a7e0c3ec4` | `sha256:f6b08b09a05725f9431502d3b5714f5c4576e82c1a84fa1debe0c24a7e0c3ec4` | 最新 | https://hub.docker.com/_/debian?tab=tags&name=trixie-slim |
| GitHub-hosted runner | `ubuntu-26.04` | `最新: ubuntu-26.04; 固定値: 掲載あり; labels: ubuntu-26.04, ubuntu-26.04-arm, ubuntu-24.04, ubuntu-24.04-arm, ubuntu-22.04, ubuntu-22.04-arm` | 最新 | https://github.com/actions/runner-images |

[依存監査へ戻る](README.md)
