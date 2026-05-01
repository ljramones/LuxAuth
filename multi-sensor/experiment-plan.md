# LuxAuth multi-sensor experiment plan

**Document version:** v1
**Date:** 2026-05-01
**Companion to:** [MultiSensorAuthenticationApproach.md](../MultiSensorAuthenticationApproach.md) — the strategic-options briefing at the repo root that this plan operationalizes.

**Status:** Research-phase exploration plan. Not adopted, not Phase 12 of microscopy path. Activation requires explicit decision to begin.

**Goal:** Through a series of small, gated experiments, determine whether the multi-sensor authentication thesis is real, identify which modalities actually carry independent discriminative signal, and arrive at a concrete answer to "what sensors and what device shape would we want to design a product around" — without doing any product design yet.

**Out of scope:** Hardware product design, enclosure design, manufacturing planning, FTO opinions, any commitment to ship anything. Each phase is structured as a research investment that produces a go/no-go decision for the next phase.

---

## Phase E0: Capacitive proof-of-concept

**Question:** Does dielectric measurement reliably distinguish real leather from synthetic substitutes under realistic conditions?

**Why this first:** Capacitive is the cheapest modality to set up, the most theoretically orthogonal to optical, and the highest-priority addition from the v3 design review. It's also the one most likely to fail for boring reasons (humidity, contact pressure, surface contamination dominating signal). Failing here cheaply tells you whether the multi-sensor thesis has the orthogonal-signal foundation it needs. Succeeding tells you the most discriminative non-optical modality probably works.

**Hardware:** ESP32 or Pi 5 you already own, FDC1004 breakout (~$25) or AD5933 board (~$30), copper foil or PCB electrodes (~$5), a few jumper wires. Total: under $50.

**Materials to test:** Five to ten samples spanning the discrimination space. Real leather scraps from at least three different sources (different tanning, different finishes, different ages). Synthetic leather samples from craft store. PVC. Coated canvas. A few items with known multi-layer construction (bonded leather, laminated). Cost: under $30 from a craft or fabric shop.

**Protocol:** For each material, ten readings at controlled contact pressure (a fixed weight on the electrode), recorded with ambient temperature and humidity logged from a cheap sensor. Repeat at three different times across at least two days to capture humidity variation. No luxury items; this is pure science.

