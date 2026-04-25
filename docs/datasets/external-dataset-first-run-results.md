# External Dataset First Run Results

**Date:** 2026-04-25

## Datasets Evaluated

| Dataset | Version | Local Path | Manifest | Images | Items | Errors |
|---|---|---|---|---|---|---|
| FabricNET | external_fabricnet_v0.1.0 | datasets/external/fabricnet | fabricnet-manifest.yaml | 130 | 130 | 0 |
| LeaData V1 | external_leadata_v0.1.0 | datasets/external/LeaData-V1 | leadata-manifest.yaml | 1200 | 16 | 0 |

## FabricNET Results

### Dataset Structure
- Flat directory: 130 JPG images (W001.jpg–W130.jpg)
- Metadata: FabricNet_parameters.xlsx (not parsed in this run — openpyxl not installed)
- Each image is one fabric sample — 130 items, 1 image each

### Splits
- Train: 78 items
- Validation: 26 items
- Test: 26 items

### Labels
- primary_label: sample ID (W001, W002, etc.)
- authenticity_status: PUBLIC_DATASET_CLASS (not authentic/counterfeit)
- region_code: EXTERNAL_FABRIC_TEXTURE

### Evaluation Summary
- Total test items: 52
- All classified as INCONCLUSIVE (expected — single-class dataset with no authentic/counterfeit distinction)
- Evaluation framework confirms pipeline runs correctly on real images

### Embedding Diagnostics
- 130 embeddings, 128 dimensions
- Vector norms: mean 1.0 (close to unit length; consistent with expected normalization)
- NN label agreement: 100% (all fabric images find other fabric images)
- Pairwise cosine similarity among fabric images: mean ~0.67, range -0.20 to 1.00
- Within-dataset texture variation appears present based on the similarity range; further analysis needed to confirm whether the baseline features capture meaningful fabric distinctions

### Nearest-Neighbor Observations
- Top-3 neighbors all fabric images with similarity 0.90–0.99
- No cross-domain contamination (fabric images do not match synthetic reference data)

## LeaData V1 Results

### Dataset Structure
- 4 species directories: Buffalo, Cow, Goat, Sheep
- 300 images per species (1200 total)
- Filenames: `{SamplePrefix} ({index}).jpg` (e.g., `CBTS3 (1).jpg`)
- 16 distinct sample groups inferred from filename prefixes

### Splits (by sample group)
- Train: 10 sample groups
- Validation: 3 sample groups
- Test: 3 sample groups
- All images from a sample group stay in the same split (no leakage)

### Labels
- primary_label: species (Buffalo, Cow, Goat, Sheep)
- secondary_labels: sample_group (e.g., CBTS3, GBTS16)
- authenticity_status: PUBLIC_DATASET_CLASS
- region_code: EXTERNAL_LEATHER_TEXTURE

### Evaluation Summary
- Total test items: 303
- All classified as INCONCLUSIVE (expected — single-class dataset)
- Pipeline processes 1200 real microscopic leather images without errors

### Embedding Diagnostics
- 1200 embeddings, 128 dimensions
- Vector norms: mean 1.03 (close to unit length; worth monitoring because embeddings are expected to be normalized)
- NN label agreement: 99.6% (leather images find other leather images)
- Mean pairwise similarity: 0.66
- Similarity range: -0.25 to 1.00

### Nearest-Neighbor Observations
- Leather images consistently find other leather images as nearest neighbors
- Some within-species clustering visible (not quantified in this run)

## Adapter Modifications

Both adapters required updates from their original template-based versions:

### FabricNET Adapter
- Changed from expecting subdirectory structure to handling flat directory
- Added XLSX metadata parsing (optional, via openpyxl)
- Sample ID extracted from filename pattern (W001, W002, etc.)

### LeaData Adapter
- Changed from expecting `images/{species}/{body_part}/` to `{Species}/{filename}.jpg`
- Added regex-based sample prefix extraction from filenames with spaces
- Sample grouping by filename prefix (CBTS3, GBTS16, etc.)

## Known Limitations

1. **Evaluation shows all INCONCLUSIVE** — expected because these datasets have a single
   authenticity class (PUBLIC_DATASET_CLASS). The evaluation framework is designed for
   authentic-vs-counterfeit comparison. Future work could add within-class species/type
   evaluation.

2. **FabricNET XLSX metadata not parsed** — requires openpyxl. Fabric type, weave pattern,
   and thread count metadata could enrich labels.

3. **LeaData split assignment is by sample group, not by species** — this means species
   distribution across splits may be uneven. A species-stratified split would be better.

4. **No cross-dataset evaluation** — FabricNET and LeaData are evaluated independently.
   Cross-material embedding behaviour not tested.

## Disclaimers

- **These results validate pipeline behavior on public texture/material data.**
- **These results do NOT indicate luxury authentication accuracy.**
- **These datasets are NOT authentic-vs-counterfeit luxury datasets.**
- **FabricNET and LeaData are academic research datasets used under their respective licenses.**
- **Third-party dataset images are stored locally only and are not committed to the repository.**
