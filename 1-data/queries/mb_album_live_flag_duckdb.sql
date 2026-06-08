-- ============================================================
--  MusicBrainz – album live flag  (DuckDB-native)
--  Compatible with DuckDB >= 0.9 + postgres extension
--
--  Exports the set of album-type release groups that carry the
--  "Live" secondary type (release_group_secondary_type.id = 6).
--  Used by the app's Live / Both / Studio album filter — an exact
--  schema lookup, replacing the brittle album-name keyword heuristic.
--
--  Requires mb_pg ATTACHed (see notebooks 06/07 for the pattern):
--    ATTACH 'host=... dbname=... user=... password=...'
--      AS mb_pg (TYPE postgres, READ_ONLY, SCHEMA <user>);
-- ============================================================

-- Live = primary type Album (rg.type = 1) AND secondary type Live (6).
-- One row per live album_id; is_live is a constant True flag so the
-- parquet self-documents and downstream code can do a membership test.
CREATE OR REPLACE TABLE album_live_flag AS
SELECT DISTINCT rg.id AS album_id,
       TRUE       AS is_live
FROM postgres_query('mb_pg',
    'SELECT rg.id
     FROM release_group rg
     JOIN release_group_secondary_type_join j ON j.release_group = rg.id
     WHERE rg.type = 1
       AND j.secondary_type = 6') AS rg;
