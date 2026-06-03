# How to rebuild the feature pipeline and run the app

Covers the country / track-stats / genre features and the v2 and v3 models. The current app
(`app_v3_weighted.py`) needs only the feature matrices — you do **not** need to train a model to
run it. Train v2/v3 only if you want the comparison apps.

## Prerequisites

- Python environment with dependencies installed (`pip install -r requirements.txt` from the project root)
- The base parquets + v1 features already built (notebooks `1-EDA/01`–`02`, `2-Prototyping/01`–`04`)

---

## Step 1 — Artist country parquet

> **Already in the repo — skip unless regenerating.** `data/sql_feature_artist_country_fast.parquet` is committed.

**Only if regenerating:** needs a running MusicBrainz PostgreSQL instance and a `.env` in the project root:

```
PG_HOST=
PG_PORT=
PG_DBNAME=
PG_USER=
PG_PASSWORD=
```

Run all cells in `2-Prototyping/06-impute-artist-country.ipynb`. Connects to Postgres via DuckDB,
runs the country imputation SQL, and overwrites `data/sql_feature_artist_country_fast.parquet`.
Runtime: several minutes.

---

## Step 2 — Album track stats parquet

> **Already in the repo — skip unless regenerating.** `data/sql_feature_album_track_stats.parquet` is committed.

**Only if regenerating:** same Postgres + `.env` setup. Run all cells in
`2-Prototyping/07-build-album-track-stats.ipynb`, which overwrites
`data/sql_feature_album_track_stats.parquet`.

---

## Step 3 — Build the country feature matrix

Run all cells in `2-Prototyping/08-feature-country.ipynb` → writes `data/features/album_country_matrix.npz`.

Expected: `X_country shape: (1758488, 2014)`, ~1.70 M non-zero entries.

---

## Step 4 — Build the track stats feature matrix

Run all cells in `2-Prototyping/09-feature-track-stats.ipynb` → writes `data/features/album_track_stats_matrix.npz`.

Expected: `X_track_stats shape: (1758488, 12)`, ~19.3 M non-zero entries.

---

## Step 5 — Build the genre tag matrix (v3 only)

Run all cells in `2-Prototyping/10-feature-genre-tags.ipynb` → writes `data/features/album_genre_matrix.npz`.

Combines album + artist + label tags. Expected: `(1758488, 10255)`, ~5.9 M non-zero entries.

---

## Step 6 — Train the models (optional — only for the comparison apps)

- **v2:** `2-Prototyping/11-knn-v2-training.ipynb` → `data/model_v2/` (tags + labels/types + ratings + country + track stats)
- **v3:** `2-Prototyping/12-knn-v3-training.ipynb` → `data/model_v3/` (genre + record_label + ratings + country + track stats)

Each combines its feature blocks, prunes, L2-normalises, fits a brute-force cosine
`NearestNeighbors`, and saves the model + matrix + album-ID index. The sanity-check cell should
print cosine distances > 0 for the top neighbours (0.0 only for the query album itself).

These model artefacts are gitignored (large); the weighted app below doesn't use them.

---

## Step 7 — Run the app

From the project root:

```bash
streamlit run 3-app/app_v3_weighted.py
```

This serves recommendations from the v3 feature blocks and exposes a slider per feature (genre,
record label, ratings, country, track stats) so you can reweight in real time. It reads the raw
feature matrices directly — no trained model required. Various-Artists releases (null artist) are
excluded from recommendations.

The older comparison apps (`3-app/app_v2.py`, `3-app/app_v3.py`) show models side-by-side and do
require the trained `.joblib` artefacts from step 6.

---

## Tuning the country feature weight

In the weighted app, just move the **Country** slider. To change the *baked* default used when
training v2/v3, edit `W_COUNTRY` in the `assemble` cell of the relevant training notebook and
retrain:

```python
W_COUNTRY = 0.1   # try 0.1 – 0.5; default is 0.2
```

No need to re-run steps 1–5 — the parquets and feature matrices don't change.
