ARG ACTIONLINT_VERSION=1.7.12
ARG DEBIAN_SNAPSHOT=20261019T190000Z
ARG QEMU_VERSION=11.1.2
ARG QEMU_SHA256=731b5681e4bb18be313231579b8efd0296c5b015fa36dc533874b639ba838016
ARG QEMU_SIGNING_FINGERPRINT=CEACC9E15534EBABB82D3FA03353C9CEF108B584

FROM golang:1.27.2-trixie@sha256:47667934874913a449b96faa7ef4777fa285d9ec29126ee80ed61c45b7cccf0e AS actionlint
ARG ACTIONLINT_VERSION
ENV CGO_ENABLED=0 GOTOOLCHAIN=local GOFLAGS=-trimpath
RUN go install -ldflags='-s -w' github.com/rhysd/actionlint/cmd/actionlint@v${ACTIONLINT_VERSION}

FROM debian:trixie-slim@sha256:a29215f6a35e51e22adffa17f89e9d2ef06214e64a2bad10d765c46aea49f11f AS qemu
ARG DEBIAN_SNAPSHOT
ARG QEMU_VERSION
ARG QEMU_SHA256
ARG QEMU_SIGNING_FINGERPRINT
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN apt-get -o Acquire::Retries=5 update \
    && apt-get -o Acquire::Retries=5 install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY docker/debian.sources /tmp/debian.sources
