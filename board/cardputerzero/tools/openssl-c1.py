#!/usr/bin/env python3
"""Apply the C1 runtime policy while preserving upstream CA and CSR settings."""

import argparse
from pathlib import Path
import re


HEADERS = re.compile(r"(?m)^[ \t]*\[([^\]\n]+)\][ \t]*(?:#.*)?$")


def ensure_section(text, name, settings, required=False):
    headers = list(HEADERS.finditer(text))
    matches = [i for i, header in enumerate(headers) if header[1].strip() == name]
    if len(matches) > 1:
        raise ValueError(f"duplicate OpenSSL section: {name}")
    if not matches:
        if required:
            raise ValueError(f"missing OpenSSL section: {name}")
        return text.rstrip() + f"\n\n[{name}]\n" + "".join(
            f"{key} = {value}\n" for key, value in settings.items())
    index = matches[0]
    header = headers[index]
    end = headers[index + 1].start() if index + 1 < len(headers) else len(text)
    body = text[header.end():end]
    additions = []
    for key, value in settings.items():
        found = re.findall(rf"(?m)^[ \t]*{re.escape(key)}[ \t]*=[ \t]*([^\n]*)$", body)
        if found and (len(found) != 1 or found[0].split("#", 1)[0].strip() != value):
            raise ValueError(f"conflicting OpenSSL setting: {name}.{key}")
        if not found:
            additions.append(f"{key} = {value}")
    if not additions:
        return text
    return text[:header.end()] + "\n" + "\n".join(additions) + text[header.end():]


def configuration(text):
    headers = list(HEADERS.finditer(text))
    global_text = text[:headers[0].start()] if headers else text
    for key, expected in {"openssl_conf": "openssl_init", "config_diagnostics": "1"}.items():
        values = re.findall(rf"(?m)^[ \t]*{key}[ \t]*=[ \t]*([^\n]*)$", global_text)
        if len(values) != 1 or values[0].split("#", 1)[0].strip() != expected:
            raise ValueError(f"unexpected global OpenSSL setting: {key}")
    for name, settings, required in (
        ("openssl_init", {"providers": "provider_sect", "ssl_conf": "msd_tls"}, True),
        ("provider_sect", {"default": "default_sect"}, True),
        ("default_sect", {"activate": "1"}, True),
        ("msd_tls", {"system_default": "msd_tls_defaults"}, False),
        ("msd_tls_defaults", {"MinProtocol": "TLSv1.2", "CipherString": "DEFAULT:@SECLEVEL=2"}, False),
    ):
        text = ensure_section(text, name, settings, required)
    return text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    args = parser.parse_args()
    try:
        original = args.config.read_text()
        updated = configuration(original)
        if updated != original:
            args.config.write_text(updated)
    except (OSError, ValueError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
