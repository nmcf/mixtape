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

---

## App integration — table dependencies and known issues

> **Status: errors observed in Explore and Find Similar tabs** (2026-06-11).

### Parquet files the feature pipeline writes and the app reads

| File | Written by | Read by app | Path |
|---|---|---|---|
| `mb_album_artists.parquet` | `1-data/01-postgres-to-parquet.ipynb` | `engine.load_lookup()` (direct path) | `data/` |
| `mb_album_country.parquet` | `1-data/03-feature-country-import.ipynb` | `engine.load_explore_data()` via `_find_parquet` | `data/` |
| `mb_album_tag.parquet` | `1-data/07-extract-tag-area.ipynb` | `engine.load_explore_data()` via `_find_parquet` | `data/` |
| `mb_tag.parquet` | `1-data/07-extract-tag-area.ipynb` | `engine.load_explore_data()` via `_find_parquet` | `data/raw/` |
| `mb_area.parquet` | `1-data/07-extract-tag-area.ipynb` | `engine.load_explore_data()` via `_find_parquet` | `data/raw/` |
| `mb_album_secondary_type.parquet` | `1-data/06-extract-secondary-type.ipynb` | `engine.load_secondary_types()` via `_find_parquet` | `data/raw/` |
| `album_ratings_matrix.npz` | `3-features/04-feature-ratings.ipynb` | `engine.load_blocks()` as `ratings` block | `data/features/` |
| `album_lastfm_popularity_matrix.npz` | `3-features/13-feature-lastfm-popularity.ipynb` | `engine.load_blocks()` as `popularity` block | `data/features/` |

### What moved and why

As part of commit `e8c6318` (App cleanup + data consolidation):

- `mb_tag.parquet`, `mb_area.parquet`, `mb_album_secondary_type.parquet` were moved from `data/` to `data/raw/`. The extraction notebooks `06` and `07` were updated to write to `../data/raw/`. The app was updated to use `_find_parquet()` which searches `data/raw/` first, then `data/`.

- **Album year data** moved: `mb_album.parquet` no longer has a `begin_date_year` column. Year now lives in `mb_album_country.album_year`. `engine.load_explore_data()` was updated to read from there. The Explore year slider now works where it previously silently failed.

### Root cause of current app errors

#### Bug 1 — Ratings index misalignment (affects Find Similar)

`04-feature-ratings.ipynb` loads `mb_album_ratings.parquet` into a DataFrame with a `RangeIndex` (0, 1, 2 …). The album_id is stored as a *column*, not the index. When the export cell calls:

```python
aligned_album_ratings = album_features.reindex(unique_album_ids)['weighted_score_norm'].fillna(0.0).values
```

`unique_album_ids` contains actual MusicBrainz album IDs (e.g., 4, 11, 37119 …). Pandas interprets these as positional row numbers against the RangeIndex — so album_id 4 gets row 4 of the ratings table, which is a completely different album. Ratings are assigned to the wrong albums across the entire matrix.

The same bug affects `artist_features.reindex(unique_artist_ids)` in the artist-ratings export.

**Fix required:** set the album_id column as the index before reindexing:

```python
aligned_album_ratings = (
    album_features.set_index('album_id')
    .reindex(unique_album_ids)['weighted_score_norm']
    .fillna(0.0).values
)
```

Same fix applies to `artist_features.set_index('artist_id')`.

The bug is pre-existing (the matrix on disk is already misaligned). It produces wrong ratings signal but not a Python exception — the app runs, but ratings-based recommendations are incorrect. The `album_ratings_matrix.npz` must be regenerated after the fix.

#### Bug 2 — `load_lookup()` uses a hardcoded path (fragile)

`engine.load_lookup()` reads:

```python
pd.read_parquet(os.path.join(DATA_DIR, 'mb_album_artists.parquet'), ...)
```

Unlike other parquets it does not go through `_find_parquet`. If `mb_album_artists.parquet` is ever moved to `data/raw/` (following the same pattern as `mb_tag.parquet`), `load_lookup()` would raise a `FileNotFoundError` and crash both tabs (lookup is used by both Find Similar and Explore results rendering).

**Fix:** wrap in `_find_parquet('mb_album_artists.parquet')` with a fallback error message.

#### Bug 3 — ~~`mb_album_tag.parquet` dual-location risk~~ (retracted)

On closer inspection, `07-extract-tag-area.ipynb` writes only `mb_tag.parquet` and `mb_area.parquet` to `data/raw/`. `mb_album_tag.parquet` is written by `01-postgres-to-parquet.ipynb` to `data/` and is read from there by the EDA and feature notebooks as well as the app (via `_find_parquet` fallthrough). There is no duplicate-location risk. No change needed.

### NPZ files regenerated

> **Status: done** (2026-06-11). Both matrices regenerated with the fixed logic.

| Matrix | State on disk |
|---|---|
| `album_lastfm_popularity_matrix.npz` | 1.76M × 2, log1p + min-max scrobbles, 252,167 albums (14.3%), fuzzy pass recovered 236 |
| `album_ratings_matrix.npz` | 1.76M × 1, correct index, merged direct (7.2%) + artist fallback (12.2%) = 341,083 albums (19.4%) |

The column-count change (4→2) is transparent to the app — `weighted_cosine` handles any column count.

### Content filter fixes (same session)

The Live Albums / Greatest Hits faders previously only filtered Find Similar results. Now applied
to all three surfaces: the album picker (`passes_content_filters()` in `app.py`), Find Similar
(`engine.recommend`), and Explore (`engine.explore_search`). Filter state echoed in the results
caption; sidebar warning when `mb_album_secondary_type.parquet` is missing.
