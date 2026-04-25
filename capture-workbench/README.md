# LuxAuth Capture Workbench

Local web-based operator tooling for microscope capture sessions.

> **This is local development/operator tooling — not a production mobile app.**
> It does not control microscope hardware. It accepts image files captured by
> microscope vendor software and submits them to the backend via HTTP APIs.

## Quick Start

From the repo root:

```bash
make dev             # Starts backend + workbench together
```

Or separately:

```bash
make backend-up      # Start backend Docker stack
make workbench       # Start workbench Vite dev server
```

Or manually:

```bash
# 1. Start backend
cd ../auth-platform
docker compose up --build -d
make health

# 2. Start workbench
cd ../capture-workbench
npm install
npm run dev
```

Open http://localhost:3000

## Configuration

Copy `.env.example` to `.env` (or rely on defaults):

```
VITE_DEVICE_SERVICE_URL=http://localhost:8103
VITE_CAPTURE_INTAKE_SERVICE_URL=http://localhost:8106
VITE_IMAGE_QUALITY_SERVICE_URL=http://localhost:8201
VITE_NORMALIZATION_SERVICE_URL=http://localhost:8202
```

## Workflow

1. **Check backend status** — verify all services are green
2. **Register or select device** — register a local microscope or paste an existing device ID
3. **Create calibration** — record scale/white-balance reference status
4. **Choose capture protocol** — select the required region set (e.g., LV monogram canvas)
5. **Create capture session** — links device, calibration, and protocol
6. **Upload images per region** — drag or select microscope image files
7. **Inspect quality results** — sharpness, exposure, glare scores appear automatically
8. **Complete session** — reports COMPLETE or INCOMPLETE based on region satisfaction

## What This Is

- A local UI for microscope acceptance testing and lab capture workflows
- Connects to the auth-platform Docker services running locally
- File upload only — no live camera control
- Stores selected device/calibration in localStorage for convenience

## What This Is NOT

- Not a production authentication interface
- Not a mobile capture app (those are planned for `iphone-app/` and `android-app/`)
- Does not control microscope hardware
- Does not produce authentication decisions or certificates
- Does not claim to authenticate luxury goods

## Relationship to Future Mobile Apps

The Capture Workbench is a local learning tool for the future iPhone and Android capture
clients. It intentionally exercises the same backend capture APIs that mobile apps will
use, but avoids native-device complexity while the capture workflow is still being
discovered.

Lessons from the workbench will inform:

- Mobile capture-session flow
- Required-region checklist design
- Microscope/camera integration points
- Rescan prompts for failed quality checks
- Image-quality feedback timing
- Offline/retry behavior
- Calibration UX
- Operator metadata fields
- Future live preview and guided capture behavior

## Technology

- Vite + React + TypeScript
- No heavy UI framework
- Connects to backend via browser fetch
