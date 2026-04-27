# OOD Experiment Results

**Date:** 2026-04-27
**Status:** Diagnostic — no production authentication claims

---

## 1. Executive Summary

Phase 4 of the Experiment Workbench compared six OOD scoring methods using
FabricNET and LeaData as cross-domain in-distribution / out-of-distribution
pairs. The experiment ran in both directions:

- **FabricNET as ID, LeaData as OOD:** Near-perfect separation (AUROC 1.0 for
  max_similarity, similarity_gap, and LOF). Fabric-texture embeddings are
  clearly distinguishable from leather-texture embeddings when fabric is the
  reference domain.

- **LeaData as ID, FabricNET as OOD:** Poor separation (AUROC ~0.50–0.57).
  With a large, diverse leather reference set (971 embeddings), fabric-texture
  queries are not reliably flagged as OOD by any simple method.

This asymmetry is informative: OOD detection depends heavily on the reference
distribution's size and diversity. A small, tight reference set (FabricNET, 104
refs) cleanly rejects dissimilar queries. A large, diverse set (LeaData, 971
refs) absorbs cross-domain queries because some leather textures resemble some
fabric textures in the hand-crafted feature space.

These are public texture/material datasets. Results validate OOD scoring
behavior — they do **not** measure luxury authentication OOD performance.

---

## 2. Experiment Setup

| Parameter | FabricNET as ID | LeaData as ID |
|---|---|---|
| In-distribution dataset | `external_fabricnet_v0.1.0` | `external_leadata_v0.1.0` |
| OOD dataset | `external_leadata_v0.1.0` | `external_fabricnet_v0.1.0` |
| Model | `texture_baseline_v0.2.0` | `texture_baseline_v0.2.0` |
| Reference embeddings | 104 (train+validation) | 971 (train+validation) |
| ID test queries | 26 | 229 |
| OOD queries | 229 | 26 |
| K | 5 | 5 |

---

## 3. FabricNET as ID, LeaData as OOD

| Method | AUROC | ID mean | OOD mean | Separation | Overlap | Threshold | False OOD | Missed OOD |
|---|---|---|---|---|---|---|---|---|
| max_similarity | **1.0000** | 0.0022 | 0.0519 | 0.0497 | 0.0000 | 0.0101 | 0.0000 | 0.0000 |
| mean_topk | 0.9988 | 0.0041 | 0.0530 | 0.0489 | 0.0345 | 0.0177 | 0.0000 | 0.0393 |
| similarity_gap | **1.0000** | 0.0022 | 0.0519 | 0.0497 | 0.0000 | 0.0101 | 0.0000 | 0.0000 |
| knn_density | 0.9988 | 0.0041 | 0.0530 | 0.0489 | 0.0345 | 0.0177 | 0.0000 | 0.0393 |
| mahalanobis | 0.8846 | 0.3824 | 1.0000 | 0.6176 | 0.0000 | 1.0000 | 0.2308 | 0.0000 |
| lof | **1.0000** | 0.0030 | 0.1048 | 0.1018 | 0.0000 | 0.0206 | 0.0000 | 0.0000 |

**Interpretation:** With a small, tight fabric-texture reference set, all
similarity-based methods achieve near-perfect or perfect AUROC. Leather-texture
queries are clearly outside the fabric reference distribution. Even the simple
`max_similarity` method (current production proxy) achieves AUROC 1.0.

Mahalanobis distance has lower AUROC (0.8846) and a 23% false OOD rate,
suggesting the covariance structure of the small reference set doesn't
generalize well.

---

## 4. LeaData as ID, FabricNET as OOD

