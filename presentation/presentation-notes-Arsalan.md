# Speaker Notes — Arsalan (Slides 5–6)

Talking points based on the current slide content. Bullets on the slides are the headlines;
these notes are what to say around them.

---

## Slide 5 — Last.fm Web Scraping

**On slide:** MusicBrainz has no listener data · listener & scrobble counts at artist and album
level · up to 4 parallel workers · fully resumable.

Talking points:
- Frame the gap: MusicBrainz has rich metadata but no listening data. How many people actually
  listen to an album is a strong popularity signal that MusicBrainz simply doesn't have.
- Explain **scrobbles**: Last.fm logs every play as a "scrobble" — so scrobble count is total
  plays across all users, while listener count is unique users. Listeners = reach,
  scrobbles = loyalty / repeat listens.
- The catalog is large (~1.75M albums), so scraping one by one would take too long. We ran up to
  **4 workers in parallel**, each covering a different slice of the album list at the same time.
- Engineering detail worth mentioning: all workers write to the same shared file safely, and
  each run rebuilds a done-set from what's already saved — so you can stop and restart without
  re-scraping anything.

*(Ref: `1-data/05-lastfm-scraper.ipynb`; output `data/lastfm_data.parquet`.)*

---

## Slide 6 — Popularity Feature

**On slide:** Last.fm listener counts and MusicBrainz community ratings · scores weighted by
confidence · no-rating albums inherit artist score · popular albums tend to be well-rated,
both sync to the Popularity dial.

Talking points:
- Two complementary signals: **play counts from Last.fm** (~14% of albums covered) and
  **star ratings from MusicBrainz** (~5% covered). Different sources, different angles on
  the same idea of how well-regarded an album is.
- Ratings are sparse — most albums have none at all. A raw average is unreliable here: one
  5-star rating looks identical to 10,000. We use a **Bayesian formula** that weights the
  score by how many votes it has. With our constant of 5, you need roughly 5 ratings before
  the score carries half its weight — a single vote barely moves the needle.
- For albums with no direct rating (~95%), we fall back to the **artist's rating as a proxy**.
  Not perfect, but better than leaving the signal at zero.
- The key insight from the EDA: **popular albums and well-rated albums are positively
  correlated**. That's why the app syncs both signals to a single **Popularity dial** — one
  control for "how much should fame and reputation influence my recommendations?"
- Hand off to Nils (model).

*(Ref: `2-eda/03-EDA-popularity.ipynb`, `3-features/04-feature-ratings.ipynb`,
`3-features/13-feature-lastfm-popularity.ipynb`.)*