**Success criteria:**
- Real leather samples cluster distinguishably from synthetic samples (minimum: visible separation in a 1-D or 2-D plot of readings).
- Within-class variance (multiple readings of the same sample) is meaningfully smaller than between-class variance (different material types).
- The discrimination survives reasonable humidity variation (readings shift but classes don't overlap).
- Different real-leather sources are distinguishable from each other, or at least don't all collapse into one class — this matters because if "leather" is a single cluster regardless of quality, capacitive can't help with authentic-vs-counterfeit-leather discrimination.

**Failure modes to watch for:**
- Humidity dominates the signal entirely.
- Contact pressure variation produces more variance than material variation.
- Real and synthetic leather give similar readings under realistic conditions.
- All real leathers cluster identically with no within-real variation, which would mean the modality only catches obvious-substitution fakes, not luxury-grade fakes.

**Decision:**
- **Pass:** Proceed to E1. Capacitive is established as a viable modality.
- **Partial pass** (works but with major caveats): Proceed to E1 with capacitive deprioritized; the multi-sensor thesis loses its strongest non-optical leg but the imaging modalities may still carry the system.
- **Fail:** Stop the entire program, or restart with a fundamentally different modality stack. If the most theoretically orthogonal cheap modality doesn't work, the multi-sensor approach has a load-bearing problem.

**Time investment:** One weekend.

---

## Phase E1: Imaging modality survey

**Question:** Of the imaging modalities (visible flat, raking light, UV fluorescence, polarized 0/90, IR if available), which produce information not present in the standard visible image?

**Why this next:** Imaging modalities are cheap and safe to test, and they're the foundation the rest of the system depends on. The risk isn't that they don't produce signal — they will produce *some* signal — but that they're correlated with each other and with the visible reference such that the multi-modal pitch isn't actually delivering. Orthogonality, not signal presence, is the question.

**Hardware:** Pi 5 with camera module (use NoIR if possible to enable IR; otherwise skip IR for E1), 365nm UV flashlight (~$80), polarizer film (~$20), 850nm IR illuminator if using NoIR (~$25), a small light tent or controlled environment (~$60), the calibration targets discussed in v3 (~$80). Total additional: ~$265.

**Materials:** Same materials as E0 plus a few additional textures — different fabric weaves, treated and untreated leather, items with edge paint, items with embossed patterns. Still no luxury items; goal is modality characterization, not authentication.

**Protocol:** For each material, captures in each modality with the calibration target visible. Multiple captures per material to establish within-class variance. Compute pairwise correlations between modalities — pixel-wise on aligned captures, or feature-wise on extracted descriptors (DINOv2 embeddings work fine for this, since you have the pipeline already).

**Success criteria:**
- At least three modalities (counting visible flat as one) produce distinguishable information from each other on the same material — i.e., the modality-to-modality correlation is well below 1.0.
- UV fluorescence shows clear material-dependent variation that isn't predictable from visible alone.
- Polarization difference (the cross-polarized minus parallel-polarized comparison) reveals features not visible in either polarized capture alone.
- Raking light reveals surface relief that flat lighting misses.
- IR (if tested) reveals material composition differences invisible to visible.

**Failure modes to watch for:**
- All imaging modalities essentially encode the same visible information with different noise characteristics. This would mean the imaging side of the multi-modal pitch is hollow.
- UV and IR both fail to show meaningful variation on the test materials. This could mean the materials don't have UV/IR signatures (likely for synthetic samples) or that the capture conditions are wrong.
- Polarization doesn't add anything detectable beyond what flat visible captures.

**Decision:**
- **Pass with all modalities:** Proceed to E2 with the full imaging stack.
- **Pass with subset:** Proceed to E2 with whichever modalities passed; document the dropped ones as not-useful-for-this-domain.
- **Fail:** This is bad. It means the imaging side of multi-sensor doesn't add to ordinary photography. Combined with E0 outcome, decide whether non-optical modalities alone can carry the system or whether the program ends here.

**Time investment:** Two to three weekends.

---

## Phase E2: Hyperspectral spot

**Question:** Does narrow-band spectral measurement (the 18-band Triad) reveal material differences that broadband imaging (visible RGB plus single UV plus single IR band) misses?

**Why this next:** Hyperspectral is the easiest "additional modality" to integrate after imaging — it's I2C, it's $70, it's a single point measurement. The question isn't whether it produces a signal but whether the signal is *additional* to what imaging already captures. If broadband imaging already separates materials sufficiently, hyperspectral is redundant. If broadband imaging misses things hyperspectral catches, it's a real addition.

**Hardware:** SparkFun Triad ($70) plus connection to existing Pi setup. No other additions.

**Materials:** Same set as E1, possibly extended with materials chosen to be visually similar but chemically different (different dye batches of the same leather color, for instance, if you can source samples).

**Protocol:** Triad reading at the center of each region also captured in E1. Compare the discrimination achievable from imaging-only embeddings against imaging-plus-spectral embeddings. The right comparison is "does adding spectral data improve material clustering or classification, not just maintain it?"

**Success criteria:**
- Spectral readings show meaningful between-class variation that maps to material chemistry rather than just color.
- Combining imaging and spectral features improves discrimination on materials that are visually similar (the hard cases).
- Spectral readings are repeatable on the same sample (low within-class variance).

**Failure modes:**
- Spectral readings are dominated by overall brightness rather than spectral shape, making them equivalent to a luminance reading.
- Materials that look the same to broadband imaging also have similar spectral signatures, meaning hyperspectral is redundant for this domain.
- The spot size (~8mm) is too coarse to capture material-specific signatures because real items have varied micro-texture within the spot.

**Decision:**
- **Pass:** Hyperspectral joins the keeper modality stack. Proceed to E3.
- **Fail:** Drop hyperspectral from the modality stack. Proceed to E3 without it. This isn't a program-ending failure — it just means the spectral resolution argument doesn't hold for this domain.

**Time investment:** One weekend (plus shipping time on the sensor).

---

## Phase E3: Thermal time-constant (passive)

**Question:** Does passive thermal cooling-curve measurement distinguish materials by bulk thermal properties in a useful way?

**Why this next:** Thermal is the next non-optical modality after capacitive in the priority stack, but it has more risk (damage, repeatability, equilibration time). Testing it on scrap materials before considering luxury items is mandatory.

**Hardware:** MLX90614 IR thermometer (~$25), a small enclosed space for thermal equilibration (could be a closed cabinet, a small insulated box). Total: under $50.

**Materials:** Same set as E0/E1/E2. Plus a few hardware samples (brass, steel, plated zinc) since thermal is most discriminative for hardware.

**Protocol:** Equilibrate samples in a warm environment (room temperature plus 5-10°C, achievable with a closed cabinet on a warm day or a brief exposure to a heat source). Move to a cooler measurement environment. Record cooling curve over 10-20 seconds via the IR thermometer. Repeat to establish within-class variance. The active-heating version with a controlled pulse is deferred to a later phase if passive proves discriminative.

**Success criteria:**
- Cooling curves visibly differ between material classes.
- Curves are repeatable on the same sample (low within-class variance from session to session).
- Hardware samples show clearly distinguishable thermal behavior (brass vs. steel vs. plated zinc).
- The signal survives the equilibration uncertainty — different equilibration times produce different starting temperatures but similar curve *shapes*.

**Failure modes:**
- Equilibration variability dominates the cooling curve shape.
- All non-metallic materials look the same thermally because the differences are below the MLX90614's resolution.
- The 10-20 minute equilibration burden makes the modality impractical even at the experimentation stage.

**Decision:**
- **Pass:** Thermal joins the keeper stack. Note that operational deployment will need active heating, deferred to a later phase.
- **Partial pass** (works on hardware, weak on leather): Keep thermal as a hardware-only modality. Acceptable.
- **Fail:** Drop thermal. The modality requires too much equipment investment to be worth pursuing if passive doesn't show signal.

**Time investment:** One weekend.

---

## Phase E4: Magnetic and structured metadata

**Question:** Do hardware-region modalities (magnetic response) and item-level structured measurements (weight, dimensions) add useful diagnostic information?

**Why this next:** Both are very cheap and very fast to test. Their value is more circumscribed than the previous modalities — magnetic only applies to metal hardware, structured metadata is sanity-check tier — but they're nearly free to integrate.

**Hardware:** Hall effect sensor (~$5), digital scale (~$30), digital caliper (~$20). Total: ~$55.

**Materials:** Hardware samples (real and counterfeit if available, otherwise different known compositions). A few complete items where weight and dimensions can be measured.

**Protocol:** Hall sensor against each piece of hardware, recording reading. Weight and dimensional measurements on items, noting expected versus actual values where authentic specifications are known.

**Success criteria:**
- Magnetic readings differentiate ferromagnetic from non-ferromagnetic hardware reliably.
- The modality's diagnostic value is clear — i.e., knowing "this hardware is ferromagnetic" maps to actionable conclusions about likely material composition.
- Weight and dimension measurements catch obvious anomalies and are repeatable.

**Failure modes:**
- Magnetic readings vary too much based on probe positioning.
- The mapping from magnetic response to authenticity is too item-type-dependent to be useful without extensive per-item-type calibration.

**Decision:**
- **Pass:** Both join the stack. Both are very cheap and even modest signal value justifies inclusion.
- **Fail (magnetic):** Drop magnetic; structured metadata stays regardless because it's essentially free.

**Time investment:** One day.

---

## Phase E5: First real-item validation

**Question:** Do the modalities that passed E0-E4 actually discriminate authentic from counterfeit on real luxury items, or only on the proxy materials used in earlier phases?

**Why this is the gate:** Everything before E5 is on proxy materials. E5 is the first time the system encounters items where the discrimination question has stakes. This is also the phase where damage risk first matters, because even non-valuable luxury items (older bags, items past their resale value) deserve more care than craft-store leather samples.

**Hardware:** Whatever modality stack survived E0-E4, probably integrated into a single Pi-based capture session by this point. Add the calibration target setup and the basic enclosure (light tent or photo box). Total addition: minimal — the modalities are already built.

**Materials:** Three to five luxury items spanning the authenticity spectrum. Ideally:
- Two known-authentic items (your own, friends', verified through provenance).
- One known-counterfeit item (cheap obvious fake, purchasable for under $50).
- One ambiguous or aged authentic item (older bag with wear, to test that the system doesn't flag aging as inauthenticity).

For damage-risk modalities (acoustic if it makes it this far, thermal active heating if attempted, capacitive contact pressure), use only items where damage is acceptable.

**Protocol:** Full modality capture per region per item. Three regions per item. The capture device is the integrated Pi rig at this point, talking to the LocalStack S3 and DB on your Mac as designed in our earlier discussion. This is also the first time the full session-as-artifact architecture gets exercised end-to-end.

**Success criteria:**
- Authentic items cluster together in the combined embedding space.
- The known counterfeit is separable from authentics by at least one modality, ideally several.
- The aged authentic item clusters with authentics, not counterfeits — the system doesn't confuse wear with inauthenticity.
- At least three modalities contribute meaningfully to the separation (orthogonality holds on real items, not just proxy materials).
- Capture session takes under 30 minutes per item with the integrated rig.

**Failure modes:**
- Modalities that worked on proxy materials don't translate to luxury items because the materials are more refined and the differences subtler.
- Single-modality discrimination dominates and the multi-modal approach is no better than just visible imaging.
- Capture process is too fragile to execute reliably (operator error, calibration drift, equipment unreliability).

**Decision:**
- **Pass:** The multi-sensor thesis is empirically validated on real items. Proceed to E6.
- **Partial pass** (some modalities transfer, others don't): Drop the modalities that didn't transfer. Proceed to E6 with the reduced stack.
- **Fail:** The thesis doesn't survive contact with real items. End the program or restart with different assumptions about what modalities matter.

**Time investment:** One to two months including the integration work. This is by far the largest phase to date.

---

## Phase E6: Expanded real-item validation and reference library construction

**Question:** Does the validated modality stack scale to a meaningful reference library, and does it discriminate at fidelity that's useful for actual authentication?

**Why this phase:** E5 establishes that the system works on a small set of items. E6 establishes whether it works at the scale needed to be useful — dozens of items per category, multiple categories, multiple authentic variants per category. This is also where you start finding out whether the system can distinguish *good* fakes (superfakes) from authentic, not just obvious fakes.

**Hardware:** Same as E5. Possibly some refinement of the integrated rig based on E5 lessons learned, but no fundamentally new modalities.

**Materials:** This is the expensive phase. You need access to:
- 20-30 authentic items across two or three categories (handbags, watches, wallets — whatever is most accessible).
- 5-10 counterfeit items, ideally including some sophisticated fakes ("superfakes") not just obvious low-quality counterfeits.
- Materials access likely requires partnerships — resale platforms, authentication services, brand cooperation, or significant personal investment in items.

This is the phase where the program either gets serious or stops. Sourcing items is a real activity that requires planning and probably money or relationships. The decision to commit to E6 is the decision to commit to a research project that operates over months, not weekends.

**Protocol:** Full modality capture on all items. Build the reference library (authentic captures) properly. Test the counterfeit items against the reference library and measure discrimination performance. Compute per-modality contribution to discrimination, modality ablation analysis, and overall system performance metrics.

**Success criteria:**
- Authentic items form coherent clusters in the combined embedding space, organized by item type and likely by sub-category (specific bag model, specific leather treatment).
- Counterfeit items, including superfakes, are reliably separable from authentics — meaning the system catches not just bad fakes but good ones.
- Per-modality contribution analysis shows that the multi-modal approach genuinely outperforms any single modality including the best one.
- The reference library construction is operationally feasible at scale — capture time, data management, and quality control don't break down.

**Failure modes:**
- Superfakes pass all modalities. The thesis doesn't beat the state of the art in counterfeiting.
- One modality dominates and the others contribute marginally — multi-modal doesn't justify its complexity.
- Reference library construction is too operationally heavy to scale beyond a handful of items.

**Decision:**
- **Pass:** The multi-sensor system is validated as a viable authentication approach. Now product planning becomes a sensible question to ask.
- **Fail:** End the program. The science works at small scale but doesn't scale to actual authentication usefulness.

**Time investment:** Three to six months realistically, depending on item access.

---

## What "the end of this phased approach" produces

Assuming the program runs through E6 successfully, you arrive at:

**A validated modality stack.** A specific list of sensors that demonstrably contribute to authentication discrimination on real items. Probably a subset of the original twelve — likely: visible flat, visible raking, UV fluorescence, polarized, capacitive, hyperspectral spot, plus structured metadata (weight, dimensions). Some modalities (IR, thermal, acoustic, photogrammetry, magnetic) may have dropped out or scoped to specific item types only. The exact stack depends on what actually worked.

**Empirical performance characterization.** You know how well the system discriminates on the test items, including superfakes. You know which modalities matter most, which are redundant, and which only matter for specific item types. You have data to support claims about the system's capability rather than theoretical arguments.

**An operational protocol that's been executed dozens of times.** The capture sequence, the calibration regimen, the operator workflow — all of these have been refined through actual use rather than designed in the abstract. You know what's annoying about the current setup, what's fragile, what takes longer than it should, and what could be simplified.

**A reference library.** Real captures of real items, stored properly, indexed in your DB, retrievable for analysis. This is itself a significant asset that informs everything downstream.

**A clear sense of the device shape needed.** The integrated rig at E6 is still breadboard-and-photo-box, but you know what it has to do: drive these specific sensors in this specific sequence, with this specific calibration regime, taking captures of items in this specific geometry, in approximately this time budget. That's the input to product planning — not a product yet, but a clear specification of what a product would have to do.

**A clear sense of what doesn't work.** Equally important. The phases that failed or partially failed give you information about the boundaries of the system, which a product would have to acknowledge.

This is the point at which "what should the device look like" becomes a reasonable question, because you have answers to "what does the device need to do, what sensors does it actually need, what's the operational profile" — all of which are prerequisites for that question. Before E6 those answers are speculative; after E6 they're empirical.

---

## What this plan deliberately doesn't include

A few things that might seem like they should be in the plan but aren't, with brief explanations:

**Acoustic experiments.** Damage risk is too high for the experimentation phase even on hardware. Add an "E5b" or "E6b" if and when you have specific hardware samples where acoustic can be validated safely, or defer until after E6 when product planning would address it deliberately.

**Active thermal heating.** Same reason — passive equilibration in E3 establishes whether thermal is worth pursuing at all. Active heating is a refinement that comes after the basic question is answered.

**Operator-facing UI work.** The capture device should have a minimum-viable operator interface (probably a web page or a CLI), not a polished operator experience. Polishing the operator workflow happens after E6 when you know what the operator actually needs.

**Cross-modal embedding learning.** Per-modality embeddings combined at decision time is sufficient through E6. Cross-modal embedding learning is a v0.2 ML question that gets addressed only after the simpler approach is validated.

**Patent FTO opinion.** Research-phase work doesn't trigger this. Commercial deployment does. The plan stops at "ready to begin product planning," not at "ready to ship," so the FTO question lives in the product planning phase that follows this plan.

**Multi-device or multi-operator considerations.** One device, one operator (you), through E6. Multi-device questions arise only when the system needs to be deployed beyond the experimenter, which is post-E6.

---

## Cumulative budget and timeline

Hardware: roughly $400-500 across all phases for the integrated rig, plus calibration targets ($80-100), plus item acquisition for E5/E6 (highly variable, possibly $1000-5000 depending on how seriously you source items).

Time: E0-E4 are weekend-scale projects, total maybe 6-8 weekends. E5 is a one-to-two-month project. E6 is a three-to-six-month project. Total program timeline: 6-12 months of evening-and-weekend work, assuming each phase passes and you continue.

The plan is structured so that failing early costs little. E0 fails after one weekend and $50. E1 fails after another two weekends and $300. The expensive commitments only come after multiple successful phases have validated the underlying thesis.

That's the plan. Each phase has a clear question, a clear hardware investment, a clear success criterion, and a clear decision about whether to proceed. The end state is a validated sensor stack and operational protocol — exactly the input to product planning, but stopping short of product planning itself.
