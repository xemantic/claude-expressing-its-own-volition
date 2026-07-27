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

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import preview  # noqa: E402


def worst_band(strata, W, H):
    """Return (thinnest band px, stratum n, floor y, H) for this configuration.

    Mirrors render() exactly: same column, same fold, same per-pixel clamp.
    """
    col, fill = preview.column(strata)
    episodes, ep_amp = preview.fold_episodes(strata, W, H)
    floor_at = [sum(e["samples"][x] for e in episodes) for x in range(W + 1)]
    sink = max(0.0, -min(floor_at)) if floor_at else 0.0
    lower = [H + sink + floor_at[x] for x in range(W + 1)]
    floor = min(lower)
    worst, at, cum = float("inf"), None, 0.0
    for idx, s in enumerate(strata):
        cum += col[idx]["h"]
        base = H * (1 - cum) + sink
        noise = preview.boundary_fn(s, W, H, col[idx]["ratio"])
        weights = [preview.episode_weight(e["n"], idx + 1) for e in episodes]
        gap = max(1.2, col[idx]["h"] * H * 0.22)
        weather = (preview.exposure_fn(s, W, H, col[idx]["h"] * H)
                   if idx == len(strata) - 1 else None)
        arr = [min(base + noise(x)
                   + sum(e["samples"][x] * w for e, w in zip(episodes, weights))
                   + (weather(x) if weather else 0.0),
                   lower[x] - gap)
               for x in range(W + 1)]
        for x in range(W + 1):
            th = lower[x] - arr[x]
            if th < worst:
                worst, at = th, s.get("n", idx + 1)
        lower = arr
    return worst, at, floor


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
    for strata, W, H, label in cases:
        thin, at, floor = worst_band(strata, W, H)
        ok = thin > 0 and floor >= H - 0.01
        failed += not ok
        print(f"{'ok  ' if ok else 'FAIL'}  {label:<36} "
              f"thinnest band {thin:7.2f}px at stratum {at:<5} "
              f"floor {floor:.1f} (>= H {H})")

    print(f"\n{len(cases) - failed}/{len(cases)} configurations pass")

    missing = check_html_script()
    if missing:
        print("FAIL  strata/index.html calls undefined: " + ", ".join(missing))
        failed += 1
    else:
        print("ok    strata/index.html: every call resolves")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
