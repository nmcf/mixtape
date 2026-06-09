# EDA Tags & Labels — review notes

> **Status: all changes implemented** (2026-06-09). See commit history for diff.

Covers `2-eda/05-EDA-tags-labels.ipynb`. Two categories of changes: removing the
archive NPZ dependency and structural code quality.

---

## 1. Drop the archive NPZ files

The notebook currently loads two v1 matrices from `archive/` for structural comparison:

| File | Used for |
|---|---|
| `album_tags_matrix.npz` | `tags_per_album`, album tag column popularity, `direct_tag_counts` (allowlist-coverage), `tag_col_counts` (column-pruning) |
| `album_labels_matrix.npz` | `labels_per_album`, label column popularity, `label_col_counts` (column-pruning) |

Every one of these can be derived directly from the raw parquets that the notebook already
loads for other cells. The archive files are not needed.

| Variable | Current source | Replacement |
|---|---|---|
| `tags_per_album` | `np.diff(X_album_tags.indptr)` | `mb_album_tag.parquet` → `groupby('album_id')['tag_id'].nunique()`, reindexed to `album_index` |
| Album tag column popularity | `X_album_tags.getnnz(axis=0)` | `groupby('tag_id')['album_id'].nunique().sort_values(ascending=False)` |
| `direct_tag_counts` (allowlist-coverage) | `np.diff(X_album_tags_saved.indptr)` | Same as `tags_per_album` — pass it in from the load cell |
| `tag_col_counts` (column-pruning) | `X_album_tags.getnnz(axis=0)` | Same album-tag group-by |
| `labels_per_album` | `np.diff(X_album_labels.indptr)` | `mb_album_label.parquet` → `groupby('album_id')['label_id'].nunique()`, reindexed to `album_index` |
| Label column popularity | `X_album_labels.getnnz(axis=0)` | `groupby('label_id')['album_id'].nunique().sort_values(ascending=False)` |
| `label_col_counts` (column-pruning) | `X_album_labels.getnnz(axis=0)` | Same label group-by |

**Outcome:** the notebook no longer depends on any archived file. It runs from raw parquets
and the current `album_genre_matrix.npz` only.

---

## 2. Consolidate repeated data loading

The notebook reads the same parquets multiple times across separate cells, and redefines
`DATA_DIR` in three places.

### Redundant parquet reads

| Parquet | Cells that load it |
|---|---|
| `mb_album_tag.parquet` | `load`, `allowlist-compute`, `label-mask-load` |
| `mb_album_label.parquet` | `allowlist-compute`, `label-mask-load` |
| `mb_artist_tag.parquet` | `load`, `label-mask-load`, `allowlist-coverage` |
| `mb_album_artists.parquet` | `load` (artist_ids.pkl context), `label-mask-load`, `allowlist-coverage` |

All four parquets should be read once in the `load` cell and kept as module-level variables.
Downstream cells reference the already-loaded DataFrames.

### `DATA_DIR` defined in three cells

Defined in `load`, `allowlist-compute`, and `label-mask-load`. Should be in `imports` only.

### Genre vocabulary computed twice under different names

`label-mask-load` builds `genre_tag_index`; `allowlist-coverage` independently builds
`genre_vocab`. Both apply `MIN_TAG_OCC = 10` to the same tag occurrence data.
`MIN_TAG_OCC` itself is also defined twice.

**Fix:** compute once in `load` (or a dedicated `vocab` cell immediately after), name it
`genre_tag_index` throughout, and define `MIN_TAG_OCC` in `imports`.

---

## 3. Label masking analysis uses wrong mask basis

In `label-mask-build`, the signal mask is constructed from album tags only:

```python
signal_mask = X_album_in_genre_vocab > 0   # album tags only
X_label_masked = X_label_raw.multiply(signal_mask)
```

But the actual feature pipeline in `02-feature-genre.ipynb` masks against the combined
album + artist signal. A label tag passes if it matches either the album's own tags *or*
the artist's tags. Using album-only as the mask basis:
- Under-counts how many label tags survive masking (~87% masked here vs less in production)
- Under-counts per-album overlap rates
- Makes the "~87% masked out" headline figure slightly misleading

**Fix:** build the mask from the combined album + artist block, matching what the feature
notebook actually does:

```python
X_album_artist = X_album_in_genre_vocab + X_artist_in_genre_vocab
signal_mask = X_album_artist > 0
X_label_masked = X_label_raw.multiply(signal_mask)
```

`X_artist_in_genre_vocab` is already built (or can easily be) from `artist_tags_raw_df`
which is loaded in the `load` cell. The existing comment in `label-mask-per-album-takeaway`
acknowledges this gap — closing it makes the analysis accurate rather than just noting it
as a known limitation.

---

## 4. `allowlist-coverage` rebuilds what `label-mask-load` already has

`label-mask-build` builds `X_album_in_genre_vocab` (album tags mapped into the genre vocab
space). `allowlist-coverage` independently rebuilds the same matrix as `X_album_genre`.
After consolidating parquet loading and vocab computation (items 2 and 3), `X_album_in_genre_vocab`
can be reused directly — no second build needed.

---

## Summary of changes

| Change | Benefit |
|---|---|
| Replace archive NPZs with parquet-derived stats | Notebook runs without archive; archive files can be gitignored |
| Consolidate parquet reads into `load` cell | Faster re-runs; single source of truth per dataset |
| Move `DATA_DIR`, `MIN_TAG_OCC` to `imports` | No silent redefinition bugs |
| Compute genre vocab once | One name, one place |
| Fix mask basis to album + artist | Analysis matches production pipeline |
| Reuse `X_album_in_genre_vocab` in allowlist-coverage | Remove duplicate matrix build |
