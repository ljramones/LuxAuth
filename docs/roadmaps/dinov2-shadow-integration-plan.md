# DINOv2 Shadow Integration Plan (Phase 11)

**Status:** Planning document — no code, infrastructure, or decision-behavior changes.
**Production decision authority during the entire shadow period:** `texture_baseline_v0.2.0`. **Unchanged.**
**DINOv2 framing during the entire shadow period:** `shadow_candidate` / `experimental`. **Not** a production authentication authority.

---

## 1. Purpose

Phase 10 diagnostic experiments on public texture data (LeaData species/item_id, FabricNET as out-of-domain) showed that a frozen DINOv2 ViT-B/14 backbone outperforms `texture_baseline_v0.2.0` by a wide margin on the experimental harness. The cluster-separation gap is ~10× on species labels, the support-set stabilization curve plateaus earlier, and the score distribution is wide enough to support meaningful threshold-based abstention. (See [Few-Shot Prototype Matching Results](../datasets/few-shot-prototype-results.md) for the full numbers and the diagnostic-only caveats.)

This plan introduces DINOv2 as a **shadow / candidate** path running alongside the production decision path. The purpose of shadow operation is to collect **real-capture evidence** before any decision-path promotion. The Phase 10 diagnostic ranking is treated as a starting hypothesis, not a decision.

**Conservative shadow framing — named explicitly so it cannot be misunderstood later.**

During the shadow period, the production decision path remains `texture_baseline_v0.2.0`, even though Phase 10 evidence suggests DINOv2 is the empirically stronger candidate on diagnostic data. Running the empirically-weaker model in production for a bounded period to gather operational evidence is a deliberate conservative choice. We are choosing not to deploy DINOv2 to decision authority on the basis of LeaData evidence alone, because LeaData is structurally easier than real luxury microscopy (single device, controlled lighting, no operator variation, no wear, no production-year drift, no counterfeit examples). The shadow period exists to convert "diagnostic-stronger on public data" into "operationally-stronger on real captures, with documented evidence and pre-declared promotion criteria." If the data does not support promotion, DINOv2 stays in shadow or is removed; texture_baseline keeps the decision path.

This framing is recorded here so that future readers — including future versions of this team — cannot interpret the parallel-running models as a hidden tradeoff or an oversight. It is a deliberate choice with a defined exit gate (see §7).

DINOv2 is **not** a production authentication authority during shadow operation. No public communication, certificate language, or downstream system should imply otherwise.

---

## 2. Phase 10 Evidence Summary

All numbers below are from public texture data with unusually consistent capture conditions. They validate the diagnostic harness; they do not validate luxury authentication accuracy or generalization. Full results: [few-shot-prototype-results.md](../datasets/few-shot-prototype-results.md).

### 2.1 Cluster_separation (species and item_id)

| Model | Dim | species cluster_sep | item_id cluster_sep |
|---|---:|---:|---:|
| `texture_baseline_v0.2.0` | 256 | +0.0178 | +0.0423 |
| `learned_metric_v0.2.0` | — | _historical-comparison gap; see §11_ | — |
| `dinov2_base_frozen_v0.1.0` | 768 | **+0.1742** | **+0.2996** |

DINOv2's gap is ≈10× texture_baseline's on species and ≈7× on item_id. Both directions agree. The 768-d vs 256-d dimensionality caveat is noted; the magnitude rules out a normalization artifact.

### 2.2 K-shot stabilization

`dinov2_base_frozen_v0.1.0` + nearest_neighbor on item_id stabilizes by **K=5** (variance spread 0.040 at K=5). On species labels, the curve is still rising at K=10 (variance spread 0.050). `texture_baseline_v0.2.0` + nearest_neighbor is still climbing at K=10 on both label strategies, with 2–3× higher variance spread than DINOv2 at every K. No curve crossings observed — DINOv2 leads at every operational K on both label strategies on LeaData.

### 2.3 DINOv2 abstention curve elbow at K=5

| Label | score_thr | margin_thr | Acc after abstention | Abstention rate | Coverage |
|---|---:|---:|---:|---:|---:|
| item_id | 0.80 | 0.10 | 0.9984 | 0.197 | 0.803 |
| species | 0.70 | 0.15 | 1.0000 | 0.293 | 0.707 |

`texture_baseline_v0.2.0` cannot use threshold-based abstention productively at the < 30% abstention budget — score distributions are too tight (0.94 same / 0.94 diff with margin ≈0.02). The threshold sweep degenerates to "no abstention" at every cell.

### 2.4 OOD sanity vs FabricNET

