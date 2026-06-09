# merge-streamlit — bringing app_features app changes into feature_merge

## Context

`feature_merge` already contains the full `cleanup` branch (merged via PR #23). The app changes
to integrate come from commits made **on top of cleanup** that landed in `feature_merge` via the
`app_features` branch. Specifically, `feature_merge` is ahead of `cleanup` on two app files:

| File | Status |
|------|--------|
| `5-app/app_v3_weighted.py` | Modified — Last.fm popularity block + ratings/knob refactor |
| `5-app/app_v6.py` | New file — experimental multi-version on-the-fly cosine app |

The goal of this plan is to document what changed, verify the changes are stable, and confirm
nothing needs reconciling before `feature_merge` is itself merged forward.

---

## Changes in `app_v3_weighted.py`

This is the **current production app** (`streamlit run 5-app/app_v3_weighted.py`). The diff from
`cleanup` to `feature_merge` is ~47 lines across three logical groups:

### 1. Last.fm popularity block added (conditional on file existence)

```python
_LASTFM_FILE      = os.path.join(FEATURES_DIR, 'album_lastfm_popularity_matrix.npz')
_LASTFM_AVAILABLE = os.path.exists(_LASTFM_FILE)

BLOCK_FILES = {
    ...
    **({'popularity': 'album_lastfm_popularity_matrix.npz'} if _LASTFM_AVAILABLE else {}),
}
```

- The popularity block is **optional** — the app checks for the `.npz` at startup and gracefully
  degrades if it's missing (sidebar info message + fixed ratings fallback weight).
- Default dial: 4 (moderate — "noticeable but not dominant").
- **What it does in cosine scoring:** adds a 4-column (album_listeners, album_scrobbles,
  artist_listeners, artist_scrobbles) block to the weighted feature sum. Albums with no Last.fm
  data get a zero row and are silently unaffected.

### 2. Ratings knob removed; ratings weight synced to popularity dial

Before: ratings had its own knob at dial 6.
After: ratings is loaded as a feature block but **has no knob** — its weight is set in code to
match the popularity dial value.

```python
KNOB_BLOCKS = {k: v for k, v in BLOCK_FILES.items() if k != 'ratings'}
# ...
if _LASTFM_AVAILABLE:
    weights['ratings'] = weights['popularity']
else:
    weights['ratings'] = dial_to_weight(6)  # fixed fallback
```

**Why:** ratings and Last.fm popularity are complementary engagement signals — both measure how
much the listening public has interacted with a release. Tying them to the same dial lets the user
control "how much does popularity matter?" as a single concept without needing to balance two
separate knobs that mostly move together anyway.

**Consequence:** the knob panel now renders 5 knobs (genre, record label, track stats, country,
era) + 1 popularity knob (6 total) rather than 6 fixed knobs. The `KNOB_BLOCKS` dict drives
which knobs are shown; the `BLOCK_FILES` dict (which still includes ratings) drives which matrices
are loaded and scored.

### 3. Era matrix swapped from `album_era_matrix.npz` → `album_temporal_matrix.npz`

```python
'era': 'album_temporal_matrix.npz',   # was: 'album_era_matrix.npz'
```

The temporal matrix is the merged 11-column block (10 era one-hot + 1 continuous year) built by
`3-features/14-feature-temporal.ipynb`. The era-only matrix (`album_era_matrix.npz`) is now
superseded. The knob label stays "Era" — the user sees no change.

### 4. Minor: `combined_ssq` loop still iterates `BLOCK_FILES` (not `KNOB_BLOCKS`)

The loop that computes per-album query eligibility scores:
```python
for name in BLOCK_FILES:   # includes ratings
```
This is intentional — ratings contributes to the combined norm² even though it has no knob, so
albums with only a ratings signal remain eligible in the dropdown.

---

## Changes in `app_v6.py` (new file)

An experimental app that supports **three model versions side-by-side** (V3, V4, V5) with
on-the-fly weighted cosine scoring — no `.joblib` model files required.

Key architectural differences from `app_v3_weighted.py`:

| Aspect | `app_v3_weighted.py` | `app_v6.py` |
|--------|----------------------|-------------|
| Feature set | Genre + label + ratings + country + track stats + era + popularity | Tags + labels + types + ratings + country + track stats + role_family + instrument + contrib_cnt + year + tag_parent |
| Weights | User-controlled dials | Loaded from `data/best_weights.json` |
| Model versions | Single (v3) | V3 / V4 / V5 selectable |
| Matrix files | New unified matrices (`album_genre_matrix.npz`, `album_temporal_matrix.npz`) | Older per-feature matrices (`album_tags_matrix.npz`, `album_year_matrix.npz`) |
| UI | Knobs + faders | Experimental / incomplete |

`app_v6.py` references several matrices that may not exist in `feature_merge`
(`album_role_family_matrix.npz`, `album_instrument_matrix.npz`, `album_contributor_counts_matrix.npz`,
`album_year_matrix.npz`, `album_tag_parent_matrix.npz`). These come from experimental feature
notebooks (`09`, `11`, `12`) that are not yet integrated into the main pipeline. The file is
present as a prototype and is **not the app that runs by default**.

---

## Merge risk assessment

| Change | Risk | Notes |
|--------|------|-------|
| Popularity block (conditional) | Low | Degrades gracefully if `.npz` missing; existing behaviour unchanged when absent |
| Ratings knob → popularity sync | Low | Behaviour change is intentional and documented; no state-breaking |
| Era matrix swap | Low | `album_temporal_matrix.npz` is committed and tested |
| `app_v6.py` new file | Low | Not loaded by default; only relevant if matrices exist |
| Merge conflict risk | None | `cleanup` is already the merge base of `feature_merge`; these changes are already in `feature_merge` |

---

## Status

**These changes are already in `feature_merge`** — they arrived via the `app_features` branch
merge. This planning doc is a record of what changed and why, not a pre-merge checklist.

## What to verify before merging `feature_merge` forward (e.g. into `main`)

- [ ] `streamlit run 5-app/app_v3_weighted.py` starts cleanly with and without `album_lastfm_popularity_matrix.npz` present
- [ ] Popularity knob appears when the `.npz` exists; info message appears when it doesn't
- [ ] Era dial loads `album_temporal_matrix.npz` (11 columns) correctly — no shape errors
- [ ] Ratings weight tracks popularity dial correctly (set popularity to 0 → ratings weight = 0)
- [ ] `app_v6.py` is either removed, moved to `archive/`, or documented as requiring experimental matrices before `feature_merge` hits `main`

## Open question

`app_v6.py` uses an older set of matrix files that diverge from the current pipeline
(`album_tags_matrix.npz` vs `album_genre_matrix.npz`, `album_year_matrix.npz` vs
`album_temporal_matrix.npz`). Decision needed: **archive it, update it to the new matrix names,
or keep it as an explicit experimental prototype** with a README note. It should not be the
default entry point.