| Method | AUROC | ID mean | OOD mean | Separation | Overlap | Threshold | False OOD | Missed OOD |
|---|---|---|---|---|---|---|---|---|
| max_similarity | 0.5017 | 0.0332 | 0.0679 | 0.0346 | 0.7819 | 0.0637 | 0.0000 | 0.5769 |
| mean_topk | 0.4940 | 0.0351 | 0.0689 | 0.0338 | 0.7692 | 0.0647 | 0.0000 | 0.5769 |
| similarity_gap | 0.5017 | 0.0332 | 0.0679 | 0.0346 | 0.7819 | 0.0637 | 0.0000 | 0.5769 |
| knn_density | 0.4940 | 0.0351 | 0.0689 | 0.0338 | 0.7692 | 0.0647 | 0.0000 | 0.5769 |
| mahalanobis | 0.5677 | 0.9135 | 1.0000 | 0.0865 | 0.0000 | 1.0000 | 0.8646 | 0.0000 |
| lof | 0.4958 | 0.0711 | 0.1589 | 0.0878 | 0.7692 | 0.1283 | 0.0000 | 0.5769 |

**Interpretation:** With a large, diverse leather-texture reference set (971
embeddings), fabric-texture queries are not reliably distinguished. All
similarity-based methods hover near chance (AUROC ~0.50). This makes sense:
the hand-crafted texture features (LBP, Gabor, histograms) capture generic
texture properties, and some fabric textures overlap with leather textures in
this feature space.

Mahalanobis slightly outperforms (0.5677) but has an 86% false OOD rate at its
best threshold — effectively useless.

---

## 5. Cross-Direction Interpretation

The asymmetry between directions reveals an important property of OOD detection:

1. **Reference set size and diversity matter more than scoring method.** A small,
   homogeneous reference set naturally rejects dissimilar queries. A large,
   diverse reference set absorbs cross-domain overlap.

2. **The simple `max_similarity` proxy works well when reference distributions
   are tight.** It achieves AUROC 1.0 on the FabricNET-as-ID direction. More
   sophisticated methods (Mahalanobis, LOF) don't improve on this case.

3. **No simple scoring method solves the diverse-reference case.** When the
   reference set is large and diverse (LeaData), all methods fail. This
   suggests that for luxury authentication, reference library curation and
   region-scoped comparison may be more important than OOD scoring sophistication.

4. **The current production proxy (`1 - max_similarity`) is adequate for its
   current role** as a simple interpretation signal. Replacing it with a more
   complex method would not help until reference distributions are better
   curated per region and per brand.

---

## 6. Recommendation for Query-Image Interpretation

1. **Keep the current simple similarity-based interpretation bands** in the
   query-image UI. They are adequate for the current diagnostic role.

2. **Do not promote dedicated OOD scoring to the UI** until validated on real
   microscope/gold-set data with per-region reference distributions.

3. **Future OOD improvement should focus on reference curation, not scoring
   methods.** Region-scoped, brand-scoped, and material-scoped reference sets
   will naturally improve OOD detection by reducing cross-class overlap.

4. **Re-run these experiments on real microscope/gold-set data** once available,
   with per-region reference distributions instead of full-dataset references.

5. **Consider adding Mahalanobis distance as a secondary signal** in diagnostic
   reports (not UI) once per-region reference sets are large enough for
   meaningful covariance estimation (25+ embeddings per region).

---

## 7. Limitations

- FabricNET and LeaData are public texture/material datasets, not luxury
  authentication datasets.
- ID/OOD distinction is between dataset domains (fabric vs leather), not between
  authentic and counterfeit luxury items.
- Hand-crafted features (texture_baseline_v0.2.0) may not capture the
  discriminative properties needed for luxury OOD detection. Learned embeddings
  may perform differently.
- The asymmetry in results is partially explained by the 10:1 size ratio between
  reference sets (971 vs 104). A balanced comparison might show different behavior.
- These results are diagnostic only and do not justify production behavior changes.

---

## 8. Related Documents

- [Baseline Feature Comparison Results](baseline-feature-comparison-results.md)
- [Preprocessing Comparison Results](preprocessing-comparison-results.md)
- [Region-Specific Analysis Results](region-specific-analysis-results.md)
- [Experiment Workbench Plan](../roadmaps/experiment-workbench-plan.md)
- [ML Improvement Roadmap](../roadmaps/ml-improvement-roadmap.md)
