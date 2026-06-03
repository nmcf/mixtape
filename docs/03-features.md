# Feature Engineering

**Notebooks:** `2-Prototyping/01` through `02` (v1 features), `08` through `10` (v2/v3 features)

Transforms raw MusicBrainz data into sparse numeric matrices for the KNN model. Three model versions use progressively richer feature sets.

## Feature matrices (`data/features/`)

| File | Shape | Description | Used in |
|------|-------|-------------|---------|
| `album_ids.pkl` | — | Master row index (album IDs) for all matrices | all |
| `artist_ids.pkl` | — | Master row index for artist matrices | — |
| `album_tags_matrix.npz` | 1M × 3,041 | Direct MusicBrainz album tags, vote-weighted | v1, v2 |
| `album_genre_matrix.npz` | 1M × 11,247 | Combined album + artist + label tags (see below) | v3 |
| `album_labels_matrix.npz` | 1M × 3,469 | Record label identity, vote-weighted | all |
| `album_types_matrix.npz` | 1M × 10 | Label type (e.g. original production, imprint) — **not** release type | all |
| `album_ratings_matrix.npz` | 1M × 1 | Bayesian-weighted album rating score | all |
| `album_country_matrix.npz` | 1M × 2,263 | One-hot primary artist country | v2, v3 |
| `album_track_stats_matrix.npz` | 1M × 12 | Track-length statistics, min-max scaled | v2, v3 |
| `artist_tags_matrix.npz` | — | Artist-level tags (built but blended into genre matrix, not used directly) | — |

## Rating weighting

Raw `(rating, rating_count)` pairs are converted to a **zero-anchored Bayesian weighted score**:

```
weighted_score = (R × v) / (v + C)
```

- `R` = raw rating value (0–100)
- `v` = rating vote count
- `C` = confidence constant (default = 5)

When `v = 0` the formula collapses to `0`. The score is then normalised to `[0, 1]` by dividing by 100.

## Genre tag matrix (`album_genre_matrix.npz`)

Built by `10-feature-genre-tags.ipynb`. Combines three tag sources into a single matrix:

| Source | Weight | Condition |
|--------|--------|-----------|
| Album tags (direct MusicBrainz tags) | 1.0 | Always |
| Artist tags | 0.5 | Only for albums with < 5 direct tags |
| Label tags | 0.3 | Always |

82.7% of albums have fewer than 5 direct tags, so artist tags are blended for the majority. Tags appearing fewer than 10 times across all sources are dropped. Rows are L1-normalised after combining so each album's profile sums to 1.0.

Result: 11,247 tag columns vs 3,041 in the original album-only matrix, with 5M non-zero entries vs 3M.

## Artist country matrix (`album_country_matrix.npz`)

Built by `08-feature-country.ipynb` from `sql_feature_artist_country_fast.parquet`. One-hot encoded per album using `country_id_imputed` from the artist country pipeline. 2,263 country columns.

The artist country parquet is produced by `06-impute-artist-country.ipynb`, which resolves each artist's country via 10 signals in priority order (direct area, begin area, release countries, AR links, label areas, etc.). 62% of artists have no direct area — ~30% of those are recovered via imputation.

## Track stats matrix (`album_track_stats_matrix.npz`)

Built by `09-feature-track-stats.ipynb` from `sql_feature_album_track_stats.parquet`. 12 columns per album:

`first_release_year`, `medium_count`, `track_count`, `total_length_ms`, `mean_length_ms`, `median_length_ms`, `stddev_length_ms`, `min_length_ms`, `max_length_ms`, `p25_length_ms`, `p75_length_ms`, `iqr_length_ms`

Each column is min-max scaled to [0, 1]. Nulls are filled with column medians before scaling.

## Feature assembly per model version

### v1
```python
X_final = hstack([X_tags, X_labels, X_types, X_ratings])
```

### v2
```python
X_final = hstack([
    X_tags * 1.0, X_labels * 1.0, X_types * 1.0, X_ratings * 1.0,
    X_country * 0.2, X_track_stats * 1.0
])
```

### v3
```python
X_final = hstack([
    X_genre * 1.0, X_labels * 1.0, X_types * 1.0, X_ratings * 1.0,
    X_country * 0.2, X_track_stats * 1.0
])
```

Country is downweighted to 0.2 because at w=1.0 it dominates cosine similarity — it is a dense single-column signal competing against thousands of sparse tag columns.

## Column pruning

Applied in all model training notebooks. Columns below `safe_threshold` nnz are dropped, where the threshold is the minimum "best column nnz" across all albums that have any features:

```python
safe_threshold = int(max_col_nnz_per_album[has_features].min())
X_knn = X_final[:, col_nnz >= safe_threshold]
```

This guarantees no album loses all its signal.

| Model | Features before prune | Features after prune |
|-------|-----------------------|----------------------|
| v1 | 6,521 | 5,647 |
| v2 | 8,796 | 5,854 |
| v3 | 17,002 | 9,810 |
