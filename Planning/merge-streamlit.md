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

### 1. Off / Low / Medium / High weight levels vs numeric dials (0–11)

The new `config.py` maps user choices to four fixed weights:

```python
WEIGHT_LEVELS = {'Off': 0.0, 'Low': 0.3, 'Medium': 1.0, 'High': 2.0}
```

`app_v3_weighted.py` uses a continuous 0–11 dial with:
```python
def dial_to_weight(d): return d / 11 * 2.0  # 0 → 0.0, 11 → 2.0
```

**The case against Off/Low/Medium/High:**
- Four discrete levels is a blunt instrument. A user who wants genre "a bit above medium" has no
  way to express that — they're forced to jump from 1.0 to 2.0, doubling the weight.
- The knob UI (0–11) was deliberately chosen to match the guitar-amp aesthetic and give a
  meaningful range. "11" as a concept (Spinal Tap) is part of the product personality. Replacing
  it with a dropdown loses both the precision and the character.
- The Low=0.3 value was not tuned — it is not the same as any of the training weights used in
  the v3 model. The dial defaults in `app_v3_weighted.py` (genre:6, country:2, era:4) were
  chosen to mirror the training weights. Discrete levels break that alignment.
- The knob widget already snaps to visible positions and has reset-to-default behaviour — it
  gives the same "quick preset feel" as Off/Low/Medium/High but with more resolution.

**What the discrete levels do better:**
- Simpler to understand for a first-time user — "High" is more intuitive than "dial 9".
- Easier to implement presets (just a dict of level strings, not floats).
- No ambiguity about what "3" vs "4" means.

**Recommendation:** keep the 0–11 knob with named snap points as labels (so the UI shows
"Medium" at 6, "High" at 9, etc.) rather than replacing numeric control with discrete levels.
The presets system from v7 is worth keeping — implement them as dial-value dicts rather than
level-string dicts.

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

### Step 3 — Restore 0–11 knob dials
Replace `LEVEL_OPTIONS / WEIGHT_LEVELS / DEFAULT_LEVELS` with numeric dial defaults
(matching the training weights). Update `controls.py` to pass dial integers, not level strings.
Presets should be dicts of dial values (0–11), not level strings.

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
- [ ] 0–11 dials restored in `controls.py` (not Off/Low/Med/High)
- [ ] Presets converted from level-strings to dial-value dicts
- [ ] `streamlit run 5-app/app.py` runs cleanly — both tabs functional
- [ ] Popularity knob appears when `.npz` present; graceful fallback when absent
- [ ] Auto-tune and presets work correctly with updated weight system
- [ ] ERA dial loads temporal matrix (11 cols) without shape errors
- [ ] README and REBUILDING.md entry point updated
- [ ] `app_v3_weighted.py` and `app_v6.py` moved to `archive/`
