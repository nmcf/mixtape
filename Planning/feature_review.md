# Feature Assembly Review

## What the assembly notebook does today

`3-features/08-feature-assembly.ipynb` is a **read-only diagnostic notebook**. It loads four
feature matrices, hstacks them, and computes sparsity statistics and column-pruning thresholds.
It writes nothing to disk — no assembled matrix, no model input. Its purpose is inspection only.

The four blocks it currently loads:

| Block | File | Shape | nnz |
|---|---|---|---|
| Tags | `album_tags_matrix.npz` | 2,241,402 × 3,041 | 3,004,997 |
| Labels | `album_labels_matrix.npz` | 2,241,402 × 3,469 | 402,047 |
| Types | `album_types_matrix.npz` | 2,241,402 × 10 | 402,047 |
| Ratings | `album_ratings_matrix.npz` | 2,241,402 × 1 | 44,334 |
| **Combined** | — | **2,241,402 × 6,521** | **3,853,425** |

---

## What actually exists in `data/features/`

21 files — 15 sparse matrices, plus index/metadata files:

**Sparse matrices:**

| File | Producing notebook | In assembly? | In app? |
|---|---|---|---|
| `album_tags_matrix.npz` | 02-feature-genre | ✅ | ❌ |
| `album_labels_matrix.npz` | 03-feature-label | ✅ | ❌ |
| `album_types_matrix.npz` | 03-feature-label | ✅ | ❌ |
| `album_ratings_matrix.npz` | 04-feature-ratings | ✅ | ✅ (hidden) |
| `album_genre_matrix.npz` | 02-feature-genre | ❌ | ✅ |
| `album_record_label_matrix.npz` | 03-feature-label | ❌ | ✅ |
| `album_track_stats_matrix.npz` | 06-feature-track-stats | ❌ | ✅ |
| `album_country_matrix.npz` | 05-feature-country | ❌ | ✅ |
| `album_era_matrix.npz` | 07-feature-era | ❌ | ✅ |
| `album_lastfm_popularity_matrix.npz` | 13-feature-lastfm-popularity | ❌ | ✅ (optional) |
| `album_year_matrix.npz` | 10-feature-year | ❌ | ❌ |
| `album_contributor_counts_matrix.npz` | 09-feature-contributors | ❌ | ❌ |
| `album_instrument_matrix.npz` | — | ❌ | ❌ |
| `album_role_family_matrix.npz` | — | ❌ | ❌ |
| `album_tag_parent_matrix.npz` | 11/12-feature-tag-* | ❌ | ❌ |

**Index / metadata:**
- `album_ids.pkl` — master row index (shared by all matrices)
- `artist_ids.pkl` — artist row index
- `album_era.parquet` — per-album year/era for audit
- `album_tag_parent_columns.json` — tag hierarchy column map
- `year_scaler.json` — year normalisation params

---

## What the app loads

`5-app/app_v3_weighted.py` (`BLOCK_FILES`):

| Block | File | User knob | Default dial |
|---|---|---|---|
| genre | `album_genre_matrix.npz` | ✅ | 6 (weight 1.09) |
| record_label | `album_record_label_matrix.npz` | ✅ | 6 (weight 1.09) |
| track_stats | `album_track_stats_matrix.npz` | ✅ | 6 (weight 1.09) |
| country | `album_country_matrix.npz` | ✅ | 2 (weight 0.36) |
| era | `album_era_matrix.npz` | ✅ | 4 (weight 0.73) |
| popularity | `album_lastfm_popularity_matrix.npz` | ✅ | 4 (weight 0.73) |
| ratings | `album_ratings_matrix.npz` | ❌ hidden — syncs to popularity | — |

---

## The core problem: the assembly notebook is stale

The assembly notebook was written against the v1 feature set (tags + labels + types + ratings).
The project has since moved on to a v3 feature set (genre + record_label + track_stats + country
+ era + ratings) and added a seventh optional block (popularity). The assembly notebook never
caught up — it has no awareness of six of the seven blocks the app currently uses, and it still
references two blocks (raw tags, label types) that the app no longer loads at all.

