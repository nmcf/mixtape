# Year & Era Feature Review

## What exists today

### Era feature (`07-feature-era.ipynb` → `album_era_matrix.npz`)

One-hot matrix, 1,758,488 × 12. Each album gets exactly one non-zero column (or an all-zero
row if no year could be found). Built from a three-source fallback chain:

1. `mb_release_year.parquet` — canonical MB first-release year (most reliable)
2. `mb_album_country.parquet` — earliest country-specific release date
3. `mb_artist.parquet` — artist formation/birth year (noisiest — introduces
   comeback-album error for albums released long after the artist formed)

Five known data-entry errors manually corrected and verified. Any year > 2026 hard-capped to
Unknown.

**Era bins (12 columns):** Pre-1900, 1900–1949, then decade bins 1950s–2020s. Unknown albums
(~2.1%) get all-zero rows — no era column exists for Unknown.

**In the app:** loaded as the `era` block, default dial 4 (weight ≈ 0.73). Treated identically
to all other blocks in the weighted cosine formula.

### Year feature (`10-feature-year.ipynb` → `album_year_matrix.npz`)

Single-column matrix, aligned to `album_ids.pkl`. Year is min-max scaled to [0, 1]. Source is
`sql_feature_album_track_stats.parquet` using `first_release_year_imputed` (falls back to raw
`first_release_year`). Coverage: ~98.9% (997,497 non-zero rows). Scaler params saved to
`year_scaler.json`.

**Not in the app** and not in the assembly notebook. Built but unused.

---

## The overlap problem

Era and year encode the same underlying signal — when was this album released — just
differently: era is coarse (10-year bins) and year is fine (exact). Having both in the model
at the same time would double-count temporal proximity. If the Era knob is at dial 6 and a
Year knob is added at dial 6, the model is effectively weighting release period twice as much
as the user intended.

The question is whether the coarse-vs-fine distinction is worth exposing, and if so, how to
do it without confusing the user or double-counting.

---

## Options

### Option A — Keep era only (no change)

Era stays as-is. Year matrix stays unused.

**Good if:** the decade-level granularity is exactly the resolution users care about.
Recommending 1970s albums to match a 1970s seed is a clear, understandable signal. Users
don't need "sounds like it was released in 1973" vs "sounds like it was released in 1977."

**Problem:** within a decade the era knob becomes binary — a 1970 album and a 1979 album look
identical in era space. Users who want "albums from roughly the same period" lose all
intra-decade nuance.

---

### Option B — Replace era with year (swap)

Remove the Era dial and Era matrix. Add a Year dial backed by `album_year_matrix.npz`.

**Good if:** continuous temporal proximity is more useful than discrete era matching.

**Problem:** continuous year is harder to explain to users ("Year" is vague — is that release
year? Recording year?). Also the year matrix was built from `sql_feature_album_track_stats`
with imputation — a different, slightly noisier source than the era matrix's three-source
fallback chain. The era notebook has better data hygiene (manual corrections, hard caps,
explicit source tracking).

---

### Option C — Merge into a single combined temporal block

Build a new matrix that stacks the 12 era one-hot columns and the 1 continuous year column
side-by-side (1,758,488 × 13). Use one dial to weight the whole block. The cosine formula
treats the combined block as a single entity — albums close in era *and* close in exact year
get a higher similarity than albums in the same decade but at opposite ends of it.

**Mechanics:**

- Era columns already scaled 0/1 (one-hot). Year column is scaled [0, 1].
- Weight the era and year sub-columns independently before stacking:
  - `X_era * era_weight + X_year * year_weight` (via column-wise scaling before hstack)
  - Or expose separate era and year dials (see Option D)
- A single "Time" dial controls both; the relative weight between era and year is a fixed
  internal ratio (e.g. 1:0.5 favouring era, tunable in the notebook).

**Good because:**
- One dial in the UI, no user confusion about double-counting
- Intra-decade nuance from year column without changing the era matching behaviour much
- Single rebuild: replace `album_era_matrix.npz` in the app with the merged matrix
- Backward-compatible: the "era" block key in the app stays; just a wider matrix

**Trade-off:** the internal era:year ratio becomes a hyperparameter. It should be tuned via
`4-model/tuning/` before merging into the app.

---

### Option D — Two separate dials (Era + Year)

Keep the Era dial and add a separate Year dial. The user controls each independently.

**Good if:** power users genuinely want to tune "decade similarity" separately from "year
proximity." This is a real use case: "I want albums from the same era (1970s) but don't care
exactly which year" vs "I want albums released within 2–3 years of this one."

**Problem:** most users won't understand the distinction, and setting both dials high
double-counts temporal proximity. This is the option most likely to confuse.

**Mitigaton:** expose both dials but document that they are correlated; treat them as a
"coarse" and "fine" temporal tuning pair. Reasonable default: Era at dial 4, Year at dial 2
(year as a soft tiebreaker within an era, not a dominant signal).

---

## Recommendation

**Option C (merged temporal block) is the best starting point.**

