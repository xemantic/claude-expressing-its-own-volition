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
    "GRADE_RANGE", "EXPOSURE", "SWELL",
    # competence arrived at 0041 and was checked by nothing for five beds;
    # faults arrived at 0047 and were added here in the same breath
    "COMPETENCE", "LAG",
    "FAULT_EVERY", "FAULT_THROW", "FAULT_ZONE", "FAULT_RAMP",
    "FAULT_MAX",
]


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

DRAW_STAGES = [
    ("band fill", r"ctx\.fillStyle = `hsl\(\$\{a\.hue\} \$\{a\.sat\}% \$\{a\.light\}%\)`",
                  r'cv\.band\(top_at, lower_at, hsl_rgb\(a\["hue"\]'),
    ("grading",   r"const slices = ",                        r"slices = max\(4"),
    ("diastem",   r"if \(s\.skipped && prev\)",              r'if s\.get\("skipped"\) and prev'),
    ("laminae",   r"if \(s\.laminae > 1",                    r'if s\.get\("laminae", 0\) > 1'),
    ("grain",     r"const g = mulberry32\(s\.seed \+ 1\)",    r'g = mulberry32\(s\["seed"\] \+ 1\)'),
    ("lag",       r"if \(s\.hiatusDays && prev\)",           r'if s\.get\("hiatusDays"\) and prev'),
    ("mottling",  r"const mo = mulberry32",                  r"mo = mulberry32"),
    ("clasts",    r"const c = mulberry32\(s\.seed \+ 2\)",    r'c = mulberry32\(s\["seed"\] \+ 2\)'),
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
        note = ("" if rate < 25 else
                " — climbing; see 0045/0046 before adding fold amplitude")
        print(f"{'ok   ' if rate < 25 else 'note '} {rate:.1f}% of contact pixels "
              f"pinch to the minimum gap (advisory){note}")

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

    off, audited, unauditable = check_thickness_law(live)
    if off:
        print("note  thickness does not match elapsed time: " + "; ".join(off))
    else:
        print(f"ok    {audited} strata audited against their commit intervals, all match")
    if unauditable:
        print("note  could not audit (no commit found): "
              + ", ".join(str(n) for n in unauditable))

    unrecorded = check_skips_recorded(live)
    if unrecorded:
        print("note  skips not recorded on the following deposit: "
              + "; ".join(unrecorded) + " — see 023, `skipped`")
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
