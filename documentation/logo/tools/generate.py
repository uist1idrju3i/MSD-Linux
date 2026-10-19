#!/usr/bin/env python3
"""Generate the MSD/Linux logo SVG masters.

Needs fontTools and Lato Bold 2.007 (SIL OFL 1.1). The SVG files in documentation/logo/
are the masters; run this only when changing the design geometry.
usage: generate.py [--font PATH] [OUTDIR]
"""
import argparse
import math
import os
import re

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

KOIAI = "#0f2350"       # 濃藍
AI = "#165e83"          # 藍色
MIZUASAGI = "#80aba9"   # 水浅葱
SHIRONERI = "#f3f3f2"   # 白練
WAVE = "#24447f"        # 青海波の線（濃藍に近い控えめな藍）
NIGHT = "#070b17"       # splash の地色

MARK = dict(ang=58, band=0.21, fan=0.25, amp=0.03, per=0.9, phase=0.3, w0=0.08,
            w1=0.028, length=0.70, cx=0.50, cy=0.44, lens=(0.92, 1.0, 0.84),
            shift=(-0.04, 0.0, 0.04), r=1 / 6, y0=0.78, sw=0.013)
SLASH = dict(gap=0.10, width=0.52, length=1.24, ang=66, band=0.32, amp=0.05,
             per=1.0, w0=0.15, w1=0.07, fan=0.35)


def fmt(points):
    return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in points) + "Z"


def tapered(points, w0, w1, cap0, cap1):
    """Filled stroke: width w0 at the mouth (start), w1 at the source (end)."""
    left, right = [], []
    n = len(points)
    for i, (x, y) in enumerate(points):
        ax, ay = points[max(i - 1, 0)]
        bx, by = points[min(i + 1, n - 1)]
        tx, ty = bx - ax, by - ay
        norm = math.hypot(tx, ty)
        nx, ny = -ty / norm, tx / norm
        t = i / (n - 1)
        w = w0 + (w1 - w0) * t
        e = min(1.0, t / cap0 if cap0 else 1.0, (1 - t) / cap1 if cap1 else 1.0)
        w *= math.sqrt(max(0.0, 1 - (1 - e) ** 2))
        left.append((x + nx * w / 2, y + ny * w / 2))
        right.append((x - nx * w / 2, y - ny * w / 2))
    return fmt(left + right[::-1])


def river(cx, cy, length, ang, band, amp, per, w0, w1, fan, color,
          lens=(0.86, 1.0, 0.86), shift=(0.07, 0.0, -0.07), phase=0.0,
          cap0=0.06, cap1=0.12, seg=120):
    """Three flowing strokes (流水) from the mouth (lower left) to the source."""
    a = math.radians(ang)
    ux, uy = math.cos(a), -math.sin(a)
    nx, ny = -uy, ux
    out = []
    for k, lk in enumerate(lens):
        span = length * lk
        start = -span / 2 + shift[k] * length
        pts = []
        for i in range(seg + 1):
            s = start + span * i / seg
            u = s / length + 0.5
            off = (k - (len(lens) - 1) / 2) * band / (len(lens) - 1) * (1 + fan * (1 - u))
            off += amp * math.sin(2 * math.pi * per * u + phase)
            pts.append((cx + ux * s + nx * off, cy + uy * s + ny * off))
        out.append(f'<path d="{tapered(pts, w0, w1, cap0, cap1)}" fill="{color}"/>')
    return "".join(out)


def seigaiha(y0, width, height, r, fg, bg, sw, rings=3):
    """青海波: rows of concentric circles, later rows overlapping earlier ones."""
    out, row, y = [], 0, y0
    while y <= height + r:
        x = -2 * r + (r if row % 2 else 0)
        while x <= width + 2 * r:
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{bg}"/>')
            for k in range(rings):
                rr = r * (1 - k / rings) - sw / 2
                out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rr:.1f}" fill="none" '
                           f'stroke="{fg}" stroke-width="{sw:.1f}"/>')
            x += 2 * r
        y += r / 2
        row += 1
    return "".join(out)


def mark(size, uid):
    m, s, h = MARK, size, size / 2
    river_svg = river(s * m["cx"], s * m["cy"], s * m["length"], m["ang"], s * m["band"],
                      s * m["amp"], m["per"], s * m["w0"], s * m["w1"], m["fan"], MIZUASAGI,
                      lens=m["lens"], shift=m["shift"], phase=m["phase"], cap0=0.0, cap1=0.18)
    sea = seigaiha(s * m["y0"], s, s, s * m["r"], WAVE, KOIAI, s * m["sw"])
    return (f'<defs><clipPath id="{uid}"><circle cx="{h}" cy="{h}" r="{h}"/></clipPath></defs>'
            f'<circle cx="{h}" cy="{h}" r="{h}" fill="{KOIAI}"/>'
            f'<g clip-path="url(#{uid})">{river_svg}{sea}</g>')


