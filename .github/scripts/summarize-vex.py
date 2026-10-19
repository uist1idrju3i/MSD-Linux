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

    components = {}
    for component in report.get("components", []):
        ref = component.get("bom-ref")
        if not ref:
            continue
        properties = component.get("properties", [])
        br_type = next(
            (
                prop.get("value")
                for prop in properties
                if prop.get("name") == "BR_TYPE"
            ),
            "unknown",
        )
        components[ref] = {
            "name": component.get("name", ref),
            "type": br_type,
        }
    exploitable = {
        "target": collections.Counter(),
        "host": collections.Counter(),
        "unknown": collections.Counter(),
    }
    top_cves = {
        "target": collections.defaultdict(list),
        "host": collections.defaultdict(list),
        "unknown": collections.defaultdict(list),
    }
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
            br_type = components.get(ref, {}).get("type", "unknown")
            section = br_type if br_type in {"target", "host"} else "unknown"
            exploitable[section][ref] += 1
            top_cves[section][ref].append((score, vulnerability.get("id", "unknown")))

    print("## Buildroot CVE report")
    print(
        f"\n- Resolved: {resolved['resolved']}"
        f"\n- Resolved with pedigree: {resolved['resolved_with_pedigree']}"
    )
    print("\n### Exploitable CVEs by component type")
    sections = [
        ("target", "Target (in image)"),
        ("host", "Host (build tools, not in image)"),
        ("unknown", "Other (unknown BR_TYPE)"),
    ]
    for category, title in sections:
        if category == "unknown" and not exploitable[category]:
            continue
        print(f"\n### {title}")
        if not exploitable[category]:
            print("\nNo exploitable CVEs were reported.")
            continue
        for ref in sorted(
            exploitable[category],
            key=lambda item: (components.get(item, {}).get("name", item), item),
        ):
            name = components.get(ref, {}).get("name", ref)
            print(f"\n#### {name}: {exploitable[category][ref]}")
            for score, cve in sorted(top_cves[category][ref], reverse=True)[:5]:
                print(f"- {cve} (CVSS {score:g})")


if __name__ == "__main__":
    main()
