# Datasets

This directory stages dataset metadata, manifests, and adapters for external public
datasets used to evaluate LuxAuth's ingestion, embedding, and search behavior.

**Actual dataset images are NOT committed to this repository.**

## Structure

```text
datasets/
├── README.md           This file
├── manifests/          Manifest templates for each dataset
├── adapters/           Documentation for dataset adapters
└── external/           Local staging for downloaded datasets (gitignored)
```

## Usage

1. Download a public dataset and place it under `datasets/external/{dataset_name}/`
2. Copy the manifest template from `datasets/manifests/` and fill in local paths
3. Run ingestion from auth-platform:
   ```bash
   cd auth-platform
   make ingest-external-dataset MANIFEST=../datasets/manifests/leadata-manifest.yaml
   ```

## Important

- `datasets/external/` is gitignored — downloaded datasets stay local
- Public datasets are for pipeline evaluation, not luxury authentication
- See [docs/datasets/dataset-storage-policy.md](../docs/datasets/dataset-storage-policy.md)
