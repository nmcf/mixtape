-- ============================================================
--  MusicBrainz – album compilation flag  (DuckDB-native)
--  Compatible with DuckDB >= 0.9 + postgres extension
--
--  Exports the set of album-type release groups that carry the
--  "Compilation" secondary type (release_group_secondary_type.id = 1).
--  Used by the app's Hits / Both / No Hits album filter (greatest-hits
--  and other compilations) — an exact schema lookup, not a name guess.
--
--  Requires mb_pg ATTACHed (see notebooks 06/07 for the pattern):
--    ATTACH 'host=... dbname=... user=... password=...'
--      AS mb_pg (TYPE postgres, READ_ONLY, SCHEMA <user>);
-- ============================================================

-- Compilation = primary type Album (rg.type = 1) AND secondary type
-- Compilation (1). One row per album_id; is_compilation is a constant
-- True flag so the parquet self-documents and code can do a membership test.
CREATE OR REPLACE TABLE album_compilation_flag AS
SELECT DISTINCT rg.id AS album_id,
       TRUE       AS is_compilation
FROM postgres_query('mb_pg',
    'SELECT rg.id
     FROM release_group rg
     JOIN release_group_secondary_type_join j ON j.release_group = rg.id
     WHERE rg.type = 1
       AND j.secondary_type = 1') AS rg;
