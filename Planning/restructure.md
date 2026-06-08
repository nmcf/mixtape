# Project Restructure Plan — 5-Folder Pipeline

## Goal

Replace the current 3-folder layout (`1-EDA/`, `2-Prototyping/`, `3-app/`) with 5 folders that map directly to the 5 pipeline steps described in the README "How it works" section. This makes the project self-documenting — a new contributor can read the README steps and immediately find the corresponding code.

---

## Target folder structure

| # | New folder | README step |
|---|---|---|
| 1 | `1-data/` | Data import — extract from MusicBrainz Postgres, save as Parquet |
| 2 | `2-eda/` | EDA — explore raw data at album, artist, and joined dataset level |
| 3 | `3-features/` | Features — build sparse feature matrices |
| 4 | `4-model/` | Model — train cosine-distance KNN models |
| 5 | `5-app/` | App — Streamlit app serving recommendations |

---

## File mapping

### `1-data/` — Data import

Files from `1-EDA/` that import data rather than explore it:

| Current path | New path |
|---|---|
| `1-EDA/01-postgres-to-parquet.ipynb` | `1-data/01-postgres-to-parquet.ipynb` |
| `1-EDA/02-parquet-to-dataframes.ipynb` | `1-data/02-parquet-to-dataframes.ipynb` |

---

### `2-eda/` — EDA

Remaining exploratory notebooks and schema docs from `1-EDA/`:

| Current path | New path |
|---|---|
| `1-EDA/03-EDA-albums.ipynb` | `2-eda/01-EDA-albums.ipynb` |
| `1-EDA/04-EDA-artists.ipynb` | `2-eda/02-EDA-artists.ipynb` |
| `1-EDA/05-EDA-master.ipynb` | `2-eda/03-EDA-master.ipynb` |
| `1-EDA/07-EDA-year.ipynb` | `2-eda/04-EDA-year.ipynb` |
| `1-EDA/EDA-tags-labels.ipynb` | `2-eda/05-EDA-tags-labels.ipynb` |
| `1-EDA/06-schema-diagrams.md` | `2-eda/schema-diagrams.md` |
| `1-EDA/SchemaSpy/` | `2-eda/SchemaSpy/` |

---

### `3-features/` — Feature engineering

Feature-building notebooks from `2-Prototyping/`, plus the shared index and queries:

| Current path | New path |
|---|---|
| `2-Prototyping/01-album-artist-index.ipynb` | `3-features/01-album-artist-index.ipynb` |
| `2-Prototyping/feature-genre.ipynb` | `3-features/02-feature-genre.ipynb` |
| `2-Prototyping/feature-label.ipynb` | `3-features/03-feature-label.ipynb` |
| `2-Prototyping/02-feature-ratings.ipynb` | `3-features/04-feature-ratings.ipynb` |
| `2-Prototyping/06-impute-artist-country.ipynb` | `3-features/05-feature-country-import.ipynb` |
| `2-Prototyping/07-build-album-track-stats.ipynb` | `3-features/06-feature-track-stats-import.ipynb` |
| `2-Prototyping/08-feature-country.ipynb` | `3-features/07-feature-country.ipynb` |
| `2-Prototyping/09-feature-track-stats.ipynb` | `3-features/08-feature-track-stats.ipynb` |
| `2-Prototyping/13-feature-era.ipynb` | `3-features/09-feature-era.ipynb` |
| `2-Prototyping/03-feature-assembly.ipynb` | `3-features/10-feature-assembly.ipynb` |
| `2-Prototyping/queries/` | `3-features/queries/` |
| `2-Prototyping/feature_charts/` | `3-features/feature_charts/` |

**Notebooks to retire** (superseded by the split notebooks above — confirm before deleting):

| File | Reason |
|---|---|
| `2-Prototyping/01-feature-tags-labels.ipynb` | Superseded by `feature-genre.ipynb` + `feature-label.ipynb` |
| `2-Prototyping/10-feature-genre-tags.ipynb` | Superseded by `feature-genre.ipynb` |

