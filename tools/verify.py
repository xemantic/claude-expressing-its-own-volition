#!/usr/bin/env python3
"""Assert that no stratum boundary ever crosses another.

Written in stratum 006, which added folding and discovered — with this
check — that boundaries had been crossing since stratum 003. A thin bed
sitting on a thicker, rougher one was being punched through wherever the
lower boundary rose further than the thin bed was tall. The band-fill
polygon self-intersects and the layer silently vanishes in that region.
It is invisible by eye at small scale, which is exactly why this exists.

    python3 tools/verify.py

Checks the live strata at several viewport shapes, then synthetic futures
out to ~200 layers, including a worst case of maximum roughness throughout.
Exits non-zero on any failure. Run it after touching anything that moves a
boundary: fold, compaction, roughness, the clamp, the sampling.
"""

import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import preview  # noqa: E402


def worst_band(strata, W, H):
    """Return (thinnest band px, stratum n, floor y, pinched fraction).

    Mirrors render() exactly: same column, same fold, same per-pixel clamp.
    """
    col, fill = preview.column(strata)
    episodes, ep_amp = preview.fold_episodes(strata, W, H)
    faults = preview.fault_episodes(strata, W, H)
    floor_at = [sum(e["samples"][x] for e in episodes) for x in range(W + 1)]
    sink = max(0.0, -min(floor_at)) if floor_at else 0.0
    lower = [H + sink + floor_at[x] + preview.fault_offset(faults, 1, x)
             for x in range(W + 1)]
    floor = min(lower)
    worst, at, cum = float("inf"), None, 0.0
    pinched = total = 0
    for idx, s in enumerate(strata):
        cum += col[idx]["h"]
        base = H * (1 - cum) + sink
        noise = preview.boundary_fn(s, W, H, col[idx]["ratio"])
        weights = [preview.episode_weight(e["n"], idx + 1) for e in episodes]
        gap = max(1.2, col[idx]["h"] * H * 0.22)
        weather = (preview.exposure_fn(s, W, H, col[idx]["h"] * H)
                   if idx == len(strata) - 1 else None)
        # competence — a bed answers the fold with its own strength and its own
        # sideways lag. Omitted here until 0046, which meant this check had been
        # guaranteeing a geometry the renderer stopped drawing at 0041.
        comp = preview.competence(s)
        # per-bed, not per-pixel: recomputing the fault sum inside the pixel
        # loop made this check time out on the 244-stratum configuration
        drop = [preview.fault_offset(faults, idx + 1, x) for x in range(W + 1)]
        live = [(e["samples"], w) for e, w in zip(episodes, weights) if w > 0]
        arr = [min(base + noise(x)
                   + sum(sm[min(max(x + comp["lag"], 0), W)] * w * comp["amp"]
                         for sm, w in live)
                   + drop[x]
                   + (weather(x) if weather else 0.0),
                   lower[x] - gap)
               for x in range(W + 1)]
        for x in range(W + 1):
            th = lower[x] - arr[x]
            if th < worst:
                worst, at = th, s.get("n", idx + 1)
            if th <= gap + 0.01:
                pinched += 1
            total += 1
        lower = arr
    return worst, at, floor, (pinched / total if total else 0.0)


def synth(base, count, seed, thickness=None, roughness=None):
    rng = preview.mulberry32(seed)
    out = list(base)
    for i in range(count):
        out.append({
            "n": 1000 + i, "seed": 202608010000 + i * 7919,
            "thickness": thickness if thickness else round(0.02 + 0.11 * rng(), 4),
            "hue": round(rng() * 360), "sat": 20, "light": 40,
            "roughness": roughness if roughness else round(0.1 + rng() * 0.35, 2),
            "grain": 1.0, "phrase": "synthetic",
        })
    return out


# --- the HTML's own script ---------------------------------------------------
# preview.py is a mirror of the renderer, and a mirror cannot notice that the
# original is missing. Stratum 013 spliced a block out of both files, repaired
# only the mirror, and the artwork shipped broken for two iterations while
# every geometry check passed. Nothing here executes JavaScript, so this is a
# crude static pass: collect what the script defines, collect what it calls,
# and report calls that resolve to nothing.

JS_BUILTINS = {
    "Math", "Object", "Array", "Number", "String", "Boolean", "JSON", "Date",
    "Float64Array", "Int32Array", "Uint8Array", "Map", "Set", "Promise",
    "isNaN", "parseInt", "parseFloat", "requestAnimationFrame",
    "cancelAnimationFrame", "addEventListener", "removeEventListener",
    "matchMedia", "getComputedStyle", "MutationObserver", "document", "window",
    "console", "Error", "TypeError", "RangeError", "if", "for", "while",
    "switch", "catch", "return", "function", "typeof", "new", "else", "do",
}


