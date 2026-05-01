# Capture Infrastructure Prerequisites

**Status:** Dependency-framing document. Not a capture infrastructure plan.
**Companion to:** [DINOv2 Shadow Integration Plan](dinov2-shadow-integration-plan.md), [Pre-Phase 11 Readiness Checklist](dinov2-shadow-integration-readiness.md)

---

## Purpose

LuxAuth Phase 11D shadow logging requires real capture data to produce meaningful evidence. This document names the prerequisites without scoping their construction. It exists so future-me recognizes a triggering opportunity quickly when one appears, rather than re-deriving the dependency chain from scratch each time the project surfaces in attention.

The prerequisites below are independent and parallelizable. Phase 11A becomes the right next move when several of them are visible — see [Trigger conditions for resumption](#trigger-conditions-for-resumption) at the bottom. None of them require LuxAuth to plan or build them; they require recognition that an opportunity outside the project is, in fact, an opportunity for the project.

---

## Prerequisite 1: Capture source

What needs to exist:

- A source of physical luxury items to image. Options worth keeping in mind, in roughly increasing acquisition cost:
  - **Personal items in the household.** Cheapest. Limited brand and model coverage, no counterfeit examples, but lets capture pipeline get exercised end-to-end without external dependencies.
  - **Items borrowed for short-term capture sessions.** Requires a relationship that permits temporary custody. Friends, family, professional acquaintances. Low marginal cost per item, capped volume.
  - **Items from a partnered reseller, consignment shop, or authentication service.** Higher volume potential, broader brand coverage. Requires a partnership conversation and likely a data-handling agreement. Counterfeit examples become realistic at this tier (resellers and authentication services routinely encounter them).
  - **Items purchased explicitly for capture and resold after.** Highest cost. Useful for filling specific gaps in coverage (e.g., a brand or model the partner pipeline doesn't reach). Worth considering when a specific authentication question would pay off.

- Each source has different acquisition cost, volume ceiling, brand/model coverage, and counterfeit availability. The right answer is probably a mix that evolves over time, not a single source.

**Recognition signals:** any conversation, opportunity, or relationship that could plausibly produce a flow of physical items. A casual comment from a reseller acquaintance about authentication pain. A consignment shop with idle inventory. A family member acquiring a high-value item. None of these are "capture pipeline" conversations on their face — recognizing them as one is the point of this section.

---

## Prerequisite 2: Capture hardware

What needs to exist:

- A microscope device meeting the optical and capture-protocol requirements established in earlier project conversations: roughly 260× optical magnification range (handheld) or comparable (benchtop), controlled illumination geometry (built-in LED ring or directional source), repeatable working distance.
- Either a vendor handheld unit (Dino-Lite Edge series or similar — well-documented USB/WiFi options exist) or a benchtop scope with a C-mount WiFi camera. Each has different tradeoffs on portability, image stability, and capture cadence.
- Calibration profile recorded and registered in the system once hardware is selected.

**Recognition signals:** budget approval for the device. Vendor evaluation invitation (some manufacturers loan units for review). Hardware availability that would let capture start within weeks rather than months. Used-equipment opportunities in adjacent professional contexts.

---

## Prerequisite 3: Capture operator

What needs to exist:

- Someone able to follow the capture protocol consistently. May be the project owner, a contracted operator, an authentication-trained staff member if a partner relationship covers it, or a rotating set of operators if multi-operator variance is desirable for shadow data realism.
- Time commitment realistic for sustained capture work, not just one-off sessions. The Phase 11D shadow window targets 10–15 sessions per week sustained over 4+ weeks (per the readiness checklist).
- Consistent technique matters more than operator credentials at this stage. The protocol is repeatable; what's needed is someone who'll actually execute it the same way each time.

**Recognition signals:** an operator with both the manual skill and the available time, OR a process design that lets the project owner do captures alongside other work without burning out. The latter is a real design constraint — sustained capture work at 10–15 sessions/week alongside other concurrent threads will fail if the cognitive load isn't bounded. If the project owner is the operator, capture sessions need to fit into a recurring time block, not be opportunistic.

---

## Prerequisite 4: Expert review capacity

What needs to exist:

- Authentication expertise available to adjudicate divergence events between texture_baseline and DINOv2.
- A queue mechanism (even a simple one — a shared spreadsheet, a Slack channel with pinned messages, an Airtable view) for surfacing divergence cases.
- Time committed sufficient to clear the queue at the rate divergence events accumulate. The Phase 11 plan §7 criterion 3 requires at least 20 reviewed divergences before promotion is on the table.

**Recognition signals:** relationship with a brand-trained authenticator, partnership with an authentication service that adjudicates as part of a broader collaboration, or a project-owner self-review pathway with appropriately documented caveats about credential limitations. The third option is the lowest-friction starting point and is acceptable for the shadow window provided the limitation is recorded — promotion-time review of the criteria can decide whether self-review evidence is sufficient or whether external expert validation is required before any production decision.

---

## Prerequisite 5: Divergence-event review UX

What needs to exist:

- Workbench enhancement (Phase 11C scope) that displays both models' scores, all four DINOv2 strategies (nearest_neighbor, top_k_mean, prototype_centroid, prototype_medoid), captured images, support set, and abstention recommendations side-by-side.
- Reviewer verdict capture back into the data layer (`model_agreement_events.reviewer_outcome` or equivalent — see Phase 11 plan §10.2).

This prerequisite is **internal** — building it is Phase 11C work. It is named here so the dependency chain is complete. Phase 11D shadow logging without Phase 11C review UX produces data that has nowhere to be reviewed, which collapses the value of the shadow window. Phases 11C and 11D should be sequenced together at minimum, ideally with 11C landing slightly ahead so the first divergence events have somewhere to go.

---

## Trigger conditions for resumption

Phase 11A becomes the right next move when **at least Prerequisites 1, 2, and 3 are visible** — meaning a capture pipeline is realistic within a few weeks, not hypothetically possible someday. Prerequisites 4 and 5 can be built or arranged during Phase 11A through 11C; they don't need to be solved before resumption, just acknowledged.

**Phase 11A is NOT triggered by:**

- Generic interest in resuming the project.
- Wanting to make progress without an external dependency in hand.
- Capture infrastructure being theoretically possible.
- A fresh idea about Phase 11A scope that feels exciting in the moment.

These are anti-triggers worth naming explicitly because the temptation will be real. The conservative pause at the end of Phase 10 was deliberately taken because building Phase 11A speculatively would produce capability that sits unused and accumulates maintenance cost. That logic doesn't change just because attention returns to the project.

---

## Adjacent watch list

Other developments that might surface a prerequisite indirectly. Brief, not exhaustive — these are example shapes, not a full enumeration:

- Acquiring high-value items personally where capture before reselling is feasible (touches Prerequisites 1 and 3).
- Authentication services becoming open to API or capture partnerships (touches Prerequisites 1 and 4).
- Vendor microscope evaluations becoming available through professional context (touches Prerequisite 2).
- A reseller, consignment shop, or auction house surfacing in conversation in a way that suggests interest in a low-cost authentication assist (touches Prerequisites 1 and 4).
- A friend or family acquaintance with a relevant collection willing to permit capture sessions (touches Prerequisites 1 and 3).
- Personal travel to a region with concentrated luxury reseller density where short-duration borrowed capture might be feasible (touches Prerequisite 1).

---

## Maintenance

Re-read this document when:

- Three months pass without progress on LuxAuth (so the dependency map stays loaded when the project resurfaces in attention).
- An opportunity arises that touches any prerequisite (so the recognition is automatic).
- Phase 11A is being considered as the next move (to verify the trigger conditions are actually met, not just felt).

If significant time passes and the prerequisites haven't moved, that itself is information — it suggests the project's binding constraint is upstream of LuxAuth's planning, and effort is better spent on the upstream constraint than on more LuxAuth planning.

---

## Related documents

- [DINOv2 Shadow Integration Plan](dinov2-shadow-integration-plan.md) — what Phase 11A through 11F build once these prerequisites are visible
- [Pre-Phase 11 Readiness Checklist](dinov2-shadow-integration-readiness.md) — the gating checklist that operationalizes the trigger conditions named above
- [Microscope Acceptance Runbook](../operations/microscope-acceptance-runbook.md) — the procedural detail for Prerequisite 2 once hardware exists
- [Dataset Acquisition Strategy](dataset-acquisition-strategy.md) — broader context on data sourcing including the Prerequisite 1 question
