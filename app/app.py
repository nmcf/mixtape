"""Mixtape — Album Recommendation App (v7 / modular)

Tabs:
  • Find Similar — pick an artist → album → get cosine-ranked recommendations
  • Explore       — pick genre tags + filters → discover matching albums
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import html as _html

import streamlit as st
import numpy as np
import pandas as pd
from streamlit_searchbox import st_searchbox

from config import (BLOCK_FILES, KNOB_BLOCKS, BLOCK_LABELS,
                    EXPLORE_TOP_N_TAGS, EXPLORE_RESULTS)
from style import get_theme, inject_css, searchbox_styles, patch_searchbox_iframe
from engine import (load_blocks, load_lookup, load_explore_data,
                    load_secondary_types,
                    make_artist_search, recommend, explore_search,
                    get_album_info, per_block_similarity)
from controls import (render_presets, render_auto_tune_buttons,
                      render_controls, render_content_filters, get_weights)

# ═══════════════════════════════════════════════════════════════════════════
# PAGE CONFIG (must be first Streamlit call)
# ═══════════════════════════════════════════════════════════════════════════
st.set_page_config(page_title="Mixtape — Dial in Your Sound", page_icon="🎚️", layout="wide")

# ── Theme + CSS ──
T, THEME = get_theme()
inject_css(T)

# ── Load data ──
blocks, album_ids, album_id_to_row, ssq = load_blocks()
lookup = load_lookup()
explore_data = load_explore_data()   # (tag_options, album_tags_df, album_meta_df, country_options)
sec_types = load_secondary_types()   # {'live': set, 'comp': set} or None

# ── Session state initialised in controls._init_state() (called by render_presets) ──
st.session_state.setdefault('knob_nonce', 0)

# ═══════════════════════════════════════════════════════════════════════════
# HEADER + THEME TOGGLE
# ═══════════════════════════════════════════════════════════════════════════
hcol, tcol = st.columns([5, 1])
with hcol:
    st.markdown("""
    <div style="margin:.1rem 0 .2rem;">
      <h1 style="margin:0;font-family:'DM Serif Display',serif;font-size:2.2rem;line-height:1;color:var(--txt);">
        Mixtape</h1>
    </div>""", unsafe_allow_html=True)
with tcol:
    st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)
    dark = st.toggle("Dark", value=st.session_state['dark'], key="dark_toggle")
    if dark != st.session_state['dark']:
        st.session_state['dark'] = dark
        st.rerun()

st.markdown("<hr style='margin:.8rem 0 1rem;'>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════
st.sidebar.markdown("""
<div style="font-family:'DM Serif Display',serif;font-size:1.4rem;color:var(--txt);margin-bottom:.1rem;">
  Tune your sound</div>
<div style="font-family:'DM Sans',sans-serif;font-size:.8rem;color:var(--dim);margin-bottom:.6rem;">
  Set the balance to find your sound</div>
