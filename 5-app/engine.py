"""Core recommendation engine — data loading, queries, auto-tune, and explore."""

import os
import pickle
import numpy as np
import pandas as pd
import streamlit as st
from scipy.sparse import load_npz

from config import (DATA_DIR, FEATURES_DIR, BLOCK_FILES, BLOCK_LABELS,
                    WEIGHT_LEVELS, DEFAULT_LEVELS, LEVEL_OPTIONS,
                    EXPLORE_TOP_N_TAGS, EXPLORE_RESULTS)

# ───────────────────────────────────────────────────────────────────────────
# Data loading (cached — runs once per server process)
# ───────────────────────────────────────────────────────────────────────────

@st.cache_resource
def load_blocks():
    """Load the five sparse feature matrices + album-ID index."""
    blocks = {name: load_npz(os.path.join(FEATURES_DIR, fn)).tocsr()
              for name, fn in BLOCK_FILES.items()}
    with open(os.path.join(FEATURES_DIR, 'album_ids.pkl'), 'rb') as f:
        album_ids = pickle.load(f)
    album_ids = np.asarray(album_ids)
    album_id_to_row = {int(aid): i for i, aid in enumerate(album_ids)}
    ssq = {name: np.asarray(X.multiply(X).sum(axis=1)).ravel().astype(np.float64)
           for name, X in blocks.items()}
    return blocks, album_ids, album_id_to_row, ssq


@st.cache_resource
def load_lookup():
    """Album-ID → (album_name, artist_name) lookup table."""
    return (
        pd.read_parquet(os.path.join(DATA_DIR, 'mb_album_artists.parquet'),
                        columns=['album_id', 'album_name', 'artist_name'])
        .drop_duplicates(subset='album_id')
        .set_index('album_id')
    )


@st.cache_resource
def load_album_country():
    """album_id → country area_id mapping (cached). None if file absent."""
    path = _find_parquet('mb_album_country.parquet')
    if not path:
        return None
    ac = pd.read_parquet(path)
    return ac.drop_duplicates('album_id').set_index('album_id')['country']


def _find_parquet(name):
    """Resolve a parquet file that might live under data/ or data/raw/."""
    for sub in ['raw', '']:
        p = os.path.join(DATA_DIR, sub, name)
        if os.path.exists(p):
            return p
    return None


@st.cache_resource
def load_secondary_types():
    """album_id → (is_live, is_compilation). Returns None if file absent."""
    from config import SECONDARY_TYPE_FILE
    path = _find_parquet(SECONDARY_TYPE_FILE)
    if not path:
        return None
    df = pd.read_parquet(path).set_index('album_id')
    return {
        'live': set(df.index[df['is_live'] == 1]),
        'comp': set(df.index[df['is_compilation'] == 1]),
    }


@st.cache_resource
def load_explore_data():
    """Load tag + country + year data for the Explore tab.

    Returns (tag_options, album_tags_df, album_meta_df, country_options) or
    (None, None, None, None) if the required parquets are missing.
    """
    tag_path     = _find_parquet('mb_tag.parquet')
    atag_path    = _find_parquet('mb_album_tag.parquet')
    area_path    = _find_parquet('mb_area.parquet')
    country_path = _find_parquet('mb_album_country.parquet')
    album_path   = _find_parquet('mb_album.parquet')

    if not all([tag_path, atag_path]):
        return None, None, None, None

    # Tag vocabulary — top N by ref_count
    tags = pd.read_parquet(tag_path)
    top_tags = tags.nlargest(EXPLORE_TOP_N_TAGS, 'ref_count')[['id', 'name']].copy()
    tag_options = dict(zip(top_tags['name'], top_tags['id']))  # name → id

    # Album ↔ tag mapping (the big table)
    album_tags_df = pd.read_parquet(atag_path)

    # Album metadata (year) — optional
    album_meta_df = None
    if album_path:
        cols_to_read = ['id', 'name']
        # Try loading with the columns that exist
        try:
            test = pd.read_parquet(album_path, columns=['id'])
            album_meta_df = pd.read_parquet(album_path, columns=['id', 'name', 'begin_date_year'])
            album_meta_df = album_meta_df.rename(columns={'id': 'album_id', 'name': 'album_name',
                                                           'begin_date_year': 'album_year'})
        except Exception:
            album_meta_df = None

    # Country options — optional
    country_options = None
    if area_path and country_path:
        try:
            areas = pd.read_parquet(area_path)
            countries_only = areas[areas['type'] == 1][['id', 'name']].copy()
            acountry = pd.read_parquet(country_path)
            # Count albums per country, keep top 40
            top_c = (acountry['country'].value_counts().head(40)
                     .reset_index().rename(columns={'country': 'area_id', 'count': 'n'}))
            top_c = top_c.merge(countries_only, left_on='area_id', right_on='id', how='left')
            top_c = top_c.dropna(subset=['name'])
            country_options = dict(zip(top_c['name'], top_c['area_id']))
        except Exception:
            country_options = None

    return tag_options, album_tags_df, album_meta_df, country_options


