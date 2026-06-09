# merge-streamlit — reconciling app_v3_weighted.py with the new modular app (v7)

## Status

`feature_merge` contains `app_v3_weighted.py` with the popularity block and temporal matrix
updates from `app_features`. `cleanup` has now been reconciled with `origin/cleanup`, which
introduced a **full modular refactor of the app** (v7) — splitting the monolithic
`app_v3_weighted.py` into `config.py`, `engine.py`, `controls.py`, `style.py`, `app.py`.

The two apps currently coexist on `cleanup`. The goal of this doc is to compare them, identify
what each does better, and define a merge plan for bringing the best of both into `feature_merge`.

---

## What changed in `app_v3_weighted.py` (app_features additions)

Three updates landed in `feature_merge` via `app_features` that are **not yet in the new modular
app**:

| Change | Detail |
|--------|--------|
| Last.fm popularity block | Conditional on `.npz` existence; graceful sidebar fallback if missing |
| Ratings synced to popularity dial | Ratings has no knob — its weight tracks the Popularity dial |
| Era matrix → temporal matrix | `album_era_matrix.npz` → `album_temporal_matrix.npz` (11 cols: era one-hot + continuous year) |

---

## What the new modular app (v7) adds

The remote `cleanup` branch introduced `5-app/app.py` and supporting modules. Key additions vs
`app_v3_weighted.py`:

### Architecture
The monolithic ~400-line file is split into four modules:

| File | Role |
|------|------|
| `config.py` | All feature block definitions, weight levels, presets, explore settings |
| `engine.py` | Recommendation logic, auto-tune, explore search, cosine scoring, per-block explanation |
| `controls.py` | Sidebar rendering: presets, auto-tune, knobs, faders |
| `style.py` | Light/dark theme CSS injection |

This is a meaningful improvement — each module has a clear single responsibility and can be
updated independently.

### Explore tab
A second tab — "Explore by Genre & Filters" — lets users discover albums by picking genre tags
directly (up to 10), optionally narrowing by country and release year range. Results can be
seeded directly into the Find Similar tab. This is new functionality not in `app_v3_weighted.py`.

### Auto-tune
A sidebar button that automatically sets feature weights based on the selected seed album's
signal profile — boosting blocks where the album has strong signal, muting blocks where it has
none. Not in `app_v3_weighted.py`.

### Presets
One-click weight profiles: "Full Mix", "Genre Purist", "Same Vibe / New Artist", "Local Sound",
"Critics' Pick". Not in `app_v3_weighted.py`.

### Theme toggle
Light/dark mode toggle in the header. Custom `DM Serif Display` / `DM Sans` / `DM Mono`
typography. Gold accent colour scheme (`#e8c84a`).

### Per-block similarity explanation
An expandable "Why these recommendations?" section showing top-3 contributing feature blocks
per result. `app_v3_weighted.py` had a simpler flat summary line.

### New fader component
`5-app/fader_component/index.html` — a new SVG-based vertical fader built alongside the
existing `knob_component`. The content filter faders (Live Albums / Greatest Hits) now use
this dedicated component.

---

## Design decisions to question

### 1. Off / Low / Medium / High weight levels — replaced with direct numeric weights

**Decision: drop discrete levels entirely. Use direct float weights, displayed via the 0–11 knob.**

The new `config.py` maps user choices to four fixed weights:
```python
WEIGHT_LEVELS = {'Off': 0.0, 'Low': 0.3, 'Medium': 1.0, 'High': 2.0}
```
This is being removed. Weights will be stored and applied as direct floats (e.g. `0.4`, `1.09`,
`2.0`) with no intermediate level abstraction.

**Why direct weights are better:**
- Presets loaded from training results (e.g. best-tuned weights from `best_weights.json`) will
  have values like `0.4`, `1.37`, `0.18` that do not map cleanly onto four fixed levels. Forcing
  them through a level lookup loses precision and breaks the link between what the model was
  trained on and what the app applies.
- Four levels is too coarse. The difference between Low=0.3 and Medium=1.0 is a 3× jump with
  no intermediate — a user or preset that wants `0.6` has nowhere to go.
- The knob UI (0–11) was deliberately chosen for the guitar-amp aesthetic and product
  personality. Replacing it with a dropdown label loses both.

**Knob ↔ weight mapping:**