Mean rejection rate across the threshold sweep: DINOv2 0.93–0.95 vs texture_baseline 0.78–0.81. **Diagnostic only.** FabricNET-vs-LeaData is structurally easy OOD (different material entirely). This is a sanity check that DINOv2 embeddings aren't catastrophically broken on out-of-domain inputs. It is not a calibration of OOD robustness on harder cases (illumination shifts, novel leather variants, brand-spoofed counterfeits).

### 2.5 Caveat — restated

LeaData and FabricNET are public texture datasets with unusually consistent capture conditions: single device per dataset, controlled lighting, no operator variation, no wear/repair/condition signal, no production-year drift, no counterfeit examples. **Results validate diagnostic behavior of the inference harness. They do not validate luxury authentication accuracy or generalization.** All Phase 10 numbers must be re-measured on real-distribution data during shadow operation before they can inform a production decision.

---

## 3. Key External Review Refinements

These six refinements were identified during external review of the Phase 10 results and shape the Phase 11 design.

### 3.1 No NN strategy lock-in before real-data evidence

Nearest_neighbor beat prototype_centroid on LeaData. This is plausibly explained by LeaData's unusually low intra-class variance — single device, controlled lighting, no wear, no operator variation. On real luxury data, intra-class variance will be substantially higher (production years, operators, microscope serial numbers, lighting, wear, repairs, possibly damage), and prototype-based strategies may outperform nearest_neighbor under those conditions.

**Phase 11 must NOT lock in nearest_neighbor.** Shadow logging records nearest_neighbor, top_k_mean, prototype_centroid, and prototype_medoid scores **in parallel** for every region in every session. Production strategy selection is a Phase 11F promotion-time decision based on real-capture evidence, not a Phase 11A design-time decision.

### 3.2 LeaData-derived thresholds are diagnostic, not production

The `(score_threshold=0.80, margin_threshold=0.10)` numbers from the Phase 10 abstention elbow are LeaData-derived starting points. They are **not** production thresholds.

**The `dinov2_base_frozen_default` threshold profile must be registered as candidate / diagnostic only.** It must carry an explicit recalibration step on real-distribution data (Phase 11E) before any production decision use. No region scoring or decision rule may consume the candidate profile until recalibration is complete and reviewed.

### 3.3 Promotion criteria declared before shadow operation begins

Defining promotion criteria after data is in hand creates rationalization risk — observed data shapes the criteria, and the criteria stop being a real bar. This is a well-known failure mode in product analytics and ML evaluation.

**Promotion criteria are declared in §7 of this document, before shadow operation begins.** Adding criteria after data is in hand, or weakening criteria to fit observed results, is explicitly prohibited. Tightening criteria based on operational evidence is permitted, with documented rationale.

### 3.4 Per-region K calibration, not a globally fixed K

K=5 / K=10 from Phase 10 came from public texture data with low intra-class variance. Real luxury data will need higher K. Capture protocol planning targets K=10 minimum, K=15-20 ideal, and ultimately calibrates K **per region**, since regions differ in capture cost and stability:

- Leather/canvas grain: cheap to capture, may stabilize at lower K
- Stitching detail: moderate capture cost
- Hardware engraving: precise placement required, harder to capture
- Heat stamp / embossing: small surface area, varies with wear
- Edge paint: ages and chips, may have high intra-class variance
- Lining material: device-positioning dependent
- Zipper / handle / strap regions: positional and mechanical wear varies

**Phase 11D shadow logging must record support-set K used per region per session** so per-region stability curves can be computed at promotion-decision time (Phase 11E).

### 3.5 PatchCore deferred but not abandoned

Phase 10c (PatchCore-style anomaly detection over an authentic-only memory bank) is deferred. FabricNET-vs-LeaData was structurally easy OOD; it does not validate PatchCore's actual value proposition. PatchCore should be evaluated when real hard-OOD probes exist — illumination shifts on the same material, novel leather variants, counterfeit candidates. Trigger conditions are documented in §12.

### 3.6 Conservative shadow framing named explicitly

During the shadow period, the empirically-weaker model (texture_baseline) makes the production decision while the empirically-stronger candidate (DINOv2) runs in shadow. This is a deliberate conservative choice for evidence gathering, not a hidden tradeoff. Named in §1 and reinforced throughout this document so future readers cannot misinterpret it.

---

## 4. Proposed Model Version

