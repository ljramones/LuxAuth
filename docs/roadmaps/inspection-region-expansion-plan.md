# Inspection Region Expansion Plan

**Date:** 2026-04-26
**Status:** Planning — no production authentication claims

## 1. Purpose

The [Inspection Region Taxonomy](../reference/luxury-item-inspection-region-taxonomy.md)
identifies 60+ candidate inspection regions across 15 layers. Implementing all of them at
once would bloat capture protocols, overwhelm operators, fragment datasets, and make ML
evaluation impractical.

This document stages region expansion so that each phase produces usable data, testable
protocols, and measurable ML results before the next phase begins.

---

## 2. Principles

- **Do not add all regions at once.** Each region added to a capture protocol increases
  operator burden and dataset sparsity.
- **Distinguish region statuses:** active, planned, experimental, brand-specific,
  metadata-only, deprecated.
- **Active capture protocols should remain small and testable.** The current 6-region MVP
  protocol stays active until an extended protocol is validated.
- **Region expansion should follow real capture evidence.** Do not add a region to the
  active protocol until at least one microscope acceptance session has captured it
  successfully.
- **Region-specific thresholds and models require real data.** Do not tune per-region
  scoring from taxonomy alone.
- **Optional regions support expert review and condition analysis** without being required
  for automated decisions.

---

## 3. Current Region Baseline

| Region Code | Status | Use | Limitations |
|---|---|---|---|
| EXTERIOR_CANVAS | Active | MVP scan recipe + capture protocol | No leather-grain variant |
| FRONT_LOGO_PRINT | Active | MVP scan recipe + capture protocol | No edge/registration sub-regions |
| INTERIOR_HEAT_STAMP | Active | MVP scan recipe + capture protocol | No foil/depth sub-regions |
| HARDWARE_ENGRAVING | Active | MVP scan recipe + capture protocol | No zipper/rivet/clasp variants |
| STITCHING_DETAIL | Active | MVP scan recipe + capture protocol | No thread/hole/repair sub-regions |
| DATE_CODE_AREA | Planned | Defined in recipe but minimal support | Underdeveloped |
| EXTERNAL_LEATHER_TEXTURE | External | Public dataset pipeline validation | Not a luxury capture region |
| EXTERNAL_FABRIC_TEXTURE | External | Public dataset pipeline validation | Not a luxury capture region |

The current LV monogram canvas handbag protocol (`lv_monogram_canvas_handbag_capture:v0.1.0`)
requires 5 active regions with 12 minimum images total. This remains the only active capture
protocol.

---

## 4. Phase 1 — Region Code Governance

**Goal:** Establish a formal region registry before adding new codes.

### Region Registry

Create `docs/reference/region-code-registry.md` with columns:

| Field | Purpose |
|---|---|
| region_code | Canonical uppercase code |
| display_name | Human-readable name for UI |
| inspection_layer | Which of the 15 taxonomy layers |
| priority_tier | 1 / 2 / 3 / 4 |
| status | active / planned / experimental / brand_specific / metadata_only / deprecated |
| capture_type | microscopic / macro / metadata / document |
| condition_sensitive | yes / no / moderate |
| glare_sensitive | yes / no |
| requires_microscope | yes / no |
| notes | Implementation notes |

### Deliverables

- `docs/reference/region-code-registry.md`
- `RegionCodes` in `auth_common/regions.py` updated to include `PLANNED` list alongside
  existing `ALL` and `EXTERNAL` lists
- Validation scripts distinguish active regions (accepted in capture protocols) from
  planned regions (documented but not yet capturable)

---

## 5. Phase 2 — Extended Handbag Capture Protocol Draft

**Goal:** Design an extended protocol without replacing the MVP.

### Protocol

```
protocol_code: lv_monogram_canvas_handbag_extended_capture
protocol_version: v0.1.0
status: draft
```

### Required Regions (Tier 1)

