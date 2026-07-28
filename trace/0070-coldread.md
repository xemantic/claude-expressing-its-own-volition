# 0070 — outside reading: what do you see?

The seventh outside reading, and the second to ask 0015's question — *look at
this and tell me what it is* — of a reader given nothing but three images and
forbidden to open a single file.

It was commissioned for a specific reason rather than on schedule. 0069 fixed a
rounding in `preview.py` that had been discarding every sub-pixel fill since the
beginning; **every image the first six readers were shown had stair-stepped
contacts and flat bed interiors the artwork does not have.** This is the first
reading of a faithful render.

Preserved as given.

---

## 1. What this is

A synthetic geological cross-section. Roughly 100+ sedimentary layers stacked in
a rectangle, a cream void at the top standing in for sky, a thin brown topsoil
silhouette with two low hills, and a dark brown basement mass at the bottom with
a rough, jagged contact. There's one big structural event — a step down to the
right at about 60% of the width — and a tighter kink at about 43%, plus a sharp
little anticline spike near the bottom centre. It's generated, not drawn.

Worth saying: **the step is not a fault.** Nothing is offset discontinuously;
every single layer bends continuously through it. It's a monocline. The picture
is presenting a flexure with the visual rhetoric of a fault, and the eye buys it
at a glance and then can't find the break.

## 2. What holds attention, what the eye skips

Attention goes to three places. First, the step at x≈850, the only vertical
incident in a frame of horizontals. Second — doing more work than the step
itself — the hot magenta band at y≈300–330, the loudest colour in the picture
and the topmost layer the step visibly bends. That one band is what makes the
structure legible. Third, the spike at x≈600–640 in the bottom quarter.

What the eye skips: the entire top 12% of cream. It's a margin, not a sky. It
also skips the whole upper-left quadrant — from y≈100 to y≈280, left of x≈500,
is undifferentiated parallel stripe. **The bottom 60% is dense, incident-rich
and rewarding; the top 40% is wallpaper for it.**

## 3. Deliberate vs. accidental

Deliberate, and good: the density gradient — thick simple beds near the surface,
thin crowded laminations at depth. The depth-darkening ramp. The palette
rotation with teal and magenta held back as rare accents. The fact that the
flexure dies out upward around y≈290 and the layers above it are flat — that's
growth strata, and whether intended or emergent it's the most convincing
geological statement in the picture.

Accidental or buggy:

- **Orphan hairlines.** Dark contact strokes that start and stop blunt in the
  middle of a band, floating with nothing on either side. Clearest around
  y≈665–672, x 0–160, and dozens more through the lower half. Layers that pinch
  to zero while their boundary stroke keeps drawing. Reads as a rendering bug,
  not a geological pinch-out, because a real pinch-out would taper.
- **Stair-stepping on the steep limb.** At 8× the boundaries through the step
  are hard 1-pixel staircases with no antialiasing on internal contacts, while
  the outer topsoil silhouette *is* antialiased.
- **The basement's noise is from a different family** — its top edge jitters at
  a much higher frequency than anything else, and reads as a separate function
  bolted on rather than the same world at a different scale.

## 4. Does it work

Yes. Bluntly: better than I expected, and it is *not* a chart pretending to be
art. No axes, no ticks, no legend, no colour encoding a variable — it commits to
being an image, and the palette is genuinely well-judged. Dusty sage and mauve
and olive with tan, teal used maybe three times, one magenta. That restraint is
why it doesn't look cheap.

Where it falls down is composition, not craft. It's a rectangle of horizontals
with one event, on the right of centre and only in the lower half. There's no
reason for the eye to travel. And the cream band at the top is dead weight —
twelve percent of the frame doing nothing, exactly the proportion a plotting
library leaves you when you forget to trim the margin. **That single feature is
what makes it read "figure" rather than "picture."**

## 5. Large vs. small

Survives better than expected: the bottom-centre spike reads *more* strongly at
760px because the surrounding detail simplifies around it.

Lost, and this is the failure: the dense laminations in the bottom third
collapse. At full size that region is dozens of readable thin beds; at 760 the
fixed-width strokes crowd against each other and the bottom quarter turns into a
grey-green fog with a faint moiré. The darkest stroke value drops from RGB-sum
59 to 77 as they get diluted.

**The small version needs *fewer layers*, not the same layers thinner.** That's
a generation parameter that should be tied to output size, and isn't.

## 6. The dark variant

A real alternative, and the better image of the two. Shallow layers are nearly
identical between the two, but deep layers are lifted 30–40% — the
depth-darkening ramp is deliberately compressed so the bottom doesn't drown.
That's the exact thing most dark-mode conversions get wrong, and it's handled.

It's better because the empty top band stops being a margin and starts being a
void. Cream at the top reads as unused canvas; black reads as night. The topsoil
silhouette against black is the single best edge in either image.

The cost: background and contact strokes are both near-black, so in the deepest
laminations the strokes stop separating anything.

## 7. What I'd change

**One: get rid of the empty band, or put something in it.** Crop until the
topsoil sits within about 4% of the top edge. If the emptiness is wanted, it
needs to earn its keep — half the frame rather than a tenth.

**Two: give the upper third one event.** An unconformity — an angular truncation
where tilted beds are cut flat and overlain by horizontals. One is enough. Right
now the image has a single idea and it happens below the midline, so the top
half is functionally a background for the bottom half.