---

### `4-model/` — Model training

KNN training and query notebooks from `2-Prototyping/`:

| Current path | New path |
|---|---|
| `2-Prototyping/04-knn-training.ipynb` | `4-model/01-knn-v1-training.ipynb` |
| `2-Prototyping/05-knn-query.ipynb` | `4-model/02-knn-query.ipynb` |
| `2-Prototyping/11-knn-v2-training.ipynb` | `4-model/03-knn-v2-training.ipynb` |
| `2-Prototyping/12-knn-v3-training.ipynb` | `4-model/04-knn-v3-training.ipynb` |

---

### `5-app/` — Streamlit app

All app files from `3-app/` move as-is:

| Current path | New path |
|---|---|
| `3-app/app.py` | `5-app/app.py` |
| `3-app/app_v2.py` | `5-app/app_v2.py` |
| `3-app/app_v3.py` | `5-app/app_v3.py` |
| `3-app/app_v3_weighted.py` | `5-app/app_v3_weighted.py` |
| `3-app/knob_component/` | `5-app/knob_component/` |

---

## Notebooks to confirm / decide

These files need a decision before we move them:

| File | Question |
|---|---|
| `2-Prototyping/01-feature-tags-labels.ipynb` | Delete (superseded) or archive? |
| `2-Prototyping/10-feature-genre-tags.ipynb` | Delete (superseded) or archive? |
| `year_feature.md` (project root) | Move to `3-features/` or `docs/`? |
| `cleanup.md` (project root) | Keep as changelog or fold into `Planning/`? |

---

## Path fixes required

All notebooks use relative paths to reach `data/` and `musicbrainz.duckdb`. Moving files changes their depth, so paths will need updating.

| Notebook group | Current relative path | New relative path |
|---|---|---|
| `1-data/` (was `1-EDA/`) | `../data/`, `../musicbrainz.duckdb` | unchanged — same depth |
| `2-eda/` (was `1-EDA/`) | `../data/` | unchanged — same depth |
| `3-features/` (was `2-Prototyping/`) | `../data/` | unchanged — same depth |
| `4-model/` (was `2-Prototyping/`) | `../data/` | unchanged — same depth |
| `5-app/` (was `3-app/`) | `../data/` | unchanged — same depth |

All folders stay at depth 1 (one level below project root), so **no path changes are needed inside notebooks**. Only the Streamlit run command in the README needs updating (`3-app/` → `5-app/`).

---

## Files and folders staying in place

| Path | Reason |
|---|---|
| `data/` | Shared data store — no change |
| `docs/` | Documentation — paths inside docs will be updated to reflect new folder names |
| `requirements.txt` | No change |
| `README.md` | Update run command, project layout section, and rebuild instructions |
| `musicbrainz.duckdb` | No change |
| `Planning/` | Planning docs |

---

## Docs to update after the move

| File | What changes |
|---|---|
| `README.md` | Run command path, project layout tree, rebuild instructions notebook paths |
| `docs/01-data-import.md` | Notebook path |
| `docs/02-datasets.md` | Notebook path |
| `docs/03-features.md` | Notebook paths |
| `docs/04-model.md` | Notebook paths |
| `docs/05-app.md` | File path and run command |
| `docs/08-howto-model-v2.md` | Notebook paths |

---

## Implementation order

1. Create the 5 new folders ✅
2. Move files per the mapping tables above ✅
3. Confirm and delete/archive the superseded notebooks ✅
4. Update `README.md`
5. Update all `docs/` files
6. Smoke-test the app run command
7. Commit

---

## EDA folder review — 2026-06-08

### Findings

All five EDA notebooks are display-only — none of them write anything to disk that the feature or model pipeline depends on. The full dependency chain is:

```
raw parquet files  →  3-features/  →  data/features/*.npz  →  4-model/  →  5-app/
```

