# Item Condition and Component Provenance Vocabulary

## 1. Purpose

Luxury goods are assemblies of components — leather panels, stitching, hardware, lining,
stamps, and edge paint — not monolithic objects. An authentic item may contain repaired,
replaced, or non-OEM components. A counterfeit body may carry authentic hardware.

This vocabulary defines the canonical terms for describing item condition, authenticity
basis, repair history, and component-level status. It ensures consistent metadata across
capture manifests, batch ingestion, future review UIs, mobile capture clients, and
condition-aware decision logic.

**This vocabulary does not authenticate repairs automatically.** It does not create
production authentication claims. It is a metadata standard for safer future decisioning.

---

## 2. Where This Vocabulary Is Used

| Context | How |
|---|---|
| Capture manifests | `condition:` and `component_conditions:` fields per item |
| Capture batch validation | Validates vocabulary values during `validate_capture_batch.py` |
| `item_condition_metadata` table | Persists item-level condition data |
| `item_component_conditions` table | Persists region/component-level data |
| Future review UI | Dropdown values for reviewer forms |
| Future mobile capture clients | Guided condition capture during operator workflow |
| Future decision-service logic | Condition-aware mismatch interpretation |
| Gold-set dataset construction | Labeling hard cases (repairs, Franken-bags, worn items) |

---

## 3. Item-Level Metadata Fields

| Field | Type | Required Today | Meaning |
|---|---|---|---|
| `condition_grade` | string | No | Overall physical condition of the item |
| `known_authenticity_basis` | string | No | How authenticity was determined |
| `known_repairs` | boolean | No (default false) | Whether any repair/restoration is known |
| `third_party_repair` | boolean | No (default false) | Whether any repair is non-brand/non-OEM |
| `restoration_notes` | text | No | Description of what was repaired and how |
| `provenance_notes` | text | No | How the item was obtained and authenticated |
| `condition_notes` | text | No | General condition observations |

All fields are optional. Missing condition metadata is valid — existing manifests
without condition fields continue to work.

---

## 4. condition_grade Vocabulary

| Value | Definition | Example | ML Relevance |
|---|---|---|---|
| `new_unworn` | Never used; tags may still be attached | Store display item | Best reference quality; minimal texture variation |
| `excellent` | Minimal signs of use | Carried a few times | Near-reference quality |
| `used_good` | Visible wear but features mostly observable | Regular use, light patina | Acceptable for reference; some texture softening |
| `used_fair` | Moderate wear; some features degraded | Corner scuffs, handle darkening | Texture may differ from new references; worth capturing but label carefully |
| `heavily_worn` | Significant wear; features partially obscured | Cracking, deep scratches, fading | Risk of condition masking texture evidence; should not be confused with counterfeit |
| `damaged` | Physical damage beyond normal wear | Torn leather, broken hardware | Usually not suitable for authentication reference |
| `restored` | Professionally restored | Recolored, reconditioned | Restoration may alter surface evidence; record what was restored |
| `unknown` | Condition not assessed | Received without inspection | Do not use as high-confidence training data |

---

## 5. known_authenticity_basis Vocabulary

| Value | Definition | Confidence | Suitable For |
|---|---|---|---|
| `brand_receipt` | Original purchase receipt from brand store | High | Training + evaluation |
| `brand_archive` | Verified against brand production records | High | Training + evaluation |
| `brand_service_record` | Serviced/repaired by the brand with documentation | High | Training + evaluation |
| `expert_authenticated` | Authenticated by a recognized independent expert | High | Training + evaluation |
| `trusted_reseller` | Purchased from a vetted reseller with authentication guarantee | Medium–High | Training + evaluation (with caution) |
| `owner_claim` | Owner asserts authenticity without documentation | Low | Evaluation or exploratory only |
| `known_counterfeit_source` | Obtained from a known counterfeit source (seizure, test purchase) | High (for counterfeit label) | Training + evaluation |
| `lab_curated` | Curated in a controlled lab setting with documented provenance | Medium–High | Training + evaluation |
| `public_dataset` | From a public academic dataset (not luxury provenance) | N/A | Pipeline validation only |
| `synthetic` | Procedurally generated for workflow testing | N/A | Smoke/pipeline testing only |
| `unknown` | Authenticity basis not recorded | Unknown | Do not use for training |

**`owner_claim` alone should not be high-confidence training data.** It is acceptable
for exploratory analysis but must be flagged if used in evaluation.

