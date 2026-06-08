-- ============================================================
--  MusicBrainz – album_stats table  (DuckDB-native, fast)
--  Compatible with DuckDB >= 0.9 + postgres_scanner extension
--
--  Fast concepts applied:
--   • Column projection at snapshot time
--   • Row filtering at snapshot time via JOIN (not IN subqueries)
--   • postgres_query() for large tables (avoids ctid crash)
--   • Every filter uses JOIN chains so Postgres uses hash joins
--   • Indexes on every join key immediately after snapshot
--   • Each intermediate result materialised as TABLE
--   • Forward join direction: narrow → wide
--   • Aggregate before joining back to the wide table
-- ============================================================


-- ============================================================
--  STAGE 0: snapshot — filtered via JOINs, not IN subqueries
-- ============================================================

-- Albums only: small table, direct scan is fine
CREATE OR REPLACE TABLE pg_release_group AS
    SELECT id FROM mb_pg.release_group WHERE type = 1;

CREATE INDEX IF NOT EXISTS idx_rg_id ON pg_release_group (id);

-- release_group_meta for all types: needed so sig2 can look up peer
-- release groups that may not themselves be type=1 albums
CREATE OR REPLACE TABLE pg_release_group_meta AS SELECT * FROM postgres_query('mb_pg',
    'SELECT id, first_release_date_year
     FROM release_group_meta
     WHERE first_release_date_year IS NOT NULL');

CREATE INDEX IF NOT EXISTS idx_rgm_id ON pg_release_group_meta (id);

-- Releases for album release groups only
CREATE OR REPLACE TABLE pg_release AS SELECT * FROM postgres_query('mb_pg',
    'SELECT r.id, r.release_group
     FROM release r
     JOIN release_group rg ON rg.id = r.release_group
     WHERE rg.type = 1');

CREATE INDEX IF NOT EXISTS idx_rel_id ON pg_release (id);
CREATE INDEX IF NOT EXISTS idx_rel_rg ON pg_release (release_group);

-- Earliest release event per release, albums only
-- Aggregated inside Postgres to minimise rows transferred
CREATE OR REPLACE TABLE pg_release_event_agg AS SELECT * FROM postgres_query('mb_pg',
    'SELECT re.release,
            MIN(re.date_year)  AS date_year,
            MIN(re.date_month) AS date_month,
            MIN(re.date_day)   AS date_day
     FROM release_event re
     JOIN release r  ON r.id  = re.release
     JOIN release_group rg ON rg.id = r.release_group
     WHERE rg.type = 1
       AND re.date_year IS NOT NULL
     GROUP BY re.release');

CREATE INDEX IF NOT EXISTS idx_re_rel ON pg_release_event_agg (release);

-- Mediums for album releases only
CREATE OR REPLACE TABLE pg_medium AS SELECT * FROM postgres_query('mb_pg',
    'SELECT m.id, m.release
     FROM medium m
     JOIN release r  ON r.id  = m.release
     JOIN release_group rg ON rg.id = r.release_group
     WHERE rg.type = 1');

CREATE INDEX IF NOT EXISTS idx_med_id  ON pg_medium (id);
CREATE INDEX IF NOT EXISTS idx_med_rel ON pg_medium (release);

-- Tracks for album mediums only; data tracks excluded in Postgres
CREATE OR REPLACE TABLE pg_track AS SELECT * FROM postgres_query('mb_pg',
    'SELECT t.id, t.medium, t.recording, t.length
     FROM track t
     JOIN medium m  ON m.id  = t.medium
     JOIN release r  ON r.id  = m.release
     JOIN release_group rg ON rg.id = r.release_group
     WHERE rg.type = 1
       AND t.is_data_track = false');

CREATE INDEX IF NOT EXISTS idx_trk_id  ON pg_track (id);
CREATE INDEX IF NOT EXISTS idx_trk_med ON pg_track (medium);
CREATE INDEX IF NOT EXISTS idx_trk_rec ON pg_track (recording);

-- AR links between album release groups with a known begin year
CREATE OR REPLACE TABLE pg_l_rg_rg AS SELECT * FROM postgres_query('mb_pg',
    'SELECT lrg.entity0, lrg.entity1, lk.begin_date_year
     FROM l_release_group_release_group lrg
     JOIN link lk ON lk.id = lrg.link
     JOIN release_group rg0 ON rg0.id = lrg.entity0
     JOIN release_group rg1 ON rg1.id = lrg.entity1
     WHERE (rg0.type = 1 OR rg1.type = 1)
       AND lk.begin_date_year IS NOT NULL');

CREATE INDEX IF NOT EXISTS idx_lrg_e0 ON pg_l_rg_rg (entity0);
CREATE INDEX IF NOT EXISTS idx_lrg_e1 ON pg_l_rg_rg (entity1);




-- ============================================================
--  STAGE 1: canonical release per album release_group
-- ============================================================

CREATE OR REPLACE TABLE t_canonical_release AS
WITH dated AS (
    SELECT
        r.release_group                         AS release_group_id,
        r.id                                    AS release_id,
        COALESCE(re.date_year,  9999)           AS sort_year,
        COALESCE(re.date_month,   12)           AS sort_month,
        COALESCE(re.date_day,     31)           AS sort_day,
        re.date_year                            AS release_year
    FROM pg_release                 r
    LEFT JOIN pg_release_event_agg  re ON re.release = r.id
),
canonical AS (
    SELECT *
    FROM dated
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY release_group_id
        ORDER BY sort_year, sort_month, sort_day, release_id
    ) = 1
)
SELECT release_group_id, release_id, release_year
FROM canonical;

CREATE INDEX IF NOT EXISTS idx_tcr_rg  ON t_canonical_release (release_group_id);
CREATE INDEX IF NOT EXISTS idx_tcr_rel ON t_canonical_release (release_id);


-- ============================================================
--  STAGE 2: tracks for canonical releases only
-- ============================================================

CREATE OR REPLACE TABLE t_canonical_tracks AS
SELECT
    cr.release_group_id,
    m.id        AS medium_id,
    t.id        AS track_id,
    t.recording AS recording,
    t.length    AS length_ms
FROM t_canonical_release    cr
JOIN pg_medium               m  ON m.release = cr.release_id
JOIN pg_track                t  ON t.medium  = m.id;

CREATE INDEX IF NOT EXISTS idx_tct_rg  ON t_canonical_tracks (release_group_id);
CREATE INDEX IF NOT EXISTS idx_tct_rec ON t_canonical_tracks (recording);


-- ============================================================
--  STAGE 3: per-album length percentiles
-- ============================================================

CREATE OR REPLACE TABLE t_album_percentiles AS
SELECT
    release_group_id,
    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY length_ms) AS p25_length_ms,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY length_ms) AS median_length_ms,
    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY length_ms) AS p75_length_ms
FROM t_canonical_tracks
WHERE length_ms IS NOT NULL
GROUP BY release_group_id;

CREATE INDEX IF NOT EXISTS idx_tap ON t_album_percentiles (release_group_id);


-- ============================================================
--  STAGE 4: imputed first_release_year
-- ============================================================
-- first_release_year is NULL when the canonical release has no
-- release_event row. Three signals, in priority order:
--
--   sig0: MIN(date_year) across ALL releases in the group via
--         pg_release_event_agg — already fully snapshotted,
--         zero additional Postgres reads. Catches groups where
--         a non-canonical edition has a date the canonical lacks.
--   sig1: AR link begin_date_year — stored on the relationship
--         row, fully independent of release_event.
--   sig2: Peer release group's first_release_date_year — a
--         different release group's release_event data entirely.
--
-- Recording/track tables carry no year data (no date columns on
-- recording; ISRC codes carry no dates) so no additional signals
-- are available from that side of the schema.

CREATE OR REPLACE TABLE t_rg_year_signals AS
WITH
sig0 AS (
    -- Any release_event date in the group (free — already snapshotted)
    SELECT r.release_group        AS release_group_id,
           MIN(re.date_year)::INT AS any_release_year
    FROM pg_release             r
    JOIN pg_release_event_agg   re ON re.release = r.id
    GROUP BY r.release_group
),
sig1 AS (
    -- AR link begin_date_year: independent of release_event
    SELECT
        CASE WHEN entity0 IN (SELECT id FROM pg_release_group)
             THEN entity0 ELSE entity1 END AS release_group_id,
        MIN(begin_date_year)::INT          AS rg_link_year
    FROM pg_l_rg_rg
    GROUP BY 1
),
sig2 AS (
    -- Peer release group's known year via AR links
    SELECT lrg.entity0                           AS release_group_id,
           MIN(rgm.first_release_date_year)::INT AS peer_rg_year
    FROM pg_l_rg_rg            lrg
    JOIN pg_release_group_meta rgm ON rgm.id = lrg.entity1
    WHERE lrg.entity0 IN (SELECT id FROM pg_release_group)
      AND rgm.first_release_date_year IS NOT NULL
    GROUP BY lrg.entity0
)
SELECT
    rg.id AS release_group_id,
    COALESCE(
        s0.any_release_year,  -- any release in group with a date (free)
        s1.rg_link_year,      -- AR relationship date (independent)
        s2.peer_rg_year       -- linked peer release group year
    )::INT AS first_release_year_imputed
FROM pg_release_group       rg
LEFT JOIN sig0              s0 ON s0.release_group_id = rg.id
LEFT JOIN sig1              s1 ON s1.release_group_id = rg.id
LEFT JOIN sig2              s2 ON s2.release_group_id = rg.id;

CREATE INDEX IF NOT EXISTS idx_rys ON t_rg_year_signals (release_group_id);


-- ============================================================
--  FINAL TABLE
-- ============================================================

CREATE OR REPLACE TABLE album_stats AS
SELECT
    rg.id                                                   AS release_group_id,
    cr.release_year::INT                                    AS first_release_year,
    -- ys.first_release_year_imputed,

    COUNT(DISTINCT t.medium_id)::SMALLINT                   AS medium_count,
    COUNT(t.track_id)::SMALLINT                             AS track_count,
    COUNT(t.length_ms)::SMALLINT                            AS track_count_with_length,
    ROUND(100.0 * COUNT(t.length_ms)
               / NULLIF(COUNT(t.track_id), 0), 1)::FLOAT    AS pct_tracks_with_length,

    ROUND(SUM(t.length_ms))::BIGINT                         AS total_length_ms,
    ROUND(AVG(t.length_ms))::INT                            AS mean_length_ms,
    ROUND(p.median_length_ms)::INT                          AS median_length_ms,
    ROUND(STDDEV_POP(t.length_ms))::INT                     AS stddev_length_ms,
    ROUND(VAR_POP(t.length_ms))::BIGINT                     AS variance_length_ms,
    MIN(t.length_ms)::INT                                   AS min_length_ms,
    MAX(t.length_ms)::INT                                   AS max_length_ms,
    (MAX(t.length_ms) - MIN(t.length_ms))::INT              AS range_length_ms,
    ROUND(p.p25_length_ms)::INT                             AS p25_length_ms,
    ROUND(p.p75_length_ms)::INT                             AS p75_length_ms,
    ROUND(p.p75_length_ms - p.p25_length_ms)::INT           AS iqr_length_ms

FROM pg_release_group                   rg
LEFT JOIN t_canonical_release           cr  ON cr.release_group_id = rg.id
LEFT JOIN t_canonical_tracks            t   ON t.release_group_id  = rg.id
LEFT JOIN t_album_percentiles           p   ON p.release_group_id  = rg.id
LEFT JOIN t_rg_year_signals             ys  ON ys.release_group_id = rg.id
GROUP BY
    rg.id,
    cr.release_year,
    -- ys.first_release_year_imputed,
    p.median_length_ms, p.p25_length_ms, p.p75_length_ms
HAVING
    ROUND(100.0 * COUNT(t.length_ms)
               / NULLIF(COUNT(t.track_id), 0), 1) IS NOT NULL;


-- ---- Sanity check -------------------------------------------
SELECT
    COUNT(*)                                                    AS total_albums,
    SUM((first_release_year IS NULL)::INT)                      AS missing_year,
    -- SUM((first_release_year_imputed IS NOT NULL)::INT)           AS with_imputed_year,
    -- SUM((first_release_year IS NULL
    --     AND first_release_year_imputed IS NOT NULL)::INT)       AS newly_imputed,
    ROUND(AVG(track_count),             2)                      AS avg_track_count,
    ROUND(AVG(mean_length_ms / 1000.0), 2)                      AS avg_mean_track_length_sec,
    ROUND(AVG(median_length_ms / 1000.0), 2)                    AS avg_median_track_length_sec,
    ROUND(AVG(total_length_ms / 60000.0), 2)                    AS avg_album_length_min
FROM album_stats;