The pickled DataFrames in `data/pickles/` (`final_album_df.pkl`, `final_artist_df.pkl`, `master_df.pkl`) are produced by `1-data/02-parquet-to-dataframes.ipynb` and consumed only by the three EDA-albums/artists/master notebooks. No feature or model notebook touches them. The feature notebooks all rebuild from raw parquet directly into sparse matrices.

### Notebook-by-notebook assessment

| Notebook | Still useful? | Recommendation |
|---|---|---|
| `01-EDA-albums.ipynb` | Marginal — ydata-profiling report of `final_album_df.pkl`. The raw parquets are more directly useful now that the pipeline is mature. | **Archive** |
| `02-EDA-artists.ipynb` | Same as above for artist data. | **Archive** |
| `03-EDA-master.ipynb` | No — reads `master_df.pkl` (a full denormalized join), produces a ydata-profiling report in minimal mode. The master DataFrame is a cartesian-product artefact (album tags × artist tags = inflated rows) noted in the notebook itself. No downstream notebook uses it. | **Archive** |
| `04-EDA-year.ipynb` | Yes — documents the year-source comparison that informed the era feature design, including the 5 specific MusicBrainz data errors corrected. Useful reference if the era feature ever needs revisiting. | **Keep** |
| `05-EDA-tags-labels.ipynb` | Yes — reads the actual feature matrices and proves key design decisions (68.8% coverage ceiling, 87% label noise masking, richness vs coverage distinction). Acts as a validation harness for `02-feature-genre.ipynb`. | **Keep** |

### master_df — remove completely

`master_df.pkl` and the code that builds it in `1-data/02-parquet-to-dataframes.ipynb` serve no purpose in the current pipeline. The recommendation is:

1. **Archive `2-eda/03-EDA-master.ipynb`** — its only input is `master_df.pkl`.
2. **Remove the `master_df` construction block from `1-data/02-parquet-to-dataframes.ipynb`** — the cell that builds and pickles `master_df` can be deleted. The two remaining outputs (`final_album_df.pkl`, `final_artist_df.pkl`) are still used by the two EDA notebooks we're archiving, but if those are archived too, the entire `02-parquet-to-dataframes.ipynb` notebook becomes dead weight.
3. **Consider archiving `1-data/02-parquet-to-dataframes.ipynb` entirely** — if albums and artists EDA notebooks are also archived, nothing reads the pickled DataFrames. The only reason to keep this notebook is if we want to preserve the ability to run the ydata-profiling EDA again in future, which is low value given the pipeline is mature.

### Remaining `2-eda/` after cleanup

If the above recommendations are accepted, `2-eda/` shrinks to:

```
2-eda/
├── 04-EDA-year.ipynb           # Keep — year source analysis + era design rationale
├── 05-EDA-tags-labels.ipynb    # Keep — genre matrix validation
├── schema-diagrams.md          # Keep — ER diagrams
└── SchemaSpy/                  # Keep — auto-generated schema HTML
```

And `1-data/` becomes a single notebook:

```
1-data/
└── 01-postgres-to-parquet.ipynb   # Keep — the actual data import
```

### Decisions — resolved ✅

| Item | Decision |
|---|---|
| `2-eda/01-EDA-albums.ipynb` | Keep — was useful during the project, retain for reference |
| `2-eda/02-EDA-artists.ipynb` | Keep — same rationale |
| `2-eda/03-EDA-master.ipynb` | **Archived** — 157M-row cartesian product, no downstream use, no value |
| `1-data/02-parquet-to-dataframes.ipynb` | **Keep, master_df block removed** — `final_album_df` and `final_artist_df` still serve the album/artist EDA notebooks |
| `data/pickles/` contents | Gitignored — no action needed |

---

## EDA improvement plan — 2026-06-08

### Goal

