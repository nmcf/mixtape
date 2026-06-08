"""Shared configuration for the Mixtape Streamlit app."""

import os

HERE         = os.path.dirname(os.path.abspath(__file__))
DATA_DIR     = os.path.join(HERE, '..', 'data')
FEATURES_DIR = os.path.join(DATA_DIR, 'features')

# ---------------------------------------------------------------------------
# Feature blocks (five sparse matrices + their metadata)
# ---------------------------------------------------------------------------
BLOCK_FILES = {
    'genre':        'album_genre_matrix.npz',
    'record_label': 'album_record_label_matrix.npz',
    'ratings':      'album_ratings_matrix.npz',
    'country':      'album_country_matrix.npz',
    'track_stats':  'album_track_stats_matrix.npz',
}
LEVEL_OPTIONS  = ['Off', 'Low', 'Medium', 'High']
WEIGHT_LEVELS  = {'Off': 0.0, 'Low': 0.3, 'Medium': 1.0, 'High': 2.0}
DEFAULT_LEVELS = {
    'genre':        'Medium',
    'record_label': 'Medium',
    'ratings':      'Medium',
    'country':      'Low',
    'track_stats':  'Medium',
}
BLOCK_LABELS = {
    'genre':        'Genre',
    'record_label': 'Record Label',
    'ratings':      'Ratings',
    'country':      'Country',
    'track_stats':  'Track Stats',
}
BLOCK_BANDS = {
    'genre':        '88.1',
    'record_label': '94.7',
    'ratings':      '101.5',
    'country':      '105.3',
    'track_stats':  '108.9',
}

# ---------------------------------------------------------------------------
# Presets — one-click recommendation profiles
# ---------------------------------------------------------------------------
PRESETS = {
    'Full Mix':              {'genre': 'Medium', 'record_label': 'Medium', 'ratings': 'Medium',
                              'country': 'Low',  'track_stats': 'Medium'},
    'Genre Purist':          {'genre': 'High',   'record_label': 'Off',    'ratings': 'Off',
                              'country': 'Off',  'track_stats': 'Off'},
    'Same Vibe, New Artist': {'genre': 'High',   'record_label': 'Medium', 'ratings': 'Off',
                              'country': 'Off',  'track_stats': 'Medium'},
    'Local Sound':           {'genre': 'Medium', 'record_label': 'Off',    'ratings': 'Off',
                              'country': 'High', 'track_stats': 'Off'},
    "Critics' Pick":         {'genre': 'Low',    'record_label': 'Off',    'ratings': 'High',
                              'country': 'Off',  'track_stats': 'Off'},
}
PRESET_DESCRIPTIONS = {
    'Full Mix':              'Balanced blend of all features — the default starting point.',
    'Genre Purist':          'Match by musical style only — ignore labels, ratings, geography.',
    'Same Vibe, New Artist': 'Similar sound and production style, across different artists.',
    'Local Sound':           'Prioritise albums from the same country or region.',
    "Critics' Pick":         'Find albums with a similar critical reception.',
}
PRESET_NAMES = list(PRESETS.keys())

# ---------------------------------------------------------------------------
# Explore — popular tags for genre browsing
# ---------------------------------------------------------------------------
EXPLORE_TOP_N_TAGS = 100
EXPLORE_RESULTS    = 20

# ---------------------------------------------------------------------------
# Content filters — Live Albums / Greatest Hits faders
# ---------------------------------------------------------------------------
# Each fader has three positions. Default = exclude (cleanest results).
LIVE_OPTIONS = ['STUDIO', 'BOTH', 'LIVE']      # STUDIO=exclude live, LIVE=only live
COMP_OPTIONS = ['ALBUMS', 'BOTH', 'HITS']      # ALBUMS=exclude comp, HITS=only comp
DEFAULT_LIVE = 'STUDIO'
DEFAULT_COMP = 'ALBUMS'
SECONDARY_TYPE_FILE = 'mb_album_secondary_type.parquet'
