# Local Model Artifact Inventory

**Date captured:** 2026-04-30
**Scope:** Cataloging only. Governance decisions belong to Phase 11A.2 ("Model artifact governance policy"). This document records what currently exists locally so Phase 11A starts from a known state.

---

## Summary

- **10 `.pt` files** found locally, all under `experiments/outputs/`.
- **All artifacts are tagged `learned_metric_v0.2.0`.** No other model versions have local `.pt` artifacts.
- **All artifacts are trained on `external_leadata_v0.1.0`** with `EXTERNAL_LEATHER_TEXTURE` as the single region.
- **None are uploaded to S3.** None are registered in `model_versions`. There is no canonical artifact designation.
- **All artifacts have full sibling provenance** (experiment_record.json, training_metrics.json, evaluation_metrics.json, plus phase-level summary.json). Recovering training configuration and evaluation metrics for any artifact takes seconds, not archaeology.
- **No `.onnx`, `.pth`, `.h5`, or `.safetensors` artifacts** exist locally outside the HuggingFace cache (HF cache is gitignored and out of scope for project artifact governance).

---

## Artifact catalog

All paths relative to repo root.

| # | Path | Size | mtime (Apr 2026) | Phase | Loss / Variant | Backbone | Embed dim | Sibling JSON |
|---:|---|---:|---|---|---|---|---:|---|
| 1 | `experiments/outputs/learned-metric/external_leadata_v0_1_0__learned_metric_v0_2_0__model.pt` | 45.6 MB | Apr 26 22:16 | Phase 5 (base) | contrastive, 20 ep, full train (897) | ResNet18 | 256 | record + training + evaluation |
| 2 | `experiments/outputs/loss-comparison/external_leadata_v0_1_0__learned_metric_v0_2_0__contrastive__model.pt` | 45.6 MB | Apr 27 15:29 | Phase 6 | contrastive, 5 ep, train=300 | ResNet18 | 256 | record + training + evaluation + phase summary |
| 3 | `experiments/outputs/loss-comparison/external_leadata_v0_1_0__learned_metric_v0_2_0__batch_hard_triplet__model.pt` | 45.6 MB | Apr 27 15:25 | Phase 6 | batch_hard_triplet, 5 ep, train=300 | ResNet18 | 256 | record + training + evaluation + phase summary |
| 4 | `experiments/outputs/loss-comparison/external_leadata_v0_1_0__learned_metric_v0_2_0__supervised_contrastive__model.pt` | 45.6 MB | Apr 27 15:29 | Phase 6 | supervised_contrastive, 5 ep, train=300 | ResNet18 | 256 | record + training + evaluation + phase summary |
| 5 | `experiments/outputs/label-strategy-comparison/external_leadata_v0_1_0__learned_metric_v0_2_0__contrastive__model.pt` | 45.6 MB | Apr 27 16:07 | Phase 7 | contrastive | ResNet18 | 256 | record + training + evaluation + phase summary |
| 6 | `experiments/outputs/label-strategy-comparison/external_leadata_v0_1_0__learned_metric_v0_2_0__batch_hard_triplet__model.pt` | 45.6 MB | Apr 27 15:59 | Phase 7 | batch_hard_triplet | ResNet18 | 256 | record + training + evaluation + phase summary |
| 7 | `experiments/outputs/backbone-comparison/external_leadata_v0_1_0__learned_metric_v0_2_0__batch_hard_triplet__model.pt` | 99.1 MB | Apr 27 18:40 | Phase 8 | batch_hard_triplet | **ResNet50** | 256 | record + training + evaluation + phase summary |
| 8 | `experiments/outputs/backbone-comparison/external_leadata_v0_1_0__learned_metric_v0_2_0__contrastive__model.pt` | 99.1 MB | Apr 27 19:53 | Phase 8 | contrastive | **ResNet50** | 256 | record + training + evaluation + phase summary |
| 9 | `experiments/outputs/augmentation-schedule-comparison/external_leadata_v0_1_0__learned_metric_v0_2_0__batch_hard_triplet__model.pt` | 45.6 MB | Apr 27 20:18 | Phase 9 | batch_hard_triplet | ResNet18 | 256 | record + training + evaluation + phase summary |
| 10 | `experiments/outputs/augmentation-schedule-comparison/external_leadata_v0_1_0__learned_metric_v0_2_0__contrastive__model.pt` | 45.6 MB | Apr 27 20:22 | Phase 9 | contrastive | ResNet18 | 256 | record + training + evaluation + phase summary |

