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


EXPOSURE = 0.022      # weathering depth as a fraction of the frame
EXPOSURE_CAP = 0.8    # ...but never more than this much of the bed itself


def exposure_fn(s, W, H, band):
    """The newest bed is the only one nothing protects, so it alone weathers.
    Biased downward by its own mean: weathering removes material."""
    rng = mulberry32((s["seed"] + 5) & M32)
    octaves = []
    # Weathering depth is set by how long the surface has been exposed, not by
    # how thick the topmost bed happens to be. Thickness is the *limit* — you
    # cannot cut past the bed below — and the frame is the *scale*. Until 0064
    # these two were the other way round, so `H * 0.022` never once bound in
    # sixty-four iterations and the relief shrank with the beds: 12px when 014
    # built it, 5.8px by 0064, heading for 2px. The horizon had gone flat.
    amp = min(H * EXPOSURE, band * EXPOSURE_CAP)
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


COMPETENCE = 0.3
LAG = 150


FAULT_EVERY = 17     # strata between breaks — rarer than folds by design
FAULT_THROW = 0.055  # slip, as a fraction of frame height
FAULT_ZONE = 8       # A fault cuts; it does not bend. Until 0070 the throw was smeared
                     # over 26px — three bed-thicknesses at the current column — so every
                     # bed bent continuously through it and the result was a monocline
                     # that the renderer, the README and INTENT all called a fault. A
                     # cold reader shown only the images said so in one sentence. The
                     # remaining width is fault *drag*: beds really do bend as they are
                     # pulled along the plane, but for a fraction of their thickness,
                     # not three times it. 0047 chose 26 to avoid steep-stroke
                     # artifacts, which stratum 027 had already fixed.
FAULT_RAMP = 3       # strata over which the slip is taken up
FAULT_MAX = 0.22     # most of the frame the accumulated throw may stretch the
                     # column by, before the whole fault field is rescaled
FAULT_APART = 0.12   # least separation between planes, as a fraction of HEIGHT.
                     # 018's invariant: every horizontal length here is measured
                     # against the vertical scale, never the window width, so
                     # nothing changes because a viewer resized. 0081 wrote this
                     # against W and 0082 measured the consequence — 0.27 H
                     # between planes in landscape against 0.089 H in portrait,
                     # three times closer in rock terms for the same section. A
                     # narrow window now simply shows fewer faults, which is what
                     # cropping means.
                     # Drawn uniformly, two planes can land 36px apart in a
                     # 1400px frame — as strata 34 and 51 did — and then read as
                     # one step of their combined throw, which defeats the
                     # horst-and-graben the alternating polarity is for. Same
                     # class as 0055: a random draw that needed a constraint.
FAULT_PLANES = 4     # distinct planes; later slips reactivate an existing one.
                     # Four is now a *judgement*, not a constraint. 0081 wrote
                     # the constraint — five planes could not be separated
                     # reliably — and 0082 dissolved it one iteration later by
                     # measuring separation against H instead of W, which needs
                     # 392px of 896 rather than 672. Five would fit in
                     # landscape. Four is kept because 0081 looked at four and
                     # judged the composition best, and nobody has looked at
                     # five since. Worth trying; do not raise it on arithmetic.
                     # 0048 capped the accumulated *throw* and nobody capped the
                     # *count* — at one new plane every FAULT_EVERY strata the
                     # frame is cut into 21 blocks by 340 strata and the section
                     # stops being a stratigraphy. Real basins do not do that
                     # either: a mature rift has a few master faults that slip
                     # again and again, not fifty small ones. See trace/0080.md.


