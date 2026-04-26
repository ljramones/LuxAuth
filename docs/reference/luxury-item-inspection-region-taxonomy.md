# Luxury Item Inspection Region Taxonomy

## 1. Purpose

Luxury goods should be inspected as assemblies of materials, construction details,
hardware, branding, identity markers, condition indicators, and provenance evidence.
This taxonomy defines the candidate inspection regions for luxury item authentication,
guides future capture protocols, mobile capture UX, gold-set data collection, and ML
evaluation planning.

This document does not imply all regions are required for every item. It does not create
production authentication claims. It is a planning and reference document.

---

## 2. Scope

**Primary focus:** Luxury handbags and small leather goods.

**Future extension planned for:**
- Watches
- Shoes / sneakers
- Apparel
- Jewelry
- Accessories (belts, wallets, cardholders)
- Packaging and provenance documents

---

## 3. Current LuxAuth Region Coverage

| Region Code | Meaning | Current Use | Status | Limitations |
|---|---|---|---|---|
| `EXTERIOR_CANVAS` | Exterior coated canvas or material surface | Scan recipe, capture protocol | Active | Covers monogram canvas; no leather-grain variant yet |
| `FRONT_LOGO_PRINT` | Front logo or printed pattern surface | Scan recipe, capture protocol | Active | Covers logo region; no print-edge or registration detail |
| `INTERIOR_HEAT_STAMP` | Interior brand heat stamp / embossing | Scan recipe, capture protocol | Active | Covers stamp; no foil or depth sub-regions |
| `HARDWARE_ENGRAVING` | Hardware metal engraving | Scan recipe, capture protocol | Active | Covers primary engraving; no zipper/rivet/clasp variants |
| `STITCHING_DETAIL` | Visible stitching lines | Scan recipe, capture protocol | Active | Covers stitching; no thread/hole/repair sub-regions |
| `DATE_CODE_AREA` | Date code or serial area | Scan recipe (planned) | Planned | Defined but minimal capture support |
| `EXTERNAL_LEATHER_TEXTURE` | Microscopic leather texture | Public dataset ingestion | External only | Not a luxury capture region |
| `EXTERNAL_FABRIC_TEXTURE` | Microscopic woven fabric | Public dataset ingestion | External only | Not a luxury capture region |

`EXTERNAL_LEATHER_TEXTURE` and `EXTERNAL_FABRIC_TEXTURE` are public dataset region codes
used for pipeline validation. They are not luxury item capture regions.

---

## 4. Inspection Layers

| # | Layer | Capture Type |
|---|---|---|
| 1 | Exterior material surface | Microscopic image |
| 2 | Printed pattern / logo surface | Microscopic image |
| 3 | Stitching and thread | Microscopic image |
| 4 | Seams, piping, corners, and edge paint | Microscopic / macro image |
| 5 | Hardware and engraving | Microscopic image |
| 6 | Zippers and pulls | Microscopic / macro image |
| 7 | Interior lining | Microscopic / macro image |
| 8 | Heat stamps / embossing | Microscopic image |
| 9 | Date codes, serials, chips, and identity markers | Image + structured metadata |
| 10 | Handles, straps, and attachment points | Microscopic / macro image |
| 11 | Adhesive, layering, and construction | Microscopic image (non-destructive only) |
| 12 | Packaging and accessories | Macro image + metadata |
| 13 | Measurements and physical properties | Structured metadata |
| 14 | Condition, repair, and alteration metadata | Structured metadata |
| 15 | Provenance and chain-of-custody metadata | Structured metadata + documents |

---

## 5. Detailed Region Taxonomy

### 5.1 Exterior Material Surface

**Inspect:** Leather grain, canvas weave, coated canvas texture, embossed leather, patent/gloss
surface, pore structure, fiber direction, surface coating, print/material interaction.

**Why it matters:** The exterior surface is the primary material signature. Authentic and
counterfeit items often differ in grain structure, pore distribution, and coating behavior.

| Current Coverage | Recommended Future Codes | Priority | Capture Type | Repair Sensitive |
|---|---|---|---|---|
| EXTERIOR_CANVAS | EXTERIOR_LEATHER_GRAIN | Tier 1 | Microscopic | Moderate (wear, patina) |
| | COATED_CANVAS_TEXTURE | Tier 1 | Microscopic | Low |
| | PATENT_SURFACE | Tier 2 | Microscopic | High (scratches, coating) |
| | EMBOSSED_LEATHER_PATTERN | Tier 2 | Microscopic | Moderate |
| | MATERIAL_SURFACE_TEXTURE | Tier 2 | Microscopic | Moderate |