| Region Code | Min Images | Capture Guidance | ML Use |
|---|---|---|---|
| EXTERIOR_CANVAS | 3 | Center of exterior panel, avoid edges | Texture embedding |
| FRONT_LOGO_PRINT | 2 | Logo area, include edges | Print quality embedding |
| INTERIOR_HEAT_STAMP | 2 | Full stamp visible, raking light | Font/depth embedding |
| HARDWARE_ENGRAVING | 2 | Primary hardware, avoid glare | Engraving embedding |
| STITCHING_DETAIL | 3 | Multiple stitch runs, include spacing | Thread/spacing embedding |
| DATE_CODE_AREA | 1 | Full code visible | OCR + embedding |

### Optional Regions (Tier 2)

| Region Code | Min Images | Condition Sensitive | Capture Guidance |
|---|---|---|---|
| EDGE_PAINT_DETAIL | 2 | **Yes** | Edge of leather panel, show layers |
| ZIPPER_PULL_ENGRAVING | 1 | Yes | Both sides if marked |
| ZIPPER_TEETH_DETAIL | 1 | Moderate | Close-up of teeth alignment |
| INTERIOR_LINING_TEXTURE | 2 | Moderate | Lining fabric, not label area |
| HANDLE_STITCHING | 2 | **Yes** | Handle attachment stitching |
| HANDLE_EDGE_PAINT | 1 | **Yes** | Handle edge, show wear |
| STRAP_ATTACHMENT | 1 | Yes | D-ring or clip attachment |
| RIVET_DETAIL | 1 | Yes | Rivet head and surrounding leather |
| CLASP_DETAIL | 1 | Yes | Clasp face and mechanism |
| CORNER_WEAR_DETAIL | 1 | **Yes** | Most worn corner |

### Rules

- Required regions must be satisfied for session completion
- Optional regions enrich expert review but do not block completion
- Missing optional regions may record a reason (e.g., "Item has no zipper")
- Condition-sensitive regions should be paired with condition metadata

---

## 6. Phase 3 — Capture Workbench Region Guidance

**Goal:** Design workbench UI support for region guidance (implement later).

### Needed

| Feature | Purpose |
|---|---|
| Region instructions | Text guidance per region (framing, lighting, common mistakes) |
| Common failure modes | "Avoid glare on hardware", "Check focus before capture" |
| Required/optional badges | Clearly label which regions must be captured |
| Capture count indicator | "2 of 3 required images captured" |
| Glare/condition badges | Warn operator about sensitive regions |
| Example images | Reference framing examples (future) |
| Missing-region reason | Allow operator to record why an optional region was skipped |

### Backend Support Needed

- Region metadata fields in capture protocols or a separate region-guidance table
- Optional region support in capture session completion logic
- Missing-region reason storage

---

## 7. Phase 4 — Manifest Template Expansion

**Goal:** Support optional regions and missing-region reasons in capture batch manifests.

### Example YAML

```yaml
images:
  - region_code: EDGE_PAINT_DETAIL
    file: item_001/edge_paint_01.png
    optional: true
    notes: "Corner with visible edge wear"

  - region_code: STITCHING_DETAIL
    file: item_001/stitching_01.png
    notes: "Known third-party restitching — see condition metadata"

missing_regions:
  - region_code: ZIPPER_PULL_ENGRAVING
    reason: "Item has no zipper pull (open-top tote)"
  - region_code: DATE_CODE_AREA
    reason: "Date code area inaccessible without disassembly"
```

### Validation Changes Needed

- Validate `missing_regions` reason codes if standardized
- Warn but do not fail on missing optional regions
- Fail on missing required regions (current behavior preserved)

---

## 8. Phase 5 — Data Explorer Coverage Views

**Goal:** Show region coverage health in the Data Explorer tab.

### Planned Views

| View | Purpose |
|---|---|
| Tier 1 coverage per dataset | Are all required regions present? |
| Tier 2 coverage per dataset | Which optional regions have images? |
| Required vs optional coverage | Coverage percentage by requirement level |
| Missing high-value regions | Which Tier 2 regions have zero images? |
| Condition-sensitive coverage | Do repaired items have repair-region captures? |
| Dataset readiness score | Composite: splits + regions + embeddings + labels |