**`known_counterfeit_source` requires careful documentation** — record the seizure
reference, test-purchase details, or expert determination.

---

## 6. Repair and Restoration Fields

| Field | Type | Meaning |
|---|---|---|
| `known_repairs` | boolean | Any repair or restoration is known or disclosed |
| `third_party_repair` | boolean | At least one repair was likely non-brand/non-OEM |
| `restoration_notes` | text | What was changed, by whom, and how it is known |

**Examples:**
- `"Third-party restitching on left side seam"`
- `"Handle replaced by non-brand repair shop; receipt available"`
- `"Hardware replated; source unknown — flagged for review"`
- `"Edge paint restoration disclosed by seller"`
- `"Professional cleaning only; no structural repairs"`

**Brand repair vs. third-party repair:** The item-level `third_party_repair` flag
indicates at least one known non-brand/non-OEM repair. Brand-authorized repairs are
represented through component-level statuses such as `repaired_brand` or `replaced_brand`.
If item-level brand repair tracking becomes common, a `brand_repair` boolean could be
added in the future, but it is not required in the current schema.

---

## 7. Component-Level Metadata Fields

| Field | Type | Required | Meaning |
|---|---|---|---|
| `region_code` | string | Yes | Must match a valid capture protocol region code |
| `component_type` | string | No | What physical component this record describes |
| `component_status` | string | No | Current status of this component |
| `source` | string | No | How the status was determined |
| `confidence` | string | No | Confidence in this assessment |
| `exclude_from_auth_decision` | boolean | No (default false) | Remove from automated decision aggregation |
| `expected_to_mismatch` | boolean | No (default false) | Known repair/replacement may cause legitimate mismatch |
| `notes` | text | No | Free-text explanation |

---

## 8. component_type Vocabulary

| Value | Category | When to Use |
|---|---|---|
| `leather_panel` | Body | Exterior or interior leather surface |
| `canvas_panel` | Body | Coated canvas (e.g., LV monogram) |
| `stitching` | Construction | Visible stitch lines |
| `thread` | Construction | Thread material specifically (when stitching was re-threaded) |
| `zipper` | Hardware | Zipper tape and teeth |
| `zipper_pull` | Hardware | Zipper pull tab |
| `clasp` | Hardware | Closure clasp/snap |
| `lock` | Hardware | Turn-lock or padlock |
| `key` | Hardware | Lock key |
| `handle` | Structure | Carry handle(s) |
| `strap` | Structure | Shoulder or crossbody strap |
| `hardware_plate` | Hardware | Decorative or functional metal plate |
| `logo_stamp` | Branding | Printed or embossed logo |
| `heat_stamp` | Branding | Heat-pressed brand stamp |
| `lining` | Interior | Interior fabric lining |
| `edge_paint` | Finish | Edge coating on leather |
| `adhesive` | Construction | Glue lines or bonding |
| `unknown` | — | Component type not determined |

---

## 9. component_status Vocabulary

| Value | Definition | Example | Decision Implication |
|---|---|---|---|
| `original_expected` | Assumed original; not independently confirmed | Default for unexamined components | Standard authentication comparison |
| `original_confirmed` | Independently confirmed as original | Brand service record confirms | Mismatch on this component is high severity |
| `replaced_brand` | Replaced by the brand's own repair service | Brand repair receipt | May differ from production-era references |
| `replaced_third_party` | Replaced by a non-brand repair service | Third-party cobbler receipt | Usually triggers expert review if mismatch |
| `repaired_brand` | Repaired (not replaced) by brand service | Restitched by brand | Minor variation expected |
| `repaired_third_party` | Repaired by non-brand service | Independent leather repair | Significant variation possible |
| `restored` | Professionally restored (recolored, reconditioned) | Edge paint restoration | Surface evidence may be altered |
| `altered` | Intentionally modified from original factory state; may be legitimate customization, undocumented modification, or suspicious alteration depending on provenance | Custom monogramming, aftermarket additions, undocumented hardware swap | Usually requires expert review; documented customization may be acceptable by policy |
| `missing` | Component is absent | Missing key for lock | Region cannot be captured or scored |
| `suspect` | Status uncertain; requires review | Hardware looks inconsistent with body | Do not use as trusted training evidence |
| `unknown` | Status not assessed | No information available | Treat as unconfirmed for training purposes |

---

## 10. source Vocabulary

