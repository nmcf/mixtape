-- ============================================================
--  MusicBrainz – artist_country_fast table  (DuckDB-native)
--  Compatible with DuckDB >= 0.9 + postgres_scanner extension
--
--  Signals used (COALESCE priority order, strongest first):
--    1. artist.area              direct column
--    2. artist.begin_area        direct column
--    3. artist_release mat       precomputed MB table, no joins
--    4. artist_release_group mat precomputed MB table, no joins
--    5. l_area_artist            inverse AR area→artist, single join
--    6. l_artist_label           direct AR artist→label→area
--    7. l_artist_place           direct AR artist→place→area
--    8. release_country (direct) artist_credit_name→release→release_event
--                                (all local tables, fast after snapshot)
--    9. release_group first      release_group→release→release_event, first date
--   10. release_group mode       release_group→release→release_event, modal country
--
--  All Postgres tables snapshotted locally once; all subsequent
--  work runs entirely in DuckDB (no cross-process round-trips).
--
--  Usage:
--    duck_con.execute(SQL_PATH.read_text(encoding="utf-8-sig"))
--    df = duck_con.execute("SELECT * FROM artist_country_fast").df()
-- ============================================================


-- ============================================================
--  STAGE 0: snapshot Postgres tables into DuckDB (runs once)
-- ============================================================

CREATE OR REPLACE TABLE pg_area               AS SELECT * FROM mb_pg.area;
CREATE OR REPLACE TABLE pg_artist             AS SELECT id, gid, name, area, begin_area
                                                 FROM mb_pg.artist;
