"""Theme definitions and CSS injection for the Mixtape app."""

import streamlit as st

LIGHT = dict(
    bg="radial-gradient(1100px 600px at 80% -10%, #efe6d2 0%, transparent 55%),"
       "linear-gradient(160deg,#f7f2e9 0%,#f1eadc 50%,#efe7d6 100%)",
    bg2="#f5f0e8", panel="#efe7d6", panel2="#e8e0cf", line="#d8cdb6",
    txt="#2c2416", dim="#9c8c72", gold="#9b6e2e", gold_soft="#c8a96e", gold_deep="#7a5320",
    input="#f3ecdc", rowline="#e3dac6", grain=".018", popbg="#f3ecdc", knob="light",
    track_off="#d8cdb6", input_solid="#f3ecdc")

DARK = dict(
    bg="linear-gradient(160deg,#1a1e27 0%,#171b23 50%,#13161d 100%)",
    bg2="#1c212b", panel="#1a1f29", panel2="#222834", line="rgba(255,255,255,.08)",
    txt="#e8eaed", dim="#8a909c", gold="#e8c84a", gold_soft="#f3d77e", gold_deep="#c4972a",
    input="rgba(255,255,255,.04)", rowline="rgba(255,255,255,.07)", grain=".02", popbg="#222834",
    knob="dark", track_off="rgba(255,255,255,.12)", input_solid="#222834")


def get_theme():
    """Return (theme_dict, theme_name) based on current session state."""
    st.session_state.setdefault('dark', True)   # dark navy is the default look
    is_dark = st.session_state['dark']
    return (DARK if is_dark else LIGHT), ("dark" if is_dark else "light")


def searchbox_styles(T):
    """react-select style overrides for st_searchbox.

    The searchbox is a custom component rendered in a sandboxed iframe, so the
    page-level CSS in inject_css() can't reach it — left alone it inherits
    Streamlit's fixed `base="dark"` theme and ignores our light/dark toggle.
    Rebuilding these overrides from the active theme T (and passing them on each
    rerun) keeps the box, dropdown and icons in step with the rest of the UI.
    """
    # DM Sans is the app's UI font; patch_searchbox_iframe() loads it into the
    # component iframe so this resolves to the real face (else falls back to sans).
    font = '"DM Sans","Source Sans Pro",sans-serif'
    return {
        # Painted behind the control. The control has rounded corners but the
        # iframe body is square and fixed-dark, so without this the dark body
        # shows through as four corner marks — paint it the page colour instead.
        "wrapper": {"backgroundColor": T['bg2']},
        "searchbox": {
            "control": {
                # opaque (not the page's translucent --input) so it fully covers
                # the component iframe's fixed dark body behind it
                "backgroundColor": T['input_solid'],
                "border": f"1px solid {T['line']}",
                "borderRadius": "10px",
                "fontFamily": font,
            },
            "input": {"color": T['gold_deep'], "fontFamily": font},
            "singleValue": {"color": T['gold_deep'], "fontFamily": font},
            "placeholder": {"color": T['dim'], "fontFamily": font},
            "menuList": {
                "backgroundColor": T['popbg'],
                "border": f"1px solid {T['line']}",
                "borderRadius": "10px",
                "boxShadow": "0 6px 20px rgba(0,0,0,.25)",
            },
            # no highlightColor — the matched substring should not be highlighted.
            # Override react-select's default blue focus/active highlight with the
            # same gold tint the baseweb dropdowns use (see [data-baseweb="popover"]
            # li:hover in inject_css) so all dropdowns match.
            "option": {
                "color": T['txt'],
                "backgroundColor": T['popbg'],
                "fontFamily": font,
                # !important to deterministically beat react-select's default
                # blue :active rule (same specificity, source-order otherwise)
                "&:hover": {"backgroundColor": f"color-mix(in srgb,{T['gold']} 20%,transparent) !important"},
                "&:active": {"backgroundColor": f"color-mix(in srgb,{T['gold']} 20%,transparent) !important"},
            },
        },
        # hide the react-select chevron; it can't be made to match baseweb's
        # selectbox arrow, and a mismatched arrow reads worse than none
        "dropdown": {"width": 0, "height": 0},
        "clear": {"icon": "cross", "fill": T['gold'], "stroke": T['gold']},
    }


