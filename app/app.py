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
def load_model():
    model               = joblib.load(os.path.join(DATA_DIR, 'model/knn_model.joblib'))
    X_knn_norm          = load_npz(os.path.join(DATA_DIR, 'model/X_knn_norm.npz'))
    album_ids_annotated = np.load(os.path.join(DATA_DIR, 'model/album_ids_annotated.npy'), allow_pickle=True)
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
            'Album':  row_data['album_name'],
            'Artist': row_data['artist_name'],
        })
        if len(results) == n:
            break

    return pd.DataFrame(results)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

st.title("mixtape")

model, X_knn_norm, album_ids_annotated, album_id_to_row = load_model()
lookup = load_lookup()

artist_query = st.text_input("Tell us your favourite artist")

if artist_query:
    matches = search_artist(artist_query, lookup)

    if matches.empty:
        st.warning("No artists found. Try a different name.")
    else:
        artists = matches['artist_name'].dropna().unique()
        selected_artist = st.selectbox("Select artist", sorted(artists))

        artist_albums = matches[
            (matches['artist_name'] == selected_artist) &
            (matches.index.isin(album_id_to_row))
        ]
        album_options = {row['album_name']: album_id for album_id, row in artist_albums.iterrows()}

        if not album_options:
            st.info("No recommendable albums found for this artist.")
        else:
            selected_album_name = st.selectbox("Select album", sorted(album_options.keys()))

            if selected_album_name:
                album_id = album_options[selected_album_name]
                recs = recommend(album_id, 10, model, X_knn_norm, album_ids_annotated, album_id_to_row, lookup)

                if recs is None or recs.empty:
                    st.info("No recommendations available for this album.")
                else:
                    st.subheader("You might also like")
                    st.dataframe(recs, use_container_width=True, hide_index=True)