As a result the notebook gives a misleading picture of the actual assembled feature space. Any
sparsity stats, column counts, or pruning thresholds it computes describe a feature set that no
longer matches production.

---

## Matrices that exist but nothing uses

Four matrices are built and committed but loaded by neither the assembly notebook nor the app:

| File | Notebook | Notes |
|---|---|---|
| `album_year_matrix.npz` | 10-feature-year | Continuous year signal; overlaps with era but finer-grained |
| `album_contributor_counts_matrix.npz` | 09-feature-contributors | Contributor/credit counts per album |
| `album_instrument_matrix.npz` | no notebook found | Unknown provenance |
| `album_role_family_matrix.npz` | no notebook found | Unknown provenance |
| `album_tag_parent_matrix.npz` | 11/12-feature-tag-* | Tag hierarchy parents |

`album_instrument_matrix.npz` and `album_role_family_matrix.npz` have no corresponding feature
notebook in `3-features/` — unclear whether they were built by an older notebook that's been
deleted or moved to archive.

---

## What needs to happen

### 1. Update `08-feature-assembly.ipynb` to reflect the current feature set

Replace the four v1 blocks with the seven blocks the app actually uses:

```
genre              album_genre_matrix.npz
record_label       album_record_label_matrix.npz
track_stats        album_track_stats_matrix.npz
country            album_country_matrix.npz
era                album_era_matrix.npz
ratings            album_ratings_matrix.npz
popularity         album_lastfm_popularity_matrix.npz   (optional)
```

The sparsity analysis, column-pruning threshold, and coverage stats should all be recomputed
against this set. The old tags/labels/types blocks can be left in a note explaining they were
the v1 feature set.

### 2. Decide what to do with the unused matrices

Each of the five unused matrices needs a decision:

- **`album_year_matrix.npz`** — the continuous year signal could complement era (which is
  binned). Worth evaluating whether adding it as an 8th block improves results. A knob already
  exists conceptually (Era is at dial 4); year could be bundled with era or given its own dial.

- **`album_contributor_counts_matrix.npz`** — contributor counts could help distinguish
  solo albums from ensemble projects. Needs evaluation before adding a knob.

- **`album_tag_parent_matrix.npz`** — the tag hierarchy feature could improve coverage for
  niche albums by backing off to broader genre parents. Worth a systematic evaluation (does it
  help, or does it blur distinctions?).

- **`album_instrument_matrix.npz`** / **`album_role_family_matrix.npz`** — track down their
  provenance first. If no producing notebook exists they may be orphaned artefacts from an old
  branch and should be moved to archive.

### 3. Clarify the role of old v1 matrices

`album_tags_matrix.npz`, `album_labels_matrix.npz`, and `album_types_matrix.npz` are still
committed and referenced by the assembly notebook but the app no longer uses them. They have
been superseded by `album_genre_matrix.npz` (richer, blended) and
`album_record_label_matrix.npz` (consolidated labels + types). Consider:

- Adding a note in the assembly notebook labelling them as v1/deprecated
- Deciding whether to keep them committed (they are large) or gitignore them

### 4. Track down missing notebook provenance

`album_instrument_matrix.npz` and `album_role_family_matrix.npz` have no visible source
notebook. Check git log for when they were first committed and which branch they came from.

```bash
git log --all --oneline -- data/features/album_instrument_matrix.npz
git log --all --oneline -- data/features/album_role_family_matrix.npz
```

---

## Summary

| Issue | Priority |
|---|---|
| Assembly notebook stale — doesn't reflect v3 feature set | High |
| Five committed matrices are unused by both assembly and app | Medium |
| Two matrices have no visible producing notebook | Medium |
| v1 matrices (tags, labels, types) still committed alongside v3 replacements | Low |