The album and artist EDA notebooks currently just run ydata-profiling reports. They don't explain any of the decisions made during the project. The goal is to rework them so a reader can trace the logic from raw data → design choice for the key decisions: album scope, Bayesian ratings, and the feature set.

The improvements below are grouped by notebook. Each one is a self-contained section that can be added or modified independently.

---

### `02-parquet-to-dataframes.ipynb` — improvements

Currently builds `final_album_df` and `final_artist_df` and pickles them. The schema inspection at the end (Step 6) is useful but passive. Two additions would make it more useful:

**1. Post-join null audit**
After building each DataFrame, print what % of rows are null for each column that matters downstream. This makes the LEFT join rationale concrete rather than just stated.

```
e.g.  albums with no rating:        42.3%  → LEFT join correct
      albums with no country:        8.1%  → LEFT join correct
      albums with no label:         15.7%  → LEFT join correct
      albums with no album tags:    31.2%  → LEFT join correct
```

**2. Negative tag_count warning**
The artist_tags table contains negative `tag_count` values (MusicBrainz downvotes). The notebook should surface these explicitly — how many, which tags — and note that feature notebooks currently keep them as-is (they contribute negative weight in tag dicts). This is the right place to flag it since it first appears here.

---

### `01-EDA-albums.ipynb` — improvements

The notebook currently loads `final_album_df`, downcasts dtypes, shows `.head()`, and runs a ydata-profiling report. Replace or supplement the profiling report with targeted analysis sections, each answering a specific question that motivated a pipeline decision.

**Section 1 — Album type breakdown (motivates valid_albums scope)**

Show how many release groups exist per primary type (Album, Single, EP, etc.) and per secondary type (Live, Compilation, Remix, etc.). Then show the counts before and after applying the `valid_albums` filter. This is the clearest way to show why the scope decision was made — a table like:

```
Type                    Raw count    % of total    In valid_albums
Studio albums           1,200,000        53%           Yes
Live albums               450,000        20%        Yes (official only)
Compilations              350,000        16%     Yes (single-artist only)
Singles / EPs             150,000         7%            No
Remixes / DJ-mixes         80,000         4%            No
Bootlegs / other           11,488       <1%            No
```

This replaces needing to explain the filter in prose — the reader sees the data and understands the choice immediately.

Note: `final_album_df` is already filtered to `valid_albums` scope, so this analysis needs to load `mb_album.parquet` directly to show the before/after. The parquet-to-dataframes notebook is the right place to reference, but the EDA is the right place to visualise it.

**Section 2 — Rating coverage and Bayesian weighting (motivates Bayesian formula)**

Show three things:
- What % of albums have any community rating at all (raw coverage)
- The distribution of `rating_count` (most albums have very few votes)
- Side-by-side: raw rating vs. Bayesian-weighted score (`R*v / (v+5)`) for a sample — show how C=5 shrinks low-vote ratings toward zero while leaving high-vote ratings unchanged

The Bayesian formula is already implemented in `3-features/04-feature-ratings.ipynb`. Recompute it here just for display to show why it was chosen: albums with 1–2 votes and a high raw score collapse toward 0, preventing them from dominating recommendations.

**Section 3 — Tag sparsity (motivates column pruning and why artist/label tags were blended in)**

Show the distribution of tag count per album:
- How many albums have 0 album tags (motivates artist tag blending)
- How many have 1–5 tags vs. 6+ tags
- The long tail of tag columns (most tags appear on very few albums — motivates the `safe_threshold` pruning)

A simple histogram and a "% albums with N or fewer tags" table makes this clear.

**Section 4 — Label distribution (motivates label as a feature)**

Show top 20 record labels by album count and the long-tail shape of the label distribution. This sets up why label identity is a useful feature — major labels cluster stylistically, and boutique labels are even more genre-coherent.

**Keep the ydata-profiling report** at the end as an appendix — it's still useful for catch-all exploration, but it should come after the targeted sections, not replace them.

---

### `02-EDA-artists.ipynb` — improvements

