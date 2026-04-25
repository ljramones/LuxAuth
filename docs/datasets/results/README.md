# Curated Dataset Results

This folder is for manually curated, commit-worthy result summaries only.

## What belongs here

- Hand-written or edited summaries of evaluation findings
- Curated tables or charts extracted from generated reports
- Comparison notes across dataset versions or model versions

## What does NOT belong here

- Raw generated reports (those live in `auth-platform/reports/` and are gitignored)
- Third-party dataset images (license restrictions apply)
- Auto-generated files that change every run

## Workflow

1. Run: `make external-dataset-report DATASET=... MODEL=...`
2. Review the generated report at `auth-platform/reports/external-datasets/{dataset}/{model}/diagnostic-report.md`
3. If findings are worth preserving, copy or summarize into a file here
4. Commit the curated summary

## Existing curated results

- [External Dataset First Run Results](../external-dataset-first-run-results.md) — FabricNET + LeaData V1 initial ingestion and diagnostics
