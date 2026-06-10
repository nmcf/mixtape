# Mixtape — Streamlit App

Interactive album recommender UI. Two modes:

- **Find Similar** — pick an artist → album → get content-based recommendations, with a live mixing board to weight features.
- **Explore** — pick genre tags (+ optional country / decade) to discover albums, then seed one into Find Similar.

## Run

```bash
streamlit run 5-app/app.py
```

Starts on `localhost:8505` (configured in `.streamlit/config.toml`).

## Modules

| File | Role |
|---|---|
| `app.py` | Entry point, layout, two tabs, result rendering |
| `config.py` | Constants, presets, feature-block config, weight ↔ dial helpers |
| `engine.py` | Data loading, weighted-cosine recommendation, auto-tune, explore search |
| `controls.py` | Sidebar — preset dropdown, knob panel, auto-tune/reset, content-filter faders |
| `style.py` | Dark / light themes + CSS |
| `fader_component/` | Custom vertical-fader HTML component (content filters) |
| `knob_component/` | Custom multi-knob panel HTML component (feature weights) |

## Full documentation

See **[`docs/05-app.md`](../docs/05-app.md)** for the complete reference — the float-weight system,
reactive artist search, presets, auto-tune, both tabs, the required data files and how to build
them, and theming.
