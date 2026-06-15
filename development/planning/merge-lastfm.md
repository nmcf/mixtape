# Last.fm Popularity — Review & Merge Plan

## What the feature does

The Last.fm popularity feature adds a sixth weighted block to the KNN recommendation engine, capturing listener/scrobble counts as a behavioural popularity signal alongside the existing categorical and structural features (genre, ratings, record label, track stats, country).

The pipeline has three stages:

**1. Scrape** (`lastfm_scraper.ipynb`)  
Parallel web scraper (1–4 workers via manual `WORKER_ID` assignment). Each worker owns a slice of `mb_album_artists.parquet`, hits Last.fm's album pages, and appends deduplicated rows to `data/lastfm_data.parquet` using `filelock` for safe concurrent writes. Includes 3-attempt retry and a rolling dedup refresh every 500 rows. Output: 207,893 rows × 9 columns (Artist, Album, Artist_Listeners, Artist_Scrobbles, Album_Listeners, Album_Scrobbles, Similar_Artists, Artist_URL, Album_URL — all numeric columns stored as comma-formatted strings).

**2. Feature engineering** (`2-Prototyping/13-feature-lastfm-popularity.ipynb`)  
Cleans the raw parquet (strips commas, coerces N/A → 0), normalises artist/album names (lowercase + strip non-alphanumeric), deduplicates keeping highest-scrobbles per pair, then joins against `mb_album_artists.parquet` to obtain `album_id`. Applies min-max scaling to four numeric features (album_listeners, album_scrobbles, artist_listeners, artist_scrobbles) and builds a CSR sparse matrix aligned to the master `album_ids.pkl` index (1,758,488 rows × 4 cols). Saves to `data/features/album_lastfm_popularity_matrix.npz`. Hit rate: ~56% of albums matched (~985k non-zero rows).

**3. App integration** (`3-app/app_v3_weighted.py`)  
The app conditionally loads the popularity block at startup if the `.npz` exists (graceful degradation otherwise). A sixth rotary knob (default dial 4 → weight ≈ 0.73) exposes it alongside the other five blocks. It participates in the same weighted cosine distance formula as every other block — no special-casing at inference time.

---

## File inventory

| File | Location | Role |
|---|---|---|
| `lastfm_scraper.ipynb` | root | Parallel web scraper → `lastfm_data.parquet` |
| `13-feature-lastfm-popularity.ipynb` | `2-Prototyping/` | Feature engineering → `album_lastfm_popularity_matrix.npz` |
| `data/lastfm_data.parquet` | `data/` | Raw scraped data (207k rows) |
| `data/features/album_lastfm_popularity_matrix.npz` | `data/features/` | Sparse popularity matrix used by app |
| `3-app/app_v3_weighted.py` | `3-app/` | App — loads popularity block, exposes knob |

Supporting files the feature depends on but doesn't own:
- `data/mb_album_artists.parquet` — album universe (scraper source list; join target in feature notebook)
- `data/features/album_ids.pkl` — master row-order index shared by all feature matrices
- `2-Prototyping/queries/mb_album_compilation_flag_duckdb.sql` and `mb_album_live_flag_duckdb.sql` — came in the same commits but are for the Live/Compilation filters, not the popularity feature

---

## What's working well

- The scraper is parallel-safe and production-ready for a multi-window workflow. The `filelock` + rolling dedup design is solid.
- The feature engineering follows the exact same pattern as every other feature block (CSR sparse, aligned to `album_ids.pkl`, min-max scaled). It slots into the weighted cosine formula with zero friction.
- The conditional app load (show knob only if `.npz` exists) is the right design — it means the app stays usable on machines that haven't run the scraper.
- Default dial 4 (weight ≈ 0.73) is a reasonable starting point — visible but not dominant. Lower than core features (dial 6 / weight 1.09), higher than country (dial 2 / weight 0.36).

---

## Issues to resolve before merging

### Structural / placement issues

**Scraper is at the root** — `lastfm_scraper.ipynb` sits in the project root instead of where it belongs. The project has a clear `1-EDA` → `2-Prototyping` → `3-app` convention. The scraper is a data acquisition step that should live in a dedicated `0-Scraping/` or `data-collection/` folder, or at minimum alongside its downstream notebook in `2-Prototyping/`. The `lastfm_dataset/` folder already exists at the root (it holds the separate HetRec dataset), which makes two unrelated "lastfm" things at the root level — confusing.

