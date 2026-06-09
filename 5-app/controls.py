"""Sidebar controls — preset dropdown, pro knobs + studio faders combined."""

import os
import streamlit as st
import streamlit.components.v1 as components

from config import (BLOCK_FILES, KNOB_BLOCKS, BLOCK_LABELS, BLOCK_BANDS,
                    PRESETS, PRESET_NAMES, PRESET_DESCRIPTIONS,
                    DEFAULT_WEIGHTS, dial_to_weight, weight_to_dial,
                    LIVE_OPTIONS, COMP_OPTIONS, DEFAULT_LIVE, DEFAULT_COMP,
                    LASTFM_AVAILABLE)

HERE = os.path.dirname(os.path.abspath(__file__))

# ───────────────────────────────────────────────────────────────────────────
# Component declarations
# ───────────────────────────────────────────────────────────────────────────

@st.cache_resource
def _declare_fader():
    return components.declare_component("studio_fader", path=os.path.join(HERE, "fader_component"))

@st.cache_resource
def _declare_knob_panel():
    return components.declare_component("pro_knobs", path=os.path.join(HERE, "knob_component"))


# ───────────────────────────────────────────────────────────────────────────
# Session state helpers
# ───────────────────────────────────────────────────────────────────────────

def _init_state():
    """Seed session state with defaults on first run."""
    for name in KNOB_BLOCKS:
        w = DEFAULT_WEIGHTS.get(name, 1.09)
        st.session_state.setdefault(f"wgt_{name}", w)
        st.session_state.setdefault(f"dial_{name}", weight_to_dial(w))
    st.session_state.setdefault('knob_nonce', 0)
    st.session_state.setdefault('live_filter', DEFAULT_LIVE)
    st.session_state.setdefault('comp_filter', DEFAULT_COMP)


def _apply_weights(weights: dict):
    """Write exact float weights + derived dial positions into session state."""
    for name, w in weights.items():
        if name in KNOB_BLOCKS:
            st.session_state[f"wgt_{name}"] = float(w)
            st.session_state[f"dial_{name}"] = weight_to_dial(w)
    st.session_state['knob_nonce'] = st.session_state.get('knob_nonce', 0) + 1


def get_weights() -> dict:
    """Return current float weights for all BLOCK_FILES (including hidden ratings)."""
    weights = {}
    for name in KNOB_BLOCKS:
        weights[name] = float(st.session_state.get(f"wgt_{name}",
                                                    DEFAULT_WEIGHTS.get(name, 1.09)))
    # Ratings has no knob — synced to popularity weight.
    # If popularity unavailable, fall back to dial-6 equivalent (~1.09).
    if LASTFM_AVAILABLE:
        weights['ratings'] = weights.get('popularity', 1.09)
    else:
        weights['ratings'] = dial_to_weight(6)
    return weights


# ───────────────────────────────────────────────────────────────────────────
# Preset dropdown
# ───────────────────────────────────────────────────────────────────────────

def _apply_preset():
    name = st.session_state.get('_preset_select')
    if name and name in PRESETS:
        _apply_weights(PRESETS[name])
        st.session_state.pop('tune_scores', None)


def render_presets():
    _init_state()
    st.sidebar.selectbox(
        "Preset",
        PRESET_NAMES,
        index=0,
        key="_preset_select",
        on_change=_apply_preset,
        help="Quick starting point — fine-tune below or hit Auto-Tune.",
    )


# ───────────────────────────────────────────────────────────────────────────
# Auto-Tune / Reset
# ───────────────────────────────────────────────────────────────────────────

def reset_weights():
    _apply_weights(DEFAULT_WEIGHTS)
    st.session_state.pop('tune_scores', None)
    st.session_state['flash'] = 'reset'


def do_auto_tune(blocks, ssq, album_id_to_row):
    from engine import auto_tune_profile, smart_auto_tune
    aid = st.session_state.get('seed_album_id')
    if aid is None:
        st.session_state['flash'] = 'noseed'
        return
    _, scores = auto_tune_profile(aid, blocks, ssq, album_id_to_row)
    if scores is None:
        st.session_state['flash'] = 'noseed'
        return
    # Pass current exact float weights as user preferences
    user_weights = {n: st.session_state.get(f"wgt_{n}", DEFAULT_WEIGHTS.get(n, 1.09))
                    for n in KNOB_BLOCKS}
    new_weights = smart_auto_tune(scores, user_weights)
    _apply_weights(new_weights)
    st.session_state['tune_scores'] = scores
    st.session_state['flash'] = 'tuned'


