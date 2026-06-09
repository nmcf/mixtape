# feature-country — notebook review

## What the feature is

A sparse one-hot country matrix: one row per album (aligned to `album_ids.pkl`), one column per
distinct MusicBrainz country area ID. Each album gets a `1.0` in the column corresponding to its
primary artist's country of origin, and `0.0` everywhere else.

**Final matrix (current run):** `(1,758,488 albums × 2,014 countries)`, 1,702,671 non-zeros —
**96.8% coverage**.

---

## How it was built

The pipeline runs across three notebooks:

### 1 — SQL import (`1-data/03-feature-country-import.ipynb`)

Runs `queries/mb_artist_country_fast_duckdb_release.sql` against the `mb_pg` Postgres snapshot.
The query is the most complex in the project — it runs in 10 stages and resolves a single
`country_id_imputed` per artist.

**Why the complexity:** 62.1% of MusicBrainz artists have `area_is_missing = True` — their
`artist.area` field is either NULL or points to a sub-national area that can't be resolved to a
country without walking the area containment graph. The SQL handles both problems.

**Stage breakdown:**

| Stage | What it does |
|-------|-------------|
| 0 | Snapshot 18 Postgres tables into DuckDB local storage; build indexes on all join keys |
| 1 | Pre-resolve `part of` link type IDs from the AR system |
| 2 | Walk the area containment graph up to 3 levels via "part of" ARs; materialise `t_area_country` mapping every area → ISO country code |
| 3 | Modal country per artist from `artist_release` materialised table (MB precomputed; no joins needed) |
| 4 | First + modal country per artist from `artist_release_group` materialised table |
| 5 | Modal country from `l_area_artist` inverse AR (area explicitly linked to artist) |
| 6 | Modal country from `l_artist_label` AR → `label.area` |
| 7 | Modal country from `l_artist_place` AR → `place.area` |
| 8 | Modal country from `release_country` → `release_event` (all local DuckDB tables after Stage 0) |
| 9 | First + modal country from `release_group` → `release` → `release_event` |
| Final | COALESCE the 10 signals in priority order; output `country_id_imputed` |

**COALESCE priority order (strongest → weakest):**

```
1. artist.area              (own area, ground truth)
2. artist.begin_area        (born/formed in)
3. artist_release mat       (precomputed by MB, no joins)
4. artist_release_group mat first release country
5. artist_release_group mat modal country
6. l_area_artist inverse AR
7. l_artist_label → label.area
8. l_artist_place → place.area
9. release_country modal
10. release_group first / modal country
```

Signals 3–10 only apply when `area_is_missing = True`. The final `country_id_imputed` is always
an integer `country_area_id` (the `area.id` of the ISO 3166-1 country entity), not an ISO string,
which keeps the feature matrix column type consistent.

**Output:** `data/sql_feature_artist_country_fast.parquet`

### 2 — Feature build (`3-features/05-feature-country.ipynb`)

```
sql_feature_artist_country_fast.parquet
    → prefer country_id_imputed over country_id (fills nulls)
    → join onto albums via mb_album_artists (drop_duplicates on album_id → primary artist only)
    → build CSR one-hot matrix aligned to album_ids.pkl
    → save: data/features/album_country_matrix.npz
```

**Key code decisions:**

- `country_df['country_final'] = country_df['country_id_imputed'].fillna(country_df['country_id'])` —
  takes the imputed value preferentially (it was derived from the richer signal stack). Falls back to
  the raw `country_id` only for artists whose area was already a country and needed no imputation.

- `album_artists.merge(...).drop_duplicates(subset='album_id')` — one country per album, taken from
  the first-matching artist in `mb_album_artists`. The ordering is whatever Postgres returned; in
  practice this is the primary artist credit.

- `pd.Categorical(album_country['country_final'])` — the category codes become column indices. This
  means column ordering is determined by the sorted unique country IDs in the current dataset, not a
  fixed global vocabulary. If a new country appears on a re-run the column layout shifts; the matrix
  must be rebuilt together with any model that uses it.

---

## Why it was designed this way

### Artist country, not release country

The feature captures *where the artist is from*, not *where the album was first pressed or
distributed*. A UK band releasing on a US label via a German distributor should match other UK bands.
Using release country would create false similarity between geographically unrelated artists who
happened to release in the same market.

