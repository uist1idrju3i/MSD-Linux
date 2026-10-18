#!/usr/bin/env python3
import collections
import json
import sys


def main() -> None:
    source = sys.stdin if len(sys.argv) == 1 or sys.argv[1] == "-" else open(
        sys.argv[1], encoding="utf-8"
    )
    with source:
        report = json.load(source)

    components = {
        component["bom-ref"]: component.get("name", component["bom-ref"])
        for component in report.get("components", [])
        if component.get("bom-ref")
    }
    exploitable = collections.Counter()
    top_cves = collections.defaultdict(list)
    resolved = collections.Counter()

    for vulnerability in report.get("vulnerabilities", []):
        state = vulnerability.get("analysis", {}).get("state", "")
        refs = [
            affected.get("ref")
            for affected in vulnerability.get("affects", [])
            if affected.get("ref")
        ]
        if state in {"resolved", "resolved_with_pedigree"}:
            resolved[state] += 1
        if state != "exploitable":
            continue
        score = max(
            (
                float(rating["score"])
                for rating in vulnerability.get("ratings", [])
                if rating.get("score") is not None
            ),
            default=0.0,
        )
        for ref in refs:
            name = components.get(ref, ref)
            exploitable[name] += 1
            top_cves[name].append((score, vulnerability.get("id", "unknown")))

    print("## Buildroot CVE report")
    print(
        f"\n- Resolved: {resolved['resolved']}"
        f"\n- Resolved with pedigree: {resolved['resolved_with_pedigree']}"
    )
    print("\n### Exploitable CVEs by component")
    if not exploitable:
        print("\nNo exploitable CVEs were reported.")
    for name in sorted(exploitable):
        print(f"\n#### {name}: {exploitable[name]}")
        for score, cve in sorted(top_cves[name], reverse=True)[:5]:
            print(f"- {cve} (CVSS {score:g})")


if __name__ == "__main__":
    main()
