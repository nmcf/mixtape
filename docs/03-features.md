# Feature Engineering

**Notebooks:** `2-Prototyping/01-feature-tags-labels.ipynb`, `2-Prototyping/02-feature-ratings.ipynb`, `2-Prototyping/03-feature-assembly.ipynb`

Transforms the enriched DataFrames into sparse numeric matrices suitable for the KNN model.

## Output files (`data/features/`)

| File | Description |
|------|-------------|
| `album_ids.pkl` | Ordered list of album IDs — the row index for all matrices |
| `album_tags_matrix.npz` | Sparse matrix: albums × tag vocabulary |
| `album_labels_matrix.npz` | Sparse matrix: albums × label IDs |
| `album_types_matrix.npz` | Sparse matrix: albums × album type |
| `album_ratings_matrix.npz` | Sparse matrix: albums × Bayesian-weighted rating score |
| `album_primary_artist_ratings_matrix.npz` | Sparse matrix: albums × primary artist weighted rating |
| `artist_ids.pkl` | Ordered list of artist IDs |
| `artist_tags_matrix.npz` | Sparse matrix: artists × tag vocabulary |
| `artist_ratings_matrix.npz` | Sparse matrix: artists × Bayesian-weighted rating |

## Rating weighting

Raw `(rating, rating_count)` pairs are converted to a **zero-anchored Bayesian weighted score** before being entered into the feature matrices:

```
weighted_score = (R × v) / (v + C)
```

- `R` = raw rating value (0–100)
- `v` = rating vote count
- `C` = confidence constant (default = 5)

When `v = 0` the formula collapses to `0`, pulling unrated items toward a neutral baseline rather than inflating them. The score is then normalised to `[0, 1]` by dividing by 100.

This is intentional for sparse ML features where fewer than 5% of items have any ratings — it avoids giving a single-vote item the same weight as a well-rated one.

## Feature matrix assembly

The four per-album feature blocks are stacked horizontally:

```
X_final_album_knn = hstack([X_tags, X_labels, X_types, X_ratings])
```

| Block | Shape example | What it encodes |
|-------|---------------|-----------------|
| `X_tags` | albums × ~N tags | Genre/style tags from MusicBrainz community votes |
| `X_labels` | albums × ~M labels | Record label identity |
| `X_types` | albums × ~K types | Release type encoding |
| `X_ratings` | albums × 1 | Bayesian-weighted album rating |

## Column pruning

Columns with fewer than `safe_threshold` non-zero entries are pruned. The threshold is set to the minimum "best column nnz" across all albums that have any features — guaranteeing no album loses all its signal:

```python
safe_threshold = int(max_col_nnz_per_album[has_features].min())
X_knn = X_final_album_knn[:, col_nnz >= safe_threshold]
```

## Feature sparsity

The resulting matrix is highly sparse. See `2-Prototyping/sparse_features_structural_analysis.png` for a visual breakdown of column nnz distributions across all four blocks.

Albums with zero non-zero entries across the entire matrix are flagged as `has_features = False` and excluded from model training. At query time, selecting one of these albums returns "no recommendations available".
