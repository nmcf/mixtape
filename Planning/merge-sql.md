# sql-merge Integration Plan

Files parked in `sql-merge/` during the `app_features → sql_features` merge.
Each file needs a home in the 5-folder structure or a decision to archive.

---

## File inventory and suggested destinations

### Model training notebooks

| File | What it does | Suggested destination |
|---|---|---|
| `knn-v3.ipynb` | Trains V3 KNN model — adds contributor blocks (role_family, instrument, contrib_cnt) to V2 | `4-model/04-knn-v3-training.ipynb` already exists — **check if duplicate, archive if so** |
| `knn-v4.ipynb` | Trains V4 KNN model — adds year block to V3 | `4-model/05-knn-v4-training.ipynb` |

> Note: `4-model/04-knn-v3-training.ipynb` was brought in from `app_features`. Diff against `sql-merge/knn-v3.ipynb` before deciding which to keep.

---

### Feature engineering notebooks

| File | What it does | Suggested destination |
|---|---|---|
| `12_weights-year.ipynb` | Builds the year sparse feature matrix (`album_year_matrix.npz`) with imputed year | `3-features/09-feature-year.ipynb` |
| `15_tag-hierarchy.ipynb` | Builds `tag_parents.csv` from MB flat tag list using substring heuristic | `3-features/10-feature-tag-hierarchy.ipynb` |
| `16_weights-tag-parents.ipynb` | Builds `album_tag_parent_matrix.npz` from `tag_parents.csv` | `3-features/11-feature-tag-parents.ipynb` |
| `weights-contributors.ipynb` | Builds contributor feature matrices (role_family, instrument, contrib_cnt) | `3-features/` — check if already covered; if not, add as `3-features/09-feature-contributors.ipynb` (renumber year +1) |

---

### Weight tuning notebooks

These are model optimisation notebooks — they don't belong in `3-features/` or `4-model/` cleanly. Best option is a new `4-model/tuning/` subfolder.

| File | What it does | Suggested destination |
|---|---|---|
| `11_tune-weights.ipynb` | Fast dot-product weight tuning for V2/V3 (avoids full KNN rebuild) | `4-model/tuning/01-tune-weights-v2-v3.ipynb` |
| `tune-base-weights.ipynb` | Tunes W_TAGS, W_LABELS, W_TYPES, W_RATINGS for V3 via random + grid search | `4-model/tuning/02-tune-base-weights-v3.ipynb` |
| `tune-weights-load.ipynb` | Loads and displays tuning results | `4-model/tuning/03-tune-weights-load.ipynb` |
| `13_tune-year-weight.ipynb` | Tunes W_YEAR for V4 (1D, two-phase log-uniform + fine grid) | `4-model/tuning/04-tune-year-weight-v4.ipynb` |

---

### Evaluation notebook

| File | What it does | Suggested destination |
|---|---|---|
| `10_evaluate-lastfm.ipynb` | Evaluates V1–V3 KNN models against Last.fm ground truth; computes Hit Rate @10, Precision @10 | `4-model/06-evaluate-lastfm.ipynb` |

---

### App versions

`app_sql_v3.py` and `app_sql_v4.py` are multi-model comparison apps (load V1/V2/V3 via KNN .joblib). `app_v6.py` is newer — on-the-fly cosine similarity using V3/V4 feature blocks and runtime weights, no .joblib needed.

| File | What it does | Suggested destination |
|---|---|---|
| `app_sql_v3.py` | Streamlit app comparing V1/V2/V3 via KNN | `archive/` — superseded by `app_v3.py` and the weighted app |
| `app_sql_v4.py` | Streamlit app comparing V1/V2/V3/V4 via KNN | `archive/` — superseded |
| `app_v6.py` | On-the-fly cosine similarity, runtime feature weights, no .joblib | `5-app/app_v4_cosine.py` (or `app_v6.py` to preserve the version number) |

---

### Analysis doc

| File | What it does | Suggested destination |
|---|---|---|
| `next-steps-analysis.md` | Post-V4 analysis: model progression table, lessons learned V2→V4, prioritised next steps (fuzzy evaluator, tag hierarchy, FAISS, artist features) | `Planning/next-steps-v4.md` |

This is a high-value doc — it captures the reasoning behind the recommended roadmap (fuzzy evaluator first, then tag hierarchy, then FAISS). Move it, don't archive it.

---

---

## Committed matrices pending review

These five matrices exist in `data/features/` and are built by notebooks already placed in
`3-features/`, but neither the assembly notebook nor the weighted app currently loads them.
They all originate from the same contributor/sql_features branch commit (`c75d946`,
author niboDS, "feat: contributor feature matrices, V3 model, and updated comparison app").

Each needs an evaluation decision before being added to the app or discarded.

| File | Producing notebook | Shape | What it encodes |
|---|---|---|---|
| `album_role_family_matrix.npz` | `3-features/09-feature-contributors.ipynb` | 1,008,102 × 7 | Normalised role-family profile (performance, production, writing, etc.) with confidence weights |
| `album_instrument_matrix.npz` | `3-features/09-feature-contributors.ipynb` | 1,008,102 × 591 | Normalised instrument profile (instruments appearing on ≥10 albums) with confidence weights |
| `album_contributor_counts_matrix.npz` | `3-features/09-feature-contributors.ipynb` | 1,008,102 × 7 | Distinct contributor counts per role family, min-max scaled |
| `album_year_matrix.npz` | `3-features/10-feature-year.ipynb` | TBD | Continuous imputed release year, min-max scaled; 98.9% coverage |
| `album_tag_parent_matrix.npz` | `3-features/11-feature-tag-hierarchy.ipynb` + `12` | TBD | Tag hierarchy parents — backs off niche tags to broader genre parents |

**Notes:**
- All three contributor matrices (`role_family`, `instrument`, `contributor_counts`) were built
  against the old 1,008,102-album universe. They need to be rebuilt against the current
  1,758,488-album universe before any evaluation.
- `album_year_matrix` overlaps with `album_era_matrix` (era is binned year). The continuous
  year signal could complement era — finer-grained similarity within a decade — but may also
  add noise. Needs evaluation.
- `album_tag_parent_matrix` could improve coverage for niche albums by backing off to broader
  genre parents. The key question is whether it blurs useful genre distinctions.
- `album_instrument_matrix` (591 cols) is the most expensive to add — evaluate whether
  instrument similarity actually improves recommendation quality vs. adding query latency.

## Suggested execution order

1. Move `next-steps-analysis.md` → `Planning/next-steps-v4.md` immediately (pure move, no changes needed)
2. Diff `knn-v3.ipynb` vs `4-model/04-knn-v3-training.ipynb` — keep whichever is more complete
3. Add `knn-v4.ipynb` → `4-model/05-knn-v4-training.ipynb`
4. Add feature notebooks (year, tag-hierarchy, tag-parents, contributors) into `3-features/` with sequential numbering
5. Create `4-model/tuning/` and move the four tuning notebooks in
6. Move `10_evaluate-lastfm.ipynb` → `4-model/06-evaluate-lastfm.ipynb`
7. Archive `app_sql_v3.py` and `app_sql_v4.py`
8. Move `app_v6.py` → `5-app/`
9. Delete `sql-merge/` once empty
