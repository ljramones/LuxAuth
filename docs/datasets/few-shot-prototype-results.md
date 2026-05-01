# Few-Shot Prototype Matching with DINOv2 Backbone Comparison

**Date:** 2026-04-30
**Status:** Diagnostic only on public texture data — no production authentication claims

---

## 1. Executive Summary

> **DIAGNOSTIC ONLY ON PUBLIC TEXTURE DATA.**
>
> All findings below are measured on LeaData (4 leather species, 16 sample groups) and FabricNET (130 woven-fabric microscopy images). These are public datasets with **unusually consistent capture conditions** — single device per dataset, controlled lighting, no operator variation, no wear/repair, no production-year drift, no counterfeit examples. They validate diagnostic behavior of the inference harness, not luxury authentication accuracy and not generalization to real lab captures.
>
> Numbers in this document are calibrations of the *experimental* harness, not production thresholds, not a production model selection, and not a production strategy selection. Phrases like "DINOv2 dominates" or "nearest-neighbor wins" are statements about LeaData behavior and are explicitly **not** statements about luxury authentication behavior.

Phase 10 cross-tabulated five few-shot inference strategies (nearest-neighbor, top-k mean, prototype centroid, prototype medoid, prototype centroid with abstention) against three embedding regimes on LeaData (`external_leadata_v0.1.0`) at K = 1, 3, 5, 10, with 500 episodes per cell and FabricNET (`external_fabricnet_v0.1.0`) used as out-of-domain queries.

**Diagnostic findings on LeaData:**

- **DINOv2 frozen outperforms `texture_baseline_v0.2.0` by a wide margin on the LeaData diagnostic harness.** Cluster_separation on species labels: +0.1742 vs +0.0178 (≈10× larger gap). At K=5 item_id: DINOv2 nearest_neighbor 98.3% vs texture_baseline 95.2%. This justifies introducing DINOv2 as a *shadow candidate* — it does not justify promotion to production decision authority. See §10 and the dedicated Phase 11 plan for the conservative integration story.
- **`learned_metric_v0.2.0` had no LeaData embeddings persisted in the database.** The grid ran as a 2-way comparison (texture_baseline vs DINOv2). The runner skipped the third model cleanly. This is a separate historical-comparison gap; see §11 for the closing-the-gap path.
- **On LeaData, nearest_neighbor outperformed prototype_centroid at every K≥3.** This is contrary to the textbook expectation. See the Open Question callout below — this finding is hypothesized to be LeaData-specific and is explicitly **not** a basis for selecting a production inference strategy.
- **Abstention works for DINOv2 on LeaData and not for texture_baseline.** DINOv2's wide score distribution permits meaningful threshold-based abstention on this data (push accuracy from 97.7% to 99.8% at 20% abstention). Texture_baseline's tight score distribution (0.94 same-class / 0.94 diff-class) leaves no room for thresholds to discriminate within the < 30% abstention budget. **Whether this property transfers to real-distribution data is unknown and must be re-measured during Phase 11 shadow operation before any threshold goes live.**
- **DINOv2 OOD rejection on FabricNET (mean 93-94%) is higher than texture_baseline (mean 78-80%).** Read this as a sanity check that DINOv2 embeddings aren't broken on out-of-domain inputs, **not** as proof of OOD robustness. FabricNET-vs-LeaData is a structurally easy OOD problem — different material entirely. Real OOD probes (illumination shifts on the same leather, novel leather variants, counterfeit candidates) are not yet available; Phase 10c (PatchCore) is conditioned on those probes existing.
- **Capture-protocol K from this evidence: starting point only.** K=5 stabilized DINOv2 nearest_neighbor on LeaData item_id. Real luxury captures will have higher intra-class variance (production years, operators, microscope serial numbers, lighting, wear, repairs) and the required K is expected to be higher. Plan the gold-set capture protocol at K=10 minimum per region, K=15-20 target where capture cost permits, and calibrate per region during shadow operation.
- **Phase 11 trigger: PROCEED to shadow integration, NOT to production promotion.** Promote `dinov2_base_frozen_v0.1.0` to a *shadow_candidate* path running alongside the production decision path during a bounded evidence-gathering window. The production decision authority remains `texture_baseline_v0.2.0` for the entire shadow period. Promotion to production decision authority is gated by pre-declared criteria evaluated against real-capture evidence (see Phase 11 plan, §7).

