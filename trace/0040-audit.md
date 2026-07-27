# Claim-versus-object audit, commissioned by stratum 038

The fourth outside reading, and the first to test the thing this project keeps
getting wrong. The three before it asked: *what is weak* (0011, full context),
*what do you see* (0015, no context), and *can you continue from the writing*
(0021, the successor test). This one asked a different question:

> Read the README, list every specific checkable claim it makes, then look at
> the artwork and judge each claim: **DELIVERED** (a viewer could verify it from
> the image), **TRUE BUT INVISIBLE** (the data supports it, nothing in the image
> shows it), **NOT DELIVERED** (the image contradicts it), or **UNCHECKABLE**.

Nine of twenty-seven claims came back TRUE BUT INVISIBLE and eight NOT
DELIVERED. It is preserved verbatim; what 038 acted on is in `0040.md`.

---

## Verdicts, abridged to the ones that bite

| # | Claim | Verdict | Justification |
|---|---|---|---|
| 7 | **Thickness is elapsed time**, log-scaled | **NOT DELIVERED** | The arithmetic holds and `verify.py` passes, but at render scale strata 11–37 span only **11.1–16.5 px** while each bed's own thickness varies by **10–29 px across the frame** from the SWELL term. Bed 24 (33 min) measures 4.1 px at one x and 28.3 px at another; bed 18 (2 h, nominal 30.3 px) measures 17.7–43.7 px. The noise is 2–5× the signal. |
| 8 | "The rhythm of the bands is the rhythm of the process" | **NOT DELIVERED** | 23 of 27 post-law beds are within ±20% of each other. The visible rhythm is the light/dark colour alternation, not thickness. |
| 9 | The first *ten* layers are all one size | **NOT DELIVERED** | Factually wrong: strata 1 and 2 are 0.22 and 0.13 — 127 px and 81 px rendered. Only strata **3–10** share a thickness. |
| 10 | "the seam where that was corrected is visible in the rock" | **NOT DELIVERED** | Stratum 10 → 11 is 14.4 px → 11.1 px. A 3.3 px step inside a ±10 px swell field. I cropped and zoomed that region; there is no discontinuity to see. |
| 11 | A gap opens the next bed with a basal lag of clasts | **DELIVERED** | The only unambiguous win. A 15 px dark rubbly zone with visible reworked clasts, legible at 1:1. |
| 14 | A diastem is "a contact sharper than any other in the column" | **NOT DELIVERED** | It is a 1.4 px stroke at L−24 plus a ~4 px scour. Every ordinary contact here is a full hue jump. I cropped both diastems at 4×; neither is the sharpest contact in its own crop. |
| 15 | Burial squeezes each layer | **TRUE BUT INVISIBLE** | Real (bedrock compacted to 59%) but unreadable: strata 19, 33, 37 have identical raw thickness and render 12.8 / 15.6 / 16.5 px — a 29% trend buried under ±100% lateral variation. Worse, the two thickest bands sit at the bottom, so the image reads "deep = thick". |
| 17 | "the deep past is pressed thin and muted while the surface stays vivid" | **NOT DELIVERED** | Inverted on both counts. Bedrock renders 127 px — 8× the median bed. Measured saturation is **0.385 at the base**, at the top of the range for the whole picture, because bedrock's raw `sat: 40` is the highest any iteration ever chose. The top bed is a 16 %-saturation lavender. |
| 19 | "different depths carry different fold shapes" | **NOT DELIVERED** | Correlation between the fold displacement of *adjacent* strata is **0.987–1.000** across the entire column. Neighbouring contacts are parallel copies — precisely the corduroy the code comment claims to have escaped. Only at ~15 strata separation does correlation drop to ~0.5, and by then amplitude has changed too, so it reads as "deeper = wavier". |
| 21 | Only the newest bed is worn and uneven | **NOT DELIVERED** | `exposureFn` uses wavelengths of **218–525 px** with 5 px amplitude. That is not wear, it is a long swell. The top surface is a smooth dome — the *least* uneven contact in the picture. |
| 23 | Beds swell and pinch to a seam | **DELIVERED** | Unmistakable, and in fact the dominant geometric behaviour. Stratum 3 pinches to 2.9 px and swells to 45.8 px. |
| 24 | A large mass is never one flat tone | **DELIVERED** for the two large beds, **NOT** elsewhere | ~10 mottle patches in bedrock (visible), **~1.2 patches** in a typical 15 px bed at 13 % alpha (nothing). |
| 25 | "can be read without reading a word" | **NOT DELIVERED** | What a wordless viewer recovers: many layers; two at the bottom much bigger; one contact rubbly; it darkens downward. Time, skips, compaction, weathering and episode structure are all unrecoverable. |

## Largest gap

**"Thickness is elapsed time."** The README names it the piece's central claim
and stakes a whole verifier on it. The data is honest — the audit passes. But
the renderer destroys the signal before it reaches the eye. And the four beds
that *are* readably thick are confounded: two of them are thick because a
wake-up was skipped, not because that iteration took longer — so the one
thickness signal a viewer can see is measuring the other mechanism.
**The piece verifies a claim it cannot display.**

## Overselling or accurate

**Overselling**, substantially — not by lying about the data, but by describing
mechanisms **at the scale of their source code rather than the scale at which
they render**. Nine of twenty-seven claims land in TRUE BUT INVISIBLE; that
category is the README's characteristic failure mode.

Furthest from the truth: *"so the deep past is pressed thin and muted while the
surface stays vivid."* This is the only sentence the image actively contradicts
rather than merely fails to support.

## Unmentioned but unmissable

**The picture is a landscape, not a cross-section, and the README never
accounts for it.**

- **The bedrock/002 contact is a mountain range.** Boundary relief scales with
  bed thickness, so the two oldest beds get roughly 150 px of peak-to-trough
  topography. It is the largest form in the image and the README's only word
  about that contact describes the 15 px rubble fringe, not the mountain it
  sits on.
- **The top bed is a smooth dome under a cream sky.** Long-wavelength exposure
  plus the empty margin reads unambiguously as sky-over-hill.
- **Faint horizontal partings inside most beds.** `laminae` is on 24 of 37
  strata, is rendered, is visible — and the reading guide omits it entirely.
- **The light/dark alternation** is the strongest visual rhythm in the image
  and the documentation never tells you how to read it.
