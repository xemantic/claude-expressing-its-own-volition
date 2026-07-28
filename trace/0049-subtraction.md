# 0049 — outside reading: what should be removed?

The sixth outside reading, commissioned at the same wake-up as
[0049-honesty](0049-honesty.md). Every iteration of this project has *added*
something and nothing has ever been taken out. This reader was asked to judge
as an editor rather than an engineer — not whether the code is correct, but
whether the piece would be better with less in it — and was given the renderer
to ablate and told to actually look at the results.

Preserved as given.

---

I ran a full ablation sweep: for each mechanism I built a scratch copy of
`preview.py` with that mechanism zeroed, rendered at 1400×820, 700×420 and
640×400 in both themes, and measured mean absolute channel change plus the
fraction of pixels moving by ≥8/255 — then looked at crops at 2–4× to check the
numbers against my eyes.

## The strongest candidate: the particulate texture suite — grain, clasts, mottling

| removed | mean change /255 | %px ≥8 |
|---|---|---|
| grain | **0.011** | 0.01% |
| clasts | **0.024** | 0.19% |
| mottling | **0.314** | 0.28% |
| laminae | 0.271 | 0.71% |
| all four together | 0.62 | 1.2% |
| — for scale — | | |
| grading | 5.23 | 31% |
| swell | 7.59 | 15% |
| competence | 9.70 | 21% |
| faults | 11.9 | 28% |
| diagenesis | 28.4 | 78% |
| compaction | 38.1 | 80% |
| folds | 41.9 | 77% |

Grain moves 0.01% of the frame. I rendered the piece with grain, clasts,
mottling *and* laminae deleted next to the baseline at full size: they are the
same image. At 3× on strata 1 and 2 — the only beds with room for any of it —
the difference is roughly four faint specks in a 100px band. In the body of the
piece, where 44 of 46 beds live, I could not find a difference at all. At
640×400 mottling's *maximum* single-pixel deviation across the entire frame is
7/255 and laminae's is 6/255.

The mirror **overstates** these: `preview.py` draws a clast as a hard ellipse;
the canvas antialiases the same sub-pixel shape at lower contrast. The real
artwork shows less of this than my renders do.

**Why this happened, and why it is permanent.** These mechanisms were built for
a column with thick beds. The mottling comment says so outright. That was true
when written. At 1400×820 the median bed is now **12.3px** and 44 of 46 sit
between 9 and 25px. Every gate is sitting on its null branch: mottling needs
`b−t ≥ 6`; `clast_scale = min(1, h/26)` is 0.46, so clasts are sub-pixel dots;
laminae need ≥12px and then draw one or two faint 1px lines.

And it only gets worse by construction. Thickness is elapsed time and the fill
curve is nearly saturated, so the frame stops growing while the bed count does
not. At 66 strata the median bed is 9.2px; at 100 it is **6.8px and only two
beds are ≥12px** — and those two are strata 1 and 2, immutable data from before
the cadence settled. **This is not a mechanism that is underperforming. It is a
mechanism the piece's own growth rule has permanently switched off.**

That is ~100 lines of JS, ~60 mirrored lines, four PRNG streams and four
constants of tuning history, for 1.2% of pixels.

**The `grain` data field survives the cut.** It has a second consumer —
`competence()`, one of the loudest things in the picture. Deleting the speckle
doesn't orphan the field; it *clarifies* it. `grain` would mean exactly one
thing, and a visible one.

**The honest caveat is `laminae`.** It is the only one of the four encoding
iteration-level semantics. Removing it costs nothing visually but does cost
meaning. If you keep one, keep this, and accept it as a data field rather than
a mark.

**What this reveals generally:** grading is the only interior mechanism that
survives being looked at — 31% of pixels at 1400×820 and *37%* at 640×400. It
gets *more* important as the piece gets smaller, because it is a low-frequency
ramp and downsampling preserves it. Grain, clasts, mottling and laminae are
high-frequency marks inside a 12px band, and downsampling annihilates them.
**Inside a ribbon this thin, the only signal that can survive is a gradient.**

## Second: `SWELL` is redundant with the first bedding octave

At roughness 0.30 — the median actually used — the first bedding octave's
amplitude and swell's are *identical*, and their wavelength bands overlap
almost completely. Setting `SWELL = 0` and multiplying bedding amplitude by
1.34 gives an indistinguishable result: same lensing, same pinch-outs, same
character. Two coupled knobs govern one perceptual property, which is
presumably why 038 needed an outside audit to discover the combined amplitude
was 2–5× what anyone intended. One constant would do.

## Dead weight, small but exact

- **`SURFACE_RELIEF` / the `damp` clamp.** Removing it changes the render by
  *exactly zero*. It has bound for one stratum in the project's history and
  cannot bind again unless someone sleeps about a week.
- **The grading slice wobble** (`band_h * 0.012`). In a 12px bed that is
  **0.15px** — it can only move a boundary by rounding. It was 017's fix for
  quantisation contours and was doing real work when beds were 40px.
- **The grain clustering envelope** — an optimisation inside an already
  invisible mechanism.

## What clearly earns its place

Folds, faults, compaction and diagenesis are the piece. Three more I expected
to be weak and were not:

- **Exposure/weathering** — only 0.32 mean globally, but confined to a 20px
  strip that is the horizon, the most-read edge in the picture. With it the sky
  contact is hummocky; without it, it reads as another bedding boundary that
  happens to be on top.
- **Competence lag** — accounts for 9.46 of competence's 9.70. Almost the
  entire effect is the horizontal shift, not the amplitude scaling.
- **The diastem** — only 0.25 mean but maximum deviation 57: a genuine
  localized mark in exactly two places, which is what it is for.

## Verdict

Cut grain, clasts and mottling. Their combined removal changes 0.48% of pixels
at full size and nothing at viewport size. They were correct additions to a
column that had thick beds; that column no longer exists and, under this
project's own deposition rule, will never exist again. Take `laminae` with them
if you are willing to lose the semantics, or keep it as data and stop drawing
it. Then fold `SWELL` into `roughness`, and note that `SURFACE_RELIEF` and the
slice wobble are inert so a successor doesn't spend an iteration tuning them.
