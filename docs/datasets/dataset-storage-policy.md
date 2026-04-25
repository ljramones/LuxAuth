# Dataset Storage Policy

## Where Data Lives

| Data Type | Location | Committed to Git? |
|---|---|---|
| Manifest templates | `datasets/manifests/` | Yes |
| Adapter documentation | `datasets/adapters/` | Yes |
| Downloaded datasets | `datasets/external/` | **No** (gitignored) |
| Synthetic images | `auth-platform/sample_data/` | Yes (small, generated) |
| Reference embeddings | PostgreSQL (pgvector) | No (database) |
| Raw/normalized images | S3/LocalStack | No (object storage) |
| Reports/projections | `auth-platform/reports/` | No (gitignored) |

## Rules

1. **Never commit actual dataset images** — they are large and may have license restrictions
2. **Manifest templates are committed** — they describe datasets without containing images
3. **Generated synthetic data is committed** — it is small, deterministic, and has no license issues
4. **Embeddings and evaluation results** live in PostgreSQL, not in Git
5. **S3 objects** (raw evidence, normalized images) are managed by the backend, not by Git

## Dataset Version Prefixes

| Prefix | Meaning | Example |
|---|---|---|
| `synthetic_*` | Locally generated test data | `synthetic_lv_monogram_v0.1.0` |
| `smoke_*` | Automated test data (auto-cleaned) | `smoke_lab_lv_monogram_batch_001` |
| `external_*` | Public datasets (not committed) | `external_leadata_v0.1.0` |
| `lab_*` | Real microscope captures | `lab_first_real_v0.1.0` |
