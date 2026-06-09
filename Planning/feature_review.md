# Feature Assembly Review

## Status

| Task | Status |
|---|---|
| 1. Rewrite assembly notebook with v3 feature set | ✅ Done |
| 2. Leave 5 unused matrices out; document in merge-sql.md | ✅ Done |
| 3. Move v1 matrices to archive; gitignore; add deprecation notes | ✅ Done |
| 4. Track down instrument/role_family provenance; add to merge-sql.md | ✅ Done |

---

## Original findings

### What the assembly notebook was doing (v1, now replaced)

`3-features/08-feature-assembly.ipynb` was written against the v1 feature set and never
updated. It loaded four stale blocks and wrote nothing to disk.

| Block | File | Shape | nnz |
|---|---|---|---|
| Tags | `album_tags_matrix.npz` | 2,241,402 × 3,041 | 3,004,997 |
| Labels | `album_labels_matrix.npz` | 2,241,402 × 3,469 | 402,047 |
| Types | `album_types_matrix.npz` | 2,241,402 × 10 | 402,047 |
| Ratings | `album_ratings_matrix.npz` | 2,241,402 × 1 | 44,334 |
| **Combined** | — | **2,241,402 × 6,521** | **3,853,425** |

The app was using a completely different feature set. The notebook gave an inaccurate picture
of production.

---

### What `data/features/` contains

| File | Producing notebook | In assembly (new)? | In app? |
|---|---|---|---|
| `album_ratings_matrix.npz` | 04-feature-ratings | ✅ | ✅ (hidden) |
| `album_genre_matrix.npz` | 02-feature-genre | ✅ | ✅ |
| `album_record_label_matrix.npz` | 03-feature-label | ✅ | ✅ |
| `album_track_stats_matrix.npz` | 06-feature-track-stats | ✅ | ✅ |
| `album_country_matrix.npz` | 05-feature-country | ✅ | ✅ |
| `album_era_matrix.npz` | 14-feature-temporal | ✅ | ❌ superseded by `album_temporal_matrix.npz` |
| `album_temporal_matrix.npz` | 14-feature-temporal | ✅ | ✅ |
| `album_lastfm_popularity_matrix.npz` | 13-feature-lastfm-popularity | ✅ (optional) | ✅ (optional) |
| `album_year_matrix.npz` | 10-feature-year | ❌ superseded by temporal matrix | ❌ |
| `album_contributor_counts_matrix.npz` | 09-feature-contributors | ❌ pending review | ❌ |
| `album_instrument_matrix.npz` | 09-feature-contributors | ❌ pending review | ❌ |
| `album_role_family_matrix.npz` | 09-feature-contributors | ❌ pending review | ❌ |
| `album_tag_parent_matrix.npz` | 11/12-feature-tag-* | ❌ pending review | ❌ |

**Index / metadata (unchanged):**
- `album_ids.pkl` — master row index
- `artist_ids.pkl` — artist row index
- `album_era.parquet` — per-album year/era for audit
- `album_tag_parent_columns.json` — tag hierarchy column map
- `temporal_year_scaler.json` — year normalisation params (formerly `year_scaler.json`)

---

### What the app loads

`5-app/app_v3_weighted.py` (`BLOCK_FILES`):

| Block | File | User knob | Default dial |
|---|---|---|---|
| genre | `album_genre_matrix.npz` | ✅ | 6 (weight 1.09) |
| record_label | `album_record_label_matrix.npz` | ✅ | 6 (weight 1.09) |
| track_stats | `album_track_stats_matrix.npz` | ✅ | 6 (weight 1.09) |
| country | `album_country_matrix.npz` | ✅ | 2 (weight 0.36) |
| era | `album_temporal_matrix.npz` | ✅ | 4 (weight 0.73) |
| popularity | `album_lastfm_popularity_matrix.npz` | ✅ | 4 (weight 0.73) |
| ratings | `album_ratings_matrix.npz` | ❌ hidden — syncs to popularity | — |

---

## Task notes

### 1. Assembly notebook rewritten ✅

`08-feature-assembly.ipynb` has been rewritten to load the v3 blocks (genre, record_label,
track_stats, country, era, ratings, popularity optional). The new notebook:

- Loads all blocks and asserts row-count alignment to `album_ids.pkl`
- Reports shape, nnz, and album coverage per block
- Shows per-block column nnz breakdown (min/median/max/singletons)
- Plots column nnz histogram and CDF for the combined matrix
- Sweeps pruning thresholds and plots album zeroing curve
- Computes the safe threshold and shows per-block column survival

