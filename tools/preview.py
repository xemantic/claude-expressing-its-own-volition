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
FILL_MIN = 0.72
FILL_MAX = 0.95
FILL_RATE = 0.7


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
    # the column always composes the frame; empty space above is a margin
    fill = FILL_MIN + (FILL_MAX - FILL_MIN) * (1 - math.exp(-total / FILL_RATE))
    scale = fill / ssum
    out = [{"h": e * scale, "ratio": e * scale / t, "burial": b, "depth": 0.0,
            "compaction": 1 / (1 + COMPACTION * b)}
           for e, t, b in zip(squeezed, raw, burial)]
    # rendered depth above each layer — geometry must use this, not raw burial
    d = 0.0
    for i in range(len(out) - 1, -1, -1):
        out[i]["depth"] = d
        d += out[i]["h"]
    return out, d


DIAGENESIS = {
    "light": {"hue": 28, "sat": 9, "light": 20},
    "dark": {"hue": 28, "sat": 11, "light": 34},
    "k": 0.7, "max": 0.82,
}
GRADE_RANGE = 4.5


def altered(s, burial, target):
    """Burial alters as well as squeezes: depth drifts a layer toward a
    common tone. The target differs by theme so the deep past merges with
    itself rather than dissolving into the ground. A view, never the data."""
    d = min(DIAGENESIS["max"], burial / (burial + DIAGENESIS["k"]))
    dh = ((target["hue"] - s["hue"] + 540) % 360) - 180
    return {
        "hue": s["hue"] + dh * d,
        "sat": s["sat"] + (target["sat"] - s["sat"]) * d,
        "light": s["light"] + (target["light"] - s["light"]) * d,
        "d": d,
    }


FOLD_EVERY = 6       # strata between deformation episodes
FOLD_EPISODE = 0.02  # displacement per episode, fraction of frame height
FOLD_RAMP = 5        # strata over which an episode's effect ramps in


def wave_span(H):
    """Horizontal wavelengths are measured against the vertical scale, not the
    window width, so slope is invariant and resizing crops the section rather
    than stretching it. 1.6 is the reference aspect."""
    return H * 1.6


EXPOSURE = 0.3


def exposure_fn(s, W, H, band):
    """The newest bed is the only one nothing protects, so it alone weathers.
    Biased downward by its own mean: weathering removes material."""
    rng = mulberry32((s["seed"] + 5) & M32)
    octaves = []
    amp = min(band * EXPOSURE, H * 0.022)
    cycles = 2.5 + rng() * 3.5
    for _ in range(3):
        octaves.append(((cycles * 2 * math.pi) / wave_span(H), rng() * 2 * math.pi, amp))
        cycles *= 2.2
        amp *= 0.45
    total = sum(o[2] for o in octaves)
    ef = (0.7 + rng() * 0.9) * 2 * math.pi / wave_span(H)
    ep = rng() * 2 * math.pi
    # an envelope: weathering cuts some stretches deeply and barely touches
    # others, and without it the relief reads as ornament rather than wear
    def f(x):
        env = 0.3 + 0.7 * (0.5 + 0.5 * math.sin(x * ef + ep))
        y = sum(math.sin(x * fr + ph) * a for fr, ph, a in octaves)
        return (y * 0.5 + total * 0.5) * env
    return f


def fold_field(W, H, seed):
    """One deformation episode's shape."""
    rng = mulberry32((seed ^ 0x5A17F0) & M32)
    octaves = []
    amp, cycles = 1.0, 0.55 + rng() * 0.75
    for _ in range(3):
        octaves.append(((cycles * 2 * math.pi) / wave_span(H), rng() * 2 * math.pi, amp))
        cycles *= 1.9
        amp *= 0.38
    norm = sum(o[2] for o in octaves)
    return lambda x: sum(math.sin(x * f + p) * a for f, p, a in octaves) / norm


def fold_episodes(strata, W, H):
    """Rock deforms in events, not continuously. An episode after stratum n
    bends everything that existed then and nothing deposited after, and is
    keyed to n rather than to a depth so it keeps its grip as the record
    grows beneath it."""
    amp = FOLD_EPISODE * H
    out = []
    for n in range(FOLD_EVERY, len(strata) + 1, FOLD_EVERY):
        field = fold_field(W, H, (strata[0]["seed"] ^ (n * 0x9E37)) & M32)
        out.append({"n": n, "samples": [field(x) * amp for x in range(W + 1)]})
    return out, amp


def episode_weight(n, i):
    """How much of an episode stratum i has taken up: 1 well below it, 0 for
    beds deposited after it, smooth between."""
    t = (n - i + 1) / FOLD_RAMP
    if t <= 0:
        return 0.0
    if t >= 1:
        return 1.0
    return t * t * (3 - 2 * t)


SWELL = 0.3  # lateral thickness variation, as a fraction of the bed


