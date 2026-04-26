# ML Diagnostics Service

Local-only developer/research service for ML diagnostics and evaluation.

> **This is local research tooling, not a production service.**

## Port: 8401

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | /health | Health check |
| GET | /datasets | List dataset versions with split counts |
| GET | /datasets/{version} | Detailed dataset metadata |
| GET | /models | List model versions |
| GET | /evaluations | List evaluation runs |
| GET | /evaluations/{id} | Evaluation run with items |
| GET | /embedding-analysis | Compute embedding statistics |
| GET | /projections | PCA 2D projection points |
| GET | /neighbors | Nearest-neighbor inspection |

## Notes

- Wraps existing diagnostic queries in a REST API for the capture-workbench UI
- Reports are generated in-memory, not via subprocess scripts
- This service does not train models or modify reference data
- Public external dataset results do not prove luxury authentication accuracy
