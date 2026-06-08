import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import streamlit as st

st.set_page_config(layout='wide', page_title='mixtape')

import json
import pickle
import numpy as np
import pandas as pd
from scipy.sparse import load_npz

DATA_DIR     = os.path.join(os.path.dirname(__file__), '..', 'data')
FEATURES_DIR = os.path.join(DATA_DIR, 'features')

# ---------------------------------------------------------------------------
# Feature blocks — shared across all model versions
# ---------------------------------------------------------------------------
# All three model versions (V3, V4, V5) are built from the same underlying
# sparse feature matrices, differing only in which blocks are included and
# what weights are applied. No .joblib files are needed; cosine similarity
# is computed at query time via weighted dot products.

BLOCKS_V3 = [
    'tags', 'labels', 'types', 'ratings',
    'country', 'track_stats',
    'role_family', 'instrument', 'contrib_cnt',
]
BLOCKS_V4 = [
    'tags', 'labels', 'types', 'ratings',
    'country', 'track_stats',
    'role_family', 'instrument',
    'year',
    # contrib_cnt excluded — W converged to 0.0 in tuning
]
BLOCKS_V5 = BLOCKS_V4 + ['tag_parent']

BLOCK_FILES = {
    'tags':        'album_tags_matrix.npz',
    'labels':      'album_labels_matrix.npz',
    'types':       'album_types_matrix.npz',
    'ratings':     'album_ratings_matrix.npz',
    'country':     'album_country_matrix.npz',
    'track_stats': 'album_track_stats_matrix.npz',
    'role_family': 'album_role_family_matrix.npz',
    'instrument':  'album_instrument_matrix.npz',
    'contrib_cnt': 'album_contributor_counts_matrix.npz',
    'year':        'album_year_matrix.npz',
    'tag_parent':  'album_tag_parent_matrix.npz',
}

# Weight key → best_weights.json key mapping
WEIGHT_KEYS = {
    'tags':        'W_TAGS',
    'labels':      'W_LABELS',
    'types':       'W_TYPES',
    'ratings':     'W_RATINGS',
    'country':     'W_COUNTRY',
    'track_stats': 'W_TRACK_STATS',
    'role_family': 'W_ROLE_FAMILY',
    'instrument':  'W_INSTRUMENT',
    'contrib_cnt': 'W_CONTRIB_CNT',
    'year':        'W_YEAR',
    'tag_parent':  'W_TAG_PARENT',
}

# ---------------------------------------------------------------------------
# Cached loading
# ---------------------------------------------------------------------------

@st.cache_resource
def load_weights():
    path = os.path.join(DATA_DIR, 'best_weights.json')
    with open(path) as f:
        return json.load(f)

@st.cache_resource
def load_blocks():
    """Load all feature blocks once and precompute per-block per-album sum-of-
    squares (||x_b||^2). These are combined at query time under per-block weights
    to compute cosine similarity without rebuilding any model artefacts."""
    blocks = {
        name: load_npz(os.path.join(FEATURES_DIR, fn)).tocsr()
        for name, fn in BLOCK_FILES.items()
    }
    ssq = {
        name: np.asarray(X.multiply(X).sum(axis=1)).ravel().astype(np.float64)
        for name, X in blocks.items()
    }
    return blocks, ssq

@st.cache_resource
def load_album_index():
    with open(os.path.join(FEATURES_DIR, 'album_ids.pkl'), 'rb') as f:
        album_ids = np.array(pickle.load(f))
    album_id_to_row = {int(aid): i for i, aid in enumerate(album_ids)}
    return album_ids, album_id_to_row

@st.cache_resource
def load_lookup():
    return (
        pd.read_parquet(
            os.path.join(DATA_DIR, 'mb_album_artists.parquet'),
            columns=['album_id', 'album_name', 'artist_name'],
        )
        .drop_duplicates(subset='album_id')
        .set_index('album_id')
    )

# ---------------------------------------------------------------------------
# Weighted cosine query — no KNN model needed
# ---------------------------------------------------------------------------

def build_weights(version_key, raw_weights, block_names):
    """Return a {block_name: scalar_weight} dict for the given model version."""
    vw = raw_weights[version_key]
    return {b: vw.get(WEIGHT_KEYS[b], 0.0) for b in block_names}

def weighted_cosine_scores(row, weights, blocks, ssq, n_albums):
    """Compute cosine similarity between album at `row` and all albums,
    using per-block scalar weights applied before L2 normalisation.

    numerator        = sum_b  w_b^2 * (X_b @ q_b)
    album norms sq   = sum_b  w_b^2 * ssq_b[album]
    query norm sq    = sum_b  w_b^2 * ssq_b[row]
    """
    num           = np.zeros(n_albums, dtype=np.float64)
    album_norm_sq = np.zeros(n_albums, dtype=np.float64)
    query_norm_sq = 0.0

    for name, w in weights.items():
        if w == 0.0:
            continue
        wb2  = w * w
        X    = blocks[name]
        q    = X.getrow(row)
        num  += wb2 * np.asarray(X.dot(q.T).todense()).ravel()
        album_norm_sq += wb2 * ssq[name]
        query_norm_sq += wb2 * ssq[name][row]

    if query_norm_sq == 0.0:
        return None

    denom = np.sqrt(album_norm_sq) * np.sqrt(query_norm_sq)
    with np.errstate(divide='ignore', invalid='ignore'):
        scores = np.where(denom > 0, num / denom, -np.inf)
    return scores

