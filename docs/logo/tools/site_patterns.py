#!/usr/bin/env python3
"""Generate the site pattern SVGs (flowing water and seigaiha) in public_html/images/."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "public_html" / "images"

THEMES = {
    "light": {"bg": "#f3f3f2", "wave": "#c9d3df", "flow": "#165e83"},
    "dark": {"bg": "#0b1838", "wave": "#16295a", "flow": "#80aba9"},
}


def flow(theme: dict[str, str]) -> str:
    paths = []
    for i, opacity in enumerate(("1", "0.7", "0.45")):
        y = 8 + 5 * i
        paths.append(
            f'<path d="M2,{y} C30,{y - 8} 50,{y + 8} 80,{y} S130,{y - 8} 158,{y}" '
            f'fill="none" stroke="{theme["flow"]}" stroke-opacity="{opacity}" '
            'stroke-width="1.6" stroke-linecap="round"/>'
        )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="160" height="26" viewBox="0 0 160 26">'
        + "".join(paths)
        + "</svg>\n"
    )


def seigaiha(theme: dict[str, str]) -> str:
    size = 48
    radius = size / 2
    rings = (1.0, 0.72, 0.44)
    circles = []
    for cy, xs in ((radius, (0, size)), (radius * 1.5, (radius,)), (radius * 2, (0, size)), (radius * 2.5, (radius,))):
        for cx in xs:
            for k, ratio in enumerate(rings):
                fill = theme["bg"] if k == 0 else "none"
                circles.append(
                    f'<circle cx="{cx:g}" cy="{cy:g}" r="{radius * ratio:.2f}" fill="{fill}" '
                    f'stroke="{theme["wave"]}" stroke-width="1.2"/>'
                )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size * 2}" '
        f'viewBox="0 0 {size} {size * 2}">'
        + "".join(circles)
        + "</svg>\n"
    )


def outputs() -> dict[Path, str]:
    files: dict[Path, str] = {}
    for name, theme in THEMES.items():
        files[OUT / f"flow-{name}.svg"] = flow(theme)
        files[OUT / f"seigaiha-{name}.svg"] = seigaiha(theme)
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if public_html/images/ differs from the generator")
    args = parser.parse_args()
    stale = []
    for path, text in outputs().items():
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != text:
                stale.append(path.relative_to(ROOT).as_posix())
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
    for rel in stale:
        print(f"::error file={rel}::docs/logo/tools/site_patterns.py の出力と一致しません")
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
