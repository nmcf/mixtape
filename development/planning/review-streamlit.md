# Review — `5-app/` Streamlit application

Date: 2026-06-10 · Branch: `feature_merge`

Scope: a full read-through of the modular app (`config.py`, `engine.py`, `controls.py`,
`style.py`, `app.py`), the two custom HTML components, supporting files, and the Explore-tab
runtime error the user is hitting. Recommendations are split into **bugs to fix**, **cleanup /
removal**, and **merge / consolidation** opportunities.

---

## 1. The Explore-tab error — root cause & fix ✅ FIXED

**Symptom**
```
Explore requires raw parquet files (mb_tag.parquet, mb_album_tag.parquet)
in data/raw/ or data/. Run duckdb-parquet.ipynb first.
```

**Root cause (corrected)**
The error message implied the data didn't exist. It did — it was just **in the wrong folder.**
`engine._find_parquet()` resolves only `data/raw/` then `data/` (relative to the project root).
The required files were sitting under a **separate, stray `notebooks/data/raw/` folder**:

| File | Contains | Was at | App looked in |
|------|----------|--------|---------------|
| `mb_album_tag.parquet` | album_id → tag_id → count (2.39M rows) | ✅ `data/` | ✅ found |
| `mb_tag.parquet` | tag_id → **name** → ref_count (vocabulary) | ❌ `notebooks/data/raw/` | `data/raw/` — not found |
| `mb_area.parquet` | area_id → name (country names) | ❌ `notebooks/data/raw/` | `data/raw/` — not found |
| `mb_album_secondary_type.parquet` | live/compilation flags | ❌ `notebooks/data/raw/` | `data/raw/` — not found |

