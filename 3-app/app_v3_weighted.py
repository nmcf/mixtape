import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import streamlit as st
import pandas as pd
import numpy as np
from scipy.sparse import load_npz
import pickle
import streamlit.components.v1 as components
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
import functools

DATA_DIR     = os.path.join(os.path.dirname(__file__), '..', 'data')
FEATURES_DIR = os.path.join(DATA_DIR, 'features')

# The v3 feature blocks + Last.fm popularity block.
# Defaults match 12-knn-v3-training.ipynb; popularity starts at 4 (noticeable but not dominant).
_LASTFM_FILE = os.path.join(FEATURES_DIR, 'album_lastfm_popularity_matrix.npz')
_LASTFM_AVAILABLE = os.path.exists(_LASTFM_FILE)

# All feature matrices loaded — ratings is always loaded but has no knob.
BLOCK_FILES = {
    'genre':        'album_genre_matrix.npz',
    'ratings':      'album_ratings_matrix.npz',   # hidden — synced to popularity
    'record_label': 'album_record_label_matrix.npz',
    'track_stats':  'album_track_stats_matrix.npz',
    'country':      'album_country_matrix.npz',
    **({'popularity': 'album_lastfm_popularity_matrix.npz'} if _LASTFM_AVAILABLE else {}),
}

# Knob blocks — ratings excluded (no knob shown for it).
KNOB_BLOCKS = {k: v for k, v in BLOCK_FILES.items() if k != 'ratings'}

BLOCK_LABELS = {
    'genre':        'Genre',
    'record_label': 'Record<br>Label',
    'track_stats':  'Track<br>Stats',
    'country':      'Country',
    'popularity':   'Popularity',
}
# Dial range is 0-11. Weight = dial / 11 * 2.0  (0 → 0.0 off, 11 → 2.0 max).
# Defaults mirror the original training weights:
#   Medium (1.0)  ≈ dial 6,  Low (0.3) ≈ dial 2
DEFAULT_DIALS = {
    'genre':        6,
    'record_label': 6,
    'country':      2,   # downweighted (matches v3 training)
    'track_stats':  6,
    'popularity':   4,   # Last.fm listeners/scrobbles — moderate default
}

def dial_to_weight(d):
    return round(d / 11 * 2.0, 4)

_COMPONENT_DIR = os.path.join(os.path.dirname(__file__), "knob_component")
_COMPONENT_PORT = 8502

def _start_component_server():
    handler = functools.partial(SimpleHTTPRequestHandler, directory=_COMPONENT_DIR)
    try:
        server = HTTPServer(("localhost", _COMPONENT_PORT), handler)
        server.serve_forever()
    except OSError:
        pass  # port already in use — server already running

_server_thread = threading.Thread(target=_start_component_server, daemon=True)
_server_thread.start()

_knob_component = components.declare_component(
    "knob_panel",
    url=f"http://localhost:{_COMPONENT_PORT}",
)

# Guitar pickup-style blade switch, served from the same component dir.
_switch_component = components.declare_component(
    "blade_switch",
    url=f"http://localhost:{_COMPONENT_PORT}/switch.html",
)

def blade_switch(title, options, default, key):
    """Tele/Strat blade-switch selector. Returns the chosen option string.

    The component is the single source of truth: keyed by `key`, Streamlit
    persists its last emitted value across reruns. `value` seeds the blade only
    at the iframe's first render (it ignores inbound renders afterwards), and
    `default` is returned until the first interaction. No session_state mirror,
    so each switch is fully independent of the knobs and of the other switch."""
    ret = _switch_component(
        title=title, options=options, value=default, default=default, key=key,
    )
    return ret if ret in options else default

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

@st.cache_resource
def load_flag_ids(filename):
    """Set of album_ids flagged with a given MusicBrainz secondary type.
    Exported by the matching queries/*_flag_duckdb.sql — an exact schema
    lookup, far more reliable than guessing from the album name."""
    df = pd.read_parquet(os.path.join(DATA_DIR, filename), columns=['album_id'])
    return set(df['album_id'].astype(int))

# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def filter_by_flag(df, mode, flag_ids, include_label):
    """Keep flagged-only or unflagged-only rows. mode == 'Both' keeps everything;
    mode == include_label keeps flagged rows; any other value keeps the rest.

    album_id is taken from an 'album_id' column if present, otherwise from the
    index (the lookup table is indexed by album_id)."""
    if mode == 'Both':
        return df
    aid = df['album_id'] if 'album_id' in df.columns else df.index
    mask = aid.astype(int).isin(flag_ids)
    return df[mask] if mode == include_label else df[~mask]

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
            'Match':      round(float(cosine[idx]) * 100, 1),
            'album_id':   aid,
        })
        if len(results) == n:
            break

    return pd.DataFrame(results)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

st.title("Mixtape — Dial in Your Sound")

blocks, album_ids, album_id_to_row, ssq = load_blocks()
lookup = load_lookup()
live_ids = load_flag_ids('mb_album_live_flag.parquet')
compilation_ids = load_flag_ids('mb_album_compilation_flag.parquet')

# --- Sidebar: feature weight knobs ---
st.sidebar.header("Tune your sound")
st.sidebar.caption("Set the balance to find your sound")

if not _LASTFM_AVAILABLE:
    st.sidebar.info(
        "💿 **Popularity knob unavailable** — run notebook "
        "`2-Prototyping/13-feature-lastfm-popularity.ipynb` first "
        "to add Last.fm listener/scrobble data.",
        icon="ℹ️",
    )

