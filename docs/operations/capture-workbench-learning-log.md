# Capture Workbench Learning Log

## 1. Purpose

The capture-workbench is a local learning tool, not a production app. It exercises the
same backend capture APIs that future iPhone and Android clients will use, but in a
browser-based file-upload workflow that avoids native-device complexity.

Observations from using the workbench should drive:
- iPhone/Android capture UX design
- Microscope capture protocol improvements
- Image quality threshold tuning
- Backend API improvements
- Operator training and documentation

This document provides a structured template for recording those observations after each
capture session.

---

## 2. When to Use This Log

Record observations whenever you run a capture session through the workbench:

- Synthetic workflow tests (uploaded generated images)
- Public dataset image upload experiments (FabricNET, LeaData images)
- Microscope acceptance testing (first real device captures)
- First real lab captures of luxury items
- Capture protocol tuning (adjusting regions, min image counts)
- UI/UX experiments (testing operator flow)
- Image quality threshold evaluation (testing sharpness/exposure/glare thresholds)
- Operator workflow reviews (watching someone else use the workbench)

---

## 3. Session Metadata Template

Copy this template for each session entry:

```markdown
### Session: YYYY-MM-DD — [short description]

| Field | Value |
|---|---|
| Date/time | |
| Operator | |
| Device used | |
| Device connection type | USB / Wi-Fi / file transfer |
| Calibration profile | |
| Capture protocol | |
| Capture session ID | |
| Backend environment | local Docker Compose |
| Dataset/case type | synthetic / public external / microscope acceptance / lab gold-set |
| Item or target description | |
| Notes | |
```

---

## 4. Capture Checklist

Use this checklist during or after each session:

- [ ] Backend services healthy (`make health` all green)
- [ ] Device selected or registered
- [ ] Calibration profile selected or created
- [ ] Capture protocol selected
- [ ] Required regions visible in UI
- [ ] `external_item_id` set correctly
- [ ] Images uploaded for each required region
- [ ] Quality results reviewed (sharpness, exposure, glare)
- [ ] Normalized result reviewed (URI or status)
- [ ] Session completed via "Complete Session"
- [ ] Missing regions reviewed
- [ ] Notes recorded in this log

---

## 5. Region-Level Observation Template

Copy this template for each region captured:

```markdown
### Region: `<REGION_CODE>`

| Field | Observation |
|---|---|
| Required image count | |
| Images uploaded | |
| Quality status | PASS / FAIL / mixed |
| Sharpness observations | |
| Exposure observations | |
| Glare observations | |
| Framing difficulty | easy / moderate / hard |
| Retakes required | 0 / 1 / 2+ |
| Operator confusion | none / minor / significant |
| Example image needed? | yes / no |
| Suggested capture instruction change | |
| Mobile app implication | |
```

---

## 6. Quality Failure Log

Record image quality failures and their likely causes:

| Image / Region | Failure | Likely Cause | Retake Needed? | Suggested Fix |
|---|---|---|---|---|
| | `LOW_SHARPNESS` | focus / motion / surface texture | | |
| | `UNDEREXPOSED` | lighting too dim / device setting | | |
| | `OVEREXPOSED` | lighting too bright / reflection | | |
| | `EXCESSIVE_GLARE` | specular reflection on metal/coated surface | | |
| | `IMAGE_TOO_SMALL` | export setting / capture mode / resolution | | |
| | `DECODE_FAILED` | unsupported file format / file corruption | | |

---

## 7. Operator Pain Points

After each session, answer these prompts:

- What was confusing about the workflow?
- Which step took the longest?
- Which region was hardest to capture?
- Did the operator know when to retake a failed image?
- Did the UI provide enough feedback after upload?
- Was the calibration step understandable?
- Were backend error messages clear when something failed?
- Was the difference between a capture session and an authentication decision clear?
- Did the operator expect a final "authentic/fake" result?

---

## 8. Backend/API Observations

Record any backend issues:

- Any failed HTTP requests? What was the status code and message?
- Any slow polling behavior (quality results taking too long)?
- Any unclear or unexpected response shape?
- Any missing endpoint that would have been useful?
- Any confusing error message from the backend?
- Any need for an image proxy/preview endpoint (to view S3 images in the browser)?
- Any need for batch upload (multiple files at once)?
- Any need for retry or offline upload behavior?

---

## 9. Capture Protocol Observations

Evaluate the capture protocol based on the session:

- Are the required regions correct for this item/target?
- Are min image counts too high or too low?
- Are region names clear to the operator?
- Are region instructions sufficient, or does the operator need examples?
- Should some regions require reference example images?
- Should some regions have different quality thresholds (e.g., hardware allows more glare)?
- Should glare-sensitive regions (HARDWARE_ENGRAVING) have special capture guidance?