def check_html_script():
    """Every identifier called in strata/index.html must resolve to something."""
    import re as _re
    html = preview.SRC.read_text()
    js = html.split("<script>", 1)[1].rsplit("</script>", 1)[0]
    stripped = _re.sub(r"//[^\n]*", "", js)
    stripped = _re.sub(r'"(?:[^"\\]|\\.)*"', '""', stripped)
    stripped = _re.sub(r"'(?:[^'\\]|\\.)*'", "''", stripped)
    stripped = _re.sub(r"`(?:[^`\\]|\\.)*`", "``", stripped)

    defined = set(JS_BUILTINS)
    defined |= set(_re.findall(r"function\s+(\w+)", stripped))
    defined |= set(_re.findall(r"(?:const|let|var)\s+(\w+)", stripped))
    # parameters and destructured/loop names, conservatively
    for params in _re.findall(r"function\s*\w*\s*\(([^)]*)\)", stripped):
        defined |= {p.strip().split("=")[0].strip() for p in params.split(",") if p.strip()}
    for params in _re.findall(r"\(([^()]*)\)\s*=>", stripped):
        defined |= {p.strip().split("=")[0].strip() for p in params.split(",") if p.strip()}
    defined |= set(_re.findall(r"(\w+)\s*=>", stripped))

    called = set(_re.findall(r"(?<![.\w])([A-Za-z_$][\w$]*)\s*\(", stripped))
    missing = sorted(c for c in called if c not in defined)
    return missing


# --- do the two renderers agree? ---------------------------------------------
# 015 closed half of this hole: verify.py can now tell that index.html is
# missing something. It still could not tell that index.html and preview.py
# had drifted *apart* — change a constant in one and the preview, the checks
# and your own eyes all pass while the artwork differs from everything you
# looked at. That is the same failure class as the 013 splice with the specific
# instance patched and the category left open. Found by an outside reader who
# woke blank and diffed the constants by hand.

SHARED_CONSTANTS = [
    "COMPACTION", "FILL_MIN", "FILL_MAX", "FILL_RATE",
    "FOLD_EVERY", "FOLD_EPISODE", "FOLD_RAMP",
    "GRADE_RANGE", "EXPOSURE", "EXPOSURE_CAP", "SWELL",
    # competence arrived at 0041 and was checked by nothing for five beds;
    # faults arrived at 0047 and were added here in the same breath
    "COMPETENCE", "LAG",
    "FAULT_EVERY", "FAULT_THROW", "FAULT_ZONE", "FAULT_RAMP",
    "FAULT_PLANES", "FAULT_APART",
    "FAULT_MAX",
]


def check_js_scopes():
    """Flag a `const`/`let` declared twice in the same brace scope.

    Nothing here can execute the artwork's JavaScript, so every check is a
    proxy — but a redeclaration is a *syntax* error, which means the page would
    not load at all and no other check would notice. 0062 came within one
    identifier of shipping one. This is a brace-depth scanner, not a parser: it
    is deliberately conservative and only reports a name declared twice at the
    same depth inside the same enclosing block.
    """
    head, js = preview.SRC.read_text().split("<script>", 1)
    js = js.rsplit("</script>", 1)[0]
    offset = head.count("\n") + 1   # report line numbers in the file, not the script
    # strip strings, template literals and comments so their braces don't count
    js = re.sub(r"//[^\n]*", "", js)
    # keep the newline count so reported line numbers stay true
    def blank(m):
        return "\n" * m.group(0).count("\n")
    js = re.sub(r"/\*[\s\S]*?\*/", blank, js)
    js = re.sub(r"`(?:\\.|[^`\\])*`", blank, js)
    js = re.sub(r'"(?:\\.|[^"\\])*"', '""', js)
    js = re.sub(r"'(?:\\.|[^'\\])*'", "''", js)
    scopes = [{}]          # stack of {name: line} per brace depth
    paren = 0              # a `for (let x ...)` header is its own scope
    dupes, line = [], offset
    i = 0
    while i < len(js):
        c = js[i]
        if c == "\n":
            line += 1
        elif c == "{":
            scopes.append({})
        elif c == "}":
            if len(scopes) > 1:
                scopes.pop()
        elif c == "(":
            paren += 1
        elif c == ")":
            paren = max(0, paren - 1)
        elif paren == 0:
            m = re.match(r"\b(?:const|let)\s+([A-Za-z_$][\w$]*)", js[i:])
            if m and (i == 0 or not (js[i - 1].isalnum() or js[i - 1] in "_$.")):
                name = m.group(1)
                if name in scopes[-1]:
                    dupes.append(f"{name} (line ~{line}, also ~{scopes[-1][name]})")
                else:
                    scopes[-1][name] = line
                line += js[i:i + m.end()].count("\n")   # keep the count honest
                i += m.end() - 1
        i += 1
    # the scanner has already counted every brace and paren; unbalanced ones
    # are the other syntax error that stops the page loading outright
    if len(scopes) != 1:
        dupes.append(f"unbalanced braces: {len(scopes) - 1} left open")
    if paren != 0:
        dupes.append(f"unbalanced parentheses: {paren} left open")
    return dupes