| Field | Value |
|---|---|
| `embedding_model_version` | `dinov2_base_frozen_v0.1.0` |
| Embedding dimension | 768 |
| Backbone | DINOv2 ViT-B/14 frozen image encoder, CLS token, L2-normalized output |
| Trainable weights at initial integration | None (frozen) |
| HuggingFace artifact | `facebook/dinov2-base` |
| Pinned revision | `f9e44c814b77203eaa57a6bdbbd535f21ede1415` |
| Status during shadow | `shadow_candidate` / `experimental` |
| Decision authority during shadow | None (the production decision path uses `texture_baseline_v0.2.0`) |
| Production registration in `model_versions` | Already inserted as part of Pass 1; `is_active = TRUE` is admin metadata, not decision authority |

---

## 5. Shadow Scoring Architecture

### 5.1 What does not change

- The production decision path remains `texture_baseline_v0.2.0`. Region scores, threshold profile, decision rules, certificate language, and downstream services are all unchanged during the shadow period.
- `decision-service` behavior is unchanged.
- `region-scoring-service` decision output is unchanged.
- `threshold_profiles` consumed by the decision path is unchanged.

### 5.2 What is added (shadow-only, log-only)

For each eligible region in each capture session, a parallel shadow scoring path computes and **logs only** (never decides on):

| Quantity | Source | Notes |
|---|---|---|
| `texture_baseline` region score | Existing production path | Recorded for divergence analysis |
| DINOv2 nearest_neighbor score | Shadow path | Top1 cosine similarity to nearest support example per class |
| DINOv2 top_k_mean score (K=3) | Shadow path | Per-class mean over top-3 closest support examples |
| DINOv2 prototype_centroid score | Shadow path | Per-class similarity to centroid of support set |
| DINOv2 prototype_medoid score | Shadow path | Per-class similarity to medoid of support set |
| top1 margin per DINOv2 strategy | Shadow path | top1_score - top2_score |
| Abstention recommendation per strategy | Shadow path | Boolean: would the candidate threshold profile abstain on this region? |
| Support-set size K used | Shadow path | Recorded per region (per §3.4) |
| Region code | Both paths | For per-region analysis |
| Model / version metadata | Both paths | embedding_model_version, threshold_profile_version |
| Agreement / divergence flag with baseline decision | Derived | Boolean per strategy |

### 5.3 Production strategy selection — explicitly deferred

Production strategy selection (NN vs prototype_centroid vs top_k_mean vs medoid) is a **Phase 11F promotion-time decision** based on real-capture evidence accumulated during the shadow window. It is **not** a Phase 11A design-time decision. The shadow architecture is intentionally strategy-agnostic — all four strategies are logged in parallel, and the comparative analysis runs at promotion-decision time on real data.

This is the load-bearing design constraint of Phase 11. Locking in NN before real-data evidence exists would defeat the purpose of the shadow window.

### 5.4 What this is not

- Not an A/B test on production decisions. The decision path is single-arm (texture_baseline) for the entire shadow period.
- Not a hot-swap candidate. Promotion is a deliberate Phase 11F event after pre-declared criteria are evaluated.
- Not an OOD detector. PatchCore is the planned OOD path; see §12.

---

## 6. Candidate Threshold Profile

### 6.1 Profile definition

| Field | Value |
|---|---|
| `profile_name` | `dinov2_base_frozen_default` |
| `profile_version` | `v0.0.1-candidate` |
| `embedding_model_version` | `dinov2_base_frozen_v0.1.0` |
| `score_threshold` (`strong_match_threshold` in current schema) | 0.80 |
| `margin_threshold` | 0.10 |
| `status` | `candidate` (or `diagnostic`) |
| Provenance | Derived from LeaData species + item_id at K=5 in Phase 10 |
| Decision authority | **None during shadow.** Used by the shadow path only to compute the abstention recommendation logged alongside DINOv2 scores. Not consumed by `region-scoring-service` decision logic. |

**Explicit warning embedded in description / commit / doc:** _LeaData-derived starting values. Not production thresholds. Requires real-distribution recalibration before any production decision use. Not promoted._

### 6.2 Schema gap (Phase 11A scope — design conversation, not migration)

Cleanup task C in this pass attempted to register the candidate profile and surfaced a schema design question, not just a missing-column problem.

The visible gaps are:

1. The `threshold_profiles` table has no `margin_threshold` column. Current columns are `strong_match_threshold`, `mismatch_threshold`, `ood_threshold`, `counterfeit_similarity_threshold`. The 0.10 margin threshold from Phase 10's abstention elbow has no clean home.
2. The table has no `description` / `provenance` / `notes` column. The "LeaData-derived, recalibrate before production" warning has no in-row home.
3. `reference_dataset_version` is `NOT NULL`. For shadow operation against future real captures, no real-distribution reference dataset exists yet. Tying the candidate profile to `external_leadata_v0.1.0` would contradict the candidate / diagnostic framing.

