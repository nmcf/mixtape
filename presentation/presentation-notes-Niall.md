# Speaker Notes — Niall (Slides 1–5)

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
  popularity, Nils → KNN + tuning, Nijit → weighted cosine + app).
- One sentence on the pipeline: source data → features → similarity model → app.

---

## Slide 2 — MusicBrainz

**On slide:** what MusicBrainz is · hosted it in Postgres · exported to Parquet · key tables.

Talking points:
- **MusicBrainz** is the open, community-built encyclopedia of music metadata — our backbone for
  artists, albums, tags, labels, etc.
- We ran the **full MusicBrainz database locally in Postgres** (it's big — a complete mirror).
- We didn't query Postgres live for the app: we **exported just the slices we need into Parquet
  tables** (columnar, compressed, fast to read).
- Mention the most important tables we pulled: artists, albums, tags, ratings, labels, country
  areas — these feed every downstream feature.
- Segue: "Postgres is huge and unfamiliar — so how did we figure out the schema?" → slide 3.

---

## Slide 3 — Claude & SchemaSpy

**On slide:** SchemaSpy maps the DB · Claude answers from the diagram · tag tables · precomputed
tables / area graph.

Talking points:
- The problem: MusicBrainz has a **large, unfamiliar schema** with hundreds of tables. Manually
  querying Postgres to understand it is slow.
- We ran **SchemaSpy** to auto-generate a full diagram/HTML of the schema, committed into the
  repo so the structure was browsable.
- Then we **pointed Claude at that schema** — instead of writing exploratory SQL, we just asked
  questions and got the table/column/relationship answers instantly.
- Concrete wins to mention:
  - Mapped the **album / artist / record-label tag tables** (used heavily for the genre feature).
  - Found MusicBrainz's **precomputed (materialized) tables** so we could skip expensive joins —
    e.g. resolving an artist's country via the hierarchical area graph.
- Takeaway: AI-assisted schema exploration turned days of SQL spelunking into minutes.

---

## Slide 4 — Genre Feature

**On slide:** blended 3 tag sources · weighted tiers (1.0 / 0.5 / 0.3) · label reinforce + rescue
· subgenre → ~20 parent families.

Talking points:
- Goal: a **genre signal per album** the similarity model can use.
- We blend **three tag sources**: album tags, artist tags, and record-label tags.
- They're **weighted**: album tags `1.0` (most direct), artist tags `0.5` (broader), label tags
  `0.3` (noisiest).
- Label tags are used carefully — **reinforcement** (only boost tags an album/artist already
  has) plus **rescue** (trusted "allowlist" labels can add signal to albums with no tags at all).
- Then a **coarse rollup**: ~2.7k fine subgenre tags collapse into ~20 parent families
  (e.g. death metal + black metal → metal) so albums in the same family relate even across
  different subgenres — similarity the fine tags alone miss.
- Segue: "Building this taught us a lot about how MB tagging actually behaves" → slide 5.

---

## Slide 5 — Tag Insights

**On slide:** sparse power-law tags (albums ~46%, artists ~9%) · no formal taxonomy · noisy label
tags · ~68% blended coverage.

Talking points:
- **Tags are sparse and power-law.** Only ~46% of albums and ~9% of artists have any tags; a
  handful of tags cover most albums while a long tail covers almost nothing. (We prune tags with
  < 10 occurrences.)
- **MusicBrainz has no formal genre taxonomy** — tags are free-form. We built our own hierarchy
  via a substring heuristic + a manual audit (the parent-family map from slide 4).
- **Label tags are noisy.** A label aggregates tags across all its artists, so most don't
  describe an individual album — coherence is bimodal and *not* predicted by label size. We only
  trust genre-coherent labels (≥60% per-album overlap).
- The payoff: **blending the three sources reaches ~68% coverage**, well above any single source,
  because each fills the others' gaps.
- Hand off to Arsalan (Last.fm / popularity).
