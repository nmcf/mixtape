# Rebuilding the pipeline

How to regenerate the data, feature matrices, and run the app from scratch. The current app (`app/app.py`) reads raw feature matrices directly — no trained model required.

All parquets are committed to the repo. If you just want to run the app, skip straight to [Step 11](#step-11--run-the-app) — the feature matrices in `data/features/` are also committed.

---

## Prerequisites

- Python environment with dependencies installed: `pip install -r requirements.txt`
- **Steps 1–3 only:** a running MusicBrainz PostgreSQL instance. Copy `.env.example` to `.env` and fill in your credentials:

```
PG_HOST=
PG_PORT=
PG_DBNAME=
PG_USER=
PG_PASSWORD=
```

---

## Step 1 — Import base parquets

> **Already in the repo — skip unless regenerating.** The base MusicBrainz parquets are committed under `data/metadata/`.

**Only if regenerating:** run all cells in `development/1-data/01-postgres-to-parquet.ipynb`. Connects to Postgres via DuckDB and exports the core MusicBrainz tables (albums, artists, tags, labels, ratings, flags) as parquet files to `data/metadata/`.

---

## Step 2 — Import artist country parquet

> **Already in the repo — skip unless regenerating.** `data/metadata/sql_feature_artist_country_fast.parquet` is committed.

**Only if regenerating:** run all cells in `development/1-data/03-feature-country-import.ipynb`. Runs the country imputation SQL (`development/1-data/queries/mb_artist_country_fast_duckdb_release.sql`) against Postgres via DuckDB and overwrites `data/metadata/sql_feature_artist_country_fast.parquet`. Runtime: several minutes.

---

## Step 3 — Import track stats parquet

> **Already in the repo — skip unless regenerating.** `data/metadata/sql_feature_album_track_stats.parquet` is committed.

**Only if regenerating:** run all cells in `development/1-data/04-feature-track-stats-import.ipynb`. Runs `development/1-data/queries/mb_album_stats_duckdb.sql` against Postgres via DuckDB and overwrites `data/metadata/sql_feature_album_track_stats.parquet`.

---

## Step 4 — Build album/artist ID index

Run all cells in `development/3-features/01-album-artist-index.ipynb` → writes `data/index/album_ids.pkl` and `data/features/artist_ids.pkl`.

This index must exist before running any of the feature matrix notebooks.

---

## Step 5 — Build genre matrix

Run all cells in `development/3-features/02-feature-genre.ipynb` → writes `data/features/album_genre_matrix.npz` and `data/features/album_tags_matrix.npz`.

Combines album + artist + label tags via a three-tier blend (universal artist tags, masked label reinforcement, allowlist label rescue — see [development/docs/03-features.md](development/docs/03-features.md)). Expected: `(1758488, 10255)`, ~5.45 M non-zero entries, covering 68.8% of albums.

---

## Step 6 — Build label matrix

Run all cells in `development/3-features/03-feature-label.ipynb` → writes `data/features/album_record_label_matrix.npz`.

---

## Step 7 — Build ratings matrix

Run all cells in `development/3-features/04-feature-ratings.ipynb` → writes `data/features/album_ratings_matrix.npz`.

Uses Bayesian-weighted ratings: `score = R·v / (v + C)`, C = 5. See [development/docs/03-features.md](development/docs/03-features.md) for details.

---

## Step 8 — Build country matrix

Run all cells in `development/3-features/05-feature-country.ipynb` → writes `data/features/album_country_matrix.npz`.

Expected: `(1758488, 2014)`, ~1.70 M non-zero entries.

---

## Step 9 — Build track stats matrix

Run all cells in `development/3-features/06-feature-track-stats.ipynb` → writes `data/features/album_track_stats_matrix.npz`.

Expected: `(1758488, 12)`, ~19.3 M non-zero entries.

---

## Step 10 — Build temporal matrix

Run all cells in `development/3-features/14-feature-temporal.ipynb` → writes:
- `data/features/album_era.parquet` — per-album best_year / era_bin (audit use)
- `data/features/album_era_matrix.npz` — era one-hot (10 cols)
- `data/features/album_temporal_matrix.npz` — era one-hot + continuous year (11 cols; this is what the app loads)
- `data/features/temporal_year_scaler.json` — year_min / year_max scaler params

Expected: temporal matrix `(1758488, 11)`, ~97.9% era coverage. The year column uses `YEAR_WEIGHT=0.3` (analytically determined — era-boundary smoothing only; see `development/2-eda/04-EDA-year.ipynb`).

---

## Step 11 — Run the app

From the project root:

```bash
streamlit run app/app.py
```

The app opens at **http://localhost:8501**. It loads the six feature matrices (genre, record label, ratings, country, track stats, temporal) directly — no trained model required. Sidebar **knobs** (0–11, guitar-amp style) set a weight per feature block; two vertical **faders** filter results by MusicBrainz release type (Live Albums, Greatest Hits).
