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

---

# Proposal: fold the parent-tag hierarchy into `02-feature-genre.ipynb`

> **Status: proposed** (2026-06-10). Not yet implemented.

`01b-feature-tag-hierarchy.ipynb` and `archive/12-feature-tag-parents.ipynb` (archived) together produce a
coarse 20-column **parent-genre** rollup (`album_tag_parent_matrix.npz`) that complements
the ~3,000-column *fine* tag matrix `02` already builds. The fine matrix gives every
subgenre its own column, so `death metal` and `black metal` albums share none; the parent
rollup collapses both to a shared `metal` column, which is exactly the cross-subgenre
similarity signal the fine matrix can't express.

The two notebooks were prototyped standalone against raw album tags. Folding them into `02`
lets the rollup reuse `02`'s vocabulary, ID space, and — most importantly — its *blended*
album+artist+label signal instead of recomputing from album tags alone. Below are the four
seams that must be bridged, then the recommended shape.

## What 11 + 12 do

| Notebook | Output | Key logic |
|---|---|---|
| `01b-feature-tag-hierarchy` | `tag_parents.csv` (439 child→parent pairs, 20 parents) | Substring heuristic (`death metal` → `metal`, longest whole-word match wins), then a **codified audit** — hardcoded `bad_parents` / `VALID_PARENTS` sets prune false positives (`new wave`→`wave`, `non-music`→`music`) and reassign mismatches |
| `12-feature-tag-parents` (archived) | `album_tag_parent_matrix.npz` (n_albums × 20) | For each (album, parent): **max** weight across the album's child tags. Weight = `tag_count / max_per_album`. Covers 378k albums (51% of tagged) |

## Seams to bridge before merging

**1. Key space: names vs ids.** `11`/`12` work on tag *name* strings; `02` works on
**tag_id**. The parent map is name-keyed and `02` never loads `mb_tag.parquet`. Integration
needs a `name → id` bridge built once from `mb_tag.parquet`, then `tag_parents.csv` lifted
into a `child_tag_id → parent_col` mapping aligned to `genre_tag_index`.

**2. Vocabulary threshold mismatch.** `02`'s `genre_tag_index` keeps tags with
`sum(tag_count) ≥ 10` *across album+artist+label sources*. `11`'s `active_tags` keeps tags
with `nunique(album_id) ≥ 10` *album-only*. These select overlapping-but-different tag sets.
After the merge, parent children should be defined relative to `genre_tag_index` so a child
tag that survives `02`'s vocab is the unit of rollup — no second threshold.

**3. Normalisation mismatch.** `02` uses `tag_count / sum_per_album` + final L1 row-norm;
`12` uses `tag_count / max_per_album` + **max** child aggregation. We resolve this by
recomputing the rollup on `02`'s own blended weights (not `12`'s raw album weights), then
scaling the coarse columns by a build-time constant `α` before stacking them onto the fine
matrix — see "Decisions" and "Recommended shape" below.

**4. The audit is a versioned input, not a recompute.** `tag_parents.csv` is the product of
manual/codified review. It must be treated as a **checked-in artifact** the pipeline *reads*,
not something `02` regenerates each run. The substring-generation step (`11`) stays a separate
offline notebook; only the cleaned CSV feeds `02`.

## Decisions (locked)

The app ties **one knob to exactly one `.npz` file** ([`5-app/config.py`](../5-app/config.py)
`BLOCK_FILES`; [`5-app/engine.py`](../5-app/engine.py) `weighted_cosine`). Two decisions follow
from that:

- **Output → Option A: one combined file, one knob.** The 20 coarse parent columns are stacked
  onto the right of the fine matrix and saved as the *same* `album_genre_matrix.npz`. The
  existing **Genre** knob scales both halves together; **no app code changes**. The fine-vs-coarse
  balance is fixed at build time via a constant `α` (the coarse block is multiplied by `α` before
  stacking), not a runtime control. If we later want users to turn fine vs family independently,
  that's a switch to two separate blocks/knobs — out of scope for now.
- **Aggregation → max.** Each album's score for a parent = the **max** weight across that
  parent's child tags the album has (matching `12`). Max reflects *how strongly* an album
  belongs to a family without rewarding how *many* subgenre tags it happens to carry.
- **`α = 0.26`, no tuning needed.** A prior model run already tuned the tag-parent block as a
  separate feature and recorded `"W_TAG_PARENT": 0.26` (against `"W_TAGS": 1.0`) in
  [`data/best_weights.json`](../data/best_weights.json) (`v5`). That ratio *is* the fine-vs-coarse
  balance we need, so we reuse it directly: `α = 0.26`. See the scale note under "On α" below.