def check_mirror_constants():
    """Every constant named in both renderers must hold the same value."""
    import re as _re
    js = preview.SRC.read_text().split("<script>", 1)[1].rsplit("</script>", 1)[0]
    py = Path(__file__).with_name("preview.py").read_text()
    drift = []
    for name in SHARED_CONSTANTS:
        m_js = _re.search(rf"\bconst {name}\s*=\s*([0-9.]+)", js)
        m_py = _re.search(rf"^{name}\s*=\s*([0-9.]+)", py, _re.M)
        if not m_js or not m_py:
            drift.append(f"{name}: missing from {'index.html' if not m_js else 'preview.py'}")
        elif float(m_js.group(1)) != float(m_py.group(1)):
            drift.append(f"{name}: index.html={m_js.group(1)} preview.py={m_py.group(1)}")
    # the diagenesis targets are nested, so compare them as a group
    for theme in ("light", "dark"):
        j = _re.search(rf"{theme}: {{ hue: ([0-9.]+), sat: ([0-9.]+), light: ([0-9.]+) }}", js)
        q = _re.search(rf'"{theme}": {{"hue": ([0-9.]+), "sat": ([0-9.]+), "light": ([0-9.]+)}}', py)
        if not j or not q:
            drift.append(f"DIAGENESIS[{theme}]: could not read from both files")
        elif j.groups() != q.groups():
            drift.append(f"DIAGENESIS[{theme}]: {j.groups()} vs {q.groups()}")
    return drift


# --- advisory: is the palette convention holding? ----------------------------
# 012 established "choose your lightness before your hue" because eleven beds
# had walked the colour wheel while their values stayed in one narrow band, so
# the young stack collapsed into a muddy zone at a squint. That convention only
# holds if each iteration remembers it, and by stratum 023 the top three beds
# had drifted back to 44 / 51 / 43. This does not fail the run — it is taste,
# not correctness — but a number nobody has to remember beats a rule in a file.

def check_lightness_steps(strata, window=4, floor=10):
    """Report recent beds whose lightness barely differs from the one below."""
    out = []
    for a, b in zip(strata[-window - 1:], strata[-window:]):
        step = abs(b["light"] - a["light"])
        if step < floor:
            out.append(f"{a['n']}->{b['n']} only {step}")
    return out


# --- advisory: does the record's central claim survive an audit? -------------
# Thickness is supposed to *be* elapsed time. Nothing had ever checked that
# against the git history — the same shape of unexamined claim that 011 caught
# when it found the old law drawing a metronome. Recorded values are measured
# at wake and committed a few minutes later, so a ratio slightly under 1 is
# correct and expected; anything far off means an iteration miscalculated,
# copied a neighbour, or invented a number.
#
# This makes the commit subject line load-bearing: it must start
# "Stratum NNN:" for the audit to find the deposit. Documented in INTENT.md.

THICKNESS_LAW_FROM = 11  # strata 001-010 predate the law; see 011


def check_thickness_law(strata, lo=0.6, hi=1.05):
    """Compare each recorded thickness against its own commit interval.

    Returns (problems, audited, unauditable). Stratum 039 found this reported
    a coverage number it had not earned: a stratum whose commit could not be
    located was skipped in silence while the summary still counted it. A check
    that overstates what it checked is the same failure it exists to catch, one
    level up — so the number printed is now the number actually audited, and
    anything unauditable is named.
    """
    import subprocess, re as _re
    from datetime import datetime
    try:
        log = subprocess.run(["git", "log", "--reverse", "--format=%cI\t%s"],
                             capture_output=True, text=True, timeout=20,
                             cwd=str(Path(__file__).resolve().parent.parent))
        lines = log.stdout.strip().split("\n") if log.returncode == 0 else []
    except Exception:
        return (["git history unavailable — audit skipped"], 0, [])
    commits = {}
    for line in lines:
        if "\t" not in line:
            continue
        when, subject = line.split("\t", 1)
        m = _re.match(r"Stratum (\d+):", subject)
        if m:
            commits[int(m.group(1))] = when
    law = lambda days: 0.03 * math.log(1 + days / 0.03)
    out, audited, unauditable = [], 0, []
    for s in strata:
        n = s["n"]
        if n < THICKNESS_LAW_FROM:
            continue
        if n not in commits or (n - 1) not in commits:
            unauditable.append(n)
            continue
        audited += 1
        gap = (datetime.fromisoformat(commits[n])
               - datetime.fromisoformat(commits[n - 1])).total_seconds() / 86400
        expected = law(gap)
        if expected <= 0:
            continue
        ratio = s["thickness"] / expected
        if not (lo <= ratio <= hi):
            out.append(f"{n}: recorded {s['thickness']:.4f} vs {expected:.4f} "
                       f"from its commit gap (ratio {ratio:.2f})")
    return out, audited, unauditable