### 5.2 Printed Pattern / Logo Surface

**Inspect:** Logo print edge quality, ink boundary, print texture, registration, repeat pattern
geometry, print-over-material interaction.

**Why it matters:** Print quality and registration are highly discriminative. Counterfeit prints
often have blurred edges, incorrect ink behavior, or misaligned repeats.

| Current Coverage | Recommended Future Codes | Priority | Capture Type | Repair Sensitive |
|---|---|---|---|---|
| FRONT_LOGO_PRINT | PRINT_EDGE_DETAIL | Tier 2 | Microscopic | Low |
| | REPEAT_PATTERN_ALIGNMENT | Tier 2 | Microscopic/macro | Low |
| | PRINT_ON_TEXTURE_INTERACTION | Tier 2 | Microscopic | Low |
| | MONOGRAM_PATTERN_DETAIL | Tier 2 | Microscopic | Low |

### 5.3 Stitching and Thread

**Inspect:** Thread twist, thickness, material, stitch spacing, angle, hole shape, needle
penetration, tension, repair/restitch evidence.

**Why it matters:** Stitching construction is one of the strongest forensic indicators. OEM
thread, stitch spacing, and hole morphology are difficult to replicate precisely.

| Current Coverage | Recommended Future Codes | Priority | Capture Type | Repair Sensitive |
|---|---|---|---|---|
| STITCHING_DETAIL | THREAD_CLOSEUP | Tier 2 | Microscopic | **High** |
| | STITCH_HOLE_DETAIL | Tier 2 | Microscopic | High |
| | STITCH_SPACING_SEQUENCE | Tier 2 | Microscopic | High |
| | BACKSIDE_STITCHING | Tier 3 | Microscopic | High |
| | REPAIRED_STITCHING_AREA | Tier 3 | Microscopic | **Very high** |

**Note:** Use `item_component_conditions` with `component_type=thread` and
`component_status=replaced_third_party` for repaired or non-OEM stitching.

### 5.4 Seams, Piping, Corners, and Edge Paint

**Inspect:** Edge paint / glazing, seam alignment, piping shape, corner wear, edge thickness,
paint cracking, refinished edges, adhesive bleed.

**Why it matters:** Edge paint quality and seam construction vary significantly between authentic
and counterfeit items. Restoration is common and must be distinguished from manufacturing.

| Current Coverage | Recommended Future Codes | Priority | Capture Type | Repair Sensitive |
|---|---|---|---|---|
| Not covered | EDGE_PAINT_DETAIL | **Tier 2** | Microscopic | **High** |
| | SEAM_CONSTRUCTION | Tier 2 | Microscopic | Moderate |
| | CORNER_WEAR_DETAIL | Tier 3 | Macro | High |
| | PIPING_DETAIL | Tier 3 | Microscopic | Moderate |
| | ADHESIVE_EDGE_DETAIL | Tier 3 | Microscopic | Moderate |
| | EDGE_RESTORATION_DETAIL | Tier 3 | Microscopic | **Very high** |

**Gap level: High.** Edge paint should be added before serious gold-set capture.

### 5.5 Hardware and Engraving

**Inspect:** Engraving sharpness, depth, font geometry, metal finish, plating texture, machining
marks, screws, rivets, clasp construction, lock/key details.

**Why it matters:** Hardware engraving is highly forensic. Font geometry, machining marks, and
plating texture are difficult to replicate. Hardware is also commonly replaced.

| Current Coverage | Recommended Future Codes | Priority | Capture Type | Repair Sensitive |
|---|---|---|---|---|
| HARDWARE_ENGRAVING | ZIPPER_PULL_ENGRAVING | Tier 2 | Microscopic | **High** |
| | RIVET_DETAIL | Tier 2 | Microscopic | High |
| | CLASP_DETAIL | Tier 2 | Microscopic | High |
| | LOCK_DETAIL | Tier 2 | Microscopic | High |
| | SCREW_HEAD_DETAIL | Tier 3 | Microscopic | Moderate |
| | PLATING_TEXTURE | Tier 3 | Microscopic | High |
| | HARDWARE_BACKSIDE | Tier 3 | Microscopic | Moderate |