| Value | Definition | Confidence Implication |
|---|---|---|
| `owner_disclosed` | Owner/seller stated this information | Low–medium; depends on trust |
| `seller_disclosed` | Professional seller disclosed (reseller, consignment) | Medium |
| `repair_receipt` | Written repair receipt or invoice | Medium–high |
| `brand_service_record` | Official brand service documentation | High |
| `expert_observed` | Independent expert physical inspection | High |
| `visual_inspection` | Observed during standard capture/intake | Medium |
| `lab_observed` | Observed in controlled lab setting | Medium–high |
| `inferred_from_mismatch` | System or reviewer inferred from embedding mismatch | Low — should not be used as ground truth without confirmation |
| `unknown` | Source of information not recorded | Low |

---

## 11. confidence Vocabulary

| Value | Meaning | Training Use |
|---|---|---|
| `high` | Documented or expert-confirmed | Suitable for training and evaluation |
| `medium` | Plausible but not fully documented | Suitable for evaluation; use cautiously for training |
| `low` | Weak claim or visual suspicion only | Evaluation or exploratory only; flag if used |
| `unknown` | No basis for confidence | Do not use as trusted training label |

---

## 12. exclude_from_auth_decision

A boolean field. When `true`, this region/component should not contribute to the
automated final authentication decision.

**Use cases:**
- Known non-original repair where mismatch is uninformative
- Severely damaged region where texture evidence is destroyed
- Missing component that cannot be captured

**Decision exclusion vs. evidence visibility:**
- Exclusion removes the region from **automated decision aggregation only**
- It does **not** delete evidence, hide evidence from expert review, or suppress audit records
- Excluded regions and their images remain visible in review workflows and audit trails
- Future UI should require reviewer/admin justification for exclusion

**Training implications:**
- Exclusion from the authentication decision does not automatically mean the region is
  safe for training
- Excluded regions should be reviewed before inclusion in training data
- Known repaired/replaced/altered regions should usually be labeled explicitly or excluded
  from training unless the training objective is specifically repair/alteration detection

**Warnings:**
- Excluding too many regions can make a scan INCONCLUSIVE by default
- Exclusion should not be used to hide counterfeit evidence

---

## 13. expected_to_mismatch

A boolean field. When `true`, this region/component may legitimately differ from
original references because of disclosed repair, replacement, or restoration.

**Behavior (future):**
- A mismatch on an `expected_to_mismatch=true` region should route to
  EXPERT_REVIEW_REQUIRED rather than automatic UNVERIFIED
- This does not automatically make the item VERIFIED — expert judgment is still needed

**Examples:**
- Known third-party restitching → thread texture will differ from OEM
- Replaced zipper pull → hardware engraving may not match brand standard
- Restored edge paint → finish may differ from factory application

---

## 14. Region Codes and Component Conditions

Component conditions must reference valid `region_code` values from the active capture
protocol. Examples:

| region_code | component_type | component_status | Scenario |
|---|---|---|---|
| STITCHING_DETAIL | thread | replaced_third_party | Known non-OEM restitching |
| HARDWARE_ENGRAVING | hardware_plate | suspect | Engraving inconsistent with body |
| INTERIOR_HEAT_STAMP | logo_stamp | restored | Heat stamp refreshed by restorer |
| EXTERIOR_CANVAS | canvas_panel | original_confirmed | Brand-confirmed original body |

External dataset region codes (`EXTERNAL_LEATHER_TEXTURE`, `EXTERNAL_FABRIC_TEXTURE`)
are for public dataset ingestion and should not normally be used in luxury item component
condition records.

---

## 15. Decision-Service Interpretation Guidance

The decision service does not yet use condition metadata. The following describes planned
future behavior:

| Scenario | Expected Handling |
|---|---|
| MISMATCH + no repair metadata | UNVERIFIED or EXPERT_REVIEW_REQUIRED depending on severity |
| MISMATCH + `expected_to_mismatch=true` | EXPERT_REVIEW_REQUIRED (not automatic VERIFIED) |
| STRONG_MATCH on `original_confirmed` | Supports authentication |
| MISMATCH on `original_confirmed` | High severity — strong counterfeit signal |
| `exclude_from_auth_decision=true` | Region removed from automated aggregation |
| Repaired item, all other regions strong | EXPERT_REVIEW_REQUIRED, pending reviewer confirmation |

