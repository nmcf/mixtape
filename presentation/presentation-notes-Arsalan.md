# Speaker Notes — Arsalan (Slides 6–7)

> **Template.** These slides are still placeholders in the deck. Fill in the `body` for slides 6
> and 7 in `presentation/index.html` (aim for ~4 single-line bullets each — see
> `presentation-style-guide.md`), then drop the "PLACEHOLDER SLIDE" tag for them. The suggestions
> below are starting points — confirm the details against your notebooks before presenting.

---

## Slide 6 — Last.fm Web Scraping

**Status:** placeholder.

Suggested bullet directions (pick ~4):
- Why Last.fm: MusicBrainz has metadata but not **popularity** — Last.fm has listener &
  scrobble counts.
- Scraped listener + scrobble counts for every **(artist, album)** pair in our album set.
- **Parallel** scraper — multiple workers running at once to get through the volume.
- **Resumable & safe** — file-locking prevents write clashes; re-runs skip rows already scraped.
- Scale/result: ended up with ~**200k+ rows** of popularity data.

Talking points:
- Frame the gap: recommendations shouldn't only be "similar genre" — **how popular** an album is
  matters too, and that data isn't in MusicBrainz.
- Walk through the scraping approach (source pages, what fields you grabbed, rate limiting).
- Highlight the engineering: making it **parallel and resumable** so a long scrape could be
  paused/restarted and split across workers without duplicating work.
- Mention data-quality gotchas (e.g. counts stored as comma-formatted strings, missing albums)
  and that cleaning happens in the popularity feature step → slide 7.

*(Ref to confirm: `1-data/05-lastfm-scraper.ipynb`; output `data/lastfm_data.parquet`.)*

---

## Slide 7 — Popularity Feature

**Status:** placeholder.

Suggested bullet directions (pick ~4):
- Turned raw Last.fm counts into a **normalized popularity feature** per album.
- Cleaned the messy inputs (string → numeric, missing values).
- Combined artist-level and album-level signals (listeners vs scrobbles).
- How it slots into the model — its own weighted block the user can tune.

Talking points:
- Explain *why normalize*: raw counts span many orders of magnitude (power-law again) — likely a
  log/scaled transform so a few megahits don't dominate.
- What the final feature looks like (one value per album? a small block?) and how it aligns
  row-for-row with the other feature matrices.
- Tie back to the tagline: popularity is one of the knobs users can **tune** in the app.
- Hand off to Nils (model).

*(Ref to confirm: `3-features/13-feature-lastfm-popularity.ipynb`.)*
