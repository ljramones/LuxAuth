# Region-Specific Analysis Results

**Date:** 2026-04-27
**Status:** Diagnostic — no production authentication claims

---

## 1. Executive Summary

Phase 3 of the Experiment Workbench established a region-specific analysis
framework for inspecting dataset coverage, readiness, and per-region embedding
behavior.

Both public external datasets now have 100% `texture_baseline_v0.2.0` embedding
coverage:

- **FabricNET** maps to `EXTERNAL_FABRIC_TEXTURE` — 130 images, cluster
  separation 0.9242, 100% NN agreement.
- **LeaData V1** maps to `EXTERNAL_LEATHER_TEXTURE` — 1,200 images across 16
  sample groups, cluster separation 0.9418, 100% NN agreement.

These results validate the region-analysis tooling and confirm that the
texture/material diagnostic pipeline behaves consistently on public data. They
do **not** measure luxury authentication accuracy — that requires real
microscope/gold-set capture data with actual luxury item regions.

---

## 2. Experiment Scope

| Parameter | Value |
|---|---|
| Datasets | `external_fabricnet_v0.1.0`, `external_leadata_v0.1.0` |
| Embedding model | `texture_baseline_v0.2.0` (256-dim, LBP+Gabor) |
| Analysis script | `scripts/run_region_analysis.py` |
| Split scope | all |
| External regions | included (`--include-external-regions`) |
| Min region images | 10 (default) |

Generated outputs (JSON, Markdown, CSV) are written to the gitignored
`experiments/outputs/region-analysis/` directory. This document is the curated
summary.

---

## 3. Results Table

| Dataset | Region | Images | Items | v0.2 Embeddings | Coverage | Readiness | Cluster Sep | NN Agree | Warnings |
|---|---|---:|---:|---:|---:|---|---:|---:|---|
| FabricNET | EXTERNAL_FABRIC_TEXTURE | 130 | 130 | 130 | 100% | training_candidate | 0.9242 | 100% | external_dataset_only |
| LeaData V1 | EXTERNAL_LEATHER_TEXTURE | 1,200 | 16 | 1,200 | 100% | training_candidate | 0.9418 | 100% | external_dataset_only |

---

## 4. FabricNET Region Analysis

FabricNET is represented as `EXTERNAL_FABRIC_TEXTURE`. The dataset contains 130
images — one per fabric sample — spanning multiple woven fabric types.

- **Readiness:** `training_candidate` based on image count (130 >= 100 threshold).
- **Embedding coverage:** 100% for `texture_baseline_v0.2.0`.
- **Cluster separation:** 0.9242 — high intra-class similarity with clear
  separation between fabric types.
- **NN agreement:** 100% — every image's nearest neighbor is the same fabric type.

**Caution:** FabricNET labels are fabric-type categories, not authentic/counterfeit
luxury labels. These results should not be interpreted as luxury-canvas
authentication performance.

---

## 5. LeaData Region Analysis

LeaData V1 is represented as `EXTERNAL_LEATHER_TEXTURE`. The dataset contains
1,200 images across 16 inferred sample groups (leather species/types). Splits
are assigned by sample group to avoid intra-item leakage.

- **Readiness:** `training_candidate` based on image count (1,200 >= 100 threshold).
- **Embedding coverage:** 100% for `texture_baseline_v0.2.0`.
- **Cluster separation:** 0.9418 — slightly higher than FabricNET, consistent
  with the richer texture variation in leather surface images.
- **NN agreement:** 100% — every image's nearest neighbor is the same leather type.

**Caution:** LeaData species/sample labels are not luxury-authenticity labels.
These results should not be interpreted as leather-goods authentication
performance.

---

## 6. Interpretation

The region-analysis framework can now answer:

- Which region codes exist in a dataset?
- How many images and items exist per region?
- Whether embeddings exist for the selected model and what coverage percentage?
- What per-region embedding diagnostics (cluster separation, NN agreement,
  recall@K) look like?
- Which regions are external/public-only and flagged accordingly?

Public external regions have high coverage and clean diagnostics. This confirms
the tooling works end-to-end: dataset loading, embedding retrieval, per-region
metric computation, readiness scoring, and report generation.

The next meaningful region-specific work requires real microscope/gold-set
capture data with actual luxury item regions:

- `EXTERIOR_CANVAS`
- `EXTERIOR_LEATHER_GRAIN`
- `STITCHING_DETAIL`
- `HARDWARE_ENGRAVING`
- `INTERIOR_HEAT_STAMP`
- `EDGE_PAINT_DETAIL`
- `ZIPPER_PULL_ENGRAVING`

Until real capture data exists for these regions, region-specific conclusions
about luxury authentication remain out of scope.

---

## 7. Limitations

- Only external public texture regions were analyzed. No luxury item capture
  regions have data yet.
- No authentic-vs-counterfeit discrimination is measured. Public datasets use
  material-type labels, not authenticity labels.
- FabricNET and LeaData are single-purpose public datasets created for material
  science research, not luxury authentication.
- `training_candidate` readiness is based primarily on image count and does not
  imply production training readiness. Label quality, item diversity, split
  integrity, and provenance also matter.
- Region-specific thresholds cannot be calibrated without real labeled data from
  known-authentic and known-counterfeit luxury items.
- Current analysis does not evaluate condition sensitivity or repair sensitivity,
  which are relevant for some luxury item regions (e.g., stitching, hardware).
- Same/different-label metrics are limited for single-label regions — cluster
  separation reflects intra-class structure only.

---

## 8. Recommended Next Steps

1. Keep FabricNET and LeaData as public texture diagnostic benchmarks for
   pipeline validation and feature extractor comparison.
2. Use `texture_baseline_v0.2.0` as the experimental baseline for public texture
   diagnostics.
3. Run region analysis on smoke/lab/gold-set datasets as they become available
   to assess luxury-region coverage and readiness.
4. Use Data Explorer region coverage views to identify missing or sparse regions
   during capture planning.
5. Do not promote external regions (`EXTERNAL_*`) into luxury capture protocols
   — they serve a different diagnostic purpose.
6. Capture real microscope data for Tier 1 and Tier 2 luxury regions before
   drawing any authentication conclusions.

---

## 9. Related Documents

- [Baseline Feature Comparison Results](baseline-feature-comparison-results.md)
- [Preprocessing Comparison Results](preprocessing-comparison-results.md)
- [Inspection Region Taxonomy](../reference/luxury-item-inspection-region-taxonomy.md)
- [Inspection Region Expansion Plan](../roadmaps/inspection-region-expansion-plan.md)
- [Experiment Workbench Plan](../roadmaps/experiment-workbench-plan.md)
- [ML Improvement Roadmap](../roadmaps/ml-improvement-roadmap.md)
- [ML Technology Explained](../ml-technology-explained.md)
