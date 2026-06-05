# Year / Era Feature — Planning

## Goal

Add an era-matching dimension to the recommendation engine. Instead of matching albums purely on audio-style features, also match on **temporal proximity** — albums from the same decade or era should score higher against each other. The era can be derived from either the album's release year or the artist's formation year (begin year), whichever is most complete and relevant.

---

## Schema Sources

### 1. `release_group_meta` (Postgres / MusicBrainz)
**The canonical source for album release year.**

| Column | Type | Notes |
|---|---|---|
| `first_release_date_year` | int2 | Year the release group first appeared anywhere |
| `first_release_date_month` | int2 | Often NULL |
| `first_release_date_day` | int2 | Often NULL |

- 4.28M rows — one per release group
- Most reliable for "when was this album first released"
- Already partially imported: `mb_album_country.parquet` carries `album_year` (from `release_country.date_year`)

### 2. `release_country` (Postgres / MusicBrainz)
**Per-country release dates — already partially imported.**

| Column | Type | Notes |
|---|---|---|
| `date_year` | int2 | Year released in a specific country |
| `date_month` | int2 | Often NULL |
| `date_day` | int2 | Often NULL |

- 13.1M rows — multiple rows per release (one per country)
- Already surfaced as `album_year` in `mb_album_country.parquet`
- Useful as a fallback when `release_group_meta` year is NULL

### 3. `release_first_release_date` (Postgres view)
**Aggregated earliest date per release across all countries.**

| Column | Type | Notes |
|---|---|---|
| `year` | int2 | Earliest known release year for that release |
| `month` | int2 | |
| `day` | int2 | |

- Derived view — 0 rows in SchemaSpy snapshot (view, populated at query time)
- More granular than `release_group_meta` (per-release not per-group)
- Could resolve cases where the group-level year is NULL

### 4. `artist` (Postgres / MusicBrainz)
**Band/artist formation year — useful as a fallback or secondary signal.**

| Column | Type | Notes |
|---|---|---|
| `begin_date_year` | int2 | Year band formed / artist born |
| `begin_date_month` | int2 | Often NULL |
| `begin_date_day` | int2 | Often NULL |
| `end_date_year` | int2 | Year band dissolved / artist died |

- Already imported as `artist_year` in `mb_artist.parquet`
- Coverage: 582,559 non-null out of 2.87M total artists (~20%)
- Useful when album-level year is missing — a band formed in 1968 is still "60s/70s" even if a release year is unknown

### 5. `artist_release_nonva` (Postgres view)
**Denormalized artist → release link with first_release_date.**

| Column | Type | Notes |
|---|---|---|
| `first_release_date` | int4 | Encoded integer date (YYYYMMDD style) |

- Could be useful for joining artist era to album era without a separate lookup
- View — check actual coverage before relying on it

---

## What We Already Have

| Field | Source file | Coverage notes |
|---|---|---|
| `album_year` | `mb_album_country.parquet` | Per country — take `MIN(album_year)` per album to get first release year |
| `artist_year` | `mb_artist.parquet` | ~20% of artists have this; present for most well-known artists |

---

## Options for the Era Feature

### Option A — Album release year from `mb_album_country` (no new import)
- Take `MIN(album_year)` per `album_id` from the existing `mb_album_country.parquet`
- Bin into decade: `FLOOR(year / 10) * 10` → 1970, 1980, 1990, etc.
- **Pros**: zero new data needed, fast to prototype
- **Cons**: `release_country` dates can vary by region; the minimum might be an obscure early release. Also misses albums with no country rows.

### Option B — Album release year from `release_group_meta` (new import)
- Import `first_release_date_year` from `release_group_meta` via the attached Postgres `mb_pg`
- Join through: `album → release → release_group → release_group_meta`
- **Pros**: semantically the cleanest — this is MusicBrainz's canonical "first release year for this work"
- **Cons**: requires a new parquet import and join chain

### Option C — Artist formation year as fallback / secondary signal
- Use `artist_year` from `mb_artist.parquet` (already imported) where album year is NULL
- Also use it as a secondary feature: an artist formed in 1965 releasing an album with no date is likely "60s/70s"
- **Pros**: no new import, adds signal for albums with missing dates
- **Cons**: formation year ≠ album year (a band from 1968 might release a comeback album in 2005)

### Option D — Combined: album year primary, artist year fallback
- Use Option B (or A) for album year; fall back to Option C when NULL
- Apply era binning only when year is known with reasonable confidence
- This is the recommended approach for the model feature

---

## Era Bins (Proposed)

| Era label | Years |
|---|---|
| Pre-War | before 1940 |
| 40s | 1940–1949 |
| 50s | 1950–1959 |
| 60s | 1960–1969 |
| 70s | 1970–1979 |
| 80s | 1980–1989 |
| 90s | 1990–1999 |
| 00s | 2000–2009 |
| 10s | 2010–2019 |
| 20s | 2020–present |
| Unknown | NULL year |

Simple formula: `era = FLOOR(year / 10) * 10` for decade bins, then label.

---

## Recommended Implementation Plan

1. **Prototype with existing data (Option A)**
   - Derive `album_first_year` as `MIN(album_year)` per album from `mb_album_country.parquet`
   - Add decade bin column
   - Measure NULL rate — if <20% missing, this may be sufficient

2. **Upgrade to release_group_meta (Option B) if coverage is poor**
   - Write a SQL query against `mb_pg` Postgres:
     ```sql
     SELECT rg.id AS release_group_id, rgm.first_release_date_year
     FROM release_group rg
     JOIN release_group_meta rgm ON rgm.id = rg.id
     WHERE rgm.first_release_date_year IS NOT NULL;
     ```
   - Import as `mb_album_release_year.parquet`
   - Join to existing album table via release → release_group

3. **Add `artist_year` as fallback** for albums with no release year
   - Already in `mb_artist.parquet` — no import needed

4. **Integrate into the feature vector**
   - Era similarity: same decade = 1.0, adjacent decade = 0.5, two+ decades apart = 0.0 (or a cosine over one-hot era vector)
   - Add as a weighted fader in the app (e.g. "Same Era" slider)
   - Default weight: moderate (era is a vibe signal, not the primary match criterion)

5. **App UI**
   - Display the album's era label in the results card
   - Add a "Same Era" weight knob alongside the existing EQ controls

---

## Open Questions

- Should era matching be **hard filter** (only show albums from same decade) or **soft weight** (nudge score up for same-era albums)? → Soft weight recommended to avoid overly narrow results.
- How to handle live albums / compilations that span multiple eras? → Use original studio album release year; already filtered by live/compilation flags.
- Should the artist's *active period* (begin → end year) be used instead of just begin year? → Worth exploring for bands with long careers (e.g. Rolling Stones active 1962–present spans many eras).