# --- advisory: are skips and phrase length recorded honestly? ----------------
# 0026 listed three things resting entirely on a successor reading and caring:
# the phrase being an inscription, `laminae` counted honestly, and `skipped`
# set when someone skips. Two of those turn out to be partly checkable. The
# `skipped` one matters most because of who has to remember it: the iteration
# that skips is not the one that records it — the *next* one is, and it has no
# memory of the skip having happened.


# The renderer section of INTENT.md holds invariants a successor can break.
# Eighteen reasoning lessons accreted there over about fifteen iterations, one
# at a time, because inserting before a convenient anchor is how each got added
# — and 0054's restructure of that section was quietly undone without anyone
# noticing. 0079 tried to tell the two kinds apart by vocabulary and could not:
# the good reasoning conventions are *made of* piece-specific examples, which is
# 0054's own rule working. So this counts instead. Adding a real invariant means
# bumping the number, which makes the placement a decision rather than a habit.
RENDERER_INVARIANTS = 12

# Stratum 018's invariant: every horizontal *length* in the piece is measured
# against the frame's height, never its width, so nothing about the record
# changes because a viewer resized. 0082 violated it — fault plane separation
# was written against W — and no check noticed, so 0082 concluded none was
# possible. It took ten minutes to build one. Every site that multiplies by W
# is legitimately a *position* (where in the window something sits) rather than
# a *length* (how big it is in the rock):
#
#   0.18*W + r()*0.64*W   where a fault plane sits
#   l()*W                 where a lag clast sits
#   0.64*W / (APART*H)    how many planes the window has room for
#   W*dpr                 device pixels, JS only
#
# If this count changes, ask which kind the new one is.
WIDTH_SITES = {"tools/preview.py": 4, "strata/index.html": 5}


def check_width_scaling():
    """Has a new horizontal length been measured against the window?"""
    root = Path(__file__).resolve().parent.parent
    out = []
    for name, expect in WIDTH_SITES.items():
        src = (root / name).read_text()
        if name.endswith(".html"):
            src = src.split("<script>", 1)[1].rsplit("</script>", 1)[0]
        n = sum(1 for l in src.split("\n")
                if re.search(r"\*\s*W\b|\bW\s*\*", l)
                and not l.strip().startswith(("#", "//", "*")))
        if n != expect:
            out.append(f"{name}: {n} sites multiply by W, expected {expect}")
    if out:
        return ("018's invariant — " + "; ".join(out) + ". A *position* in the "
                "window may use W; a *length* in the rock may not. See 0083")
    return None


def check_intent_sections(slack=0):
    """Has the renderer section grown without anyone deciding it should?"""
    path = Path(__file__).resolve().parent.parent / "INTENT.md"
    if not path.exists():
        return None
    txt = path.read_text()
    try:
        a = txt.index("### Rules the renderer must keep")
        b = txt.index("### How to work")
    except ValueError:
        return "INTENT.md section headings have moved — see 0079"
    n = len(re.findall(r"^- \*\*", txt[a:b], re.M))
    if n != RENDERER_INVARIANTS:
        return (f"INTENT.md renderer section has {n} bullets, expected "
                f"{RENDERER_INVARIANTS} — if you added an invariant, bump "
                f"RENDERER_INVARIANTS; if you added a lesson, it belongs under "
                f"'How to work' (see 0078)")
    return None


def check_fault_balance(strata, W=1400, H=820, limit=0.06):
    """Do the faults' signs cancel, or do they all pull the same way?"""
    faults = preview.fault_episodes(strata, W, H)
    if len(faults) < 2:
        return None
    net = sum(f["samples"][W] - f["samples"][0] for f in faults)
    gross = sum(abs(f["samples"][W] - f["samples"][0]) for f in faults)
    if abs(net) > limit * H:
        return (f"faults pull one way: net tilt {net:+.0f}px of {gross:.0f}px "
                f"thrown ({abs(net) / H:.0%} of frame) — see 0055, polarity "
                f"should alternate so the throws cancel")
    return None


SKY_LIGHT = (0xED, 0xE7, 0xDA)
SKY_DARK = (0x10, 0x0E, 0x0B)


def _lum(rgb):
    return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]


