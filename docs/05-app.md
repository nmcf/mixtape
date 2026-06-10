# Streamlit App

**Entry point:** `5-app/app.py`

**Architecture:** modular — `config.py`, `engine.py`, `controls.py`, `style.py`, `app.py`

Older monolithic app files (`app_v3_weighted.py`, `app_v6.py`) have been archived to `5-app/archive/`.

## Running the app

```bash
source env/bin/activate
streamlit run 5-app/app.py
```

The app opens at `http://localhost:8505` (port set in `5-app/.streamlit/config.toml`).

## Module overview

| File | Role |
|------|------|
| `config.py` | All constants, BLOCK_FILES, KNOB_BLOCKS, PRESETS, DEFAULT_WEIGHTS, `dial_to_weight`, `weight_to_dial` |
| `engine.py` | Data loading (cached), weighted cosine, auto-tune profiling, Explore search |
| `controls.py` | Sidebar UI — preset dropdown, knob panel, auto-tune buttons, content filter faders |
| `style.py` | Theme (light/dark) and CSS injection |
| `app.py` | Page config, header, tab layout, result rendering |

## How the app works

Instead of a pre-fitted KNN model, the app loads raw sparse feature matrices and computes weighted cosine similarity at query time:

```
numerator   = Σ_b w_b² · (X_b · q_b)
album norms = sqrt(Σ_b w_b² · ssq_b)
cosine      = numerator / (album_norms · query_norm)
```

~60–180 ms over the ~1.76M-album index. No full-matrix rebuild or renormalisation per query.

## Weight system — float weights + dial display

Weights are stored as **exact floats** (0.0–2.0). The guitar-amp dial (0–11) is a display-only
representation derived by rounding. This means:

- **Presets** store exact float weights (e.g. `genre: 1.09`) that mirror the v3 training weights.
- **Dial display** is computed on-the-fly: `weight_to_dial(w) = round(w / 2.0 * 11)`.
- **Scoring** always uses the exact float, not the rounded dial value.
- When a user turns a knob, the exact weight is computed: `dial_to_weight(d) = round(d/11 * 2.0, 4)`.

Session state holds two values per block: `wgt_{name}` (float, used by engine) and `dial_{name}`
(int 0–11, used by knob display). When a preset is applied, exact weights go into `wgt_*` and
rounded dial positions go into `dial_*` — the knob snaps to nearest integer but scoring uses
full-precision floats.

### Feature knobs

The sidebar has one rotary knob per visible block: Genre, Record Label, Country, Track Stats, Era,
and optionally Popularity (if `album_lastfm_popularity_matrix.npz` exists). The knob reads 0–11.

**Ratings has no knob.** Ratings weight auto-syncs to the Popularity dial — both are engagement
signals. When popularity is unavailable, ratings defaults to `dial_to_weight(6) ≈ 1.09`.

### Presets

One-click weight profiles stored as exact floats in `PRESETS` in `config.py`:

| Preset | Description |
|--------|-------------|
| Full Mix | Balanced blend of all features — the default starting point |
| Genre Purist | Match by musical style only |
| Same Vibe, New Artist | Similar sound + era, different artists |
| Local Sound | Prioritise country-of-origin match |
| Critics' Pick | Favour popularity / critical reception |

### Auto-Tune

Clicking **✦ Auto-Tune** calls `auto_tune_profile()` (per-block cosine signal strength profiling on
the seed album, normalised 0–1), then `smart_auto_tune()` which combines signal strength with the
user's current float weights and returns a new float weight dict. Weights are applied via the same
`_apply_weights()` path as presets — exact floats into `wgt_*`, rounded dials into `dial_*`.

## Tabs

### Find Similar

1. Type an artist name → artist dropdown → album dropdown (filtered to albums with signal under current weights).
2. Recommendations rendered as a styled three-column table: `#` · Album/Artist · Similarity score + bar.
3. Expandable **"Why these recommendations?"** section shows per-block cosine breakdown for each result.

The active weight mix is echoed in the subtitle as `MIX › Genre 1.09  ·  Era 0.73  ·  …`.

### Explore

Discover albums by genre tag rather than by artist. Controls:

- **Genre/tag multiselect** — top 100 tags by MusicBrainz ref_count.
- **Country filter** — top 40 countries by album count.
- **Year range slider** — 1920–2026.

Scoring: `relevance = matched_tag_count / total_album_tag_count` — prevents mega-popular
"tagged with everything" albums from dominating. At most 2 albums per artist shown.

Clicking a result seeds it into the Find Similar tab for cosine recommendations.

## Content filters

Two mixing-console-style **vertical faders** (custom component, `5-app/fader_component/`) below
the knobs filter results by MusicBrainz release-group **secondary type**.

| Fader | Options | Keeps |
|-------|---------|-------|
| **Live Albums** | STUDIO / BOTH / LIVE | STUDIO = exclude live releases; LIVE = live only |
| **Greatest Hits** | ALBUMS / BOTH / HITS | ALBUMS = exclude compilations; HITS = compilations only |

Both default to the exclude-unwanted position (STUDIO / ALBUMS).

## Data loaded at startup

All resources cached with `@st.cache_resource`:

| Resource | Source | Purpose |
|----------|--------|---------|
| genre matrix | `data/features/album_genre_matrix.npz` | Genre feature block |
| record_label matrix | `data/features/album_record_label_matrix.npz` | Label feature block |
| ratings matrix | `data/features/album_ratings_matrix.npz` | Ratings (synced to popularity) |
| country matrix | `data/features/album_country_matrix.npz` | Country feature block |
| track_stats matrix | `data/features/album_track_stats_matrix.npz` | Track stats feature block |
| era matrix | `data/features/album_temporal_matrix.npz` | 11-col: 10 era one-hot bins + continuous year |
| popularity matrix | `data/features/album_lastfm_popularity_matrix.npz` | Optional — Last.fm data |
| album index | `data/features/album_ids.pkl` | Master row index |
| lookup table | `data/mb_album_artists.parquet` | album_id → name + artist_name |
| secondary types | `data/raw/mb_album_secondary_type.parquet` | Live / compilation flags |

Paths auto-resolve under `data/raw/` then `data/` via `engine._find_parquet()`.

## Required data files & how to build them

The committed feature matrices in `data/features/` are enough to run **Find Similar**. The two
extra tabs/filters need a few raw extracts:

| Feature | Files | Build with |
|---------|-------|-----------|
| **Find Similar** | `data/features/*.npz` (genre, record_label, ratings, country, track_stats, era/temporal, popularity), `data/features/album_ids.pkl`, `data/mb_album_artists.parquet` | `3-features/*` notebooks |
| **Content filters** | `data/raw/mb_album_secondary_type.parquet` | `1-data/06-extract-secondary-type.ipynb` |
| **Explore** (required) | `data/raw/mb_tag.parquet` (tag vocabulary) + `data/mb_album_tag.parquet` | `1-data/07-extract-tag-area.ipynb` |
| **Explore** (optional country/decade filters) | `data/raw/mb_area.parquet`, `data/mb_album_country.parquet`, `data/mb_release_year.parquet` | `1-data/07-extract-tag-area.ipynb` |

If a file is missing the feature **degrades gracefully** — Explore shows a hint, the Popularity
knob disappears, content filters become no-ops — rather than crashing.

## Theme

Light/dark toggle in the top-right corner. `style.py` generates a CSS variable set and injects it
via `st.markdown`. All custom HTML/SVG components reference the same CSS variables for consistent
theming across native Streamlit widgets and custom components.
