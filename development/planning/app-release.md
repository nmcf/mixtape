# App Release Plan

**Goal:** Extract the Streamlit app into a clean, self-contained repo that a new user can clone and run locally with `streamlit run app/app.py` — no MusicBrainz Postgres, no notebooks, no build steps.

All development artefacts (notebooks, EDA, feature engineering, model training, scraper) stay in this repo under a `development/` folder. The release repo contains only what the app reads at runtime.

---

## Branch Strategy

Three branches stage the work from active development to a clean public release:

| Branch | Role | What lives here |
|--------|------|-----------------|
| `feature_merge` | **Development** | Everything — notebooks, EDA, feature engineering, model training, scraper, the app, and all data. The working branch where features are built and merged. |
| `app_release` | **Clean-up** | The restructured repo: `app/` + release `data/` at root, with all dev artefacts moved under `development/`. New release-facing features and the final folder layout are prepared here. `development/` is still present. |
| `app_testing` | **Final check** | The release subset **only** — `development/` is removed entirely. Used to verify the app clones and runs with nothing but the runtime files, before merging to `main`. |

**Flow:** `feature_merge` → `app_release` (restructure + new features) → `app_testing` (strip `development/`, verify clean run) → `main`.

The purpose of `app_testing` is to confirm we carried across **everything the app needs** and **left behind everything that was development-only**. If the app runs cleanly on `app_testing` with no `development/` folder, the release is complete.

### Files & folders to commit to `app_testing` (the release)

These are the only things that should exist on the `app_testing` branch:

```
app/                              # all 5 scripts + components + .streamlit/
├── app.py
├── config.py
├── controls.py
├── engine.py
├── style.py
├── knob_component/index.html
├── fader_component/index.html
└── .streamlit/config.toml
assets/
└── cassette-header.svg           # README header graphic
data/
├── features/                     # 7 runtime .npz matrices
├── index/                        # album_ids.pkl, mb_tag.parquet, mb_area.parquet
└── metadata/                     # 5 runtime parquets
README.md                         # release README (from readme-draft)
requirements.txt                  # runtime-only deps (8 packages)
LICENSE
.gitignore                        # release version (no development/ rules needed)
```

### Files & folders that stay behind on `app_release` (development only)

Everything below is removed before `app_testing` is finalised — it belongs only to the development/clean-up branch:

```
development/                      # the entire folder — remove on app_testing
├── 1-data/  2-eda/  3-features/  4-model/
├── archive/  docs/  planning/  presentation/
├── data/                         # dev-only features, metadata, scraped, model*, pickles
├── README.md                     # original dev README
├── REBUILDING.md                 # pipeline rebuild guide
├── .ai_context.md                # AI working context
├── musicbrainz.duckdb            # local MB cache (also gitignored)
└── requirements.txt              # full dev dependency list
.env                              # DB credentials — not needed (app has no DB connection)
.env.example                      # DB credential template — dev only
.claude/                          # local AI tooling (already gitignored)
env/                              # local virtualenv (already gitignored)
```

**Note:** `.env` / `.env.example` are not required by the app (no Postgres connection at runtime) and should not appear on `app_testing`. The release `.gitignore` can drop the `development/` and `data/model*` rules since neither exists on that branch.

---

## File Size Audit

All release files checked against 100 MB hard limit and 50 MB warning threshold.

| File | Size | Status |
|------|------|--------|
| `album_track_stats_matrix.npz` | 53 MB | ⚠️ >50 MB — watch for Git LFS |
| `mb_album_artists.parquet` | 40 MB | ✅ |
| `mb_album_secondary_type.parquet` | 16 MB | ✅ |
| `album_genre_matrix.npz` | 15 MB | ✅ |
| `album_ids.pkl` | 8.4 MB | ✅ |
| `mb_album_country.parquet` | 6.9 MB | ✅ |
| `mb_release_year.parquet` | 5.8 MB | ✅ |
| `album_temporal_matrix.npz` | 4.6 MB | ✅ |
| `mb_album_tag.parquet` | 4.5 MB | ✅ |
| `mb_tag.parquet` | 3.4 MB | ✅ |
| `album_country_matrix.npz` | 3.6 MB | ✅ |
| `album_lastfm_popularity_matrix.npz` | 2.6 MB | ✅ |
| `album_record_label_matrix.npz` | 1.8 MB | ✅ |
| `mb_area.parquet` | 1.5 MB | ✅ |
| `album_ratings_matrix.npz` | 758 KB | ✅ |