> **OPEN QUESTION — NN vs prototype, hypothesized LeaData-specific.**
>
> On LeaData, nearest_neighbor outperformed prototype_centroid at every K≥3 for both embedding models. This contradicts the textbook expectation that averaging beats single-NN once support sets are large enough.
>
> The most plausible explanation is that **LeaData has unusually low intra-class variance** — single capture device, consistent lighting, no operator variation, no wear or repair signal, no production-year drift. Under those conditions, the nearest support example is reliably the highest-fidelity probe, and centroid averaging dilutes it.
>
> On real luxury data, intra-class variance is expected to be substantially higher (different production years, multiple operators, multiple microscope serial numbers, lighting variation, wear, repairs, possibly damage). Under high-variance conditions, prototype-based averaging typically outperforms single-NN because the centroid smooths out outliers in the support set.
>
> **Implication for Phase 11.** Phase 11 shadow operation must log nearest_neighbor, top_k_mean, prototype_centroid, and prototype_medoid scores **in parallel** for every region in every session. Production strategy selection (NN vs prototype_centroid vs other) is a Phase 11 promotion-time decision based on real-capture evidence, **not** a Phase 11 design-time decision. Locking in NN before real-data evidence exists is explicitly disallowed.

---

## 2. Experiment Setup

| Parameter | Value |
|---|---|
| Primary dataset | `external_leadata_v0.1.0` (1200 images, 4 species, 16 sample groups) |
| OOD dataset | `external_fabricnet_v0.1.0` (130 images, woven fabric textures) |
| Embedding models compared | `texture_baseline_v0.2.0`, `dinov2_base_frozen_v0.1.0` |
| Embedding model deferred | `learned_metric_v0.2.0` — no LeaData embeddings persisted; runner skipped |
| Label strategies | `external_item_id` (16 classes), `species` (4 classes) |
| Shots (K) | 1, 3, 5, 10 |
| Episodes per cell | 500 |
| Query images per class per episode | 5 |
| Score thresholds (abstention sweep) | 0.0, 0.5, 0.6, 0.7, 0.8, 0.85, 0.9 |
| Margin thresholds (abstention sweep) | 0.0, 0.02, 0.05, 0.1, 0.15 |
| Seed | 42 |
| Episode sampling | Split-aware; train split only |

---

## 3. Cluster_separation (Foundation-Model Thesis Check)

Computed on the full LeaData embedding set (n=1200) under each model, sampling 20,000 pairs.

| Model | Dim | species same | species diff | **species cluster_sep** | item_id cluster_sep | recall@1 species |
|---|---:|---:|---:|---:|---:|---:|
| `texture_baseline_v0.2.0` | 256 | 0.9577 | 0.9399 | **+0.0178** | +0.0423 | 0.9983 |
| `learned_metric_v0.2.0` | — | — | — | _no data_ | _no data_ | — |
| `dinov2_base_frozen_v0.1.0` | 768 | 0.6685 | 0.4943 | **+0.1742** | +0.2996 | 0.9992 |

**Foundation-model thesis: confirmed.** DINOv2's cluster_separation is ~10× texture_baseline's on species and ~7× on item_id. Both are well above the +0.05 floor, in both directions. The dimensionality caveat (768d vs 256d cosine spaces have different absolute scales) is acknowledged, but the magnitude difference cannot be a normalization artifact.

**Recall@1 saturation is misleading here.** Both models hit ~99.8% recall@1 on species — top-line accuracy makes the models look comparable. Cluster_separation reveals what's actually happening: texture_baseline scores everything as similar (0.94 same / 0.94 diff — nearly indistinguishable distributions), while DINOv2 actually pushes different classes apart (0.67 same / 0.49 diff — clearly separated distributions). This is the difference between "lucky NN agreement" and "robust embeddings with margin to spare."

This is the operational argument for DINOv2: it's not that it gets the easy cases more correct, it's that it has *headroom* for harder cases (closer-to-decision-boundary queries, illumination shifts, finer-grained class structure on real luxury data).

---

## 4. Support-Set Stabilization Curves

### 4.1 item_id labels (16 classes)

