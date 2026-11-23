#!/usr/bin/env python3
"""Generate the complete Buildroot surface table from pinned sources."""

import argparse
import csv
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[5]
CHANGES = {
    "CMP": ("cmp", "CMP/CRMF", "RAUCはCMS/X.509を使いCMPを呼ばない。curlのTLS backendにもCMP APIなし"),
    "QUIC": ("quic", "OpenSSL QUIC", "契約はHTTPSのTCP TLS。RAUCはHTTP/3を指定せずngtcp2/nghttp3も選ばない"),
    "SSL_TRACE": ("ssl-trace", "SSL_traceとCLIの-trace", "配送script・RAUC・curlにSSL_trace呼出しなし。診断用-traceを失うことは明記"),
    "COMP": ("comp", "SSL/TLS・証明書compression", "curlのSSL_OP_NO_COMPRESSIONはrecord圧縮だけを禁じる。TLS 1.3証明書圧縮は暗黙利用があり未利用を証明できない"),
}


def collect(kconfig, configuration, recipe):
    blocks = re.split(r"(?m)^config ", kconfig)[1:]
    if not blocks:
        raise ValueError("no Buildroot symbols")
    values = {}
    for line in configuration.splitlines():
        if line.startswith("BR2_") and "=" in line:
            name, value = line.split("=", 1)
            values[name] = value
        match = re.fullmatch(r"# (BR2_\w+) is not set", line)
        if match:
            values[match[1]] = "n"
    rows = []
    for block in blocks:
        name = block.splitlines()[0]
        match = re.search(r'^\s+(?:bool|string) "([^"]+)"', block, re.M)
        if name not in values and match:
            raise ValueError("symbol missing in normalized configuration: " + name)
        value = values.get(name, "not-recorded（内部symbolが依存条件により未出力）")
        meaning = match[1] if match else "platform内部の選択"
        default = "; ".join(re.findall(r"^\s+default (.+)$", block, re.M)) or "n（既定指定なし）"
        key = name.removeprefix("BR2_PACKAGE_LIBOPENSSL_ENABLE_")
        flag = re.search(r"\$\(if \$\(" + re.escape(name) + r"\),,([^)]*)\)", recipe)
        reason = "既存algorithm・protocol・診断設定を維持。今回の4機能以外を変更しない"
        if name.endswith("_ARGON2"):
            reason = "cryptsetupのOpenSSL 3 backendがEVP_KDF_fetchでArgon2を利用"
        elif name.endswith("_ECX"):
            reason = "msd-updateのEd25519を維持。X25519/EdDSAを除かない"
        elif name.endswith("_BIN"):
            reason = "msd-updateがopenssl pkeyutlを実行するためCLIを保持"
        elif name.endswith(("_MODULE", "_DYNAMIC_ENGINE", "_LOADER_ENGINE", "_PADLOCK_ENGINE", "_ENGINES")):
            reason = "provider/ENGINE設定を維持。上流既定とcascadeによる無効をyと混同しない。RAUCの将来selectも別途確認"
        elif name.endswith(("_CACHED_FETCH", "_THREAD_POOL", "_SM2_PRECOMP_TABLE", "_SECURE_MEMORY")):
            reason = "性能・保護設定を容量目的で変更しない"
        elif "TARGET_ARCH" in name:
            reason = "既存linux-aarch64とasmを維持。PPC用の内部選択は本機の削減候補にしない"
        row = dict(symbol=name, meaning=meaning, default=default, baseline=value, candidate=value,
                   configure_flag=flag[1].strip() if flag else "platform選択またはtarget install処理",
                   decision="維持", reason=reason, available_3_5_9="yes",
                   source="package/libopenssl/Config.in; package/libopenssl/libopenssl.mk")
        if key in CHANGES:
            token, meaning, reason = CHANGES[key]
            row.update(meaning=meaning, candidate="n", configure_flag="no-" + token,
                       decision="比較のみ・4項目組は採用見送り", reason=reason)
        rows.append(row)
    if len({row["symbol"] for row in rows}) != len(rows):
        raise ValueError("duplicate Buildroot symbols")
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--configuration", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    package = ROOT / "vendor/buildroot/package/libopenssl"
    rows = collect((package / "Config.in").read_text(), args.configuration.read_text(),
                   (package / "libopenssl.mk").read_text())
    with args.out.open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"Buildroot symbol coverage: {len(rows)}; missing=0")