**No files exceed 100 MB.** One file (`album_track_stats_matrix.npz`, 53 MB) exceeds the 50 MB threshold and should be tracked with Git LFS in the release repo.

**Estimated total release data size: ~168 MB**

---

## Files Removed from Release List After Code Audit

A review of `engine.py` confirmed the following files are **not read at runtime** and belong in `development/` only:

| File | Why it was listed | Why it's not needed |
|------|--------------------|---------------------|
| `mb_artist.parquet` (36 MB) | Assumed needed for artist display | Not loaded anywhere in engine.py |
| `mb_artist_credit.parquet` (26 MB) | Assumed needed for search | Not loaded anywhere in engine.py |
| `sql_feature_artist_country_fast.parquet` (38 MB) | Assumed app source | Feature already baked into `album_country_matrix.npz` |
| `sql_feature_album_track_stats.parquet` (80 MB) | Assumed app source | Feature already baked into `album_track_stats_matrix.npz` |
| `mb_album_ratings.parquet` | Assumed ratings source | Ratings baked into `album_ratings_matrix.npz` |
| `mb_album_label.parquet` | Assumed label display | Not loaded anywhere in engine.py |
| `mb_album_compilation_flag.parquet` | Assumed content filter source | Superseded by `mb_album_secondary_type.parquet` |
| `mb_album_live_flag.parquet` | Assumed content filter source | Superseded by `mb_album_secondary_type.parquet` |
| `mb_artist_tag.parquet` | Assumed Explore tab source | Not loaded in load_explore_data |
| `artist_ids.pkl` | Assumed index file | Not loaded in load_blocks or anywhere in engine.py |
| `temporal_year_scaler.json` | Assumed params file | Not loaded by the app — year scaling is baked into the matrix |
| `mb_album.parquet` | Assumed core table | Path resolved into `album_path` in `load_explore_data` but variable is never used — dead reference. Comment on the same line confirms it was ruled out (`mb_album.parquet has no year column`). Not needed. |

---

## What the App Actually Needs at Runtime

### Python scripts
All currently in `5-app/` → rename folder to `app/` in both repos:

| File | Role |
|------|------|
| `app.py` | Entry point — layout, tabs, result rendering |
| `config.py` | Constants, presets, weight↔dial helpers, `BLOCK_FILES`, all path variables |
| `engine.py` | Data loading (cached), weighted-cosine query, auto-tune, artist/explore search |
| `controls.py` | Sidebar widgets — preset buttons, knob panel, auto-tune, faders |
| `style.py` | CSS injection, dark/light theme |
| `knob_component/index.html` | SVG rotary knob panel |
| `fader_component/index.html` | Vertical mixing-console faders (Live/Hits filters) |
| `.streamlit/config.toml` | Port, theme, cache settings |

### Data files — confirmed runtime reads

