# mixtape

Album recommendation engine built on the MusicBrainz database. Enter an artist you love, pick one of their albums, and get 10 similar albums recommended by a KNN model trained on community tags, ratings, label data, artist country, and track statistics.

Three model versions are available for side-by-side comparison in the app.

## How it works

1. **Data import** — DuckDB notebooks extract artist/album data from a local MusicBrainz PostgreSQL instance and save it as Parquet files.
2. **EDA** — notebooks explore the raw data at the album, artist, and joined dataset level.
3. **Features** — sparse feature matrices are built from genre tags, labels, ratings, artist country, and album track statistics.
4. **Model** — cosine-distance KNN models are trained on the L2-normalised feature matrix. Three versions exist, each adding more features.
5. **App** — a Streamlit app serves recommendations in the browser, with a comparison view across all three models.

See the [`docs/`](docs/) folder for detailed documentation on each step.

## Prerequisites

- Python 3.11+
- A local MusicBrainz PostgreSQL database (only needed to re-import data; Parquet files and trained models are included)

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
streamlit run 3-app/app_v3.py
```

The app opens at **http://localhost:8501**.

No database connection is needed — the pre-built models and Parquet files in `data/` are all that's required.

## Re-building from scratch

If you want to re-import data or retrain the models, you'll need a MusicBrainz PostgreSQL database. Copy `.env.example` to `.env` and fill in your credentials, then run the notebooks in order:

```
1-EDA/01-postgres-to-parquet.ipynb              → imports Parquet files from Postgres
1-EDA/02-parquet-to-dataframes.ipynb            → builds pickled DataFrames

2-Prototyping/01-feature-tags-labels.ipynb      → builds tag, label, and type sparse matrices
2-Prototyping/02-feature-ratings.ipynb          → builds Bayesian-weighted rating matrices
2-Prototyping/03-feature-assembly.ipynb         → inspects and validates the combined matrix
2-Prototyping/04-knn-training.ipynb             → trains v1 model → data/model/

2-Prototyping/06-impute-artist-country.ipynb    → builds artist country parquet (needs Postgres)
2-Prototyping/07-build-album-track-stats.ipynb  → builds album track stats parquet (needs Postgres)
2-Prototyping/08-feature-country.ipynb          → builds country feature matrix
2-Prototyping/09-feature-track-stats.ipynb      → builds track stats feature matrix
2-Prototyping/10-feature-genre-tags.ipynb       → builds combined genre tag matrix
2-Prototyping/11-knn-v2-training.ipynb          → trains v2 model → data/model_v2/
2-Prototyping/12-knn-v3-training.ipynb          → trains v3 model → data/model_v3/
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
│   ├── 04-knn-training.ipynb           Train: v1 KNN model → data/model/
│   ├── 05-knn-query.ipynb              Prototype: interactive recommendation queries
│   ├── 06-impute-artist-country.ipynb  Build: artist country parquet (needs Postgres)
│   ├── 07-build-album-track-stats.ipynb Build: album track stats parquet (needs Postgres)
│   ├── 08-feature-country.ipynb        Build: country feature matrix
│   ├── 09-feature-track-stats.ipynb    Build: track stats feature matrix
│   ├── 10-feature-genre-tags.ipynb     Build: combined genre tag matrix
│   ├── 11-knn-v2-training.ipynb        Train: v2 KNN model → data/model_v2/
│   ├── 12-knn-v3-training.ipynb        Train: v3 KNN model → data/model_v3/
│   ├── feature_charts/                 Saved feature diagnostic plots + regen script
│   └── queries/                        SQL queries for DuckDB feature extraction
├── 3-app/
│   ├── app.py                          Streamlit app (v1 only)
│   ├── app_v2.py                       Streamlit app (v1 vs v2 comparison)
│   └── app_v3.py                       Streamlit app (v1 vs v2 vs v3 comparison)
├── data/
│   ├── mb_*.parquet                    Raw MusicBrainz exports
│   ├── sql_feature_*.parquet           Country + track-stats feature exports
│   ├── features/                       Sparse feature matrices (.npz, .pkl)
│   ├── model/                          v1 model artefacts
│   ├── model_v2/                       v2 model artefacts
│   ├── model_v3/                       v3 model artefacts
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
| [08-howto-model-v2.md](docs/08-howto-model-v2.md) | How to run the v2/v3 model pipeline |
