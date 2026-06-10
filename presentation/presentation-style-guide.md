# Presentation Style Guide

Rules for editing the Mixtape slide deck (`presentation/index.html`). Follow these so the
deck stays consistent when different people (and AI agents) add content.

## The deck at a glance

- Single self-contained file: `presentation/index.html` (HTML + CSS + JS, no build step, no
  dependencies). Assets (e.g. logos) live alongside it in `presentation/`.
- Aesthetic: a Walkman / cassette tape. Each slide is rendered as a vivid cassette — textured
  black body, cream paper label with retro stripe bands, a "90" mark, reel windows, screws.
- Navigation: the **skip-back / skip-forward** transport buttons move between slides (arrow
  keys and spacebar also work). **Play** toggles the spinning reels + play/pause icon. **Stop**
  and **Record** are cosmetic only.

## Where the content lives

All slide content is in the `slides` array in the `<script>` block. Each slide is an object:

```js
{ presenter: "NIALL", title: "MusicBrainz", logo: "musicbrainz-logo.svg",
  body: "<ul><li>...</li></ul>" }
```

- `presenter` — UPPERCASE name. Drives the per-presenter colour theme (see below). **Do not
  rename** the theme keys.
- `title` — short noun phrase. Rendered UPPERCASE by CSS, so write it in normal case.
- `body` — HTML string. Usually a `<ul>` of bullets. The intro slide uses a styled tagline
  `<p>` + summary instead.
- `logo` — optional. Path to an SVG in `presentation/`. When set, the logo shows on the right
  and the "90" mark is auto-hidden. Reusable on any slide.

To add or edit a slide, edit only this array. You rarely need to touch the CSS/HTML.

## Bullet rules

- **Aim for ~4 bullets per slide.** This is a *soft* guideline, not a hard limit. The cassette
  grows to fit its content, so more bullets make that slide taller than the others — the goal
  is keeping every slide a consistent size. Combine related points rather than adding a 5th/6th.
- **Keep each bullet to a single line** at normal screen width. If it wraps, shorten it or
  merge it with a neighbour.
- **Plain English first.** Explain the idea, not the implementation. We deliberately walked
  back overly technical bullets (file names, function calls, SQL) into readable explanations.
  A little precision is fine (a key number, one identifier in `<code>`), but don't list code.
- **Lead with the insight**, then the supporting detail (e.g. "Found precomputed tables —
  skipped costly joins" rather than the reverse).

## HTML conventions in `body`

- Bullets: `<ul><li>…</li></ul>`.
- Em dash: `&mdash;`  ·  ampersand: `&amp;`  ·  ≥: `&ge;`  ·  arrow: `&rarr;`.
- Inline code / identifiers: wrap in `<code>…</code>` (subtle tinted style is already defined).
  Use sparingly — for a table/file/weight name, not whole snippets.
- Keep the tagline pattern from slide 1 if you need an intro-style slide (italic `<p>` then a
  one-line summary).

## Per-presenter colour themes

Set in the `themes` object; each presenter gets stripe colours + an accent (echoes the four
reference cassettes). Keep the mapping as-is:

| Presenter | Theme |
|---|---|
| NIALL | teal |
| ARSALAN | amber / yellow |
| NILS | orange |
| NIJIT | red / multi |

## Placeholder slides

- Unfinished slides show a "PLACEHOLDER SLIDE" tag. This is driven by a slide-index check in
  `render()` (`current >= N`). **When you fill in a placeholder slide, lower that threshold** so
  the tag stops showing for it. Filled slides should never show the tag.

## Content accuracy

- Ground every bullet in the repo — the notebooks (`1-data/`, `2-eda/`, `3-features/`,
  `4-model/`, `5-app/`), the `planning/` and `docs/` notes. Read the source before writing
  claims; don't invent numbers.

## Previewing

- It's a static file: open it directly (`open presentation/index.html`). The in-app preview
  server may be blocked by this project's `.claude/launch.json` (it forces a Python venv) — that
  is unrelated to the deck.

## Commits

- Commit only `presentation/` files unless asked otherwise; other work on the branch is often
  in progress. Stage paths explicitly (`git add presentation/` / `git commit presentation/`).