| Model | Strategy | K=1 | K=3 | K=5 | K=10 |
|---|---|---:|---:|---:|---:|
| texture_baseline_v0.2.0 | nearest_neighbor | 0.886 | 0.934 | 0.952 | 0.969 |
| texture_baseline_v0.2.0 | top_k_mean | 0.886 | 0.907 | 0.931 | 0.955 |
| texture_baseline_v0.2.0 | prototype_centroid | 0.886 | 0.920 | 0.926 | 0.939 |
| texture_baseline_v0.2.0 | prototype_medoid | 0.886 | 0.906 | 0.914 | 0.928 |
| **dinov2_base_frozen_v0.1.0** | **nearest_neighbor** | **0.909** | **0.971** | **0.983** | 0.989 |
| dinov2_base_frozen_v0.1.0 | top_k_mean | 0.909 | 0.960 | 0.982 | **0.989** |
| dinov2_base_frozen_v0.1.0 | prototype_centroid | 0.909 | 0.968 | 0.977 | 0.982 |
| dinov2_base_frozen_v0.1.0 | prototype_medoid | 0.909 | 0.944 | 0.958 | 0.971 |

### 4.2 species labels (4 classes — coarser, more variance)

| Model | Strategy | K=1 | K=3 | K=5 | K=10 |
|---|---|---:|---:|---:|---:|
| texture_baseline_v0.2.0 | nearest_neighbor | 0.703 | 0.870 | 0.925 | 0.971 |
| texture_baseline_v0.2.0 | prototype_centroid | 0.703 | 0.824 | 0.840 | 0.862 |
| texture_baseline_v0.2.0 | prototype_medoid | 0.703 | 0.737 | 0.755 | 0.766 |
| **dinov2_base_frozen_v0.1.0** | **nearest_neighbor** | **0.802** | **0.929** | 0.957 | **0.986** |
| dinov2_base_frozen_v0.1.0 | top_k_mean | 0.802 | 0.879 | 0.933 | 0.978 |
| dinov2_base_frozen_v0.1.0 | prototype_centroid | 0.802 | 0.922 | 0.939 | 0.957 |

**Shape findings:**