""", unsafe_allow_html=True)

render_presets()
render_auto_tune_buttons(blocks, ssq, album_id_to_row)
st.sidebar.markdown("<hr style='margin:.2rem 0 .4rem;'>", unsafe_allow_html=True)
render_controls(T)
render_content_filters()
if sec_types is None:
    st.sidebar.warning(
        "Content filters inactive — mb_album_secondary_type.parquet not found. "
        "Run 1-data/06-extract-secondary-type.ipynb to generate it.",
        icon="⚠️",
    )

# ── Derive weights from session state (set by controls) ──
weights = get_weights()

combined_ssq = np.zeros(len(album_ids))
for name in BLOCK_FILES:
    if weights[name] ** 2:
        combined_ssq += weights[name] ** 2 * ssq[name]


def is_queryable(album_id):
    r = album_id_to_row.get(int(album_id))
    return r is not None and combined_ssq[r] > 0


def passes_content_filters(album_id):
    """Apply the Live Albums / Greatest Hits faders — same semantics as recommend()."""
    if sec_types is None:
        return True
    aid = int(album_id)
    live_filter = st.session_state.get('live_filter', 'BOTH')
    comp_filter = st.session_state.get('comp_filter', 'BOTH')
    is_live = aid in sec_types['live']
    is_comp = aid in sec_types['comp']
    if live_filter == 'STUDIO' and is_live:
        return False
    if live_filter == 'LIVE' and not is_live:
        return False
    if comp_filter == 'ALBUMS' and is_comp:
        return False
    if comp_filter == 'HITS' and not is_comp:
        return False
    return True


# ═══════════════════════════════════════════════════════════════════════════
# RESULT RENDERER (shared by both tabs)
# ═══════════════════════════════════════════════════════════════════════════

def render_results_table(recs, title, subtitle="", show_similarity=True):
    """Render a styled results table."""
    if recs is None or recs.empty:
        st.info("No results found.")
        return
    st.markdown(f"""
    <h2 style="margin:1.4rem 0 .1rem;font-family:'DM Serif Display',serif;font-size:1.9rem;
        color:var(--gold);">{title}</h2>
    <div style="font-family:'DM Mono',monospace;font-size:.66rem;color:var(--dim);
        letter-spacing:.05em;margin:.1rem 0 1rem;">{_html.escape(subtitle)}</div>
    """, unsafe_allow_html=True)

    # Determine the score column
    score_col = 'Similarity' if show_similarity and 'Similarity' in recs.columns else 'Match'
    has_score = score_col in recs.columns
    vals = recs[score_col].to_numpy(dtype=float) if has_score else np.ones(len(recs))
    lo, hi = vals.min(), vals.max()
    rng = (hi - lo) or 1.0

    has_tags_matched = 'Tags Matched' in recs.columns

    rows_html = ""
    for i in range(len(recs)):
        row = recs.iloc[i]
        score_val = float(vals[i]) if has_score else 0
        fill = 18 + (score_val - lo) / rng * 82 if has_score else 50

        album = _html.escape(str(row.get('Album', '?')))
        artist = _html.escape(str(row.get('Artist', '?')))
        year = row.get('Year', '')
        year_str = f" · {year}" if year else ""
        extra_info = ""
        if has_tags_matched:
            tm = int(row['Tags Matched'])
            extra_info = (f"<span style='font-family:DM Mono;font-size:.7rem;color:var(--dim);'>"
                          f"{tm} tag{'s' if tm != 1 else ''}</span>")

        score_display = f"{score_val:.4f}" if show_similarity else f"{int(score_val)}%"

        rows_html += f"""
        <div style="display:grid;grid-template-columns:38px 1fr 160px;gap:1rem;align-items:center;
             padding:.85rem .2rem;border-bottom:1px solid var(--rowline);">
          <div style="font-family:'DM Mono';font-size:1.05rem;color:var(--gold-deep);text-align:center;">{i+1:02d}</div>
          <div><div style="font-family:'DM Serif Display',serif;font-size:1.08rem;color:var(--txt);">{album}</div>
               <div style="font-size:.86rem;color:var(--dim);">{artist}{year_str} {extra_info}</div></div>
          <div><div style="text-align:right;font-family:'DM Mono';font-size:.82rem;color:var(--gold);">{score_display}</div>
               <div style="height:6px;border-radius:4px;margin-top:.3rem;background:{T['track_off']};overflow:hidden;">
                 <div style="height:100%;width:{fill:.0f}%;border-radius:4px;
                   background:linear-gradient(90deg,var(--gold-deep),var(--gold-soft));"></div></div></div>
        </div>"""

    st.markdown(f"""
    <div style="border:1px solid var(--line);border-radius:16px;overflow:hidden;
         background:linear-gradient(180deg,var(--panel),var(--bg2));
         box-shadow:0 20px 50px rgba(0,0,0,.18);">
      <div style="display:grid;grid-template-columns:38px 1fr 160px;gap:1rem;padding:.7rem 1rem;
           background:color-mix(in srgb,var(--gold) 8%,transparent);font-family:'DM Mono';
           font-size:.62rem;letter-spacing:.16em;color:var(--gold);">
        <div style="text-align:center;">#</div><div>ALBUM · ARTIST</div>
        <div style="text-align:right;">{'SIMILARITY' if show_similarity else 'MATCH'}</div></div>
      <div style="padding:0 1rem;">{rows_html}</div>
    </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# TABS
# ═══════════════════════════════════════════════════════════════════════════

tab_similar, tab_explore = st.tabs(["🎧  Find Similar", "🔍  Explore"])

