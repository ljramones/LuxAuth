# Pre-Phase 11 Readiness Checklist

**Status:** Tracking document. Not part of Phase 11 implementation scope.
**Companion to:** [DINOv2 Shadow Integration Plan](dinov2-shadow-integration-plan.md)

---

## Purpose

Phase 11 (DINOv2 shadow integration) does not have a hard deadline. The right time to start Phase 11A is **when the preconditions for Phase 11D shadow logging are visible**, not earlier. Building 11A through 11C speculatively — before real captures are flowing, before an expert reviewer is identified, before there's anywhere for divergence events to land — produces capability that sits unused, accumulates maintenance cost, and may need rework when real captures finally arrive and surface assumptions that turned out wrong.

This document is the gate. Use it to decide whether Phase 11A should start now or wait.

The three readiness sections below are necessary, not sufficient. Hitting all checkboxes does not automatically mean Phase 11A starts — it means Phase 11A is no longer blocked by missing preconditions. The actual go decision is a separate review against the [shadow integration plan §7 promotion criteria](dinov2-shadow-integration-plan.md#7-promotion-criteria--pre-declared) preview, plus current resource allocation across other concurrent threads.

---

## 1. Real Capture Flow

Phase 11D shadow logging is only useful if real captures are flowing through the system. This is the load-bearing precondition.

- [ ] At least one working microscope + phone/app setup is ready end-to-end
- [ ] `capture-intake-service` is deployed and accepting real sessions (not just synthetic / replay)
- [ ] 1–3 real luxury items available to start capturing (authentic is the priority — the shadow window does not require counterfeits to begin)
- [ ] A simple, repeatable capture protocol is defined (5–8 regions per item is sufficient to start)
- [ ] Sustainable capture cadence: target **10–15 real capture sessions per week** during the shadow window
- [ ] Capture operator identified and committed to the cadence

**Why this gate matters.** The shadow window is 4 weeks calendar time and 100+ sessions ([plan §7 criteria 1–2](dinov2-shadow-integration-plan.md#7-promotion-criteria--pre-declared)). At 10–15 sessions/week, that is achievable in 7–10 weeks. At 2–3 sessions/week, the window stretches to many months and the calendar-time criterion becomes the bottleneck rather than the data sufficiency criterion. Knowing the cadence ahead of time lets you size the shadow window honestly.

---

## 2. Expert Review Capacity

[Plan §7 criterion 3](dinov2-shadow-integration-plan.md#7-promotion-criteria--pre-declared) requires an expert-reviewed subset of at least 20 divergence cases. Without a reviewer, no promotion decision can be made — DINOv2 stays in shadow indefinitely.

- [ ] One person identified as the reviewer (self, friend, reseller, professional authenticator)
- [ ] Reviewer understands the commitment: ~5–20 cases per week during the shadow period
- [ ] Basic review process defined — Slack + shared spreadsheet is fine to start
- [ ] Time commitment confirmed: 2–4 hours per week
- [ ] Reviewer's domain expertise documented (years of experience, brands familiar with, any formal credentials) — needed for promotion-decision audit trail

**Why this gate matters.** The reviewer is the source of truth that resolves divergence between texture_baseline and DINOv2. If the reviewer is not lined up before shadow logging begins, divergence cases pile up unreviewed and the promotion decision criterion that depends on them (criterion 4: concordance with expert review) becomes unsatisfiable. Identifying the reviewer is cheap; getting them committed to the cadence is the harder part.

---

## 3. Minimal Divergence Review Capability

The reviewer needs somewhere to actually do the review. This does not require a polished workbench — a basic page that surfaces the relevant data is sufficient.

- [ ] Basic workbench / page exists that shows, per divergence event:
  - Original capture images for the session
  - Support-set images that drove the comparison
  - `texture_baseline` score and decision
  - All four DINOv2 strategies (nearest_neighbor, top_k_mean, prototype_centroid, prototype_medoid) with scores and per-strategy decisions
  - Top-1 margin per DINOv2 strategy
  - Abstention recommendation per strategy
- [ ] Ability to record expert verdict (Correct / Wrong / Inconclusive) plus free-text notes
- [ ] Reviewer's verdict persists in `model_agreement_events.reviewer_outcome` (or whatever the final schema names it — see [plan §10.2](dinov2-shadow-integration-plan.md#102-per-region-model-agreement-record))

**Why this gate matters.** A reviewer with a Slack channel full of unstructured screenshots is not actually reviewable evidence — the verdict needs to attach to a specific divergence event so promotion-time analysis can compute concordance rates. Even a minimal Streamlit page that reads `shadow_region_scores` and `model_agreement_events` and writes the verdict back is enough; this gate is about the data round-trip working, not about UX polish.

This page is part of Phase 11C scope in the integration plan. The readiness gate is satisfied when the page exists in skeleton form, not when it's complete.

---

## Starter Plan: First 20–30 Real Capture Sessions

When sections 1–3 above are unblocked enough to start capturing, this is the suggested ramp.

### Week 1 — Setup & first items

1. Pick **2–3 items** to begin with. Ideal mix: one authentic item with strong provenance, one item of uncertain status.
2. Define a minimum capture recipe. Suggested regions for a handbag:
   - Exterior leather / canvas (3–5 spots)
   - Stitching detail (2–3 areas)
   - Hardware engraving (2 areas)
   - Heat stamp / interior logo
   - Zipper / puller if present
3. Capture each item using the guided app / capture-workbench flow.
4. Upload every session through the real `capture-intake-service` path. Do not bypass the production ingestion code path.

### Weeks 2–4 — Build volume

- Aim for **3–5 sessions per week** during ramp; ramp toward the 10–15/week target.
- Vary capture conditions slightly between sessions — different lighting, small angle changes, different operators if available, different days. The point is to surface real intra-class variance early, not to artificially clean it up.
- Log basic metadata: item type, brand, known status (authentic / questionable / fake), date, microscope serial, operator if multiple.

### Pro tips

- Quality > quantity early. Five clean sessions teach more than fifteen rushed ones.
- Save raw + normalized images via the standard pipeline (the system already does this).
- Tag sessions clearly: `real_item_001_authentic`, `real_item_002_questionable`. Tags become invaluable when you're sorting through 100+ sessions at promotion-decision time.
- Capture the same item twice on different days at least once during the ramp. The within-item-across-days comparison is one of the cheapest probes of the variance assumptions in the [Phase 10 results NN-vs-prototype open question](../datasets/few-shot-prototype-results.md#1-executive-summary).

---

## Trigger Rule: When Phase 11A Begins

Phase 11A becomes appropriate to start when **all** of the following are true:

1. Section 1 (real capture flow) shows ≥ 80% of items checked, with a credible plan for the remaining 20%.
2. Section 2 (expert review capacity) is fully checked. The reviewer is named and committed.
3. Section 3 (divergence review capability) has a documented design even if the page isn't built yet — Phase 11C builds it, but the design must be locked before 11A starts so the schema work in 11A.1 reflects what the page actually needs.
4. No higher-priority concurrent thread is consuming the attention required for a multi-week implementation pass.

If any of (1)–(4) are not true, the answer is "wait." Returning to other threads and resuming when triggers fire is better resource allocation than building Phase 11A speculatively.

---

## Out of Scope for This Document

This document deliberately does **not** include:

- A detailed capture protocol template with exact region specifications and photo guidance — this should be created as a separate operations document when section 1 is being executed against, not speculatively now.
- A Google Sheet / Airtable template for expert review — this is a section 2 / section 3 operational artifact, created when the reviewer is identified.
- A Streamlit / workbench UI sketch for divergence review — this is Phase 11C scope, designed once the data model in [plan §10](dinov2-shadow-integration-plan.md#10-data-model-and-audit-needs) is locked.

Each of those is a worthwhile follow-on document. Each is a separate work item from this checklist, scoped when the corresponding readiness gate is being actively addressed.

---

## Status Log

Use this section as the team-shared tracking surface. Update with date + initials when status changes.

| Date | Section | Item | Status / Note |
|---|---|---|---|
| _populate as work progresses_ |  |  |  |

---

## Related Documents

- [DINOv2 Shadow Integration Plan](dinov2-shadow-integration-plan.md) — the Phase 11 implementation plan this readiness checklist gates
- [Few-Shot Prototype Matching Results](../datasets/few-shot-prototype-results.md) — the Phase 10 evidence that motivates Phase 11
- [auth-platform real testing readiness plan](../../auth-platform/docs/auth-platform-real-testing-readiness-plan.md) — broader real-testing readiness, of which Phase 11 readiness is a subset
- [Microscope Acceptance Runbook](../operations/microscope-acceptance-runbook.md) — capture infrastructure setup
- [Inspection Region Taxonomy](../reference/luxury-item-inspection-region-taxonomy.md) — canonical region codes used in capture protocol design
