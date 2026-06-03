import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import streamlit as st
import pandas as pd
import numpy as np
from scipy.sparse import load_npz
import pickle

DATA_DIR     = os.path.join(os.path.dirname(__file__), '..', 'data')
FEATURES_DIR = os.path.join(DATA_DIR, 'features')

# The five v3 feature blocks. Defaults match 12-knn-v3-training.ipynb.
BLOCK_FILES = {
    'genre':        'album_genre_matrix.npz',
    'record_label': 'album_record_label_matrix.npz',
    'ratings':      'album_ratings_matrix.npz',
    'country':      'album_country_matrix.npz',
    'track_stats':  'album_track_stats_matrix.npz',
}
DEFAULT_WEIGHTS = {
    'genre':        1.0,
    'record_label': 1.0,
    'ratings':      1.0,
    'country':      0.2,
    'track_stats':  1.0,
}
BLOCK_LABELS = {
    'genre':        'Genre tags',
    'record_label': 'Record label',
    'ratings':      'Ratings',
    'country':      'Country',
    'track_stats':  'Track stats',
}

# ---------------------------------------------------------------------------
# Cached resource loading
# ---------------------------------------------------------------------------

@st.cache_resource
def load_blocks():
    """Load the raw (unweighted) feature blocks plus precomputed per-block,
    per-album sum-of-squares used for fast runtime cosine reweighting."""
    blocks = {name: load_npz(os.path.join(FEATURES_DIR, fn)).tocsr()
              for name, fn in BLOCK_FILES.items()}

    with open(os.path.join(FEATURES_DIR, 'album_ids.pkl'), 'rb') as f:
        album_ids = pickle.load(f)
    album_ids = np.asarray(album_ids)
    album_id_to_row = {int(aid): i for i, aid in enumerate(album_ids)}

    # Per-block per-album sum of squares: ||x_b||^2 for every album.
    # Combined under weights w as sqrt(sum_b w_b^2 * ssq_b) — no full-matrix rebuild needed.
    ssq = {name: np.asarray(X.multiply(X).sum(axis=1)).ravel().astype(np.float64)
           for name, X in blocks.items()}

    return blocks, album_ids, album_id_to_row, ssq

@st.cache_resource
def load_lookup():
    return (
        pd.read_parquet(os.path.join(DATA_DIR, 'mb_album_artists.parquet'),
                        columns=['album_id', 'album_name', 'artist_name'])
        .drop_duplicates(subset='album_id')
        .set_index('album_id')
    )

# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def search_artist(name, lookup):
    mask = lookup['artist_name'].str.contains(name, case=False, na=False)
    return lookup[mask]

def weighted_cosine(row, weights, blocks, ssq, n_albums):
    """Cosine of the seed album row against every album, under per-block weights.

    numerator   = sum_b w_b^2 * (X_b @ q_b)
    album norms = sqrt(sum_b w_b^2 * ssq_b)
    query norm  = sqrt(sum_b w_b^2 * ssq_b[row])
    """
    num            = np.zeros(n_albums, dtype=np.float64)
    album_norm_sq  = np.zeros(n_albums, dtype=np.float64)
    query_norm_sq  = 0.0

    for name, X in blocks.items():
        wb2 = weights[name] ** 2
        if wb2 == 0.0:
            continue
        q = X.getrow(row)                                   # 1 x cols
        num += wb2 * np.asarray(X.dot(q.T).todense()).ravel()
        album_norm_sq += wb2 * ssq[name]
        query_norm_sq += wb2 * ssq[name][row]

    if query_norm_sq == 0.0:
        return None  # seed album has no signal under the current weights

    denom = np.sqrt(album_norm_sq) * np.sqrt(query_norm_sq)
    with np.errstate(divide='ignore', invalid='ignore'):
        cosine = np.where(denom > 0, num / denom, -np.inf)
    return cosine