Similar rework — replace the report-first approach with targeted sections. The artist notebook should focus on things that directly connect to how artist data feeds into the model.

**Section 1 — Various Artists and the VA problem (motivates same-artist exclusion)**

"Various Artists" (`artist_credit = 1`) is the first row in the DataFrame. Show:
- How many albums are credited to Various Artists
- That VA albums slipped through the `valid_albums` filter via the studio branch (~1.5% of index per `.ai_context.md`)
- That recommendations skip VA albums at query time (null `artist_name` check in the app)

This explains a quirk a reader would otherwise notice and wonder about.

**Section 2 — Artist type distribution (context for the dataset)**

Show a breakdown of `type`: Person, Group, Orchestra, Character, Other. This is quick (a value_counts table) but contextually useful — the reader understands what kind of entities are in the dataset.

**Section 3 — Negative tag votes (data quality flag)**

Surface the negative `tag_count` values visible in `.head()`. Show how many artist–tag rows are negative, which tags are most downvoted, and note that they are currently kept as-is. This is an open question — they could be filtered — but at minimum they should be documented.

**Section 4 — Artist country coverage (motivates country as a feature and its downweighting)**

Show the distribution of `area` (artist country):
- Top 20 countries by artist count
- % of artists with no country data
- Why country was downweighted to 0.2 in the model: at w=1.0 it dominated cosine similarity because country is dense (one-hot with few nulls) compared to sparse tag columns

A bar chart of top countries and a null-rate number is enough.

**Section 5 — Albums per artist (motivates same-artist exclusion)**

Show the distribution of album count per artist. The long tail (a few artists with hundreds of albums) makes clear why same-artist exclusion matters — without it, all recommendations for a prolific artist would be that artist's own back catalogue.

**Keep the ydata-profiling report** at the end as a catch-all appendix.

---

### What to leave out

- Deep statistical analysis (correlations, interaction plots) — covered by ydata-profiling
- Any analysis that requires loading feature matrices (`.npz`) — that belongs in `05-EDA-tags-labels.ipynb`
- Anything that doesn't directly connect to a pipeline decision


---

## 3-features/ review — 2026-06-08

### Findings

The 10 notebooks in `3-features/` split into three distinct categories:

| Category | Notebooks |
|---|---|
| Index building | `01-album-artist-index.ipynb` |
| **Data import from Postgres** | `05-feature-country-import.ipynb`, `06-feature-track-stats-import.ipynb` |
| Feature engineering (parquet → sparse matrix) | `02`, `03`, `04`, `07`, `08`, `09`, `10` |

The two import notebooks (`05` and `06`) are purely SQL-execution steps — they connect to the MusicBrainz PostgreSQL database via DuckDB, run a query, and save a parquet file. They contain no feature engineering logic. They belong in `1-data/` with the other import notebooks, not in `3-features/`.

### queries/ folder

The `queries/` folder contains four SQL files:

| File | Used by | What it does |
|---|---|---|
| `mb_artist_country_fast_duckdb_release.sql` | `05-feature-country-import.ipynb` | 10-signal country resolution chain with area hierarchy walking |
| `mb_album_stats_duckdb.sql` | `06-feature-track-stats-import.ipynb` | Album track statistics — lengths, percentiles, track counts |
| `mb_album_live_flag_duckdb.sql` | Used during initial import (01-postgres-to-parquet) | Live secondary-type flag export |
| `mb_album_compilation_flag_duckdb.sql` | Used during initial import (01-postgres-to-parquet) | Compilation secondary-type flag export |

All four SQL files are database-extraction queries. None are used during feature engineering. The folder belongs in `1-data/` alongside the notebooks that run them.

### `01-album-artist-index.ipynb`

Builds `data/features/album_ids.pkl` and `data/features/artist_ids.pkl` — the master row index that every feature notebook loads first. This is genuinely a prerequisite for feature engineering (not an import step), so it stays in `3-features/`. However, it could also reasonably sit in `1-data/` since it reads directly from parquets with no ML logic. Current placement is fine.

