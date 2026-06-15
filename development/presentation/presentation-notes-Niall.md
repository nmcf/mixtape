# Speaker Notes — Niall (Slides 1–4)

Talking points based on the current slide content. Bullets on the slides are the headlines;
these notes are what to say around them.

---

## Slide 1 — Mixtape (intro)

**On slide:** tagline *"Tune the algorithm to your perfect sound."* + one-line summary.

Talking points:
- Set the scene: Mixtape is an **album recommendation engine**. You give it an artist/album you
  like and it surfaces similar albums.
- The twist vs. a black-box recommender: **you control the weights**. The tagline is literal —
  sliders let you tune how much genre, popularity, etc. drive the result. Hence the cassette /
  "tuning" theme.
- Quick intro of the team and who owns which part (Niall → data + genre, Arsalan → Last.fm +
  popularity, Nils → KNN + tuning, Nijat → weighted cosine + app).
- One sentence on the pipeline: source data → features → similarity model → app.

---

## Slide 2 — MusicBrainz

**On slide:** open-source encyclopedia · Postgres + Parquet · SchemaSpy + Claude skipping joins ·
artists, albums, tags, labels, areas & countries.

Talking points:
- **MusicBrainz** is the open, community-built encyclopedia of music metadata — our backbone for
  artists, albums, tags, labels, and more.
- We ran the **full MusicBrainz database locally in Postgres** (a complete mirror), then
  **exported just the slices we need into Parquet tables** — columnar, compressed, fast to read.
- The schema is large and unfamiliar with hundreds of tables. We ran **SchemaSpy** to generate a
  full diagram of it, then **pointed Claude at that diagram** — instead of writing exploratory
  SQL we just asked questions and got answers instantly. That's also how we found MusicBrainz's
  **precomputed tables**, which let us skip costly joins (e.g. resolving artist countries via
  the area hierarchy).
- Key tables we pulled: **artists, albums, tags, labels, areas & countries** — these feed every
  downstream feature.
- Segue: "The most important thing we pulled was the tag data — here's what we built from it."

---

## Slide 3 — Genre Feature

**On slide:** 3 tag sources blended (weighted 1.0 / 0.5 / 0.3) · noisy label tags, genre-coherent
ones trusted · genre hierarchy ~2.7k subgenres → ~20 parent families · ~68% blended coverage.

Talking points:
- Goal: a **genre signal per album** the similarity model can use.
- We blend **three tag sources**: album tags `1.0` (most direct), artist tags `0.5` (broader),
  label tags `0.3` (noisiest — a label aggregates tags across all its artists).
- Label tags need special handling: we only use **genre-coherent labels** (≥ 60% per-album
  overlap), and we use them to reinforce existing signal or rescue albums that have no tags at
  all via a trusted allowlist.
- Then a **coarse rollup**: ~2.7k fine subgenre tags collapse into ~20 parent families
  (e.g. death metal + black metal → metal) so albums in the same family relate even when their
  subgenres differ — similarity the fine tags alone would miss.
- The payoff: blending the three sources reaches **~68% coverage**, well above any single source.
- Segue: "All of this signal — and every other feature — gets stored the same way."

---

## Slide 4 — Feature Matrices

**On slide:** each feature is a table, one row per album · different angles · all line up ·
building blocks of the recommender.

Talking points:
- Every feature (genre, popularity, country, year, …) is stored as its own **sparse matrix**
  saved to a `.npz` file in `data/features/`.
- **Rows are albums, columns are feature values.** They're mostly zeros (most albums have only a
  few tags), so we use **sparse** matrices — far smaller and faster than dense arrays.
- Critically, every matrix is **row-aligned** to the same master album index, so row *N* is the
  same album in every file. That's what lets us stack blocks and compare albums consistently.
- In the app, **one slider maps to one feature block** — which is what makes the weighted-cosine
  tuning possible (Nijit's part).
- Hand off to Arsalan (Last.fm / popularity feature).
