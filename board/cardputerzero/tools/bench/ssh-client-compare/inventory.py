#!/usr/bin/env python3
"""Extract the fixed sources' option tokens and retain their primary evidence."""

import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import re
import subprocess

from build import ROOT, VARIANTS, sha
from runtime import parse_config


def configure_tokens(text):
    return re.findall(r"(?<!\S)(--[A-Za-z][A-Za-z0-9_-]*)", text)


def unix_cache_value(relative, cache, token):
    if relative.parent == Path("cmake/platforms") and relative.stem != "unix":
        return "非対象platform（Unix build）"
    return cache.get(token, "非対象platform")


def collect(build, serial):
    rows, sources = {}, {}
    defaults = {}
    if serial:
        text = serial.read_text(errors="replace")
        if "SSH_CONFIG_BEGIN" in text:
            block = text.split("SSH_CONFIG_BEGIN", 1)[1].split("SSH_CONFIG_END", 1)[0]
            defaults = {key: "\n".join(value) if isinstance(value, list) else value
                        for key, value in parse_config(block).items()}

    def add(variant, category, token, path, default="上流資料に明記なし", evidence=""):
        relative = str(path.relative_to(ROOT))
        sources[relative] = sha(path)
        key = (variant, category, token)
        selected = token in {
            "BR2_PACKAGE_OPENSSH", "BR2_PACKAGE_OPENSSH_CLIENT", "BR2_PACKAGE_DROPBEAR",
            "BR2_PACKAGE_PUTTY", "PROGRAMS", "-F", "-T", "-i", "-p",
            "-P", "-o", "-Q", "-hostkey", "-batch", "-noagent", "BatchMode", "StrictHostKeyChecking",
            "UserKnownHostsFile", "UpdateHostKeys", "GlobalKnownHostsFile", "IdentitiesOnly",
        } or (category == "client設定" and token.lower() in {
            "batchmode", "stricthostkeychecking", "userknownhostsfile", "updatehostkeys",
            "globalknownhostsfile", "identitiesonly", "connecttimeout"}) or token.endswith(("_INSTALL_TARGET_CMDS", "_POST_INSTALL_TARGET_HOOKS", "_INSTALL_INIT_SYSV",
                              "_INSTALL_INIT_SYSTEMD", "_MAKE_OPTS", "_PROGRAMS"))
        if category == "CLI":
            selected = token in dict(openssh={"-v", "-F", "-o", "-i", "-p", "-Q", "-V", "-G"},
                                    dropbear={"-T", "-o", "-i", "-p", "-Q", "-V", "-h"},
                                    putty={"-v", "-batch", "-ssh", "-noagent", "-i", "-hostkey", "-P"})[variant]
        rows[key] = dict(variant=variant, category=category, option=token,
                         meaning="一次資料の原文列を参照", upstream_default=default,
                         fixed_version="固定sourceに存在。条件分岐・到達性はsource参照",
                         latest_change="同版を比較。最新版の確認範囲は本文参照",
                         decision="採用（比較条件の明示指定）" if selected else "不採用（明示変更せず）",
                         reason=("clientのみのpayloadと非対話の鍵確認を再現するため" if selected else
                                 "recipeと上流の既定を維持する比較。機能の削除や製品導入の承認ではない"),
                         source=relative, upstream_text=evidence.strip())

    for variant in VARIANTS:
        recipe = ROOT / "vendor/buildroot/package" / variant
        config = recipe / "Config.in"
        for token in re.findall(r"(?m)^config (BR2_\w+)", config.read_text()):
            block = config.read_text().split("config " + token, 1)[1].split("\nconfig ", 1)[0]
            found = re.search(r"(?m)^\s*default (.+)", block)
            add(variant, "Buildroot", token, config, found[1] if found else "Kconfigの暗黙既定", block)
        make = recipe / f"{variant}.mk"
        for match in re.finditer(r"(?m)^(?:define )?(" + variant.upper() + r"_[A-Z0-9_]+)(?:\s*[:+?]?=([^\n]*)|$)", make.read_text()):
            add(variant, "recipe変数", match[1], make, evidence=match[0])
        source = next((build / variant / "buildroot/build").glob(f"{variant}-*"))
        if variant != "putty":
            configure = source / "configure"
            help_text = subprocess.check_output(["/bin/sh", configure, "--help"], text=True)
            for line in help_text.splitlines():
                for token in configure_tokens(line):
                    add(variant, "configure", token, configure, evidence=line)
        else:
            cache = dict(re.findall(r"(?m)^([^/#\n:=]+):[^=]+=(.*)$", (source / "CMakeCache.txt").read_text()))
            for path in [source / "CMakeLists.txt", *sorted((source / "cmake").rglob("*.cmake"))]:
                text = path.read_text()
                cleaned = re.sub(r"(?m)#.*$", "", text)
                for match in re.finditer(r"set\(\s*(\w+)\s+([^()]*?)\s+CACHE (BOOL|STRING|PATH)", cleaned):
                    add(variant, "CMake:" + str(path.relative_to(source)), match[1], path,
                        match[2].strip() + "; build=" + unix_cache_value(path.relative_to(source), cache, match[1]), match[0])
                for match in re.finditer(r"option\(\s*(\w+)\s+([^)]*)\)", text):
                    add(variant, "CMake", match[1], path, evidence=match[0])
        if variant == "openssh":
            path = source / "ssh.c"
            match = re.search(r"getopt\(ac, av, ((?:\s*\"[^\"]*\")+)\)", path.read_text())
            for token in re.sub(r'[\s\":]', '', match[1]):
                add(variant, "CLI", "-" + token, path, "指定なし", match[0])
            path = source / "readconf.c"
            block = path.read_text().split("} keywords[] = {", 1)[1].split("\n};", 1)[0]
            for token, opcode in re.findall(r'\{ "([a-z0-9]+)", (\w+) \}', block):
                add(variant, "client設定", token, path, defaults.get(token, "-G非出力。別名・条件指定・非対応を含む"), opcode)
        elif variant == "dropbear":
            path = source / "src/default_options.h"
            for token, value in re.findall(r"(?m)^#define (\w+)\s*([^\n]*)", path.read_text()):
                add(variant, "compile macro", token, path, value, value)
            path = source / "src/cli-runopts.c"
            for token in re.findall(r"case '(.)':", path.read_text()):
                add(variant, "CLI", "-" + token, path, "指定なし。compile guardに依存")
            for token in re.findall(r'match_extendedopt\(&optstr, "([^"]+)"\)', path.read_text()):
                add(variant, "client設定", token, path, "cli-runopts.cの初期化・分岐を参照")
        else:
            path = source / "cmdline.c"
            for path in (source / "cmdline.c", source / "unix/plink.c"):
                for token in re.findall(r'"(--?[A-Za-z0-9][A-Za-z0-9-]*)"', path.read_text()):
                    add(variant, "CLI", token, path, "指定なし。tool種別の分岐を含む")
            path = source / "doc/plink.1"
            for token in re.findall(r"\\fB(--?[A-Za-z0-9][A-Za-z0-9-]*)", path.read_text().replace(r"\-", "-")):
                add(variant, "CLI", token, path, "指定なし。plink.1を参照")
            path = source / "conf.h"
            for match in re.finditer(r"(?ms)^CONF_OPTION\((\w+),(.*?)(?=^\))", path.read_text()):
                default = re.search(r"DEFAULT_\w+\(([^\n]*)\)", match[2])
                add(variant, "session設定", "CONF_" + match[1], path,
                    default[1] if default else "mappingは空、LOAD_CUSTOMはsettings.cを参照", match[0])
        for path in sorted(source.rglob("*.c")):
            if any(name in path.parts for name in ("test", "tests", "CMakeFiles", "fuzzing")):
                continue
            for token in re.findall(r'getenv\("([A-Za-z_][A-Za-z0-9_]*)"\)', path.read_text(errors="replace")):
                add(variant, "環境変数", token, path, "未設定。各呼出しのfallbackを参照",
                    "source全体からの候補。server・GUI・他OSだけの参照も含む")
    return [rows[key] for key in sorted(rows)], sources


def encode_multiline(value):
    return "json:" + json.dumps(value, ensure_ascii=False) if "\n" in value or "\r" in value else value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--serial", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--check", type=Path)
    args = parser.parse_args()
    rows, sources = collect(args.build.resolve(), args.serial)
    if args.check:
        with args.check.open(newline="") as stream:
            actual = list(csv.DictReader(stream))
        key = lambda row: (row["variant"], row["category"], row["option"])
        expected, observed = set(map(key, rows)), set(map(key, actual))
        missing, extra = expected - observed, observed - expected
        print(f"missing={len(missing)} extra={len(extra)} rows={len(actual)}")
        if missing or extra or len(actual) != len(observed):
            raise SystemExit(1)
    else:
        if not args.out:
            parser.error("--out or --check required")
        args.out.mkdir(parents=True, exist_ok=False)
        with (args.out / "options.csv").open("x", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows({key: encode_multiline(value) for key, value in row.items()} for row in rows)
        metadata = dict(sources=sources, counts=dict(Counter(row["category"] for row in rows)))
        (args.out / "inventory.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps(metadata["counts"], ensure_ascii=False))


if __name__ == "__main__":
    main()
