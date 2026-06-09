"""Shared configuration for the Mixtape Streamlit app."""

import os

HERE         = os.path.dirname(os.path.abspath(__file__))
DATA_DIR     = os.path.join(HERE, '..', 'data')
FEATURES_DIR = os.path.join(DATA_DIR, 'features')

# ---------------------------------------------------------------------------
# Popularity block — conditional on file existence
# ---------------------------------------------------------------------------
_LASTFM_FILE     = os.path.join(FEATURES_DIR, 'album_lastfm_popularity_matrix.npz')
LASTFM_AVAILABLE = os.path.exists(_LASTFM_FILE)

# ---------------------------------------------------------------------------
# Feature blocks
# ---------------------------------------------------------------------------
# All matrices are always loaded.  Ratings has no knob — its weight is synced
# to the Popularity dial at runtime (both are engagement signals).
BLOCK_FILES = {
    'genre':        'album_genre_matrix.npz',
    'record_label': 'album_record_label_matrix.npz',
    'ratings':      'album_ratings_matrix.npz',       # hidden — synced to popularity
    'country':      'album_country_matrix.npz',
    'track_stats':  'album_track_stats_matrix.npz',
    'era':          'album_temporal_matrix.npz',      # 11-col: era one-hot + continuous year
    **({'popularity': 'album_lastfm_popularity_matrix.npz'} if LASTFM_AVAILABLE else {}),
}

# Blocks shown as knobs — ratings excluded.
KNOB_BLOCKS = [k for k in BLOCK_FILES if k != 'ratings']

BLOCK_LABELS = {
    'genre':        'Genre',
    'record_label': 'Record<br>Label',
    'country':      'Country',
    'track_stats':  'Track<br>Stats',
    'era':          'Era',
    'popularity':   'Popularity',
}

BLOCK_BANDS = {
    'genre':        '88.1',
    'record_label': '94.7',
    'country':      '98.3',
    'track_stats':  '101.5',
    'era':          '105.3',
    'popularity':   '108.9',
}

# ---------------------------------------------------------------------------
# Weight ↔ dial conversion
# ---------------------------------------------------------------------------
# Dials run 0–11 (guitar-amp aesthetic).  Linear mapping: weight = dial/11 * 2.0
# Presets store exact float weights; the dial is derived by rounding for display
# only.  Scoring always uses the exact float.

DIAL_MAX   = 11
WEIGHT_MAX = 2.0


def dial_to_weight(d: int) -> float:
    """Map a dial position [0, 11] to a weight [0.0, 2.0]."""
    return round(max(0, min(DIAL_MAX, int(d))) / DIAL_MAX * WEIGHT_MAX, 4)


def weight_to_dial(w: float) -> int:
    """Map an exact float weight to the nearest dial position [0, 11]."""
    return max(0, min(DIAL_MAX, round(float(w) / WEIGHT_MAX * DIAL_MAX)))


# ---------------------------------------------------------------------------
# Default weights  (mirror v3 training weights)
# ---------------------------------------------------------------------------
# genre / record_label / track_stats at 1.09  → dial 6
# country at 0.36                             → dial 2  (downweighted — binary signal)
# era at 0.73                                 → dial 4
# popularity at 0.73                          → dial 4
DEFAULT_WEIGHTS = {
    'genre':        1.09,
    'record_label': 1.09,
    'country':      0.36,
    'track_stats':  1.09,
    'era':          0.73,
    'popularity':   0.73,
}

# ---------------------------------------------------------------------------
# Presets — exact float weights; dial display derived via weight_to_dial()
# ---------------------------------------------------------------------------
PRESETS = {
    'Full Mix': {
        'genre': 1.09, 'record_label': 1.09, 'country': 0.36,
        'track_stats': 1.09, 'era': 0.73, 'popularity': 0.73,
    },
    'Genre Purist': {
        'genre': 2.0,  'record_label': 0.0,  'country': 0.0,
        'track_stats': 0.0,  'era': 0.0,   'popularity': 0.0,
    },
    'Same Vibe, New Artist': {
        'genre': 2.0,  'record_label': 1.09, 'country': 0.0,
        'track_stats': 1.09, 'era': 1.09,  'popularity': 0.0,
    },
    'Local Sound': {
        'genre': 1.09, 'record_label': 0.0,  'country': 2.0,
        'track_stats': 0.0,  'era': 0.0,   'popularity': 0.0,
    },
    "Critics' Pick": {
        'genre': 0.36, 'record_label': 0.0,  'country': 0.0,
        'track_stats': 0.0,  'era': 0.0,   'popularity': 2.0,
    },
}
PRESET_DESCRIPTIONS = {
    'Full Mix':              'Balanced blend of all features — the default starting point.',
    'Genre Purist':          'Match by musical style only — ignore labels, ratings, geography.',
    'Same Vibe, New Artist': 'Similar sound and production era, across different artists.',
    'Local Sound':           'Prioritise albums from the same country or region.',
    "Critics' Pick":         'Find albums with similar popularity and critical reception.',
}
PRESET_NAMES = list(PRESETS.keys())

# ---------------------------------------------------------------------------
# Explore settings
# ---------------------------------------------------------------------------
EXPLORE_TOP_N_TAGS = 100
EXPLORE_RESULTS    = 20

# ---------------------------------------------------------------------------
# Content filters
# ---------------------------------------------------------------------------
LIVE_OPTIONS        = ['STUDIO', 'BOTH', 'LIVE']
COMP_OPTIONS        = ['ALBUMS', 'BOTH', 'HITS']
DEFAULT_LIVE        = 'STUDIO'
DEFAULT_COMP        = 'ALBUMS'
SECONDARY_TYPE_FILE = 'mb_album_secondary_type.parquet'