# ───────────────────────────────────────────────────────────────────────────
# Search helpers
# ───────────────────────────────────────────────────────────────────────────

def search_artist(name, lookup):
    mask = lookup['artist_name'].str.contains(name, case=False, na=False)
    return lookup[mask]


# ───────────────────────────────────────────────────────────────────────────
# Weighted cosine recommendation (for "Find Similar" tab)
# ───────────────────────────────────────────────────────────────────────────

def weighted_cosine(row, weights, blocks, ssq, n_albums):
    num = np.zeros(n_albums)
    album_norm_sq = np.zeros(n_albums)
    query_norm_sq = 0.0
    for name, X in blocks.items():
        wb2 = weights[name] ** 2
        if wb2 == 0.0:
            continue
        q = X.getrow(row)
        num += wb2 * np.asarray(X.dot(q.T).todense()).ravel()
        album_norm_sq += wb2 * ssq[name]
        query_norm_sq += wb2 * ssq[name][row]
    if query_norm_sq == 0.0:
        return None
    denom = np.sqrt(album_norm_sq) * np.sqrt(query_norm_sq)
    with np.errstate(divide='ignore', invalid='ignore'):
        return np.where(denom > 0, num / denom, -np.inf)


def recommend(album_id, n, weights, blocks, album_ids, album_id_to_row, ssq, lookup,
              sec_types=None, live_filter='BOTH', comp_filter='BOTH'):
    if album_id not in album_id_to_row:
        return None
    row = album_id_to_row[album_id]
    n_albums = len(album_ids)
    cosine = weighted_cosine(row, weights, blocks, ssq, n_albums)
    if cosine is None:
        return None
    cosine[row] = -np.inf
    # Bigger candidate pool when filtering, so we still fill n after exclusions
    filtering = sec_types is not None and (live_filter != 'BOTH' or comp_filter != 'BOTH')
    pool = min(n_albums, n * (200 if filtering else 50))
    cand = np.argpartition(-cosine, pool - 1)[:pool]
    cand = cand[np.argsort(-cosine[cand])]
    input_artist = lookup.loc[album_id, 'artist_name'] if album_id in lookup.index else None

    live_set = sec_types['live'] if sec_types else set()
    comp_set = sec_types['comp'] if sec_types else set()

    results = []
    for idx in cand:
        if not np.isfinite(cosine[idx]):
            continue
        aid = int(album_ids[idx])
        if aid not in lookup.index:
            continue
        # Content filters
        if sec_types is not None:
            is_live = aid in live_set
            is_comp = aid in comp_set
            if live_filter == 'STUDIO' and is_live:
                continue
            if live_filter == 'LIVE' and not is_live:
                continue
            if comp_filter == 'ALBUMS' and is_comp:
                continue
            if comp_filter == 'HITS' and not is_comp:
                continue
        row_data = lookup.loc[aid]
        if pd.isna(row_data.get('artist_name')):
            continue
        if input_artist and row_data['artist_name'] == input_artist:
            continue
        results.append({
            'Album':      str(row_data['album_name']) if row_data['album_name'] is not None else '(unknown)',
            'Artist':     str(row_data['artist_name']) if row_data['artist_name'] is not None else '(unknown)',
            'Similarity': round(float(cosine[idx]), 4),
            'album_id':   aid,
        })
        if len(results) == n:
            break
    return pd.DataFrame(results)


# ───────────────────────────────────────────────────────────────────────────
# Auto-Tune — signal-strength profiling
# ───────────────────────────────────────────────────────────────────────────

def _block_cosine(row, name, blocks, ssq):
    X = blocks[name]; s = ssq[name]
    if s[row] <= 0:
        return None
    q = X.getrow(row)
    num = np.asarray(X.dot(q.T).todense()).ravel().astype(np.float64)
    denom = np.sqrt(s) * np.sqrt(s[row])
    with np.errstate(divide='ignore', invalid='ignore'):
        c = np.where(denom > 0, num / denom, np.nan)
    c[row] = np.nan
    return c


