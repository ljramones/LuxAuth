# Dataset Acquisition Strategy

**Date:** 2026-04-25
**Status:** Planning — no production authentication claims

## The Strategic Bottleneck

Architecture is no longer the bottleneck for LuxAuth. The event-driven pipeline, dataset
governance, evaluation harness, ML lifecycle, and capture intake APIs are implemented.
The next unlock is **verified data** — real microscope images of known-authentic and
known-counterfeit luxury goods with documented provenance.

Without verified data:
- Learned models cannot be meaningfully trained or evaluated
- Threshold calibration has no ground truth
- Authentication accuracy claims have no basis
- The system remains a validated pipeline prototype, not an authentication tool

---

## Authentic Item Sourcing

| Source | Confidence | Practical Notes |
|---|---|---|
| **Personal known-authentic items** | High (if original receipt available) | Cheapest starting point; limited variety |
| **Retailer/consignment partnerships** | Medium–High | Access to variety; may require agreements |
| **Expert-authenticated items** | High | Requires trusted expert; adds cost |
| **Brand receipts / service records** | High | Gold standard for provenance |
| **Trusted reseller inventory** | Medium | Must verify authentication process |

**Priority for pilot:** Start with personal items with original receipts. Even 5 items
with documented provenance and full region captures establish the first real evaluation
baseline.

---

## Counterfeit Sourcing

Sourcing known-counterfeit items has legal and ethical constraints that must be taken
seriously.

| Source | Feasibility | Legal/Ethical Notes |
|---|---|---|
| **Customs seizure partnerships** | High confidence; legally clear | Requires agency relationship; items may be destroyed on schedule |
| **Forensic/academic partnerships** | High confidence | University forensic programs may have counterfeit reference collections |
| **Controlled research purchases** | Medium confidence | Legal only in some jurisdictions; document purchase context carefully |
| **Items authenticated as counterfeit by experts** | High confidence | Expert must document basis for determination |
| **Self-identified fakes from owners** | Low–medium | Owner may be wrong; use `SUSPECT_COUNTERFEIT` label |

**Key constraint:** every counterfeit item must have documented provenance explaining
how counterfeit status was determined. Use `known_counterfeit_source` for high-confidence
items and `SUSPECT_COUNTERFEIT` for uncertain ones.

---

## Chain of Custody

Every reference item should have:
- Who captured it (operator)
- When it was captured (timestamp)
- What device was used (device_id, calibration_id)
- How authenticity was determined (known_authenticity_basis)
- Who labeled it (reviewer_id or provenance_type)
- How confident the label is (label_confidence)
- Any known repairs or alterations (condition metadata)

This metadata is supported by the current schema (`reference_items`,
`reference_label_reviews`, `item_condition_metadata`).

---

## Gold-Set Size Stages

| Stage | Authentic Items | Counterfeit Items | Images (est.) | Purpose |
|---|---|---|---|---|
| **Pilot** | 5 | 5 | ~50 per class | First real evaluation; quality check |
| **Useful early set** | 25 | 25 | ~250 per class | Meaningful metric-learning experiments |
| **Serious benchmark** | 100 | 100 | ~1000 per class | Statistical validation; confidence intervals |
| **Production-grade** | 500+ | 200+ | ~5000+ per class | Production threshold calibration; model deployment |

Each stage should include all required capture regions per item (5 regions × multiple
images per region).

---

## Condition Variation

The gold set should intentionally include:

| Case | Why | Min Count (Pilot) |
|---|---|---|
| Pristine authentic | Clean reference baseline | 2 |
| Worn authentic | Prevents condition as proxy for authenticity | 1 |
| Repaired authentic | Tests condition-aware routing | 1 |
| Authentic with replaced components | Tests component-level mismatch | 1 |
| Known counterfeit (various quality) | Establishes counterfeit baseline | 3–5 |
| Franken-bag / altered items | Tests mixed-provenance detection | If available |

See [Item Condition Vocabulary](../reference/item-condition-vocabulary.md) for labeling
guidance.

---

## Label Confidence Rules

| Scenario | Recommended Label | Confidence | Training Use |
|---|---|---|---|
| Brand receipt + expert confirmed | CONFIRMED_AUTHENTIC | high | Training + evaluation |
| Expert opinion only | CONFIRMED_AUTHENTIC | medium | Evaluation; training with caution |
| Owner claim only | CONFIRMED_AUTHENTIC | low | Exploratory only |
| Customs seizure with documentation | CONFIRMED_COUNTERFEIT | high | Training + evaluation |
| Expert-identified counterfeit | CONFIRMED_COUNTERFEIT | high | Training + evaluation |
| Suspected but not confirmed | SUSPECT_COUNTERFEIT | low | Exclude from training |

---

## Negative-Class Provenance

The counterfeit/negative class is harder to source responsibly than the authentic class.
If high-confidence counterfeit items are unavailable:

1. **Use public external datasets** (LeaData, FabricNET) for pipeline validation only
2. **Train authentic-only models** using one-class metric learning or anomaly detection
3. **Use expert-review workflow** for items that do not match authentic references, rather
   than labeling them as counterfeit without confirmation
4. **Document the absence** of counterfeit data as a limitation in any evaluation report

---

## What This Strategy Does NOT Do

- Does not make production authentication claims
- Does not guarantee gold-set availability on any timeline
- Does not authorize illegal procurement of counterfeit goods
- Does not claim that pilot-scale data is sufficient for production deployment
- Does not substitute for real-world validation with blind holdout sets

---

## Related Documents

- [ML Improvement Roadmap](ml-improvement-roadmap.md)
- [ML Technology Explained](../ml-technology-explained.md)
- [Microscope Acceptance Runbook](../operations/microscope-acceptance-runbook.md)
- [Item Condition Vocabulary](../reference/item-condition-vocabulary.md)
- [Public Dataset Evaluation Plan](../datasets/public-dataset-evaluation-plan.md)
