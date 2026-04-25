# scan-recipe-service

Manages scan recipes that define which image regions are required for authenticating a specific brand/category/material combination.

## Endpoints

- `GET /health` - Health check
- `GET /ready` - Readiness check
- `GET /scan-recipes/resolve?brand=&category=&material=` - Resolve matching recipe
- `GET /scan-recipes/{recipe_id}` - Get recipe by ID

## Port

8102