def auto_tune_profile(album_id, blocks, ssq, album_id_to_row, topk=25):
    if album_id not in album_id_to_row:
        return None, None
    row = album_id_to_row[album_id]
    raw = {}
    for name in BLOCK_FILES:
        c = _block_cosine(row, name, blocks, ssq)
        if c is None:
            raw[name] = 0.0
            continue
        fin = c[np.isfinite(c)]
        if fin.size < topk + 5:
            raw[name] = 0.0
            continue
        top = np.partition(fin, -topk)[-topk:]
        raw[name] = max(0.0, float(top.mean() - np.median(fin)))
    mx = max(raw.values()) if raw else 0.0
    scores = {n: (raw[n] / mx if mx > 0 else 0.0) for n in BLOCK_FILES}
    if mx <= 0:
        return dict(DEFAULT_LEVELS), scores
    return scores, scores   # return raw scores — smart-tune logic lives in the callback


def smart_auto_tune(scores, user_prefs):
    """Combine signal strength scores with user preferences (slider values).

    Parameters
    ----------
    scores : dict[str, float]  — per-block signal strength (0..1)
    user_prefs : dict[str, float] — per-block user weight from WEIGHT_LEVELS

    Returns
    -------
    dict[str, str] — per-block level name (Off/Low/Medium/High)
    """
    combined = {n: scores.get(n, 0) * user_prefs.get(n, 0) for n in BLOCK_FILES}
    mx = max(combined.values()) if combined else 0.0

    if mx <= 0:
        # Fallback to pure signal strength
        levels = {}
        for n in BLOCK_FILES:
            r = scores.get(n, 0)
            levels[n] = ('Off' if r <= 0 else 'High' if r >= 0.66
                         else 'Medium' if r >= 0.33 else 'Low')
        return levels

    norm = {n: combined[n] / mx for n in BLOCK_FILES}
    levels = {}
    for n in BLOCK_FILES:
        r = norm[n]
        levels[n] = ('Off' if r <= 0.05 else 'High' if r >= 0.66
                     else 'Medium' if r >= 0.33 else 'Low')
    # Guarantee at least one High
    if not any(v == 'High' for v in levels.values()):
        best = max(norm, key=norm.get)
        levels[best] = 'High'
    return levels


# ───────────────────────────────────────────────────────────────────────────
# Explore — tag-based album discovery
# ───────────────────────────────────────────────────────────────────────────

