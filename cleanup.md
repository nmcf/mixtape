# Project Cleanup — Change Log

Documents all changes made to the project during the cleanup session on 2026-06-02.

---

## 1. New branch structure

Two branches were created from `main`:

- `cleanup-recovery` — untouched backup of the original project state, kept for reference
- `cleanup` — working branch where all changes were made and pushed for review

---

## 2. Project restructure into three sections

The project was reorganised from a flat collection of folders into three numbered sections that reflect the pipeline stages.

### New top-level structure

```
mixtape/
├── 1-EDA/          ← early data exploration and schema review
├── 2-Prototyping/  ← feature engineering and model training
├── 3-app/          ← the Streamlit application
├── data/           ← shared data store (unchanged)
├── docs/           ← pipeline documentation (unchanged)
├── musicbrainz.duckdb
├── requirements.txt
├── README.md
├── .ai_context.md
├── .env / .env.example
└── .gitignore
```

### Files moved into `1-EDA/`

| Old path | New path |
|---|---|
| `EDA/EDA-albums.ipynb` | `1-EDA/03-EDA-albums.ipynb` |
| `EDA/EDA-artists.ipynb` | `1-EDA/04-EDA-artists.ipynb` |
| `EDA/EDA-master.ipynb` | `1-EDA/05-EDA-master.ipynb` |
| `datasets/duckdb-parquet.ipynb` | `1-EDA/01-postgres-to-parquet.ipynb` |
| `datasets/parquet-dataframes.ipynb` | `1-EDA/02-parquet-to-dataframes.ipynb` |
| `SchemaSpy/` | `1-EDA/SchemaSpy/` |
| `docs/06-schema-diagrams.md` | `1-EDA/06-schema-diagrams.md` |

Deleted after moving (now empty): `EDA/`, `datasets/`

### Files moved into `2-Prototyping/`

| Old path | New path |
|---|---|
| `features/weights-tags.ipynb` | `2-Prototyping/01-feature-tags-labels.ipynb` |
| `features/weights-ratings.ipynb` | `2-Prototyping/02-feature-ratings.ipynb` |
| `features/features.ipynb` | `2-Prototyping/03-feature-assembly.ipynb` |
| `model/knn.ipynb` | `2-Prototyping/04-knn-training.ipynb` |
| `model/knn-query.ipynb` | `2-Prototyping/05-knn-query.ipynb` |
| `features/sparse_features_structural_analysis.png` | `2-Prototyping/sparse_features_structural_analysis.png` |

Deleted after moving (now empty): `features/`, `model/`

### Files moved into `3-app/`

| Old path | New path |
|---|---|
| `app/app.py` | `3-app/app.py` |

Deleted after moving (now empty): `app/`

> **Note:** The folder was initially named `3-model/` then renamed to `3-app/` to better reflect its contents.

---

## 3. Notebook renames

All notebooks were given numbered prefixes and descriptive names to make the run order and purpose immediately clear.

### `1-EDA/`

| Old name | New name |
|---|---|
| `duckdb-parquet.ipynb` | `01-postgres-to-parquet.ipynb` |
| `parquet-dataframes.ipynb` | `02-parquet-to-dataframes.ipynb` |
| `EDA-albums.ipynb` | `03-EDA-albums.ipynb` |
| `EDA-artists.ipynb` | `04-EDA-artists.ipynb` |
| `EDA-master.ipynb` | `05-EDA-master.ipynb` |

### `2-Prototyping/`

| Old name | New name |
|---|---|
| `weights-tags.ipynb` | `01-feature-tags-labels.ipynb` |
| `weights-ratings.ipynb` | `02-feature-ratings.ipynb` |
| `features.ipynb` | `03-feature-assembly.ipynb` |
| `knn.ipynb` | `04-knn-training.ipynb` |
| `knn-query.ipynb` | `05-knn-query.ipynb` |

---

## 4. File path fixes

Only one path change was required across all notebooks after the restructure:

| File | Old value | New value |
|---|---|---|
| `1-EDA/01-postgres-to-parquet.ipynb` | `duckdb.connect("musicbrainz.duckdb")` | `duckdb.connect("../musicbrainz.duckdb")` |

All other notebook paths (`../data/...`) remained valid because all notebooks stayed at depth 1 (one directory below the project root). `app.py`'s `DATA_DIR` also required no change as `3-app/` is at the same depth as the old `app/`.

---

## 5. Data folder changes

One directory was deleted from `data/`:

| Path | Action | Reason |
|---|---|---|
| `data/npz/` | Deleted | Exact duplicate of `data/features/` — identical 9 files, `data/features/` is the one all notebooks reference |

All 10 parquet files were kept for pipeline reproducibility (not everyone has access to the MusicBrainz PostgreSQL database). All model artefacts and feature matrices were left in place.

---

## 6. Notebook documentation added

Every notebook in `1-EDA/` and `2-Prototyping/` received:

- **A header markdown cell** at the top covering: purpose, what it does, inputs, outputs, and run order relative to neighbouring notebooks
- **Inline developer markdown cells** between every code cell explaining the logic of each step — what is happening, why decisions were made, and what the output is used for downstream

---

## 7. Requirements cleanup

Three unused packages were removed from `requirements.txt`:

| Package | Reason removed |
|---|---|
| `SQLAlchemy` | Never imported — DuckDB connects to Postgres natively via its own extension |
| `psycopg2-binary` | Never imported — DuckDB Postgres scanner is used instead |
| `ipywidgets` | Never imported — `ydata-profiling` renders via iframe, not widgets |

A usage note was added to `duckdb` clarifying it is only needed for re-importing data from Postgres.

---

## 8. Documentation updates

All documentation was updated to reflect the new structure:

| File | Changes |
|---|---|
| `README.md` | Updated run command, project layout, rebuild instructions, and doc links |
| `.ai_context.md` | Updated structure diagram, pipeline stages, notebook inventory, and run command; added Notebooks section describing inline docs |
| `docs/01-data-import.md` | Updated notebook path |
| `docs/02-datasets.md` | Updated notebook path |
| `docs/03-features.md` | Updated notebook paths and PNG path |
| `docs/04-model.md` | Updated notebook paths |
| `docs/05-app.md` | Updated file path and run command |

---

## 9. Files kept locally (not committed)

| Path | Reason |
|---|---|
| `env/` | Local virtual environment — gitignored, reproducible from `requirements.txt` |
| `.DS_Store` | macOS metadata — not project content |
| `.ai_context.md` | Committed to git so team members can use it |