The 0–11 dial maps linearly to `[0.0, 2.0]`:
```python
def dial_to_weight(d: int) -> float:
    return d / 11 * 2.0   # 0 → 0.0,  6 → ~1.09,  11 → 2.0
```

Presets store **exact float weights**, not dial positions. When a preset is applied, the dial
is set to the nearest integer position:
```python
def weight_to_dial(w: float) -> int:
    return round(w / 2.0 * 11)   # clamp to [0, 11]
```

This means the knob visually snaps to the closest position (e.g. weight `0.4` → dial `2`,
weight `1.37` → dial `8`) while the **backend uses the exact preset float for scoring**.
The slight rounding only affects the display — the cosine calculation always uses the
original precision value from the preset definition.

```python
# In config.py
PRESETS = {
    'Full Mix': {
        'genre': 1.09, 'record_label': 1.09, 'country': 0.36,
        'track_stats': 1.09, 'era': 0.73, 'popularity': 0.73,
    },
    'Genre Purist': {
        'genre': 2.0, 'record_label': 0.0, 'country': 0.0,
        'track_stats': 0.0, 'era': 0.0, 'popularity': 0.0,
    },
    # ...
}

# In controls.py — when applying a preset, set dial display only
def preset_dial(weight: float) -> int:
    return max(0, min(11, round(weight / 2.0 * 11)))
```

The session state holds two parallel values per block: the **exact weight** (float, used for
scoring) and the **dial position** (int, used for display). The knob component reads the dial
int; the engine reads the float.

### 2. Era still points to `album_era_matrix.npz` (not temporal)

`config.py` in the new modular app still loads the old era-only matrix:
```python
'era': 'album_era_matrix.npz',
```
This needs updating to `album_temporal_matrix.npz` before the new app is usable. The temporal
matrix is what the pipeline now produces — the era-only matrix is superseded.

### 3. Ratings has its own knob in the new app

`config.py` gives ratings a full knob at `Medium` default. `app_v3_weighted.py` removed the
ratings knob and synced ratings weight to the popularity dial. The new app has no popularity
block at all yet.

Decision needed: adopt the "ratings syncs to popularity" design from `app_v3_weighted.py`, or
restore a separate ratings knob alongside a popularity one.

**Recommendation:** keep the sync. It reduces cognitive load — popularity and ratings are both
engagement signals and should feel like one dial to the user. The new app should add the
popularity block and remove the standalone ratings knob as `app_v3_weighted.py` did.

### 4. `app_v3_weighted.py` is still the entry point in README/REBUILDING

The docs reference `streamlit run 5-app/app_v3_weighted.py`. If we merge the new modular app,
the entry point becomes `streamlit run 5-app/app.py`. This needs updating in:
- `README.md` (Quick start + layout section)
- `REBUILDING.md` (Step 11)

---

## Feature comparison

| Feature | `app_v3_weighted.py` | new `app.py` (v7) |
|---------|----------------------|-------------------|
| Find Similar tab | ✅ | ✅ |
| Explore tab | ✗ | ✅ |
| Auto-tune | ✗ | ✅ |
| Presets | ✗ | ✅ |
| 0–11 knob dials | ✅ | ✗ (Off/Low/Med/High) |
| Popularity block | ✅ | ✗ (not yet added) |
| Ratings synced to popularity | ✅ | ✗ (separate knob) |
| Temporal matrix (era + year) | ✅ | ✗ (era-only matrix) |
| Light/dark theme | ✗ | ✅ |
| Per-block explanation | Basic (caption line) | ✅ (expandable, per-result) |
| Modular code structure | ✗ (monolith) | ✅ |
| fader_component | ✅ | ✅ (new version) |
| Streamlit config.toml | ✗ | ✅ |

---

## Merge plan

The new modular structure is strictly better for maintainability. The goal is to bring
`feature_merge`'s feature additions into the modular app, not the other way around.

### Step 1 — Merge cleanup into feature_merge
Bring the modular app files (`app.py`, `config.py`, `engine.py`, `controls.py`, `style.py`,
`fader_component/`, `.streamlit/`) across.

### Step 2 — Update config.py
- Swap `album_era_matrix.npz` → `album_temporal_matrix.npz`
- Add popularity block (conditional on file existence, matching `app_v3_weighted.py` pattern)
- Remove ratings from `BLOCK_FILES` knob set; keep it loaded but weight-synced to popularity