-- postgres_query() bypasses ctid parallel scan that crashes some Docker setups
CREATE OR REPLACE TABLE pg_artist_release     AS
    SELECT artist, country_code
    FROM postgres_query('mb_pg',
        'SELECT artist, country_code FROM artist_release
         WHERE country_code IS NOT NULL');
CREATE OR REPLACE TABLE pg_artist_release_group AS
    SELECT artist, release_group
    FROM postgres_query('mb_pg',
        'SELECT artist, release_group FROM artist_release_group');
CREATE OR REPLACE TABLE pg_iso_3166_1         AS SELECT * FROM mb_pg.iso_3166_1;
CREATE OR REPLACE TABLE pg_iso_3166_2         AS SELECT * FROM mb_pg.iso_3166_2;
CREATE OR REPLACE TABLE pg_l_area_area        AS SELECT * FROM mb_pg.l_area_area;
CREATE OR REPLACE TABLE pg_l_area_artist      AS SELECT entity0, entity1
                                                 FROM mb_pg.l_area_artist;
CREATE OR REPLACE TABLE pg_l_artist_label     AS SELECT entity0, entity1
                                                 FROM mb_pg.l_artist_label;
CREATE OR REPLACE TABLE pg_l_artist_place     AS SELECT entity0, entity1
                                                 FROM mb_pg.l_artist_place;
CREATE OR REPLACE TABLE pg_label              AS SELECT id, area FROM mb_pg.label
                                                 WHERE area IS NOT NULL;
CREATE OR REPLACE TABLE pg_place              AS SELECT id, area FROM mb_pg.place
                                                 WHERE area IS NOT NULL;
-- release_group: ALL types (no type filter) so singles/EPs also contribute
CREATE OR REPLACE TABLE pg_release_group      AS SELECT id, artist_credit
                                                 FROM mb_pg.release_group;
CREATE OR REPLACE TABLE pg_release            AS SELECT id, release_group, artist_credit
                                                 FROM mb_pg.release;
CREATE OR REPLACE TABLE pg_release_event      AS SELECT release, country,
                                                        date_year, date_month, date_day
                                                 FROM mb_pg.release_event
                                                 WHERE country IS NOT NULL;
CREATE OR REPLACE TABLE pg_artist_credit_name AS SELECT artist_credit, artist
                                                 FROM mb_pg.artist_credit_name;
CREATE OR REPLACE TABLE pg_link               AS SELECT * FROM mb_pg.link;
CREATE OR REPLACE TABLE pg_link_type          AS SELECT * FROM mb_pg.link_type;

-- Indexes on all join keys
CREATE INDEX IF NOT EXISTS idx_iso1_area    ON pg_iso_3166_1          (area);
CREATE INDEX IF NOT EXISTS idx_laa_e0       ON pg_l_area_area         (entity0);
CREATE INDEX IF NOT EXISTS idx_laa_e1       ON pg_l_area_area         (entity1);
CREATE INDEX IF NOT EXISTS idx_laa_e1       ON pg_l_area_artist       (entity1);
CREATE INDEX IF NOT EXISTS idx_laa_e0_art   ON pg_l_area_artist       (entity0);
CREATE INDEX IF NOT EXISTS idx_link_id      ON pg_link                (id);
CREATE INDEX IF NOT EXISTS idx_lt_id        ON pg_link_type           (id);
CREATE INDEX IF NOT EXISTS idx_ar_artist    ON pg_artist_release      (artist);
CREATE INDEX IF NOT EXISTS idx_arg_artist   ON pg_artist_release_group(artist);
CREATE INDEX IF NOT EXISTS idx_arg_rg       ON pg_artist_release_group(release_group);
CREATE INDEX IF NOT EXISTS idx_lal_e0       ON pg_l_artist_label      (entity0);
CREATE INDEX IF NOT EXISTS idx_lal_e1       ON pg_l_artist_label      (entity1);
CREATE INDEX IF NOT EXISTS idx_label_id     ON pg_label               (id);
CREATE INDEX IF NOT EXISTS idx_lap_e0       ON pg_l_artist_place      (entity0);
CREATE INDEX IF NOT EXISTS idx_lap_e1       ON pg_l_artist_place      (entity1);
CREATE INDEX IF NOT EXISTS idx_place_id     ON pg_place               (id);
CREATE INDEX IF NOT EXISTS idx_rg_id        ON pg_release_group       (id);
CREATE INDEX IF NOT EXISTS idx_rg_ac        ON pg_release_group       (artist_credit);
CREATE INDEX IF NOT EXISTS idx_rel_rg       ON pg_release             (release_group);
CREATE INDEX IF NOT EXISTS idx_rel_id       ON pg_release             (id);
CREATE INDEX IF NOT EXISTS idx_re_release   ON pg_release_event       (release);
CREATE INDEX IF NOT EXISTS idx_re_country   ON pg_release_event       (country);
CREATE INDEX IF NOT EXISTS idx_acn_ac       ON pg_artist_credit_name  (artist_credit);
CREATE INDEX IF NOT EXISTS idx_acn_artist   ON pg_artist_credit_name  (artist);


-- ============================================================
--  STAGE 1: pre-resolve "part of" link type ids
-- ============================================================

CREATE OR REPLACE TABLE pg_part_of_link_ids AS
SELECT lk.id AS link_id
FROM pg_link      lk
JOIN pg_link_type lt ON lt.id = lk.link_type
WHERE lt.name = 'part of';

CREATE INDEX IF NOT EXISTS idx_poli ON pg_part_of_link_ids (link_id);


-- ============================================================
--  STAGE 2: area hierarchy + country resolution (computed once)
-- ============================================================

-- Walk area containment up to 3 levels via "part of" AR
CREATE OR REPLACE VIEW v_area_parent AS
SELECT rel.entity0 AS area_id, rel.entity1 AS parent_area_id, 1 AS depth
FROM pg_l_area_area rel
JOIN pg_part_of_link_ids p ON p.link_id = rel.link

UNION ALL

SELECT rel.entity0, rel2.entity1, 2
FROM pg_l_area_area      rel
JOIN pg_part_of_link_ids p   ON p.link_id    = rel.link
JOIN pg_l_area_area      rel2 ON rel2.entity0 = rel.entity1
JOIN pg_part_of_link_ids p2  ON p2.link_id   = rel2.link

UNION ALL

SELECT rel.entity0, rel3.entity1, 3
FROM pg_l_area_area      rel
JOIN pg_part_of_link_ids p   ON p.link_id    = rel.link
JOIN pg_l_area_area      rel2 ON rel2.entity0 = rel.entity1
JOIN pg_part_of_link_ids p2  ON p2.link_id   = rel2.link
JOIN pg_l_area_area      rel3 ON rel3.entity0 = rel2.entity1
JOIN pg_part_of_link_ids p3  ON p3.link_id   = rel3.link;


-- Materialise area → effective ISO country code (used by every signal)
CREATE OR REPLACE TABLE t_area_country AS
WITH area_with_own_iso AS (
    SELECT
        a.id                AS area_id,
        a.name              AS area_name,
        a.type              AS area_type,
        iso1.code           AS iso_3166_1_code,
        NULL::INTEGER       AS country_area_id,
        NULL::VARCHAR       AS country_iso_code
    FROM pg_area            a
    JOIN pg_iso_3166_1      iso1 ON iso1.area = a.id
),
area_resolved_via_parent AS (
    SELECT
        a.id                AS area_id,
        a.name              AS area_name,
        a.type              AS area_type,
        NULL::VARCHAR       AS iso_3166_1_code,
        parent_iso.area     AS country_area_id,
        parent_iso.code     AS country_iso_code
    FROM pg_area            a
    LEFT JOIN pg_iso_3166_1 own_iso    ON own_iso.area    = a.id
    JOIN v_area_parent      ap         ON ap.area_id      = a.id
    JOIN pg_iso_3166_1      parent_iso ON parent_iso.area = ap.parent_area_id
    WHERE own_iso.area IS NULL
    QUALIFY ROW_NUMBER() OVER (PARTITION BY a.id ORDER BY ap.depth) = 1
)
SELECT area_id, area_name, area_type, country_area_id,
       COALESCE(iso_3166_1_code, country_iso_code) AS effective_country_code
FROM area_with_own_iso
UNION ALL
SELECT area_id, area_name, area_type, country_area_id,
       country_iso_code AS effective_country_code
FROM area_resolved_via_parent;

CREATE INDEX IF NOT EXISTS idx_tac ON t_area_country (area_id);


-- ISO code → country area.id (used in final imputation step)
CREATE OR REPLACE TABLE t_iso_to_area_id AS
SELECT code AS iso_code, area AS country_area_id
FROM pg_iso_3166_1;

CREATE INDEX IF NOT EXISTS idx_tia ON t_iso_to_area_id (iso_code);


-- ============================================================
--  STAGE 3: signal – artist_release materialized table
-- ============================================================
-- MusicBrainz precomputes (artist, country_code) — no joins needed.
-- Modal country per artist across all releases.

CREATE OR REPLACE TABLE t_sig_release_mat AS
WITH counted AS (
    SELECT artist AS artist_id, country_code, COUNT(*) AS cnt
    FROM pg_artist_release
    GROUP BY artist, country_code
),
ranked AS (
    SELECT artist_id, country_code,
           ROW_NUMBER() OVER (
               PARTITION BY artist_id ORDER BY cnt DESC, country_code
           ) AS rn
    FROM counted
)
SELECT artist_id,
       MAX(country_code) FILTER (WHERE rn = 1) AS release_mat_country_mode
FROM ranked GROUP BY artist_id;

CREATE INDEX IF NOT EXISTS idx_srm ON t_sig_release_mat (artist_id);


-- ============================================================
--  STAGE 4: signal – artist_release_group materialized table
-- ============================================================
-- Precomputed (artist, release_group) — bridges to release_event
-- without needing artist_credit_name at all.
-- Covers all release group types (albums, singles, EPs, etc.).

CREATE OR REPLACE TABLE t_sig_release_group_mat AS
WITH rg_country AS (
    SELECT
        arg.artist                          AS artist_id,
        ac.effective_country_code           AS country_code,
        COALESCE(re.date_year,  9999)       AS sort_year,
        COALESCE(re.date_month,   12)       AS sort_month,
        COALESCE(re.date_day,     31)       AS sort_day
    FROM pg_artist_release_group    arg
    JOIN pg_release                 r   ON r.release_group = arg.release_group
    JOIN pg_release_event           re  ON re.release      = r.id
    JOIN t_area_country             ac  ON ac.area_id      = re.country
),
-- first-release country per artist across all their release groups
first_per_artist AS (
    SELECT artist_id, country_code
    FROM rg_country
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY artist_id
        ORDER BY sort_year, sort_month, sort_day, country_code
    ) = 1
),
-- modal country per artist across all their release group release events
counted AS (
    SELECT artist_id, country_code, COUNT(*) AS cnt
    FROM rg_country GROUP BY artist_id, country_code
),
mode_per_artist AS (
    SELECT artist_id, country_code
    FROM counted
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY artist_id ORDER BY cnt DESC, country_code
    ) = 1
)
SELECT
    COALESCE(f.artist_id, m.artist_id)  AS artist_id,
    f.country_code                      AS arg_first_country,
    m.country_code                      AS arg_mode_country
