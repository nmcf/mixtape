# Speaker Notes — Nils (Slides 8–9)

---

## Slide 8 — KNN Model

**On slide:** albums as points in feature space · cosine similarity finds
nearest neighbours · ~1M albums, brute-force search · OK Computer was the
first sanity check.

**Talking points:**

- As told: With all feature blocks built and row-aligned to the same album index, the model stacks them into one combined normalised matrix.
  
- The algorithm used was **k-nearest neighbours with cosine similarity**. So With every album a point in feature space: each query is "give me the 10 closest points" (also representing albums).

- Cosine similarity suits sparse, high-dimensional data well because it compares direction, not magnitude, an album with 3 tags and one with 30
  can still point the same way if they share the same cluster.

- The feature matrix started at **2.2M albums × 6,521 features** (tags, label tags, label types, and ratings. 
After applying a safe column-pruning threshold (removing sparsely populated columns that add only noise), roughly **1 million albums** remained

- The model uses brute-force cosine distance against every row. No approximation, no index structure
- We investigated faster index structures, but at ~2% matrix density they all performed worse than brute-force.
- FAISS didn't suit IVF clustering — sklearn brute-force is the right tool at this scale for a single-user demo.

- Hand off: "But a single model with fixed weights is just a starting point. The interesting question is whether the weights are right — which is what tuning is about."

---

**Numbers to have ready if asked:**

- V1 baseline shape: **2,241,402 albums × 6,521 features** (notebook output)
- Albums with any features (recommendable set): **~1,008,102** before pruning,
  **~1,000,406** in the final fitted model
- V1 blocks: tags (3,041 cols), label tags (3,469 cols), label types (10 cols),
  ratings (1 col)
- V5 final shape grew further with country, track stats, contributor, year, and
  tag-parent blocks — ending at **~9,415 columns** across 11 blocks
- Brute-force was confirmed right: FAISS IVF needs >2% column density to
  cluster effectively; SVD compression to 128–512 dims loses 40–60% of
  neighbourhood structure

---

## Slide 9 — Model Tuning

**On slide:** each block has a weight — tuning finds the balance · evaluated
against Last.fm ground truth (HR@10) · label type block was the surprise ·
V1 → V5: +29% hit rate, weights saved to `best_weights.json`.

**Talking points:**

- The feature matrix has one weight per block — a scalar multiplied before
  L2 normalisation. Because only ratios matter after normalisation, tuning is
  about balance: how loud should genre be relative to era, label type, country?

- **The evaluation pipeline.** We needed real ground truth. So we scraped
  Last.fm across 30 top genres → 15 top artists per genre → top 20 albums
  per artist → 12 similar albums each. That yields roughly **70k similar
  pairs**.
- "Filtering those pairs to studio albums present in MusicBrainz gave ~2k seed albums to evaluate against..
  The metric used is **Hit Rate @10**: for each seed album, does at least one known-similar album appear in our top 10 recommendations?

- **The tuning problem was a memory problem.** Naively, each weight combination
  requires rebuilding a full KNN model — that took minutes per trial and would eat up hours for combinations. 
- As more feature blocks are added, the search space scales badly.
- The solution: pre-compute the dot products between seed album rows and all other albums for each block independently
  (stored as float16 to halve memory), then just re-weight at trial time and
  re-normalise — no model rebuild. 
- Further improvements came from a three-phase strategy: sensitivity scan → random search
  over the top-N blocks → focused 8×8 grid search.

- **The progression and what each version taught us:**
  Tuning and feature expansion together led to a roughly 30% increase in HR@10    
 
- **Highest impact** "The label type block — a few columns (major label / indie / self-released) — needed a 3.5× boost; it was being drowned out by thousands of tag columns." Listeners seem to cluster strongly around label type

- **The theoretical ceiling.** Our best HR@10 is ~8%. Sounds low compared to a ceiling of ~54%
  (Last.fm similar albums include live releases, EPs, and remasters).
  So ~14% of ceiling reached isn't a failure — it's a structural measurement gap, not a model gap.

- Hand off to Nijat explaining live tuning

---

**Numbers to have ready if asked:**

| Model | HR@10 | Δ vs V1 | Lesson |
  |---|---|---|---|
  | V1 | 0.064 | baseline | Tags + labels + types + ratings |
  | V2 | 0.069 | +8% | Country + track stats help — but weight landscape is flat |
  | V3 | 0.067 | –3% vs V2 | Contributor features hurt — only 25–30% coverage |
  | V4 | 0.077 | +20% | Year block + base weight tuning pays off |
  | V5 | 0.082 | +29% | Parent genre rollup (`W_TAG_PARENT = 0.26`) |

- Theoretical ceiling: **~53.7%** (fraction of Last.fm pairs resolvable to studio
  album IDs in MusicBrainz)
- Ground truth: ~70k raw similar pairs → **~11,600 matched pairs** after
  string-to-ID join (~17% match rate — fuzzy matching was a flagged improvement)
- Evaluation seeds: **1,974** albums (full dataset run)
- Naive tuning: **~60s per trial**, 40+ min for 36 combos
- Optimised: **~0.1s per trial** via pre-stored float16 dot products
- `W_TYPES = 3.507` — the standout weight; 10 cols outperforming 3,000+ tag cols
- `W_RATINGS` is **completely flat from 0.02 to 0.275** — set to 0.1 as a round number
- `W_CONTRIB_CNT` converged to **0.0** — contributor count adds nothing
- V3 went *backwards* vs V2 — "more features" isn't always better