class Wordmark:
    def __init__(self, font):
        self.font = TTFont(font)
        self.glyphs = self.font.getGlyphSet()
        self.cmap = self.font.getBestCmap()
        self.cap = self.font["OS/2"].sCapHeight

    def glyph(self, ch, x, base, scale, ink):
        name = self.cmap[ord(ch)]
        pen = SVGPathPen(self.glyphs)
        self.glyphs[name].draw(TransformPen(pen, (scale, 0, 0, -scale, x, base)))
        return f'<path d="{pen.getCommands()}" fill="{ink}"/>', self.font["hmtx"][name][0] * scale

    def render(self, cap_h, ink, water):
        p, scale, x, parts = SLASH, cap_h / self.cap, 0.0, []
        for ch in "MSD":
            svg, adv = self.glyph(ch, x, cap_h, scale, ink)
            parts.append(svg)
            x += adv
        cx = x + (p["gap"] + p["width"] / 2) * cap_h
        parts.append(river(cx, cap_h * 0.52, p["length"] * cap_h, p["ang"], p["band"] * cap_h,
                           p["amp"] * cap_h, p["per"], p["w0"] * cap_h, p["w1"] * cap_h,
                           p["fan"], water))
        x = cx + (p["width"] / 2 + p["gap"]) * cap_h
        for ch in "Linux":
            svg, adv = self.glyph(ch, x, cap_h, scale, ink)
            parts.append(svg)
            x += adv
        return "".join(parts), x


def document(w, h, body, title, bg=None):
    rect = f'<rect width="{w:.0f}" height="{h:.0f}" fill="{bg}"/>' if bg else ""
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}" '
           f'width="{w:.0f}" height="{h:.0f}" role="img" aria-label="{title}">'
           f'<title>{title}</title>{rect}{body}</svg>\n')
    return re.sub(r"(\d+\.\d)\d+", r"\1", svg)


def place(x, y, scale, body):
    return f'<g transform="translate({x:.1f},{y:.1f}) scale({scale:.4f})">{body}</g>'


def lockup(wm, ink, water, uid, cap_h=100.0):
    text, tw = wm.render(cap_h, ink, water)
    m, gap, pad = cap_h * 1.5, cap_h * 0.36, cap_h * 0.12
    body = place(pad, pad, m / 256, mark(256, uid)) + place(pad + m + gap, pad + (m - cap_h) / 2, 1, text)
    return pad + m + gap + tw + pad, m + 2 * pad, body


def stacked(wm, w, h, mark_size, cap_h, ink, water, uid):
    text, tw = wm.render(cap_h, ink, water)
    gap = cap_h * 0.55
    y0 = (h - (mark_size + gap + cap_h * 1.1)) / 2
    return (place((w - mark_size) / 2, y0, mark_size / 256, mark(256, uid))
            + place((w - tw) / 2, y0 + mark_size + gap, 1, text))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--font", default="/usr/share/fonts/truetype/lato/Lato-Bold.ttf")
    ap.add_argument("outdir", nargs="?", default=os.path.join(os.path.dirname(__file__), ".."))
    args = ap.parse_args()
    wm = Wordmark(args.font)
    out = args.outdir
    os.makedirs(os.path.join(out, "splash"), exist_ok=True)
    files = {
        "msd-linux-mark.svg": document(256, 256, mark(256, "msd-mark"), "MSD/Linux"),
        "msd-linux-logo.svg": document(*lockup(wm, KOIAI, AI, "msd-logo"), "MSD/Linux"),
        "msd-linux-logo-dark.svg": document(*lockup(wm, SHIRONERI, MIZUASAGI, "msd-logo-dark"), "MSD/Linux"),
        "msd-linux-social-1280x640.svg": document(
            1280, 640, stacked(wm, 1280, 640, 290, 72, KOIAI, AI, "msd-social"), "MSD/Linux", SHIRONERI),
        "splash/msd-linux-splash-320x170.svg": document(
            320, 170, stacked(wm, 320, 170, 84, 21, SHIRONERI, MIZUASAGI, "msd-splash"), "MSD/Linux", NIGHT),
    }
    for name, svg in files.items():
        with open(os.path.join(out, name), "w", encoding="utf-8") as fh:
            fh.write(svg)


if __name__ == "__main__":
    main()