Inserting a partial profile (with `strong_match_threshold=0.80` only) was considered and rejected — a downstream caller could read the row and miss the margin requirement entirely.

**The underlying design question, however, is not "which columns are missing."** The non-null `reference_dataset_version` constraint is encoding an implicit design decision: that threshold profiles are always calibrated for a specific data distribution. Candidate and diagnostic profiles violate this assumption — they exist precisely because no real-distribution calibration has happened yet. The right move is to make the assumption explicit by tying the constraint to the `status` field:

- `status = active` → real-distribution calibration required; `reference_dataset_version` must be a real lab dataset; consumed by decision logic.
- `status = candidate` → calibrated against shadow-period or pending real data; `reference_dataset_version` may be a placeholder or pending; not consumed by decision logic.
- `status = diagnostic` → calibrated against public-data diagnostic experiments (e.g., LeaData, FabricNET); `reference_dataset_version` points at the diagnostic dataset; never consumed by decision logic; retained for traceability.
- `status = retired` → previously active profile that has been superseded; retained for audit-chain reconstruction; never consumed by decision logic.

**Phase 11A scope (design pass + minimal migration):**

- Make the `status`-vs-`reference_dataset_version` design explicit in the schema (CHECK constraint, partial index, or enum) rather than enforcing it only in application code.
- Add `margin_threshold` (or generalize the threshold representation if more thresholds are anticipated).
- Add `description` / `provenance` / `notes` to capture provenance and warnings in-row.
- Decide whether candidate/diagnostic profiles live in `threshold_profiles` with a status field, or in a separate `candidate_threshold_profiles` table. Either is defensible; the choice affects how Phase 11D code reads profiles.
- Once the schema reflects the design, register the candidate profile per §6.1.

The design pass is small but should not be rushed — getting the status taxonomy right now avoids retrofitting it later when more candidate profiles accumulate.

### 6.3 Recalibration trigger

The candidate profile is **never** consumed by decision logic. It exists to inform shadow-path abstention recommendations and to serve as the starting point for Phase 11E recalibration. After Phase 11E completes, a successor profile (e.g., `dinov2_base_frozen_default_v1` with `status=draft`, then `active` after review) is created and registered. The original `v0.0.1-candidate` profile is retained for historical traceability.

---

## 7. Promotion Criteria — Pre-declared

DINOv2 may move from shadow status to production decision authority only after **all** of the following are satisfied. These criteria are declared **before** Phase 11D shadow operation begins. Adding criteria after data is in hand, or weakening criteria to fit observed results, is explicitly prohibited. Tightening criteria based on operational evidence is permitted, with documented rationale and a recorded review.

| # | Criterion | Notes |
|---:|---|---|
| 1 | Minimum **4 weeks** of shadow operation calendar time | Calendar weeks, not "session weeks" — drift, seasonality, and operator rotation need wall-clock exposure |
| 2 | Minimum **100 real capture sessions** with full shadow logging | Sessions must hit the production capture path, not synthetic / replay |
| 3 | Expert-reviewed subset of at least **N divergence cases** | N to be set in Phase 11D; suggested **N ≥ 20**. Divergence = baseline and shadow disagree on at least one strategy |
| 4 | DINOv2 shows **better or equal** concordance with expert review than texture_baseline on the reviewed subset | Both directions count: DINOv2 gets credit when expert agrees with shadow over baseline; loses credit when expert agrees with baseline over shadow |
| 5 | Abstention curve **recalibrated on real-distribution data** | Phase 11E output. Must identify a usable elbow at < 30% abstention rate, or document why the elbow is acceptable at higher abstention |
| 6 | Inference strategy **selected from real-data evidence**, with documented rationale | Not the LeaData ranking. Selection methodology must be recorded — which metric was optimized, on which subset, with what cross-validation |
| 7 | **No systematic failure mode** identified in divergence logs | Specific brands, regions, capture conditions, or operators where DINOv2 systematically misclassifies. Even one such mode should pause promotion until investigated |
| 8 | Region-specific performance analysis completed; **per-region K calibration data captured** | Phase 11D logging requirement, Phase 11E analysis requirement |
| 9 | Condition / repair / wear cases reviewed and behavior documented | If shadow logging surfaces wear-related divergence, the behavior must be characterized before promotion (not necessarily solved) |
| 10 | False-positive risk reviewed against domain-realistic adversarial probes if available | Counterfeit candidates, brand-spoofed surfaces. If unavailable, document the gap |