**Possible future result states** (not yet implemented):
- `VERIFIED_WITH_DISCLOSED_REPAIR`
- `ALTERED_COMPONENT_DETECTED`
- `AUTHENTIC_BODY_COMPONENT_MISMATCH`

---

## 16. Gold-Set Capture Guidance

Gold-set datasets should intentionally include:

| Case | Why |
|---|---|
| Pristine authentic | Establishes clean reference baseline |
| Worn authentic | Prevents condition from being a proxy for authenticity |
| Heavily worn authentic | Tests robustness of texture features under degradation |
| Repaired authentic (disclosed) | Tests condition-aware decision routing |
| Authentic with replaced components | Tests component-level mismatch handling |
| Known counterfeit | Establishes counterfeit reference baseline |
| Suspected altered/Franken-bag | Tests mixed-provenance detection (if legally/ethically available) |

---

## 17. Manifest Examples

### Example A: Clean authentic item

```yaml
condition:
  condition_grade: excellent
  known_authenticity_basis: brand_receipt
  known_repairs: false
  third_party_repair: false
  provenance_notes: "Original receipt available"
  condition_notes: "Light wear only"
component_conditions: []
```

### Example B: Authentic with third-party stitching repair

```yaml
condition:
  condition_grade: used_good
  known_authenticity_basis: expert_authenticated
  known_repairs: true
  third_party_repair: true
  restoration_notes: "Third-party restitching on left side seam"
  provenance_notes: "Expert confirmed body and hardware as authentic"
  condition_notes: "Moderate exterior wear"
component_conditions:
  - region_code: STITCHING_DETAIL
    component_type: thread
    component_status: replaced_third_party
    source: repair_receipt
    confidence: medium
    exclude_from_auth_decision: false
    expected_to_mismatch: true
    notes: "Non-OEM thread may not match authentic reference stitching"
```

### Example C: Suspected Franken-bag

```yaml
condition:
  condition_grade: used_fair
  known_authenticity_basis: expert_authenticated
  known_repairs: true
  third_party_repair: true
  restoration_notes: "Handle and clasp origin uncertain"
  provenance_notes: "Leather body appears authentic; hardware requires review"
  condition_notes: "Mixed condition across components"
component_conditions:
  - region_code: HARDWARE_ENGRAVING
    component_type: hardware_plate
    component_status: suspect
    source: expert_observed
    confidence: medium
    exclude_from_auth_decision: false
    expected_to_mismatch: false
    notes: "Engraving quality inconsistent with body provenance"
```

---

## 18. Training and Evaluation Rules

- High-confidence pristine/used authentic examples are training candidates
- Repaired/altered items should usually be evaluation or expert-review cases first
- `confidence: unknown` or `component_status: suspect` items should not be used for training
- Component-level altered examples are valuable but must be labeled carefully
- All images from one physical item must remain in the same split
- Condition distribution should be tracked across splits to avoid bias

---

## 19. Current Implementation Status

| Feature | Status |
|---|---|
| `item_condition_metadata` table | Implemented |
| `item_component_conditions` table | Implemented |
| Manifest `condition:` support | Implemented |
| Manifest `component_conditions:` support | Implemented |
| Validation of condition vocabulary | Implemented (warnings for unknown grades) |
| Persistence during batch validation | Implemented |
| Linking to reference_items during ingestion | Implemented |
| Decision-service condition-aware logic | **Not yet implemented** |
| Review UI condition forms | **Not yet implemented** |
| Mobile client condition capture | **Not yet implemented** |

**Canonical vocabulary vs. current validation:** The values listed in this document are
the canonical recommended vocabulary for manifests, review workflows, and future client
UI. Current validation is intentionally permissive in some places — it may warn rather
than fail on unknown values to avoid blocking early ingestion workflows. Future review
UI and mobile clients should constrain users to canonical values. Stricter validation
that rejects non-canonical values may be enabled once workflows stabilize.

---

## 20. Related Documents

- [Item Condition and Component Provenance (Architecture)](../architecture/item-condition-and-component-provenance.md)
- [ML Improvement Roadmap](../roadmaps/ml-improvement-roadmap.md)
- [ML Technology Explained](../ml-technology-explained.md)
- [Capture Manifest Template](../templates/capture-manifest-template.yaml)
- [Microscope Acceptance Runbook](../operations/microscope-acceptance-runbook.md)
- [Service Interactions](../../auth-platform/docs/service-interactions.md)