def recommend(album_id, n, version_key, raw_weights, block_names,
              blocks, ssq, album_ids, album_id_to_row, lookup):
    if album_id not in album_id_to_row:
        return None

    row      = album_id_to_row[album_id]
    n_albums = len(album_ids)
    weights  = build_weights(version_key, raw_weights, block_names)
    scores   = weighted_cosine_scores(row, weights, blocks, ssq, n_albums)

    if scores is None:
        return None

    scores[row] = -np.inf  # exclude seed itself
    pool = min(n_albums, n * 50)
    cand = np.argpartition(-scores, pool - 1)[:pool]
    cand = cand[np.argsort(-scores[cand])]

    input_artist = lookup.loc[album_id, 'artist_name'] if album_id in lookup.index else None

    results = []
    for idx in cand:
        if not np.isfinite(scores[idx]):
            continue
        aid      = int(album_ids[idx])
        row_data = lookup.loc[aid] if aid in lookup.index else {'album_name': None, 'artist_name': None}
        if pd.isna(row_data['artist_name']):
            continue
        if input_artist and row_data['artist_name'] == input_artist:
            continue
        results.append({
            'Album':    row_data['album_name'],
            'Artist':   row_data['artist_name'],
            'album_id': aid,
        })
        if len(results) == n:
            break

    return pd.DataFrame(results) if results else None

# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------

def search_artist(name, lookup):
    mask = lookup['artist_name'].str.contains(name, case=False, na=False)
    return lookup[mask]

def ids_set(recs):
    if recs is not None and not recs.empty:
        return set(recs['album_id'].tolist())
    return set()

def highlight_exclusive(df, exclusive_ids):
    return [
        'background-color: #fff3cd; color: #1a1714; font-weight: 500;'
        if aid in exclusive_ids else ''
        for aid in df['album_id']
    ]

def render_col(recs, label, exclusive_ids):
    st.markdown('**{}**'.format(label))
    if recs is None or recs.empty:
        st.info('No results for this album.')
    else:
        st.dataframe(
            recs[['Album', 'Artist']].style.apply(
                lambda _: highlight_exclusive(recs, exclusive_ids),
                axis=0,
                subset=pd.IndexSlice[:, 'Album'],
            ),
            use_container_width=True,
            hide_index=True,
        )

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

st.title('mixtape')

raw_weights      = load_weights()
blocks, ssq      = load_blocks()
album_ids, album_id_to_row = load_album_index()
lookup           = load_lookup()

artist_query = st.text_input('Tell us your favourite artist')

if artist_query:
    matches = search_artist(artist_query, lookup)

    if matches.empty:
        st.warning('No artists found. Try a different name.')
    else:
        artists         = matches['artist_name'].dropna().unique()
        selected_artist = st.selectbox('Select artist', sorted(artists))

        artist_albums = matches[matches['artist_name'] == selected_artist]
        album_options = {
            row['album_name']: album_id
            for album_id, row in artist_albums.iterrows()
            if int(album_id) in album_id_to_row
        }

        if not album_options:
            st.info('No recommendable albums found for this artist.')
        else:
            selected_album_name = st.selectbox('Select album', sorted(album_options.keys()))

            if selected_album_name:
                album_id = album_options[selected_album_name]

                recs_v3 = recommend(
                    album_id, 10, 'v3', raw_weights, BLOCKS_V3,
                    blocks, ssq, album_ids, album_id_to_row, lookup,
                )
                recs_v4 = recommend(
                    album_id, 10, 'v4', raw_weights, BLOCKS_V4,
                    blocks, ssq, album_ids, album_id_to_row, lookup,
                )
                recs_v5 = recommend(
                    album_id, 10, 'v5', raw_weights, BLOCKS_V5,
                    blocks, ssq, album_ids, album_id_to_row, lookup,
                )

                if all(r is None or r.empty for r in [recs_v3, recs_v4, recs_v5]):
                    st.info('No recommendations available for this album.')
                else:
                    st.subheader('You might also like')

                    s3, s4, s5 = ids_set(recs_v3), ids_set(recs_v4), ids_set(recs_v5)
                    shared_ids = s3 & s4 & s5
                    only_v3    = s3 - s4 - s5
                    only_v4    = s4 - s3 - s5
                    only_v5    = s5 - s3 - s4

                    st.markdown(
                        "<span style='background-color:#fff3cd;padding:2px 8px;"
                        "border-radius:3px;font-size:0.85em;color:#1a1714;'>highlighted</span>"
                        "&nbsp; = exclusive to this model &nbsp;|&nbsp;"
                        "<span style='font-size:0.85em;'>plain</span>"
                        " = appears in at least one other",
                        unsafe_allow_html=True,
                    )
                    st.write('')

                    col1, col2, col3 = st.columns(3)

                    with col1:
                        render_col(recs_v3, 'v3 (contributors · instruments)', only_v3)
                    with col2:
                        render_col(recs_v4, 'v4 (+ year · tuned weights)', only_v4)
                    with col3:
                        render_col(recs_v5, 'v5 (+ parent genres)', only_v5)

                    st.caption(
                        '{} in all three · {} only in v3 · {} only in v4 · {} only in v5'.format(
                            len(shared_ids), len(only_v3), len(only_v4), len(only_v5),
                        )
                    )