**If any criterion is not satisfied:** options are (a) extend shadow operation, (b) revise approach, (c) document why the criterion is unattainable and seek explicit waiver with rationale. Promotion without satisfying criteria — or with weakened criteria — is a process violation.

---

## 8. Per-Region K Calibration

### 8.1 Why a global K is wrong

K=5 / K=10 from Phase 10 came from public texture data with low intra-class variance. Real luxury data will have higher intra-class variance from:

- Production-year variation (different leather batches, different tooling)
- Operator differences (positioning, focus, exposure)
- Microscope serial-number variation (sensor noise, optical aberrations, calibration drift)
- Lighting variation (illumination geometry, color temperature, ambient leak)
- Wear patterns (use-induced surface change, polishing, oxidation)
- Repair or alteration (re-stitched seams, replaced hardware, refinished edge paint)

Higher intra-class variance pushes the support-set stabilization curve to the right — more shots are needed before scoring stabilizes.

### 8.2 Initial capture protocol recommendation

- **K=10 minimum** per important region.
- **K=15-20 target** where capture cost permits.
- K calibrated **per region**, not globally fixed.

### 8.3 Regions to calibrate independently

Capture cost and stability vary by region:

- Leather / canvas grain
- Stitching detail
- Hardware engraving
- Heat stamp / embossing
- Edge paint
- Lining material
- Zipper / handle / strap regions

Each region's stability curve is computed independently from real-capture support-set data accumulated during shadow operation.

### 8.4 Phase 11 logging requirement

Phase 11D shadow logging must record `support_set_size_k` per region per session. Phase 11E recalibration analysis computes per-region K-stability curves and proposes per-region K targets for the production capture protocol, replacing the LeaData-derived global K.

---

## 9. Implementation Phases

This is a planning document. Implementation begins in Phase 11A as a separate work item.

### 9.1 Phase 11A — Threshold profile design pass, model artifact governance, DINOv2 deployment readiness

Phase 11A is structurally three workstreams that are easy to confuse with one-off fixes. Each is treated as a small but explicit design pass, not a migration ticket.

**11A.1 — Threshold profile schema design pass**

- Surface and resolve the `status`-vs-`reference_dataset_version` design question per §6.2. The non-null constraint encodes an implicit assumption that profiles are always real-data-calibrated; candidate and diagnostic profiles violate that assumption. The fix is to make the assumption explicit, not to silently relax the constraint.
- Decide the status taxonomy (`active` / `candidate` / `diagnostic` / `retired` is the proposed shape) and how each interacts with `reference_dataset_version`, decision-logic consumption, and audit retention.
- Add `margin_threshold` column (or generalize threshold representation if more thresholds are anticipated).
- Add `description` / `provenance` / `notes` column.
- Once schema supports it, register `dinov2_base_frozen_default` candidate profile per §6.1.

**11A.2 — Model artifact governance policy (broader than learned_metric)**

The `learned_metric_v0.2.0` gap surfaced a structural lifecycle gap: training experiments produce `.pt` artifacts in `experiments/outputs/` but there is no canonical promotion path from local artifact to S3-uploaded, `model_versions`-registered model. This gap will recur on every future training experiment if not addressed structurally. A one-off fix on `learned_metric` leaves the underlying problem in place.

The policy question to answer: when an experiment produces a candidate model artifact, what is the explicit promotion path from local file to canonical S3-registered `model_versions` row, and what is the retention policy for non-promoted experimental artifacts?

The answer does not need to be elaborate. It needs to exist. A one-page document covering:

- When does a training experiment's output become a candidate for promotion (criteria — accuracy threshold, validation set, reviewer sign-off)?
- What designates one artifact as canonical when an experiment runs multiple variants (loss / backbone / augmentation sweep)?
- What is the upload + registration mechanism (script, Makefile target, or manual procedure)?
- What is the retention policy for non-promoted experiment artifacts (delete after N days, archive cold, retain indefinitely)?
- Who has authority to promote, retire, or delete?

Once the policy exists, apply it to close the `learned_metric_v0.2.0` historical gap as the policy's first instance: designate a canonical `.pt` artifact (likely the Phase 5 base, given that subsequent phases varied training regimen), upload to S3, register in `model_versions`, generate LeaData embeddings via `generate_embeddings.py`, and update [Few-Shot Prototype Matching Results §3](../datasets/few-shot-prototype-results.md) with the third row.

**11A.3 — DINOv2 deployment readiness**

