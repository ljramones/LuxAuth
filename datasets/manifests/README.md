# Dataset Manifests

YAML manifests describe external public datasets for ingestion into the LuxAuth backend.

Each manifest specifies:
- Dataset source, license, and citation
- Local file path
- Label schema
- Split strategy

## Usage

1. Copy a template (e.g., `leadata-manifest.template.yaml`)
2. Fill in `source_url`, `source_license`, `source_citation`
3. Update `local_path` if your download location differs
4. Run: `cd auth-platform && make ingest-external-dataset MANIFEST=../datasets/manifests/leadata-manifest.yaml`

## Templates

- `leadata-manifest.template.yaml` — Microscopic leather textures
- `fabricnet-manifest.template.yaml` — Microscopic woven fabric textures