def boundary_fn(s, W, H, ratio):
    """Bedding relief plus one long swell of the bed's own: deposition is not
    uniform across a basin, and without it every boundary rides the shared
    fold in parallel and the column reads as even ribbons."""
    rng = mulberry32(s["seed"])
    octaves = []
    damp = 1.0
    amp = s["roughness"] * s["thickness"] * H * 0.5 * ratio * damp
    cycles = 1.2 + rng() * 1.6
    for _ in range(4):
        octaves.append(((cycles * 2 * math.pi) / wave_span(H), rng() * 2 * math.pi, amp))
        cycles *= 2.1
        amp *= 0.45
    sw = mulberry32((s["seed"] + 6) & M32)
    swell_amp = s["thickness"] * ratio * H * SWELL * damp
    swell_f = (0.8 + sw() * 1.7) * 2 * math.pi / wave_span(H)
    swell_p = sw() * 2 * math.pi
    return lambda x: (sum(math.sin(x * f + p) * a for f, p, a in octaves)
                      + math.sin(x * swell_f + swell_p) * swell_amp)


def lag_fn(s, W, H, span):
    u = mulberry32(s["seed"] + 3)
    octaves = []
    amp = span * 0.34
    cycles = 9 + u() * 10
    for _ in range(3):
        octaves.append(((cycles * 2 * math.pi) / wave_span(H), u() * 2 * math.pi, amp))
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
        if rot == 0.0:  # axis-aligned: solve each scanline directly
            y0 = max(0, int(math.ceil(cy - ry)))
            y1 = min(self.h - 1, int(cy + ry))
            for y in range(y0, y1 + 1):
                t = 1.0 - ((y - cy) / ry) ** 2
                if t <= 0:
                    continue
                half = rx * math.sqrt(t)
                for x in range(max(0, int(cx - half)), min(self.w - 1, int(cx + half)) + 1):
                    if clip and not clip(x, y):
                        continue
                    self.blend(x, y, rgb, alpha)
            return
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
    target = DIAGENESIS["dark" if dark else "light"]
    cv = Canvas(W, H, bg)

    col, fill_total = column(strata)
    cum = 0.0
    episodes, ep_amp = fold_episodes(strata, W, H)
    floor_at = [sum(e["samples"][x] for e in episodes) for x in range(W + 1)]
    # measured, not bounded — see the note in the renderer
    sink = max(0.0, -min(floor_at)) if floor_at else 0.0

    # boundaries sampled per pixel, then clamped so no bed can be punched
    # through by the relief of a thicker, rougher one beneath it
    def fn_of(arr):
        return lambda x: arr[0 if x < 0 else (W if x > W else int(round(x)))]

    lower_arr = [H + sink + floor_at[x] for x in range(W + 1)]
    lower_at = fn_of(lower_arr)
    prev = None

    for idx, s in enumerate(strata):
        cum += col[idx]["h"]
        base = H * (1 - cum) + sink
        noise = boundary_fn(s, W, H, col[idx]["ratio"])
        a = altered(s, col[idx]["burial"], target)
        weights = [episode_weight(e["n"], idx + 1) for e in episodes]
        min_gap = max(1.2, col[idx]["h"] * H * 0.22)
        weather = (exposure_fn(s, W, H, col[idx]["h"] * H)
                   if idx == len(strata) - 1 else None)
        arr = [min(base + noise(x)
                   + sum(e["samples"][x] * w for e, w in zip(episodes, weights))
                   + (weather(x) if weather else 0.0),
                   lower_arr[x] - min_gap)
               for x in range(W + 1)]
        top_at = fn_of(arr)

        cv.band(top_at, lower_at, hsl_rgb(a["hue"], a["sat"], a["light"]))

        # grading: coarse and dark at the base, fining upward, in slices that
        # follow the bed's own boundaries
        # finer steps, each boundary wobbling on its own so quantisation cannot
        # line up into parallel contours across the bed — see stratum 017
        slices = max(4, min(32, round(col[idx]["h"] * H / 2.5)))
        gw = mulberry32((s["seed"] + 9) & M32)
        band_h = col[idx]["h"] * H

        def sliced(f, wf, wp, wa):
            def g(x):
                t = top_at(x)
                y = t + (lower_at(x) - t) * f
                return y + (math.sin(x * wf + wp) * wa if 0 < f < 1 else 0.0)
            return g

        for k in range(slices):
            wf = (1.5 + gw() * 3) * 2 * math.pi / wave_span(H)
            wp = gw() * 2 * math.pi
            wa = band_h * 0.012
            f0 = k / slices
            f1 = 1.0 if k == slices - 1 else (k + 1) / slices + 0.02
            dl = GRADE_RANGE * (1 - 2 * ((k + 0.5) / slices))
            cv.band(sliced(f0, wf, wp, wa), sliced(f1, wf, wp, wa),
                    hsl_rgb(a["hue"], a["sat"], a["light"] + dl))

        # a diastem: a wake-up that looked and deposited nothing. No rubble —
        # nothing was reworked — just a sharper contact and a shallow scour.
        if s.get("skipped") and prev:
            dz = min(col[idx]["h"] * H * 0.16, 5) * (1 + 0.35 * (s["skipped"] - 1))
            sc = mulberry32((s["seed"] + 11) & M32)
            f1 = (14 + sc() * 16) * 2 * math.pi / wave_span(H)
            p1 = sc() * 2 * math.pi

            def scour_top(x, lower_at=lower_at, top_at=top_at, dz=dz, f1=f1, p1=p1):
                lo, hi = lower_at(x), top_at(x) + 1
                return min(lo, max(hi, lo - dz * (0.55 + 0.45 * math.sin(x * f1 + p1))))

            cv.band(scour_top, lower_at,
                    hsl_rgb(a["hue"], max(3, a["sat"] - 4), max(3, a["light"] - 7)))
            cv.stroke(lower_at,
                      hsl_rgb(a["hue"], a["sat"], max(3, a["light"] - 24)), 0.75)

        # lamination: internal partings, one per distinct piece of work,
        # erased by burial once the bed is thinner than a few pixels
        if s.get("laminae", 0) > 1 and col[idx]["h"] * H >= 12:
            # quieter and jittered off the grid — see stratum 017
            lm = mulberry32((s["seed"] + 8) & M32)
            for k in range(1, s["laminae"]):
                f = (k + (lm() - 0.5) * 0.45) / s["laminae"]
                cv.stroke((lambda f: lambda x: top_at(x) + (lower_at(x) - top_at(x)) * f)(f),
                          hsl_rgb(a["hue"], a["sat"], max(3, a["light"] - 9)),
                          0.16 + lm() * 0.1)

        g = mulberry32(s["seed"] + 1)
        ge = mulberry32((s["seed"] + 10) & M32)
        grain_f = (1.1 + ge() * 1.8) * 2 * math.pi / wave_span(H)
        grain_p = ge() * 2 * math.pi
        count = int((s["grain"] * col[idx]["h"] * H * W) / 900 / math.sqrt(col[idx]["ratio"]))
        for _ in range(count):
            x = g() * W
            t, b = top_at(x), lower_at(x)
            if b <= t:
                g(); g(); g()
                continue
            y = t + g() * (b - t)
            dl = (g() - 0.5) * 20
            # grain clusters rather than sprinkling evenly — see stratum 019
            env = 0.25 + 0.75 * (0.5 + 0.5 * math.sin(x * grain_f + grain_p))
            alpha = (0.04 + g() * 0.18) * env
            r = 0.8 + g() * 1.6
            rgb = hsl_rgb(a["hue"], a["sat"], a["light"] + dl)
            for dy in range(int(r) + 1):
                for dx in range(int(r) + 1):
                    cv.blend(int(x) + dx, int(y) + dy, rgb, alpha)

        if s.get("hiatusDays") and prev:
            band = col[idx]["h"] * H
            span = min(band * 0.28, band * (0.06 + s["hiatusDays"] * 0.018))
            wob = lag_fn(s, W, H, span)

            def lag_top(x, lower_at=lower_at, top_at=top_at, span=span, wob=wob):
                lo, hi = lower_at(x), top_at(x) + 2
                return min(lo, max(hi, lo - span + wob(x)))

            cv.band(lag_top, lower_at,
                    hsl_rgb(a["hue"], max(4, a["sat"] - 6), max(4, a["light"] - 9)))

            l = mulberry32(s["seed"] + 4)
            pa = altered(prev, col[idx - 1]["burial"], target)
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
                      hsl_rgb(a["hue"], a["sat"], max(3, a["light"] - 20)), 0.65)

        # mottling: a large mass is never one tone, and the thick beds had
        # been the least textured things in the picture
        mo = mulberry32(s["seed"] + 7)
        for _ in range(round(col[idx]["h"] * H * W / 17000)):
            bx = mo() * W
            t, b = top_at(bx), lower_at(bx)
            if b - t < 6:
                mo(); mo(); mo()
                continue
            band = b - t
            by = t + mo() * band
            cv.ellipse(bx, by, band * (1.5 + mo() * 2.5), band * (0.25 + mo() * 0.3),
                       0.0, hsl_rgb(a["hue"], a["sat"], a["light"] + (mo() - 0.5) * 26),
                       0.13,
                       clip=lambda px, py: top_at(px) <= py <= lower_at(px))

        # clasts: the coarse fraction — a density, not a handful
        c = mulberry32(s["seed"] + 2)
        band_px = max(1.0, col[idx]["h"] * H)
        clast_scale = min(1.0, band_px / 26)
        for _ in range(round(band_px * W / 3500)):
            x = c() * W
            t, b = top_at(x), lower_at(x)
            if b - t < 2.5:
                c(); c(); c(); c()
                continue
            inset = min(3.0, (b - t) * 0.18)
            y = t + inset + c() * (b - t - 2 * inset)
            cv.ellipse(x, y, (1.4 + c() * 4) * clast_scale,
                       (0.8 + c() * 2.2) * clast_scale, (c() - 0.5) * 1.2,
                       hsl_rgb(a["hue"], a["sat"], max(4, a["light"] - 14)), 0.3)

        cw = max(0.25, min(1.0, (col[idx]["h"] * H) / 12))
        cv.stroke(top_at, hsl_rgb(a["hue"], a["sat"], max(4, a["light"] - 12)),
                  0.5 * cw)

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
