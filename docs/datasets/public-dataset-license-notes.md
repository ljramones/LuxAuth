# Public Dataset License Notes

## General Rules

1. **Review the license** before downloading or using any public dataset
2. **Do not assume commercial use is allowed** — most academic datasets restrict it
3. **Do not commit dataset images** to this repository
4. **Record source URL, citation, and license** in the dataset manifest
5. **Do not distribute** dataset images or derivatives externally

## Per-Dataset Notes

### LeaData
- Academic research dataset
- Review original publication and dataset page for license terms
- Microscopic leather images — no brand-specific content expected

### FabricNET
- Academic research dataset
- Review original publication for license terms
- Microscopic fabric images — no brand-specific content expected

### TILDA / AITEX
- Textile defect datasets
- Typically available for research use
- Review individual dataset licenses

### DTD (Describable Textures Dataset)
- Published by VGG group
- Commonly used in research — review license for commercial restrictions

### LFFD / Luxury Fashion Datasets
- **Extra caution required**
- May contain brand logos, trademarks, or copyrighted imagery
- Label schemas may not align with authentication use cases
- Do not use for training without thorough license and label review

## In Manifests

Every manifest must include:
```yaml
source_url: "URL where dataset was obtained"
source_license: "License identifier (e.g., CC BY 4.0)"
source_citation: "BibTeX or full citation"
commercial_use_allowed: false  # Default false; change only after license review
```