### 5.6 Zippers and Pulls

**Inspect:** Zipper teeth geometry, tape texture, pull shape, slider backside, supplier marks.

| Current Coverage | Recommended Future Codes | Priority | Capture Type | Repair Sensitive |
|---|---|---|---|---|
| Not explicit | ZIPPER_TEETH_DETAIL | Tier 2 | Microscopic | Moderate |
| | ZIPPER_PULL_FRONT | Tier 2 | Microscopic | High |
| | ZIPPER_PULL_BACK | Tier 2 | Microscopic | High |
| | ZIPPER_TAPE_TEXTURE | Tier 3 | Microscopic | Low |
| | ZIPPER_SLIDER_BACK | Tier 3 | Microscopic | Moderate |

**Gap level: High.** Zipper details should be added before gold-set capture.

### 5.7 Interior Lining

**Inspect:** Lining fabric weave, color/texture, print, pocket stitching, interior seam
construction, interior wear.

| Current Coverage | Recommended Future Codes | Priority | Capture Type | Repair Sensitive |
|---|---|---|---|---|
| Indirect (INTERIOR_HEAT_STAMP only) | INTERIOR_LINING_TEXTURE | Tier 2 | Microscopic | Moderate |
| | INTERIOR_POCKET_STITCHING | Tier 3 | Microscopic | Moderate |
| | INTERIOR_SEAM_DETAIL | Tier 3 | Microscopic | Moderate |
| | LINING_PRINT_DETAIL | Tier 3 | Microscopic | Low |

### 5.8 Heat Stamp / Embossing

**Inspect:** Font geometry, letter spacing, emboss depth, foil behavior, edge sharpness,
surrounding material deformation, stamp wear.

| Current Coverage | Recommended Future Codes | Priority | Capture Type | Repair Sensitive |
|---|---|---|---|---|
| INTERIOR_HEAT_STAMP | HEAT_STAMP_EDGE_DETAIL | Tier 2 | Microscopic | Moderate |
| | FOIL_STAMP_TEXTURE | Tier 2 | Microscopic | Moderate |
| | STAMP_DEPTH_DETAIL | Tier 3 | Microscopic | Moderate |
| | STAMP_SURROUNDING_MATERIAL | Tier 3 | Microscopic | Moderate |

### 5.9 Date Codes, Serials, Chips, and Identity Markers

**Inspect:** Date code, serial number, model/production codes, NFC/RFID markers, microchip
location, hidden tags, interior labels, security labels.

| Current Coverage | Recommended Future Codes | Priority | Capture Type | Repair Sensitive |
|---|---|---|---|---|
| DATE_CODE_AREA | SERIAL_LABEL | Tier 1 | Image + metadata | Low |
| | NFC_TAG_AREA | Tier 4 | Metadata | Low |
| | RFID_CHIP_AREA | Tier 4 | Metadata | Low |
| | INTERIOR_MODEL_TAG | Tier 2 | Image | Low |
| | SECURITY_LABEL | Tier 3 | Image | Low |
| | MICROCHIP_LOCATION | Tier 4 | Metadata | Low |

**Note:** Many of these are structured metadata rather than microscopic images.
Brand-specific rules apply (e.g., LV moved from date codes to microchips).

### 5.10 Handles, Straps, and Attachment Points

**Inspect:** Handle grain, handle stitching, handle edge paint, strap holes, buckle hardware,
attachment tabs, D-rings, replacement evidence.

| Current Coverage | Recommended Future Codes | Priority | Capture Type | Repair Sensitive |
|---|---|---|---|---|
| Not explicit | HANDLE_GRAIN | Tier 2 | Microscopic | Moderate |
| | HANDLE_STITCHING | Tier 2 | Microscopic | **High** |
| | HANDLE_EDGE_PAINT | Tier 2 | Microscopic | High |
| | STRAP_HOLE_DETAIL | Tier 3 | Microscopic | Moderate |
| | STRAP_ATTACHMENT | Tier 2 | Microscopic | High |
| | BUCKLE_DETAIL | Tier 3 | Microscopic | Moderate |
| | D_RING_DETAIL | Tier 3 | Microscopic | Moderate |
| | REPLACED_HANDLE_DETAIL | Tier 3 | Microscopic | **Very high** |

