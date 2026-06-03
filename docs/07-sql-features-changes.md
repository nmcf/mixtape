# sql_features branch — Changes Overview

> **Historical record** of the original `sql_features` branch. File paths and figures predate the
> project restructure and the album-scope rebuild — `sql_features/*.ipynb` are now under
> `2-Prototyping/` (06–12), `app_sql_v2.py` is now `3-app/app_v2.py`. The bug notes below were
> addressed in later work. For current state see the top-level docs.

## What was added

This branch adds two new feature blocks to the KNN recommendation model and a side-by-side comparison app to evaluate the effect.

### New files

| File | Purpose |
|---|---|
| `queries/mb_artist_country_fast_duckdb_release.sql` | Builds `artist_country_fast` table in DuckDB |
| `queries/mb_album_stats_duckdb.sql` | Builds `album_stats` table in DuckDB |
| `07_impute_artist_country.ipynb` | Runs the country SQL and exports parquet |
| `08_build_album_track_stats.ipynb` | Runs the album stats SQL and exports parquet |
| `weights-country.ipynb` | Turns artist country into a sparse feature matrix |
| `weights-track-stats.ipynb` | Turns album track stats into a sparse feature matrix |
| `knn-v2.ipynb` | Builds the extended KNN model (v2) |
| `app_sql_v2.py` | Streamlit app comparing baseline vs extended model |

### New data artefacts (committed to repo)

- `data/sql_feature_artist_country_fast.parquet` — 2.86 M artists with imputed country
- `data/sql_feature_album_track_stats.parquet` — 2.24 M albums with track-length statistics

---

## Feature 1 — Artist Country

**SQL pipeline** (`mb_artist_country_fast_duckdb_release.sql`)

The query snapshots ~15 Postgres tables into DuckDB once, then resolves each artist's country using 10 signals in priority order:

1. `artist.area` — direct area column (ground truth)
2. `artist.begin_area` — area where artist was formed/born
3. `artist_release` materialised table — modal country across all releases
4. `artist_release_group` mat — first/modal country across all release groups
5. `l_area_artist` inverse AR — area explicitly linked to artist
6. `l_artist_label` AR — label's area
7. `l_artist_place` AR — place's area
8. Release country (local join) — modal country from release events
9. Release group first country — earliest release event country
10. Release group modal country — most common release event country

Areas that are not countries themselves are walked up the MusicBrainz area containment hierarchy (up to 3 levels) to find their parent country via the `l_area_area` "part of" relationship.

The result is stored in `artist_country_fast` with a `country_id_imputed` column (an integer area ID). 62% of artists have no direct area set; of those, ~30% can be imputed via one of the 10 signals.

**Feature matrix** (`weights-country.ipynb`)

- Joins `artist_country_fast` onto albums via `mb_album_artists`
- Builds a sparse one-hot matrix: one column per unique country ID
- Shape: `(1,008,102 albums × 2,263 countries)`, ~883 k non-zero entries
- Saved as `data/features/album_country_matrix.npz`

---

## Feature 2 — Album Track Statistics

**SQL pipeline** (`mb_album_stats_duckdb.sql`)

Builds `album_stats` for every album-type release group, keyed on `release_group_id`. The pipeline has 4 stages:

1. **Snapshot** — filters Postgres tables down to album release groups only (type = 1) and materialises them locally
2. **Canonical release** — picks one release per release group (earliest by date, then by ID) to avoid counting duplicate tracks
3. **Track-length percentiles** — computes p25/median/p75 per album using `PERCENTILE_CONT`
4. **Year imputation** — fills missing `first_release_year` via AR link dates or peer release group dates (commented out in the final table but staged)

Columns in `album_stats`: `release_group_id`, `first_release_year`, `medium_count`, `track_count`, `track_count_with_length`, `pct_tracks_with_length`, `total_length_ms`, `mean_length_ms`, `median_length_ms`, `stddev_length_ms`, `variance_length_ms`, `min_length_ms`, `max_length_ms`, `range_length_ms`, `p25_length_ms`, `p75_length_ms`, `iqr_length_ms`.

**Feature matrix** (`weights-track-stats.ipynb`)

- Loads 12 columns from `album_track_stats.parquet` (excludes `pct_tracks_with_length`, `track_count_with_length`, `variance_length_ms`, `range_length_ms` as redundant/data-quality flags)
- Fills nulls with column medians, then min-max scales each column to [0, 1]
- Aligns to the master `album_ids.pkl` index; drops explicit zeros to stay sparse
- Shape: `(1,008,102 × 12)`, ~11.1 M non-zero entries
- Saved as `data/features/album_track_stats_matrix.npz`

---

## Extended KNN Model v2 (`knn-v2.ipynb`)

Extends the baseline pipeline from `knn.ipynb` by appending the two new feature blocks:

| Block | Weight | Columns |
|---|---|---|
| Tags | 1.0 | 3,041 |
| Labels | 1.0 | 3,469 |
| Types | 1.0 | 10 |
| Ratings | 1.0 | 1 |
| **Country** | **0.2** | **2,263** |
| **Track stats** | **1.0** | **12** |

Country is downweighted to 0.2 because at weight 1.0 it dominated cosine similarity (a single dense binary column competing against thousands of sparse tag columns). The comment in the notebook suggests tuning between 0.1–0.5.

After hstack, the pipeline follows the same steps as v1: expand to full album universe, safe column pruning (threshold = 10), L2 normalisation, brute-force cosine NearestNeighbors fit. Model artefacts are saved to `data/model_v2/`.

---

## Comparison App (`app_sql_v2.py`)

Streamlit app that loads both models and shows their recommendations side-by-side for any selected album. Rows unique to one model are highlighted in amber; rows shared by both appear plain. A summary line counts shared vs unique recommendations per model.

---

## Known issues (from code review)

1. **Duplicate index name** in `mb_artist_country_fast_duckdb_release.sql` line 2041 — `idx_laa_e1` is used twice; the second `CREATE INDEX IF NOT EXISTS` on `pg_l_area_artist(entity1)` is silently skipped, leaving that column unindexed.

2. **Invalid Streamlit kwarg** in `app_sql_v2.py` lines 1273 and 1284 — `width='stretch'` is not a valid parameter for `st.dataframe`; should be `use_container_width=True`. Raises a TypeError whenever recommendations render.

3. **Unconditional model loading at startup** in `app_sql_v2.py` lines 1208–1210 — both models are loaded before any UI renders; if `data/model_v2/` files are missing the app crashes with no user-facing message.