### Recommendations

**1. Move `05-feature-country-import.ipynb` → `1-data/03-feature-country-import.ipynb`**

It connects to Postgres, runs SQL, saves a parquet. No feature engineering. Identical pattern to `01-postgres-to-parquet.ipynb`.

**2. Move `06-feature-track-stats-import.ipynb` → `1-data/04-feature-track-stats-import.ipynb`**

Same rationale. Postgres → SQL → parquet.

**3. Move `3-features/queries/` → `1-data/queries/`**

All four SQL files are Postgres extraction queries. Co-locating them with the import notebooks that run them makes the import pipeline self-contained.

**4. Update SQL file paths in notebooks 05 and 06**

Both notebooks load their SQL files with a relative path (e.g. `queries/mb_artist_country_fast_duckdb_release.sql`). After moving to `1-data/`, the path stays the same (`queries/...`) since both the notebooks and queries/ folder move together.

**5. Renumber `3-features/` after removing the two import notebooks**

After moving `05` and `06` out, the remaining sequence has a gap. Renumber:

| Current | New |
|---|---|
| `01-album-artist-index.ipynb` | `01-album-artist-index.ipynb` (unchanged) |
| `02-feature-genre.ipynb` | `02-feature-genre.ipynb` (unchanged) |
| `03-feature-label.ipynb` | `03-feature-label.ipynb` (unchanged) |
| `04-feature-ratings.ipynb` | `04-feature-ratings.ipynb` (unchanged) |
| `05-feature-country-import.ipynb` | → moved to `1-data/` |
| `06-feature-track-stats-import.ipynb` | → moved to `1-data/` |
| `07-feature-country.ipynb` | `05-feature-country.ipynb` |
| `08-feature-track-stats.ipynb` | `06-feature-track-stats.ipynb` |
| `09-feature-era.ipynb` | `07-feature-era.ipynb` |
| `10-feature-assembly.ipynb` | `08-feature-assembly.ipynb` |

### Decisions needed

| Item | Question |
|---|---|
| `05-feature-country-import.ipynb` | Move to `1-data/`? |
| `06-feature-track-stats-import.ipynb` | Move to `1-data/`? |
| `3-features/queries/` | Move to `1-data/queries/`? |
| `3-features/` renumbering | Renumber 07–10 → 05–08 after the moves? |

---

## data/ and project-wide file audit — 2026-06-08

### data/ parquets — all 15 committed parquets assessed

All `mb_*.parquet` base table exports are active. No base parquet can be removed.

The two flag parquets (`mb_album_live_flag.parquet`, `mb_album_compilation_flag.parquet`) are specifically used by `app_v3_weighted.py` (the current production app) for the Live/Greatest Hits fader filters, and also by the new EDA album section. Both are required.

**Summary: no committed parquets can be removed.**

---

### data/features/ — matrix and index file audit