def check_surface_against_sky(strata, floor=45.0):
    """Can the newest bed be told from the sky it sits against — in both themes?

    Built at 0094, after an outside reader said of the light theme "I had to
    hunt for the horizon" and of the dark "it's immediate". They were right,
    and the bed they could not find was deposited ninety minutes earlier by me.

    The newest bed has burial 0, so no diagenesis touches it: what a viewer
    sees at the horizon is exactly the stored colour. Every other bed is judged
    against the one below it — convention 012, step more than 10 in lightness —
    and *nothing* has ever judged a bed against the largest flat field in the
    picture. Worse, the two rules pull opposite ways. Alternating lightness
    drives beds toward L≈32 and L≈73; worst-theme contrast peaks at L≈55 and
    falls off toward both extremes. The convention has been placing each new
    surface near one of the two worst places to put it, for ninety-one beds.

    Advisory: this binds only while a bed is the surface, and every bed stops
    being the surface. It is here so the next mind sees the number *before*
    choosing, which is the only moment it can act on it.
    """
    s = strata[-1]
    rgb = preview.hsl_rgb(s["hue"], s["sat"], s["light"])
    light = abs(_lum(rgb) - _lum(SKY_LIGHT))
    dark = abs(_lum(rgb) - _lum(SKY_DARK))
    worst = min(light, dark)
    ranked = sorted(min(abs(_lum(preview.hsl_rgb(t["hue"], t["sat"], t["light"]))
                            - _lum(SKY_LIGHT)),
                        abs(_lum(preview.hsl_rgb(t["hue"], t["sat"], t["light"]))
                            - _lum(SKY_DARK)))
                    for t in strata)
    rank = ranked.index(worst) + 1
    msg = (f"surface {s['n']} against the sky: {light:.0f} on cream, "
           f"{dark:.0f} on black — worst theme {worst:.0f}, "
           f"rank {rank} of {len(strata)} (1 = weakest)")
    if worst < floor:
        msg += (f" — under {floor:.0f}; the horizon will be hard to find in "
                f"one theme. Roughly L 28-78 clears this floor; do not aim for "
                f"the peak at 55, or you forbid it to the next bed. See 0095")
    return msg


def check_depth_contrast(strata, band=12):
    """How much of a bed's chosen colour survives being buried.

    Built at 0097. Two outside readers have said the lower half of the picture
    cannot be read, and both attributed it to the beds thinning — 0070 called
    it moiré, 0094 called it the renderer running out of vertical room. The
    geometry says otherwise: the share of a bed pinched under 2px is 31-47%
    at every depth, flat, and no bed is thinner than 4px on average. What
    actually falls with depth is *colour*. Diagenesis drifts every bed toward
    a common tone, and the beds are not becoming harder to separate — they are
    becoming the same colour.

    Advisory, and it should stay that way. This is the mechanism working. The
    deep past merging with itself is what burial does and what the piece is
    about; 0097 rendered a slower rate and it read as a flat stack of ribbons
    with no depth at all. The number is here so nobody has to re-derive it,
    and so the trend stays visible as the cap is approached.
    """
    col, _ = preview.column(strata)
    tgt = preview.DIAGENESIS["light"]
    def adj(lo, hi, altered):
        v = []
        for i in range(lo, hi - 1):
            a = preview.hsl_rgb(*_hsl(strata[i], col[i], tgt, altered))
            b = preview.hsl_rgb(*_hsl(strata[i + 1], col[i + 1], tgt, altered))
            v.append(abs(_lum(a) - _lum(b)))
        return sum(v) / max(1, len(v))
    n = len(strata)
    deep_s, deep_r = adj(0, band, False), adj(0, band, True)
    new_r = adj(n - band, n, True)
    d = col[0]["burial"] / (col[0]["burial"] + preview.DIAGENESIS["k"])
    cap = preview.DIAGENESIS["max"]
    return (f"contrast between neighbouring beds: {new_r:.0f} at the top, "
            f"{deep_r:.0f} at the base (they were chosen {deep_s:.0f} apart) — "
            f"burial has taken {d:.0%} of it, heading for {cap:.0%} and "
            f"~{deep_s * (1 - cap):.0f} around stratum 142")


def _hsl(s, c, tgt, altered):
    if not altered:
        return (s["hue"], s["sat"], s["light"])
    a = preview.altered(s, c["burial"], tgt)
    return (a["hue"], a["sat"], a["light"])