def explore_search(selected_tag_ids, country_id, year_range,
                   album_tags_df, album_meta_df, lookup, album_id_to_row,
                   max_results=EXPLORE_RESULTS):
    """Find albums matching selected genre tags, optionally filtered by country and year.

    Scoring: for each album, score = sum of tag_count for all matching tags.
    Higher = better match (more of the requested tags, with higher community agreement).
    """
    if not selected_tag_ids:
        return None

    # Step 1: find albums that have any of the selected tags
    mask = album_tags_df['tag_id'].isin(selected_tag_ids)
    matches = album_tags_df[mask].copy()
    if matches.empty:
        return None

    # Matched score = sum of tag_count for the selected tags this album has
    scored = matches.groupby('album_id')['tag_count'].sum().reset_index()
    scored.columns = ['album_id', 'matched_count']
    # How many of the selected tags this album carries
    tag_hits = matches.groupby('album_id')['tag_id'].nunique().reset_index()
    tag_hits.columns = ['album_id', 'tags_matched']
    scored = scored.merge(tag_hits, on='album_id')

    # Step 2: filter to "recommendable" albums (in the feature matrix)
    recommendable = set(album_id_to_row.keys())
    scored = scored[scored['album_id'].isin(recommendable)]
    if scored.empty:
        return None

    # Relevance: how much of the album's TOTAL tagging is the selected genres.
    # This stops mega-popular albums (tagged with everything at count 1) from
    # dominating, and makes genre-defining albums rise instead.
    cand_ids = set(scored['album_id'])
    totals = (album_tags_df[album_tags_df['album_id'].isin(cand_ids)]
              .groupby('album_id')['tag_count'].sum().reset_index())
    totals.columns = ['album_id', 'total_count']
    scored = scored.merge(totals, on='album_id', how='left')
    scored['relevance'] = scored['matched_count'] / scored['total_count'].clip(lower=1)
    # Need a few tags total for relevance to mean anything
    scored = scored[scored['total_count'] >= 3]
    if scored.empty:
        return None

    # Step 3: optionally filter by year
    if album_meta_df is not None and year_range is not None:
        yr_min, yr_max = year_range
        yr_lookup = album_meta_df.set_index('album_id')['album_year']
        scored = scored.merge(yr_lookup, on='album_id', how='left')
        scored = scored[scored['album_year'].between(yr_min, yr_max) | scored['album_year'].isna()]
    else:
        scored['album_year'] = None

    # Step 4: optionally filter by country
    if country_id is not None:
        ac = load_album_country()
        if ac is not None:
            country_albums = set(ac.index[ac == country_id])
            scored = scored[scored['album_id'].isin(country_albums)]

    if scored.empty:
        return None

    # Step 5: rank — by how central the selected genres are to each album
    # (relevance), with tag-match count as a tiebreaker. Relevance-primary stops
    # mega-popular "tagged with everything" albums from dominating.
    scored = scored.sort_values(['relevance', 'tags_matched'],
                                ascending=[False, False]).head(max_results * 4)
    results = []
    artist_counts = {}
    for _, row in scored.iterrows():
        aid = int(row['album_id'])
        if aid not in lookup.index:
            continue
        lr = lookup.loc[aid]
        artist = str(lr.get('artist_name', '')) if lr.get('artist_name') is not None else ''
        if not artist or artist == 'Various Artists':
            continue
        # Cap at 2 albums per artist for variety
        if artist_counts.get(artist, 0) >= 2:
            continue
        artist_counts[artist] = artist_counts.get(artist, 0) + 1

        album_name = str(lr.get('album_name', '')) if lr.get('album_name') is not None else '(unknown)'
        year_val = row.get('album_year')
        year_str = str(int(year_val)) if pd.notna(year_val) and year_val is not None else ''
        results.append({
            'Album':         album_name,
            'Artist':        artist,
            'Tags Matched':  int(row['tags_matched']),
            'Match':         int(round(row['relevance'] * 100)),
            'Year':          year_str,
            'album_id':      aid,
        })
        if len(results) >= max_results:
            break

    return pd.DataFrame(results) if results else None


# ───────────────────────────────────────────────────────────────────────────
# Album Card — rich metadata for display
# ───────────────────────────────────────────────────────────────────────────

def get_album_info(album_id, lookup, explore_data):
    """Return a dict with album metadata for the card display."""
    tag_options, album_tags_df, album_meta_df, country_options = explore_data
    info = {}

    if album_id in lookup.index:
        r = lookup.loc[album_id]
        info['album_name'] = str(r.get('album_name') or '?')
        info['artist_name'] = str(r.get('artist_name') or '?')

    if album_meta_df is not None:
        yr = album_meta_df[album_meta_df['album_id'] == album_id]
        if not yr.empty:
            y = yr.iloc[0].get('album_year')
            if pd.notna(y):
                info['year'] = int(y)

    if country_options and album_tags_df is not None:
        ac = load_album_country()
        if ac is not None and album_id in ac.index:
            cid = ac.loc[album_id]
            inv = {v: k for k, v in country_options.items()}
            info['country'] = inv.get(cid, '')

    if album_tags_df is not None and tag_options:
        inv = {v: k for k, v in tag_options.items()}
        rows = album_tags_df[album_tags_df['album_id'] == album_id]
        tags = []
        for _, tr in rows.nlargest(6, 'tag_count').iterrows():
            name = inv.get(tr['tag_id'])
            if name:
                tags.append(name)
        if tags:
            info['tags'] = tags

    return info


# ───────────────────────────────────────────────────────────────────────────
# Why this rec — per-block cosine breakdown
# ───────────────────────────────────────────────────────────────────────────

def per_block_similarity(query_row, rec_row, blocks, ssq):
    """Compute cosine similarity per feature block between two album rows."""
    result = {}
    for name, X in blocks.items():
        q_norm = ssq[name][query_row] ** 0.5
        r_norm = ssq[name][rec_row] ** 0.5
        if q_norm > 0 and r_norm > 0:
            dot = X[query_row].dot(X[rec_row].T).toarray().item()
            result[name] = round(dot / (q_norm * r_norm), 3)
        else:
            result[name] = 0.0
    return result
