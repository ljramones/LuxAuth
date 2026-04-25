# Capture Intake Service

Device-agnostic capture session management. Accepts image evidence and metadata
from any capture client (mobile app, desktop, Raspberry Pi, lab rig).

**Does NOT control microscope hardware.** The capture client owns device interaction.

## Port: 8106

## Endpoints

- `GET /health` — Health check
- `GET /capture-protocols` — List active protocols
- `GET /capture-protocols/{code}` — Get protocol with regions
- `POST /capture-protocols` — Create protocol
- `POST /capture-sessions` — Create capture session
- `GET /capture-sessions/{id}` — Get session
- `GET /capture-sessions/{id}/status` — Region completeness status
- `POST /capture-sessions/{id}/images` — Upload capture image
- `POST /capture-sessions/{id}/complete` — Mark session complete/incomplete
