#!/usr/bin/env python3
"""Compare the static site before/after the Pages header change."""

import argparse
import csv
import functools
import hashlib
import http.server
import shutil
import subprocess
import threading
from contextlib import ExitStack
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright


def pixels(left, right):
    a, b = Image.open(left).convert("RGB"), Image.open(right).convert("RGB")
    if a.size != b.size:
        raise ValueError("image dimensions differ")
    a, b = a.tobytes(), b.tobytes()
    return sum(a[i:i + 3] != b[i:i + 3] for i in range(0, len(a), 3))


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--browser", default="google-chrome")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = args.output.resolve()
    out.mkdir()
    rows = []
    paths = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", args.baseline, "public_html"], cwd=root,
        text=True).splitlines()
    for path in paths:
        target = out / "before" / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(subprocess.check_output(
            ["git", "show", f"{args.baseline}:{path}"], cwd=root))
    shutil.copytree(root / "public_html", out / "after/public_html")
    for name in ("w3m", "lynx"):
        version = subprocess.run([name, "-version"], capture_output=True, text=True, check=True)
        rows.append(("version", name, (version.stdout + version.stderr).splitlines()[0]))
    for page in ("index.html", "404.html"):
        for name, width in (("w3m", 40), ("w3m", 80), ("lynx", 80)):
            dumps = []
            for variant in ("before", "after"):
                command = (["w3m", "-T", "text/html", "-dump", "-cols", str(width),
                            "-o", "display_charset=UTF-8"] if name == "w3m" else [
                                "lynx", "-stdin", "-dump", "-nolist", "-width=80",
                                "-display_charset=utf-8", "-assume_charset=utf-8"])
                data = subprocess.check_output(
                    command, input=(out / variant / "public_html" / page).read_bytes())
                (out / f"{variant}-{page}-{name}{width}.txt").write_bytes(data)
                dumps.append(data)
            rows.append(("text-diff", f"{page}-{name}{width}", int(dumps[0] != dumps[1])))
    control = out / "control.png"
    negative = out / "negative.png"
    image = Image.new("RGB", (2, 2), "white")
    image.save(control)
    image.putpixel((0, 0), (0, 0, 0))
    image.save(negative)
    assert pixels(control, control) == 0 and pixels(control, negative) == 1
    rows.extend([("control", "A/A", 0), ("control", "one-pixel", 1)])
    cases = [(320, 170, color, full, "none") for color in ("light", "dark") for full in (False, True)]
    cases += [(800, 360, color, False, "none") for color in ("light", "dark")]
    cases += [(1280, 800, color, True, "none") for color in ("light", "dark")]
    cases += [(320, 170, "light", False, "active")]
    with sync_playwright() as playwright, ExitStack() as stack:
        urls = {}
        for variant in ("before", "after"):
            handler = functools.partial(Handler, directory=str(out / variant / "public_html"))
            server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
            stack.callback(server.server_close)
            stack.callback(server.shutdown)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            urls[variant] = f"http://127.0.0.1:{server.server_port}"
        browser = playwright.chromium.launch(executable_path=shutil.which(args.browser),
                                              headless=True, args=["--no-sandbox"])
        stack.callback(browser.close)
        rows.append(("version", "Chrome", browser.version))
        for page in ("index.html", "404.html"):
            for width, height, color, full, forced in cases:
                key = f"{page}-{width}x{height}-{color}-{'full' if full else 'first'}-{forced}"
                images = []
                for variant in ("before", "after"):
                    context = browser.new_context(viewport={"width": width, "height": height},
                                                  color_scheme=color, forced_colors=forced)
                    tab = context.new_page()
                    errors = []
                    tab.on("pageerror", lambda error: errors.append(str(error)))
                    tab.on("requestfailed", lambda request: errors.append(request.url))
                    tab.goto(f"{urls[variant]}/{page}", wait_until="networkidle")
                    tab.evaluate("document.fonts.ready")
                    path = out / f"{variant}-{key}.png"
                    tab.screenshot(path=str(path), full_page=full)
                    images.append(path)
                    context.close()
                    if errors:
                        raise RuntimeError(errors)
                rows.append(("pixel-diff", key, pixels(*images)))
    with (out / "results.csv").open("w") as file:
        writer = csv.writer(file)
        writer.writerow(("kind", "case", "value"))
        writer.writerows(rows)
    with (out / "SHA256SUMS").open("w") as file:
        for path in sorted(out.glob("*")):
            if path.is_file() and path.name != "SHA256SUMS":
                file.write(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n")
    assert all(value == 0 for kind, _, value in rows if kind in ("text-diff", "pixel-diff"))
    print("ok - 6 text comparisons and 18 screenshot pairs are unchanged; A/A=0 negative=1")


if __name__ == "__main__":
    main()