- Confirm `dinov2_base_frozen_v0.1.0` is registered in `model_versions` (already inserted in Pass 1).
- Confirm embedding-service production deployment can serve DINOv2 embeddings (transformers / safetensors pinned, HF cache volume, model rebuild rolled to the production environment).
- Establish or update the relevant ADR (`auth-platform/docs/architecture/adr-0002-learned-embedding-dimension-and-backbone.md`, or a new `adr-0003-dinov2-shadow-integration.md` if scope warrants — decision belongs to 11A).

### 9.2 Phase 11B — DINOv2 reference-dataset re-embedding and Data Explorer coverage

- Generate DINOv2 embeddings for all governed reference datasets where DINOv2 will be used in shadow scoring.
- Update Data Explorer / workbench tooling to display DINOv2 alongside texture_baseline.
- Verify pgvector storage and HNSW index performance at scale (768-d at production reference-library scale; capacity planning per §13).

### 9.3 Phase 11C — DINOv2 query-image support in the workbench

- Capture-workbench query path supports DINOv2 scoring alongside existing texture_baseline scoring.
- Side-by-side comparison view for diagnostic use (per §11).
- Detailed UX specification belongs to this phase.

### 9.4 Phase 11D — Dual-strategy DINOv2 shadow logging in the production scoring path

- `region-scoring-service` computes and logs all four DINOv2 strategies in parallel with the production texture_baseline decision (per §5.2).
- Production decision behavior unchanged.
- New audit / log records populated per region per session (per §10).
- Per-region K logging captured (per §8.4).
- **This is the start of the 4-week / 100-session shadow window** (per §7 criteria 1–2).

### 9.5 Phase 11E — Real-capture threshold and strategy recalibration

After sufficient shadow data accumulates:

- Recalibrate `dinov2_base_frozen_default` thresholds on real distributions; identify the abstention curve elbow on real-distribution data.
- Compare nearest_neighbor vs top_k_mean vs prototype_centroid vs prototype_medoid on real-capture data; document strategy selection rationale.
- Compute per-region K stability curves; propose per-region K targets for the production capture protocol.
- Output: a recalibrated successor threshold profile in `draft` status and a strategy-selection recommendation, both gated on Phase 11F review.

### 9.6 Phase 11F — Promotion decision review

- Apply §7 promotion criteria to accumulated evidence.
- If criteria are satisfied, propose promotion with documented rationale; activate the recalibrated threshold profile; switch decision-path embedding model to DINOv2.
- If criteria are not satisfied, document gaps and either extend shadow operation or revise approach.
- Promotion is a deliberate event with a written record, not an automatic flip.

---

## 10. Data Model and Audit Needs

The shadow path must populate two record streams. Naming below is illustrative; final schema is a Phase 11A / 11D decision.

### 10.1 Per-region shadow score record

Proposed table: `shadow_region_scores`

| Field | Type | Notes |
|---|---|---|
| `id` | uuid | Primary key |
| `session_id` | uuid | References scan_sessions |
| `region_code` | varchar | Per-region analysis key |
| `embedding_model_version` | varchar | `dinov2_base_frozen_v0.1.0` initially; future model versions follow |
| `strategy_name` | varchar | One of `nearest_neighbor`, `top_k_mean`, `prototype_centroid`, `prototype_medoid` |
| `support_set_size_k` | int | Per §8.4 |
| `top1_score` | float | Cosine similarity to top class |
| `top2_score` | float | For margin computation |
| `top1_margin` | float | top1_score - top2_score |
| `predicted_class` | varchar | Whatever the strategy returns; reference_item_id or class label |
| `abstention_recommendation` | boolean | Computed against the candidate threshold profile |
| `threshold_profile_version` | varchar | Which candidate profile produced the abstention recommendation |
| `correlation_id` | uuid | Tying to scan session and audit chain |
| `created_at` | timestamptz | Insertion time |

Index on `(session_id, region_code, strategy_name)` for divergence analysis.

### 10.2 Per-region model agreement record

Proposed table: `model_agreement_events`

| Field | Type | Notes |
|---|---|---|
| `id` | uuid | Primary key |
| `session_id` | uuid | References scan_sessions |
| `region_code` | varchar | |
| `baseline_decision` | varchar | What `texture_baseline_v0.2.0` decided for this region |
| `shadow_decision_per_strategy` | jsonb | DINOv2 decision per strategy: `{nearest_neighbor: ..., prototype_centroid: ..., ...}` |
| `agreement_flag_per_strategy` | jsonb | Boolean per strategy: did this DINOv2 strategy agree with baseline? |
| `divergence_magnitude` | float | Score gap between baseline and the disagreeing-strategy DINOv2 score |
| `reviewer_outcome` | varchar | NULLABLE; populated when expert review occurs (per §7 criterion 3) |
| `reviewer_notes` | text | NULLABLE |
| `created_at` | timestamptz | |
| `reviewed_at` | timestamptz | NULLABLE |

