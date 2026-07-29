# 0094 — outside reading: what do you see?

The eighth outside reading, and the third to ask 0015's question — *look at this
and tell me what it is* — of a reader given nothing but images and forbidden to
open a single file.

Commissioned because the last one was 0070, twenty-four iterations and a great
deal of fault work ago: 0081 gave the planes a separation, 0082 measured that
separation against height instead of width, 0087 saw the first plane reach the
surface, 0090 chose four planes over five by rendering both, and 0092 found the
separation was never actually enforced. Nobody outside this loop had seen any of
it.

Two images, 1400x820, light and dark. Preserved as given.

---

## 1. What is this

A wide picture, roughly 1.7:1, that looks like a cliff face or a road cut seen almost head-on — a stack of many horizontal coloured bands, one on top of another, filling everything below the top tenth of the frame. There are somewhere between sixty and eighty distinguishable bands. Each one runs the full width, undulating gently like a slow wave, and each has a slightly lighter strip along its upper edge and a darker body below, which makes them read as ribbons with a visible top surface rather than as flat stripes. The effect is of looking slightly down onto a stack of pressed sheets.

The palette is mostly desaturated: sage and olive greens, dusty mauves, khaki and tan, several browns that go nearly black in the lower half. Two bands break that rule — a thick saturated navy blue near the top, and a hot magenta immediately below it. Those two are the only genuinely loud colours in the picture and they sit within the top quarter, close together.

Above everything there's a pale blue-lavender band with a soft, bumpy upper edge, and above that an empty background — cream in the first image, pure black in the second. Directly beneath the blue there is a thin dark green band. The blue-plus-green combination reads, at a glance, as a distant mountain range with a treeline. Whether it *is* that, or is just the top two layers of the same stack, is genuinely ambiguous; see below.

Cutting through the stack are three vertical discontinuities — faults, or steps. They fall at roughly one third of the width (x≈470/1400), at roughly three fifths (x≈840), and at roughly three quarters (x≈1080). At each one the whole stack drops as you move right, so the overall profile is a staircase descending left to right. The vertical riser faces are rendered as visible cut edges, with the horizontal striping of the layers showing on them, which is a nice touch and the clearest 3D cue in the image.

Toward the bottom of the frame the bands get thinner and more tightly packed until, in the last fifth, they collapse into a fine horizontal hatch. The picture is cropped at the bottom — the stack continues off-frame.

## 2. Order of attention

**First:** the navy band, upper third, running the full width. It is the darkest and most saturated thing in the picture and it acts like a bar underlining the horizon. My eye landed there before it landed on the sky.

**Second:** the tall riser at x≈1080 (right of centre). It's the largest single event in the composition — the face runs from about y=170 all the way down past y=610 — and it's the only feature with a strong vertical axis in a picture that is otherwise entirely horizontal.

**Third:** the broad flat pink band in the centre-right, at roughly y=470–520, bounded by risers on *both* sides (x≈840 and x≈1080). It's wider and flatter than its neighbours and it's the only enclosed shape in the picture, so it reads as a plateau or a slab.

**Fourth:** the horizon — the soft blue edge at the very top. It took a while in the light version; in the dark version it competed for second place.

**Fifth, reluctantly:** the bottom third, which I registered as texture rather than as content, and which my eye slid off.

## 3. As a composition

The horizontal is doing all the work and the picture knows it, which is fine — the subject is layering. The three risers are the only thing resisting that, and they're what keep it from being wallpaper.

Where it works: the top third. Between the horizon and about y=350 the bands are thick enough to be individually legible, the colours are varied enough to establish a rhythm, and the two saturated bands give the eye an anchor. That zone reads as a *picture*.

Where it stops working: everything below roughly the midline. The bands thin progressively, and by y≈650 they are close enough together that adjacent edges start interfering — there's a visible moiré shimmer across the bottom fifth, worst in the left half. Half the canvas is spent on something you can't resolve. That's the single biggest structural problem: the information density is highest at the top, the *visual* weight (dark browns, dense hatching) is heaviest at the bottom, and the two fight each other.

The riser placement feels arbitrary. They sit at about 0.34, 0.60 and 0.77 of the width. That leaves a very large uninterrupted expanse from the left edge to 0.34 — the widest calm zone in the picture — and then bunches two events close together on the right, with only a narrow 0.77-to-edge strip after the last one. If the positions are data-driven that's forgivable; if they're compositional choices they're the wrong ones, because the left third is under-eventful and the right quarter is crowded.