---

## 9. Phase 6 — Gold-Set Capture Protocol

**Goal:** Define capture requirements for the first real gold-set dataset.

| Stage | Authentic | Counterfeit | Regions | Notes |
|---|---|---|---|---|
| Pilot | 5 | 5 | Tier 1 only | Validate workflow |
| Early set | 25 | 25 | Tier 1 + selected Tier 2 | First ML comparison |
| Serious benchmark | 100 | 100 | Tier 1 + Tier 2 | Statistical validation |

### Requirements

- Capture all Tier 1 regions for every item
- Capture selected Tier 2 regions where applicable (edge paint, zipper, handles)
- Capture condition-sensitive regions for repaired/worn items
- Split by physical item, never by individual image
- Record condition and provenance metadata for every item
- Include hard cases: worn, repaired, replaced hardware, Franken-bag candidates

---

## 10. Phase 7 — Region-Specific ML and Scoring

**Future work requiring real data:**

| Capability | Dependency |
|---|---|
| Region-specific similarity thresholds | Real per-region evaluation data |
| Region-specific quality thresholds | Microscope capture statistics per region |
| Region-specific embedding models | Enough data per region for training |
| Weighted multi-region scoring | Region discrimination measured on real data |
| Condition-aware mismatch interpretation | Condition metadata linked to scoring |
| Per-region OOD detection | Reference density per region |

**Do not implement from taxonomy alone.** These require empirical measurement on real
gold-set data.

---

## 11. Risks

| Risk | Mitigation |
|---|---|
| Too many regions overwhelm operators | Keep active protocols small; use optional regions |
| Optional regions create inconsistent datasets | Track coverage in Data Explorer; require reasons for missing |
| Region code drift / naming inconsistency | Maintain formal registry with governance |
| Sparse data per region in early datasets | Start with Tier 1; add Tier 2 only when capture is proven |
| Capture protocol too complex for mobile UX | Mobile app shows only protocol-required regions |
| Premature per-region thresholding | Wait for real data; label thresholds as defaults |

---

## 12. Immediate Next Actions

1. **Create region registry doc** — `docs/reference/region-code-registry.md` with all
   known region codes, statuses, and metadata
2. **Add planned Tier 2 codes** to `RegionCodes.PLANNED` list in `regions.py`
   (non-active, not accepted in current capture protocols)
3. **Draft extended LV handbag capture protocol** — document only, do not activate
4. **Add region guidance metadata to docs** before implementing in workbench UI
5. **Do not replace current MVP capture protocol** until extended protocol is validated
   with real microscope captures

---

## Tooling: Region Analysis Framework

A region analysis framework (`ml/experiments/region_analysis.py`) supports
coverage and readiness diagnostics per dataset:

- Per-region image/item counts, split and label distributions
- Readiness scoring: no_data / sparse / diagnostic_only / evaluation_ready /
  training_candidate (based on image count — a rough proxy only)
- Per-region embedding metrics where sufficient data exists
- External-only region flagging, unknown region code warnings

This framework will support future Data Explorer coverage/readiness views.
Readiness scores are diagnostic only — they do not substitute for label quality,
item diversity, split integrity, or provenance checks.

Initial public external region-analysis results are documented in
[Region-Specific Analysis Results](../datasets/region-specific-analysis-results.md).

## 13. Related Documents

- [Inspection Region Taxonomy](../reference/luxury-item-inspection-region-taxonomy.md)
- [Item Condition Vocabulary](../reference/item-condition-vocabulary.md)
- [ML Improvement Roadmap](ml-improvement-roadmap.md)
- [Dataset Acquisition Strategy](dataset-acquisition-strategy.md)
- [Microscope Acceptance Runbook](../operations/microscope-acceptance-runbook.md)
- [Service Interactions](../../auth-platform/docs/service-interactions.md)
