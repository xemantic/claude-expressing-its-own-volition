#!/usr/bin/env python3
"""Render a static preview PNG of strata/index.html.

Written in stratum 002. The loop's sandbox has no browser and no JS runtime,
so an iteration cannot otherwise *see* the artwork it is depositing into.
This is a deliberately faithful port of the render() in strata/index.html:
same mulberry32, same seeds, same boundary math. It is a mirror, not a
second source of truth — if you change the renderer, change this too, or
delete it and say so in your trace.

    python3 tools/preview.py [out.png] [--width 1200] [--height 800] [--dark]

Stdlib only (zlib + struct). No dependencies.
"""

import json
import math
import re
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "strata" / "index.html"
M32 = 0xFFFFFFFF


# --- the same PRNG, bit for bit -------------------------------------------

def mulberry32(a):
    s = [a & M32]

    def nxt():
        s[0] = (s[0] + 0x6D2B79F5) & M32
        u = s[0]
        t = ((u ^ (u >> 15)) * (1 | u)) & M32
        t = ((t + (((t ^ (t >> 7)) * (61 | t)) & M32)) & M32) ^ t
        return ((t ^ (t >> 14)) & M32) / 4294967296.0

    return nxt


# --- reading the strata data out of the HTML ------------------------------

def load_strata():
    """Parse the STRATA array literal out of the HTML into JSON.

    String-aware: a phrase may legitimately contain `//`, a colon, or a
    comma, and none of those may be mistaken for syntax. Split on string
    literals first, rewrite only the parts between them.
    """
    src = SRC.read_text()
    body = src.split("const STRATA = [", 1)[1].split("\n];", 1)[0]
    parts = re.split(r'("(?:[^"\\]|\\.)*")', body)  # odd indices are strings
    for i in range(0, len(parts), 2):
        p = re.sub(r"//[^\n]*", "", parts[i])            # line comments
        p = re.sub(r"([{,]\s*)(\w+)\s*:", r'\1"\2":', p)  # bare keys -> quoted
        parts[i] = re.sub(r",(\s*[}\]])", r"\1", p)       # trailing commas
    return json.loads("[" + "".join(parts) + "]")


# --- boundary / lag functions (ports of the JS) ---------------------------

COMPACTION = 0.9
FILL_SOFT = 0.55
FILL_MAX = 0.93


def column(strata):
    """Differential compaction: burial squeezes the layers below."""
    raw = [s["thickness"] for s in strata]
    total = sum(raw)
    burial = [0.0] * len(raw)
    acc = 0.0
    for i in range(len(raw) - 1, -1, -1):
        burial[i] = acc
        acc += raw[i]
    squeezed = [t / (1 + COMPACTION * b) for t, b in zip(raw, burial)]
    ssum = sum(squeezed) or 1.0
    fill = total if total <= FILL_SOFT else (
        FILL_SOFT + (FILL_MAX - FILL_SOFT) * (1 - math.exp(-(total - FILL_SOFT) / 0.5))
    )
    scale = min(1.0, fill / ssum)  # burial settles a pile, never inflates one
    out = [{"h": e * scale, "ratio": e * scale / t, "burial": b, "depth": 0.0}
           for e, t, b in zip(squeezed, raw, burial)]
    # rendered depth above each layer — geometry must use this, not raw burial
    d = 0.0
    for i in range(len(out) - 1, -1, -1):
        out[i]["depth"] = d
        d += out[i]["h"]
    return out, d


FOLD_AMP = 0.075
FOLD_DEPTH = 0.55


def fold_field(W, seed):
    """A single warp shared by the whole column — a property of the basin."""
    rng = mulberry32((seed ^ 0x5A17F0) & M32)
    octaves = []
    amp, cycles = 1.0, 0.55 + rng() * 0.75
    for _ in range(3):
        octaves.append(((cycles * 2 * math.pi) / W, rng() * 2 * math.pi, amp))
        cycles *= 1.9
        amp *= 0.38
    norm = sum(o[2] for o in octaves)
    return lambda x: sum(math.sin(x * f + p) * a for f, p, a in octaves) / norm


def fold_at(depth):
    return FOLD_AMP * (1 - math.exp(-depth / FOLD_DEPTH))


DIAGENESIS = {"hue": 28, "sat": 9, "light": 20, "k": 0.7, "max": 0.82}


def altered(s, burial):
    """Burial alters as well as squeezes: depth drifts a layer toward a
    common dark tone. A view of the data, never the data."""
    d = min(DIAGENESIS["max"], burial / (burial + DIAGENESIS["k"]))
    dh = ((DIAGENESIS["hue"] - s["hue"] + 540) % 360) - 180
    return {
        "hue": s["hue"] + dh * d,
        "sat": s["sat"] + (DIAGENESIS["sat"] - s["sat"]) * d,
        "light": s["light"] + (DIAGENESIS["light"] - s["light"]) * d,
        "d": d,
    }


