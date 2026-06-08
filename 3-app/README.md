# Mixtape — Streamlit App

Interactive album recommender UI. Two modes:

- **Find Similar** — pick an artist → album → get content-based recommendations, with a live mixing board to weight features.
- **Explore** — pick genre tags (+ optional country / decade) to discover albums, then seed one into Find Similar.

## Run

```bash
cd 3-app
streamlit run app.py
```

Starts on `localhost:8505` (configured in `.streamlit/config.toml`).

## Controls

| Control | What it does |
|---|---|
| **Preset** dropdown | One-click weight profiles (Full Mix, Genre Purist, Local Sound, …) |
| **Pro Knobs** | Per-feature weights (Genre / Record Label / Ratings / Country / Track Stats), 0–11 |
| **Auto-Tune** | Refines weights using each album's signal strength × your current preset |
| **Content Filters** | *Live Albums* (Studio / Both / Live) and *Greatest Hits* (Albums / Both / Hits) — filter recommendations by release type |

## Architecture

| File | Role |
|---|---|
| `app.py` | Entry point, layout, two tabs, result rendering |
| `config.py` | Constants, presets, feature-block config, filter options |
| `style.py` | Dark / light themes + CSS |
| `engine.py` | Data loading, weighted-cosine recommendation, auto-tune, explore search, content filtering |
| `controls.py` | Sidebar — preset dropdown, auto-tune/reset, knob panel, content-filter faders |
| `fader_component/` | Custom vertical-fader HTML component (content filters) |
| `knob_component/` | Custom multi-knob panel HTML component (feature weights) |

## Required data

The app reads feature matrices and lookup tables from `../data/` (project root). Paths auto-resolve under `data/raw/` or `data/`.

**Find Similar needs:**
- `data/features/*.npz` — five sparse feature blocks (genre, record_label, ratings, country, track_stats)
- `data/features/album_ids.pkl` — album-id index
- `data/mb_album_artists.parquet` — album/artist name lookup

**Content filters need:**
- `data/raw/mb_album_secondary_type.parquet` — live/compilation flags
  (build with `notebooks/extract-secondary-type.ipynb`)

**Explore needs:**
- `data/raw/mb_tag.parquet`, `data/raw/mb_album_tag.parquet` (required)
- `data/raw/mb_area.parquet`, `data/mb_album_country.parquet`, `data/mb_album.parquet` (optional — enable country/decade filters)
  (build tag/area with `notebooks/extract-tag-area.ipynb`)

If a data file is missing, the relevant feature degrades gracefully (Explore shows a hint; content filters become no-ops) instead of crashing.
