# Next Steps Analysis — mixtape recommendation engine
_Generated after V4 model completion · June 2026_

---

## Model progression summary

| Model | Hit Rate | Δ vs V1 | Key addition |
|---|---|---|---|
| V1 | 0.0638 | baseline | Tags, labels, types, ratings |
| V2 | 0.0694 | +8.8% | Country, track stats |
| V3 | 0.0674 | +5.6% | Contributors (net negative) |
| V4 | 0.0765 | +19.9% | Year, tuned weights |

V4 is the best model to date, but absolute hit rate remains low. The evidence
suggests the ceiling is not the model architecture — it is evaluation quality
and feature signal strength. Both need attention before adding more complexity.

---

## Lessons learned V2 → V4

- **More features do not automatically help.** V3 added three contributor blocks
  and scored worse than V2. Feature quality and weight sensitivity matter more
  than feature count.
- **Weight landscape is often flat.** Country, track stats, role family, and
  instrument weights all showed flat or near-flat tuning landscapes. Only labels,
  types, and year had clear peaks.
- **Small weights can still justify inclusion.** Year at W=0.126 contributes
  meaningfully (+2% hit rate) despite being a single column competing against
  thousands of tag columns.
- **Artefact alignment is critical.** The row/id mismatch bug (X_norm rows ≠
  ids_ann length) produced silently wrong results that were hard to diagnose.
  Always assert shape consistency after saving model artefacts.
- **W_CONTRIB_CNT dropped to 0.** Contributor count is not a useful similarity
  signal at this scale — it captures album size (orchestral vs solo) more than
  genre or style.
- **W_INSTRUMENT near zero (0.03), W_ROLE_FAMILY near zero (0.05).** Contributor
  profile features have very low discriminative power in their current flat form.

---

## Recommended next steps

### 1. Fix fuzzy matching in the evaluator _(highest priority)_

**Problem:** The Last.fm ground truth linker uses exact string matching. MusicBrainz
album names often differ in punctuation, articles, remaster suffixes, and live
edition labels. Many known-similar album pairs are invisible to the scorer,
meaning a perfect model could still score very low.

**Fix:** Replace exact matching with fuzzy matching using `rapidfuzz` at ~85%
similarity threshold in the ground truth linker. This increases effective ground
truth density without changing the model.

**Why first:** Until evaluation is reliable, it is difficult to tell whether model
changes represent genuine improvements or noise. This fixes the measurement
instrument before tuning what it measures.

---

### 2. Tag hierarchy rollup _(high impact, low cost)_

**Problem:** Tags are currently treated as a flat bag of words. An album tagged
"death metal" shares no direct signal with an album tagged "metal" even though
they are closely related. Albums with sparse or idiosyncratic tags get poor
coverage.

**Fix:** Build a tag parent-mapping table from MusicBrainz tag relationships and
add rolled-up parent genre columns to the tag matrix. Two modes to evaluate:
- **Additive:** add parent tag columns alongside child tag columns
- **Fallback:** fill zero-tag albums using parent genre only

Tags already dominate the model (W_TAGS = 1.0 reference weight), so improving
their coverage and hierarchy should have a proportionally large effect.

---

### 3. FAISS approximate nearest neighbours _(infrastructure)_

**Problem:** Brute-force cosine search over 1M × 9K is memory-intensive and slow
to query. The matrix will only grow as features are added.

**Fix:** Replace `sklearn.NearestNeighbors` with a FAISS `IVFFlat` index.
Expected outcome: ~100× query latency reduction with <1% hit rate loss.

**Why now:** The feature matrix is already at 9,395 columns and 1M rows. Before
adding more feature blocks (artist-level, richer tags), moving to an approximate
index makes iteration faster and the app more responsive.

---

### 4. Artist-level features _(new signal source)_

**Problem:** The model is purely album-level. Two albums by artists from the same
scene, country, or era share no signal unless their albums have matching tags.
This is a structural gap — the recommendation engine knows nothing about the
artist beyond what appears on the album's own tag/label/type columns.

**Candidate features:**
- Artist origin country (already partly captured via album country, but not
  systematically)
- Artist active period (decade vector)
- Artist-level aggregated tag profile (genre signal averaged across all albums
  by that artist, giving sparse-tag albums a richer genre anchor)

**Implementation note:** Artist features need to be album-aligned (one row per
album, not per artist) and added as a new sparse block with its own weight.

---

### 5. Revisit instrument features within genre context _(speculative)_

**Current state:** W_INSTRUMENT = 0.03 — near zero. The flat instrument matrix
provides almost no discriminative power globally.

**Hypothesis:** Instrument similarity is meaningful within genres but not across
them. A violin is a strong signal within classical but noise when comparing
classical to jazz. Segmenting the instrument block by genre cluster before
computing similarity could recover signal that is currently washed out.

**Risk:** High implementation complexity for uncertain gain. Defer until steps
1–4 are complete and evaluation is reliable enough to detect the improvement.

---

## Suggested execution order

| Step | Effort | Expected impact | Dependency |
|---|---|---|---|
| 1. Fuzzy evaluator | Low | High (fixes measurement) | None |
| 2. Tag hierarchy | Medium | High | None |
| 3. FAISS index | Medium | Infrastructure | None |
| 4. Artist features | Medium-high | Medium | Fuzzy evaluator working |
| 5. Instrument by genre | High | Uncertain | Steps 1–4 complete |

Steps 1–3 are independent and can be started in parallel. Step 4 requires a
reliable evaluator (step 1) to confirm whether it helps. Step 5 should only be
attempted once evaluation is solid and the lower-effort wins are exhausted.

---

## What not to do next

- **Do not add more contributor features** — role family and instrument are
  already in the model at near-zero weights. The signal is not there in flat form.
- **Do not increase model complexity before fixing evaluation** — tuning against
  a noisy ground truth produces overfitted or meaningless results.
- **Do not move to approximate NN before the matrix is stable** — if major feature
  blocks are still being added, rebuilding the FAISS index repeatedly is wasteful.
  Complete tag hierarchy work first.