FROM first_per_artist   f
FULL OUTER JOIN mode_per_artist m ON m.artist_id = f.artist_id;

CREATE INDEX IF NOT EXISTS idx_srgm ON t_sig_release_group_mat (artist_id);


-- ============================================================
--  STAGE 5: signal – l_area_artist (inverse AR area→artist)
-- ============================================================
-- entity0=area, entity1=artist. Single join to t_area_country.
-- Captures cases where artist.area is NULL but an area editor
-- has explicitly linked the area to the artist via the AR system.

CREATE OR REPLACE TABLE t_sig_area_artist AS
WITH base AS (
    SELECT
        laa.entity1                     AS artist_id,
        ac.effective_country_code       AS country_code
    FROM pg_l_area_artist   laa
    JOIN t_area_country     ac  ON ac.area_id = laa.entity0
),
counted AS (
    SELECT artist_id, country_code, COUNT(*) AS cnt
    FROM base GROUP BY artist_id, country_code
),
ranked AS (
    SELECT artist_id, country_code,
           ROW_NUMBER() OVER (
               PARTITION BY artist_id ORDER BY cnt DESC, country_code
           ) AS rn
    FROM counted
)
SELECT artist_id,
       MAX(country_code) FILTER (WHERE rn = 1) AS area_artist_country_mode
