# mixtape

Album recommendation engine built on the MusicBrainz database. Enter an artist you love, pick one of their albums, and get 10 similar albums recommended by a KNN model trained on community tags, ratings, label data, artist country, track statistics, release era, and Last.fm popularity.

Three model versions are available for side-by-side comparison; the current app applies feature weights in real time without a pre-fitted model.

## How it works

1. **Data import** — DuckDB notebooks extract artist/album data from a local MusicBrainz PostgreSQL instance and save it as Parquet files.
2. **EDA** — notebooks explore the raw data at the album, artist, and joined dataset level.
3. **Features** — sparse feature matrices are built from genre tags, labels, ratings, artist country, album track statistics, release era, and Last.fm listener/scrobble counts.
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
streamlit run 5-app/app_v3_weighted.py
```

The app opens at **http://localhost:8501**. Start typing an artist in the live search box to pick one, choose a starting album, and get recommendations from the v3 feature set. You can reweight features (genre, record label, country, track stats, era, and Last.fm popularity) in real time using guitar-amp-style **knobs** (0–11) in the sidebar. Ratings weight auto-syncs to the Popularity dial. Two mixing-console-style **vertical faders** — **Live Albums** (Live/Both/Studio) and **Greatest Hits** (Hits/Both/Albums) — narrow results by MusicBrainz release type.

No database connection is needed — the Parquet files and feature matrices in `data/` are all that's required. (The trained `.joblib` models used by the older comparison apps `app_v2.py`/`app_v3.py` are not committed; retrain them with the v2/v3 notebooks if you want those apps.)

## Re-building from scratch

See [REBUILDING.md](REBUILDING.md) for the full step-by-step pipeline.

## Project layout

```
mixtape/
├── 1-data/
│   ├── 01-postgres-to-parquet.ipynb         Import: Postgres → Parquet
│   ├── 02-parquet-to-dataframes.ipynb       Build: Parquet → pickled DataFrames (EDA only)
│   ├── 03-feature-country-import.ipynb      Import: artist country SQL → Parquet (needs Postgres)
│   ├── 04-feature-track-stats-import.ipynb  Import: track stats SQL → Parquet (needs Postgres)
│   ├── 05-lastfm-scraper.ipynb              Scrape: Last.fm listener/scrobble counts → data/lastfm_data.parquet
│   ├── queries/                             SQL queries for DuckDB Postgres extraction (incl. live/compilation flags)
│   ├── schema-diagrams.md                   Parquet table relationships and pipeline data flow
│   └── SchemaSpy/                           Auto-generated HTML reference for the MusicBrainz Postgres schema
├── 2-eda/
│   ├── 01-EDA-albums.ipynb                  Exploratory analysis: albums + key design decisions
│   ├── 02-EDA-artists.ipynb                 Exploratory analysis: artists + key design decisions
│   ├── 04-EDA-year.ipynb                    Exploratory analysis: year/era sources and coverage
│   └── 05-EDA-tags-labels.ipynb             Exploratory analysis: tag/label coverage + genre blend
├── 3-features/
│   ├── 01-album-artist-index.ipynb          Build: master album/artist ID index (run first)
│   ├── 02-feature-genre.ipynb               Build: album, artist, and blended genre tag matrices
│   ├── 03-feature-label.ipynb               Build: label, type, and record_label matrices
│   ├── 04-feature-ratings.ipynb             Build: Bayesian-weighted rating matrices
│   ├── 05-feature-country.ipynb             Build: country feature matrix
│   ├── 06-feature-track-stats.ipynb         Build: track stats feature matrix
│   ├── 08-feature-assembly.ipynb            Inspect: combined feature matrix
│   ├── 09–12-feature-*.ipynb                Experimental: contributors, tag hierarchy, tag parents
│   ├── 13-feature-lastfm-popularity.ipynb   Build: Last.fm popularity sparse matrix
│   ├── 14-feature-temporal.ipynb            Build: era parquet + era matrix + temporal matrix (era + year)
│   └── feature_charts/                      Saved feature diagnostic plots + regen script
├── 4-model/
│   ├── 01-knn-v1-training.ipynb             Train: v1 KNN model → data/model/
│   ├── 02-knn-query.ipynb                   Prototype: interactive recommendation queries
│   ├── 03-knn-v2-training.ipynb             Train: v2 KNN model → data/model_v2/
│   ├── 04-knn-v3-training.ipynb             Train: v3 KNN model → data/model_v3/
│   ├── 05-knn-v4-training.ipynb             Train: v4 KNN model (in progress)
│   ├── 06-evaluate-lastfm.ipynb             Evaluate: recommendation quality vs Last.fm listening data
│   └── tuning/                              Weight tuning experiments (v2/v3/v4)
├── 5-app/
│   ├── app.py                               Streamlit app (v1 only)
│   ├── app_v2.py                            Streamlit app (v1 vs v2 comparison)
│   ├── app_v3.py                            Streamlit app (v1 vs v2 vs v3 comparison)
│   ├── app_v3_weighted.py                   Streamlit app (v3 features, runtime knobs + filters) — current
│   ├── app_v6.py                            Streamlit app (experimental — on-the-fly cosine, v3/v4 features)
│   └── knob_component/                      Custom HTML/SVG sidebar widgets (rotary knobs + fader switches)
├── data/
│   ├── mb_*.parquet                         Raw MusicBrainz exports (committed)
│   ├── sql_feature_*.parquet                Country + track-stats feature exports (committed)
│   ├── features/                            Sparse feature matrices + index (.npz, .pkl) (committed)
│   ├── model/                               v1 model artefacts (gitignored)
│   ├── model_v2/                            v2 model artefacts (gitignored)
│   ├── model_v3/                            v3 model artefacts (gitignored)
│   └── pickles/                             Intermediate DataFrames (gitignored)
├── docs/                                    Step-by-step pipeline documentation
├── Planning/                                Planning and backlog documents
├── archive/                                 Retired notebooks, apps, and datasets
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
| [1-data/schema-diagrams.md](1-data/schema-diagrams.md) | Parquet table relationships and pipeline data flow |
