# Speaker Notes — Nijat (Slides 10–11)

Talking points based on the current slide content. Bullets on the slides are the headlines;
these notes are what to say around them.

---

## Slide 10 — Your Personal Mix

**On slide:** no pre-built model · one knob per signal · re-ranks 1.76M in under a second · change the weights, not the model.

Talking points:
- Pick up from Nils: his **KNN works out all the neighbors ahead of time** and saves them as one
  fixed model.
- My part flips that: **no model built in advance**. We work out how similar albums are **live —
  the moment you ask**.
- Why? Because we want the user to **change things in real time**. Each knob is one signal —
  **genre, popularity, era**. Turn a knob up, that signal **counts for more** in the result.
- With a fixed model, every change = **retrain 1.76M albums = a long wait**. Our way: **under a
  second**, no retrain.
- The key line: **"change the weights, not the model."** Same data, infinite settings.
- This is what makes the tagline literal — **tune the algorithm to your sound**.
- Segue: "Let me show you what that feels like" -> slide 11 / live demo.

---

## Slide 11 — Try It Live (the app + live demo)

**On slide:** search -> pick -> 10 similar · knobs + filter faders · Find Similar / Explore · data -> features -> your perfect sound.

Talking points:
- This is the finished product. **Built with Streamlit.** we designed the whole thing to feel
  like a **mixing board**.
- **Demo flow (do it live):**
  1. **Search an artist** — e.g. Radiohead -> pick **Kid A**. It returns **10 similar albums**.
  2. **Turn a knob** — results **change instantly**, live. (Pause — let them watch the change.)
  3. **Faders** — filter out **live albums** and **greatest-hits** collections.
  4. **Two modes** — *Find Similar* (from an album) and *Explore* (pick genres by mood).
- Keep the demo **short and safe** — one search, one knob turn, one filter. Backup video ready in
  case of bad WiFi.
- **Closing line (only if I'm closing the talk):** tie the whole pipeline together —
  **MusicBrainz + Last.fm data -> features -> Nils's model -> this app you can play with.**
  End on the tagline: *tune the algorithm to your perfect sound.*
- If someone else closes: stop after the demo, hand off cleanly.

---