**Important for Franken-bag detection:** handle/strap replacement is a common alteration.

### 5.11 Adhesive, Layering, and Construction

**Inspect:** Adhesive bleed, layer stack, folded edges, reinforcement, bonded layers.

| Current Coverage | Recommended Future Codes | Priority | Capture Type | Repair Sensitive |
|---|---|---|---|---|
| Not covered | EDGE_LAYER_DETAIL | Tier 3 | Microscopic | Moderate |
| | ADHESIVE_DETAIL | Tier 3 | Microscopic | Moderate |
| | FOLD_CONSTRUCTION | Tier 3 | Microscopic | Low |
| | LAYER_STACK_DETAIL | Tier 3 | Microscopic | Low |

**Note:** May require non-destructive edge views only.

### 5.12 Packaging and Accessories

**Inspect:** Dust bag fabric, box print, care card, receipt, tags, authenticity card, lock/key set.

| Recommended Codes | Priority | Capture Type |
|---|---|---|
| DUST_BAG_FABRIC | Tier 4 | Macro / microscopic |
| PACKAGING_PRINT | Tier 4 | Macro |
| AUTH_CARD_PRINT | Tier 4 | Macro |
| CARE_CARD_PRINT | Tier 4 | Macro |
| RECEIPT_DOCUMENT | Tier 4 | Document / metadata |
| ACCESSORY_SET | Tier 4 | Metadata |

**Mostly metadata/provenance evidence.** Optional microscopic capture for packaging material.

### 5.13 Measurements and Physical Properties

| Recommended Metadata Fields | Priority | Type |
|---|---|---|
| measured_weight_g | Tier 2 | Numeric |
| measured_width_mm | Tier 2 | Numeric |
| measured_height_mm | Tier 2 | Numeric |
| measured_depth_mm | Tier 2 | Numeric |
| handle_drop_mm | Tier 3 | Numeric |
| strap_length_mm | Tier 3 | Numeric |
| stitches_per_cm | Tier 2 | Numeric |
| hardware_dimension_mm | Tier 3 | Numeric |

**Not ML-only.** Structured metadata that complements visual inspection.

### 5.14 Condition, Repair, and Alteration Metadata

**Current coverage:** Good foundation via `item_condition_metadata` and
`item_component_conditions` tables with controlled vocabulary.

See [Item Condition Vocabulary](item-condition-vocabulary.md) for canonical values.

See [Item Condition Architecture](../architecture/item-condition-and-component-provenance.md)
for schema and future decision behavior.

---

## 6. Tiered Region Priorities

### Tier 1 — MVP Required / High-Value Regions

| Region Code | Layer |
|---|---|
| EXTERIOR_CANVAS (or EXTERIOR_LEATHER_GRAIN) | Exterior material |
| FRONT_LOGO_PRINT | Logo/print |
| INTERIOR_HEAT_STAMP | Heat stamp |
| HARDWARE_ENGRAVING | Hardware |
| STITCHING_DETAIL | Stitching |
| DATE_CODE_AREA | Identity markers |

### Tier 2 — Strong Additions Before Gold-Set Capture

| Region Code | Layer |
|---|---|
| EDGE_PAINT_DETAIL | Edge paint |
| ZIPPER_PULL_ENGRAVING | Zippers |
| ZIPPER_TEETH_DETAIL | Zippers |
| INTERIOR_LINING_TEXTURE | Interior |
| HANDLE_STITCHING | Handles |
| HANDLE_EDGE_PAINT | Handles |
| STRAP_ATTACHMENT | Handles/straps |
| RIVET_DETAIL | Hardware |
| CLASP_DETAIL | Hardware |
| CORNER_WEAR_DETAIL | Seams/corners |
| INTERIOR_MODEL_TAG | Identity markers |

### Tier 3 — Condition / Repair Sensitive Regions

| Region Code | Layer |
|---|---|
| REPAIRED_STITCHING_AREA | Stitching |
| REPLACED_HANDLE_DETAIL | Handles |
| EDGE_RESTORATION_DETAIL | Edge paint |
| PLATING_TEXTURE | Hardware |
| PIPING_DETAIL | Seams |
| HARDWARE_BACKSIDE | Hardware |
| BACKSIDE_STITCHING | Stitching |

### Tier 4 — Optional / Brand-Specific / Metadata-Heavy