## Recommended shape

Keep the **generation** of `tag_parents.csv` in `11` (offline, audited, versioned). Move the
**rollup** (`12`) into `02` as a new block after `genre-combine`, derive it from the
already-blended `X_genre` (not raw album tags), aggregate with **max**, scale by `α`, and stack:

```python
from scipy.sparse import hstack
from sklearn.preprocessing import normalize
ALPHA_TAG_PARENT = 0.26   # from best_weights.json v5 W_TAG_PARENT — see "On α"

# After X_genre (album × n_tags, fine) is built and L1-normalised.
# parent_cols: list of n_parents arrays, each holding the genre_tag_index column
#   positions of one parent's child tags (built from tag_parents.csv via the name→id bridge).
cols = []
for child_idx in parent_cols:                      # one parent at a time
    # row-wise MAX across this parent's child columns → one coarse column
    cols.append(X_genre[:, child_idx].max(axis=1))
X_parent = hstack(cols).tocsr()                    # album × n_parents (≈20), max-aggregated
X_parent = normalize(X_parent, norm='max', axis=1) # 0–1 row scale, so α=0.26 transfers (see caveat)

X_genre_combined = hstack([X_genre, ALPHA_TAG_PARENT * X_parent]).tocsr()
save_npz(f'{FEATURES_DIR}/album_genre_matrix.npz', X_genre_combined)
```

Rolling up `X_genre` (not raw album tags) is the real payoff of merging:

- **Higher coverage.** `12` covers 51% of albums because it only sees album tags. `X_genre`
  already carries artist (universal) and label-derived signal, so the parent rollup inherits
  that coverage — albums with only artist/label signal get a parent vector too.
- **One vocabulary, one threshold.** The coarse columns are a projection of the same fine
  matrix over the same `genre_tag_index`; no second vocab or threshold to maintain.
- **One source of truth.** The whole genre signal is built in one notebook and ships as one file.

**On `α` — use `0.26` (sourced, not tuned):** because cosine sees the fine and coarse columns as
one vector, `α` sets how much the 20 coarse columns pull the similarity relative to the ~3,000
fine columns. We take this from the already-tuned `W_TAG_PARENT = 0.26` in
[`data/best_weights.json`](../data/best_weights.json) (`v5`), where the parent block carried
weight `0.26` against fine tags at `1.0`. Define it once as a named constant in `02`'s `imports`
cell: `ALPHA_TAG_PARENT = 0.26`.

**Scale caveat (one line of code).** That `0.26` was tuned when the parent block was `12`'s
standalone matrix, whose rows sit on a `0–1` scale (max of per-album-max-normalised child
weights). Our coarse block is a max over the *L1-normalised* `X_genre`, so its rows are much
smaller in magnitude — the tuned ratio only transfers if the two blocks are on the same footing.
So **L1- or max-normalise `X_parent`'s rows to a `0–1` scale before applying `α`**, e.g.
`X_parent = normalize(X_parent, norm='max', axis=1)`. With that one line, `α = 0.26` reproduces
the tuned fine-vs-coarse balance without any new tuning. (If we ever do revisit it, re-tune `α`
directly against the `4-model` eval rather than by eye.)

**Note — `album_tag_parent_matrix.npz` becomes optional.** `12`'s standalone output is no longer
needed for the app under Option A (the coarse signal lives inside `album_genre_matrix.npz`). Keep
`12` only if the separate 20-column matrix is still wanted for analysis/EDA.

## Summary of proposed changes

| Change | Benefit |
|---|---|
| Keep `11` (substring + audit) as the offline generator of `tag_parents.csv` | Audit stays a reviewed, versioned artifact — not recomputed per run |
| Build a `name → tag_id` bridge from `mb_tag.parquet`, lift `tag_parents.csv` to per-parent `genre_tag_index` column positions | Fixes the name/id and dual-threshold seams |
| Move the rollup into `02` after `genre-combine`: **max** over each parent's child columns of `X_genre` | Inherits blended album+artist+label coverage; one vocab; not distorted by subgenre tag count |
| **Option A:** scale coarse block by `α` and `hstack` onto the fine matrix; save as the same `album_genre_matrix.npz` | One **Genre** knob scales both; zero app code changes |
| Set `ALPHA_TAG_PARENT = 0.26` from the tuned `W_TAG_PARENT` in `best_weights.json` (`v5`); max-normalise `X_parent` rows first so the value transfers | Reuses an existing tuned weight — no new tuning needed |

---

# Rewrite: `2-eda/05-EDA-tags-labels.ipynb`

> **Status: proposed** (2026-06-10). Companion to the `02` change above.

