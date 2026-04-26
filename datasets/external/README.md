# External Datasets Staging Area

This directory contains **downloaded public datasets** used for pipeline validation, embedding testing, and metric learning experiments in LuxAuth.

> **Important**: This folder is **gitignored**.
> **Do not commit any dataset images or large files.**
> See [dataset-storage-policy.md](../../docs/datasets/dataset-storage-policy.md) for full storage, licensing, and governance rules.

## Directory Structure

```text
datasets/external/
├── README.md
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

## Dataset Inventory

### 1. LeaData (V1 & V2)
- **Type**: Microscopic leather images
- **Size**: V1 ~1,200 images; V2 ~38k images
- **Content**: High-resolution microscopic images of leather from multiple species (buffalo, cow, goat, sheep)
- **Best for**: Leather grain texture embeddings, species-level variation, baseline material fingerprinting
- **Region code**: `EXTERNAL_LEATHER_TEXTURE`
- **Source**: Dryad repository
- **License**: Research / non-commercial (cite the paper)
- **Ingestion status**: V1 ingested and tested; V2 adapter ready but not yet ingested

### 2. FabricNET
- **Type**: Microscopic woven fabrics
- **Size**: ~130 images + FabricNet_parameters.xlsx
- **Content**: Microscopic images of woven fabrics with metadata (weft, warp, mass, texture type)
- **Best for**: Early pipeline validation and woven/canvas texture testing
- **Region code**: `EXTERNAL_FABRIC_TEXTURE`
- **Source**: Kaggle
- **License**: CC BY-NC-SA 4.0
- **Ingestion status**: Ingested and tested

### 3. TILDA Textile Texture Database (CD1+CD2)
- **Type**: High-resolution fabric textures with defects
- **Size**: ~3,200 TIF images (~1.2 GB)
- **Content**: Industrial textile images across multiple fabric types with annotated defects (holes, oil spots, thread errors, etc.)
- **Best for**: Fabric defect detection, weave variation, anomaly vs. normal clustering
- **Region code**: `EXTERNAL_FABRIC_TEXTURE`
- **Source**: University of Freiburg
- **License**: Research use (see original PDF)
- **Ingestion status**: Adapter and manifest ready; not yet ingested

### 4. Ten Fabrics Dataset (TFD)
- **Type**: Scanned fabric patches with defects
- **Size**: 3,000 images (256×256 patches)
- **Content**: 10 different fabric types; 75% defect-free, 25% defective
- **Best for**: Real scanned fabric inspection, multi-fabric generalization
- **Region code**: `EXTERNAL_FABRIC_TEXTURE`
- **Source**: Kaggle
- **License**: Check dataset page
- **Ingestion status**: Adapter and manifest ready; not yet ingested

### 5. Multi-Class Fabric Defect Detection Dataset
- **Type**: Production-line fabric images
- **Size**: 3,077 high-res PNG images (1280×720)
- **Content**: 9 classes (defect-free + 8 defect types)
- **Best for**: Realistic manufacturing defects, anomaly detection, OOD testing
- **Region code**: `EXTERNAL_FABRIC_TEXTURE`
- **Source**: Kaggle
- **License**: Research / non-commercial
- **Ingestion status**: Adapter and manifest ready; not yet ingested

### 6. AITEX Fabric Image Database
- **Type**: Industrial fabric defect database
- **Size**: 245 images (4096×256)
- **Content**: 7 fabric types; 140 defect-free + 105 defective images with masks
- **Best for**: Clean defect detection benchmark, high-resolution texture
- **Region code**: `EXTERNAL_FABRIC_TEXTURE`
- **Source**: AITEX + Kaggle mirror
- **License**: Research use
- **Ingestion status**: Adapter and manifest ready; not yet ingested

### 7. Leather Defect Classification
- **Type**: Leather surface defects
- **Size**: Several thousand images
- **Content**: Multiple defect classes (folding marks, grain off, pinhole, growth marks, loose grain, etc.)
- **Best for**: Complementing LeaData with real-world leather anomalies
- **Region code**: `EXTERNAL_LEATHER_TEXTURE`
- **Source**: Kaggle
- **License**: Check dataset page
- **Ingestion status**: Adapter and manifest ready; not yet ingested

### 8. Chanel Luxury Bags Dataset
- **Type**: Macro product photography (not microscopic)
- **Size**: ~12k images
- **Content**: Chanel handbags, accessories — mix of authentic and potentially questionable items
- **Best for**: Later-stage brand/model similarity testing (after microscopic pipeline is mature)
- **Region code**: `EXTERNAL_LUXURY_MACRO`
- **Source**: Innovatiana / research collection
- **License**: Review carefully before any use — may contain brand imagery
- **Ingestion status**: Adapter and manifest ready; **deferred** until microscopic pipeline is stable
- **Note**: Use only after microscopic textures are validated. Extra license caution required.

## Usage Guidelines

- **Ingestion**: Use `make ingest-external-dataset MANIFEST=...` from auth-platform. Always create a new `reference_dataset_version` per dataset.
- **Label mapping for defect datasets**:
  - Defect-free / good / normal → `NORMAL_TEXTURE`
  - Defect / anomaly → `DEFECTIVE_TEXTURE`
- **Do not mix** datasets from different sources in the same `reference_dataset_version`.
- **Do not claim** authentication accuracy from any external dataset.
- **Currently tested**: LeaData V1 and FabricNET only. Other datasets have adapters but have not been ingested yet.

## Ingestion Priority

| Priority | Dataset | Reason |
|---|---|---|
| ✅ Done | LeaData V1 | Microscopic leather baseline |
| ✅ Done | FabricNET | Microscopic fabric baseline |
| Next | TILDA | Large-scale fabric with defects |
| Next | Leather Defect Classification | Leather anomaly detection |
| Later | LeaData V2 | Scale test (38k images) |
| Later | Ten Fabrics Dataset | Multi-fabric generalization |
| Later | Multi-Class Fabric Defect | Production defect types |
| Later | AITEX | High-res defect benchmark |
| Deferred | Chanel Luxury Bags | Macro photos; requires microscopic stability first |

**Last Updated**: April 2026
