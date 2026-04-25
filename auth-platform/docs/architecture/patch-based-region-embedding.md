# Patch-Based Region Embedding

## Status

**Design note** — not yet implemented. Should be designed before large real reference
libraries are built.

## Problem

The current pipeline processes one global view per image:

1. Raw image → center-crop to square → resize to 512×512 → single embedding

This has limitations:

- **Center-crop discards edges.** Microscope images may be rectangular, and important
  texture detail near the edges is lost.
- **Single global embedding averages over the entire image.** Fine-grained texture
  differences in a specific sub-region may be diluted by the global average.
- **Microscope framing varies.** Slight repositioning between captures can shift which
  content falls inside vs. outside the center crop.

## Alternative Approaches

### Padded Resize

Resize the full image into a square canvas with padding (black, white, or reflected).
Preserves all content but introduces artificial border regions.

### Multi-Crop Embedding Fusion

Generate multiple overlapping crops from the image and fuse their embeddings:
- 5-crop (center + 4 corners)
- Grid crops (4×4 tiles)
- Random crops during training; fixed grid during inference

Fusion strategies: mean pooling, max pooling, learned aggregation.

### Patch-Based Embedding

Divide the normalized image into a grid of patches (e.g., 4×4 = 16 patches of 128×128
from a 512×512 image). Each patch produces its own embedding. The set of patch embeddings
represents the image.

**Advantages:**
- Preserves spatial detail that global embeddings lose
- Enables patch-level similarity (find which sub-region matches a reference)
- Supports variable image sizes without cropping
- Aligns with ViT/DINOv2 patch-token architectures

**Challenges:**
- Storage: 16 embeddings per image vs 1 (16× storage and search cost)
- Search: patch-to-patch matching is more complex than image-to-image
- Aggregation: how to combine patch scores into a region score

## Possible Schema

If patch-based embeddings become first-class derivatives, the schema could include:

```text
image_patches
  id UUID
  image_asset_id UUID (parent)
  patch_index INT
  row INT
  col INT
  x_offset INT
  y_offset INT
  width INT
  height INT
  patch_object_uri TEXT (optional — stored patch image)

patch_embeddings
  id UUID
  image_patch_id UUID
  embedding vector(N)
  embedding_model_version TEXT
  created_at TIMESTAMP
```

Aggregation could happen at query time (mean of patch similarities) or be precomputed.

## Why Design Before Scale

Once a reference library contains thousands of images with global embeddings, adding
patch-level embeddings requires:
- Re-processing all reference images into patches
- Generating and storing 16× more embeddings
- Updating vector search to support patch-level queries
- Re-running all evaluations

Designing the patch strategy early — even if not implementing it immediately — avoids
committing to a global-only approach that may need to be replaced.

## Recommendation

1. **Evaluate multi-crop vs. center-crop** on public external datasets (FabricNET,
   LeaData) during Phase 2 of the ML improvement roadmap
2. **Design patch schema** before committing to large-scale real reference ingestion
3. **Implement patch embeddings** only after empirical evidence shows they improve
   nearest-neighbor quality over global embeddings on real microscope data

## Related Documents

- [ML Technology Explained](../../../docs/ml-technology-explained.md)
- [ML Improvement Roadmap](../../../docs/roadmaps/ml-improvement-roadmap.md)
- [ADR-0002: Embedding Dimension and Backbone](adr-0002-learned-embedding-dimension-and-backbone.md)