**`test similar album listen.ipynb`** — this notebook (7,658 lines, the largest single file in the diff) is at the root with no clear name. It's presumably an ad-hoc experiment. Needs to either be cleaned up and moved to `2-Prototyping/` with a proper name, or deleted.

**Feature notebook numbering** — `13-feature-lastfm-popularity.ipynb` is correctly placed in `2-Prototyping/` and follows the numbering convention. No action needed there.

### Data quality issues

**~44% of albums unmatched.** The name-normalisation join (lowercase + strip non-alphanumeric) is fragile. Artists with non-ASCII names, "The X" vs "X" variants, or albums with subtitles after a colon will silently miss. The feature notebook shows sample unmatched rows in a debug cell — those should be inspected to see whether a second-pass fuzzy match (e.g. `rapidfuzz`) would recover a meaningful chunk before the matrix is considered final.

**Missing album stats (~8,300 rows) treated as 0.** Zero after min-max scaling is indistinguishable from "not in Last.fm at all". For albums where the artist is known but the album page returned no data, imputing from artist-level stats (artist_listeners / artist_scrobbles) would be more honest than a zero.

**No validation that the matrix row order still matches `album_ids.pkl`.** If the MB dataset is refreshed and `album_ids.pkl` is regenerated, the popularity matrix silently becomes misaligned. A fast sanity check at app startup (compare matrix `.shape[0]` to `len(album_ids)`) would catch this.

### Code / app issues

**Warning text in app doesn't mention popularity sparsity.** The warning shown when no albums are queryable under the current weights mentions "ratings and record label" as sparse features but not popularity (~56% coverage). Should include it so users understand why dialling up popularity alone may not yield results for niche albums.

**Knob default rationale is undocumented.** Dial 4 = weight 0.73 is written as a magic number. A short inline comment tying it to the v3 training weight scheme would help the next person who tunes defaults.

---

## Merge recommendations

### 1. Move the scraper into `2-Prototyping/`

Rename and move `lastfm_scraper.ipynb` → `2-Prototyping/00-lastfm-scraper.ipynb` (or prefix `13a` to sit next to the feature notebook). This keeps data acquisition close to the feature engineering step that consumes it, and clears the root of a misplaced notebook.

Alternative: create a `0-DataCollection/` folder if you anticipate adding more scrapers (e.g. Spotify, Discogs). Given there's only one scraper today, moving into `2-Prototyping/` is simpler.

### 2. Clean up or move `test similar album listen.ipynb`

Either rename it to something meaningful and move it to `2-Prototyping/` (e.g. `14-popularity-test-queries.ipynb`), or delete it if it's throwaway. At 7,600+ lines it's the largest file in the repo and is currently invisible to anyone reading the project structure.

### 3. Add a second-pass fuzzy match in `13-feature-lastfm-popularity.ipynb`

After the normalised-name join, run `rapidfuzz.process.extractOne` on the unmatched rows against the MB album list. A threshold of ~90 should recover a meaningful share of the unmatched 44% without introducing bad joins. Log the recovery rate and add it to the notebook's summary output.

### 4. Improve missing-album-stats imputation

For the ~8,300 rows where album stats are missing but artist stats exist, impute `album_listeners` and `album_scrobbles` from the artist-level values scaled by the median `album/artist` ratio across matched rows. This is preferable to a hard zero.

### 5. Add a startup alignment check in the app

In `app_v3_weighted.py`, after loading `album_lastfm_popularity_matrix.npz`, assert `matrix.shape[0] == len(album_ids)`. A mismatch means the matrix was built against a different version of `album_ids.pkl` — surfacing this as a clear error is far better than silent corruption in the recommendations.

### 6. Fix the sparsity warning text

In the app's "no queryable albums" warning, add popularity to the list of sparse features mentioned. One-line change.

### 7. Update `docs/03-features.md`

Add a section for the Last.fm popularity block documenting: what was scraped, the four features, the match rate, and the knob default. The existing docs describe every other feature block but have nothing on Last.fm yet.

---

## Suggested merge sequence

1. Clean up root (`test similar album listen.ipynb` — keep or delete, move scraper)
2. Feature notebook improvements (fuzzy match pass, imputation) — rebuild `.npz` after
3. App fixes (alignment check, warning text) — low risk, quick
4. Docs update
5. Merge to `main`

The popularity feature is functionally sound and already integrated. The merge is mostly housekeeping and data quality hardening, not architectural change.