| File | Git | Written by | Read by | Verdict |
|---|---|---|---|---|
| `album_ids.pkl` | ✅ committed | `3-features/01-album-artist-index` | All feature + model notebooks | Required |
| `artist_ids.pkl` | ✅ committed | `3-features/01-album-artist-index` | Genre feature notebook | Required |
| `album_era.parquet` | ✅ committed | `3-features/07-feature-era` | Nothing downstream | **Metadata only** — not read by any model or app. Kept for debugging/audit use. No action needed but worth knowing. |
| `album_tags_matrix.npz` | gitignored | `3-features/02-feature-genre` | `4-model/01-knn-v1-training` only | Used by v1 model training only — v2/v3 use `album_genre_matrix` |
| `artist_tags_matrix.npz` | gitignored | `3-features/02-feature-genre` | Nothing — intermediate artefact only | **Orphaned intermediate.** Built as a step toward `album_genre_matrix` but never loaded by any model or app. **Delete.** |
| `album_primary_artist_ratings_matrix.npz` | gitignored | `3-features/04-feature-ratings` | Nothing | **Orphaned artefact.** Built but never read anywhere in the project. **Delete.** |
| `album_labels_matrix.npz` | gitignored | `3-features/03-feature-label` | v1 + v2 model notebooks | Required for v1/v2 |
| `album_types_matrix.npz` | gitignored | `3-features/03-feature-label` | All model notebooks | Required (all versions) |
| `album_record_label_matrix.npz` | gitignored | `3-features/03-feature-label` | v3 model notebook | Required for v3 |
| `album_ratings_matrix.npz` | gitignored | `3-features/04-feature-ratings` | All model notebooks | Required (all versions) |
| `album_genre_matrix.npz` | gitignored | `3-features/02-feature-genre` | v2 + v3 model notebooks | Required for v2/v3 |
| `album_country_matrix.npz` | gitignored | `3-features/05-feature-country` | v3 model notebook + app | Required for v3/weighted app |
| `album_track_stats_matrix.npz` | gitignored | `3-features/06-feature-track-stats` | v3 model notebook | Required for v3 |
| `album_era_matrix.npz` | gitignored | `3-features/07-feature-era` | `5-app/app_v3_weighted.py` | Required — weighted app reads it directly |

**Two files to delete:**
1. `data/features/artist_tags_matrix.npz` — intermediate build artefact, nothing reads it
2. `data/features/album_primary_artist_ratings_matrix.npz` — built by the ratings notebook, never loaded

Both are gitignored so deletion is local only — no git change needed. The feature notebooks that write them should also have the save cell removed or commented so they don't regenerate on next run.

---

### Misplaced files — scan of all folders

**Project root** — clean. Only config files (`README.md`, `.gitignore`, `.env.example`, `requirements.txt`, `musicbrainz.duckdb`). Nothing misplaced.

