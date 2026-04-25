# Phase 8A: Device-Agnostic Capture Intake APIs

## Overview

Phase 8A adds backend APIs that allow any capture client (mobile app, desktop client,
Raspberry Pi agent, or vendor SDK wrapper) to submit microscope images and capture
metadata into the existing evidence pipeline.

## Key Architectural Rule

**The backend accepts captured evidence and metadata. It does NOT directly control
the microscope.**

The capture client (whatever form it takes) is responsible for:
- Connecting to the microscope hardware
- Controlling focus, lighting, magnification
- Capturing images
- Submitting images to the capture intake APIs

The backend is responsible for:
- Validating the capture session and protocol
- Validating uploaded images
- Storing raw evidence immutably in S3
- Publishing to the image quality pipeline
- Tracking region completeness

## Session Types

| Type | Purpose | Source |
|---|---|---|
| Scan session | Authentication pipeline | scan-session-service |
| Capture session | Device capture intake | capture-intake-service |
| Capture batch | Manifest-based lab ingestion | future batch service |

## Capture Flow

```text
Capture Client (app/desktop/Pi)
  │ POST /capture-sessions
  │ POST /capture-sessions/{id}/images (for each region)
  │ POST /capture-sessions/{id}/complete
  ▼
capture-intake-service (port 8106)
  │ validates protocol, region, image
  │ stores in S3
  │ publishes to image-quality-queue
  ▼
existing pipeline: quality → norm → embed → search → score → decision
```

## Capture Protocol

A capture protocol defines which regions must be captured and minimum image counts.
The default protocol `lv_monogram_canvas_handbag_capture` requires:

| Region | Min Images |
|---|---|
| EXTERIOR_CANVAS | 3 |
| FRONT_LOGO_PRINT | 2 |
| INTERIOR_HEAT_STAMP | 2 |
| HARDWARE_ENGRAVING | 2 |
| STITCHING_DETAIL | 3 |

## Session Lifecycle

```text
CREATED → CAPTURING → COMPLETE / INCOMPLETE
```

- CREATED: session registered, no images yet
- CAPTURING: first image uploaded
- COMPLETE: all required regions satisfied
- INCOMPLETE: completion requested but regions missing

## Device Registration

Devices are registered with:
- device_serial, device_type, manufacturer, firmware_version
- Calibration profiles (scale reference, white balance, magnification)

## Disclaimers

- No vendor-specific microscope control is implemented
- The backend is device-agnostic by design
- A future mobile app or desktop client will implement the capture UI
- SageMaker remains deferred
