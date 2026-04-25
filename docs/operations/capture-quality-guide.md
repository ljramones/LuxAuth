# Capture Quality Guide

How to capture better microscope images for the authentication pipeline.

## Focus

- Use the microscope's manual or fixed focus at the target working distance
- Verify sharpness before capturing — the quality service checks Laplacian variance
- If the quality service reports `LOW_SHARPNESS`, the image is too soft
- Avoid auto-focus that hunts between captures — use a fixed distance

## Exposure

- Target mid-range luminance (not too dark, not too bright)
- The quality service flags `UNDEREXPOSED` (mean luminance <40) and `OVEREXPOSED` (>220)
- Use manual exposure if your microscope supports it
- Check a few test captures before a full session

## Glare Control

- Glare appears as bright white spots with low color saturation
- The quality service flags `EXCESSIVE_GLARE` when >15% of pixels are bright+desaturated
- Solutions:
  - Add a polarizing filter
  - Use a diffuser on the light source
  - Angle the light source away from specular reflection
  - For metal surfaces (hardware, zippers), cross-polarization helps

## Lighting Consistency

- Keep the same lighting setup for all captures in a session
- Do not mix natural light with artificial light
- Document the lighting profile in the manifest
- Different microscope positions may create different shadows — be aware

## Region Coverage

- Center the target region in the field of view
- Avoid capturing partial regions or regions cut off at the edge
- The protocol defines which regions to capture — follow it exactly
- If a region is physically damaged or inaccessible, note it in the manifest

## Multiple Images Per Region

- The protocol specifies minimum images per region (e.g., 3 for EXTERIOR_CANVAS)
- Capture from slightly different positions within the same region
- This improves embedding robustness and similarity matching
- Do not duplicate the exact same capture — slightly vary position

## File Format

- Prefer PNG or TIFF for lossless capture
- JPEG is acceptable but avoid heavy compression (quality <85)
- Do not use proprietary microscope formats that cannot be decoded by Pillow
- Supported: JPEG, PNG, TIFF, BMP

## What to Avoid

- Do not post-process images (no sharpening, no color correction, no cropping)
- Do not compress images after capture
- Do not rename files inconsistently — match the manifest
- Do not mix captures from different devices in the same batch without documenting it
- Do not capture with the lens cap on (it happens)

## Documenting Failed Captures

- If a capture is unusable, either exclude it from the manifest or mark it in notes
- The validation script will flag quality failures
- Do not delete raw captures — they are evidence even if unusable
