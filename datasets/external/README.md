
```markdown
# External Datasets Staging Area

This directory contains **downloaded public datasets** used for pipeline validation, embedding testing, and metric learning experiments in LuxAuth.

> **Important**: This folder is **gitignored**.  
> **Do not commit any dataset images or large files.**  
> See `dataset-storage-policy.md` for full storage, licensing, and governance rules.

## Directory Structure

```bash
datasets/external/
├── README.md                  ← This file
├── AITEX-Fabric-Image-Database/
├── dataset-chanel-luxury-bags/
├── fabricnet/
├── LeaData-V1/
├── LeaData-V2/
├── Leather-Defect-Classification/
├── Multi-Class-Fabric-Detection-Dataset/
├── Ten-Fabrics-Dataset-TFD/
└── tilda_CD1+CD2/
```

---

## Dataset Inventory

### 1. LeaData (V1 & V2)
- **Type**: Microscopic leather images
- **Size**: ~38k images (V2 is the larger version)
- **Content**: High-resolution microscopic images of leather from multiple species (buffalo, cow, goat, sheep)
- **Best for**: Leather grain texture embeddings, species-level variation, baseline material fingerprinting
- **Region code suggestion**: `EXTERNAL_LEATHER_TEXTURE`
- **Source**: Dryad repository
- **License**: Research / non-commercial (cite the paper)

### 2. FabricNET
- **Type**: Microscopic woven fabrics
- **Size**: Small (~130 images + parameters)
- **Content**: Microscopic images of woven fabrics with metadata (weft, warp, mass, texture type)
- **Best for**: Early pipeline validation and woven/canvas texture testing
- **Region code suggestion**: `EXTERNAL_FABRIC_TEXTURE`
- **Source**: Kaggle
- **License**: CC BY-NC-SA 4.0

### 3. TILDA Textile Texture Database (CD1+CD2)
- **Type**: High-resolution fabric textures with defects
- **Size**: ~3,200 TIF images (~1.2 GB)
- **Content**: Industrial textile images across multiple fabric types with annotated defects (holes, oil spots, thread errors, etc.)
- **Best for**: Fabric defect detection, weave variation, anomaly vs. normal clustering
- **Region code suggestion**: `EXTERNAL_FABRIC_TEXTURE`
- **Source**: University of Freiburg
- **License**: Research use (see original PDF)

### 4. Ten Fabrics Dataset (TFD)
- **Type**: Scanned fabric patches with defects
- **Size**: 3,000 images (256×256 patches)
- **Content**: 10 different fabric types; 75% defect-free, 25% defective. Includes ground-truth block annotations.
- **Best for**: Real scanned fabric inspection, multi-fabric generalization
- **Region code suggestion**: `EXTERNAL_FABRIC_TEXTURE`
- **Source**: Kaggle
- **License**: Check dataset page

### 5. Multi-Class Fabric Defect Detection Dataset
- **Type**: Production-line fabric images
- **Size**: 3,077 high-res PNG images (1280×720)
- **Content**: 9 classes (defect-free + 8 defect types: hole, horizontal, vertical, lines, pinched fabric, needle mark, broken stitch, stain)
- **Best for**: Realistic manufacturing defects, anomaly detection, OOD testing
- **Region code suggestion**: `EXTERNAL_FABRIC_TEXTURE`
- **Source**: Kaggle
- **License**: Research / non-commercial

### 6. AITEX Fabric Image Database
- **Type**: Industrial fabric defect database
- **Size**: 245 images (4096×256)
- **Content**: 7 fabric types; 140 defect-free + 105 defective images with masks
- **Best for**: Clean defect detection benchmark, high-resolution texture
- **Region code suggestion**: `EXTERNAL_FABRIC_TEXTURE`
- **Source**: AITEX + Kaggle mirror
- **License**: Research use

### 7. Leather Defect Classification
- **Type**: Leather surface defects
- **Size**: Several thousand images
- **Content**: Multiple defect classes on leather (folding marks, grain off, pinhole, growth marks, loose grain, etc.)
- **Best for**: Complementing LeaData with real-world leather anomalies
- **Region code suggestion**: `EXTERNAL_LEATHER_TEXTURE`
- **Source**: Kaggle
- **License**: Check dataset page

### 8. Chanel Luxury Bags Dataset
- **Type**: Macro product photography (not microscopic)
- **Size**: ~12k images
- **Content**: Chanel handbags, accessories — mix of authentic and potentially questionable items
- **Best for**: Later-stage brand/model similarity testing (after microscopic pipeline is mature)
- **Region code suggestion**: `EXTERNAL_LUXURY_MACRO`
- **Source**: Innovatiana / research collection
- **Note**: Use only after microscopic textures are stable

---

## Usage Guidelines

- **Ingestion**: Use your existing ingest scripts. Always create a new `reference_dataset_version` (e.g. `external_tilda_v1`, `external_leather_defect_v1`).
- **Label Mapping**:
  - Defect-free / good / normal → `pseudo_authentic`
  - Any defect → `pseudo_anomalous` or `pseudo_counterfeit`
- **Evaluation**: Run your full evaluation harness after each new dataset.
- **Do not mix** datasets from different sources in the same `reference_dataset_version`.

## Next Steps Recommendations
1. Ingest **TILDA** and **Leather Defect Classification** first.
2. Run baseline vs. learned embedding comparison.
3. Consider generating **synthetic counterfeits** from clean images for stronger metric learning signals.

---

**Last Updated**: April 2026  

```


