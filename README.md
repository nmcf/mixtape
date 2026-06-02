# mixtape

Album recommendation engine built on the MusicBrainz database. Enter an artist you love, pick one of their albums, and get 10 similar albums recommended by a KNN model trained on community tags, ratings, and label data.

## How it works

1. **Data import** — a DuckDB notebook extracts artist/album data from a local MusicBrainz PostgreSQL instance and saves it as Parquet files.
2. **EDA** — notebooks explore the raw data at the album, artist, and joined dataset level.
3. **Features** — sparse feature matrices are built from tags, labels, types, and Bayesian-weighted ratings.
4. **Model** — a cosine-distance KNN model is trained on the L2-normalised feature matrix.
5. **App** — a Streamlit app serves recommendations in the browser.

See the [`docs/`](docs/) folder for detailed documentation on each step. Each notebook also contains inline developer notes explaining the logic of every cell.

## Prerequisites

- Python 3.11+
- A local MusicBrainz PostgreSQL database running at `localhost:5432` (only needed to re-import data; the Parquet files and trained model are included)

## Quick start

### 1. Clone the repo

```bash
git clone <repo-url>
cd mixtape
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv env
source env/bin/activate       # macOS/Linux
# .\env\Scripts\activate      # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the app

```bash
streamlit run 3-app/app.py
```

The app opens at **http://localhost:8501**.

No database connection is needed to run the app — the pre-built model and Parquet files in `data/` are all that's required.

## Re-building from scratch

If you want to re-import data or retrain the model, you'll need a MusicBrainz PostgreSQL database. Copy `.env.example` to `.env` and fill in your credentials, then run the notebooks in order:

```
1-EDA/01-postgres-to-parquet.ipynb              → imports Parquet files from Postgres
1-EDA/02-parquet-to-dataframes.ipynb            → builds pickled DataFrames

2-Prototyping/01-feature-tags-labels.ipynb      → builds tag, label, and type sparse matrices
2-Prototyping/02-feature-ratings.ipynb          → builds Bayesian-weighted rating matrices
2-Prototyping/03-feature-assembly.ipynb         → inspects and validates the combined matrix
2-Prototyping/04-knn-training.ipynb             → trains and saves the KNN model
```

## Project layout

```
mixtape/
├── 1-EDA/
│   ├── 01-postgres-to-parquet.ipynb    Import: Postgres → Parquet
│   ├── 02-parquet-to-dataframes.ipynb  Build: Parquet → pickled DataFrames
│   ├── 03-EDA-albums.ipynb             Exploratory analysis: albums
│   ├── 04-EDA-artists.ipynb            Exploratory analysis: artists
│   ├── 05-EDA-master.ipynb             Exploratory analysis: joined dataset
│   ├── 06-schema-diagrams.md           Schema and data flow diagrams
│   └── SchemaSpy/                      Auto-generated HTML schema visualisation
├── 2-Prototyping/
│   ├── 01-feature-tags-labels.ipynb    Build: tag, label, and type sparse matrices
│   ├── 02-feature-ratings.ipynb        Build: Bayesian-weighted rating matrices
│   ├── 03-feature-assembly.ipynb       Inspect: combined feature matrix
│   ├── 04-knn-training.ipynb           Train: KNN model → data/model/
│   └── 05-knn-query.ipynb              Prototype: interactive recommendation queries
├── 3-app/
│   └── app.py                          Streamlit app
├── data/
│   ├── mb_*.parquet                    Raw MusicBrainz exports (10 tables)
│   ├── features/                       Sparse feature matrices (.npz, .pkl)
│   ├── model/                          Trained model artefacts
│   └── pickles/                        Intermediate DataFrames
├── docs/                               Step-by-step pipeline documentation
└── requirements.txt
```

## Documentation

| Doc | Contents |
|-----|----------|
| [01-data-import.md](docs/01-data-import.md) | Parquet table schemas and import logic |
| [02-datasets.md](docs/02-datasets.md) | DataFrame construction and joins |
| [03-features.md](docs/03-features.md) | Feature engineering and Bayesian ratings |
| [04-model.md](docs/04-model.md) | KNN training pipeline |
| [05-app.md](docs/05-app.md) | Streamlit app walkthrough |
| [06-schema-diagrams.md](1-EDA/06-schema-diagrams.md) | Schema and data flow diagrams |
