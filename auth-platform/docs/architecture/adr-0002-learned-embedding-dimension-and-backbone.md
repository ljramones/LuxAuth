# ADR-0002: Learned Embedding Dimension and Backbone Selection

## Status

**Proposed** — not yet implemented. Decision required before first serious gold-set
learned-model training.

## Date

2026-04-25

## Context

The current system uses two embedding approaches:

- `texture_baseline_v0.1.0`: 128-dimensional hand-crafted feature vector. This is
  deterministic, does not use a neural network, and serves as a pipeline validation
  baseline. Its dimension is fixed by its feature design and will not change.

- `learned_metric_v0.1.0`: 128-dimensional learned embedding from a randomly initialized
  ResNet18 with a projection head. This model exists only to validate the ML lifecycle
  (train → export → register → re-embed → evaluate). It is a **lifecycle scaffold**, not
  a representative learned model. Its underperformance versus the baseline is expected
  and is not a meaningful comparison.

Before training a learned model on real gold-set data, two decisions must be made:

1. **Embedding dimension** — 128, 256, 512, or 768?
2. **Backbone architecture** — which pretrained or self-supervised model?

These decisions are coupled: changing either after a large reference library is built
requires re-embedding all references, which is expensive and operationally disruptive.

## Decision

**Not yet decided.** This ADR captures the decision space and constraints.

### Embedding Dimension Candidates

| Dimension | Pros | Cons |
|---|---|---|
| 128 | Current baseline compatibility; fast search; small storage | May lack capacity for fine-grained texture discrimination |
| 256 | Moderate capacity increase; reasonable search cost | Doubles storage vs 128 |
| 512 | Common in production metric-learning systems | Higher storage and search cost; may be overkill for small reference libraries |
| 768 | Matches ViT/CLIP/DINOv2 native dimension; avoids lossy projection | Highest cost; only justified with large-scale reference data |

### Backbone Candidates

| Backbone | Type | Pros | Cons |
|---|---|---|---|
| ResNet18/34 (ImageNet pretrained) | Supervised CNN | Well-understood; fast inference; small | Limited capacity for fine texture |
| ResNet50 (ImageNet pretrained) | Supervised CNN | Better capacity; standard metric-learning backbone | Larger; slower on CPU |
| ConvNeXt-Tiny/Small | Modern CNN | Strong ImageNet performance; good transfer | Less studied for microscopy |
| DINOv2 (ViT-S/B) | Self-supervised ViT | Excellent visual features without task-specific labels; strong transfer | Requires downloading pretrained weights; larger model |
| SigLIP / CLIP ViT | Vision-language | Rich visual features; zero-shot capability | May be overparameterized for texture similarity |

### Key Constraint

**Changing embedding dimension after reference library growth requires full re-embedding.**
The `reference_embeddings` table stores vectors at a fixed dimension (currently
`vector(128)` in pgvector). Changing this requires:

1. Alter the pgvector column dimension
2. Re-embed all reference images with the new model
3. Rebuild HNSW indexes
4. Re-run all evaluations
5. Update all threshold profiles

This is manageable during early development but becomes costly at scale.

## Rationale for Deferral

- No real gold-set data exists yet — architecture experiments without real data are speculative
- The lifecycle scaffold (learned_metric_v0.1.0) proves the machinery works regardless of dimension
- Public external datasets (LeaData, FabricNET) can inform backbone selection once
  experiments are run, but they are not luxury-authentication data
- The decision should be made with empirical evidence from real microscope captures

## Revisit Triggers

- [ ] Before first serious gold-set learned-model training
- [ ] Before committing to large-scale real reference embeddings (>1000 images)
- [ ] When backbone transfer experiments on real microscope data are available
- [ ] If DINOv2 or equivalent self-supervised features show strong microscopy transfer
      in external benchmarks

## Consequences

**If decided too early:** May choose a dimension/backbone that does not suit real
microscopy data, requiring re-embedding later.

**If decided too late:** Early reference embeddings at 128-d may need to be discarded
and regenerated, wasting ingestion effort.

**Recommended approach:** Run backbone comparison experiments on the first real gold-set
(even if small), then commit to dimension and backbone before scaling reference ingestion.

## Related Documents

- [ML Technology Explained](../../../docs/ml-technology-explained.md)
- [ML Improvement Roadmap](../../../docs/roadmaps/ml-improvement-roadmap.md)
- [ADR-0001: Defer SageMaker](adr-0001-defer-sagemaker.md)