**Filename convention.** All artifacts follow `<dataset>__<model_version>__<variant>__model.pt`, where `<variant>` encodes the training-regimen sweep dimension for the originating phase. The Phase 5 base (#1) omits `<variant>` because it predates the sweep convention. This naming convention is encoding metadata that should live in a registry; it works as a stopgap but is not a governance solution.

**Sibling provenance.** Every artifact has at minimum:
- `<...>_experiment_record.json` — full training configuration (backbone, dim, loss, epochs, batch size, learning rate, label strategy, train/val/test counts, device, training time)
- `<...>_training_metrics.json` — per-epoch train and validation losses
- `<...>_evaluation_metrics.json` — at-training-time evaluation (cluster_separation, recall@K, NN agreement, per-label / per-region breakdown). Note: this is the model's evaluation on its own test split, not a re-embed-and-evaluate pass against the live `reference_embeddings` table.

Phases 6-9 additionally have `<phase>_comparison_summary.json` aggregating all variants for that phase's sweep with results inline.

---

## Duplication / "same logical model" flag

**All 10 artifacts are tagged `learned_metric_v0.2.0`.** This is a real ambiguity, not a naming inconsistency.

The canonical interpretation requires a decision:

1. **Phase 5 base (#1) is the original `learned_metric_v0.2.0`.** It was trained for 20 epochs on the full training set (897 images) with the contrastive loss configuration that defined the version at the time. Subsequent phases (6-9) reused the `learned_metric_v0.2.0` tag while varying training regimen because no version-bumping convention was established for sweep variants. Each Phase 6-9 `.pt` is technically a different model than Phase 5's, sharing only the version tag.

2. **Multiple files with identical names exist across phases** (e.g., `__contrastive__model.pt` appears in Phase 6, Phase 7, Phase 9, all under the `learned_metric_v0.2.0` tag). These are different artifacts with different training configurations, distinguishable only by their containing directory.

This is the symptom that motivated the Phase 11A.2 model artifact governance workstream. The fix is structural (versioning convention + canonical designation + registry); a one-off `learned_metric` patch leaves the pattern in place for the next training experiment.

---

## Likely canonical-choice candidate (NOT a designation)

If a canonical designation had to be made today, **artifact #1 — the Phase 5 base** — would be the strongest candidate. Reasoning:

- It is the artifact closest to the original semantic intent of `learned_metric_v0.2.0`. ADR-0002 named the embedding dimension and backbone choice for v0.2.0; the Phase 5 base is the artifact produced under that decision.
- It was trained with the largest training budget (20 epochs vs 5 in Phases 6-9; full 897-image training set vs 300 subset).
- Its self-reported evaluation metrics are the strongest of the cohort (cluster_separation 0.5609, recall@1 1.0, recall@3 1.0, recall@5 1.0).
- It predates the sweep variants and is unambiguously "the model" rather than "one of several variants under the same tag."

Caveats that argue against rushing this designation:

- Self-reported evaluation metrics are computed on the model's own test split with no isolation from training-time tuning. A real evaluation requires re-embedding LeaData via `generate_embeddings.py` and computing cluster_separation against the live `reference_embeddings` table (the same path Phase 10 used for texture_baseline and DINOv2). This was the missing input for the Phase 10 3-way comparison and is the exact gap Phase 11A.2 needs to close.
- Phase 6-9 sweep variants discovered training-regimen improvements (e.g., batch_hard_triplet at medium scale showed a ~0.71 cluster_sep on its own evaluation per the augmentation-schedule results). It is plausible that one of those variants, under proper re-evaluation, would outperform the Phase 5 base. The artifact governance policy needs to handle the case where "canonical" isn't simply "earliest" or "best by training-time metric."
- The version tag itself may need rethinking. If multiple sweep variants under `learned_metric_v0.2.0` are kept, the version scheme is hiding information. Either each variant gets its own version (e.g., `learned_metric_v0.2.0_contrastive_20ep_full`, etc.) or the tag is reserved for the canonical artifact and variants live elsewhere.

These are governance design questions for Phase 11A.2, not blockers for inventory.

---

## Dead weight assessment

**None of the 10 artifacts look like dead weight in the "obvious failed experiment" sense.** Every artifact has a successful training run (evaluation_metrics.json exists, no error markers in sibling files), and each was produced by a deliberate sweep variant in its respective phase. None are crash dumps, partial checkpoints, or abandoned hyperparameter probes.

However, a fair fraction are likely **lifecycle dead weight** in the sense of being superseded by their successor experiments without ever being individually promotable:

- The Phase 6 contrastive (#2) and Phase 9 contrastive (#10) artifacts are similar regimens (contrastive loss, ResNet18, 256-d) at different epoch / augmentation settings; only one would survive a "best-per-loss-family" retention policy.
- Several variants exist primarily as comparison anchors for their phase's sweep (e.g., the no-augmentation baseline in Phase 9) and have no standalone value once the comparison is concluded.

The retention policy is exactly the question Phase 11A.2 needs to answer. Candidates for retention principles, recorded here as input to that conversation, not as a recommendation:

- Retain the canonical artifact for each registered `model_version` (designated, not just labeled).
- Retain artifacts referenced by published curated results docs.
- Retain the most recent N months of training output regardless of canonical status, as a safety margin against premature deletion.
- Cold-archive everything else.

**Total disk consumption: ~573 MB.** Not currently a storage problem locally. Not yet uploaded to S3, so not a cloud cost problem either. The retention question is governance hygiene, not capacity pressure.

---

## What this inventory leaves Phase 11A.2 needing

To make artifact governance decisions in minutes rather than archaeology, Phase 11A.2 needs to:

1. **Decide a canonical designation per registered model_version.** For `learned_metric_v0.2.0`, the Phase 5 base (#1) is the strongest candidate but requires re-evaluation against the live `reference_embeddings` path before designation. For DINOv2, no `.pt` exists — the artifact is a HuggingFace pinned revision, which is its own governance pattern that should be reflected in the policy.
2. **Decide a versioning convention for sweep variants.** Either bump the version per variant or move variants out of the canonical version tag.
3. **Decide a retention policy.** What survives, in what location (local / S3 / cold archive), for how long.
4. **Decide a promotion procedure.** Local `.pt` → S3 upload → `model_versions` registration. The mechanism (script, Makefile target, manual procedure with checklist).
5. **Apply the policy to close the `learned_metric_v0.2.0` gap as the first instance.** Designate, upload, register, generate embeddings via `generate_embeddings.py`, update [Few-Shot Prototype Matching Results §3](../datasets/few-shot-prototype-results.md) with the third row.

This inventory provides the ground truth for steps 1-3. Steps 4-5 are policy application and run independently.

---

## Related documents

- [DINOv2 Shadow Integration Plan §9.1 (Phase 11A scope)](../roadmaps/dinov2-shadow-integration-plan.md#91-phase-11a--threshold-profile-design-pass-model-artifact-governance-dinov2-deployment-readiness) — the governance workstream this inventory feeds
- [Few-Shot Prototype Matching Results §11 (limitations)](../datasets/few-shot-prototype-results.md) — where the missing `learned_metric_v0.2.0` row in the comparison is documented as a Phase 11A carryover
- [ADR-0002: Embedding Dimension and Backbone](../../auth-platform/docs/architecture/adr-0002-learned-embedding-dimension-and-backbone.md) — the architectural decision that named `learned_metric_v0.2.0`
- [Phase 10 Retrospective](../retrospectives/phase-10-retrospective.md) — the meta-lessons document where the artifact governance gap is named as a what-didn't-work item