def patch_searchbox_iframe():
    """Patch the st_searchbox component iframe from the page side.

    The searchbox renders in a sandboxed, same-origin iframe whose <body> is
    painted with Streamlit's fixed base-theme background (dark). That dark body
    shows through wherever the control doesn't cover it — the rounded corners and
    the gap above the open dropdown — and no web font is loaded inside it. Neither
    is reachable via style_overrides. This drops a tiny components.html helper that
    reaches the (same-origin) iframe and makes its body transparent (so the themed
    page shows through instead) and loads DM Sans so the box matches the UI font.
    Degrades silently (try/except) if the parent document can't be reached.
    """
    import streamlit.components.v1 as components
    components.html("""
<script>
(function () {
  function patch() {
    try {
      var pdoc = window.parent.document;
      var frames = pdoc.querySelectorAll('iframe[title="streamlit_searchbox.searchbox"]');
      frames.forEach(function (fr) {
        var d = fr.contentDocument;
        if (!d || d.getElementById('mixtape-sb-patch')) return;
        var link = d.createElement('link');
        link.rel = 'stylesheet';
        link.href = 'https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&display=swap';
        d.head.appendChild(link);
        var st = d.createElement('style');
        st.id = 'mixtape-sb-patch';
        // transparent iframe body (no dark corner artifacts on the control) and
        // a transparent, shadowless react-select menu container (its default
        // white panel otherwise shows through the themed menuList's rounded
        // corners). Elevation is restored on the menuList via style_overrides.
        st.textContent =
          'html,body{background:transparent !important;}' +
          'div[class*="-menu"]{background:transparent !important;box-shadow:none !important;}';
        d.head.appendChild(st);
      });
    } catch (e) { /* cross-origin / not ready — ignore */ }
  }
  patch();
  setInterval(patch, 700);
})();
</script>
""", height=0)


def inject_css(T):
    """Inject the full CSS block into the page."""
    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500;600;700&display=swap');