COPY docker/qemu-signing-key.asc /tmp/qemu-signing-key.asc
COPY docker/qemu-patches/*.patch /tmp/qemu-patches/
RUN rm -f /etc/apt/sources.list /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources \
    && sed "s/@DEBIAN_SNAPSHOT@/${DEBIAN_SNAPSHOT}/g" /tmp/debian.sources \
        > /etc/apt/sources.list.d/debian.sources \
    && apt-get -o Acquire::Retries=5 update \
    && apt-get -o Acquire::Retries=5 install -y --no-install-recommends \
        build-essential \
        curl \
        gnupg \
        gpgv \
        libfdt-dev \
        libglib2.0-dev \
        libpixman-1-dev \
        libslirp-dev \
        libzstd-dev \
        meson \
        ninja-build \
        patch \
        pkg-config \
        python3 \
        python3-venv \
        xz-utils \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/* /tmp/debian.sources

WORKDIR /tmp/qemu
RUN set -euxo pipefail \
    && curl --proto '=https' --fail --location --retry 8 --retry-delay 20 --retry-max-time 600 \
        --retry-all-errors "https://download.qemu.org/qemu-${QEMU_VERSION}.tar.xz" \
        -o qemu.tar.xz \
    && curl --proto '=https' --fail --location --retry 8 --retry-delay 20 --retry-max-time 600 \
        --retry-all-errors "https://download.qemu.org/qemu-${QEMU_VERSION}.tar.xz.sig" \
        -o qemu.tar.xz.sig \
    && printf '%s  %s\n' "${QEMU_SHA256}" qemu.tar.xz | sha256sum -c - \
    && mkdir -m 0700 /tmp/qemu-gnupg \
    && export GNUPGHOME=/tmp/qemu-gnupg \
    && gpg --batch --import /tmp/qemu-signing-key.asc \
    && actual_fingerprint="$(gpg --batch --list-keys --with-colons "${QEMU_SIGNING_FINGERPRINT}" | awk -F: '$1 == "fpr" { print $10; exit }')" \
    && test "${actual_fingerprint}" = "${QEMU_SIGNING_FINGERPRINT}" \
    && gpg --batch --export "${QEMU_SIGNING_FINGERPRINT}" > qemu-signing-keyring.gpg \
    && if ! gpgv --status-fd=1 --keyring=/tmp/qemu/qemu-signing-keyring.gpg \
        qemu.tar.xz.sig qemu.tar.xz >gpgv.status 2>gpgv.log; then \
        cat gpgv.log gpgv.status >&2; \
        exit 1; \
    fi \
    && cat gpgv.status \
    && grep -Fq "[GNUPG:] VALIDSIG ${QEMU_SIGNING_FINGERPRINT} " gpgv.status \
    && tar -xJf qemu.tar.xz --strip-components=1 \
    && for patch_file in /tmp/qemu-patches/*.patch; do \
        patch -p1 --forward --batch < "${patch_file}"; \
    done \
    && ./configure \
        --prefix=/opt/qemu \
        --target-list=aarch64-softmmu \
        --enable-plugins \
        --enable-tools \
        --enable-slirp \
        --enable-fdt=system \
        --disable-docs \
        --disable-user \
        --disable-gtk \
        --disable-sdl \
        --disable-vnc \
    && make -j"$(nproc)" \
    && make install \
    && install -d /opt/qemu/lib/qemu-plugins \
    && for plugin_dir in build/contrib/plugins build/tests/tcg/plugins; do \
        if [[ -d "${plugin_dir}" ]]; then \
            find "${plugin_dir}" -maxdepth 1 -type f -name '*.so' \
                -exec install -m 0755 '{}' /opt/qemu/lib/qemu-plugins/ \;; \
        fi; \
    done \
    && find /opt/qemu/bin -maxdepth 1 -type f -executable -exec strip --strip-unneeded '{}' + \
    && find /opt/qemu/lib/qemu-plugins -maxdepth 1 -type f -name '*.so' \
        -exec strip --strip-unneeded '{}' + \
    && version_output="$(/opt/qemu/bin/qemu-system-aarch64 --version)" \
    && grep -Fq "QEMU emulator version ${QEMU_VERSION}" <<< "${version_output}" \
    && machine_help="$(/opt/qemu/bin/qemu-system-aarch64 -machine help)" \
    && grep -Eq '(^|[[:space:]])raspi3ap([[:space:]]|$)' <<< "${machine_help}" \
    && grep -Eq '(^|[[:space:]])raspi3b([[:space:]]|$)' <<< "${machine_help}" \
    && { test -s /opt/qemu/lib/qemu-plugins/libinsn.so \
        || test -s /opt/qemu/lib/qemu-plugins/libhotblocks.so; } \
    && /opt/qemu/bin/qemu-img create -f raw /tmp/qemu-smoke.raw 1M \
    && /opt/qemu/bin/qemu-img info /tmp/qemu-smoke.raw >/dev/null

FROM debian:trixie-slim@sha256:a29215f6a35e51e22adffa17f89e9d2ef06214e64a2bad10d765c46aea49f11f AS msd-dev
ARG ACTIONLINT_VERSION

ARG DEBIAN_SNAPSHOT=20261019T190000Z
ARG SHELLCHECK_VERSION=0.11.0
ARG SHELLCHECK_SHA256=8c3be12b05d5c177a04c29e3c78ce89ac86f1595681cab149b65b97c4e227198
ARG SHELLCHECK_ARM64_SHA256=12b331c1d2db6b9eb13cfca64306b1b157a86eb69db83023e261eaa7e7c14588

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

COPY --from=actionlint /go/bin/actionlint /usr/local/bin/actionlint
COPY --from=qemu /opt/qemu /opt/qemu

LABEL org.opencontainers.image.source="https://github.com/uist1idrju3i/MSD-Linux" \
      org.opencontainers.image.description="MSD/Linux development tools and test environment" \
      org.opencontainers.image.licenses="GPL-2.0-or-later"

# Bootstrap CA roots from the default deb.debian.org source before using HTTPS snapshots.
RUN apt-get -o Acquire::Retries=5 update \
    && apt-get -o Acquire::Retries=5 install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY docker/debian.sources /tmp/debian.sources
RUN rm -f /etc/apt/sources.list /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources \
    && sed "s/@DEBIAN_SNAPSHOT@/${DEBIAN_SNAPSHOT}/g" /tmp/debian.sources \
        > /etc/apt/sources.list.d/debian.sources \
    && apt-get -o Acquire::Retries=5 update \
    && apt-get -o Acquire::Retries=5 install -y --no-install-recommends \
        bc \
        binutils \
        bison \
        bzip2 \
        build-essential \
        bash \
        ca-certificates \
        cmake \
        cpio \
        curl \
        debianutils \
        device-tree-compiler \
        diffutils \
        dosfstools \
        e2fsprogs \
        fdisk \
        file \
        findutils \
        flex \
        g++ \
        gawk \
        gcc \
        git \
        gzip \
        libelf-dev \
        libncurses-dev \
        libssl-dev \
        make \
        mtools \
        openssl \
        patch \
        perl \
        python3 \
        python3-venv \
        rsync \
        sed \
        squashfs-tools \
        tar \
        unzip \
        wget \
        xz-utils \
    && apt-get -o Acquire::Retries=5 install -y --no-install-recommends \
        libfdt1 \
        libglib2.0-0t64 \
        libpixman-1-0 \
        libslirp0 \
        libzstd1 \
        zlib1g \
    && rm -rf /var/lib/apt/lists/* /tmp/debian.sources

ARG TARGETARCH
# The legacy builder leaves TARGETARCH empty.
RUN target_arch="${TARGETARCH:-$(dpkg --print-architecture)}" \
    && case "${target_arch}" in \
        amd64) \
            SHELLCHECK_ARCH=x86_64; \
            SHELLCHECK_EXPECTED_SHA256="${SHELLCHECK_SHA256}"; \
            ;; \
        arm64) \
            SHELLCHECK_ARCH=aarch64; \
            SHELLCHECK_EXPECTED_SHA256="${SHELLCHECK_ARM64_SHA256}"; \
            ;; \
        *) \
            printf 'Unsupported target architecture: %s\n' "${target_arch}" >&2; \
            exit 1; \
            ;; \
    esac \
    && curl --fail --location --retry 8 --retry-delay 20 --retry-max-time 600 \
        --retry-all-errors \
        "https://github.com/koalaman/shellcheck/releases/download/v${SHELLCHECK_VERSION}/shellcheck-v${SHELLCHECK_VERSION}.linux.${SHELLCHECK_ARCH}.tar.xz" \
        -o /tmp/shellcheck.tar.xz \
    && printf '%s  %s\n' "${SHELLCHECK_EXPECTED_SHA256}" /tmp/shellcheck.tar.xz \
        | sha256sum -c - \
    && tar -xJf /tmp/shellcheck.tar.xz -C /tmp --strip-components=1 \
        "shellcheck-v${SHELLCHECK_VERSION}/shellcheck" \
    && install -m 0755 /tmp/shellcheck /usr/local/bin/shellcheck \
    && rm -f /tmp/shellcheck.tar.xz /tmp/shellcheck

COPY .github/zizmor-requirements.txt /tmp/zizmor-requirements.txt
RUN python3 -m venv /opt/zizmor \
    && /opt/zizmor/bin/pip install --require-hashes -r /tmp/zizmor-requirements.txt \
    && ln -s /opt/zizmor/bin/zizmor /usr/local/bin/zizmor \
    && rm -rf /opt/zizmor/bin/pip* /opt/zizmor/lib/python3.*/site-packages/pip* \
    && rm -f /tmp/zizmor-requirements.txt

RUN printf '\nUMASK 027\n' >> /etc/login.defs \
    && ln -s /opt/qemu/bin/qemu-system-aarch64 /usr/local/bin/qemu-system-aarch64 \
    && ln -s /opt/qemu/bin/qemu-img /usr/local/bin/qemu-img \
    && groupadd --gid 1000 builder \
    && useradd --uid 1000 --gid 1000 --create-home --home-dir /home/builder \
        --shell /bin/bash builder

WORKDIR /work
USER builder

RUN qemu-system-aarch64 --version \
    && qemu-img --version \
    && actionlint -version \
    && shellcheck --version \
    && zizmor --version \
    && make --version | head -1 \
    && gcc --version | head -1 \
    && python3 --version
