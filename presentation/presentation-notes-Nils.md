# Speaker Notes — Nils (Slides 8–9)

> **Template.** These slides are still placeholders in the deck. Fill in the `body` for slides 8
> and 9 in `presentation/index.html` (aim for ~4 single-line bullets each — see
> `presentation-style-guide.md`), then drop the "PLACEHOLDER SLIDE" tag for them. The suggestions
> below are starting points — confirm the details against your notebooks before presenting.

---

## Slide 8 — KNN Model

**Status:** placeholder.

Suggested bullet directions (pick ~4):
- The recommender is a **k-nearest-neighbours** search over album feature vectors.
- Feature space = the stacked blocks (genre, popularity, country, year, …).
- Similarity metric (cosine) finds the closest albums to a query.
- Baseline behaviour / first results — what "good" looked like early on.

Talking points:
- Explain the core idea simply: every album is a **point in feature space**; recommendations are
  its **nearest neighbours**.
- Describe how the feature blocks combine into one vector and why cosine similarity suits sparse,
  high-dimensional genre data.
- Mention any baseline/sanity checks (pick a famous album, show neighbours make sense).
- Note limitations of plain KNN that motivate tuning → slide 9.

*(Ref to confirm: notebooks under `4-model/`.)*

---

## Slide 9 — Model Tuning

**Status:** placeholder.

Suggested bullet directions (pick ~4):
- Each feature block has a **weight**; tuning finds the best balance.
- How we evaluated (the eval metric / held-out checks).
- Best weights are saved and reused (`best_weights.json`).
- What tuning changed — better, more relevant neighbours.

Talking points:
- The key lever: **per-block weights** (how much genre vs popularity vs country, etc.).
- Walk through the tuning process — search/eval loop, what metric you optimised, how you avoided
  overfitting to a few favourite albums.
- Show a before/after example if you have one (neighbours improving after tuning).
- Connect to the app: the tuned weights become the **defaults**, but users can still override
  them with the sliders → hand off to Nijat.

*(Ref to confirm: `4-model/` tuning notebooks; `data/best_weights.json`.)*