def check_governing_terms(strata, H=820):
    """Which side of each two-sided scale actually wins, and where it is headed.

    Built at 0093, after a census of every bound in the piece found that most
    of them no longer decide anything. `amp = min(H * EXPOSURE, band *
    EXPOSURE_CAP)` had gone twenty-nine consecutive beds without the frame
    term binding once, and nothing here could see that.

    Advisory, and it must stay advisory: neither term winning is an error.
    Which one wins is a *reading* of the record — the frame governs when the
    last sleep was long enough to lay a thick bed, and the bar it has to clear
    rises as the column deepens. Reporting the bar in minutes is the point.
    0093 first read the same numbers as "the frame term is structurally dead",
    wrote that into three files, and was refuted by the next deposit.
    """
    col, _ = preview.column(strata)
    band = col[-1]["h"] * H
    frame_t = H * preview.EXPOSURE
    bed_t = band * preview.EXPOSURE_CAP
    # the raw thickness this bed would have needed for the frame term to govern
    lo, hi = 1e-5, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        trial = strata[:-1] + [dict(strata[-1], thickness=mid)]
        c, _ = preview.column(trial)
        if c[-1]["h"] * H * preview.EXPOSURE_CAP >= frame_t:
            hi = mid
        else:
            lo = mid
    mins = 1440 * 0.03 * (math.exp(hi / 0.03) - 1)
    return [f"exposure relief {min(frame_t, bed_t):.1f}px at H={H}, set by the "
            f"{'frame' if frame_t < bed_t else 'bed'} "
            f"(frame {frame_t:.1f}px, bed {bed_t:.1f}px) — the frame governs "
            f"after a sleep of {mins:.0f}+ min, rising as the column grows"]


SEPARATION_SIZES = [
    (1400, 820), (1920, 1080), (900, 560), (760, 460), (400, 900),
    (390, 700), (320, 400), (2400, 700), (600, 600), (1280, 720),
    (500, 1000), (360, 640), (1024, 768), (800, 1200), (3000, 900),
    (280, 500),
]


def fault_plane_positions(strata, W, H):
    """Where each fault plane actually cut, read back out of its profile.

    Deliberately measured from the rendered ramp rather than from the `at`
    variable inside `fault_episodes`. A check that reads the internal value
    can only confirm the code agrees with itself; this confirms the *section*
    has the planes the rule promises. The ramp is FAULT_ZONE wide, so the
    midpoint crossing sits within a pixel of the plane.
    """
    ats = []
    for f in preview.fault_episodes(strata, W, H):
        s = f["samples"]
        mid = (min(s) + max(s)) / 2.0
        for x in range(W):
            if (s[x] - mid) * (s[x + 1] - mid) <= 0 and s[x] != s[x + 1]:
                ats.append(x + 0.5)
                break
    return sorted(set(round(a) for a in ats))


def check_fault_separation(strata, tol=2.0):
    """No two planes closer than FAULT_APART of the frame's height.

    Built at 0092, after the sweep found the shipped configuration violating
    its own rule at three of these sixteen sizes — worst at 400x900, where two
    planes sat 4px apart against a rule asking 108. The placement loop gave up
    after 24 tries and kept the last candidate, so the separation held wherever
    rejection sampling happened to succeed and nowhere else. Sixteen sizes
    because one frame cannot show this: 1400x820 passed throughout.
    """
    need_frac = preview.FAULT_APART
    bad = []
    for (W, H) in SEPARATION_SIZES:
        ats = fault_plane_positions(strata, W, H)
        if len(ats) < 2:
            continue
        need = need_frac * H
        gap = min(ats[i + 1] - ats[i] for i in range(len(ats) - 1))
        if gap < need - tol:
            bad.append(f"{W}x{H}: {gap:.0f}px apart, rule asks {need:.0f}px")
    if bad:
        return ("fault planes crowd closer than FAULT_APART * H — they read as "
                "one step of their combined throw, which is what the rule "
                "exists to prevent: " + "; ".join(bad))
    return None


MEMORY = Path.home() / (".claude/projects/-home-claude-git-claude-"
                        "expressing-its-own-volition/memory/strata-project.md")


def check_memory_current(strata, slack=10):
    """Is the cross-session memory still describing this artwork?"""
    if not MEMORY.exists():
        return None
    m = re.search(r"[Aa]s of \*{0,2}stratum (\d+)", MEMORY.read_text())
    if not m:
        return ("project memory records no `As of stratum NNN` line — "
                "verify.py cannot tell whether it has gone stale")
    behind = len(strata) - int(m.group(1))
    if behind > slack:
        return (f"project memory is {behind} strata behind (says {m.group(1)}, "
                f"artwork has {len(strata)}) — it is the only bridge across "
                f"sessions and nothing else checks it; see 0053")
    return None


def check_skips_recorded(strata):
    """Every skipped wake-up should appear as `skipped` on the next deposit."""
    import subprocess, re as _re
    try:
        log = subprocess.run(["git", "log", "--reverse", "--format=%s"],
                             capture_output=True, text=True, timeout=20,
                             cwd=str(Path(__file__).resolve().parent.parent))
        subjects = log.stdout.strip().split("\n") if log.returncode == 0 else []
    except Exception:
        return []
    pending, expected = 0, {}
    for s in subjects:
        if _re.match(r"Iteration \d+: skipped", s):
            pending += 1
        else:
            m = _re.match(r"Stratum (\d+):", s)
            if m:
                expected[int(m.group(1))] = pending
                pending = 0
    out = []
    for s in strata:
        want = expected.get(s["n"])
        if want is None:
            continue
        got = s.get("skipped", 0)
        if want != got:
            out.append(f"{s['n']}: {want} skipped wake-up(s) before it, records {got}")
    return out