# ───────────────────────────────────────────────────────────────────────────
# TAB 1: Find Similar (the original flow)
# ───────────────────────────────────────────────────────────────────────────
with tab_similar:
    st.session_state['seed_album_id'] = None

    # Check if seeded from Explore
    explore_seed = st.session_state.get('explore_seed')

    if explore_seed:
        album_id = explore_seed['album_id']
        st.session_state['seed_album_id'] = album_id
        st.markdown(f"""
        <div style="border-left:3px solid var(--gold);padding:.5rem 0 .5rem .8rem;margin:0 0 .8rem;">
          <div style="font-family:'DM Serif Display',serif;font-size:1.15rem;">{_html.escape(str(explore_seed.get('album_name','?')))}</div>
          <div style="font-size:.8rem;color:var(--dim);">{_html.escape(str(explore_seed.get('artist_name','')))}</div>
          <div style="font-family:DM Mono;font-size:.6rem;color:var(--gold);margin-top:.15rem;">SEEDED FROM EXPLORE</div>
        </div>""", unsafe_allow_html=True)
        if st.button("← Back to search", key="clear_seed"):
            st.session_state.pop('explore_seed', None)
            st.rerun()
    else:
        # Live typeahead — suggestions appear and refine as you type.
        # The searchbox is a sandboxed-iframe component: its built-in label sits
        # on the iframe's fixed dark base-theme background, so we render our own
        # themed label instead. The key stays constant across theme changes so the
        # typed artist / selection survives a light/dark toggle; style_overrides is
        # rebuilt from the active theme T and re-applied in place on each rerun.
        st.markdown("<div class='mixtape-field-label'>Artist</div>", unsafe_allow_html=True)
        selected_artist = st_searchbox(
            make_artist_search(lookup),
            label="",
            placeholder="Start typing an artist…",
            key="artist_search",
            style_overrides=searchbox_styles(T),
        )
        patch_searchbox_iframe()  # transparent iframe body + UI font (see style.py)
        album_id = None
        if selected_artist:
            artist_albums = lookup[lookup['artist_name'] == selected_artist]
            album_options = {row['album_name']: aid
                             for aid, row in artist_albums.iterrows()
                             if is_queryable(aid) and passes_content_filters(aid)}
            if not album_options:
                st.info("No albums match the current weights and content filters. "
                        "Raise more channels or relax the Live/Hits faders.")
            else:
                selected_album_name = st.selectbox("Pick a Starting Album",
                                                   sorted(album_options.keys()))
                if selected_album_name:
                    album_id = album_options[selected_album_name]
                    st.session_state['seed_album_id'] = album_id

    # Render Album Card + Recommendations (shared by both search and explore-seed paths)
    album_id = st.session_state.get('seed_album_id')
    if album_id and not all(w == 0.0 for w in weights.values()):
        # Album Card
        info = get_album_info(album_id, lookup, explore_data)
        parts = [info.get('artist_name', '')]
        if 'year' in info:
            parts.append(str(info['year']))
        if info.get('country'):
            parts.append(info['country'])
        subtitle = ' · '.join(p for p in parts if p)
        tags_str = ' · '.join(info.get('tags', []))

        if not explore_seed:
            st.markdown(f"""
            <div style="border-left:3px solid var(--gold);padding:.5rem 0 .5rem .8rem;margin:.6rem 0 .8rem;">
              <div style="font-family:'DM Serif Display',serif;font-size:1.15rem;">{_html.escape(info.get('album_name','?'))}</div>
              <div style="font-size:.8rem;color:var(--dim);">{_html.escape(subtitle)}</div>
              {f'<div style="font-family:DM Mono;font-size:.6rem;color:var(--gold);margin-top:.15rem;">{_html.escape(tags_str)}</div>' if tags_str else ''}
            </div>""", unsafe_allow_html=True)

        # Recommendations
        recs = recommend(album_id, 10, weights, blocks, album_ids,
                         album_id_to_row, ssq, lookup,
                         sec_types=sec_types,
                         live_filter=st.session_state.get('live_filter', 'BOTH'),
                         comp_filter=st.session_state.get('comp_filter', 'BOTH'))
        active = "  ·  ".join(f"{BLOCK_LABELS[k].replace('<br>', ' ')} {weights[k]:.2f}"
                              for k in KNOB_BLOCKS if weights.get(k, 0) > 0)
        if sec_types is not None:
            filt = (f"FILTERS › {st.session_state.get('live_filter', 'BOTH')} · "
                    f"{st.session_state.get('comp_filter', 'BOTH')}")
        else:
            filt = "FILTERS › OFF (no secondary-type data)"
        render_results_table(recs, "You Might Also Like",
                             f"MIX › {active}   |   {filt}", show_similarity=True)

        # Per-block explanation (expandable, minimal)
        if recs is not None and not recs.empty and album_id in album_id_to_row:
            with st.expander("↳ Why these recommendations?", expanded=False):
                q_row = album_id_to_row[album_id]
                explain_rows = []
                for _, rec in recs.iterrows():
                    rid = rec.get('album_id')
                    if rid and rid in album_id_to_row:
                        sims = per_block_similarity(q_row, album_id_to_row[rid], blocks, ssq)
                        top_reasons = sorted(sims.items(), key=lambda x: -x[1])[:3]
                        reasons = '  '.join(
                            f"<span style='color:var(--gold);'>{BLOCK_LABELS.get(n, n.title())}</span> "
                            f"<span style='color:var(--dim);'>{int(v*100)}%</span>"
                            for n, v in top_reasons if v > 0
                        )
                        explain_rows.append(
                            f"<div style='font-family:DM Mono;font-size:.62rem;padding:.2rem 0;"
                            f"border-bottom:1px solid var(--rowline);'>"
                            f"<span style='color:var(--txt);'>{_html.escape(str(rec['Album'])[:30])}</span>"
                            f"&nbsp;&nbsp;{reasons}</div>"
                        )
                st.markdown(''.join(explain_rows), unsafe_allow_html=True)

    elif album_id and all(w == 0.0 for w in weights.values()):
        st.warning("Every channel is down — raise at least one.")
    elif not explore_seed and not (st.session_state.get('seed_album_id')):
        st.markdown("""
        <div style="padding:1.5rem 0;color:var(--dim);font-size:.9rem;">
          Type an artist above to get started.
        </div>""", unsafe_allow_html=True)


