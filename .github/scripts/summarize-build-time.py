#!/usr/bin/env python3
"""Print per-step and per-package totals from Buildroot's build-time.log."""
import collections
import sys


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else "output/build/build-time.log"
    top = int(sys.argv[2]) if len(sys.argv) > 2 else 15
    started: dict[tuple[str, str], float] = {}
    steps: collections.Counter[str] = collections.Counter()
    pkgs: collections.Counter[str] = collections.Counter()
    first = last = None
    unmatched = 0
    with open(path, encoding="utf-8") as log:
        for line in log:
            stamp, kind, rest = line.rstrip("\n").split(":", 2)
            step, pkg = (part.strip() for part in rest.split(":", 1))
            when = float(stamp)
            first = when if first is None else min(first, when)
            last = when if last is None else max(last, when)
            if kind.strip() == "start":
                started[(step, pkg)] = when
            elif (step, pkg) in started:
                spent = when - started.pop((step, pkg))
                steps[step] += spent
                pkgs[pkg] += spent
            else:
                unmatched += 1
    if first is None:
        print("=br-time=\tempty")
        return 0
    print(f"=br-time=\twall\t{last - first:.1f}")
    print(f"=br-time=\tunmatched\t{unmatched + len(started)}")
    for step, spent in steps.most_common():
        print(f"=br-time=\tstep\t{step}\t{spent:.1f}")
    for pkg, spent in pkgs.most_common(top):
        print(f"=br-time=\tpackage\t{pkg}\t{spent:.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