- **DINOv2 plateaus early.** On item_id, DINOv2 nearest_neighbor reaches 0.983 at K=5, then only +0.6 points by K=10. On species, K=5 → K=10 gains 3 points (0.957 → 0.986). The diminishing-returns point is K=5 for item_id and K=10 for species.
- **Texture_baseline plateaus late.** On species especially, texture_baseline nearest_neighbor is still climbing at K=10 (0.971 vs DINOv2's 0.986) — almost catching up at K=10, but with much higher per-episode variance.
- **Variance (p95-p05 spread) collapses much faster for DINOv2.** At K=5 item_id: DINOv2 spread 0.040, texture_baseline 0.100 (2.5× higher). At K=5 species: DINOv2 0.150, texture_baseline 0.200. The "stable scoring" point arrives earlier with DINOv2.
- **No curve crossings observed.** DINOv2 dominates at every K on both label strategies. The two curves don't switch order at any operational K.
- **Prior calibration:** Foundation-model curve plateaus earlier — confirmed (3-5 shots for DINOv2 item_id stability vs 10+ shots for texture_baseline). Prototype_centroid beats nearest_neighbor at K≥3 — **NOT confirmed**, NN wins at every K for both models. Top_k_mean lands between NN and centroid — partially confirmed (varies by model and K).

---

## 5. Cross-Model Ranking at K=5

This is the most likely operational K. Single-table view, sorted by accuracy:

### 5.1 item_id labels at K=5

| Rank | Model | Strategy | Acc | Std | Margin | Spread |
|---:|---|---|---:|---:|---:|---:|
| 1 | dinov2_base_frozen_v0.1.0 | nearest_neighbor | 0.9832 | 0.018 | 0.187 | 0.040 |
| 2 | dinov2_base_frozen_v0.1.0 | top_k_mean | 0.9823 | 0.018 | 0.187 | 0.060 |
| 3 | dinov2_base_frozen_v0.1.0 | prototype_centroid | 0.9766 | 0.021 | 0.196 | 0.060 |
| 4 | dinov2_base_frozen_v0.1.0 | prototype_medoid | 0.9581 | 0.028 | 0.188 | 0.100 |
| 5 | texture_baseline_v0.2.0 | nearest_neighbor | 0.9516 | 0.027 | 0.020 | 0.100 |
| 6 | texture_baseline_v0.2.0 | top_k_mean | 0.9305 | 0.030 | 0.021 | 0.100 |
| 7 | texture_baseline_v0.2.0 | prototype_centroid | 0.9263 | 0.036 | 0.022 | 0.120 |
| 8 | texture_baseline_v0.2.0 | prototype_medoid | 0.9142 | 0.037 | 0.023 | 0.120 |

### 5.2 species labels at K=5

| Rank | Model | Strategy | Acc | Std | Margin | Spread |
|---:|---|---|---:|---:|---:|---:|
| 1 | dinov2_base_frozen_v0.1.0 | nearest_neighbor | 0.9566 | 0.054 | 0.231 | 0.150 |
| 2 | dinov2_base_frozen_v0.1.0 | prototype_centroid | 0.9390 | 0.058 | 0.214 | 0.150 |
| 3 | dinov2_base_frozen_v0.1.0 | top_k_mean | 0.9328 | 0.063 | 0.218 | 0.200 |
| 4 | dinov2_base_frozen_v0.1.0 | prototype_medoid | 0.8509 | 0.082 | 0.220 | 0.250 |
| 5 | texture_baseline_v0.2.0 | nearest_neighbor | 0.9246 | 0.070 | 0.029 | 0.200 |
| 6 | texture_baseline_v0.2.0 | prototype_centroid | 0.8405 | 0.089 | 0.025 | 0.300 |
| 7 | texture_baseline_v0.2.0 | top_k_mean | 0.8310 | 0.087 | 0.032 | 0.250 |
| 8 | texture_baseline_v0.2.0 | prototype_medoid | 0.7551 | 0.092 | 0.034 | 0.300 |

**Diagnostic ranking on LeaData: DINOv2 + nearest_neighbor leads.**

- DINOv2 + nearest_neighbor leads at K=5 on both label strategies on LeaData.
- DINOv2's mean_top1_margin is ~10× texture_baseline's on item_id and ~8× on species, which is what enables threshold-based abstention on this data.
- **Phase 11 design implication, with the open question explicitly preserved:** Shadow logging must record nearest_neighbor, top_k_mean, prototype_centroid, and prototype_medoid scores **in parallel** for every region in every session. The LeaData diagnostic ranking is a starting hypothesis for which strategy to promote, not a decision. Real-capture intra-class variance is expected to be substantially higher than LeaData's, and the strategy ranking may flip on real data — see the Open Question callout in §1. Production strategy selection happens at promotion-decision time on real-capture evidence, not at design time on public-data evidence.

---

## 6. Abstention Curve Elbow at K=5

`prototype_centroid_with_abstention` is the same scoring as `prototype_centroid` with the abstention filter applied. The elbow analysis below uses the threshold sweep (score thresholds {0.0, 0.5, 0.6, 0.7, 0.8, 0.85, 0.9} × margin thresholds {0.0, 0.02, 0.05, 0.1, 0.15}).

### 6.1 DINOv2 + abstention at K=5

| Label | score_thr | margin_thr | Acc after abst | Abst rate | Coverage |
|---|---:|---:|---:|---:|---:|
| item_id | 0.80 | 0.10 | **0.9984** | 0.197 | 0.803 |
| species | 0.70 | 0.15 | **1.0000** | 0.293 | 0.707 |

**Elbow location (DINOv2 item_id at K=5):** baseline accuracy without abstention is 0.977. Pushing accuracy to 0.998 costs 19.7% abstention rate. The next meaningful gain (to 0.9999+) would require >40% abstention rate, which is operationally unattractive. The 80%-coverage / 99.8%-accuracy point is the elbow.

**Elbow location (DINOv2 species at K=5):** baseline 0.939, abstention pushes to 1.000 at 29.3% abstention rate. Higher gain (per-class accuracy uniformity) but at higher abstention cost.

### 6.2 texture_baseline + abstention at K=5

| Label | score_thr | margin_thr | Acc after abst | Abst rate |
|---|---:|---:|---:|---:|
| item_id | 0.00 | 0.00 | 0.9263 | 0.000 |
| species | 0.00 | 0.00 | 0.8405 | 0.000 |

**Texture_baseline cannot use threshold-based abstention productively at the < 30% abstention budget.** Score distributions are too tightly clustered (mean similarity 0.94 with margins ~0.02) — any threshold above 0.0 either rejects everything or rejects nothing. To reach abstention rates compatible with the < 30% budget, the threshold has to be 0.0/0.0, which means no abstention at all. This isn't a limitation of the prototype_centroid_with_abstention strategy — it's a limitation of the embedding's score geometry.

**Operational implication for `region-scoring-service` threshold_profiles:** threshold profiles need to be model-version-specific. The current `texture_baseline_default` profile has `strong_match_threshold=0.85`, which sits inside the bulk of the texture_baseline same-class distribution and isn't separating signal from noise on LeaData. A new `dinov2_base_frozen_default` profile should be created with **candidate / diagnostic** status — populated with the LeaData-derived starting values (`score_threshold=0.80, margin_threshold=0.10`) and explicitly **not** wired into any decision rule until recalibrated on real-distribution data during Phase 11 shadow operation. The 0.80 / 0.10 numbers are starting points for shadow logging, not production thresholds.

---

## 7. OOD Rejection Findings (Diagnostic Only)

FabricNET (woven fabric microscopy) used as OOD against LeaData (leather microscopy) support classes. 500 OOD queries scored against 100 episodes per (model, K) cell. "Rejection rate" here is the threshold-sweep mean abstention rate — what fraction of OOD queries get filtered out across the full threshold sweep.

| Model | K | Mean rejection across thresholds | Max (high-threshold) |
|---|---:|---:|---:|
| texture_baseline_v0.2.0 | 1 | 0.801 | 1.000 |
| texture_baseline_v0.2.0 | 5 | 0.799 | 1.000 |
| texture_baseline_v0.2.0 | 10 | 0.805 | 1.000 |
| dinov2_base_frozen_v0.1.0 | 1 | 0.937 | 1.000 |
| dinov2_base_frozen_v0.1.0 | 5 | 0.944 | 1.000 |
| dinov2_base_frozen_v0.1.0 | 10 | 0.945 | 1.000 |

**Diagnostic-only framing.** FabricNET-vs-LeaData is a structurally easy OOD problem — completely different material with different microscopic properties. A strong rejection rate here proves embeddings aren't catastrophically broken on out-of-domain inputs. It does **not** prove OOD robustness on the harder cases:

- Same material under novel illumination
- Different leather variant not seen in support
- Damaged or altered material
- Brand-spoofed counterfeits with similar surface texture

**Read this row of evidence as a sanity check, not a calibration.** Real OOD calibration must wait for harder OOD probes — at minimum, leather captured under different illumination, ideally a curated counterfeit-leather set.

That said: DINOv2 outperforms texture_baseline by ~14 percentage points on this easy OOD task too. Consistent with everything else.

---

## 8. Capture Protocol Implications

| Question | Answer (diagnostic only) |
|---|---|
| Smallest K reaching within 0.02 of asymptotic accuracy (DINOv2 + NN, item_id) | K=3 (acc 0.971; asymptote ~0.989 at K=10) |
| Smallest K reaching within 0.02 of asymptotic accuracy (DINOv2 + NN, species) | K=10 (curve still rising; asymptote not reached) |
| Smallest K with stable variance (p95-p05 ≤ 0.05) (DINOv2 + NN, item_id) | K=5 (spread 0.040) |
| Smallest K with stable variance (DINOv2 + NN, species) | K=10 (spread 0.050) |
| Suggested capture protocol K from this evidence | **K=5 for fine-grained labels, K=10 for coarse labels** |

**IMPORTANT CAVEAT — RESTATED, DELIBERATELY.**

LeaData species is 4 classes (Cow / Goat / Sheep / Buffalo) — a coarser distinction than authentic-vs-counterfeit Chanel caviar 2022 at brand granularity. LeaData item_id is 16 classes — closer in granularity to real authentication, but the within-class image set is consistent device, consistent lighting, consistent material handling. Real luxury authentication will face:

- Lower within-class consistency (different devices, lighting, operators)
- Higher between-class similarity (counterfeits explicitly designed to mimic authentic surface)
- Narrower margins (1-2 mm difference in stitch density, micro-scale tool marks)

**The required K on real luxury data is likely higher than what these results suggest, not the same.** Use these K values as a diagnostic floor for protocol design, not a target. Treat the gold-set capture protocol as needing K=10 minimum per region, plan for K=15-20, and let real-data evidence pull it down if it can.

---

## 9. Limitations

- Public texture data only; no luxury authentication validation.
- Labels are species / item_id, not authentic / counterfeit at brand granularity.
- DINOv2 is frozen (no fine-tuning on microscopy).
- Results may not transfer to real lab captures.
- `learned_metric_v0.2.0` was not part of the comparison because no embeddings were persisted on LeaData under that model version. The trained artifact was not registered in `model_versions` and not uploaded to S3 (multiple candidate `.pt` files exist locally from Phase 5/6/7/8/9 runs, but no canonical artifact is designated). Closing this gap is non-trivial — it requires designating a canonical artifact, S3 upload, `model_versions` registration, and embedding generation — and is therefore deferred to Phase 11A as a historical-comparison carryover task. The 2-way DINOv2-vs-texture_baseline comparison stands; the 3-way learned_metric comparison is held until Phase 11A closes the gap.
- No PatchCore anomaly path tested yet (Phase 10c).
- No real microscope / gold-set data yet.
- Within-class variance under controlled capture conditions does not predict variance under real-world capture conditions.
- OOD rejection on FabricNET is an easy OOD problem; results are diagnostic, not calibration.

---

## 10. Phase 10c (PatchCore) and Phase 11 (Shadow Integration) Assessment

### 10.1 Phase 11 — Shadow Integration

**Recommended: proceed to shadow integration. The production decision authority remains `texture_baseline_v0.2.0` for the entire shadow period.**

This is a deliberate conservative framing: the empirically-weaker model (texture_baseline) continues to make the production decision while the empirically-stronger candidate (DINOv2) runs alongside in a shadow path, gathering real-capture evidence. Promotion is gated on pre-declared criteria, evaluated against that real-capture evidence — not on the LeaData diagnostic ranking.

The detailed plan, including pre-declared promotion criteria, per-region K calibration, parallel-strategy logging, and the 4-week / 100-session shadow window, lives in the dedicated Phase 11 plan: see [DINOv2 Shadow Integration Plan](../roadmaps/dinov2-shadow-integration-plan.md).

Critical design constraints carried forward from the Open Question in §1:

- Phase 11 must **not** lock in nearest_neighbor as the production inference strategy. NN, top_k_mean, prototype_centroid, and prototype_medoid scores must be logged in parallel for every region in every session.
- The (0.80, 0.10) threshold values from §6 are LeaData-derived starting points. The `dinov2_base_frozen_default` threshold profile must be registered as **candidate / diagnostic** only and recalibrated on real-distribution data before any decision-path use.
- The "single dominant combination" framing reflects LeaData's class structure under unusually consistent capture conditions, not a property that necessarily transfers to luxury microscopy. The Phase 11 design is intentionally **strategy-agnostic at design time** — strategy selection is a promotion-time decision.

### 10.2 Phase 10c — PatchCore Anomaly Detection

**Recommended: lower priority, not deferred indefinitely.**

The case for PatchCore weakens because DINOv2 + abstention already resolves most "uncertain zone" decisions cleanly:
- 99.8% accuracy at 80% coverage on item_id (DINOv2 K=5)
- 100% accuracy at 71% coverage on species (DINOv2 K=5)

The remaining 20-30% abstention cohort might still benefit from an anomaly-detection second-opinion path — but the marginal value is no longer obvious. PatchCore makes the strongest case when the metric path's "I don't know" cohort is large (say >40%), and DINOv2 has compressed it to under 30%.

**However:** the OOD evaluation here is a structurally easy OOD problem. Harder OOD (illumination shifts on real leather, novel leather variants, brand-spoofed counterfeits) is exactly the regime where PatchCore's patch-level anomaly scoring could outperform a global-similarity-with-threshold approach. So PatchCore is not killed by these results — it just shifts from "next phase" to "phase that runs after real lab data exists and a hard-OOD probe set is available."

**Suggested ordering revision:**

- Phase 11 (shadow integration of DINOv2 + nearest_neighbor + abstention): run now, produces real-capture data.
- Phase 10c (PatchCore): defer until at least the first 100 real-capture sessions exist and produce a hard-OOD probe set (e.g., the same authentic items captured under three illumination conditions, plus first counterfeit candidates if available).
- Future: episodic ProtoNet training, LoRA fine-tuning of DINOv2 on luxury microscopy.

---

## 11. Reproducibility

- Run config: `experiments/outputs/few-shot/<timestamp>/run_config.json` (seed 42, full grid spec).
- Per-cell summary: `few_shot_summary.json`
- Episode-level results: `per_episode_results.csv`
- Threshold sweep curves: `abstention_curves.csv`
- Cross-tabulation: `make compare-few-shot`
- Re-running embeddings: `make generate-dinov2-embeddings`
- Re-running grid: `make few-shot-full`

Git SHA at time of run: see `run_config.json["git_sha"]` per output directory.