def recommend(album_id, n, weights, blocks, album_ids, album_id_to_row, ssq, lookup):
    if album_id not in album_id_to_row:
        return None
    row = album_id_to_row[album_id]
    n_albums = len(album_ids)

    cosine = weighted_cosine(row, weights, blocks, ssq, n_albums)
    if cosine is None:
        return None

    cosine[row] = -np.inf  # exclude the seed itself

    # Candidate pool large enough to absorb same-artist exclusions
    pool = min(n_albums, n * 50)
    cand = np.argpartition(-cosine, pool - 1)[:pool]
    cand = cand[np.argsort(-cosine[cand])]

    input_artist = lookup.loc[album_id, 'artist_name'] if album_id in lookup.index else None

    results = []
    for idx in cand:
        if not np.isfinite(cosine[idx]):
            continue
        aid = int(album_ids[idx])
        row_data = lookup.loc[aid] if aid in lookup.index else {'album_name': None, 'artist_name': None}
        # Skip Various-Artists releases (samplers/compilations) — they have no single
        # artist, so they aren't actionable recommendations in an artist→album tool.
        if pd.isna(row_data['artist_name']):
            continue
        if input_artist and row_data['artist_name'] == input_artist:
            continue
        results.append({
            'Album':      row_data['album_name'],
            'Artist':     row_data['artist_name'],
            'Similarity': round(float(cosine[idx]), 4),
            'album_id':   aid,
        })
        if len(results) == n:
            break

    return pd.DataFrame(results)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

st.title("mixtape — tune your mix")

blocks, album_ids, album_id_to_row, ssq = load_blocks()
lookup = load_lookup()

# --- Sidebar: feature weight sliders ---
st.sidebar.header("Feature weights")
st.sidebar.caption(
    "Drag a feature up to make it matter more in the recommendations. "
    "Defaults match the trained v3 model."
)
def reset_weights():
    # Runs as a callback before the sliders are rebuilt, so writing to their
    # session-state keys here actually resets the widgets on the next run.
    for name in BLOCK_FILES:
        st.session_state[f"w_{name}"] = DEFAULT_WEIGHTS[name]

st.sidebar.button("Reset to v3 defaults", on_click=reset_weights)

weights = {}
for name in BLOCK_FILES:
    weights[name] = st.sidebar.slider(
        BLOCK_LABELS[name],
        min_value=0.0, max_value=3.0, value=DEFAULT_WEIGHTS[name], step=0.1,
        key=f"w_{name}",
    )

# An album can only be queried if it has signal in a block whose weight is > 0.
# Combined query-norm² under the current weights = sum_b w_b² * ssq_b. Albums
# where this is zero have nothing to match on, so they are hidden from the
# album dropdown to avoid offering albums that would return no recommendations.
combined_ssq = np.zeros(len(album_ids), dtype=np.float64)
for name in BLOCK_FILES:
    w2 = weights[name] ** 2
    if w2:
        combined_ssq += w2 * ssq[name]

def is_queryable(album_id):
    row = album_id_to_row.get(int(album_id))
    return row is not None and combined_ssq[row] > 0

# --- Main: artist → album → recommendations ---
artist_query = st.text_input("Tell us your favourite artist")

if artist_query:
    matches = search_artist(artist_query, lookup)

    if matches.empty:
        st.warning("No artists found. Try a different name.")
    else:
        artists = matches['artist_name'].dropna().unique()
        selected_artist = st.selectbox("Select artist", sorted(artists))

        artist_albums = matches[matches['artist_name'] == selected_artist]
        album_options = {
            row['album_name']: album_id
            for album_id, row in artist_albums.iterrows()
            if is_queryable(album_id)
        }

        if not album_options:
            st.info(
                "No recommendable albums for this artist under the current weights. "
                "Try raising more sliders — sparser features (ratings, record label) "
                "cover far fewer albums."
            )
        else:
            selected_album_name = st.selectbox("Select album", sorted(album_options.keys()))

            if selected_album_name:
                album_id = album_options[selected_album_name]

                if all(w == 0.0 for w in weights.values()):
                    st.warning("All feature weights are zero — raise at least one slider.")
                else:
                    recs = recommend(album_id, 10, weights, blocks,
                                     album_ids, album_id_to_row, ssq, lookup)

                    if recs is None or recs.empty:
                        st.info("No recommendations available for this album.")
                    else:
                        st.subheader("You might also like")
                        active = " · ".join(
                            f"{BLOCK_LABELS[k]} {weights[k]:g}"
                            for k in BLOCK_FILES if weights[k] > 0
                        )
                        st.caption(f"Weights — {active}")
                        st.dataframe(
                            recs[['Album', 'Artist', 'Similarity']],
                            use_container_width=True, hide_index=True,
                        )
