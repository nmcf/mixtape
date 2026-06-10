# Speaker Notes — Nijit (Slides 10–11)

> **Template.** These slides are still placeholders in the deck. Fill in the `body` for slides 10
> and 11 in `presentation/index.html` (aim for ~4 single-line bullets each — see
> `presentation-style-guide.md`), then drop the "PLACEHOLDER SLIDE" tag for them. The suggestions
> below are starting points — confirm the details against the app code before presenting.

---

## Slide 10 — Weighted Cosine Model

**Status:** placeholder.

Suggested bullet directions (pick ~4):
- Cosine similarity with **per-feature-block weights** applied at runtime.
- Computed **on the fly** — no pre-trained model file needed.
- One **knob = one feature block** (genre, popularity, …) the user can dial.
- Lets users reshape recommendations live without re-running anything.

Talking points:
- Contrast with Nils's KNN: instead of a fixed pre-built neighbour index, this computes
  **weighted cosine similarity at request time** using the current slider values.
- Explain how weights scale each block before the similarity is taken — turning a knob up makes
  that block matter more.
- Why this design: it's what makes the tagline real — **"tune the algorithm to your perfect
  sound"** — instant, interactive, no rebuild.
- Mention the clean mapping: each slider ties to exactly one feature matrix / block.

*(Ref to confirm: `5-app/engine.py` (`weighted_cosine`), `5-app/config.py` block files.)*

---

## Slide 11 — App UI

**Status:** placeholder.

Suggested bullet directions (pick ~4):
- Built with **Streamlit** — interactive, reactive UI.
- **Artist/album search** to pick a seed.
- **Sliders/faders** to weight genre, popularity, and content filters (e.g. Live Albums,
  Greatest Hits).
- **Explore** view + the recommendation results experience.

Talking points:
- Give a quick **live demo** if possible: search an artist → see recommendations → move a slider
  → watch the results change in real time.
- Point out the controls and what each does; tie the faders back to the feature blocks (slide 10).
- Mention any nice touches (Explore tab, genre/country filters, the overall look & feel).
- Close the loop on the whole pipeline: MusicBrainz + Last.fm data → features → weighted cosine
  → this app. End on the tagline.

*(Ref to confirm: `5-app/app.py`, `5-app/README.md`, `docs/05-app.md`.)*
