# AI Context — sql_features branch

## What this branch is doing

Adding two new feature blocks (artist country + album track statistics) to the existing KNN recommendation model. The goal is to see whether geography and structural audio metadata improve recommendation quality beyond the baseline tag/label/rating features.

## Data source

MusicBrainz PostgreSQL database, accessed via DuckDB's `postgres_scanner` extension. All Postgres tables are snapshotted into DuckDB once at the start of each SQL script, then all subsequent work runs entirely in DuckDB (no cross-process round-trips).

## How the feature pipeline fits into the broader project

```
Postgres (MusicBrainz)
        │
        ▼
  DuckDB snapshot (SQL scripts in queries/)
        │
        ├── mb_artist_country_fast_duckdb_release.sql
        │       → artist_country_fast table
        │       → exported to data/sql_feature_artist_country_fast.parquet
        │
        └── mb_album_stats_duckdb.sql
                → album_stats table
                → exported to data/sql_feature_album_track_stats.parquet

Parquet files
        │
        ├── weights-country.ipynb
        │       → data/features/album_country_matrix.npz   (1,008,102 × 2,263)
        │
        └── weights-track-stats.ipynb
                → data/features/album_track_stats_matrix.npz  (1,008,102 × 12)

Feature matrices
        │
        └── knn-v2.ipynb
                → hstack with baseline matrices (tags, labels, types, ratings)
                → column prune → L2 normalise → NearestNeighbors fit
                → data/model_v2/knn_model_v2.joblib  (+ norm matrix + id arrays)

Models
        │
        └── app_sql_v2.py  (Streamlit)
                → loads v1 + v2 models
                → side-by-side recommendation comparison
```

## Key design decisions

**Country downweighted to 0.2** — at full weight, the country one-hot columns dominated cosine similarity because they are dense (most albums have exactly one country signal) whereas tag/label columns are very sparse. The notebook comment suggests tuning between 0.1 and 0.5.

**Canonical release selection** — the album stats query picks exactly one release per release group (earliest date, then lowest ID) to avoid inflating track counts when an album has multiple releases (reissues, deluxe editions, etc.).

**10-signal country imputation** — 62% of MusicBrainz artists have no direct area set. The SQL resolves country via a priority chain of 10 independent signals (AR links, label areas, release countries, etc.), recovering a country for ~30% of those artists.

**Safe column pruning** — before fitting the KNN model, columns whose non-zero count is below the minimum across all annotated albums are dropped. This ensures every annotated album has at least one non-zero feature after pruning, preventing cosine similarity from being undefined.

## Schema — artist_country_fast

| Column | Type | Description |
|---|---|---|
| `artist_id` | INTEGER | MusicBrainz internal artist ID |
| `artist_name` | VARCHAR | Artist name |
| `area_id` | INTEGER | area.id from artist.area (nullable) |
| `area_name` | VARCHAR | Human-readable area name |
| `country_id` | INTEGER | Resolved country area ID (nullable if area is a sub-national region with no parent) |
| `area_is_missing` | BOOLEAN | True when artist.area is NULL |
| `country_id_imputed` | INTEGER | Best available country ID (own country if known, else imputed from signals) |

## Schema — album_stats

| Column | Type | Description |
|---|---|---|
| `release_group_id` | INTEGER | MusicBrainz release group ID |
| `first_release_year` | INTEGER | Year of canonical release (nullable) |
| `medium_count` | SMALLINT | Number of discs |
| `track_count` | SMALLINT | Total tracks across all mediums |
| `track_count_with_length` | SMALLINT | Tracks that have a length value |
| `pct_tracks_with_length` | FLOAT | Coverage % |
| `total_length_ms` | BIGINT | Sum of all track lengths |
| `mean_length_ms` | INTEGER | Average track length |
| `median_length_ms` | INTEGER | Median track length |
| `stddev_length_ms` | INTEGER | Standard deviation of track lengths |
| `variance_length_ms` | BIGINT | Variance |
| `min_length_ms` | INTEGER | Shortest track |
| `max_length_ms` | INTEGER | Longest track |
| `range_length_ms` | INTEGER | max − min |
| `p25_length_ms` | INTEGER | 25th percentile track length |
| `p75_length_ms` | INTEGER | 75th percentile track length |
| `iqr_length_ms` | INTEGER | p75 − p25 |

## Feature matrix used in model v2

12 columns selected from album_stats (excludes `pct_tracks_with_length`, `track_count_with_length` as data-quality flags; `variance_length_ms` and `range_length_ms` as redundant). Each column is min-max scaled to [0, 1] before building the sparse matrix.

## Files to run in order (to reproduce model v2)

1. `07_impute_artist_country.ipynb` — produces `sql_feature_artist_country_fast.parquet`
2. `08_build_album_track_stats.ipynb` — produces `sql_feature_album_track_stats.parquet`
3. `weights-country.ipynb` — produces `album_country_matrix.npz`
4. `weights-track-stats.ipynb` — produces `album_track_stats_matrix.npz`
5. `knn-v2.ipynb` — produces `data/model_v2/` artefacts
6. `app_sql_v2.py` — `streamlit run sql_features/app_sql_v2.py`

Steps 1–2 require a running MusicBrainz Postgres instance and `.env` credentials (`PG_HOST`, `PG_PORT`, `PG_DBNAME`, `PG_USER`, `PG_PASSWORD`). Steps 3–6 only need the parquet files.

## Known issues

- `mb_artist_country_fast_duckdb_release.sql` line 2041: duplicate index name `idx_laa_e1` causes `pg_l_area_artist(entity1)` to be unindexed.
- `app_sql_v2.py` lines 1273, 1284: `width='stretch'` is not a valid `st.dataframe` kwarg (`use_container_width=True` is correct); causes TypeError when recommendations render.
- `app_sql_v2.py` lines 1208–1210: both models loaded at startup — app crashes if `data/model_v2/` files are absent.