The imputation waterfall still falls through to release-based signals (stages 3–10) when artist
area is unknown — but it treats these as weak proxies for artist origin, not as the thing being
measured.

### One-hot, not ordinal

Country is a nominal categorical. There is no natural ordering: France is not "between" Germany
and Spain in any sense that should affect cosine similarity. A one-hot encoding gives each country
equal standing in the feature space and lets the KNN model treat country co-occurrence as a binary
match/no-match signal.

### One country per album (primary artist only)

For albums with multiple contributing artists the join would otherwise produce multiple rows.
Taking only the primary artist keeps the matrix strictly one-hot (one non-zero per album row).
Allowing multiple countries would require weighted or multi-hot encoding and would conflate
collaboration albums with solo work from either artist's country.

### Area hierarchy walking (up to 3 levels)

MusicBrainz editors often enter a city or region rather than a country. Walking up the area
containment graph via "part of" ARs resolves these to their parent country. Three levels covers
the realistic depth: city → state/province → country. Without this step, a large fraction of
sub-national areas would produce orphan IDs that don't match any ISO country entry and would be
dropped from the matrix.

### No frequency threshold

Unlike genre tags, country columns are not pruned at a minimum occurrence count. Every country
that appears in the data gets a column, even if only one album holds that country. The rationale:
a rare country is not noise — it is a strong similarity signal for the handful of albums that share
it. An album from Iceland should match other Icelandic albums precisely *because* that's a rare
column.

The tradeoff is 2,014 columns with a very long tail (1,500 countries have fewer than 5 albums).
These sparse columns contribute almost nothing to most queries but are exactly what fires when two
genuinely obscure-origin albums are compared.

---

## How it impacts predictions

### Coverage and weight

96.8% of albums receive a country signal. The 3.2% with no country fall back entirely on genre,
era, ratings, label, and track-stats for similarity — they will never match on country grounds.

### Matching behaviour in KNN

The country matrix is one component of a weighted feature assembly (see `3-features/20-feature-assembly.ipynb`). Its practical effect in cosine similarity:

- **Strong within-country pull:** two albums from the same country share the single non-zero
  column and get a country cosine of 1.0 (before weighting). Albums from different countries
  get 0.0. Country is binary — there is no partial match.
- **Dominance risk in small-catalogue countries:** an album from a country with only 2 albums
  in the universe will almost always find the other album as its nearest neighbour on this
  dimension, regardless of genre or era. The assembly weight for the country matrix must be
  calibrated accordingly.
- **US/UK concentration:** the largest country column (US, ~434k albums) covers 24.7% of the
  universe. Two randomly selected albums have a ~6% chance of both being US-origin just by
  chance. This means the country signal is much weaker in practice for US/UK albums than for
  albums from smaller music markets — the feature differentiates less where it's needed most
  (distinguishing among the mass of US albums).

### Open questions for the EDA notebook

1. What is the actual country distribution? Top 20 countries by album count, and the long tail.
2. What fraction of "imputed" country assignments are likely wrong? (i.e. artists where the
   COALESCE fell all the way to stage 9/10 — release country as a proxy for artist origin)
3. Does the one-primary-artist-per-album rule lose meaningful signal for collaboration albums?
   How many albums in the universe have multi-nationality primary credits?
4. How does country interact with genre in the recommendation output — do US-country albums
   cluster by genre as expected, or does the country signal override genre for them?
5. Should small-country albums (< 10 in the universe) be treated differently — perhaps grouped
   into a regional bucket (e.g. "Nordic", "West Africa") rather than individual columns?

## Related files

| File | Role |
|------|------|
| `1-data/queries/mb_artist_country_fast_duckdb_release.sql` | 10-signal imputation SQL |
| `1-data/03-feature-country-import.ipynb` | Runs SQL, exports parquet |
| `3-features/05-feature-country.ipynb` | Builds CSR matrix |
| `data/sql_feature_artist_country_fast.parquet` | Per-artist country signal |
| `data/features/album_country_matrix.npz` | Final feature matrix |
| `data/mb_album_artists.parquet` | Album → artist bridge |