def fault_episodes(strata, W, H):
    """Rock folds until it cannot, and then it breaks.

    0045 measured the fold's displacement outgrowing the beds it bends. Real
    columns do not accumulate that without limit — past some strain the rock
    faults instead. So every FAULT_EVERY strata one break cuts the record.

    A fault drops the older side; it never lifts it. That is not a cosmetic
    choice. Everything below the break moves together, so their gaps are
    preserved exactly and no bed can be pushed through another — the guarantee
    survives by construction rather than by clamping. The bed straddling the
    event thickens into a wedge on the dropped side, which is what growth
    strata actually do.
    """
    out = []
    planes = []
    # how many planes this window has room for at the piece's own scale
    room = 1 + int(0.64 * W / max(1e-6, FAULT_APART * H))
    limit = max(1, min(FAULT_PLANES, room))
    for n in range(FAULT_EVERY, len(strata) + 1, FAULT_EVERY):
        r = mulberry32((strata[0]["seed"] ^ (n * 0x85EB)) & M32)
        if len(planes) < limit:
            at = 0.18 * W + r() * 0.64 * W      # keep the plane off the edges
            for _ in range(24):                 # ...and clear of its neighbours
                if all(abs(at - q) >= FAULT_APART * H for q in planes):
                    break
                at = 0.18 * W + r() * 0.64 * W
        else:                                   # reactivate an existing plane
            r()
            at = planes[int(r() * len(planes)) % len(planes)]
        throw = FAULT_THROW * H * (0.6 + r() * 0.8)
        # Polarity alternates rather than being drawn independently. Three
        # independent flips at 0055 all landed the same way, and the section
        # read as one staircase tilting the whole record down-leftward — the
        # deep beds on that side pushed off the frame. Independent polarity
        # also lets the net throw random-walk without bound, which is the 0048
        # failure again. Alternating, the throws cancel pairwise and the result
        # is horst and graben: up-thrown and down-thrown blocks side by side,
        # which is what a conjugate fault set actually makes.
        down_right = (len(out) % 2 == 0)
        prof = []
        for x in range(W + 1):
            t = (x - at) / FAULT_ZONE
            t = 0.0 if t < 0 else (1.0 if t > 1 else t)
            k = t * t * (3 - 2 * t)             # same smoothstep the folds use
            prof.append(throw * (k if down_right else 1 - k))
        planes.append(at)
        out.append({"n": n, "samples": prof})

    # Faults accumulate. Measured at 0048: twenty of them stretch the column by
    # 593px in an 820px frame, which is the same unbounded-accumulation failure
    # 0045 found in the fold — built by me, one iteration after diagnosing it.
    # So the fault field obeys the rule the column already obeys: it composes
    # the frame. Scaling is uniform and the profiles stay non-negative, so the
    # never-lift guarantee is untouched.
    if out:
        worst = max(sum(f["samples"][x] for f in out) for x in range(W + 1))
        cap = FAULT_MAX * H
        if worst > cap:
            k = cap / worst
            for f in out:
                f["samples"] = [v * k for v in f["samples"]]
    return out


def fault_offset(faults, i, x):
    """How far stratum i has been dropped at x.

    Taken up over FAULT_RAMP strata rather than all at once — a fault slips
    repeatedly, and dumping a whole throw into one bed inflates it into a
    single shapeless mass. Spread over three, it builds a wedge.

    This is monotone in i by construction: an older bed is always dropped at
    least as far as a younger one, so every gap can only widen. No bed can be
    pushed through its neighbour, whatever the throw.
    """
    total = 0.0
    for f in faults:
        t = (f["n"] - i + 1) / FAULT_RAMP
        if t <= 0:
            continue
        if t >= 1:
            total += f["samples"][x]
        else:
            total += f["samples"][x] * t * t * (3 - 2 * t)
    return total


def competence(s):
    """How stiffly a bed answers the same deformation — fine grain is weak.
    Without this every bed between two episodes took an identical displacement
    and adjacent contacts were parallel copies. See stratum 039."""
    c = mulberry32((s["seed"] + 12) & M32)
    # mapped to the range grain is actually chosen in — see stratum 042
    soft = min(1.0, max(0.0, (s["grain"] - 1.0) / 1.2))
    jitter = (c() - 0.5) * 0.2
    return {"amp": 1 + COMPETENCE * (0.5 - soft + jitter),
            "lag": round(LAG * (soft - 0.5 + jitter))}