Rationale:
- Era is already in the app and working. Year adds intra-decade nuance without introducing
  a second correlated dial that users would have to manage.
- A single "Time" or "Era" dial is easier to explain than two temporal dials.
- The merge is low-risk: the era columns dominate (11 era cols + 1 year col); the year column
  acts as a soft tiebreaker within an era rather than a competing signal.
- If the tuning shows the year sub-column adds noise rather than signal, it can be dropped
  without touching the app UI — just rebuild the matrix.

Option D (two dials) is worth keeping as a fallback if evaluation shows the merged block
loses something important.

---

## Implementation plan

### Step 1 — Data quality alignment

The year matrix (`10-feature-year.ipynb`) uses a different data source
(`sql_feature_album_track_stats` + imputation) to the era matrix (`mb_release_year.parquet`
+ fallback chain). Before merging them, align the year source:

- Update `10-feature-year.ipynb` to use the same three-source fallback chain as `07-feature-era.ipynb`
  (`release_group_meta_year` → `album_country_year` → `artist_begin_year`)
- Apply the same five manual corrections and the > 2026 hard cap
- This makes the year column a strict refinement of the era column — both are anchored to the
  same `best_year` value, so the combined block is internally consistent

The existing `album_era.parquet` already stores `best_year` and `best_year_source` per album.
`10-feature-year.ipynb` can load it directly instead of re-running the fallback chain:

```python
era_df = pd.read_parquet('../data/features/album_era.parquet',
                         columns=['album_id', 'best_year'])
# best_year is already cleaned, corrected, and capped
```

### Step 2 — Build the merged matrix

New notebook: `3-features/14-feature-temporal.ipynb` (or update `10-feature-year.ipynb`).

```
1. Load album_ids.pkl
2. Load album_era_matrix.npz (12 cols, already built)
3. Load best_year from album_era.parquet; scale to [0, 1] using the same year range
4. Build year_col: sparse (n_albums × 1), zero for Unknown albums (consistent with era)
5. Scale year_col by an internal weight ratio (start with 0.5 relative to era cols)
6. hstack([era_matrix * 1.0, year_col * 0.5]) → album_temporal_matrix.npz
7. Save to data/features/album_temporal_matrix.npz
```

The internal 1.0:0.5 era:year ratio is a starting point. Tune via
`4-model/tuning/` using the Last.fm evaluator (`06-evaluate-lastfm.ipynb`).

### Step 3 — Swap in the app

In `5-app/app_v3_weighted.py`:

```python
BLOCK_FILES = {
    ...
    'era': 'album_temporal_matrix.npz',   # was album_era_matrix.npz
    ...
}
BLOCK_LABELS = {
    ...
    'era': 'Era',   # label unchanged — user sees no difference
    ...
}
```

No UI change required. The Era dial still controls the temporal block; users don't need to
know the block now includes an intra-decade year signal.

### Step 4 — Evaluate

Run `4-model/06-evaluate-lastfm.ipynb` comparing:
- Baseline: era-only (`album_era_matrix.npz`)
- Merged: era + year (`album_temporal_matrix.npz`) at the default 1.0:0.5 ratio
- Merged at 1.0:1.0 ratio (equal weighting)
- Year-only as a sanity check

Report HR@10 / Precision@10 / MRR@10 for each. If the merged block does not improve on era-only
at any ratio, year adds no useful signal and Option A (keep era only) is correct.

### Step 5 — Retire or keep `10-feature-year.ipynb`

If Step 4 shows the year signal helps: keep `10-feature-year.ipynb` as a reference but
supersede it with `14-feature-temporal.ipynb` as the canonical source for temporal features.

If year adds no signal: mark `10-feature-year.ipynb` as archived, leave `album_year_matrix.npz`
in `archive/`, and keep the era block as-is.

---

## Open questions

- What era:year internal ratio is optimal? Start at 1.0:0.5; tune via evaluator.
- Does the artist-begin fallback introduce more noise than signal? The EDA shows that albums
  with `best_year_source = artist_begin` are the noisiest group — consider excluding them from
  the year column (zero them out) even if they keep their era bin.
- For Unknown-era albums (2.1%), should the year column also be zeroed, or can it provide a
  signal even without an era bin? Current plan: zero both for consistency.

---

## Files touched by this work

| File | Change |
|---|---|
| `3-features/07-feature-era.ipynb` | No change — era matrix stays as-is until evaluation |
| `3-features/10-feature-year.ipynb` | Update to use `album_era.parquet` as year source; rebuild matrix |
| `3-features/14-feature-temporal.ipynb` | New notebook: build merged temporal matrix |
| `data/features/album_temporal_matrix.npz` | New: merged era + year matrix |
| `data/features/album_year_matrix.npz` | Rebuilt with aligned year source (move to archive if year adds no signal) |
| `5-app/app_v3_weighted.py` | Swap `album_era_matrix.npz` → `album_temporal_matrix.npz` in `BLOCK_FILES` |
| `4-model/tuning/` | New tuning run comparing era-only vs merged |