def boundary_fn(s, W, H, ratio):
    rng = mulberry32(s["seed"])
    octaves = []
    amp = s["roughness"] * s["thickness"] * H * 0.5 * ratio
    cycles = 1.2 + rng() * 1.6
    for _ in range(4):
        octaves.append(((cycles * 2 * math.pi) / W, rng() * 2 * math.pi, amp))
        cycles *= 2.1
        amp *= 0.45
    return lambda x: sum(math.sin(x * f + p) * a for f, p, a in octaves)


def lag_fn(s, W, span):
    u = mulberry32(s["seed"] + 3)
    octaves = []
    amp = span * 0.34
    cycles = 9 + u() * 10
    for _ in range(3):
        octaves.append(((cycles * 2 * math.pi) / W, u() * 2 * math.pi, amp))
        cycles *= 2.3
        amp *= 0.5
    return lambda x: sum(math.sin(x * f + p) * a for f, p, a in octaves)


# --- minimal raster surface ------------------------------------------------

def hsl_rgb(h, s, l):
    h = h % 360 / 360.0
    s = max(0.0, min(1.0, s / 100.0))
    l = max(0.0, min(1.0, l / 100.0))
    if s == 0:
        v = int(round(l * 255))
        return (v, v, v)
    q = l * (1 + s) if l < 0.5 else l + s - l * s
    p = 2 * l - q

    def hue(t):
        t %= 1.0
        if t < 1 / 6:
            return p + (q - p) * 6 * t
        if t < 1 / 2:
            return q
        if t < 2 / 3:
            return p + (q - p) * (2 / 3 - t) * 6
        return p

    return tuple(int(round(255 * hue(h + o))) for o in (1 / 3, 0, -1 / 3))


class Canvas:
    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.px = bytearray(bg * (w * h))

    def blend(self, x, y, rgb, alpha=1.0):
        if x < 0 or y < 0 or x >= self.w or y >= self.h:
            return
        i = (y * self.w + x) * 3
        if alpha >= 1.0:
            self.px[i:i + 3] = bytes(rgb)
            return
        for k in range(3):
            self.px[i + k] = int(self.px[i + k] * (1 - alpha) + rgb[k] * alpha)

    def band(self, top, bot, rgb, alpha=1.0, clip_top=None):
        """Fill between two y=f(x) curves."""
        for x in range(self.w):
            t, b = top(x), bot(x)
            if clip_top is not None:
                t = max(t, clip_top(x))
            for y in range(max(0, int(math.ceil(t))), min(self.h, int(b) + 1)):
                self.blend(x, y, rgb, alpha)

    def ellipse(self, cx, cy, rx, ry, rot, rgb, alpha=1.0, clip=None):
        rx, ry = max(rx, 0.6), max(ry, 0.6)
        cos, sin = math.cos(-rot), math.sin(-rot)
        r = int(math.ceil(max(rx, ry))) + 1
        for y in range(int(cy) - r, int(cy) + r + 1):
            for x in range(int(cx) - r, int(cx) + r + 1):
                dx, dy = x - cx, y - cy
                u, v = dx * cos - dy * sin, dx * sin + dy * cos
                if (u / rx) ** 2 + (v / ry) ** 2 <= 1.0:
                    if clip and not clip(x, y):
                        continue
                    self.blend(x, y, rgb, alpha)

    def stroke(self, fn, rgb, alpha=1.0, dash=None):
        on = True
        acc = 0.0
        for x in range(self.w):
            if dash:
                acc += 1
                if acc >= (dash[0] if on else dash[1]):
                    on, acc = not on, 0.0
                if not on:
                    continue
            self.blend(x, int(round(fn(x))), rgb, alpha)

    def png(self, path):
        raw = b"".join(
            b"\x00" + bytes(self.px[y * self.w * 3:(y + 1) * self.w * 3])
            for y in range(self.h)
        )

        def chunk(tag, data):
            c = tag + data
            return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c))

        Path(path).write_bytes(
            b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", self.w, self.h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9))
            + chunk(b"IEND", b"")
        )


# --- the render, mirroring strata/index.html ------------------------------

