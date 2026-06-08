import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import streamlit as st
import pandas as pd
import numpy as np
import joblib
from scipy.sparse import load_npz

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')

# ---------------------------------------------------------------------------
# Cached resource loading
# ---------------------------------------------------------------------------

@st.cache_resource
def load_model_v1():
    model               = joblib.load(os.path.join(DATA_DIR, 'model/knn_model.joblib'))
    X_knn_norm          = load_npz(os.path.join(DATA_DIR, 'model/X_knn_norm.npz'))
    album_ids_annotated = np.load(os.path.join(DATA_DIR, 'model/album_ids_annotated.npy'), allow_pickle=True)
    album_id_to_row     = {aid: i for i, aid in enumerate(album_ids_annotated)}
    return model, X_knn_norm, album_ids_annotated, album_id_to_row

@st.cache_resource
def load_model_v2():
    model               = joblib.load(os.path.join(DATA_DIR, 'model_v2/knn_model_v2.joblib'))
    X_knn_norm          = load_npz(os.path.join(DATA_DIR, 'model_v2/X_knn_norm_v2.npz'))
    album_ids_annotated = np.load(os.path.join(DATA_DIR, 'model_v2/album_ids_annotated_v2.npy'), allow_pickle=True)
    album_id_to_row     = {aid: i for i, aid in enumerate(album_ids_annotated)}
    return model, X_knn_norm, album_ids_annotated, album_id_to_row

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

def recommend(album_id, n, model, X_knn_norm, album_ids_annotated, album_id_to_row, lookup):
    if album_id not in album_id_to_row:
        return None

    input_artist = lookup.loc[album_id, 'artist_name'] if album_id in lookup.index else None

    row = album_id_to_row[album_id]
    distances, indices = model.kneighbors(X_knn_norm[row], n_neighbors=n * 5)

    results = []
    for idx, dist in zip(indices[0], distances[0]):
        aid = album_ids_annotated[idx]
        if aid == album_id:
            continue
        row_data = lookup.loc[aid] if aid in lookup.index else {'album_name': None, 'artist_name': None}
        if input_artist and row_data['artist_name'] == input_artist:
            continue
        results.append({
            'Album':    row_data['album_name'],
            'Artist':   row_data['artist_name'],
            'album_id': aid,
        })
        if len(results) == n:
            break

    return pd.DataFrame(results)

def highlight_differences(df, shared_ids):
    """Return a list of CSS style strings — highlight rows whose album_id is NOT in shared_ids."""
    styles = []
    for aid in df['album_id']:
        if aid not in shared_ids:
            styles.append('background-color: #fff3cd; color: #1a1714; font-weight: 500;')
        else:
            styles.append('')
    return styles

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

st.title("mixtape")

model_v1, X_v1, ids_v1, id2row_v1 = load_model_v1()
model_v2, X_v2, ids_v2, id2row_v2 = load_model_v2()
lookup = load_lookup()

artist_query = st.text_input("Tell us your favourite artist")

if artist_query:
    matches = search_artist(artist_query, lookup)

    if matches.empty:
        st.warning("No artists found. Try a different name.")
    else:
        artists = matches['artist_name'].dropna().unique()
        selected_artist = st.selectbox("Select artist", sorted(artists))

        # Use union of both model indices so an album only needs to be in one
        artist_albums = matches[
            (matches['artist_name'] == selected_artist) &
            (matches.index.isin(id2row_v1) | matches.index.isin(id2row_v2))
        ]
        album_options = {row['album_name']: album_id for album_id, row in artist_albums.iterrows()}

        if not album_options:
            st.info("No recommendable albums found for this artist.")
        else:
            selected_album_name = st.selectbox("Select album", sorted(album_options.keys()))

            if selected_album_name:
                album_id = album_options[selected_album_name]

                recs_v1 = recommend(album_id, 10, model_v1, X_v1, ids_v1, id2row_v1, lookup)
                recs_v2 = recommend(album_id, 10, model_v2, X_v2, ids_v2, id2row_v2, lookup)

                if (recs_v1 is None or recs_v1.empty) and (recs_v2 is None or recs_v2.empty):
                    st.info("No recommendations available for this album.")
                else:
                    st.subheader("You might also like")

                    # Compute which album_ids appear in both result sets
                    ids_in_v1   = set(recs_v1['album_id'].tolist()) if recs_v1 is not None and not recs_v1.empty else set()
                    ids_in_v2   = set(recs_v2['album_id'].tolist()) if recs_v2 is not None and not recs_v2.empty else set()
                    shared_ids  = ids_in_v1 & ids_in_v2

                    # Legend
                    st.markdown(
                        "<span style='background-color:#fff3cd;padding:2px 8px;border-radius:3px;"
                        "font-size:0.85em;'>highlighted</span>"
                        "&nbsp; = unique to this model &nbsp;|&nbsp; "
                        "<span style='font-size:0.85em;'>plain</span> = appears in both",
                        unsafe_allow_html=True
                    )
                    st.write("")

                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown("**Baseline model** (tags · labels · ratings)")
                        if recs_v1 is None or recs_v1.empty:
                            st.info("No results from baseline model.")
                        else:
                            display_v1 = recs_v1[['Album', 'Artist']].copy()
                            styled_v1  = display_v1.style.apply(
                                lambda _: highlight_differences(recs_v1, shared_ids),
                                axis=0, subset=pd.IndexSlice[:, 'Album']
                            )
                            st.dataframe(styled_v1, width='stretch', hide_index=True)

                    with col2:
                        st.markdown("**Extended model** (+ country · track stats)")
                        if recs_v2 is None or recs_v2.empty:
                            st.info("No results from extended model.")
                        else:
                            display_v2 = recs_v2[['Album', 'Artist']].copy()
                            styled_v2  = display_v2.style.apply(
                                lambda _: highlight_differences(recs_v2, shared_ids),
                                axis=0, subset=pd.IndexSlice[:, 'Album']
                            )
                            st.dataframe(styled_v2, width='stretch', hide_index=True)

                    # Summary line
                    n_unique_v1 = len(ids_in_v1 - ids_in_v2)
                    n_unique_v2 = len(ids_in_v2 - ids_in_v1)
                    st.caption(
                        f"{len(shared_ids)} album(s) in common · "
                        f"{n_unique_v1} unique to baseline · "
                        f"{n_unique_v2} unique to extended model"
                    )