FROM ranked GROUP BY artist_id;

CREATE INDEX IF NOT EXISTS idx_saa ON t_sig_area_artist (artist_id);


-- ============================================================
--  STAGE 6: signal – direct artist→label area
-- ============================================================
-- l_artist_label: entity0=artist, entity1=label → label.area
-- All link types (signed to, member of label, etc.)

CREATE OR REPLACE TABLE t_sig_label_direct AS
WITH base AS (
    SELECT
        lal.entity0                     AS artist_id,
        ac.effective_country_code       AS country_code
    FROM pg_l_artist_label  lal
    JOIN pg_label            l   ON l.id       = lal.entity1
    JOIN t_area_country      ac  ON ac.area_id = l.area
),
counted AS (
    SELECT artist_id, country_code, COUNT(*) AS cnt
    FROM base GROUP BY artist_id, country_code
),
ranked AS (
    SELECT artist_id, country_code,
           ROW_NUMBER() OVER (
               PARTITION BY artist_id ORDER BY cnt DESC, country_code
           ) AS rn
    FROM counted
)
SELECT artist_id,
       MAX(country_code) FILTER (WHERE rn = 1) AS label_direct_country_mode
FROM ranked GROUP BY artist_id;

CREATE INDEX IF NOT EXISTS idx_sld ON t_sig_label_direct (artist_id);


-- ============================================================
--  STAGE 7: signal – direct artist→place area
-- ============================================================
-- l_artist_place: entity0=artist, entity1=place → place.area
-- All link types (primary venue, owns, recorded at, born in, etc.)

CREATE OR REPLACE TABLE t_sig_place_direct AS
WITH base AS (
    SELECT
        lap.entity0                     AS artist_id,
        ac.effective_country_code       AS country_code
    FROM pg_l_artist_place  lap
    JOIN pg_place            p   ON p.id       = lap.entity1
    JOIN t_area_country      ac  ON ac.area_id = p.area
),
counted AS (
    SELECT artist_id, country_code, COUNT(*) AS cnt
    FROM base GROUP BY artist_id, country_code
),
ranked AS (
    SELECT artist_id, country_code,
           ROW_NUMBER() OVER (
               PARTITION BY artist_id ORDER BY cnt DESC, country_code
           ) AS rn
    FROM counted
)
SELECT artist_id,
       MAX(country_code) FILTER (WHERE rn = 1) AS place_direct_country_mode
FROM ranked GROUP BY artist_id;

CREATE INDEX IF NOT EXISTS idx_spd ON t_sig_place_direct (artist_id);