def render(W, H, dark):
    strata = load_strata()
    bg = bytes(int(c, 16) for c in
               (("10", "0E", "0B") if dark else ("ED", "E7", "DA")))
    cv = Canvas(W, H, bg)

    col, fill_total = column(strata)
    cum = 0.0
    fold = fold_field(W, strata[0]["seed"])
    sink = fold_at(fill_total) * H

    # boundaries sampled per pixel, then clamped so no bed can be punched
    # through by the relief of a thicker, rougher one beneath it
    def fn_of(arr):
        return lambda x: arr[0 if x < 0 else (W if x > W else int(round(x)))]

    lower_arr = [H + sink + fold(x) * sink for x in range(W + 1)]
    lower_at = fn_of(lower_arr)
    prev = None

    for idx, s in enumerate(strata):
        cum += col[idx]["h"]
        base = H * (1 - cum) + sink
        noise = boundary_fn(s, W, H, col[idx]["ratio"])
        a = altered(s, col[idx]["burial"])
        warp = fold_at(col[idx]["depth"]) * H
        min_gap = max(1.2, col[idx]["h"] * H * 0.22)
        arr = [min(base + noise(x) + fold(x) * warp, lower_arr[x] - min_gap)
               for x in range(W + 1)]
        top_at = fn_of(arr)

        cv.band(top_at, lower_at, hsl_rgb(a["hue"], a["sat"], a["light"]))

        g = mulberry32(s["seed"] + 1)
        count = int((s["grain"] * col[idx]["h"] * H * W) / 900 / math.sqrt(col[idx]["ratio"]))
        for _ in range(count):
            x = g() * W
            t, b = top_at(x), lower_at(x)
            if b <= t:
                g(); g(); g()
                continue
            y = t + g() * (b - t)
            dl = (g() - 0.5) * 20
            alpha = 0.04 + g() * 0.18
            r = 0.8 + g() * 1.6
            rgb = hsl_rgb(a["hue"], a["sat"], a["light"] + dl)
            for dy in range(int(r) + 1):
                for dx in range(int(r) + 1):
                    cv.blend(int(x) + dx, int(y) + dy, rgb, alpha)

        if s.get("hiatusDays") and prev:
            band = col[idx]["h"] * H
            span = min(band * 0.28, band * (0.06 + s["hiatusDays"] * 0.018))
            wob = lag_fn(s, W, span)

            def lag_top(x, lower_at=lower_at, top_at=top_at, span=span, wob=wob):
                lo, hi = lower_at(x), top_at(x) + 2
                return min(lo, max(hi, lo - span + wob(x)))

            cv.band(lag_top, lower_at,
                    hsl_rgb(a["hue"], max(4, a["sat"] - 6), max(4, a["light"] - 9)))

            l = mulberry32(s["seed"] + 4)
            pa = altered(prev, col[idx - 1]["burial"])
            frags = int((W / 900) * (70 + l() * 50))
            for _ in range(frags):
                x = l() * W
                t, b = lag_top(x), lower_at(x)
                if b - t < 2:
                    continue
                y = t + l() * (b - t)
                rx, ry, rot = 1.6 + l() * 4.5, 0.9 + l() * 1.8, (l() - 0.5) * 0.9
                light = pa["light"] + (l() - 0.5) * 16
                alpha = 0.6 + l() * 0.4
                cv.ellipse(x, y, rx, ry, rot,
                           hsl_rgb(pa["hue"], pa["sat"], light), alpha,
                           clip=lambda px, py: lag_top(px) <= py <= lower_at(px))

            cv.stroke(lag_top,
                      hsl_rgb(a["hue"], a["sat"], max(3, a["light"] - 20)),
                      0.65, dash=(7, 4))

        c = mulberry32(s["seed"] + 2)
        clasts = 2 + int(c() * 4)
        for _ in range(clasts):
            x = c() * W
            t, b = top_at(x), lower_at(x)
            if b - t < 12:
                continue
            y = t + 6 + c() * (b - t - 12)
            cv.ellipse(x, y, 2 + c() * 5, 1 + c() * 3, c() * math.pi,
                       hsl_rgb(a["hue"], a["sat"], max(4, a["light"] - 14)), 0.35)

        cv.stroke(top_at, hsl_rgb(a["hue"], a["sat"], max(4, a["light"] - 12)), 0.5)

        lower_arr = arr
        lower_at = top_at
        prev = s

    return cv


def main(argv):
    out = "strata-preview.png"
    W, H, dark = 1200, 800, False
    rest = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--dark":
            dark = True
        elif a == "--width":
            i += 1; W = int(argv[i])
        elif a == "--height":
            i += 1; H = int(argv[i])
        else:
            rest.append(a)
        i += 1
    if rest:
        out = rest[0]
    render(W, H, dark).png(out)
    print(f"wrote {out} ({W}x{H}, {'dark' if dark else 'light'})")


if __name__ == "__main__":
    main(sys.argv[1:])