**docs/** — clean. All markdown files are pipeline documentation, correctly placed.

**Planning/** — two files:

| File | Status |
|---|---|
| `restructure.md` | Active planning log — keep here while cleanup is in progress |
| `merge-lastfm.md` | Unimplemented proposal for a future feature. Keep here as a backlog item. |

**archive/** — five files, all safe to permanently delete:

| File | Why safe to delete |
|---|---|
| `01-feature-tags-labels.ipynb` | Superseded by `3-features/02-feature-genre` + `03-feature-label` |
| `10-feature-genre-tags.ipynb` | Superseded by `3-features/02-feature-genre` |
| `03-EDA-master.ipynb` | master_df removed from pipeline; EDA covered by active notebooks |
| `cleanup.md` | June 2 session log; superseded by git history |
| `year_feature.md` | Era feature complete; planning notes have no further value |

### Actions

1. **Delete `data/features/artist_tags_matrix.npz`** (local only — gitignored)
2. **Delete `data/features/album_primary_artist_ratings_matrix.npz`** (local only — gitignored)
3. **Remove the save cells for both files from their feature notebooks:**
   - `artist_tags_matrix.npz` is saved in `3-features/02-feature-genre.ipynb` — remove or comment the `.save()` call
   - `album_primary_artist_ratings_matrix.npz` is saved in `3-features/04-feature-ratings.ipynb` — remove or comment the `.save()` call
4. **Delete all 5 files in `archive/`** — all superseded, git history preserves them if ever needed

---

## docs/08-howto-model-v2.md review — 2026-06-08

### Problems with the current file

**Name is wrong on two counts:**
- `08` — the numbering implies it's the eighth topic in a reference series, but docs 06 and 07 are historical SQL context notes (not part of the main series). There is no logical sequence from 05-app.md to this file.
- `howto-model-v2` — the file no longer covers "how to add v2". It is now a full pipeline rebuild guide covering all features (country, track stats, genre, era) and all models (v1, v2, v3), ending with running the app. The "v2" name is a leftover from when it was originally written just to document the v2 model addition.

**Content scope is incomplete:**
The prerequisites section hand-waves over the base pipeline (data import, v1 feature build) rather than treating them as numbered steps. A reader rebuilding from scratch has to cross-reference the README rebuild section alongside this doc. The two should be one or the other — not both partial.

**Wrong document type for `docs/`:**
The other docs (`01`–`05`) are **reference documentation** — they explain what the pipeline does, what the schemas are, what the maths is. This file is a **runbook** — step-by-step operational instructions for a specific task (rebuild everything). These are different in nature and a new reader would look for them in different places.

**Duplication with README:**
The README "Re-building from scratch" section lists the same notebooks in order. This doc adds expected output shapes and "skip unless regenerating" notes, but the two now overlap enough that maintaining both is a burden.

### Recommendation

**Rename to `REBUILDING.md` and move to the project root.**

- Project root is where developers expect operational runbooks — alongside `README.md`, `requirements.txt`, `.env.example`. This is the same convention used by many open-source projects (`CONTRIBUTING.md`, `DEPLOYING.md`, etc.).
- Keeping it in `docs/` alongside the reference docs creates a category mismatch.
- Moving it to root also means it's visible immediately on GitHub without navigating into `docs/`.

**Expand to cover the full pipeline as numbered steps** (no prerequisites hand-wave):

All data imports come first. All three parquets are already committed so can be skipped unless regenerating from a fresh MusicBrainz Postgres instance — this should be clearly flagged per step, not buried in a prerequisites section. Model training is not included: the current app (`app_v3_weighted.py`) reads raw feature matrices directly and requires no trained model. EDA notebooks are not included — they are for exploration only and produce nothing the pipeline consumes.

| Step | What | Notebook | Needs Postgres? |
|---|---|---|---|
| 1 | Import base parquets | `1-data/01-postgres-to-parquet.ipynb` | ✅ Yes (skip if committed parquets are current) |
| 2 | Import artist country parquet | `1-data/03-feature-country-import.ipynb` | ✅ Yes (skip if committed parquet is current) |
| 3 | Import track stats parquet | `1-data/04-feature-track-stats-import.ipynb` | ✅ Yes (skip if committed parquet is current) |
| 4 | Build album/artist ID index | `3-features/01-album-artist-index.ipynb` | ❌ |
| 5 | Build genre matrix | `3-features/02-feature-genre.ipynb` | ❌ |
| 6 | Build label matrix | `3-features/03-feature-label.ipynb` | ❌ |
| 7 | Build ratings matrix | `3-features/04-feature-ratings.ipynb` | ❌ |
| 8 | Build country matrix | `3-features/05-feature-country.ipynb` | ❌ |
| 9 | Build track stats matrix | `3-features/06-feature-track-stats.ipynb` | ❌ |
| 10 | Build era matrix | `3-features/07-feature-era.ipynb` | ❌ |
| 11 | Run the app | `streamlit run 5-app/app_v3_weighted.py` | ❌ |

Steps 1–3 require Postgres and can all be skipped if the committed parquets are used as-is. Steps 4–10 build feature matrices from those parquets. Step 11 runs the app.

**Remove the README "Re-building from scratch" section** once this exists as `REBUILDING.md` — the README can just link to it. This eliminates the duplication.

**Keep `docs/08-howto-model-v2.md` for now** as a redirect/stub pointing to `REBUILDING.md`, or simply delete it once `REBUILDING.md` is in place. Docs 06 and 07 (historical SQL context) can stay in `docs/` as they are purely reference notes.

### Decisions needed

| Item | Question |
|---|---|
| File location | Move to project root as `REBUILDING.md`, or keep in `docs/` with a better name? |
| README rebuild section | Remove it once `REBUILDING.md` exists, or keep both? |
| `docs/08-howto-model-v2.md` | Delete once replaced, or keep as stub? |