| Region Code | Layer |
|---|---|
| NFC_TAG_AREA | Identity |
| RFID_CHIP_AREA | Identity |
| AUTH_CARD_PRINT | Packaging |
| DUST_BAG_FABRIC | Packaging |
| PACKAGING_PRINT | Packaging |
| SECURITY_LABEL | Identity |
| RECEIPT_DOCUMENT | Provenance |

---

## 7. Coverage Assessment

| Inspection Area | Current Coverage | Gap Level | Notes |
|---|---|---|---|
| Exterior material texture | Good | Low | Canvas covered; leather-grain variant needed |
| Logo/print surface | Basic | Medium | FRONT_LOGO_PRINT exists; no edge/registration detail |
| Stitching | Basic | Medium | Needs thread/hole/repair sub-regions |
| Heat stamp | Good | Low | INTERIOR_HEAT_STAMP exists |
| Hardware engraving | Basic | Medium | Needs zipper/rivet/clasp variants |
| Date/serial/code area | Planned | Medium | DATE_CODE_AREA defined but minimal support |
| Edge paint/glazing | **Missing** | **High** | Important before gold-set |
| Zipper/pull details | **Missing** | **High** | Important before gold-set |
| Lining/interior fabric | **Missing** | **High** | Important before gold-set |
| Handles/straps/attachments | **Missing** | **High** | Important for Franken-bag detection |
| Dimensions/weight/stitch counts | Missing | Medium | Structured metadata |
| Packaging/accessories | Missing | Low | Metadata-heavy, optional |
| Repair/condition metadata | Good foundation | Low | Schema and vocabulary exist |
| Franken/altered component modeling | Foundation exists | Medium | Decision logic future |
| Brand-specific protocols | Early | Medium | Need per-brand capture protocols |

---

## 8. Capture Protocol Implications

- The current LV monogram canvas protocol is a narrow MVP with 5 Tier 1 regions
- Serious gold-set capture should add Tier 2 regions (edge paint, zipper, lining, handles)
- Not every brand or item type needs every region
- Capture protocols should be product-type and material-specific
- Mobile app should show only required regions for the selected protocol
- Optional regions can support expert review without being required for automated decision

---

## 9. ML Implications

- Regions have different embedding distributions — leather grain occupies a different space
  than hardware engraving or stitching
- Cross-region nearest-neighbor comparison can be misleading and should be filtered by
  region code
- Region-specific similarity thresholds will likely be required once real data exists
- Region-specific embedding models may eventually outperform a single mixed-region model
- Some regions are better suited for texture embeddings (leather, canvas), others for
  OCR/geometry (date codes, serial labels), others for structured metadata (dimensions, NFC)
- Condition-sensitive regions (stitching, handles, edge paint) need metadata-aware
  interpretation to avoid condition bias

---

## 10. Mobile UX Implications

- Each region may need an example image showing correct framing
- Region-specific capture instructions are needed (e.g., "avoid glare on hardware")
- Hardware and reflective materials need special guidance (polarizer, angle)
- Optional and repair-sensitive regions should be clearly marked in the UI
- Mobile app should support retakes when quality fails
- Mobile app should handle incomplete/inconclusive states gracefully

---

## 11. Recommended Next Steps

1. Add Tier 2 region codes to `RegionCodes` as planned future values
2. Draft an extended handbag capture protocol with Tier 1 + selected Tier 2 regions
3. Update capture-workbench to display optional region guidance
4. Capture microscope acceptance images for Tier 1 + selected Tier 2 regions
5. Include hard cases in gold-set capture (worn, repaired, replaced hardware, Franken-bag)
6. Do not expand decision logic until real data supports region-specific weights

---

## 12. Related Documents

- [Item Condition Vocabulary](item-condition-vocabulary.md)
- [Inspection Region Expansion Plan](../roadmaps/inspection-region-expansion-plan.md)
- [Item Condition Architecture](../architecture/item-condition-and-component-provenance.md)
- [ML Improvement Roadmap](../roadmaps/ml-improvement-roadmap.md)
- [ML Technology Explained](../ml-technology-explained.md)
- [Microscope Acceptance Runbook](../operations/microscope-acceptance-runbook.md)
- [Capture Manifest Template](../templates/capture-manifest-template.yaml)
- [Service Interactions](../../auth-platform/docs/service-interactions.md)