**features/** (7 .npz matrices)

| File | Feature block | Size |
|------|---------------|------|
| `album_genre_matrix.npz` | Genre (10,255 cols; 3-tier tag blend) | 15 MB |
| `album_record_label_matrix.npz` | Record Label (2,968 cols) | 1.8 MB |
| `album_country_matrix.npz` | Country (2,014 cols; one-hot) | 3.6 MB |
| `album_track_stats_matrix.npz` | Track Stats (12 cols; min-max scaled) | 53 MB ⚠️ |
| `album_temporal_matrix.npz` | Era (11 cols; one-hot + continuous year) | 4.6 MB |
| `album_lastfm_popularity_matrix.npz` | Popularity — Last.fm (2 cols; log1p) | 2.6 MB |
| `album_ratings_matrix.npz` | Popularity — Ratings (1 col; Bayesian) | 758 KB |

**index/** (1 .pkl + 2 parquets)

| File | Used for | Size |
|------|----------|------|
| `album_ids.pkl` | Master row index — matrix row ↔ release group id | 8.4 MB |
| `mb_tag.parquet` | Tag vocabulary for Explore genre picker | 3.4 MB |
| `mb_area.parquet` | Country names for Explore country filter | 1.5 MB |

**metadata/** (5 parquets)

| File | Used for | Size |
|------|----------|------|
| `mb_album_artists.parquet` | Album/artist name lookup (title, artist_name per album_id) | 40 MB |
| `mb_album_country.parquet` | Country per album + album_year (primary year source for Explore) | 6.9 MB |
| `mb_album_secondary_type.parquet` | Live/Greatest Hits flags for content filters | 16 MB |
| `mb_album_tag.parquet` | Album ↔ tag mapping for Explore tab scoring | 4.5 MB |
| `mb_release_year.parquet` | Release year (fallback if mb_album_country lacks album_year) | 5.8 MB |

---

## Path Changes Required in Source Files

### Current path setup (`config.py`)
```python
HERE         = os.path.dirname(os.path.abspath(__file__))
DATA_DIR     = os.path.join(HERE, '..', 'data')
FEATURES_DIR = os.path.join(DATA_DIR, 'features')
```

### Required additions to `config.py`
Add directory constants for the two new sub-folders so no path is hardcoded elsewhere:
```python
METADATA_DIR = os.path.join(DATA_DIR, 'metadata')
INDEX_DIR    = os.path.join(DATA_DIR, 'index')
```
`DATA_DIR` and `FEATURES_DIR` are unchanged — `app/` sits at the same depth as `5-app/` relative to `data/`.

### Changes to `engine.py`

**1. Import the new path variables from config:**
```python
from config import (DATA_DIR, FEATURES_DIR, METADATA_DIR, INDEX_DIR, ...)
```

**2. `_find_parquet` — update search order:**
Currently searches `data/raw/` then `data/` root. Update to search `data/metadata/` then `data/index/`:
```python
def _find_parquet(name):
    for sub in ['metadata', 'index']:
        p = os.path.join(DATA_DIR, sub, name)
        if os.path.exists(p):
            return p
    return None
```

**3. `load_blocks` — update `album_ids.pkl` path:**
Currently reads from `FEATURES_DIR`. Move to `INDEX_DIR`:
```python
# Before
with open(os.path.join(FEATURES_DIR, 'album_ids.pkl'), 'rb') as f:
# After
with open(os.path.join(INDEX_DIR, 'album_ids.pkl'), 'rb') as f:
```

**No other hardcoded paths exist in the app scripts** — all other file references go through `_find_parquet` or `BLOCK_FILES` (which uses `FEATURES_DIR`). All path logic is cleanly centralised in `config.py`.

---

## Requirements Files

The existing `requirements.txt` stays in this repo under `development/` as the full development dependency list (notebooks, scraping, DB tooling).

A new, separate `requirements.txt` is created for the release repo containing only runtime dependencies:

```
# Mixtape — runtime dependencies only
pandas
numpy
scikit-learn
scipy
joblib
pyarrow
streamlit
streamlit-searchbox
```

Packages present in dev `requirements.txt` that are **not** included in the release:
`duckdb`, `ydata-profiling`, `matplotlib`, `seaborn`, `jupyterlab`, `ipykernel`, `ipywidgets`, `requests`, `beautifulsoup4`, `filelock`, `openpyxl`, `rapidfuzz`, `python-dotenv`

Note: `python-dotenv` is dropped — no `.env` file exists in the release (no DB connection). Confirm it is not imported in any app script before removing.

---

## Suggested Folder Structure — Release Repo

```
mixtape-app/                          # new public repo
├── app/                              # renamed from 5-app/
│   ├── app.py
│   ├── config.py
│   ├── engine.py
│   ├── controls.py
│   ├── style.py
│   ├── knob_component/
│   │   └── index.html
│   ├── fader_component/
│   │   └── index.html
│   └── .streamlit/
│       └── config.toml
├── assets/                           # static files referenced by README
│   └── cassette-header.svg           # header graphic (copy from planning/cassette-header.svg)
├── data/
│   ├── features/                     # .npz sparse matrices — one per feature block
│   │   ├── album_genre_matrix.npz
│   │   ├── album_record_label_matrix.npz
│   │   ├── album_country_matrix.npz
│   │   ├── album_track_stats_matrix.npz      # ⚠️ 53 MB — use Git LFS
│   │   ├── album_temporal_matrix.npz
│   │   ├── album_lastfm_popularity_matrix.npz
│   │   └── album_ratings_matrix.npz
│   ├── index/                        # row/ID maps + UI vocabulary lookups
│   │   ├── album_ids.pkl
│   │   ├── mb_tag.parquet
│   │   └── mb_area.parquet
│   └── metadata/                     # album/artist property tables
│       ├── mb_album_artists.parquet
│       ├── mb_album_country.parquet
│       ├── mb_album_secondary_type.parquet
│       ├── mb_album_tag.parquet
│       └── mb_release_year.parquet
├── requirements.txt                  # runtime-only deps (new file — see Requirements section)
├── README.md
└── .gitignore
```

### Data folder rationale

| Folder | Contents | Rule of thumb |
|--------|----------|---------------|
| `features/` | `.npz` sparse matrices | Loaded by `engine.py` for weighted-cosine scoring — one file per feature block |
| `index/` | `.pkl` row map + vocabulary parquets | Files that translate between IDs/positions and human-readable values |
| `metadata/` | Property parquets | Structured tables loaded for display, search, and filtering |

---

## Stray Dev-Only Files to Relocate

The following files are currently in `data/` or `data/features/` but are not needed at runtime and are not yet listed anywhere in the plan. They move to `development/` data or are otherwise accounted for below.

| File | Current location | Move to | Notes |
|------|-----------------|---------|-------|
| `album_era.parquet` | `data/features/` | `development/` data | Intermediate artefact from `14-feature-temporal.ipynb`; superseded by `album_temporal_matrix.npz` |
| `year_scaler.json` | `data/features/` | `development/` data | Older scaler file; superseded by `temporal_year_scaler.json` (itself also dev-only) |
| `album_tag_parent_columns.json` | `data/features/` | `development/` data | Output of `01b-feature-tag-hierarchy.ipynb`; not used by app |
| `best_weights.json` | `data/` | `development/` data | Tuning artefact from weight optimisation notebooks |
| `lastfm_data.parquet` | `data/` | `development/` data | Raw Last.fm scraper output (34 MB); used to build `album_lastfm_popularity_matrix.npz` |
| `lastfm_album_matched.parquet` | `data/` | `development/` data | Matched Last.fm scrobble data (25 MB); used in feature notebook only |

**`data/raw/` dissolution:** The `data/raw/` subfolder ceases to exist in both repos. Its three files redistribute:
- `mb_album_secondary_type.parquet` → `data/metadata/`
- `mb_tag.parquet` → `data/index/`
- `mb_area.parquet` → `data/index/`

---

## `.gitignore` Notes

### Dev repo — one missing entry
`data/model_v4/` is not in the current `.gitignore` (only v1–v3 are listed). Add it:
```
data/model_v4/
```

### Release repo — create from scratch
The release repo needs a new `.gitignore` covering:
```
# Python environment
env/
venv/
__pycache__/
*.pyc
*.pyo

# OS
.DS_Store
Thumbs.db

# Secrets (belt-and-suspenders — no .env should exist in this repo)
.env
```

Note: all `data/` files in the release repo should be tracked (small enough, no secrets). Git LFS handles `album_track_stats_matrix.npz`.

---

## `REBUILDING.md` Update Required

`REBUILDING.md` documents the full pipeline rebuild procedure and references the current folder layout (`1-data/`, `2-eda/`, etc. at repo root). After restructuring, all those paths are under `development/`. Add a checklist item to update `REBUILDING.md` path references before closing out the restructure.

---

## Suggested Folder Structure — This Repo (Development)

```
mixtape/                              # this repo
├── development/
│   ├── 1-data/                       # data import notebooks
│   ├── 2-eda/                        # EDA notebooks
│   ├── 3-features/                   # feature engineering notebooks
│   ├── 4-model/                      # model training + evaluation notebooks
│   ├── archive/                      # retired notebooks and scripts
│   ├── docs/                         # pipeline documentation
│   ├── planning/                     # this file and all planning docs
│   └── presentation/                 # slide decks
├── app/                              # renamed from 5-app/ — the Streamlit app
├── data/
│   ├── features/                     # all .npz matrices (release subset + dev-only)
│   │                                 # dev-only here: album_era.parquet, year_scaler.json,
│   │                                 #   album_tag_parent_columns.json, temporal_year_scaler.json
│   ├── index/                        # album_ids.pkl, mb_tag.parquet, mb_area.parquet
│   ├── metadata/                     # runtime parquets + dev-only parquets kept here for rebuild access
│   ├── scraped/                      # lastfm_data.parquet, lastfm_album_matched.parquet
│   ├── model/                        # trained KNN models v1 (gitignored)
│   ├── model_v2/                     # trained KNN models v2 (gitignored)
│   ├── model_v3/                     # trained KNN models v3 (gitignored)
│   ├── model_v4/                     # trained KNN models v4 (gitignored — add to .gitignore)
│   └── pickles/                      # intermediate EDA dataframes (gitignored via *.pkl)
│   # Note: best_weights.json and stray dev parquets move here from data/ root
├── requirements.txt                  # full dev requirements — original file kept here (notebooks + app)
├── musicbrainz.duckdb                # local MB cache (gitignored)
├── .env                              # DB credentials (gitignored)
├── .env.example
├── .ai_context.md
├── README.md
└── REBUILDING.md
```

**Note:** `planning/`, `docs/`, `presentation/` and all numbered notebook folders move under `development/`. The `data/` folder stays at root level and is shared — only the release files are copied across to the new repo.

---

## Execution Checklist

Complete steps in this order — each group should leave the app in a working state before moving to the next.

### 1. Resolve open questions
- [x] Confirm whether `mb_album.parquet` is needed — **not needed**. `album_path` is resolved but never read; comment in code confirms it was ruled out. Stays in `development/`.
- [x] Confirm `python-dotenv` is not imported in any of the 5 app scripts — **confirmed clean**, no dotenv reference anywhere in `5-app/`.

### 2. Code changes (do before moving any files)
- [x] Apply path changes in `config.py` — add `METADATA_DIR` and `INDEX_DIR` constants
- [x] Apply path changes in `engine.py` — update `_find_parquet` search order (`metadata/`, `index/`) and `album_ids.pkl` load path (`INDEX_DIR`)
- [x] Add `data/model_v4/` to `.gitignore` in this repo

### 3. Restructure `data/` in this repo
- [x] Create `data/features/`, `data/index/`, `data/metadata/`, `data/scraped/` sub-folders (most already exist)
- [x] Move `data/raw/mb_album_secondary_type.parquet` → `data/metadata/`
- [x] Move `data/raw/mb_tag.parquet` → `data/index/`
- [x] Move `data/raw/mb_area.parquet` → `data/index/`
- [x] Move `data/features/album_ids.pkl` → `data/index/`
- [x] Move all 15 runtime parquets from `data/` root → `data/metadata/`
- [x] Move stray dev-only files: `best_weights.json`, `lastfm_data.parquet`, `lastfm_album_matched.parquet` → `data/scraped/` or otherwise out of the root
- [x] Delete now-empty `data/raw/` folder
- [x] **Test app still runs end-to-end** before continuing

### 4. Rename app folder
- [x] Rename `5-app/` → `app/`
- [x] **Test app still runs** (`streamlit run app/app.py`)

### 5. Restructure this repo's non-data folders
- [x] Create `development/` folder
- [x] Move `1-data/`, `2-eda/`, `3-features/`, `4-model/` → `development/`
- [x] Move `archive/`, `docs/`, `planning/`, `presentation/` → `development/`
- [x] Update `REBUILDING.md` — all pipeline path references change from `1-data/` etc. to `development/1-data/` etc.
- [x] **Final test** — confirm app still runs from repo root with new layout
- [x] Move `app/README.md` (dev artefact) → `development/archive/README-app.md`
- [x] Move root `README.md` (dev README) → `development/README.md`
- [x] Replace root `README.md` with `development/planning/readme-draft.md` — draft comment and path already correct

### 6. Create the release repo
- [ ] Create new repo `mixtape-app/`
- [ ] Initialise Git LFS, add tracking rule for `*.npz` or specifically `album_track_stats_matrix.npz`
- [ ] Copy `app/` folder across
- [ ] Copy release data files only (see "What the App Actually Needs at Runtime")
- [ ] Create `assets/` folder, copy `development/planning/cassette-header.svg` → `assets/cassette-header.svg`
- [ ] Write `.gitignore` for release repo (see `.gitignore` Notes section)
- [ ] Write `README.md` from draft (`development/planning/readme-draft.md`)
  - Update img path: `assets/cassette-header.svg` (already set in draft)
  - Remove the draft comment line above the img tag
- [ ] Write trimmed `requirements.txt` (runtime-only deps — see Requirements section)
- [ ] **Full end-to-end test** on a clean clone of the release repo