# ───────────────────────────────────────────────────────────────────────────
# TAB 2: Explore (tag-based discovery)
# ───────────────────────────────────────────────────────────────────────────
with tab_explore:
    tag_options, album_tags_df, album_meta_df, country_options = explore_data

    if tag_options is None:
        st.info("Explore requires the tag vocabulary (mb_tag.parquet) in data/raw/ or data/. "
                "Run 1-data/07-extract-tag-area.ipynb to generate it.")
    else:
        st.markdown("""
        <div style="font-family:'DM Serif Display',serif;font-size:1.3rem;color:var(--gold);margin-bottom:.5rem;">
          Explore by Genre & Filters</div>
        <div style="font-family:'DM Mono',monospace;font-size:.66rem;color:var(--dim);margin-bottom:1rem;">
          Pick genres you're in the mood for — optionally narrow by country and decade.</div>
        """, unsafe_allow_html=True)

        # ── Genre tag picker ──
        sorted_tags = sorted(tag_options.keys())
        selected_tags = st.multiselect(
            "Pick Genres / Tags",
            sorted_tags,
            default=[],
            placeholder="e.g. jazz, electronic, post-punk…",
            max_selections=10,
        )

        # ── Filters row ──
        fcol1, fcol2 = st.columns(2)
        with fcol1:
            # Country filter
            if country_options:
                country_names = ["(any)"] + sorted(country_options.keys())
                sel_country = st.selectbox("Country", country_names)
                country_id = country_options.get(sel_country) if sel_country != "(any)" else None
            else:
                country_id = None

        with fcol2:
            # Year range
            if album_meta_df is not None:
                year_range = st.slider("Release Year", 1920, 2026, (1960, 2026), step=5)
            else:
                year_range = None

        # ── Search ──
        if selected_tags:
            selected_tag_ids = [tag_options[t] for t in selected_tags]
            with st.spinner("Searching…"):
                results = explore_search(
                    selected_tag_ids, country_id, year_range,
                    album_tags_df, album_meta_df, lookup, album_id_to_row,
                    max_results=EXPLORE_RESULTS,
                    sec_types=sec_types,
                    live_filter=st.session_state.get('live_filter', 'BOTH'),
                    comp_filter=st.session_state.get('comp_filter', 'BOTH'))

            tags_str = ", ".join(selected_tags)
            filters = []
            if country_id and sel_country != "(any)":
                filters.append(sel_country)
            if year_range:
                filters.append(f"{year_range[0]}–{year_range[1]}")
            filter_str = (" · " + " · ".join(filters)) if filters else ""

            render_results_table(results, "Discoveries",
                                 f"TAGS › {tags_str}{filter_str}",
                                 show_similarity=False)

            if results is not None and not results.empty:
                st.markdown("<div style='font-family:DM Mono;font-size:.62rem;color:var(--dim);"
                            "margin:.6rem 0 .3rem;'>↳ Pick one to get similar recommendations:</div>",
                            unsafe_allow_html=True)
                cols = st.columns(min(len(results), 4))
                for i, (_, row) in enumerate(results.head(8).iterrows()):
                    with cols[i % 4]:
                        label = str(row['Album'])[:20]
                        if st.button(f"→ {label}", key=f"seed_{i}",
                                     use_container_width=True):
                            st.session_state['explore_seed'] = {
                                'album_id': row['album_id'],
                                'album_name': row['Album'],
                                'artist_name': row['Artist'],
                            }
                            st.rerun()
        else:
            st.markdown("""
            <div style="padding:1.5rem 0;color:var(--dim);font-size:.9rem;">
              Select genre tags above to start exploring.
            </div>""", unsafe_allow_html=True)