`mb_album_tag` only stores numeric `tag_id`s; the human-readable names live in `mb_tag.parquet`
(see `01-postgres-to-parquet.ipynb` line 222: *"the human-readable tag name is resolved in a later
notebook"*). With `mb_tag.parquet` unreachable, `tag_options` came back `None` and the tab
short-circuited to the hint.

**Fix applied — folder consolidation (see §1a).** Moving the three parquets into the project
`data/raw/` immediately re-enabled Explore (100 tags, 37 countries) and the content filters
(152k live, 481k compilation albums). The stale error message was also corrected to name the real
notebook (`1-data/07-extract-tag-area.ipynb`).

---

## 1a. Consolidation performed — `notebooks/` → `1-data/`, one data folder

There was a duplicate, stray structure parallel to the real pipeline:

```
notebooks/
├── extract-secondary-type.ipynb     # DuckDB→parquet import
├── extract-tag-area.ipynb           # DuckDB→parquet import
└── data/raw/                        # ← second data root, app never looked here
    ├── mb_tag.parquet
    ├── mb_area.parquet
    └── mb_album_secondary_type.parquet
```

These are import notebooks (same role as `1-data/01-05`) and their outputs belong in the single
project `data/` tree. Consolidation done:

1. **Parquets → `data/raw/`** — moved `mb_tag.parquet`, `mb_area.parquet`,
   `mb_album_secondary_type.parquet` into the project `data/raw/` (where `_find_parquet` looks).
   They are committable (not gitignored), matching the repo's "parquets are committed" convention
   (17 already tracked in `data/`).
2. **Notebooks → `1-data/`** — moved and renumbered to follow the existing 01–05 sequence:
   - `extract-secondary-type.ipynb` → `1-data/06-extract-secondary-type.ipynb`
   - `extract-tag-area.ipynb`       → `1-data/07-extract-tag-area.ipynb`
3. **Output paths fixed** — both wrote `./data/raw/…` (relative to `notebooks/`); rewritten to
   `../data/raw/…` so they now match the sibling import notebooks (which write `../data/…`).
4. **`notebooks/` directory removed** — empty after the move.
5. **References updated** — `5-app/README.md` and the Explore error string now point at the
   `1-data/06`/`07` notebooks.

**Follow-up consistency note (not blocking):** the moved notebooks attach Postgres with
`duckdb.connect()` (ephemeral) + `ATTACH … AS mb`, whereas `1-data/01` uses a persistent
`../musicbrainz.duckdb` + `AS mb_pg` and reads credentials from `.env`. They work as-is, but
aligning the connection idiom (and pulling creds from `.env`) would make the import folder uniform.

---

## 2. Bugs & correctness issues

### 2a. Year filter silently never worked ✅ FIXED
`load_explore_data()` read album year from `mb_album.parquet`:
```python
album_meta_df = pd.read_parquet(album_path, columns=['id', 'name', 'begin_date_year'])
```
But `mb_album.parquet` has **only** `['id', 'name', 'artist_credit']` — there is no
`begin_date_year` column. The read raised, the bare `except Exception: album_meta_df = None`
swallowed it, and the **Release Year slider was built but filtered nothing** (and the year column
in results was always blank).

**Fixed:** `album_meta_df` now loads `['album_id','album_year']` from `mb_album_country.parquet`
(1.57M rows after dropna/dedup), falling back to `mb_release_year.parquet`
(`release_group_meta_year` → `album_year`) if country data is absent. The year filter and the
"Year" column in Explore results now function.

> Data-quality aside: the loaded year range is 1884–2205 — there are clearly dirty future years in
> the source. Not an app bug, but the slider is capped at 2026 so out-of-range rows are simply
> excluded. Worth a cleanup pass in the import layer eventually.

### 2b. Over-broad `except Exception` hides schema drift
The two `try/except Exception: … = None` blocks in `load_explore_data` mask exactly the kind of
schema mismatch in 2a. At minimum log a warning, or narrow the except, so a broken column read is
visible rather than degrading to "feature absent" silently.

### 2c. `_find_parquet` resolves `data/` but notebooks write to `data/raw/`
Not a bug per se, but worth noting: content-filter and explore parquets are written to `data/raw/`
by the extract notebooks, while most committed parquets live in `data/`. `_find_parquet` handles
both, but the split is easy to trip over. Pick one convention (suggest committing the small
vocab/area files into `data/` alongside the rest) and document it.

---

## 3. Cleanup / removal candidates

### 3a. Orphan component file — `knob_component/switch.html`
The faders are served from `fader_component/index.html` (`controls._declare_fader`). The old
`knob_component/switch.html` is **referenced nowhere** in the modular app — it's a leftover from
`app_v3_weighted.py`, which served the fader out of the knob component folder. Safe to delete.

### 3b. Unused imports
| File | Unused | Note |
|------|--------|------|
| `controls.py` | `BLOCK_FILES`, `BLOCK_BANDS`, `PRESET_DESCRIPTIONS` | imported, never referenced in code |
| `app.py` | `EXPLORE_TOP_N_TAGS` | only used in `engine.py` |

### 3c. Dead config — `BLOCK_BANDS`
`config.BLOCK_BANDS` (the "88.1 / 94.7 / …" radio-dial frequency labels) is defined but **never
read anywhere**. Either wire it into the knob component as a cosmetic label or delete it.

### 3d. Unused config — `PRESET_DESCRIPTIONS`
Defined and imported into `controls.py` but never rendered. This is actually a **missed UX
opportunity** rather than pure dead code: showing the description as caption/help text under the
preset dropdown would be a nice touch. Either use it (preferred) or drop it.

### 3e. `engine.search_artist()` — fallback only
Kept intentionally as a non-reactive fallback after the `st_searchbox` port, but **nothing calls
it** now. Acceptable to keep as a documented helper; flag for removal if no fallback path
materialises.

---

## 4. Merge / consolidation opportunities

### 4a. Session-state init is split across two files
`app.py` does `st.session_state.setdefault('knob_nonce', 0)` and `style.get_theme()` seeds
`'dark'`, while `controls._init_state()` seeds `wgt_*` / `dial_*` / `knob_nonce` / filters.
`knob_nonce` is initialised in **both** places. Consolidate all session-state seeding into a single
`_init_state()` (in controls or a small `state.py`) called once at startup, so there's one source
of truth.

### 4b. `weighted_cosine` and `_block_cosine` share math
`engine.weighted_cosine` (all blocks, weighted) and `engine._block_cosine` (single block, for
auto-tune) and `per_block_similarity` (pairwise, for the "why" expander) all implement variants of
the same cosine. Not urgent, but a single private `_cosine(row, X, ssq)` helper would DRY the three
and reduce the chance of them drifting.

### 4c. Knob/fader components — shared plumbing
`fader_component/index.html` and `knob_component/index.html` are each standalone HTML with
duplicated Streamlit-message boilerplate (`isStreamlitMessage: true`, resize handling, theme CSS
vars). If these get further work, factor the shared JS handshake into one snippet. Low priority —
they're stable.

### 4d. `style.py` theme dicts vs `.streamlit/config.toml`
The dark palette is defined **twice**: once in `style.DARK` (used for the custom CSS/components) and
again in `.streamlit/config.toml` (`[theme]`, used by native widgets). They're consistent today
(`#171b23`, `#e8c84a`, …) but will drift. Consider generating one from the other, or at least a
comment cross-linking them.

---

## 5. Documentation drift — `5-app/README.md`

The in-folder README is stale and contradicts the actual app:
- **Run instructions say `cd 3-app`** — the folder is `5-app/`.
- Controls table lists **"Pro Knobs … (Genre / Record Label / Ratings / Country / Track Stats)"** —
  but Ratings has **no knob** now (synced to Popularity), Era and Popularity knobs are missing from
  the list, and weights are floats not the old levels.
- Doesn't mention the float-weight system, `dial_to_weight`/`weight_to_dial`, or the reactive
  `st_searchbox` artist search.

Recommend rewriting it to match `docs/05-app.md` (which is current), or replacing its body with a
pointer to `docs/05-app.md` to avoid maintaining two copies.

---

## 6. What's good (keep as-is)

- Clean module separation (`config` constants / `engine` data+math / `controls` UI / `style` theme
  / `app` layout) — the split is sensible and worth preserving.
- The float-weight model with display-only dial rounding is correctly implemented and isolated in
  `config.py`.
- Graceful degradation pattern (popularity knob, content filters) is solid — missing files disable
  features instead of crashing. The Explore tab follows the same pattern; the only problem is the
  *required* vocabulary file genuinely isn't there.
- `@st.cache_resource` on all loaders and the artist index keeps reruns cheap.
- Weighted-cosine query path is efficient (precomputed per-block sum-of-squares, no per-query
  renormalisation).

---

## 7. Action order — status

1. ✅ **Consolidated `notebooks/` → `1-data/` and the stray data folder → `data/raw/`** (§1a) —
   this re-enabled Explore + content filters.
2. ✅ **Fixed the stale Explore error message** — now names `1-data/07-extract-tag-area.ipynb`.
3. ✅ **Fixed the year-source bug (2a)** — year now loads from `mb_album_country.parquet`.
4. ✅ **Refreshed `5-app/README.md`** data section to point at the renumbered notebooks.
5. ⬜ **Delete orphans** — `knob_component/switch.html`, unused imports, decide on `BLOCK_BANDS`.
6. ⬜ *(Optional)* consolidate session-state init (4a) and wire up `PRESET_DESCRIPTIONS` (3d).
7. ⬜ *(Optional)* align the `1-data/06`/`07` Postgres connection idiom with `01` (§1a follow-up).