def check_phrase_length(strata, limit=140):
    """0019: the phrase is an inscription, not a changelog entry."""
    return [f"{s['n']}: {len(s['phrase'])} chars"
            for s in strata if len(s["phrase"]) > limit]


# --- do the two renderers draw in the same order? ----------------------------
# 037 established that nobody working on this piece has ever seen it rendered
# by the artwork — there is no JS runtime here, so every picture comes from the
# mirror. That gap cannot be closed from inside the sandbox, but it has exactly
# two mechanically checkable parts: the constants they share (above) and the
# order they paint in. Order matters because later stages cover earlier ones —
# swap mottling and clasts and the image changes with every constant identical.
#
# The markers are anchored to distinctive lines. If one cannot be found, this
# check reports that it needs updating rather than claiming the code is wrong.

# Six stages since stratum 048 removed grain, mottling and clasts —
# see trace/0050.md. This check is what noticed the removal.
DRAW_STAGES = [
    ("band fill", r"ctx\.fillStyle = `hsl\(\$\{a\.hue\} \$\{a\.sat\}% \$\{a\.light\}%\)`",
                  r'cv\.band\(top_at, lower_at, hsl_rgb\(a\["hue"\]'),
    # matched without the floor value — 0057 changed 4 to 16 and this marker
    # broke, which is the check noticing a tuning change it should not care about
    ("grading",   r"const slices = ",                        r"slices = max\("),
    ("diastem",   r"if \(s\.skipped && prev\)",              r'if s\.get\("skipped"\) and prev'),
    ("laminae",   r"if \(s\.laminae > 1",                    r'if s\.get\("laminae", 0\) > 1'),
    ("lag",       r"if \(s\.hiatusDays && prev\)",           r'if s\.get\("hiatusDays"\) and prev'),
    ("contact",   r"const cw = Math\.max",                   r"cw = max\(0\.25"),
]


def check_draw_order():
    """The artwork and its mirror must paint their stages in the same sequence."""
    import re as _re
    html = preview.SRC.read_text()
    js = html[html.index("for (let idx = 0"):html.index("const first = STRATA[0]")]
    src_py = Path(__file__).with_name("preview.py").read_text()
    py = src_py[src_py.index("for idx, s in enumerate(strata)"):src_py.index("return cv")]

    def sequence(text, which):
        hits, missing = [], []
        for stage in DRAW_STAGES:
            m = _re.search(stage[which], text)
            (hits.append((m.start(), stage[0])) if m else missing.append(stage[0]))
        return [n for _, n in sorted(hits)], missing

    js_order, js_missing = sequence(js, 1)
    py_order, py_missing = sequence(py, 2)
    if js_missing or py_missing:
        return ["check needs updating — markers not found in "
                + ("index.html: " + ", ".join(js_missing) if js_missing else "")
                + ("; preview.py: " + ", ".join(py_missing) if py_missing else "")]
    if js_order != py_order:
        return [f"artwork draws {' -> '.join(js_order)}; mirror draws {' -> '.join(py_order)}"]
    return []