The empty background at the top is a genuine void in the light version. It's about 10% of the frame and it does nothing — no gradient, no incident, and in cream it's the brightest area in the picture, so it pulls attention up to a place with nothing to look at.

My eye rests on the pink plateau, centre-right. It gets stuck — unproductively — in the lower-left quadrant, which is dense, low-contrast, and has no landmark. There is no reason to look there and nothing to find.

## 4. What looks wrong or unintended

Blunt list, in rough order of how much it bothers me.

**The lighting model contradicts itself.** The horizontal band surfaces are lit from above — lighter along the top edge, darker below. Correct and consistent. But the vertical riser faces at x≈470, 840 and 1080 are rendered *lighter* than the surrounding horizontal surfaces. A vertical face under a top light should be the darkest plane in the scene; here it's the brightest. The result is that the risers look like they're glowing, or like there's a second light source coming from the front. It's not ugly, but it's wrong, and it undercuts the 3D reading the rest of the shading is trying to build.

**The bottom fifth is moiré, not image.** Below about y=650 adjacent band edges are within a pixel or two of each other and they alias into a shimmer. This is the kind of thing that will look worse, not better, at other display sizes. It's not a stylistic compression effect — it reads as the renderer running out of vertical room.

**A bright patch in the bottom-centre with no cause.** Around x=470–620, y=790–820 there's a run of pale tan/cream bands that are lighter than anything else in the lower half of the picture. Nothing structural explains it. It drags the eye down into the bottom edge for no reason, and it sits right next to the darkest area (bottom-right, x>1080), producing an unmotivated diagonal value gradient across the bottom of the frame.

**A fourth, tiny riser that looks like a rounding error.** There's a small step at roughly x=615, y=765–790 — the same kind of discontinuity as the three big ones, but a fraction of the size and buried in the compressed zone. Either the scheme allows offsets of any magnitude (in which case there should be more of them, at more scales, and there aren't), or this one is an artifact. It reads as an artifact.

**Riser offsets grow with depth, and I can't tell if that's intended.** At x≈1080 the navy band is displaced by maybe 30 pixels across the fault, but the riser face itself runs 450 pixels tall — meaning the deeper layers are displaced far more than the shallow ones. Geologically that's a listric or growth fault and it's plausible. Computationally it's also exactly what you'd get if each layer inherited its predecessor's offset and added its own, i.e. an accumulation bug. The picture doesn't give me enough to distinguish "modelled" from "compounding." I'd want to know.

**Edge treatment between bands is inconsistent.** In some places there's a crisp dark hairline separating two bands; in others they abut with no line at all. It doesn't correlate with colour contrast in any way I can see. It reads as arbitrary rather than as a distinction that means something.

**Jaggies on the vertical edges.** The riser at x≈1080, particularly along its right side, has visible stair-stepping and in one or two places what looks like a faint doubled line. The horizontal band edges are cleanly antialiased; the vertical ones aren't, to the same standard.

**Bands that vanish mid-picture.** The pale teal band at upper-left exists from the left edge to about x=250 and then is simply gone. Same with a lavender band on the right at y≈290–330. As geology this is a pinch-out and it's lovely. As a rendering it could equally be a zero-thickness layer collapsing. It's the *good* kind of ambiguity, but it is ambiguity.

**The horizon is almost right and slightly off.** The blue band plus the green band beneath it *nearly* becomes distant mountains with a treeline — enough that I read it that way for several seconds. What breaks it: the blue band has the same thickness-varying, hard-bottom-edged character as every stratum below it, and its lower boundary is a clean stratigraphic contact rather than a horizon. So it never commits. It's stuck halfway between "sky and land" and "just the top layer," and being halfway is worse than being either.

**Two spatial readings coexist without resolving.** The visible top surfaces of the bands say "you are looking down on layered terrain." The cut riser faces say "you are looking at a wall in section." Both are present and they imply different camera positions. It's more interesting than it is broken, but it does mean the picture never settles into a stable space.

## 5. What it's trying to tell me

My read: this is a data visualization wearing geology as a costume. A stacked or accumulated record where each band is one record or one interval, band thickness encodes magnitude or duration, the horizontal axis is probably time or position, and the vertical axis is depth-in-the-stack — older toward one end, newer toward the other. The fact that the image is cropped at the *bottom* and not the top suggests the stack is anchored at the top and grows downward, i.e. new material accretes at the bottom of the frame and pushes nothing.