def reset_weights():
    # Flip the nonce only. The knob component watches reset_nonce and, when it
    # changes, snaps every dial back to its default AND re-emits — so `result`
    # (the source of truth) becomes the defaults too. No dial state is mirrored
    # in session_state, so nothing stale can be written back afterwards.
    st.session_state["knob_reset_flag"] = not st.session_state.get("knob_reset_flag", False)

st.sidebar.button("Reset Defaults", on_click=reset_weights)

# Seed each knob's `value` from its last emitted value (Streamlit persists the
# component's return under its key). This way, if Streamlit remounts the iframe
# on a rerun, it re-initialises to the user's current settings rather than
# snapping to defaults. `defaultValue` is carried separately and used by the
# iframe only on a reset (nonce change).
_prev = st.session_state.get("knob_panel") or {}
def _dial(name):
    try:
        return int(_prev.get(name, DEFAULT_DIALS[name]))
    except (TypeError, ValueError):
        return DEFAULT_DIALS[name]

# ratings is not in DEFAULT_DIALS (no knob) — safe to skip in _dial

knob_defs = [
    {"id": name, "label": BLOCK_LABELS[name],
     "value": _dial(name), "defaultValue": DEFAULT_DIALS[name]}
    for name in KNOB_BLOCKS
]

with st.sidebar:
    # 5 knobs when no popularity, 5 knobs when popularity present (ratings removed)
    _knob_height = 280
    result = _knob_component(
        knobs=knob_defs, key="knob_panel", height=_knob_height,
        reset_nonce=st.session_state.get("knob_reset_flag", False),
        default={name: DEFAULT_DIALS[name] for name in KNOB_BLOCKS},
    )

with st.sidebar:
    _sw_col1, _sw_col2 = st.columns(2)
    with _sw_col1:
        live_mode = blade_switch(
            "Live Albums", ["Live", "Both", "Studio"], "Both", key="live_switch")
    with _sw_col2:
        hits_mode = blade_switch(
            "Greatest Hits", ["Collections", "Both", "Albums"], "Both", key="hits_switch")

# `result` is the dict the knob component last emitted (persisted by key across
# reruns); falls back to the `default` above before the first render.
current_dials = {name: int(result.get(name, DEFAULT_DIALS[name])) for name in KNOB_BLOCKS}
weights = {name: dial_to_weight(current_dials[name]) for name in KNOB_BLOCKS}

# Ratings has no knob — its weight is synced to popularity.
# If popularity is unavailable, fall back to a fixed medium weight (dial 6 ≈ 1.09).
if _LASTFM_AVAILABLE:
    weights['ratings'] = weights['popularity']
else:
    weights['ratings'] = dial_to_weight(6)

# An album can only be queried if it has signal in a block whose weight is > 0.
# Combined query-norm² under the current weights = sum_b w_b² * ssq_b. Albums
# where this is zero have nothing to match on, so they are hidden from the
# album dropdown to avoid offering albums that would return no recommendations.
combined_ssq = np.zeros(len(album_ids), dtype=np.float64)
for name in BLOCK_FILES:   # includes ratings
    w2 = weights[name] ** 2
    if w2:
        combined_ssq += w2 * ssq[name]

def is_queryable(album_id):
    row = album_id_to_row.get(int(album_id))
    return row is not None and combined_ssq[row] > 0

# --- Main: artist → album → recommendations ---
artist_query = st.text_input("Set the Tone — Name an Artist")

if artist_query:
    matches = search_artist(artist_query, lookup)

    if matches.empty:
        st.warning("No artists found. Try a different name.")
    else:
        artists = matches['artist_name'].dropna().unique()
        selected_artist = st.selectbox("Pick the Artist", sorted(artists))

        artist_albums = matches[matches['artist_name'] == selected_artist]
        artist_albums = filter_by_flag(artist_albums, live_mode, live_ids, 'Live')
        artist_albums = filter_by_flag(artist_albums, hits_mode, compilation_ids, 'Collections')
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
            selected_album_name = st.selectbox("Pick a Starting Album", sorted(album_options.keys()))

            if selected_album_name:
                album_id = album_options[selected_album_name]

                if all(w == 0.0 for w in weights.values()):
                    st.warning("All knobs are at zero — turn at least one up.")
                else:
                    recs = recommend(album_id, 10, weights, blocks,
                                     album_ids, album_id_to_row, ssq, lookup)

                    if recs is not None and not recs.empty:
                        recs = filter_by_flag(recs, live_mode, live_ids, 'Live')
                        recs = filter_by_flag(recs, hits_mode, compilation_ids, 'Collections')

                    if recs is None or recs.empty:
                        st.info("No recommendations available for this album.")
                    else:
                        st.subheader("Checkout these albums")
                        active = " · ".join(
                            f"{BLOCK_LABELS[k].replace('<br>', ' ')}: {current_dials[k]}"
                            for k in KNOB_BLOCKS if weights[k] > 0
                        )
                        st.caption(f"EQ — {active}")
                        st.dataframe(
                            recs[['Album', 'Artist', 'Match']],
                            use_container_width=True, hide_index=True,
                            column_config={
                                'Album':  st.column_config.TextColumn(width='medium'),
                                'Artist': st.column_config.TextColumn(width='medium'),
                                'Match':  st.column_config.NumberColumn(
                                    width=35, format='%.1f%%'
                                ),
                            },
                        )
