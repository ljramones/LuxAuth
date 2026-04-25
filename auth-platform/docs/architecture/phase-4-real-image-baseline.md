# Phase 4: Real Image Evidence + Baseline Texture Embeddings

## Overview

Phase 4 replaces stub/fake image processing with real image handling and deterministic 
computer-vision-based texture embeddings. This is **not** a trained ML model — it is a 
baseline feature extraction pipeline that proves the end-to-end architecture works with 
real images.

## What Changed

### Evidence Upload
- Real image validation (format, dimensions, decode check)
- SHA-256 checksums
- Image metadata stored (width, height, format, color mode)
- Non-image files are rejected with HTTP 400

### Image Quality
- Real quality metrics using OpenCV:
  - Sharpness via variance of Laplacian
  - Exposure via luminance histogram analysis
  - Glare detection via bright/low-saturation pixel ratio
- Configurable thresholds
- Blurry, overexposed, underexposed, and glare images are correctly detected

### Normalization
- EXIF orientation correction
- RGB conversion
- Center-crop to square
- Resize to 512x512
- Output as PNG

### Embeddings
- **texture_baseline_v0.1.0**: 128-dimensional feature vector
- Computed from:
  - Grayscale intensity histogram (32 bins)
  - Color channel histograms (3×16 = 48 bins)
  - Edge/gradient histogram (32 bins)
  - Local variance histogram (16 bins)
- Normalized to unit length
- Stored in pgvector with HNSW index

### Vector Search
- Real pgvector cosine similarity queries against reference_embeddings
- Filtered by region_code for like-for-like comparison
- Returns authentic and counterfeit cluster scores
- Falls back to stub behavior if no reference embeddings exist

## Important Disclaimers

1. **texture_baseline_v0.1.0 is NOT a trained ML model.** It extracts hand-crafted 
   texture features. A production system would use a trained metric-learning model 
   (e.g., ResNet + ArcFace/triplet loss).

2. **Synthetic test images are NOT real luxury products.** The `sample_data/` directory 
   contains procedurally generated textures for pipeline testing only.

3. **SageMaker remains deferred.** See ADR-0001.

4. **This does NOT authenticate real products.** Real authentication requires:
   - Curated, labeled dataset of authentic and counterfeit items
   - Controlled microscopic imaging hardware
   - Trained metric-learning or contrastive model
   - Expert validation and review
   - Statistical validation on holdout sets

## Embedding Dimensions

| Model | Dimensions | Type |
|---|---|---|
| stub_embedder_v0.1.0 (Phase 1-3) | 768 | Fake random vectors |
| texture_baseline_v0.1.0 (Phase 4) | 128 | Hand-crafted texture features |
| Future trained model | 256-768 | Learned metric embeddings |