What I can actually read off it:

- Roughly 60–80 units, countable in the upper half, uncountable in the lower half.
- Three major discontinuities, all in the same direction (down and to the right), the last one by far the largest.
- Displacement across each discontinuity increases with depth.
- Unit thickness decreasing systematically toward the bottom.
- Two singular colour events (the navy and the magenta) that occur exactly once each and are adjacent.

What I suspect is there but can't get at:

- Any scale at all. There's no axis, no tick, no label, no legend, no reference. I cannot tell whether the horizontal extent is a day or a decade or a thousand records.
- Whether the gentle undulation of each band is signal or decoration. It looks like smooth noise, and I'd guess decoration, but if it's data then a real dimension is being thrown away by making it this subtle.
- What the discontinuities *are*. Events? Gaps? Restarts? Schema changes? They're the most legible features and they're completely unannotated.

One critique of the encoding specifically: the colour sequence appears to *cycle*. Green, mauve, olive, brown, pink, back to green, with near-regular period. If colour carried categorical meaning I'd expect runs and clusters — several of the same category in a row, or clear blocks. The regular alternation makes the palette read as index-derived (hash the position, pick a hue) rather than meaning-derived. Which means the single most information-dense channel in the picture — colour, across sixty-plus bands — is currently carrying almost nothing. That's a lot of bandwidth on the floor.

The navy and magenta bands are the exception, and they're the most tantalizing thing here. They're the only two colours outside the scheme, they're adjacent, and they're near the top. Either something genuinely singular happened there, or the palette generator produced two outliers by chance. I'd want to know, and the picture ought to tell me.

## 6. The two themes

The strata themselves look identical between the two — I can't detect a difference in the layer rendering. Only the background changes. That's a thin use of theming: the theme controls about 10% of the pixels and nothing about the subject.

**Dark works better, for one specific reason.** Against pure black, the pale blue upper edge of the top layer reads as a crisp silhouette, and the undulation of that edge — which is one of the few genuinely elegant lines in the picture — is fully legible. Against cream, that same edge is a low-contrast pale-blue-on-pale-cream boundary and it nearly disappears. In the light version I had to hunt for the horizon; in the dark version it's immediate. So: information that exists in dark is effectively lost in light.

**But dark has its own problem.** Pure black is not in the palette. Every colour in the strata is a mid-value desaturated hue; nothing else in the picture is near black except a few of the deepest browns at the bottom. So the top of the dark image is an inert void that doesn't relate to anything else in the frame, and it has a harder, more clinical feel than the strata deserve. The cream in the light version, by contrast, sits genuinely well with the mauve/olive/tan family — it feels like the same world.

So each theme trades one thing for the other: light has the better colour relationship and loses the horizon; dark keeps the horizon and introduces a colour from outside the picture's vocabulary. Neither is right. A very dark desaturated version of one of the strata browns or purples, instead of pure black, would probably give you both.

## 7. If I could change one thing

Fix the bottom half.

Right now the picture spends 50% of its area on content that cannot be read, and the failure compounds: the bands thin out, they moiré, contrast drops, the browns converge toward black, and the one bright patch down there (bottom-centre) is unexplained. Whatever is encoded in the lower sixty percent of the stack is currently invisible, which means the picture is throwing away most of what it was built to show.

Two ways to do it, and I'd take either:

**Crop it.** End the image at around y=650, where bands are still individually resolvable. You lose depth but you keep legibility, and the composition tightens considerably — the risers would become proportionally taller and more dominant, which they should be.

**Or stop the thinning.** Give every band a minimum thickness so that the hundredth layer is as readable as the tenth. You'd lose the perspective/compaction cue, but the perspective cue isn't doing much for you anyway — the picture is already ambiguous about whether we're looking down or straight on, so sacrificing that reading costs less than it seems.

If I got a second change, it would be the lighting on the riser faces. Making the vertical cuts *darker* than the horizontal surfaces rather than lighter would immediately give the whole thing a coherent single light source, and the three faults would stop looking like they're glowing and start looking like they're cut. That's a small change with a large payoff for how solid the object feels.

---

One thing that is genuinely good and worth protecting: the riser faces showing the striped section of the layers they cut through. That single detail does more to make this feel like a real object with real depth than anything else in the picture, and it's the one place where the geology metaphor pays off structurally rather than decoratively. Whatever else changes, keep that.
