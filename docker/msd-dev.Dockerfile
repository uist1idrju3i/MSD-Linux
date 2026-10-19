FROM debian:trixie-slim@sha256:a29215f6a35e51e22adffa17f89e9d2ef06214e64a2bad10d765c46aea49f11f

ARG DEBIAN_SNAPSHOT=20261019T190000Z
ARG QEMU_DEB_VERSION=1:11.0.2+ds-2~bpo13+1
ARG ACTIONLINT_VERSION=1.7.12
ARG ACTIONLINT_SHA256=8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8
ARG ACTIONLINT_ARM64_SHA256=325e971b6ba9bfa504672e29be93c24981eeb1c07576d730e9f7c8805afff0c6
ARG SHELLCHECK_VERSION=0.11.0
ARG SHELLCHECK_SHA256=8c3be12b05d5c177a04c29e3c78ce89ac86f1595681cab149b65b97c4e227198
ARG SHELLCHECK_ARM64_SHA256=12b331c1d2db6b9eb13cfca64306b1b157a86eb69db83023e261eaa7e7c14588

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

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
        -t trixie-backports \
        "qemu-system-arm=${QEMU_DEB_VERSION}" \
        "qemu-utils=${QEMU_DEB_VERSION}" \
    && test "$(dpkg-query -W -f='${Version}' qemu-system-arm)" = "${QEMU_DEB_VERSION}" \
    && test "$(dpkg-query -W -f='${Version}' qemu-utils)" = "${QEMU_DEB_VERSION}" \
    && rm -rf /var/lib/apt/lists/* /tmp/debian.sources

ARG TARGETARCH
RUN case "${TARGETARCH}" in \
        amd64) \
            ACTIONLINT_ARCH=amd64; \
            ACTIONLINT_EXPECTED_SHA256="${ACTIONLINT_SHA256}"; \
            SHELLCHECK_ARCH=x86_64; \
            SHELLCHECK_EXPECTED_SHA256="${SHELLCHECK_SHA256}"; \
            ;; \
        arm64) \
            ACTIONLINT_ARCH=arm64; \
            ACTIONLINT_EXPECTED_SHA256="${ACTIONLINT_ARM64_SHA256}"; \
            SHELLCHECK_ARCH=aarch64; \
            SHELLCHECK_EXPECTED_SHA256="${SHELLCHECK_ARM64_SHA256}"; \
            ;; \
        *) \
            printf 'Unsupported target architecture: %s\n' "${TARGETARCH}" >&2; \
            exit 1; \
            ;; \
    esac \
    && curl --fail --location --retry 8 --retry-delay 20 --retry-max-time 600 \
        --retry-all-errors \
        "https://github.com/rhysd/actionlint/releases/download/v${ACTIONLINT_VERSION}/actionlint_${ACTIONLINT_VERSION}_linux_${ACTIONLINT_ARCH}.tar.gz" \
        -o /tmp/actionlint.tar.gz \
    && printf '%s  %s\n' "${ACTIONLINT_EXPECTED_SHA256}" /tmp/actionlint.tar.gz \
        | sha256sum -c - \
    && tar -xzf /tmp/actionlint.tar.gz -C /tmp actionlint \
    && install -m 0755 /tmp/actionlint /usr/local/bin/actionlint \
    && curl --fail --location --retry 8 --retry-delay 20 --retry-max-time 600 \
        --retry-all-errors \
        "https://github.com/koalaman/shellcheck/releases/download/v${SHELLCHECK_VERSION}/shellcheck-v${SHELLCHECK_VERSION}.linux.${SHELLCHECK_ARCH}.tar.xz" \
        -o /tmp/shellcheck.tar.xz \
    && printf '%s  %s\n' "${SHELLCHECK_EXPECTED_SHA256}" /tmp/shellcheck.tar.xz \
        | sha256sum -c - \
    && tar -xJf /tmp/shellcheck.tar.xz -C /tmp --strip-components=1 \
        "shellcheck-v${SHELLCHECK_VERSION}/shellcheck" \
    && install -m 0755 /tmp/shellcheck /usr/local/bin/shellcheck \
    && rm -f /tmp/actionlint.tar.gz /tmp/actionlint /tmp/shellcheck.tar.xz /tmp/shellcheck

COPY .github/zizmor-requirements.txt /tmp/zizmor-requirements.txt
RUN python3 -m venv /opt/zizmor \
    && /opt/zizmor/bin/pip install --require-hashes -r /tmp/zizmor-requirements.txt \
    && ln -s /opt/zizmor/bin/zizmor /usr/local/bin/zizmor \
    && rm -f /tmp/zizmor-requirements.txt

RUN printf '\nUMASK 027\n' >> /etc/login.defs \
    && groupadd --gid 1000 builder \
    && useradd --uid 1000 --gid 1000 --create-home --home-dir /home/builder \
        --shell /bin/bash builder

WORKDIR /work
USER builder

RUN qemu-system-aarch64 --version \
    && actionlint -version \
    && shellcheck --version \
    && zizmor --version \
    && make --version | head -1 \
    && gcc --version | head -1 \
    && python3 --version
