# Cleanup Plan

## Target structure

```
mixtape/
├── 1-EDA/
├── 2-Prototyping/
├── 3-model/
├── data/              ← stays as-is (all parquets, features, model artefacts)
├── docs/
├── musicbrainz.duckdb
├── requirements.txt
├── README.md
├── .ai_context.md     ← keep locally, update after cleanup
├── .env / .env.example
├── .gitignore
└── env/               ← keep locally
```

The `data/` directory is the shared data store for all three sections. Notebooks are reorganised but data paths are preserved where possible — see path impact notes below.

---

## Section 1 — `1-EDA/`

Early data exploration and schema review.

**Move into `1-EDA/` (flat, no subdirectories):**

| Current path | New path | Path changes required |
|---|---|---|
| `EDA/EDA-albums.ipynb` | `1-EDA/EDA-albums.ipynb` | None — `../data/pickles/` still resolves correctly |
| `EDA/EDA-artists.ipynb` | `1-EDA/EDA-artists.ipynb` | None — `../data/pickles/` still resolves correctly |
| `EDA/EDA-master.ipynb` | `1-EDA/EDA-master.ipynb` | None — `../data/pickles/` still resolves correctly |
| `datasets/duckdb-parquet.ipynb` | `1-EDA/duckdb-parquet.ipynb` | `duckdb.connect("musicbrainz.duckdb")` → `duckdb.connect("../musicbrainz.duckdb")`. Output parquet paths `../data/mb_*.parquet` unchanged |
| `datasets/parquet-dataframes.ipynb` | `1-EDA/parquet-dataframes.ipynb` | None — `../data/mb_*.parquet` and `../data/pickles/` still resolve correctly |
| `SchemaSpy/` | `1-EDA/SchemaSpy/` | None — static HTML, no file path dependencies |
| `docs/06-schema-diagrams.md` | `1-EDA/06-schema-diagrams.md` | Internal links to SchemaSpy stay valid (same directory) |

**Delete after moving (now empty):**
- `EDA/`
- `datasets/`

---

## Section 2 — `2-Prototyping/`

Feature engineering and model training work. All notebooks kept flat (directly inside `2-Prototyping/`) so that `../data/` paths continue to resolve to the root `data/` directory without changes.

**Move into `2-Prototyping/` (flat):**

| Current path | New path | Path changes required |
|---|---|---|
| `features/features.ipynb` | `2-Prototyping/features.ipynb` | None — `../data/features/` and `../data/mb_album.parquet` still resolve correctly |
| `features/weights-ratings.ipynb` | `2-Prototyping/weights-ratings.ipynb` | None — `../data/features/` and `../data/mb_*.parquet` still resolve correctly |
| `features/weights-tags.ipynb` | `2-Prototyping/weights-tags.ipynb` | None — `../data/features/` and `../data/mb_*.parquet` still resolve correctly |
| `features/sparse_features_structural_analysis.png` | `2-Prototyping/sparse_features_structural_analysis.png` | None |
| `model/knn.ipynb` | `2-Prototyping/knn.ipynb` | None — `../data/features/`, `../data/model/`, `../data/mb_album.parquet` still resolve correctly |
| `model/knn-query.ipynb` | `2-Prototyping/knn-query.ipynb` | None — `../data/model/` and `../data/mb_album_artists.parquet` still resolve correctly |

**Delete after moving (now empty):**
- `features/`
- `model/`

---

## Section 3 — `3-model/`

The Streamlit app — the final deliverable.

**Move into `3-model/`:**

| Current path | New path | Path changes required |
|---|---|---|
| `app/app.py` | `3-model/app.py` | None — `DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')` resolves to `mixtape/data/` from either location. Both `app/` and `3-model/` are at the same depth |

**Delete after moving (now empty):**
- `app/`

---

## `data/` — stays at root, one change

All parquet files are kept (needed for feature pipeline reproducibility). All model artefacts stay in `data/model/`. All feature matrices stay in `data/features/`.

**One delete inside `data/`:**

| Path | Action | Reason |
|---|---|---|
| `data/npz/` | Delete | Exact duplicate of `data/features/` — same 9 files, same content. `data/features/` is the one all notebooks reference, so `data/npz/` is the orphan |

---

## `docs/` — minor trim

`docs/01` through `docs/05` stay at `docs/`. `docs/06-schema-diagrams.md` moves to `1-EDA/` (see above) since it directly references the SchemaSpy directory.

---

## Keep locally (no changes)

| Path | Reason |
|---|---|
| `env/` | Local virtual environment, keep for active development |
| `.DS_Store` | macOS metadata, keep locally |
| `.ai_context.md` | Update with new structure after cleanup is done |

---

## Full path change summary

Only two path changes are needed across all notebooks:

| File | Old path | New path |
|---|---|---|
| `1-EDA/duckdb-parquet.ipynb` | `duckdb.connect("musicbrainz.duckdb")` | `duckdb.connect("../musicbrainz.duckdb")` |

All other notebook paths (`../data/...`) resolve correctly from their new locations because all notebooks stay at depth 1 (one level below the project root).

`app.py`'s `DATA_DIR` requires no change — `3-model/` is at the same depth as the old `app/`.

---

## Nothing else to delete

All other files are either kept, moved, or locally retained. No data is lost.