Index on `(reviewer_outcome IS NULL)` partial index for the review queue.

### 10.3 Queryability requirements

Both record streams must be queryable for:

- Phase 11E recalibration analysis (per-region, per-strategy score distributions; per-region K-stability curves)
- Phase 11F promotion decision review (criteria 3, 4, 6, 7, 8 from §7)
- Operational divergence dashboards during shadow operation
- Audit-chain reconstruction for any specific session

---

## 11. Workbench Implications

Plan-level callouts; detailed UX specification belongs in Phase 11C.

- Side-by-side `texture_baseline` vs DINOv2 score display per region.
- NN vs top_k_mean vs prototype_centroid vs prototype_medoid comparison view per region.
- Score / margin / abstention recommendation display.
- Support-set size K visibility per region.
- Divergence event flagging for the expert review queue (per §10.2 reviewer_outcome).
- Export of divergence cases for offline analysis.
- Filter/search by region, by brand, by capture condition, by reviewer outcome.

The workbench must visibly mark DINOv2-derived information as `shadow_candidate / experimental` so that operators do not accidentally treat shadow output as decision authority.

---

## 12. PatchCore Relationship (Phase 10c)

PatchCore-style anomaly detection over an authentic-only memory bank is **deferred but not abandoned**. Phase 10's OOD evaluation used FabricNET-vs-LeaData, which is structurally easy OOD (different material entirely) and does not validate PatchCore's actual value proposition.

PatchCore should be evaluated when **real hard-OOD probes** exist, derived from shadow-period real-capture data.

### 12.1 Trigger conditions

Any one of the following pulls Phase 10c forward from "planned but unscheduled" to "scheduled":