---

## 10. Mobile App Implications

Each session should produce mobile requirements where applicable:

| Observation | Future Mobile Requirement |
|---|---|
| Operator needed example image for a region | Add region example/overlay in capture UI |
| Glare failures common on hardware | Add live glare warning before capture |
| Retakes frequent due to blur | Add pre-upload sharpness check or focus indicator |
| Calibration step confusing | Add guided calibration wizard |
| Network/API delay noticeable | Add upload queue with background retry and status polling |
| Metadata entry repetitive across regions | Add session-level defaults and templates |
| Operator unsure when session is done | Add visual progress bar for region completeness |
| Operator expected authentication result | Add clear separation between capture and auth submission |

---

## 11. Decision / Authentication Boundary Notes

The capture-workbench currently completes capture sessions only. It does **not** issue
authentication decisions or certificates.

If operators expect a final authentication result after completing a capture session,
record that as a product requirement. Future mobile UX may need:

- A separate "submit for authentication" step after capture completion
- Clear labeling that capture ≠ authentication
- A status screen showing "capture complete, authentication pending" vs "authenticated"

---

## 12. Session Summary Template

Copy this template to summarize each session:

```markdown
### Session Summary

**What worked well:**

- 

**What failed or confused the operator:**

- 

**Most common quality issue:**

- 

**Regions needing better guidance:**

- 

**Backend/API changes suggested:**

- 

**Capture protocol changes suggested:**

- 

**Mobile app requirements discovered:**

- 

**Follow-up actions:**

- 
```

---

## 13. Example Entry

> This is a fictional example using a non-brand test target.

### Session: 2026-04-26 — USB microscope acceptance with woven cloth

| Field | Value |
|---|---|
| Date/time | 2026-04-26 10:30 |
| Operator | Larry |
| Device used | Generic USB microscope (200x) |
| Device connection type | USB |
| Calibration profile | workbench_cal_initial |
| Capture protocol | lv_monogram_canvas_handbag_capture (used as test template) |
| Capture session ID | abc12345-... |
| Backend environment | local Docker Compose |
| Dataset/case type | microscope acceptance |
| Item or target description | Woven cotton cloth sample for focus/lighting validation |
| Notes | First session with new microscope. Testing workflow only. |

### Region: `EXTERIOR_CANVAS` (simulated with cloth surface)

| Field | Observation |
|---|---|
| Required image count | 3 |
| Images uploaded | 4 (1 retake) |
| Quality status | mixed (3 PASS, 1 FAIL) |
| Sharpness observations | First image blurry — microscope not yet focused |
| Exposure observations | Good after adjusting desk lamp position |
| Glare observations | None on cloth — would expect issues on leather/metal |
| Framing difficulty | easy |
| Retakes required | 1 |
| Operator confusion | None for this region |
| Example image needed? | No |
| Suggested capture instruction change | Add "verify focus before first capture" step |
| Mobile app implication | Live focus indicator before capture button |

### Quality Failure Log

| Image / Region | Failure | Likely Cause | Retake Needed? | Suggested Fix |
|---|---|---|---|---|
| EXTERIOR_CANVAS image 1 | LOW_SHARPNESS | Microscope not focused at start | Yes | Add focus check prompt |

### Session Summary

**What worked well:**
- Backend services connected immediately
- Upload flow was straightforward
- Quality scores appeared within a few seconds

**What failed or confused the operator:**
- First image was out of focus — no pre-capture warning
- Wasn't sure if calibration was required or optional

**Most common quality issue:**
- LOW_SHARPNESS on first capture before focusing

**Regions needing better guidance:**
- All regions could benefit from a "check focus" reminder

**Backend/API changes suggested:**
- None for this session

**Capture protocol changes suggested:**
- Consider adding a "focus verification capture" step before the real protocol begins

**Mobile app requirements discovered:**
- Live focus indicator (sharpness preview) before capture
- Guided calibration step with explanation of why it matters

**Follow-up actions:**
- Try hardware/metal target to test glare detection
- Try leather sample to test texture variation

---

## 14. Related Documents

- [Capture Workbench README](../../capture-workbench/README.md)
- [Microscope Acceptance Runbook](microscope-acceptance-runbook.md)
- [Capture Quality Guide](capture-quality-guide.md)
- [First Real Capture Checklist](first-real-capture-checklist.md)
- [Capture Manifest Template](../templates/capture-manifest-template.yaml)
- [Item Condition Vocabulary](../reference/item-condition-vocabulary.md)
- [ML Technology Explained](../ml-technology-explained.md)
- [Service Interactions](../../auth-platform/docs/service-interactions.md)
