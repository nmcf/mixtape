"""
generate_feature_charts.py

Regenerates all feature-matrix diagnostic charts into this folder
(2-Prototyping/feature_charts/). Run from the project root:

    source env/bin/activate
    python 2-Prototyping/feature_charts/generate_feature_charts.py

Charts produced:
  - sparse_features_structural_analysis.png   v1 blocks (tags, labels, artist tags) — built by notebook 01
  - genre_country_structural_analysis.png      v2/v3 additions (genre, country, record_label)
  - track_stats_distributions.png              the 12 min-max-scaled track-stat columns
  - model_feature_comparison.png               feature counts + indexed albums per model
"""

import os
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.sparse import load_npz

# Resolve paths relative to the project root regardless of where this is run from
HERE      = os.path.dirname(os.path.abspath(__file__))
ROOT      = os.path.abspath(os.path.join(HERE, '..', '..'))
FEATURES  = os.path.join(ROOT, 'data', 'features')
OUT       = HERE

sns.set_theme(style="whitegrid")

# Consistent colour per feature block
C = {
    'genre':       '#4A90E2',
    'country':     '#E056FD',
    'record':      '#10AC84',
    'track':       '#F39C12',
    'v1':          '#4A90E2',
    'v2':          '#E056FD',
    'v3':          '#10AC84',
}


def structural_pair(ax_l, ax_r, X, name, colour, row_bins, row_xlim):
    """Profile-complexity histogram (left) + long-tail popularity curve (right)."""
    per_row = X.getnnz(axis=1)
    sns.histplot(per_row, bins=row_bins, ax=ax_l, color=colour, kde=True)
    ax_l.set_title(f'{name}: Profile Complexity', fontsize=12, weight='bold')
    ax_l.set_xlabel('Non-zero features per album')
    ax_l.set_ylabel('Count of albums')
    ax_l.set_xlim(*row_xlim)

    popularity = np.sort(X.getnnz(axis=0))[::-1]
    ax_r.plot(popularity, color=colour, linewidth=2.5)
    ax_r.fill_between(range(len(popularity)), popularity, color=colour, alpha=0.25)
    ax_r.set_yscale('log')
    ax_r.set_title(f'{name}: Long-Tail Feature Popularity', fontsize=12, weight='bold')
    ax_r.set_xlabel('Feature index (sorted by global popularity)')
    ax_r.set_ylabel('Albums sharing feature (log scale)')


def chart_genre_country_recordlabel():
    X_genre   = load_npz(os.path.join(FEATURES, 'album_genre_matrix.npz'))
    X_country = load_npz(os.path.join(FEATURES, 'album_country_matrix.npz'))
    X_record  = load_npz(os.path.join(FEATURES, 'album_record_label_matrix.npz'))

    fig, axes = plt.subplots(3, 2, figsize=(16, 18))
    structural_pair(axes[0, 0], axes[0, 1], X_genre,   'Genre Tags (album+artist+label)', C['genre'],   range(0, 35), (0, 30))
    structural_pair(axes[1, 0], axes[1, 1], X_country, 'Artist Country',                  C['country'], range(0, 5),  (0, 4))
    structural_pair(axes[2, 0], axes[2, 1], X_record,  'Record Label (identity+type)',    C['record'],  range(0, 10), (0, 8))
    plt.tight_layout()
    out = os.path.join(OUT, 'genre_country_structural_analysis.png')
    plt.savefig(out, dpi=300)
    plt.close(fig)
    print(f'Saved: {out}')


def chart_track_stats():
    X = load_npz(os.path.join(FEATURES, 'album_track_stats_matrix.npz')).tocsc()
    cols = [
        'first_release_year', 'medium_count', 'track_count', 'total_length_ms',
        'mean_length_ms', 'median_length_ms', 'stddev_length_ms', 'min_length_ms',
        'max_length_ms', 'p25_length_ms', 'p75_length_ms', 'iqr_length_ms',
    ]
    fig, axes = plt.subplots(3, 4, figsize=(20, 12))
    for i, (ax, label) in enumerate(zip(axes.ravel(), cols)):
        # Only the non-zero entries carry signal (matrix dropped explicit zeros)
        vals = X[:, i].data
        sns.histplot(vals, bins=40, ax=ax, color=C['track'])
        ax.set_title(label, fontsize=11, weight='bold')
        ax.set_xlabel('Min-max scaled value [0, 1]')
        ax.set_ylabel('Count (non-zero)')
        ax.set_xlim(0, 1)
    fig.suptitle('Album Track-Stat Features — scaled value distributions',
                 fontsize=15, weight='bold', y=1.01)
    plt.tight_layout()
    out = os.path.join(OUT, 'track_stats_distributions.png')
    plt.savefig(out, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved: {out}')


def chart_model_comparison():
    # Pulled from the trained model matrices
    models = ['v1', 'v2', 'v3']
    norms = {
        'v1': load_npz(os.path.join(ROOT, 'data', 'model',    'X_knn_norm.npz')),
        'v2': load_npz(os.path.join(ROOT, 'data', 'model_v2', 'X_knn_norm_v2.npz')),
        'v3': load_npz(os.path.join(ROOT, 'data', 'model_v3', 'X_knn_norm_v3.npz')),
    }
    n_features = [norms[m].shape[1] for m in models]
    n_albums   = [norms[m].shape[0] for m in models]
    colours    = [C[m] for m in models]

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    b1 = axes[0].bar(models, n_features, color=colours)
    axes[0].set_title('Features per model (after pruning)', fontsize=13, weight='bold')
    axes[0].set_ylabel('Number of feature columns')
    axes[0].bar_label(b1, fmt='{:,.0f}', padding=3)

    b2 = axes[1].bar(models, n_albums, color=colours)
    axes[1].set_title('Albums indexed per model', fontsize=13, weight='bold')
    axes[1].set_ylabel('Number of albums')
    axes[1].bar_label(b2, fmt='{:,.0f}', padding=3)

    plt.tight_layout()
    out = os.path.join(OUT, 'model_feature_comparison.png')
    plt.savefig(out, dpi=300)
    plt.close(fig)
    print(f'Saved: {out}')


if __name__ == '__main__':
    chart_genre_country_recordlabel()
    chart_track_stats()
    chart_model_comparison()
    print('All feature charts regenerated.')