-- ============================================================
--  STAGE 8: signal – direct release_country
-- ============================================================
-- artist_credit_name → release → release_event → country
-- Was excluded when tables were remote; all tables are now local
-- so this is a fast DuckDB-only hash join.
-- Modal country per artist across all individual release events.

CREATE OR REPLACE TABLE t_sig_release_country AS
WITH base AS (
    SELECT
        acn.artist                      AS artist_id,
        ac.effective_country_code       AS country_code
    FROM pg_artist_credit_name  acn
    JOIN pg_release              r   ON r.artist_credit = acn.artist_credit
    JOIN pg_release_event        re  ON re.release      = r.id
    JOIN t_area_country          ac  ON ac.area_id      = re.country
),
counted AS (
    SELECT artist_id, country_code, COUNT(*) AS cnt
    FROM base GROUP BY artist_id, country_code
),
ranked AS (
    SELECT artist_id, country_code,
           ROW_NUMBER() OVER (
               PARTITION BY artist_id ORDER BY cnt DESC, country_code
           ) AS rn
    FROM counted
)
SELECT artist_id,
       MAX(country_code) FILTER (WHERE rn = 1) AS release_country_mode
FROM ranked GROUP BY artist_id;

CREATE INDEX IF NOT EXISTS idx_src ON t_sig_release_country (artist_id);


-- ============================================================
--  STAGE 9: signal – release_group first + modal country
-- ============================================================
-- release_group (all types) → release → release_event → country
-- Bridge to artist via artist_credit_name on release_group.artist_credit.
-- Computed after all aggregation so the acn join is on a small table.

CREATE OR REPLACE TABLE t_sig_rg_country AS
WITH rg_country AS (
    SELECT
        r.release_group,
        ac.effective_country_code           AS country_code,
        COALESCE(re.date_year,  9999)       AS sort_year,
        COALESCE(re.date_month,   12)       AS sort_month,
        COALESCE(re.date_day,     31)       AS sort_day
    FROM pg_release         r
    JOIN pg_release_event   re  ON re.release  = r.id
    JOIN t_area_country     ac  ON ac.area_id  = re.country
),
rg_first AS (
    SELECT release_group, country_code
    FROM rg_country
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY release_group
        ORDER BY sort_year, sort_month, sort_day, country_code
    ) = 1
),
rg_counted AS (
    SELECT release_group, country_code, COUNT(*) AS cnt
    FROM rg_country GROUP BY release_group, country_code
),
rg_mode AS (
    SELECT release_group, country_code
    FROM rg_counted
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY release_group ORDER BY cnt DESC, country_code
    ) = 1
),
artist_rg_first AS (
    SELECT acn.artist AS artist_id, f.country_code AS rg_first_country
    FROM rg_first               f
    JOIN pg_release_group       rg  ON rg.id            = f.release_group
    JOIN pg_artist_credit_name  acn ON acn.artist_credit = rg.artist_credit
),
artist_rg_mode AS (
    SELECT acn.artist AS artist_id, m.country_code AS rg_mode_country
    FROM rg_mode                m
    JOIN pg_release_group       rg  ON rg.id            = m.release_group
    JOIN pg_artist_credit_name  acn ON acn.artist_credit = rg.artist_credit
),
artist_first_counted AS (
    SELECT artist_id, rg_first_country, COUNT(*) AS cnt
    FROM artist_rg_first GROUP BY artist_id, rg_first_country
),
artist_mode_counted AS (
    SELECT artist_id, rg_mode_country, COUNT(*) AS cnt
    FROM artist_rg_mode GROUP BY artist_id, rg_mode_country
)
SELECT
    COALESCE(af.artist_id, am.artist_id) AS artist_id,
    MAX(af.rg_first_country) FILTER (WHERE af.cnt = (
        SELECT MAX(cnt) FROM artist_first_counted af2
        WHERE af2.artist_id = af.artist_id))    AS rg_first_country_mode,
    MAX(am.rg_mode_country)  FILTER (WHERE am.cnt = (
        SELECT MAX(cnt) FROM artist_mode_counted am2
        WHERE am2.artist_id = am.artist_id))    AS rg_mode_country_mode
