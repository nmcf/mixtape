# Popularity Feature — overview and improvement notes

Covers `2-eda/03-EDA-popularity.ipynb`, `3-features/04-feature-ratings.ipynb`, and
`3-features/13-feature-lastfm-popularity.ipynb`.

---

## How the feature works

Popularity is built from two independent signals — MusicBrainz user ratings and Last.fm
listener/scrobble counts — then stacked into a single block the app exposes as one "Popularity"
knob.

### Signal 1 — MusicBrainz ratings (`04-feature-ratings.ipynb`)

MusicBrainz lets users submit 0–100 ratings for albums and artists. Raw ratings are sparse
and vote-count skewed, so the notebook applies a **zero-anchored Bayesian weight**:

```
weighted_score = (R × v) / (v + C)      # C = 5
```

`R` is the raw rating (0–100), `v` is the vote count, `C = 5` is the prior strength.
Zero-anchoring means an album with no votes starts at 0 rather than the dataset mean —
unrated albums contribute nothing instead of pulling toward average. Dividing by 100
puts both album and artist scores on `[0, 1]`.

Artist ratings are aligned to the album index via `mb_artist_credit` (primary artist
as proxy for albums that have no direct rating). Two sparse matrices are exported:
- `album_ratings_matrix.npz` — direct album ratings
- `artist_ratings_matrix.npz` — primary artist rating mapped to each album

Coverage: ~5% of albums have a direct rating (~88k of 1.75M).

### Signal 2 — Last.fm popularity (`13-feature-lastfm-popularity.ipynb`)

Last.fm data is scraped separately and provides four numeric columns per album:
`album_listeners`, `album_scrobbles`, `artist_listeners`, `artist_scrobbles`.

The notebook:
1. Cleans strings (comma-separated numbers, `"N/A"`, `"None Found"` → 0)
2. Normalises names (lowercase, strip special chars, collapse whitespace) and deduplicates
   by keeping the highest-scrobbles row per `(artist_norm, album_norm)` pair
3. Matches against MusicBrainz albums via `mb_album_artists.parquet` on the normalised keys
4. Min-max scales all four columns independently to `[0, 1]`
5. Writes a sparse LIL → CSR matrix: `album_lastfm_popularity_matrix.npz` (1.76M × 4)

Coverage: ~14% of albums matched (~252k of 1.75M).

### Downstream stacking

Both matrices follow the same row order as `album_ids.pkl`. They are horizontally stacked
with the other feature blocks in the main assembly notebook. In the app (`5-app/config.py`,
`5-app/engine.py`), all popularity columns are tied to a single **Popularity** knob that
scales them together in the `weighted_cosine` call.

---

## Coverage summary

| Signal | Covered albums | Share |
|---|---|---|
| MusicBrainz ratings (direct) | ~88k | ~5% |
| Last.fm listeners/scrobbles | ~252k | ~14% |
| Either signal | ~300k (est.) | ~17% |

For ~83% of the catalogue, all popularity columns are zero — the knob has no effect on
those albums regardless of how it is set.

---

## Improvement suggestions

### 1. Combine artist ratings earlier as a fallback, not a separate matrix

`04` exports `artist_ratings_matrix.npz` separately and leaves the merge to the assembly
notebook. But every album already has a primary artist; artist ratings could be merged
directly in `04` as a single "best available" column:

```python
# album rating if it exists, else artist rating, else 0
merged = album_ratings.copy()
no_direct = merged.data == 0         # or: (merged == 0) for dense
merged[no_direct] = artist_ratings[no_direct]
```

This halves the number of rating matrices in the pipeline and makes the fallback behaviour
explicit rather than implicit in the assembly step.

### 2. Last.fm matching is brittle for edge cases

The name-normalisation join can silently drop or mis-match albums:
- **Split artist names** — e.g. "The Beatles" vs "Beatles" normalise differently
- **Multiple editions** — when an album has multiple Last.fm entries after deduplication,
  the highest-scrobbles row wins, which may be a reissue rather than the canonical release
- **No fuzzy fallback** — a single extra character (parenthetical year, live suffix) breaks
  the exact-match join entirely

A fuzzy match pass (e.g. RapidFuzz `token_sort_ratio ≥ 90`) over the unmatched residual
would likely recover another 1–3% of the catalogue without introducing many false positives.

### 3. Min-max scaling is fragile for the Last.fm columns

`album_scrobbles` and `artist_scrobbles` are long-tailed distributions. Min-max maps the
top-of-tail (e.g. The Beatles, Radiohead) to 1.0 and compresses almost everything else
into `[0, 0.1]`. A log-transform before scaling would spread mid-popularity albums across
a more useful range:

```python
df['album_scrobbles_scaled'] = np.log1p(df['album_scrobbles'])
# then min-max scale the log values
```

This better reflects perceptual popularity (going from 1k → 10k listeners is as meaningful
as 100k → 1M) and would make the Popularity knob feel more responsive across the full range.

### 4. The four Last.fm columns are highly correlated

The EDA shows `album_listeners` and `album_scrobbles` are strongly correlated (~r = 0.9+),
as are the corresponding artist columns. Carrying four columns that largely encode the same
signal inflates the Last.fm block's contribution to the cosine similarity relative to its
effective information content.

Two options:
- **Reduce to two columns** — `album_scrobbles` (best per-album signal) and `artist_scrobbles`
  (universal coverage proxy), dropping the listener duplicates
- **PCA to one column** — collapse all four into a single popularity score; simpler to reason
  about and easier to weight against the ratings signal

### 5. Bayesian prior `C = 5` is arbitrary

The comment in `04` describes `C = 5` as pragmatic. The value is never evaluated against a
held-out ground truth — it is just set once and left. Given that the median vote count for
rated albums is low, even a small change to `C` shifts which lightly-rated albums survive.

Worth running a quick sensitivity check: plot the distribution of `weighted_score` at
`C = 2`, `5`, `10`, `20` to confirm `5` sits in a stable region rather than near an
inflection point.

### 6. No coverage report at assembly time

Neither notebook logs how many albums end up with a non-zero popularity signal after stacking.
Adding a brief summary print at the end of `13` and the assembly notebook (total covered, share
by source, overlap between ratings and Last.fm) would make coverage regressions visible
immediately if the scraper or matching step changes.

---

## Summary

| Issue | Effort | Impact |
|---|---|---|
| Log-transform Last.fm scrobbles before min-max | Low | Medium — better knob feel across the range |
| Merge artist ratings as direct fallback in `04` | Low | Low — cleaner pipeline, same output |
| Add coverage report at assembly | Low | Low — observability |
| Reduce/collapse correlated Last.fm columns | Medium | Medium — cleaner feature weighting |
| Fuzzy-match fallback for unmatched Last.fm albums | Medium | Medium — ~1–3% more coverage |
| Sensitivity check on Bayesian prior `C` | Low | Low — confidence that `5` is appropriate |