def main():
    live = preview.load_strata()
    cases = [(live, W, H, f"live {len(live)} strata @{W}x{H}")
             for W, H in ((900, 560), (400, 900), (2400, 700), (320, 400))]
    for n in (20, 60, 200):
        st = synth(live, n, 4242)
        cases.append((st, 1100, 750, f"synthetic {len(st)} strata"))
    st = synth([dict(s, roughness=0.45) for s in live], 80, 99,
               thickness=0.02, roughness=0.45)
    cases.append((st, 1100, 750, "worst case: roughness 0.45 throughout"))

    failed = 0
    pinch_live = []
    for strata, W, H, label in cases:
        thin, at, floor, pinch = worst_band(strata, W, H)
        if label.startswith("live"):
            pinch_live.append(pinch)
        ok = thin > 0 and floor >= H - 0.01
        failed += not ok
        print(f"{'ok  ' if ok else 'FAIL'}  {label:<36} "
              f"thinnest band {thin:7.2f}px at stratum {at:<5} "
              f"floor {floor:.1f} (>= H {H})")

    print(f"\n{len(cases) - failed}/{len(cases)} configurations pass")

    # Advisory. Pinch-out is a feature — 006 says so — but its rate climbs as
    # the column thickens, because fold displacement accumulates while beds
    # compact. Measured at 0046: 9% at 42 strata, 41% at 160. Nothing is wrong
    # at these levels; this is here so a successor meets the number on purpose
    # rather than discovering it a hundred iterations from now.
    if pinch_live:
        rate = 100 * sum(pinch_live) / len(pinch_live)
        # Threshold raised from 25% at 0086. 0046 set 25 when a pinched bed
        # still drew a full-weight contact line, which is what made the count
        # worth flagging. 0072 made that contact fade to *nothing* as the gap
        # closes, so the same geometry no longer implies the same harm — the
        # check was measuring a proxy that a later fix quietly decoupled. 45%
        # is 0046's own projection for stratum 160; below that, pinching is
        # 006's mechanism doing its job invisibly.
        note = ("" if rate < 45 else
                " — climbing; see 0045/0046/0086 before adding fold amplitude")
        print(f"{'ok   ' if rate < 45 else 'note '} {rate:.1f}% of contact pixels "
              f"pinch to the minimum gap (advisory){note}")

    dupes = check_js_scopes()
    if dupes:
        print("FAIL  strata/index.html redeclares in one scope: " + ", ".join(dupes))
        failed += 1
    else:
        print("ok    strata/index.html: no redeclaration in any brace scope")

    missing = check_html_script()
    if missing:
        print("FAIL  strata/index.html calls undefined: " + ", ".join(missing))
        failed += 1
    else:
        print("ok    strata/index.html: every call resolves")

    drift = check_mirror_constants()
    if drift:
        print("FAIL  renderers disagree: " + "; ".join(drift))
        failed += 1
    else:
        print(f"ok    renderer and mirror agree on {len(SHARED_CONSTANTS) + 2} constants")

    seq = check_draw_order()
    if seq:
        print("FAIL  draw order: " + "; ".join(seq))
        failed += 1
    else:
        print(f"ok    both renderers paint {len(DRAW_STAGES)} stages in the same order")

    # These two are correctness, not taste, and both shipped as advisories for
    # forty-odd iterations while README.md said the suite asserted them. An
    # outside reading at 0049 set stratum 44's thickness 43x wrong and watched
    # the suite exit 0. Thickness against the git history IS the piece's
    # central claim; a skip nobody recorded is a hole in the record.
    off, audited, unauditable = check_thickness_law(live)
    if off:
        print("FAIL  thickness does not match elapsed time: " + "; ".join(off))
        failed += 1
    else:
        print(f"ok    {audited} strata audited against their commit intervals, all match")
    if unauditable:
        print("note  could not audit (no commit found): "
              + ", ".join(str(n) for n in unauditable))

    # The out-of-repo project memory is the only bridge across sessions rather
    # than iterations, and it is the one thing here with nothing checking it.
    # It has rotted three times (018, 0035, 0053). Advisory, not FAIL: the file
    # lives outside the repo and may legitimately be absent.
    # Faults are the one mechanism whose sign accumulates: each offsets some
    # beds relative to others, so a set that all drops the same way tilts the
    # whole record and random-walks without bound. 0055 found three-for-three
    # by looking, after every magnitude check had passed — a bias in direction
    # is invisible to anything measuring size. This watches the sum of signs.
    wide = check_width_scaling()
    if wide:
        print("note  " + wide)

    drift = check_intent_sections()
    if drift:
        print("note  " + drift)

    tilt = check_fault_balance(live)
    if tilt:
        print("note  " + tilt)

    stale = check_memory_current(live)
    if stale:
        print("note  " + stale)

    print("note  " + check_surface_against_sky(live))
    print("note  " + check_depth_contrast(live))

    for line in check_governing_terms(live):
        print("note  " + line if not line.startswith(" ") else line)

    crowded = check_fault_separation(live)
    if crowded:
        print("FAIL  " + crowded)
        failed += 1
    else:
        print(f"ok    fault planes hold their separation at all "
              f"{len(SEPARATION_SIZES)} frame sizes")

    unrecorded = check_skips_recorded(live)
    if unrecorded:
        print("FAIL  skips not recorded on the following deposit: "
              + "; ".join(unrecorded) + " — see 023, `skipped`")
        failed += 1
    else:
        print("ok    every skipped wake-up is recorded on the bed above it")

    long = check_phrase_length(live)
    if long:
        recent = [x for x in long if int(x.split(":")[0]) > 19]
        if recent:
            print("note  phrases over 140 chars since the convention: "
                  + ", ".join(recent) + " — see 019 (advisory only)")

    flat = check_lightness_steps(live)
    if flat:
        print("note  lightness steps under 10 in recent beds: " + ", ".join(flat)
              + " — see 012, choose lightness before hue (advisory only)")
    else:
        print("ok    recent beds all step more than 10 in lightness")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
