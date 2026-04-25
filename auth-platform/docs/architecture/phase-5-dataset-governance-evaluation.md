# Phase 5: Reference Dataset Governance + Evaluation Harness

## Overview

Phase 5 adds the backend foundation for managing labeled reference datasets, dataset
versions, evaluation sets, threshold profiles, and reproducible evaluation runs. This
enables the platform to answer critical questions about model and data provenance before
introducing real metric-learning training.

## Why This Phase Comes Before Real Training

Before training a metric-learning model, the platform needs:

1. **Dataset versioning** — which reference images were used, in which version
2. **Split management** — which images are for training vs. evaluation
3. **Label provenance** — who labeled each image, how confident is the label
4. **Threshold profiles** — what scoring thresholds produce what outcomes
5. **Reproducible evaluation** — can we measure false positive/negative rates
6. **Baseline metrics** — what does texture_baseline_v0.1.0 achieve before training

Without these foundations, training a model would produce results that cannot be
reproduced, compared, or trusted.

## Dataset Versions

Each named dataset version (e.g., `synthetic_lv_monogram_v0.1.0`) contains:
- A set of reference images (via `reference_dataset_members`)
- Each member assigned to a split: train, validation, test, or holdout
- Flags: `include_in_search`, `include_in_evaluation`, `include_in_training`
- A lifecycle status: draft → active → retired

### Splits

| Split | include_in_search | include_in_evaluation | include_in_training | Purpose |
|---|---|---|---|---|
| train | TRUE | FALSE | TRUE | Build the reference database; train models |
| validation | FALSE | TRUE | FALSE | Tune thresholds; validate during training |
| test | FALSE | TRUE | FALSE | Final evaluation; never used for training |
| holdout | FALSE | FALSE | FALSE | Reserved for future independent evaluation |

## Label Governance

Every reference item/image has a `reference_label_reviews` entry recording:
- Who reviewed it (reviewer_id)
- Authenticity assessment
- Confidence level (high/medium/low)
- Provenance type (synthetic, expert_review, receipt_verified, partner_supplied)
- Notes

For synthetic test data, all labels are `provenance_type=synthetic, label_confidence=high`.

## Threshold Profiles

Scoring thresholds are stored in the `threshold_profiles` table:
- `strong_match_threshold` — minimum authentic similarity for STRONG_MATCH
- `mismatch_threshold` — maximum counterfeit similarity before MISMATCH
- `ood_threshold` — out-of-distribution detection threshold
- `require_all_regions` — whether all recipe regions must be scored

Profiles are tied to specific embedding models and dataset versions.

## Evaluation Runs

An evaluation run:
1. Selects test-split images from a dataset version
2. Runs vector search against search-eligible references (excluding self-match)
3. Applies threshold profile to predict labels
4. Compares predictions to expected labels
5. Records per-item results and summary metrics

### Metrics

| Metric | Definition |
|---|---|
| True positive | Authentic expected, system predicts VERIFIED |
| True negative | Counterfeit expected, system predicts UNVERIFIED |
| False positive | Counterfeit expected, system predicts VERIFIED |
| False negative | Authentic expected, system predicts UNVERIFIED |
| Inconclusive | System cannot determine (tracked separately) |
| Expert review | System requests human review (tracked separately) |

### Running an evaluation

```bash
make run-evaluation          # uses defaults
make evaluation-report       # prints latest report
```

## Disclaimers

1. **Synthetic data is only for pipeline validation.** Real evaluation requires
   curated, labeled datasets with verified chain-of-custody.

2. **texture_baseline_v0.1.0 is a hand-crafted feature extractor**, not a trained
   model. Evaluation metrics from this baseline establish a floor, not a target.

3. **SageMaker remains deferred** per ADR-0001. When a real metric-learning model
   is trained, the evaluation harness will measure improvement over the baseline.

4. **This does NOT authenticate real products.** The evaluation measures how well
   the system distinguishes synthetic texture groups, which validates the
   infrastructure but not real-world authentication capability.
