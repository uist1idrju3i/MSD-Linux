#!/usr/bin/env python3
import argparse
import json
import re
import urllib.request
from pathlib import Path


def validate_components(sbom: dict, show_info: dict, project_version: str, kernel_version: str) -> None:
    if sbom.get("bomFormat") != "CycloneDX":
        raise SystemExit("Expected a CycloneDX SBOM")
    project = sbom.get("metadata", {}).get("component", {})
    if project.get("version") != project_version:
        raise SystemExit("SBOM project version does not match the checkout")
    project_ref = project.get("bom-ref")
    if not project_ref:
        raise SystemExit("The SBOM project has no reference")
    expected = {
        ref: info for ref, info in show_info.items()
        if "rootfs" not in info["type"] and not info["virtual"]
    }
    components = sbom.get("components", [])
    refs = [component.get("bom-ref") for component in components]
    if len(refs) != len(set(refs)) or project_ref in refs:
        raise SystemExit("Duplicate SBOM component reference")
    if set(refs) != set(expected):
        raise SystemExit(
            f"SBOM coverage mismatch: missing={sorted(set(expected) - set(refs))}, "
            f"extra={sorted(set(refs) - set(expected), key=str)}"
        )
    for component in components:
        ref = component["bom-ref"]
        info = expected[ref]
        version = kernel_version if ref == "linux" else info.get("version", "")
        if component.get("name") != info["name"] or component.get("version") != version:
            raise SystemExit(f"SBOM name/version mismatch: {ref}")
        kinds = [prop.get("value") for prop in component.get("properties", [])
                 if prop.get("name") == "BR_TYPE"]
        if kinds != [info["type"]]:
            raise SystemExit(f"SBOM host/target mismatch: {ref}")
    known_refs = set(refs) | {project_ref}
    graph = sbom.get("dependencies", [])
    graph_refs = [edge.get("ref") for edge in graph]
    if len(graph_refs) != len(set(graph_refs)) or set(graph_refs) != known_refs:
        raise SystemExit("SBOM dependency graph coverage mismatch")
    for edge in graph:
        if not set(edge.get("dependsOn", [])).issubset(known_refs):
            raise SystemExit(f"Unknown SBOM dependency reference: {edge['ref']}")
        if edge["ref"] == project_ref:
            continue
        expected_deps = set()
        for dep in expected[edge["ref"]].get("dependencies", []):
            if show_info.get(dep, {}).get("virtual"):
                expected_deps.update(ref for ref, info in show_info.items()
                                     if dep in info.get("provides", []))
            else:
                expected_deps.add(dep)
        if set(edge.get("dependsOn", [])) != expected_deps:
            raise SystemExit(f"SBOM dependency mismatch: {edge['ref']}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("sbom", type=Path)
    parser.add_argument("--kernel-makefile", type=Path)
    parser.add_argument("--show-info", type=Path)
    parser.add_argument("--project-version")
    args = parser.parse_args()
    if bool(args.show_info) != bool(args.project_version):
        parser.error("--show-info and --project-version must be used together")
    if args.project_version and not re.fullmatch(r"[0-9a-f]{40}", args.project_version):
        parser.error("--project-version must be the full checkout commit")
    path = args.sbom
    defconfig = Path("configs/msd_cardputerzero_defconfig").read_text()
    match = re.search(
        r"BR2_LINUX_KERNEL_CUSTOM_TARBALL_LOCATION=.*?"
        r"github,raspberrypi,linux,([0-9a-f]{40})",
        defconfig,
    )
    if not match:
        raise SystemExit("Could not find the pinned Raspberry Pi kernel commit")

    commit = match.group(1)
    url = f"https://raw.githubusercontent.com/raspberrypi/linux/{commit}/Makefile"
    if args.kernel_makefile:
        makefile = args.kernel_makefile.read_text()
    else:
        with urllib.request.urlopen(url, timeout=30) as response:
            makefile = response.read().decode()

    version_parts = []
    for key in ("VERSION", "PATCHLEVEL", "SUBLEVEL"):
        value = re.search(rf"^{key}\s*=\s*(\d+)", makefile, re.MULTILINE)
        if not value:
            raise SystemExit(f"Could not read {key} from the pinned kernel Makefile")
        version_parts.append(value.group(1))
    version = ".".join(version_parts)

    sbom = json.loads(path.read_text())
    kernel_components = [
        component
        for component in sbom.get("components", [])
        if component.get("name", "").lower() in {"linux", "linux-custom"}
        or component.get("purl", "").split("@", 1)[0] == "pkg:generic/linux"
    ]
    if len(kernel_components) != 1:
        raise SystemExit(
            f"Expected one kernel component, found {len(kernel_components)}"
        )

    kernel = kernel_components[0]
    kernel["version"] = version
    cpe = kernel.get("cpe")
    if not isinstance(cpe, str):
        raise SystemExit("The kernel component has no CPE string")
    cpe_parts = cpe.split(":")
    if len(cpe_parts) != 13 or cpe_parts[:5] != ["cpe", "2.3", "o", "linux", "linux_kernel"]:
        raise SystemExit(f"Unexpected kernel CPE: {cpe}")
    cpe_parts[5] = version
    kernel["cpe"] = ":".join(cpe_parts)
    properties = [prop for prop in kernel.get("properties", [])
                  if prop.get("name") != "msd:linux:source-commit"]
    properties.append({"name": "msd:linux:source-commit", "value": commit})
    kernel["properties"] = properties
    if args.show_info:
        validate_components(sbom, json.loads(args.show_info.read_text()), args.project_version, version)
    path.write_text(json.dumps(sbom, indent=2) + "\n")
    print(f"Set the Linux component version and CPE version to {version}")


if __name__ == "__main__":
    main()
