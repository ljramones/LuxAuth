# Multi-Sensor Research Track

**Status:** Parallel research track, not adopted. Phase 11 (DINOv2 shadow integration on the microscopy path) remains the active workstream.

This folder holds working artifacts for the multi-sensor authentication research track — a strategic alternative to the in-flight microscopy/DINOv2 pipeline. The strategic-options briefing lives at the repo root for prominence; the operational planning, experiment results, and capture artifacts live in this folder.

## Contents

| File | Purpose |
|---|---|
| [experiment-plan.md](experiment-plan.md) | Phased experiment plan (E0–E6) with explicit go/no-go gates, hardware budgets, success criteria, and failure modes per phase |
| [parts-and-circuits.md](parts-and-circuits.md) | Per-phase parts list, wiring diagrams, and cumulative budget for E0–E6. Covers I2C bus layout, electrode/probe construction, lighting and tent layout, sensor positioning fixtures, integration considerations (pull-ups, power budget, cable lengths), and a deliberately-not-included list. CAD pricing as of 2026. |
| [few-shot-academic-position.md](few-shot-academic-position.md) | Academic-defense position for the multi-sensor system's few-shot operation. Argues that few-shot prototype-based authentication is a property of the embedding space, not the capture modality, and explains how Phase 10's microscopy validation transfers to and is extended in multi-sensor. Names what the system claims, what it doesn't, and what's empirically tested vs assumed. |

## Companion documents (outside this folder)

- [MultiSensorAuthenticationApproach.md](../MultiSensorAuthenticationApproach.md) — strategic-options briefing at repo root. Defines the modality stack, architectural integration, patent posture, and operational definition. The experiment plan in this folder operationalizes that strategic doc.

## Activation gate

The experiment plan does not begin until an explicit decision to start E0 is made. Until then, this folder is dormant. If E0 produces a no-go decision, the folder remains as a record of a strategic option that was considered, tested cheaply, and rejected on evidence.

## What does not belong here

- Phase 11 (microscopy/DINOv2) artifacts — those live under `auth-platform/`, `docs/roadmaps/dinov2-*`, etc.
- Production code or service wiring — this is research-phase exploration. Integration into the production pipeline only happens after the multi-sensor thesis is empirically validated through the phased plan.
- Patent FTO opinions or legal analysis — research-phase work doesn't trigger that. Commercial deployment does, and this folder stops well short of commercial deployment.
