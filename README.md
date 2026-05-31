# mixtape

Album recommendation engine built on the MusicBrainz database. Enter an artist you love, pick one of their albums, and get 10 similar albums recommended by a KNN model trained on community tags, ratings, and label data.

## How it works

1. **Data import** — a DuckDB notebook extracts artist/album data from a local MusicBrainz PostgreSQL instance and saves it as Parquet files.
2. **Datasets** — a second notebook loads the Parquet files into pandas DataFrames, enriches them with aggregated tags and ratings, and pickles the results.
3. **Features** — sparse feature matrices are built from tags, labels, types, and Bayesian-weighted ratings.
4. **Model** — a cosine-distance KNN model is trained on the L2-normalised feature matrix.
5. **App** — a Streamlit app serves recommendations in the browser.

See the [`docs/`](docs/) folder for detailed documentation on each step.

## Prerequisites

- Python 3.11+
- A local MusicBrainz PostgreSQL database running at `localhost:5432` (only needed to re-import data; the Parquet files and trained model are checked in)

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
streamlit run app/app.py
```

The app opens at **http://localhost:8501**.

No database connection is needed to run the app — the pre-built model and Parquet files in `data/` are all that's required.

## Re-building from scratch

If you want to re-import data or retrain the model, you'll need a MusicBrainz PostgreSQL database. Copy `.env.example` to `.env` and fill in your credentials, then run the notebooks in order:

```
datasets/duckdb-parquet.ipynb       → imports Parquet files from Postgres
datasets/parquet-dataframes.ipynb   → builds pickled DataFrames
features/weights-ratings.ipynb      → explores Bayesian rating weighting
features/features.ipynb             → builds sparse feature matrices
model/knn.ipynb                     → trains and saves the KNN model
```

## Project layout

```
mixtape/
├── app/
│   └── app.py                  Streamlit app
├── data/
│   ├── *.parquet               Raw MusicBrainz exports
│   ├── features/               Sparse feature matrices (.npz, .pkl)
│   ├── model/                  Trained model artefacts
│   └── pickles/                Intermediate DataFrames
├── datasets/
│   ├── duckdb-parquet.ipynb    Import: Postgres → Parquet
│   └── parquet-dataframes.ipynb  Build: Parquet → DataFrames
├── features/
│   ├── features.ipynb          Assemble feature matrices
│   ├── weights-ratings.ipynb   Rating weight exploration
│   └── weights-tags.ipynb      Tag weight exploration
├── model/
│   ├── knn.ipynb               Train KNN model
│   └── knn-query.ipynb         Query / evaluation notebook
├── EDA/                        Exploratory data analysis notebooks
├── docs/                       Step-by-step documentation
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
| [06-schema-diagrams.md](docs/06-schema-diagrams.md) | Mermaid schema and data flow diagrams |
