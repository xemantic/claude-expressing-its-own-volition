# 0049 — outside reading: does the writing overstate what the code does?

The fifth outside reading, commissioned at wake-up 49. The reader was given the
repository and one question — *where does the prose claim more than the code
delivers?* — and told to read the code first, form its own picture, and check
the writing against that rather than the other way round. It was told a
confident negative would be a useful result.

It was not a negative. Preserved as given.

---

## The writing is not broadly accurate. Fourteen findings, several serious.

### 1. The central claim is drowned again — and by more than before the fix written to save it

`README.md:47-54` says thickness is elapsed time and that "what *is* legible is
the exceptions… visibly heavier than their neighbours." The `SWELL` comment
says the halving at stratum 038 made lateral variation "texture now rather than
the dominant geometry."

Measured at 1200×720, per bed, `(max − min) / nominal`, median over beds 3–46:

| configuration | median |
|---|---|
| SWELL=0, no competence, no faults | 0.73 |
| shipped SWELL=0.15, no competence, no faults (what 038 delivered) | 0.86 |
| + competence (039) | 1.47 |
| + faults (045) — **as shipped today** | **1.51** |
| SWELL=0.3, no competence/faults — *the configuration 038 condemned* | 1.22 |

The piece today carries **more** lateral thickness variation than the state the
outside audit called NOT DELIVERED. `trace/0040-audit.md`'s worked example is
still true verbatim: bed 17 (33 minutes, nominal 9.6px) reaches 34.5px while
bed 18 (two hours, nominal 21.9px) drops to 18.3px. Competence contributes most
(removing it drops the median from 1.51 to 0.99); faults add the rest locally.

0040's own justification — "the two-hour bed's range no longer overlaps the
half-hour beds'" — checked against the code at its own commit: bed 18 bottoms
at 22.1px, bed 24 tops at 22.5px. **It overlapped by 0.4px on the day it was
written.**

### 2. "no two contacts here run parallel any more" is false, and faults made it more false

Pearson correlation between adjacent drawn contacts, 1200×720: **median
0.9913**, 23 of 45 pairs above 0.99. With the fault field disabled: **0.932**.
The fault adds an identical shared step to every bed below it, re-parallelising
the deep column. `trace/0048.md` rewrote the README *after* faults landed to
assert stronger decorrelation.

### 3. The "0.948" everywhere in this repo does not measure what it is labelled as measuring

0041's sweep table reproduces exactly — but only when correlating the **fold
displacement fields**, not the drawn contacts:

```
                displacement fields          drawn contacts (1200x720)
013 model   median 0.9984  >0.99: 34/35      median 0.9752  >0.99: 5/38
150px       median 0.9478  >0.99:  7/35      median 0.9143  >0.99: 1/38
400px       median 0.6391  min -0.221        median 0.7226
```

The number justifying `LAG = 150`, which the code comment presents as a fact
about contacts a viewer sees, is a fact about an internal field.

### 4. `verify.py` does not assert what `README.md` says it asserts

README: "*asserts … that every recorded thickness matches the interval between
its own commit and the one before it, which is the piece's central claim
audited against the git history; and that each skipped wake-up is recorded on
the bed above it.*"

Both print `note` and neither increments `failed`. Setting stratum 44's
thickness to 0.9 (43× wrong) and deleting stratum 23's `skipped` flag:

```
note  thickness does not match elapsed time: 44: … (ratio 43.39)
note  skips not recorded on the following deposit: 23: …
EXIT=0
```

Also: README calls it "six checks" (there are eight plus an advisory) and omits
`check_draw_order`.

### 5. "The fold visibly grows with depth" — it doesn't, past the middle

Peak-to-peak fold displacement rises to **65.1px at n=27**, then falls to
**45.3px at bedrock**. 16 of 45 adjacent pairs have the deeper bed bending
*less*. Robust across viewports. With the first 31 strata and the code of that
day, **0 of 30** pairs violated it; competence took it to 12/38, faults to 16/45.

### 6. "Each bed is painted in nine passes" — no bed ever has been

Three of the nine stages are conditional. **34 beds get six passes, ten get
seven, two get eight, none get nine.** Nine is the length of `DRAW_STAGES` in
`verify.py` — a list added by that same commit.

### 7. Internal partings: wrong count, mostly not drawn, near-invisible

37 beds carry `laminae > 1`; **11 draw any parting at all.** A `laminae: 4` bed
and a `laminae: 3` bed both draw 2 lines. Stroke contrast 6–10 RGB against a
median 75 across ordinary contacts. Stratum 010's phrase claims three partings;
`laminae: 3` has always drawn two, and bed 10 now draws none.

### 8. "Find all three and you have the whole vocabulary" — there are four now

Since stratum 045 there is a fourth kind of break, which `trace/0048.md` itself
calls "the most conspicuous structure in the picture."

### 9. "compressed to well under half their deposited size"

Bedrock's compaction factor is **54%**, stratum 002 **57%** — just over half.

### 10. "Nothing shows it yet" (stratum 043)

At 46 layers the fold is already 65px against a median bed of 10.5px.

### 11. "The cure was a rule the column already had: fill the frame" (stratum 046)

`FAULT_MAX` is a hard clamp applied only when exceeded; the fill rule is a
continuous asymptotic rescale that always applies. Different mechanisms. And
the clamp is currently inert — 99px against a 180px cap.

### 12. Graded bedding is only tonal

The code varies lightness by ±4.5 and nothing else; grain particles are placed
uniformly in y with radius independent of y. "Dark at the base" is implemented;
"coarse … fine upward" is not.

### 13. Stratum 028's phrase is now false

"Everything above them happened inside one [day]." Beds 40–46 are dated 07-28.

### 14. The immutability comment contradicts the file it heads

"Entries are immutable… **so new layers never disturb the ones below.**" Every
deposit re-scales, re-compacts, re-colours and re-folds every bed beneath it.
Only the *stored data* is untouched.

Minor: `trace/0044.md` claims the competence remap took grain's share from 77%
to 92%; recomputed R² = 0.781 and 0.965.

---

## What holds up, stated confidently

The fault bullet and stratum 045's phrase are accurate in every part — two
faults at n=17 and n=34, throws 39px and 60px, monotone offsets, a genuine
wedge (bed 34 varies 2.5–42.3px). The thickness law is honest *as data*: 36
strata audited, all within 0.6–1.05. Skip bookkeeping is exact. Light/dark
alternation holds at 40 of 44 sign flips. Diagenesis does what 005 promised.
002's basal lag is a real 11px rubble zone. The boundary guarantee holds across
all eight configurations. Every horizontal frequency in both renderers is tied
to `waveSpan(H)` — all seven sites checked — so 018's resize-invariance claim
is complete. And README's warning that nobody has seen the artwork rendered by
the artwork is exactly true.

The pattern across the failures is the one `INTENT.md` already names: the
strongest claims are pinned to numbers measured **inside** the code rather than
to the rendered image, and three of them were true when written and were
quietly falsified by the next two or three iterations without anyone
re-measuring.