def episode_weight(n, i):
    """How much of an episode stratum i has taken up: 1 well below it, 0 for
    beds deposited after it, smooth between."""
    t = (n - i + 1) / FOLD_RAMP
    if t <= 0:
        return 0.0
    if t >= 1:
        return 1.0
    return t * t * (3 - 2 * t)


SWELL = 0.15  # lateral thickness variation, as a fraction of the bed
SURFACE_RELIEF = 0.035  # most relief the sky-facing surface may carry


def boundary_fn(s, W, H, ratio, damp=1.0):
    """Bedding relief plus one long swell of the bed's own: deposition is not
    uniform across a basin, and without it every boundary rides the shared
    fold in parallel and the column reads as even ribbons."""
    rng = mulberry32(s["seed"])
    octaves = []
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
        """Fill between two y=f(x) curves, weighting each row by its coverage.

        The canvas antialiases; this used to round to whole rows, so a band
        thinner than a pixel drew *nothing at all*. 0068 measured the cost:
        grading divides a bed into sixteen tonal steps and 59 of 65 beds are
        thinner than sixteen pixels, so every picture this project has ever
        produced — including every image shown to six outside readers — was
        showing flat bed interiors the artwork does not have.

        This is a change to the mirror only, to make it resemble the artwork.
        The renderer is untouched: the canvas has always done this.
        """
        for x in range(self.w):
            t, b = top(x), bot(x)
            if clip_top is not None:
                t = max(t, clip_top(x))
            if b <= t:
                continue
            y0 = max(0, int(math.floor(t)))
            y1 = min(self.h - 1, int(math.ceil(b)) - 1)
            for y in range(y0, y1 + 1):
                cover = min(b, y + 1.0) - max(t, float(y))
                if cover > 0:
                    self.blend(x, y, rgb, alpha * min(1.0, cover))

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

    def stroke(self, fn, rgb, alpha=1.0, x0=None, x1=None, prev0=None):
        """Draw a y=f(x) curve as a connected line.

        This plotted one pixel per column until stratum 027, which meant any
        contact steeper than 45 degrees came out as a dotted trail — while the
        canvas, which strokes a real path, drew it solid. The mirror was
        misrepresenting every steep boundary in the piece, and twenty-six
        iterations judged the artwork through it. Spanning between consecutive
        samples is what `lineTo` does.
        """
        # `prev0` seeds continuity when a caller draws one curve as several
        # runs. Without it every run begins with no predecessor and cannot span
        # a steep jump, so a near-vertical contact comes out as a dotted trail —
        # which is exactly the bug stratum 027 fixed and 0072 reintroduced by
        # splitting the contact into runs of constant alpha. Caught by looking
        # at a fault plane; no check here would have seen it.
        prev = prev0
        for x in range(0 if x0 is None else max(0, x0),
                       self.w if x1 is None else min(self.w, x1 + 1)):
            yf = fn(x)
            if prev is None or abs(yf - prev) <= 1.0:
                # split the line between the two rows it falls between, as the
                # canvas does. 0069 gave `band` coverage weighting and left this
                # rounding to whole rows, so contacts stayed hard-edged while
                # everything around them went smooth — a cold reader at 0070
                # found the seam at 8x and called the steep limb "crunchy".
                top = yf - 0.5
                y0 = int(math.floor(top))
                f = top - y0
                self.blend(x, y0, rgb, alpha * (1.0 - f))
                self.blend(x, y0 + 1, rgb, alpha * f)
            else:
                lo, hi = (prev, yf) if prev < yf else (yf, prev)
                for yy in range(int(math.floor(lo)), int(math.ceil(hi))):
                    self.blend(x, yy, rgb, alpha)
            prev = yf

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
    faults = fault_episodes(strata, W, H)
    floor_at = [sum(e["samples"][x] for e in episodes) for x in range(W + 1)]
    # measured, not bounded — see the note in the renderer
    sink = max(0.0, -min(floor_at)) if floor_at else 0.0

    # boundaries sampled per pixel, then clamped so no bed can be punched
    # through by the relief of a thicker, rougher one beneath it
    def fn_of(arr):
        return lambda x: arr[0 if x < 0 else (W if x > W else int(round(x)))]

    # the base carries the same drop as the oldest bed, so the whole faulted
    # block moves as one and nothing below can be crossed
    lower_arr = [H + sink + floor_at[x] + fault_offset(faults, 1, x)
                 for x in range(W + 1)]
    lower_at = fn_of(lower_arr)
    prev = None

    for idx, s in enumerate(strata):
        cum += col[idx]["h"]
        base = H * (1 - cum) + sink
        # only the sky-facing surface is bounded in frame terms; buried
        # contacts keep their full relief — see stratum 029
        bed_relief = (0.87 * s["roughness"] * s["thickness"] * H * col[idx]["ratio"]
                      + s["thickness"] * col[idx]["ratio"] * H * SWELL)
        damp = (min(1.0, (H * SURFACE_RELIEF) / max(1e-6, bed_relief))
                if idx == len(strata) - 1 else 1.0)
        noise = boundary_fn(s, W, H, col[idx]["ratio"], damp)
        a = altered(s, col[idx]["burial"], target)
        weights = [episode_weight(e["n"], idx + 1) for e in episodes]
        comp = competence(s)

        def warped(x, comp=comp, weights=weights):
            sx = 0 if x + comp["lag"] < 0 else (W if x + comp["lag"] > W else x + comp["lag"])
            return sum(e["samples"][sx] * w * comp["amp"]
                       for e, w in zip(episodes, weights))
        min_gap = max(1.2, col[idx]["h"] * H * 0.22)
        weather = (exposure_fn(s, W, H, col[idx]["h"] * H)
                   if idx == len(strata) - 1 else None)
        drop = [fault_offset(faults, idx + 1, x) for x in range(W + 1)]
        arr = [min(base + noise(x) + warped(x) + drop[x]
                   + (weather(x) if weather else 0.0),
                   lower_arr[x] - min_gap)
               for x in range(W + 1)]
        top_at = fn_of(arr)

        cv.band(top_at, lower_at, hsl_rgb(a["hue"], a["sat"], a["light"]))

        # grading: dark at the base, lightening upward, in slices that follow
        # the bed's own boundaries. Tone only — the audit at 0049 found the
        # "coarse at the base, fine upward" this used to claim was never
        # implemented, and 048 removed the grain that might have carried it.
        # finer steps, each boundary wobbling on its own so quantisation cannot
        # line up into parallel contours across the bed — see stratum 017
        # The floor is set by tone, not by pixels. Grading spans 23-31 RGB
        # base to top across the palette, so fewer than ~16 steps puts each
        # step above the ~2 RGB threshold where banding becomes visible — and
        # the old floor of 4 did exactly that. `h*H/2.5` was written when beds
        # were 40px and gave 16 slices; at today's 10.9px median it bottomed
        # out on the floor and grading became a four-band staircase inside
        # every bed. Since 048 removed grain, mottling and clasts, this is the
        # only interior signal left, and a gradient is the only kind of
        # interior that survives being downsampled. See trace/0057.md.
        slices = max(16, min(32, round(col[idx]["h"] * H / 2.5)))
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
            # The profile is not linear, because settling is not. A graded bed is
        # mostly fine sediment above a thin coarse base, so the tone should hold
        # through the upper bed and fall away near the contact. Centred on zero
        # (the 2/3) so the curve does not shift every bed's mean lightness — an
        # uncentred sqrt profile darkens the whole column by 1.5 units, which is
        # the bias 0056 audited for. See trace/0059.md.
            dl = GRADE_RANGE * (2 / 3 - 2 * ((k + 0.5) / slices) ** 2)
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

            # a thin clean dark zone — a different kind of contact, not a
            # sharper line; see stratum 040
            cv.band(scour_top, lower_at,
                    hsl_rgb(a["hue"], max(3, a["sat"] - 8), max(3, a["light"] - 18)))
            cv.stroke(lower_at,
                      hsl_rgb(a["hue"], a["sat"], max(3, a["light"] - 24)), 0.75)

        # lamination: internal partings, one per distinct piece of work,
        # erased by burial once the bed is thinner than a few pixels
        # Gate and spacing were written for 40px beds. At today's 10.5px median
        # no bed passed >= 12 at viewport size, so laminae — the one mechanism
        # carrying iteration-level meaning into the picture, and the one 0050
        # deliberately spared *for* that meaning — drew literally nothing where
        # anyone looks: ablating it at 760x460 changed zero pixels. The divisor
        # was as bad: it allowed 2 partings, so a laminae:4 bed and a laminae:3
        # bed drew the same single line. Now 22 of 46 beds draw one and 18 draw
        # the true count. See trace/0058.md.
        if s.get("laminae", 0) > 1 and col[idx]["h"] * H >= 6:
            # quieter and jittered off the grid — see stratum 017
            # the view draws only as many partings as the bed has room for;
            # the stored count stays honest — see stratum 032
            lm = mulberry32((s["seed"] + 8) & M32)
            room = max(2, int((col[idx]["h"] * H) / 2.2))
            drawn = min(s["laminae"], room)
            for k in range(1, drawn):
                f = (k + (lm() - 0.5) * 0.45) / drawn
                cv.stroke((lambda f: lambda x: top_at(x) + (lower_at(x) - top_at(x)) * f)(f),
                          hsl_rgb(a["hue"], a["sat"], max(3, a["light"] - 9)),
                          0.16 + lm() * 0.1)

        # Grain speckle, mottling and clasts were removed at stratum 048.
        # Three texture systems built for a column with thick beds; the
        # deposition rule made beds permanently thin, and by 0050 they moved
        # 0.01%, 0.25% and 0.18% of pixels — nothing at viewport size. The
        # `grain` field survives: it decides how stiffly a bed folds.
        # See trace/0050.md and trace/0049-subtraction.md.
        if s.get("hiatusDays") and prev:
            band = col[idx]["h"] * H
            span = min(band * 0.28, band * (0.06 + s["hiatusDays"] * 0.018),
                       H * 0.03)
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

        # A contact marks where one bed meets the next. Where this bed has been
        # squeezed to its seam there is no second colour, so a full-strength
        # line is a stain rather than a boundary — a cold reader at 0070 found
        # them "floating with nothing on either side", and 0071 traced it to
        # the stroke weight coming from the bed's *average* height while
        # pinching happens per column. The contact now fades with the room the
        # bed actually has at each x, in runs of constant alpha so the canvas
        # can draw the same thing with one strokeStyle per path.
        cw = max(0.25, min(1.0, (col[idx]["h"] * H) / 12))
        crgb = hsl_rgb(a["hue"], a["sat"], max(4, a["light"] - 12))
        lv = []
        for x in range(W + 1):
            t = (lower_arr[x] - arr[x] - min_gap) / max(1e-6, min_gap * 1.6)
            t = 0.0 if t < 0 else (1.0 if t > 1 else t)
            lv.append(int(t * t * (3 - 2 * t) * 8 + 0.5))
        run = 0
        for x in range(1, W + 2):
            if x > W or lv[x] != lv[run]:
                if lv[run] > 0:
                    cv.stroke(top_at, crgb, 0.5 * cw * lv[run] / 8, run, x - 1,
                              top_at(run - 1) if run > 0 else None)
                run = x

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