The old expansion logic (re-mapping from a 1M-album subset to the 2.2M universe) is no longer
needed — v3 matrices are built at the full 1,758,488-album universe from the start.

---

### 2. Five unused matrices — deferred to per-feature review ✅

The five matrices below are built and committed but not yet integrated. Each needs individual
evaluation before being added to the app. They have been documented in
`Planning/merge-sql.md` under "Committed matrices pending review".

| File | Producing notebook | Decision |
|---|---|---|
| `album_role_family_matrix.npz` | 09-feature-contributors | Pending review |
| `album_instrument_matrix.npz` | 09-feature-contributors | Pending review |
| `album_contributor_counts_matrix.npz` | 09-feature-contributors | Pending review |
| `album_year_matrix.npz` | 10-feature-year | Pending review |
| `album_tag_parent_matrix.npz` | 11/12-feature-tag-* | Pending review |

---

### 3. v1 matrices archived and gitignored ✅

`album_tags_matrix.npz`, `album_labels_matrix.npz`, and `album_types_matrix.npz` have been:
- Moved to `archive/` via `git mv`
- Added to `.gitignore` under `data/features/` so regenerated copies stay untracked

**Why these were superseded:**

`album_tags_matrix.npz` was produced by the old `01-feature-tags-labels.ipynb` notebook
(since deleted and split). It contained only direct MusicBrainz album tags — no artist tags,
no label tags. `album_genre_matrix.npz` (built by `02-feature-genre.ipynb`) supersedes it
with a three-tier blend: album tags (weight 1.0) + artist tags applied universally (weight 0.5)
+ masked label tag reinforcement and allowlist rescue (weight 0.3). Genre coverage improved
from ~40% (album tags only) to 68.8% (1,210,648 albums), and the tag vocabulary grew from
2,684 to 10,255 columns.

`album_labels_matrix.npz` and `album_types_matrix.npz` were produced by the same old
notebook. They encoded record labels and release types as separate blocks. Both were
consolidated into `album_record_label_matrix.npz` (built by `03-feature-label.ipynb`) via
`hstack`, removing the need to treat them separately in training and the app. The label
weighting was also corrected at this point — the old scheme weighted by `tag_count` and
systematically underweighted boutique labels; the new scheme uses equal per-(album, label)
weighting with explicit deduplication.

---

### 4. Instrument and role_family provenance resolved ✅

Both `album_instrument_matrix.npz` and `album_role_family_matrix.npz` are produced by
`3-features/09-feature-contributors.ipynb`. The confusion arose because the feature_review
was written before `09-feature-contributors.ipynb` was integrated from the contributors
branch.

**Commit:** `c75d946` — "feat: contributor feature matrices, V3 model, and updated comparison
app" — Author: niboDS, 8 Jun 2026. This commit also introduced `album_contributor_counts_matrix.npz` and the weight tuning notebooks.

**What `09-feature-contributors.ipynb` builds (all from recording/work/release contributor
parquets with confidence weights 1.0 / 0.9 / 0.6):**

| Matrix | Shape (old universe) | What it encodes |
|---|---|---|
| `album_role_family_matrix.npz` | 1,008,102 × 7 | Normalised role-family profile (performance, production, writing, technical, visual_packaging, business_label, other) |
| `album_instrument_matrix.npz` | 1,008,102 × 591 | Normalised instrument profile; instruments on ≥10 albums only |
| `album_contributor_counts_matrix.npz` | 1,008,102 × 7 | Distinct contributor counts per role family, min-max scaled |

**Note:** all three matrices were built against the old 1,008,102-album universe. They must
be rebuilt against the current 1,758,488-album universe before evaluation or integration.
This is tracked in `Planning/merge-sql.md`.

---

## Remaining open questions

- `album_year_matrix` has been superseded by `album_temporal_matrix.npz` (era + year merged behind single Era dial, built by `14-feature-temporal.ipynb`). `YEAR_WEIGHT=0.3` set analytically — era-boundary smoothing only; formal tuning blocked (no `lastfm_album_similarity.parquet`). See `2-eda/04-EDA-year.ipynb` for the cosine analysis. ✅ Shipped.
- Do contributor/instrument features improve recommendation quality enough to justify the
  extra query dimensions? Needs evaluation via `4-model/06-evaluate-lastfm.ipynb`.
- Should tag parents improve coverage for niche albums, or blur genre distinctions? Needs A/B
  evaluation before merging into the genre block or adding as a separate knob.
