# Streamlit App

**Files:** `3-app/app.py` (v1), `3-app/app_v2.py` (v1 vs v2), `3-app/app_v3.py` (v1 vs v2 vs v3), `3-app/app_v3_weighted.py` (v3 with weight knobs + filters)

`app_v3_weighted.py` is the current active app.

## Running the app

```bash
source env/bin/activate
streamlit run 3-app/app_v3_weighted.py
```

The app opens at `http://localhost:8501` by default.

## App versions

| File | What it does | Loads |
|------|-------------|-------|
| `app.py` | v1 only, single model | `data/model/` joblib |
| `app_v2.py` | v1 vs v2 side-by-side | `data/model/`, `data/model_v2/` joblibs |
| `app_v3.py` | v1 vs v2 vs v3 side-by-side | all three joblibs |
| `app_v3_weighted.py` | **v3 features with runtime weight knobs + album filters (current)** | raw feature matrices + flag parquets — no trained model |

The comparison apps (`app_v2.py`, `app_v3.py`) load trained `.joblib` models, which are **not
committed** (gitignored) — retrain via the v2/v3 notebooks to use them. The current weighted app
needs only the committed feature matrices.

## Weighted app — `app_v3_weighted.py`

Instead of a pre-fitted KNN model, this app loads the five raw v3 feature blocks (genre,
record_label, ratings, country, track_stats) and precomputes each block's per-album
sum-of-squares once at startup. Sidebar **knobs** set a weight per block; per query it computes
weighted cosine directly:

```
numerator   = Σ_b w_b² · (X_b · q_b)
album norms = sqrt(Σ_b w_b² · ssq_b)
cosine      = numerator / (album_norms · query_norm)
```

No full-matrix rebuild or renormalisation per query (~60–180 ms over the 1.76M-album index).
The album dropdown is filtered to albums that have signal under the *current* weights, so it
never offers an album that would return no recommendations.

### Feature knobs

The sidebar header reads **"Tune your sound"**. Each feature block is a guitar-amp-style rotary
knob (custom component, `3-app/knob_component/index.html`) reading **0–11**, mapped to a block
weight by `dial_to_weight(d) = d/11·2.0` (0 → off, 11 → 2.0 max). Click a tick around the ring to
set a value. Defaults (dial units) are Country = 2 and the rest = 6 (mirroring the v3 training
weights where country is downweighted); a "Reset Defaults" button restores them via an `on_click`
callback. The active weights are echoed under the results as an **"EQ — …"** caption.

Results render as a three-column table — **Album · Artist · Match** — where Match is the weighted
cosine shown as a right-aligned percentage to one decimal (`st.column_config.NumberColumn`,
`format='%.1f%%'`, pinned narrow via an integer pixel `width`).

### Album filters

Two mixing-console-style **vertical faders** below the knobs (custom component,
`3-app/knob_component/switch.html`, placed side by side with `st.columns(2)`) filter results by
MusicBrainz release-group **secondary type** — an exact schema lookup, not an album-name guess.
Each fader has three detents with the option labels at top / middle / bottom; click a label or
anywhere along the track to slide the cap.

| Fader | Options | Keeps |
|-------|---------|-------|
| **Live Albums** | Live · Both · Studio | Live = secondary type Live (6); Studio = everything else |
| **Greatest Hits** | Collections · Both · Albums | Collections = secondary type Compilation (1); Albums = everything else |

Both default to **Both** and chain on both the artist-album dropdown and the recommendation
results, via the generic `filter_by_flag()` helper. The flags are pre-exported to
`data/mb_album_live_flag.parquet` and `data/mb_album_compilation_flag.parquet` (single `album_id`
column each) by the matching `2-Prototyping/queries/*_flag_duckdb.sql`, then loaded into sets by
`load_flag_ids()`. This replaced an earlier album-name keyword heuristic that mis-classified
titles with no "live" keyword (e.g. "Set List", date-format concert titles).

### Custom widget plumbing & state model

Both the knob panel and the fader switches are custom HTML/SVG components served from a small
background `HTTPServer` thread on port 8502 and registered with `declare_component(url=...)`
(Streamlit's built-in component file server failed in this environment). All outbound messages to
Streamlit must include `isStreamlitMessage: true`.

Each widget is the **single source of truth** for its own value — there is no `session_state`
mirror, so the knobs and the two faders move fully independently. Streamlit persists a keyed
component's last emitted value; the knob panel is re-seeded from that persisted value each rerun so
a silent iframe remount restores the user's dials rather than snapping to defaults. After first
render every iframe **ignores ordinary inbound renders** — only a change to the knob panel's
`reset_nonce` arg (flipped by the "Reset Defaults" button) makes it re-apply (using each knob's
`defaultValue`) and re-emit so the Python side stays in sync. The faders have no external reset, so
they ignore all inbound renders after init. This event-based scheme replaced an earlier 600 ms
time-window guard that caused cross-widget glitches and a stale-value "memory" bug.

**Various-Artists releases are excluded from recommendations.** ~1.5% of the index (VA samplers
and compilations that slipped past the import filter via the studio branch) have a null
`artist_name`; `recommend()` skips them, since a release with no single artist isn't actionable
here. Seeds are unaffected — the album dropdown is always built from a selected real artist.

## User flow

```mermaid
flowchart TD
    A[User types artist name] --> B{Artist found?}
    B -- No --> C[Show warning]
    B -- Yes --> D[Dropdown: select artist from matches]
    D --> E{Recommendable albums exist?}
    E -- No --> F[Show info message]
    E -- Yes --> G[Dropdown: select album]
    G --> H[KNN query across all loaded models]
    H --> I[Display results in side-by-side columns]
```

## Data loaded at startup

All resources are cached with `@st.cache_resource` and load once per server process:

| Resource | Source | Purpose |
|----------|--------|---------|
| v1 model + matrix | `data/model/` | Runs v1 recommendations |
| v2 model + matrix | `data/model_v2/` | Runs v2 recommendations |
| v3 model + matrix | `data/model_v3/` | Runs v3 recommendations |
| Lookup table | `data/mb_album_artists.parquet` | Maps album IDs to names and artist names |

The album dropdown is filtered to albums present in any model's index — albums with no features in any model are hidden.

## Highlight logic (`app_v3.py`)

Rows are highlighted amber when an album appears in **only that model's** results and not in either of the other two. Plain rows appear in at least one other model.

```python
def highlight_unique(df, other_ids):
    return [
        'background-color: #fff3cd; ...' if aid not in other_ids else ''
        for aid in df['album_id']
    ]
```

The summary line below the tables shows how many albums appear in all three, and the unique count per model.

## Key functions

### `search_artist(name, lookup)`
Case-insensitive partial string match on `artist_name`. Returns all matching rows from the lookup table.

### `recommend(album_id, n, model, X_knn_norm, album_ids_annotated, album_id_to_row, lookup)`
Runs a KNN query for the given album across one model, fetches `n * 5` candidates, then:
- Removes the seed album itself
- Removes other albums by the same primary artist

Returns a DataFrame with `Album`, `Artist`, and `album_id` columns, truncated to `n` rows. Returns `None` if the album has no features in this model.

### `render_model_col(label, recs, other_ids)`
Renders one column: applies the highlight style and calls `st.dataframe`. Shared across all three columns to keep rendering DRY.