FROM artist_first_counted   af
FULL OUTER JOIN artist_mode_counted am ON am.artist_id = af.artist_id
GROUP BY COALESCE(af.artist_id, am.artist_id);

CREATE INDEX IF NOT EXISTS idx_srg ON t_sig_rg_country (artist_id);


-- ============================================================
--  FINAL TABLE
-- ============================================================

CREATE OR REPLACE TABLE artist_country_fast AS
WITH base AS (
    SELECT
        ar.id                               AS artist_id,
        ar.gid                              AS artist_mbid,
        ar.name                             AS artist_name,
        ar.area                             AS area_id,
        ac_area.area_name,
        ac_area.effective_country_code      AS area_country_code,
        ac_area.country_area_id             AS area_country_area_id,
        ac_begin.effective_country_code     AS begin_country_code
    FROM pg_artist              ar
    LEFT JOIN t_area_country    ac_area  ON ac_area.area_id  = ar.area
    LEFT JOIN t_area_country    ac_begin ON ac_begin.area_id = ar.begin_area
),
signals AS (
    SELECT
        b.artist_id,
        b.artist_mbid,
        b.artist_name,
        b.area_id,
        b.area_name,

        -- country_id: area_id if already a country, else walked-up ancestor
        CASE
            WHEN b.area_id IS NULL              THEN NULL
            WHEN b.area_country_area_id IS NULL THEN b.area_id
            ELSE                                     b.area_country_area_id
        END                                         AS country_id,

        (b.area_country_code IS NULL)               AS area_is_missing,

        COALESCE(
            b.area_country_code,                 -- 1. own area (ground truth)
            b.begin_country_code,                -- 2. born/formed in
            srm.release_mat_country_mode,        -- 3. artist_release mat
            srgm.arg_first_country,              -- 4. artist_release_group mat first
            srgm.arg_mode_country,               -- 4. artist_release_group mat mode
            saa.area_artist_country_mode,        -- 5. l_area_artist inverse AR
            sld.label_direct_country_mode,       -- 6. l_artist_label AR
            spd.place_direct_country_mode,       -- 7. l_artist_place AR
            src.release_country_mode,            -- 8. release_country (local join)
            srg.rg_first_country_mode,           -- 9. release_group first
            srg.rg_mode_country_mode             -- 10. release_group mode
        )                                           AS imputed_iso_code

    FROM base                           b
    LEFT JOIN t_sig_release_mat         srm  ON srm.artist_id  = b.artist_id
    LEFT JOIN t_sig_release_group_mat   srgm ON srgm.artist_id = b.artist_id
    LEFT JOIN t_sig_area_artist         saa  ON saa.artist_id  = b.artist_id
    LEFT JOIN t_sig_label_direct        sld  ON sld.artist_id  = b.artist_id
    LEFT JOIN t_sig_place_direct        spd  ON spd.artist_id  = b.artist_id
    LEFT JOIN t_sig_release_country     src  ON src.artist_id  = b.artist_id
    LEFT JOIN t_sig_rg_country          srg  ON srg.artist_id  = b.artist_id
)
SELECT
    s.artist_id,
    -- s.artist_mbid,
    s.artist_name,
    s.area_id,
    s.area_name,
    s.country_id,
    s.area_is_missing,
    CASE
        WHEN NOT s.area_is_missing          THEN s.country_id
        WHEN s.imputed_iso_code IS NOT NULL  THEN iac.country_area_id
        ELSE                                     NULL
    END                                         AS country_id_imputed
FROM signals                s
LEFT JOIN t_iso_to_area_id  iac ON iac.iso_code = s.imputed_iso_code;


-- ---- Sanity check -------------------------------------------
SELECT
    COUNT(*)                                                AS total_artists,
    SUM(area_is_missing::INT)                               AS missing_area,
    ROUND(100.0 * SUM(area_is_missing::INT) / COUNT(*), 2)  AS pct_missing,
    SUM((country_id         IS NOT NULL)::INT)              AS with_country_id,
    SUM((country_id_imputed IS NOT NULL)::INT)              AS with_country_id_imputed,
    SUM((area_is_missing
         AND country_id_imputed IS NOT NULL)::INT)          AS imputed_from_signals
FROM artist_country_fast;