def render_auto_tune_buttons(blocks, ssq, album_id_to_row):
    a, b = st.sidebar.columns([3, 2])
    with a:
        st.button("✦ Auto-Tune", on_click=do_auto_tune,
                  args=(blocks, ssq, album_id_to_row),
                  help="Refine weights based on this album's signal × your preset.")
    with b:
        st.button("Reset", on_click=reset_weights)

    flash = st.session_state.pop('flash', None)
    if flash == 'tuned':
        st.sidebar.markdown("<div style='font-family:DM Mono;font-size:.64rem;color:var(--gold);"
                            "margin:.1rem 0 .3rem;'>◉ Smart-tuned.</div>", unsafe_allow_html=True)
    elif flash == 'noseed':
        st.sidebar.warning("Pick an album first.")
    elif flash == 'reset':
        st.sidebar.markdown("<div style='font-family:DM Mono;font-size:.64rem;color:var(--dim);"
                            "margin:.1rem 0 .3rem;'>↺ Reset.</div>", unsafe_allow_html=True)

    if not LASTFM_AVAILABLE:
        st.sidebar.info(
            "💿 **Popularity knob unavailable** — run "
            "`3-features/13-feature-lastfm-popularity.ipynb` to add Last.fm data.",
            icon="ℹ️",
        )


# ───────────────────────────────────────────────────────────────────────────
# Knobs panel
# ───────────────────────────────────────────────────────────────────────────

def render_controls(T, **_kw):
    _init_state()
    nonce = st.session_state.get('knob_nonce', 0)
    panel = _declare_knob_panel()

    # Build knob definitions using dial positions from session state
    defs = [
        {
            "id":           name,
            "label":        BLOCK_LABELS.get(name, name),
            "value":        st.session_state[f"dial_{name}"],
            "defaultValue": weight_to_dial(DEFAULT_WEIGHTS.get(name, 1.09)),
        }
        for name in KNOB_BLOCKS
    ]

    with st.sidebar:
        result = panel(knobs=defs, reset_nonce=nonce, height=220, key="pk")

    # When the knob component emits a new dial value, update both dial + weight
    if isinstance(result, dict):
        for name in KNOB_BLOCKS:
            if name in result:
                new_dial = int(result[name])
                if new_dial != st.session_state.get(f"dial_{name}"):
                    st.session_state[f"dial_{name}"] = new_dial
                    st.session_state[f"wgt_{name}"] = dial_to_weight(new_dial)

    st.sidebar.markdown("<hr style='margin:.3rem 0;'>", unsafe_allow_html=True)


# ───────────────────────────────────────────────────────────────────────────
# Content filters — Live Albums / Greatest Hits
# ───────────────────────────────────────────────────────────────────────────

def render_content_filters():
    """Two faders that filter recommendations by release-group secondary type."""
    st.session_state.setdefault('live_filter', DEFAULT_LIVE)
    st.session_state.setdefault('comp_filter', DEFAULT_COMP)
    nonce = st.session_state.get('knob_nonce', 0)
    fader = _declare_fader()

    st.sidebar.markdown("<hr style='margin:.5rem 0 .3rem;'>", unsafe_allow_html=True)
    st.sidebar.markdown("<div style='font-family:DM Mono;font-size:.58rem;letter-spacing:.16em;"
                        "color:var(--dim);margin-bottom:.2rem;'>CONTENT FILTERS</div>",
                        unsafe_allow_html=True)

    with st.sidebar:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("<div style='text-align:center;font-family:DM Mono;font-size:.52rem;"
                        "color:var(--dim);margin-bottom:-.3rem;'>Live Albums</div>",
                        unsafe_allow_html=True)
            r = fader(title="", options=LIVE_OPTIONS,
                      value=st.session_state['live_filter'],
                      nonce=nonce, height=150, key="ff_live")
            if r in LIVE_OPTIONS:
                st.session_state['live_filter'] = r
        with c2:
            st.markdown("<div style='text-align:center;font-family:DM Mono;font-size:.52rem;"
                        "color:var(--dim);margin-bottom:-.3rem;'>Greatest Hits</div>",
                        unsafe_allow_html=True)
            r = fader(title="", options=COMP_OPTIONS,
                      value=st.session_state['comp_filter'],
                      nonce=nonce, key="ff_comp", height=150)
            if r in COMP_OPTIONS:
                st.session_state['comp_filter'] = r
