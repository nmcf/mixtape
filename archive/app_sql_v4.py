import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import streamlit as st

# Must be the very first Streamlit call
st.set_page_config(layout='wide', page_title='mixtape')

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
def load_model_v4():
    model               = joblib.load(os.path.join(DATA_DIR, 'model_v4/knn_model_v4.joblib'))
    X_knn_norm          = load_npz(os.path.join(DATA_DIR, 'model_v4/X_knn_norm_v4.npz'))
    album_ids_annotated = np.load(os.path.join(DATA_DIR, 'model_v4/album_ids_annotated_v4.npy'), allow_pickle=True)
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

def ids_set(recs):
    if recs is not None and not recs.empty:
        return set(recs['album_id'].tolist())
    return set()

def highlight_unique(df, exclusive_ids):
    return [
        'background-color: #fff3cd; color: #1a1714; font-weight: 500;'
        if aid in exclusive_ids else ''
        for aid in df['album_id']
    ]

def render_results(recs, label, exclusive_ids):
    st.markdown(f'**{label}**')
    if recs is None or recs.empty:
        st.info('No results for this album.')
    else:
        st.dataframe(
            recs[['Album', 'Artist']].style.apply(
                lambda _: highlight_unique(recs, exclusive_ids),
                axis=0, subset=pd.IndexSlice[:, 'Album']
            ),
            use_container_width=True,
            hide_index=True,
        )

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

st.title('mixtape')

model_v1, X_v1, ids_v1, id2row_v1 = load_model_v1()
model_v2, X_v2, ids_v2, id2row_v2 = load_model_v2()
model_v4, X_v4, ids_v4, id2row_v4 = load_model_v4()
lookup = load_lookup()

artist_query = st.text_input("Tell us your favourite artist")

if artist_query:
    matches = search_artist(artist_query, lookup)

    if matches.empty:
        st.warning('No artists found. Try a different name.')
    else:
        artists = matches['artist_name'].dropna().unique()
        selected_artist = st.selectbox('Select artist', sorted(artists))

        artist_albums = matches[
            (matches['artist_name'] == selected_artist) &
            (matches.index.isin(id2row_v1) |
             matches.index.isin(id2row_v2) |
             matches.index.isin(id2row_v4))
        ]
        album_options = {row['album_name']: album_id for album_id, row in artist_albums.iterrows()}

        if not album_options:
            st.info('No recommendable albums found for this artist.')
        else:
            selected_album_name = st.selectbox('Select album', sorted(album_options.keys()))

            if selected_album_name:
                album_id = album_options[selected_album_name]

                recs_v1 = recommend(album_id, 10, model_v1, X_v1, ids_v1, id2row_v1, lookup)
                recs_v2 = recommend(album_id, 10, model_v2, X_v2, ids_v2, id2row_v2, lookup)
                recs_v4 = recommend(album_id, 10, model_v4, X_v4, ids_v4, id2row_v4, lookup)

                if all(r is None or r.empty for r in [recs_v1, recs_v2, recs_v4]):
                    st.info('No recommendations available for this album.')
                else:
                    st.subheader('You might also like')

                    s1, s2, s4 = ids_set(recs_v1), ids_set(recs_v2), ids_set(recs_v4)
                    shared_ids = s1 & s2 & s4
                    only_v1   = s1 - s2 - s4
                    only_v2   = s2 - s1 - s4
                    only_v4   = s4 - s1 - s2

                    st.markdown(
                        "<span style='background-color:#fff3cd;padding:2px 8px;"
                        "border-radius:3px;font-size:0.85em;color:#1a1714;'>highlighted</span>"
                        "&nbsp; = exclusive to this model &nbsp;|&nbsp;"
                        "<span style='font-size:0.85em;'>plain</span> = appears in at least one other",
                        unsafe_allow_html=True
                    )
                    st.write('')

                    col1, col2, col3 = st.columns(3)

                    with col1:
                        render_results(recs_v1, 'Baseline (tags · labels · ratings)', only_v1)
                    with col2:
                        render_results(recs_v2, 'v2 (+ country · track stats)', only_v2)
                    with col3:
                        render_results(recs_v4, 'v4 (+ year · contributors · instruments)', only_v4)

                    st.caption(
                        f'{len(shared_ids)} in all three · '
                        f'{len(only_v1)} only in baseline · '
                        f'{len(only_v2)} only in v2 · '
                        f'{len(only_v4)} only in v4'
                    )
