#!/usr/bin/env python3
import json
import re
import sys
import urllib.request
from pathlib import Path


def main() -> None:
    path = Path(sys.argv[1])
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
    if len(cpe_parts) != 13:
        raise SystemExit(f"Unexpected kernel CPE: {cpe}")
    cpe_parts[5] = version
    kernel["cpe"] = ":".join(cpe_parts)
    path.write_text(json.dumps(sbom, indent=2) + "\n")
    print(f"Set the Linux component version and CPE version to {version}")


if __name__ == "__main__":
    main()