:root {{
  --bg2:{T['bg2']}; --panel:{T['panel']}; --panel2:{T['panel2']}; --line:{T['line']};
  --txt:{T['txt']}; --dim:{T['dim']}; --gold:{T['gold']}; --gold-soft:{T['gold_soft']};
  --gold-deep:{T['gold_deep']}; --input:{T['input']}; --rowline:{T['rowline']};
}}
.stApp {{ background:{T['bg']}; color:var(--txt); font-family:'DM Sans',sans-serif; }}
.stApp::before {{ content:""; position:fixed; inset:0; pointer-events:none; z-index:0; opacity:{T['grain']};
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='120'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E"); }}
[data-testid="stHeader"] {{ background:transparent; }}
.block-container {{ padding-top:1.6rem; max-width:1200px; position:relative; z-index:1; }}
h1,h2,h3 {{ font-family:'DM Serif Display',serif; }}

[data-testid="stSidebar"] {{ background:linear-gradient(180deg,var(--panel) 0%,var(--bg2) 100%);
  border-right:1px solid var(--line); }}
[data-testid="stSidebar"] * {{ color:var(--txt); }}

/* inputs */
[data-testid="stTextInput"] input {{ background:var(--input)!important; border:1px solid var(--line)!important;
  border-radius:10px!important; color:var(--gold-deep)!important; font-family:'DM Mono',monospace;
  font-size:1.02rem; padding:.7rem .9rem; }}
[data-testid="stTextInput"] input:focus {{ border-color:var(--gold)!important;
  box-shadow:0 0 0 2px color-mix(in srgb,var(--gold) 28%,transparent)!important; }}
[data-baseweb="select"] > div {{ background:var(--input)!important; border:1px solid var(--line)!important;
  border-radius:10px!important; color:var(--gold-deep)!important; }}
[data-baseweb="select"] svg {{ color:var(--gold)!important; }}
[data-baseweb="popover"] > div, [data-baseweb="popover"] ul,
[data-baseweb="popover"] [role="listbox"] {{ background:{T['popbg']}!important; border-color:var(--line)!important; }}
[data-baseweb="popover"] li {{ color:var(--txt)!important; background:transparent!important; }}
[data-baseweb="popover"] li:hover {{ background:color-mix(in srgb,var(--gold) 20%,transparent)!important; }}

/* labels */
.stTextInput label, .stSelectbox label, .stMultiSelect label,
.mixtape-field-label {{ color:var(--gold)!important; font-weight:700;
  letter-spacing:.04em; text-transform:uppercase; font-size:.7rem; }}
.mixtape-field-label {{ font-family:'DM Sans',sans-serif; margin-bottom:.4rem; }}

/* buttons */
.stButton button {{ border-radius:10px; font-family:'DM Mono',monospace; font-weight:600;
  letter-spacing:.05em; text-transform:uppercase; font-size:.72rem; border:1px solid var(--line);
  color:var(--gold-deep); background:transparent; transition:all .18s ease; width:100%; }}
.stButton button:hover {{ border-color:var(--gold); color:var(--gold); }}
.stButton button[kind="primary"] {{ color:#1a130a; border:none;
  background:linear-gradient(180deg,var(--gold-soft) 0%,var(--gold) 60%,var(--gold-deep) 100%);
  box-shadow:0 5px 18px color-mix(in srgb,var(--gold) 40%,transparent); }}
.stButton button[kind="primary"]:hover {{ transform:translateY(-1px); }}

/* faders */
[data-testid="stSidebar"] [data-baseweb="slider"] > div > div {{ background:var(--gold)!important; }}
[data-testid="stSidebar"] [role="slider"] {{ background:radial-gradient(circle at 35% 30%,var(--gold-soft),var(--gold-deep))!important;
  border:1px solid var(--line)!important; box-shadow:0 2px 8px rgba(0,0,0,.4)!important; }}
[data-testid="stSidebar"] [data-testid="stTickBar"] {{ display:none; }}

/* premium stepper */
.st-key-stepwrap .stButton button {{ border-radius:50%!important; width:42px!important; height:42px!important;
  min-width:42px!important; padding:0!important; font-size:1.2rem!important; font-weight:600!important;
  border:1px solid var(--line)!important; color:var(--gold)!important;
  background:radial-gradient(circle at 35% 30%,var(--panel2),var(--bg2))!important;
  box-shadow:0 3px 10px rgba(0,0,0,.25), inset 0 1px 0 color-mix(in srgb,var(--gold) 25%,transparent)!important; }}
.st-key-stepwrap .stButton button:hover {{ border-color:var(--gold)!important; color:#fff!important;
  box-shadow:0 0 14px color-mix(in srgb,var(--gold) 45%,transparent)!important; }}

/* control-style selector pills */
.st-key-stylepick [role="radiogroup"] {{ display:grid; grid-template-columns:1fr 1fr; gap:6px; }}
.st-key-stylepick [role="radiogroup"] label {{ margin:0!important; padding:.5rem .4rem; border:1px solid var(--line);
  border-radius:9px; font-family:'DM Mono',monospace; font-size:.66rem; cursor:pointer; justify-content:center; }}
.st-key-stylepick [role="radiogroup"] label > div:first-child {{ display:none!important; }}
.st-key-stylepick [role="radiogroup"] label:has(input:checked) {{ border-color:var(--gold);
  background:color-mix(in srgb,var(--gold) 14%,transparent); }}
.st-key-stylepick [role="radiogroup"] label p {{ color:inherit!important; }}

/* tabs */
.stTabs [data-baseweb="tab-list"] {{ background:transparent; border-bottom:1px solid var(--line); }}
.stTabs [data-baseweb="tab"] {{ color:var(--dim); font-family:'DM Mono',monospace; font-size:.78rem;
  letter-spacing:.08em; text-transform:uppercase; }}
.stTabs [data-baseweb="tab"][aria-selected="true"] {{ color:var(--gold); border-bottom-color:var(--gold); }}

/* multiselect */
[data-baseweb="tag"] {{ background:color-mix(in srgb,var(--gold) 18%,transparent)!important;
  border:1px solid var(--line)!important; color:var(--gold-deep)!important; }}
[data-baseweb="tag"] span {{ color:var(--gold-deep)!important; }}

[data-testid="stAlert"] {{ background:color-mix(in srgb,var(--gold) 8%,transparent); border:1px solid var(--line);
  border-radius:10px; color:var(--txt); }}
hr {{ border-color:var(--line); }}
</style>
""", unsafe_allow_html=True)