- Shadow-period abstention rate creeps above 30% on production volumes (signal: the metric path's "I don't know" cohort is too large; PatchCore's patch-level anomaly scoring may resolve some of it).
- Failure cases where DINOv2 similarity scores and expert review systematically disagree (signal: similarity is the wrong metric for these cases; an anomaly-detection second-opinion path could help).
- Novel material or variant cases where neither nearest_neighbor nor prototype strategies produce confident outputs.
- Counterfeit-like probes become available — seizures, confidential samples, deliberately purchased counterfeits, brand-spoofed surfaces.
- An operational event (one-off divergence cluster, customer escalation) reveals a class of failure that PatchCore is well-suited to address.

### 12.2 Until then

Until at least one trigger condition is met, Phase 10c remains a planned but unscheduled follow-on. It is documented in the experiment workbench plan and the ML improvement roadmap, with explicit dependencies on real-capture data, hard-OOD probes, and shadow-period evidence.

---

## 13. Risks

Documented explicitly so future readers cannot say they were not warned.

| # | Risk | Mitigation / Acceptance |
|---:|---|---|
| 1 | Public texture results may not transfer to real luxury microscopy | Shadow window exists for exactly this reason. Pre-declared §7 criteria gate promotion |
| 2 | NN-beating-prototype on LeaData is the most likely candidate for non-transfer; intra-class variance differences may flip the result | Parallel-strategy logging in Phase 11D; strategy selection deferred to Phase 11F |
| 3 | DINOv2 frozen weights are trained on natural images; behavior on microscope device artifacts (illumination geometry, sensor noise, optical aberrations) is unvalidated on real luxury data | Shadow logging surfaces this; Phase 11E recalibration analyzes failures |
| 4 | 768-d storage and search cost: DINOv2 embeddings are ≈3× texture_baseline in dimensionality, with proportional impact on pgvector storage, HNSW index size, and query latency | At LeaData scale (1200 embeddings) this is trivial. At production-scale reference libraries (hundreds of thousands of embeddings) capacity planning is required — Phase 11B verification step |
| 5 | Threshold overfitting to LeaData distribution if recalibration is not done rigorously on real data | Phase 11E recalibration is a §7 promotion criterion (criterion 5). Methodology must be documented |
| 6 | Production strategy lock-in if NN is selected without sufficient real-data evidence | Parallel-strategy logging plus §7 criterion 6 (rationale documented). Locking in NN before Phase 11F is a process violation |
| 7 | No verified counterfeit data in current reference library | Phase 11 does not address counterfeit acquisition. Separate strategic concern; flagged for the dataset acquisition strategy roadmap |
| 8 | No adversarial robustness analysis | Counterfeiters who acquire the system can probe DINOv2's failure modes. §7 criterion 10 flags this; mitigation depends on availability of adversarial probes |
| 9 | Shadow operation introduces ongoing computational and storage cost in production for a model that may not promote | Bounded shadow window (4 weeks minimum, with §7 review at the end). If promotion is not warranted, shadow path is removed and the cost stops |
| 10 | Schema gaps in `threshold_profiles` (no margin_threshold, no description, NOT NULL reference_dataset_version) make the candidate profile awkward to register | §6.2 documents the gap; Phase 11A addresses it |
| 11 | `learned_metric_v0.2.0` historical-comparison gap means the shadow integration is justified by a 2-way comparison, not a 3-way comparison | Phase 11A carryover task (Cleanup B); does not block Phase 11D |
| 12 | Operational risk during shadow period: a bug in the shadow path could degrade the production decision path through resource contention, latency, or shared-state corruption | Shadow path must be implementable as a fully out-of-band reader of inputs. No shared mutable state with the decision path. Phase 11D acceptance includes load testing at production scale |

---

## 14. Immediate Pre-Implementation Tasks

The following must be completed before Phase 11A begins. This pass closed (a) and (b) directly and identified (c) and (d) as Phase 11A carryovers.

| Task | Status from this pass | Carryover to Phase 11A |
|---|---|---|
| (a) Results doc tightened with diagnostic-only lead and NN-vs-prototype open-question callout | **Done** in this pass (Cleanup A) | — |
| (b) Phase 11 plan document created with all 15 sections | **Done** in this pass (this document) | — |
| (c) `learned_metric_v0.2.0` LeaData embedding gap closed | **Documented as the surfacing case for a broader gap** in this pass (Cleanup B). Multiple `.pt` artifacts exist locally without canonical designation, S3 upload path, or `model_versions` registration. The pattern will recur on every future training experiment. The right fix is a model artifact governance policy, applied to learned_metric as its first instance — not a one-off `learned_metric` patch | **Carryover to Phase 11A.2 (artifact governance)** |
| (d) `dinov2_base_frozen_default` candidate threshold profile registered | **Documented as the surfacing case for a schema design question** in this pass (Cleanup C). The non-null `reference_dataset_version` constraint encodes an implicit assumption that profiles are always real-data-calibrated; candidate and diagnostic profiles violate that assumption. The right fix is a small design pass on the `status`-vs-`reference_dataset_version` relationship — not a column-addition migration | **Carryover to Phase 11A.1 (threshold profile design)** |

Both carryovers are framed as design passes (small, explicit) rather than migration tickets (mechanical). The distinction matters: getting the design right now avoids retrofitting later when more candidate profiles or unpromoted artifacts accumulate.

---

## 15. Related Documents

### 15.1 Linked

- [Pre-Phase 11 Readiness Checklist](dinov2-shadow-integration-readiness.md) — gate that determines when Phase 11A is appropriate to start
- [Few-Shot Prototype Matching Results](../datasets/few-shot-prototype-results.md) — Phase 10 evidence
- [OOD Experiment Results](../datasets/ood-experiment-results.md) — earlier OOD evaluation context
- [ML Improvement Roadmap](ml-improvement-roadmap.md) — overall ML phase sequencing
- [Experiment Workbench Plan](experiment-workbench-plan.md) — experiment phase tracking
- [ML Technology Explained](../ml-technology-explained.md) — technical primer for non-ML stakeholders

### 15.2 Updates required as part of this pass

- `docs/roadmaps/ml-improvement-roadmap.md` — add Phase 11 (formerly Phase 6 in that doc's numbering, since that file uses its own phase numbering for ML improvement) with sub-phases 11A-11F
- `docs/roadmaps/experiment-workbench-plan.md` — note Phase 11 as the production-bound follow-on to Phase 10
- `docs/roadmap.md` — top-level entry for Phase 11
- `notebooks/EXECUTION_PLAN.md` — Phase 10 marked complete, Phase 11 referenced, Phase 10c marked deferred-pending-shadow-evidence

### 15.3 Phase 11A document creation

- `auth-platform/docs/architecture/adr-0002-learned-embedding-dimension-and-backbone.md` — exists; should be extended to cover DINOv2, or a new ADR (`adr-0003-dinov2-shadow-integration.md`) created as a Phase 11A task. Decision on extend-vs-new belongs to Phase 11A.