Combining fine + coarse columns into one `album_genre_matrix.npz` (Option A) **silently breaks the
existing EDA notebook** unless it's updated: every cell that does `np.diff(X_genre.indptr)` or
`X_genre.shape` now counts the ~20 coarse columns too, so `genre_per_album`, the coverage number,
and the richness plots would all shift for the wrong reason. The rewrite has two jobs: **(1)** make
Parts 1–5 operate on the *fine* sub-matrix so their numbers stay comparable to today, and **(2)**
add a new Part that analyses the coarse parent rollup.

## A. Setup cell — split the combined matrix

The loaded matrix is now `[fine | α·coarse]`. Slice it once, up front, and keep the existing
`X_genre` name pointing at the **fine** block so Parts 1–5 are untouched downstream:

```python
import json
n_tags  = len(genre_tag_index)                       # fine column count (already computed)
parents = json.load(open(f'{FEATURES_DIR}/album_tag_parent_columns.json'))
n_parents = len(parents)                              # ≈20

X_genre_full = load_npz(f'{FEATURES_DIR}/album_genre_matrix.npz')
X_genre   = X_genre_full[:, :n_tags]                  # FINE block — Parts 1–5 use this, unchanged
X_parent  = X_genre_full[:, n_tags:]                  # COARSE block — new Part 6 uses this
assert X_parent.shape[1] == n_parents
genre_per_album = np.diff(X_genre.indptr)             # now counts fine tags only, as before
```

Also load the hierarchy inputs for the new part: `tag_parents.csv` and `mb_tag.parquet` (the
name→id bridge), so the EDA can name parents and show example child→parent groupings.

## B. New Part 6 — The Parent Hierarchy (coarse genre)

Slots in after Part 4 (it's the same "structure vs coverage" theme) or as a final Part 6. Proposed
cells, each with a markdown takeaway in the notebook's existing voice:

| Cell | Content | Point it makes |
|---|---|---|
| **6.0 intro (md)** | What `11` does: substring heuristic + codified audit collapses ~439 subgenres into 20 families. Reference `11`/`12`. | Frames the coarse view as a *complement* to the fine matrix |
| **6.1 the gap** | Death-metal vs black-metal demo. Pair **`album_id=710599`** — Cannabis Corpse, *"Tube of the Resinated"* (only tag `death metal`, count 3) with **`album_id=49567`** — Immortal, *"Damned in Black"* (only tag `black metal`, count 5). Each fine vector is a single, *different* column → **fine cosine = 0**; both roll up to `metal` → **coarse cosine high**. | The concrete problem the rollup solves — cross-subgenre similarity the fine matrix can't express |
| **6.2 family distribution** | Bar chart: albums per parent family from `X_parent` (20 bars), plus a child→parent example table for 3–4 families (`metal`, `house`, `indie`). | Shows the shape of the coarse signal and that the audit is sensible |
| **6.3 coverage check** | Coverage of the coarse block vs the fine block. Because it's rolled from the **blended** `X_genre`, parent coverage should ≈ fine coverage — **not** add new coverage. | Frames the rollup as a *structure/richness* gain, not coverage — same lesson as Part 4's "+0 coverage" |
| **6.4 α contribution** | At `α = 0.26`, report the coarse block's share of the combined row L2-norm (median across albums). One bar/hist: fine-norm vs coarse-norm contribution. | Makes the fine-vs-coarse balance visible and shows `0.26` keeps coarse as a minority nudge, not a takeover |
| **6.5 neighbour shift** | For ~3 query albums, list top-10 neighbours under fine-only vs combined. Show the combined list pulls in same-family, different-subgenre albums. | Demonstrates the payoff end-to-end on real recommendations |

> **Design decision — coarse genre is structure, not coverage.** Like universal artist tags in
> Part 4, the parent rollup adds *no* new covered albums (it's a projection of signal already in the
> blend); its value is cross-subgenre similarity, which a coverage count can't see — it shows up in
> 6.1 and 6.5.

## C. Intro & inputs — small edits

- Add to **Inputs:** `data/tag_parents.csv`, `data/mb_tag.parquet`, and note `album_genre_matrix.npz`
  now carries `[fine | α·coarse]` columns.
- Add a line to the opening list: *"6. The parent hierarchy — coarse genre families that capture
  cross-subgenre similarity the fine tags miss."*
- Extend the "two words" note (coverage / richness) to name the coarse rollup as a richness-style gain.

## D. If `12` is dropped

If `album_tag_parent_matrix.npz` is no longer built (see note above), Part 6 still works — it reads
the coarse columns straight out of the combined matrix via the split in section A. Only
`album_tag_parent_columns.json` is still needed (for parent names); have `02` write it.
