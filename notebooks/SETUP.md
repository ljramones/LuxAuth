# Notebook Setup

Notebooks must use the `auth-platform/.venv` environment. The default system
Jupyter kernel may not have the required packages.

## Quick Start

```bash
# From the repo root:
make notebook-deps      # install notebook dependencies into auth-platform venv
make notebook-kernel    # register the Jupyter kernel
make notebook           # start JupyterLab
```

Then in Jupyter: **Kernel > Change Kernel > LuxAuth auth-platform**

## Manual Setup

```bash
cd auth-platform
source .venv/bin/activate
python -m pip install -r ../notebooks/requirements.txt
python -m ipykernel install --user --name luxauth-auth-platform --display-name "LuxAuth auth-platform"
```

Start JupyterLab:

```bash
cd auth-platform
source .venv/bin/activate
jupyter lab --notebook-dir=../notebooks
```

Or classic notebook:

```bash
jupyter notebook --notebook-dir=../notebooks
```

## Backend Access

Notebooks that query Postgres or S3 require the backend to be running:

```bash
# From repo root:
make backend-up

# Verify:
make backend-health
```

## Troubleshooting

### ModuleNotFoundError: numpy / matplotlib / pandas

**Cause:** Wrong kernel selected or dependencies not installed.

**Fix:** Run `make notebook-deps` and select the **LuxAuth auth-platform** kernel
in Jupyter (Kernel > Change Kernel).

### zsh: no matches found: psycopg[binary]

**Cause:** zsh interprets square brackets as glob patterns.

**Fix:** Quote the package name when installing manually:

```bash
pip install 'psycopg[binary]'
```

Or install from the requirements file which handles this automatically:

```bash
pip install -r ../notebooks/requirements.txt
```

### FigureCanvasAgg is non-interactive / plots don't display

**Cause:** Notebook uses `matplotlib.use("Agg")` which disables inline display.

**Fix:** Use `%matplotlib inline` instead. All committed notebooks should already
have this. If you see `matplotlib.use("Agg")` in a notebook, replace it with
`%matplotlib inline`.

### Database connection failed

**Cause:** Backend Postgres is not running.

**Fix:**

```bash
make backend-up
# or from auth-platform:
make health
```
