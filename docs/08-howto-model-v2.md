# How to use the extended model (v2)

## Prerequisites

- Python environment with dependencies installed (`pip install -r requirements.txt` from the project root)

---

## Step 1 — Artist country parquet

> **Already in the repo — skip this step unless you need to regenerate the data.**
>
> `data/sql_feature_artist_country_fast.parquet` is committed and ready to use.

**Only run this if you need to regenerate:**

You will need a running MusicBrainz PostgreSQL instance and a `.env` file in the project root:

```
PG_HOST=
PG_PORT=
PG_DBNAME=
PG_USER=
PG_PASSWORD=
```

Open and run all cells in `sql_features/07_impute_artist_country.ipynb`. This connects to Postgres via DuckDB, runs the country imputation SQL, and overwrites `data/sql_feature_artist_country_fast.parquet`. Runtime: several minutes. The notebook prints a summary table at the end — check that `total_artists` is in the millions and `with_country_id_imputed` is non-zero before continuing.

---

## Step 2 — Album track stats parquet

> **Already in the repo — skip this step unless you need to regenerate the data.**
>
> `data/sql_feature_album_track_stats.parquet` is committed and ready to use.

**Only run this if you need to regenerate:**

Requires the same Postgres + `.env` setup as step 1.

Open and run all cells in `sql_features/08_build_album_track_stats.ipynb`. This snapshots track data from Postgres, computes per-album statistics, and overwrites `data/sql_feature_album_track_stats.parquet`. Runtime: several minutes. The notebook prints a stats summary — confirm `total_albums` is ~2.2 M and `no_tracks` is 0.

---

## Step 3 — Build the country feature matrix

Open and run all cells in `sql_features/weights-country.ipynb`.

Reads the parquet from step 1 and writes:

```
data/features/album_country_matrix.npz
```

Expected output: `X_country shape: (1008102, 2263)`, ~883 k non-zero entries.

---

## Step 4 — Build the track stats feature matrix

Open and run all cells in `sql_features/weights-track-stats.ipynb`.

Reads the parquet from step 2 and writes:

```
data/features/album_track_stats_matrix.npz
```

Expected output: `X_track_stats shape: (1008102, 12)`, ~11 M non-zero entries.

---

## Step 5 — Train the v2 KNN model

Open and run all cells in `sql_features/knn-v2.ipynb`.

This combines all feature blocks (tags, labels, types, ratings from the baseline + the two new blocks from steps 3–4), normalises, prunes, and fits a NearestNeighbors model. It writes three artefacts:

```
data/model_v2/knn_model_v2.joblib
data/model_v2/X_knn_norm_v2.npz
data/model_v2/album_ids_annotated_v2.npy
```

The sanity check cell at the end should print cosine distances > 0 for the top neighbours (distance 0.0 only for the query album itself). If all distances are 0.0, something went wrong in normalisation.

---

## Step 6 — Run the comparison app

From the project root:

```bash
streamlit run sql_features/app_sql_v2.py
```

The app loads both the baseline model (v1, from `data/model/`) and the extended model (v2, from `data/model_v2/`). Search for an artist, select an album, and you'll see recommendations from both models side-by-side. Rows highlighted in amber are unique to that model; plain rows appear in both.

> **Note:** The app requires the v1 model artefacts to already exist in `data/model/`. If you haven't run the baseline pipeline yet, do that first (`knn.ipynb` in the main project).

---

## Tuning the country feature weight

If country is dominating the v2 recommendations (everything is from the same country as the input album), reduce `W_COUNTRY` in `knn-v2.ipynb` cell `assemble` and re-run from step 5:

```python
W_COUNTRY = 0.1   # try 0.1 – 0.5; default is 0.2
```

No need to re-run steps 1–4 — the parquet and feature matrices don't change.
