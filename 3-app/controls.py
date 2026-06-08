"""Sidebar controls — preset dropdown, pro knobs + studio faders combined."""

import os
import streamlit as st
import streamlit.components.v1 as components

from config import (BLOCK_FILES, BLOCK_LABELS, BLOCK_BANDS, LEVEL_OPTIONS,
                    WEIGHT_LEVELS, DEFAULT_LEVELS,
                    PRESETS, PRESET_NAMES, PRESET_DESCRIPTIONS,
                    LIVE_OPTIONS, COMP_OPTIONS, DEFAULT_LIVE, DEFAULT_COMP)

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
# Preset dropdown
# ───────────────────────────────────────────────────────────────────────────

def _apply_preset():
    name = st.session_state.get('_preset_select')
    if name and name in PRESETS:
        for k, v in PRESETS[name].items():
            st.session_state[f"lvl_{k}"] = v
        st.session_state.pop('tune_scores', None)
        st.session_state['knob_nonce'] += 1


def render_presets():
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
    for name in BLOCK_FILES:
        st.session_state[f"lvl_{name}"] = DEFAULT_LEVELS[name]
    st.session_state.pop('tune_scores', None)
    st.session_state['knob_nonce'] += 1
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
    user_prefs = {n: WEIGHT_LEVELS[st.session_state[f"lvl_{n}"]] for n in BLOCK_FILES}
    levels = smart_auto_tune(scores, user_prefs)
    for n in BLOCK_FILES:
        st.session_state[f"lvl_{n}"] = levels[n]
    st.session_state['tune_scores'] = scores
    st.session_state['knob_nonce'] += 1
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


# ───────────────────────────────────────────────────────────────────────────
# Knob → level mapping (0-11 ↔ Off/Low/Medium/High)
# ───────────────────────────────────────────────────────────────────────────

_LVL2KNOB = {'Off': 0, 'Low': 4, 'Medium': 7, 'High': 11}
_KNOB_CUTS = [(9, 'High'), (5, 'Medium'), (1, 'Low'), (0, 'Off')]

def _knob_to_level(v):
    for thresh, lvl in _KNOB_CUTS:
        if v >= thresh:
            return lvl
    return 'Off'


# ───────────────────────────────────────────────────────────────────────────
# Combined render — knobs on top, faders below, no radio picker
# ───────────────────────────────────────────────────────────────────────────

def render_controls(T, **_kw):
    nonce = st.session_state.get('knob_nonce', 0)
    tune_scores = st.session_state.get('tune_scores', {})
    names = list(BLOCK_FILES.keys())

    # ── Pro Knobs panel (compact, all 5 in one component) ──
    panel = _declare_knob_panel()
    defs = [{"id": n, "label": BLOCK_LABELS[n],
             "value": _LVL2KNOB[st.session_state[f"lvl_{n}"]],
             "defaultValue": _LVL2KNOB[DEFAULT_LEVELS[n]]}
            for n in names]

    with st.sidebar:
        result = panel(knobs=defs, reset_nonce=nonce, height=220, key="pk")

    if isinstance(result, dict):
        for n in names:
            if n in result:
                st.session_state[f"lvl_{n}"] = _knob_to_level(result[n])

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
