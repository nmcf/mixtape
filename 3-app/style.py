"""Theme definitions and CSS injection for the Mixtape app."""

import streamlit as st

LIGHT = dict(
    bg="radial-gradient(1100px 600px at 80% -10%, #efe6d2 0%, transparent 55%),"
       "linear-gradient(160deg,#f7f2e9 0%,#f1eadc 50%,#efe7d6 100%)",
    bg2="#f5f0e8", panel="#efe7d6", panel2="#e8e0cf", line="#d8cdb6",
    txt="#2c2416", dim="#9c8c72", gold="#9b6e2e", gold_soft="#c8a96e", gold_deep="#7a5320",
    input="#f3ecdc", rowline="#e3dac6", grain=".018", popbg="#f3ecdc", knob="light",
    track_off="#d8cdb6")

DARK = dict(
    bg="linear-gradient(160deg,#1a1e27 0%,#171b23 50%,#13161d 100%)",
    bg2="#1c212b", panel="#1a1f29", panel2="#222834", line="rgba(255,255,255,.08)",
    txt="#e8eaed", dim="#8a909c", gold="#e8c84a", gold_soft="#f3d77e", gold_deep="#c4972a",
    input="rgba(255,255,255,.04)", rowline="rgba(255,255,255,.07)", grain=".02", popbg="#222834",
    knob="dark", track_off="rgba(255,255,255,.12)")


def get_theme():
    """Return (theme_dict, theme_name) based on current session state."""
    st.session_state.setdefault('dark', True)   # dark navy is the default look
    is_dark = st.session_state['dark']
    return (DARK if is_dark else LIGHT), ("dark" if is_dark else "light")


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
.stTextInput label, .stSelectbox label, .stMultiSelect label {{ color:var(--gold)!important; font-weight:700;
  letter-spacing:.04em; text-transform:uppercase; font-size:.7rem; }}

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
