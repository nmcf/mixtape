# feature-track-stats notebook planning

## Goal

Build track-level features for use in the recommendation model. Tracks are the atomic unit of a mixtape, so track-level statistics complement the existing album and artist features already engineered in `EDA-albums.ipynb` and `EDA-artists.ipynb`.

## Context

No track-level analysis exists yet. Current pipeline has:
- `mb_album.parquet` — album features (rating, year, tags, country, label)
- `mb_artist.parquet` — artist features (rating, year, type, area, tags)
- `master_df.pkl` — 157.9M row product of album × artist × tags

Track data lives in the MusicBrainz Postgres DB (`mb_pg`) across these tables:

| Table | Key columns |
|-------|-------------|
| `track` | id, recording, medium, position, number, name, artist_credit, length, is_data_track |
| `recording` | id, name, artist_credit, length, video |
| `recording_meta` | id, rating, rating_count |
| `recording_tag` | recording, tag, count |
| `recording_first_release_date` | recording, year, month, day |

## Candidate features

### From `track` + `recording`
- `track_length` — duration in seconds (length is stored in ms)
- `is_video` — boolean from `recording.video`
- `is_data_track` — boolean from `track.is_data_track`
- `track_position` — position within medium (early/late track on album)

### From `recording_meta`
- `recording_rating` — mean rating (0–100 scale, same as album/artist ratings)
- `recording_rating_count` — vote count (reliability weight)

### From `recording_tag`
- `recording_tag_count` — total tags applied to a recording
- Top-N tag distribution (same treatment as album/artist tags)

### From `recording_first_release_date`
- `first_release_year` — earliest year the recording appeared on any release

### Derived
- `appearances` — number of releases a recording appears on (via `track` table count)
- `artist_credit_matches_album` — boolean: does the track artist credit match the album's?

## Questions to answer in the notebook

1. How many unique recordings are there after filtering to our album population?
2. What is the distribution of track lengths — are there outliers (interludes, live recordings, bonus tracks)?
3. How sparse is `recording_meta` ratings vs album/artist ratings?
4. Are recording tags distinct from album tags or largely duplicated?
5. How many recordings appear on more than one release (re-releases, compilations)?

## Output

Parquet files mirroring the existing pattern:
- `data/mb_track.parquet` — one row per track, track-level features
- `data/mb_recording_tag.parquet` — recording × tag counts (same shape as `mb_album_tag.parquet`)

These feed into `parquet-dataframes.ipynb` to extend `master_df` with a track dimension.

## Dependencies

- Existing parquet pipeline in `duckdb-parquet.ipynb`
- `mb_pg` attached DuckDB connection (postgres scanner)
- Scoped to album population already in `mb_album.parquet` — no standalone track export