### Step 3 — Replace discrete levels with direct float weights + dial display
- Remove `LEVEL_OPTIONS`, `WEIGHT_LEVELS`, `DEFAULT_LEVELS` from `config.py`
- `PRESETS` becomes a dict of `{block: float_weight}` — exact values, not level strings
- Add `dial_to_weight(d)` and `weight_to_dial(w)` helpers (linear mapping over `[0, 2.0]`)
- Session state stores two values per block: `wgt_{name}` (float, used by engine) and
  `dial_{name}` (int 0–11, used by knob display)
- When a preset is applied, exact weights go into `wgt_*` and rounded dial positions go into
  `dial_*` — the knob snaps to nearest integer but scoring uses the full precision float
- Default dials mirror the v3 training weights (genre: ~1.09 → dial 6, country: ~0.36 → dial 2, etc.)

### Step 4 — Update docs
- `README.md`: entry point → `streamlit run 5-app/app.py`
- `REBUILDING.md` Step 11: same
- `docs/05-app.md`: document Explore tab, auto-tune, presets, theme toggle

### Step 5 — Archive or remove `app_v3_weighted.py`
Once the modular app is verified working with all feature blocks, move
`app_v3_weighted.py` to `archive/`. `app_v6.py` should go there too (it references
experimental matrices that don't exist in the main pipeline).

---

## Checklist before merging to main

- [ ] `config.py` updated: temporal matrix, popularity block, no standalone ratings knob
- [ ] Discrete levels removed; `config.py` presets use direct float weights
- [ ] `dial_to_weight` / `weight_to_dial` helpers in place; session state holds both `wgt_*` and `dial_*` per block
- [ ] Knob displays rounded dial position; engine scores with exact float — verified they differ for at least one preset value (e.g. `0.4` → dial `2` → display only)
- [ ] `streamlit run 5-app/app.py` runs cleanly — both tabs functional
- [ ] Popularity knob appears when `.npz` present; graceful fallback when absent
- [ ] Auto-tune and presets work correctly with updated weight system
- [ ] ERA dial loads temporal matrix (11 cols) without shape errors
- [ ] README and REBUILDING.md entry point updated
- [ ] `app_v3_weighted.py` and `app_v6.py` moved to `archive/`

---

## Follow-up: Restore the reactive artist search (v3_weighted → modular app)

### What v3_weighted had (the good version)

The archived `app_v3_weighted.py` used a **live typeahead** via the `streamlit-searchbox`
package (`st_searchbox`). Suggestions appear and refine *as you type*, with no extra "submit"
or selectbox-of-all-matches step. Three pieces made it work:

```python
from streamlit_searchbox import st_searchbox

@st.cache_resource
def artist_index(_lookup):
    """Sorted unique artist names + precomputed lowercased column, so substring
    matching across ~566k artists is fast per keystroke."""
    names = pd.Series(sorted(_lookup['artist_name'].dropna().unique()))
    return pd.DataFrame({'name': names, 'lower': names.str.lower()})

def make_artist_search(lookup, limit=50):
    idx = artist_index(lookup)
    def _search(query):
        q = (query or '').strip().lower()
        if len(q) < 2:
            return []
        hits = idx[idx['lower'].str.contains(re.escape(q), na=False)]
        if hits.empty:
            return []
        is_prefix = hits['lower'].str.startswith(q)
        ordered = pd.concat([hits[is_prefix], hits[~is_prefix]])  # prefix hits first
        return ordered['name'].head(limit).tolist()
    return _search

selected_artist = st_searchbox(make_artist_search(lookup),
                               label="Set the Tone — Name an Artist",
                               placeholder="Start typing an artist…",
                               key="artist_search")
```

Key design properties:
- **`artist_index()`** is cached once: a sorted unique-name Series with a precomputed
  `lower` column so each keystroke does a vectorised `str.contains` over ~566k names
  (no per-call `.unique()` / `.sort()`).
- **`re.escape(q)`** so names with regex metacharacters (`+`, `(`, `*` — common in band
  names) don't break the match.
- **Prefix-first ordering**: exact prefix matches float to the top, substring matches follow.
- **`len(q) < 2` guard**: no suggestions until 2+ chars, avoiding a 566k-row scan on the
  first letter.
- Picking a suggestion goes **straight to the album dropdown** — one interaction, not three.

### What the new modular app currently has (the regression)

`app.py` replaced the typeahead with a plain `st.text_input` + `st.selectbox`-of-matches,
backed by `engine.search_artist()`:

```python
artist_query = st.text_input("Artist", placeholder="e.g. Radiohead, Eminem, Miles Davis…")
if artist_query:
    matches = search_artist(artist_query, lookup)          # substring over the FULL lookup
    ...
    selected_artist = st.selectbox("Pick the Artist", sorted(artists))
    ...
    selected_album_name = st.selectbox("Pick a Starting Album", ...)
```

Downsides vs v3_weighted:
1. **Not reactive** — the user types, then must tab/enter to commit, *then* pick from a
   second dropdown of all matching artists. Three interactions instead of one.
2. **`search_artist()` scans the full lookup** (`lookup['artist_name'].str.contains`) on
   every rerun — no cached lowercased index, no prefix ordering, no length guard.
3. No `re.escape` — a query like `Sigur Rós (` or `+44` can raise a regex error.

### Plan — port the reactive search into the modular structure

**Dependency:** `streamlit-searchbox` is NOT currently installed or in `requirements.txt`
(only the archived app imported it). Step 0 is to add it back.

#### Step 0 — Dependency
- Add `streamlit-searchbox` to `requirements.txt`.
- `pip install streamlit-searchbox` in the active env.

#### Step 1 — `engine.py`: add the cached index + search-callback factory
Move `artist_index()` and `make_artist_search()` out of the archived app into `engine.py`
(alongside the existing `search_artist`, which can stay as a fallback helper). Add
`import re` at the top.

```python
@st.cache_resource
def artist_index(_lookup):
    names = pd.Series(sorted(_lookup['artist_name'].dropna().unique()))
    return pd.DataFrame({'name': names, 'lower': names.str.lower()})

def make_artist_search(lookup, limit=50):
    idx = artist_index(lookup)
    def _search(query):
        q = (query or '').strip().lower()
        if len(q) < 2:
            return []
        hits = idx[idx['lower'].str.contains(re.escape(q), na=False)]
        if hits.empty:
            return []
        is_prefix = hits['lower'].str.startswith(q)
        return pd.concat([hits[is_prefix], hits[~is_prefix]])['name'].head(limit).tolist()
    return _search
```

#### Step 2 — `app.py`: swap the text_input + selectbox for `st_searchbox`
In the **Find Similar** tab, replace the `artist_query` text_input / `search_artist` /
`st.selectbox("Pick the Artist")` block with:

```python
from streamlit_searchbox import st_searchbox
from engine import make_artist_search   # add to existing engine import

selected_artist = st_searchbox(
    make_artist_search(lookup),
    label="Artist",
    placeholder="Start typing an artist…",
    key="artist_search",
)
if selected_artist:
    artist_albums = lookup[lookup['artist_name'] == selected_artist]
    album_options = {row['album_name']: aid
                     for aid, row in artist_albums.iterrows()
                     if is_queryable(aid)}
    if not album_options:
        st.info("No recommendable albums under current weights. Raise more channels.")
    else:
        selected_album_name = st.selectbox("Pick a Starting Album",
                                            sorted(album_options.keys()))
        if selected_album_name:
            album_id = album_options[selected_album_name]
            st.session_state['seed_album_id'] = album_id
```

Notes for the port:
- Keep the existing **explore-seed branch** untouched — `st_searchbox` only replaces the
  manual-search path (the `else:` branch of `if explore_seed:`).
- `is_queryable()` already exists in `app.py` and works unchanged — it gates the album
  dropdown to albums with signal under the current weights.
- The downstream Album Card + recommendation rendering already keys off
  `st.session_state['seed_album_id']`, so nothing below changes.

#### Step 3 — Cleanup
- `engine.search_artist()` can be **kept as a fallback** (cheap, no harm) or removed if
  nothing else references it. Grep before deleting.
- Confirm no other module imports `search_artist` from `engine`.

#### Step 4 — Verify
- [ ] `streamlit-searchbox` in `requirements.txt` and installed
- [ ] Typing 2+ chars shows live suggestions, prefix matches first
- [ ] Band names with regex metacharacters (`+44`, `!!!`, `Sigur Rós (`) don't error
- [ ] Picking an artist immediately shows the album dropdown (single interaction)
- [ ] Explore-seed flow still works and is visually distinct from the search flow
- [ ] No full-lookup scan per keystroke (index is cached via `@st.cache_resource`)
