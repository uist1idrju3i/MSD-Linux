"""Collect read-only configuration evidence; this does not run a product build."""

import argparse
import csv
import json
import re
from pathlib import Path


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(output, name, fields, rows):
    with (output / name).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(fields)
        writer.writerows(rows)


def config_values(path, prefix):
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(rf"({prefix}\w+)=(.*)", line)
        disabled = re.fullmatch(rf"# ({prefix}\w+) is not set", line)
        if match:
            values[match[1]] = match[2]
        elif disabled:
            values[disabled[1]] = "n"
    return values


def collect(args):
    repo, output = args.repository.resolve(), args.output
    output.mkdir(parents=True, exist_ok=True)
    source = repo / "vendor/buildroot"
    info = read_json(args.package_info)
    variables = read_json(args.variables)
    components = read_json(args.sbom)["components"]
    sbom = {record["bom-ref"]: record for record in components}
    if len(sbom) != len(components):
        raise ValueError("duplicate SBOM component reference")
    selected = {name: record for name, record in info.items()
                if not record.get("virtual") and record["type"] in ("host", "target")}
    if set(selected) != set(sbom):
        raise ValueError("show-info and SBOM component populations differ")

    def normalize(value):
        for mapping in args.path_map:
            old, new = mapping.split("=", 1)
            value = value.replace(old, new)
        return value

    recipes, package_variables = [], {}
    for key, record in sorted(selected.items()):
        directory = record["package_dir"]
        if directory.startswith("/work/"):
            path = repo / directory.removeprefix("/work/")
        else:
            path = source / directory
        if not path.is_dir():
            raise ValueError(f"missing recipe directory: {key}")
        prefix = key.upper().replace("-", "_") + "_"
        package_variables[key] = {
            name: {kind: normalize(value) for kind, value in values.items()}
            for name, values in sorted(variables.items()) if name.startswith(prefix)
        }
        recipes.append([
            key, record["type"], record["version"], sbom[key]["version"],
            ";".join(str(p.relative_to(repo)) for p in sorted(path.glob("*.mk"))),
            ";".join(str(p.relative_to(repo)) for p in sorted(path.glob("Config.in*"))),
            len(package_variables[key]),
        ])
    write_csv(output, "packages.csv", ["component", "role", "show_info_version", "sbom_version",
              "recipes", "configuration_definitions", "variable_records"], recipes)
    (output / "package-variables.json").write_text(
        json.dumps(package_variables, indent=2) + "\n", encoding="utf-8")

    config = config_values(args.configuration, "BR2_")
    paths = [source / "Config.in"]
    for directory in ("arch", "boot", "fs", "linux", "package", "system", "toolchain"):
        paths.extend((source / directory).rglob("Config.in*"))
    paths.extend((repo / "package").rglob("Config.in*"))
    definitions = []
    for path in sorted(set(paths)):
        if not path.is_file():
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            match = re.fullmatch(r"\s*(?:menuconfig|config)\s+(BR2_\w+)\s*", line)
            if match:
                symbol = match[1]
                value = config.get(symbol, "not-recorded")
                if re.search(r"PASSWORD|PASSWD|TOKEN|SECRET", symbol):
                    value = "withheld"
                definitions.append([symbol, path.relative_to(repo), number, value])
    write_csv(output, "buildroot-symbols.csv",
              ["symbol", "source", "line", "normalized_value"], definitions)

    gcc = []
    for category in ("common", "warnings", "params", "optimizers", "target"):
        path = args.gcc_help_dir / f"component-sdk-gcc-{category}-Os-a53.txt"
        for line in path.read_text(encoding="utf-8").splitlines():
            match = re.match(r"^  (-\S+)\s+(.*)$", line)
            if match:
                value = normalize(match[2].strip())
                if match[1] == "-o":
                    value = re.sub(r"(?<=\s)/\S+$", "@GCC_OUTPUT@", value)
                gcc.append([category, match[1], value])
    write_csv(output, "gcc-options.csv", ["category", "option", "query_result"], gcc)
    common = {name: {kind: normalize(value) for kind, value in variables[name].items()}
              for name in ("TARGET_CFLAGS", "TARGET_CXXFLAGS", "TARGET_LDFLAGS", "HOST_CFLAGS",
                           "HOST_LDFLAGS", "TOOLCHAIN_WRAPPER_ARGS", "TOOLCHAIN_WRAPPER_OPTS")}
    (output / "common-variables.json").write_text(
        json.dumps(common, indent=2) + "\n", encoding="utf-8")
    kernel = sorted(config_values(args.kernel_config, "CONFIG_").items())
    write_csv(output, "kernel-config.csv", ["symbol", "artifact_value"], kernel)
    options = []
    for record in read_json(args.configure_help_dir / "status.json"):
        name = record["source_directory"]
        if record["returncode"] != 0:
            continue
        text = (args.configure_help_dir / f"{name}.txt").read_text(encoding="utf-8")
        text += "\n" + (args.configure_help_dir / f"{name}.stderr").read_text(encoding="utf-8")
        for number, line in enumerate(text.splitlines(), 1):
            match = re.match(r"^  (-\S+)(?:\s+(.*))?$", line)
            if match:
                options.append([name, number, match[1], (match[2] or "").strip()])
    write_csv(output, "configure-options.csv",
              ["source_directory", "help_line", "option", "first_line_description"], options)
    print(json.dumps({"packages": len(recipes), "buildroot_definitions": len(definitions),
                      "gcc_records": len(gcc), "kernel_symbols": len(kernel),
                      "configure_records": len(options)}, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repository", "output", "package-info", "sbom", "variables", "configuration",
                 "kernel-config", "gcc-help-dir", "configure-help-dir"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--path-map", action="append", default=[], metavar="FROM=TO")
    collect(parser.parse_args())
