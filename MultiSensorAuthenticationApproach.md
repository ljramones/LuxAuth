# LuxAuth Multi-Sensor Authentication Approach

**Document version:** v3
**Date:** 2026-05-01
**v3 update summary:** new top-level Status section reframes the document as a parallel research track with an explicit v0.1 decision gate; new "Operational definition" section gives a concrete engineering boundary for "normal magnification"; modalities reorganized by priority/risk tiers (High / Medium / Experimental); thermal switched to passive-cooling for v0.1 (eliminates active-pulse-control problem); acoustic and photogrammetry demoted to Experimental tier; magnetic reframed as diagnostic input rather than standalone authenticity signal; calibration targets clarified as separate per-modality references with ~$80-100 overhead; explicit safety preconditions and proceed/stop decision criteria added to v0.1 exploration; new "Roadmap placement" section replaces the prior "Relationship" section. Full section-level diff in the [Revision history](#revision-history) at the bottom.

---

## Status

**Parallel research track, not adopted.** This document describes a strategic alternative to the in-flight microscopy/DINOv2 path, not a planned next phase of it. Phase 11 (DINOv2 shadow integration on the microscopy path) remains the active workstream. This document only proceeds past v0.1 exploration if the one-evening signal check demonstrates that physically orthogonal modalities provide independent discriminative signal on real items. If v0.1 fails, this document remains a considered-and-rejected strategic option in the project record.

This is research-phase design work. It is not a production specification, and patent freedom-to-operate analysis remains required before any commercial deployment.

---

## Executive summary

A multi-sensor authentication system captures multiple physically distinct measurement modalities of the same item region and combines them into a unified authentication decision. Each modality reads a different physical property of the material — fluorescence chemistry, infrared absorption, polarization response, surface topology, spectral reflectance, dielectric behavior, thermal diffusivity, acoustic damping, magnetic content — and a counterfeiter has to defeat all of them simultaneously rather than just one.

The architectural impact on the existing LuxAuth pipeline is small. The pipeline is already modality-agnostic: it ingests captures, produces embeddings, performs similarity search, scores per region, and aggregates region scores into a conservative authentication decision. The multi-sensor approach changes what gets captured and which embedding model is applied to each capture. Everything downstream carries forward.

Total hardware cost is targeted at under $750 for the full rig. Individual modalities can be tested for under $50 each.

---

## Operational definition: "normal magnification"

Because the patent posture argument depends on operating outside the microscopy regime, the engineering needs a concrete boundary. For purposes of this document, "normal magnification" or "non-microscopic" means:

The capture system images a macroscopic region visible to the unaided eye. Field of view is measured in centimeters, not microscope-scale millimeters. The system does not rely on microscope optics, microscope-scale feature extraction, or any classification dependent on features at sub-100-micron resolution. A standard close-focus camera lens is permissible; macro photography in the 1:1 to 1:4 range is permissible; objective lenses, microscope tubes, or USB-microscope handheld devices are not.

This is an engineering boundary, not a legal conclusion. It exists to keep the system design honest. Whether this boundary is sufficient to avoid specific patent claims is a question for an FTO opinion against the actual implementation.

---

## Motivation

**Patent posture.** The dominant commercial system has filed patents whose independent claims center on microscopic image classification using machine learning, with "microscopic" doing significant claim-scope work. Designing around that limitation requires staying out of the microscopy regime as a structural matter, not tweaking implementation details. Multi-modal capture at normal magnification is potentially less directly exposed to microscopy-specific claims, but this is not legal clearance — multi-modal sensor fusion has its own active patent landscape, and a real FTO opinion against the specific implementation is required before commercialization. Research-phase exploration only.

**Operational profile.** Microscopy at authentication-relevant scales (roughly 10-micron features over a ~12mm × 10mm field of view) requires careful working distance, narrow depth of field, controlled focus, and a non-trivial operator skill curve. Multi-modal capture at normal magnification eliminates these.

**Defense in depth.** A microscopy-only system gives counterfeiters one signal to defeat. The multi-sensor thesis is that the combined feature space across physically orthogonal modalities is more discriminative than any single modality, because the modalities capture genuinely independent physical properties. The strength of the thesis depends on the modalities actually being orthogonal rather than correlated, which is what the v0.1 exploration is designed to test.

---

## Intended deployment context

The multi-sensor protocol described here is intended primarily for **reference library construction** — building a high-quality gold-set of authentic captures across modalities, against which subsequent authentication queries can be compared. A complete capture per item takes fifteen to thirty minutes once the rig is set up and the operator is trained, which is appropriate for reference library work but too slow for high-throughput operational deployment.

For operational at-counter authentication, a fast subset of modalities would be calibrated against the rich reference library. Operational capture might use only visible reference, UV fluorescence, and capacitive measurement — three modalities, ninety seconds total — with the per-modality scores compared against the full multi-modal reference embeddings. Operational deployment is a v0.3+ question and out of scope for this document.

For high-value-item authentication services where each item commands enough revenue to justify the time, the full multi-sensor protocol can be deployed operationally.

---

## Modality priority and risk assessment

Modalities are organized by v0.1 priority based on expected signal value, cost, repeatability risk, and damage risk to items.

**High priority** (cheap, safe, expected high signal — start here):

| Modality | Expected signal | Cost | Repeatability risk | Damage risk |
|---|---|---|---|---|
| Visible reference (flat) | High | $0-30 | Low | None |
| Visible raking light | Medium-high | $30 | Low-medium | None |
| UV fluorescence (365nm) | High | $60-100 | Medium | None to item; UV eye/skin precautions required |
| Polarized visible | Medium-high | $20 | Low | None |
| Capacitive / dielectric | High (theory) | $5-50 | Medium-high (humidity, contact) | None to robust items; possible contact pressure marking on delicate finishes |

**Medium priority** (moderate cost or applicability, useful additions after High tier validates):

| Modality | Expected signal | Cost | Repeatability risk | Damage risk |
|---|---|---|---|---|
| NIR reflectance (850nm) | Medium | $50-100 | Medium | None |
| Hyperspectral spot | Medium-high | $70 | Low-medium | None |
| Transmitted light | High (when applicable) | $30 | Low | None |
| Weight + dimensions | Low-medium | $50 | Low | None |
| Magnetic (hardware diagnostic) | Variable, item-dependent | $5 | Low | None |

**Experimental** (damage risk, repeatability problems, or unproven for luxury — defer or scope-restrict):

| Modality | Expected signal | Cost | Repeatability risk | Damage risk |
|---|---|---|---|---|
| Photogrammetric height map | Uncertain (smartphone quality) | $0-20 | Medium-high | None |
| Thermal time-constant | Medium (theory) | $25-50 | High (pulse control) | Possible on adhesives, waxes, patina, exotics, vintage |
| Acoustic response | Medium (hardware/structured leather only) | $50-100 | Medium | Yes — surface marking risk on smooth finishes; hardware-only and thick-structured-leather-only |

The High tier is what v0.1 should focus on. Medium tier is for v0.2 once orthogonality is demonstrated. Experimental tier requires non-damaging protocols validated on scrap materials before any application to real items.

---

## The capture modalities

### Core imaging modalities

**Visible-light reference (flat illumination).** Standard photograph under controlled diffuse white-light illumination, with a calibration target visible in frame. Baseline against which other modalities are interpreted. Captures color accuracy, edge work, finishing quality, surface uniformity, hardware plating consistency.

**Visible-light raking illumination.** Same region under low-angle directional light, all other lighting off. Reveals surface relief invisible under flat light: embossing depth, stitch hole quality, edge paint thickness, heat-stamp impressions, leather grain elevation. Free addition — same camera, different lighting geometry.

**Ultraviolet fluorescence (365nm).** Same region illuminated with 365nm UV light, all visible-light sources off. Use 365nm specifically; the longer-wavelength 395nm variant is much weaker and triggers fluorescence in fewer materials. Captures adhesive composition (authentic vs. counterfeit glues fluoresce differently), dye chemistry, optical brighteners (frequently present in counterfeit fabrics), aged versus new material.

**Near-infrared reflectance (850nm).** Same region illuminated with 850nm IR, captured with IR-capable camera (phone IR-cut filters block this; a converted webcam or Pi NoIR camera is needed). Captures dye penetration depth, underlying material structure beneath surface coatings, fiber composition.

**Polarized visible light.** Two captures of the region under visible light, polarizer at 0° and 90°. The cross-polarized difference reveals specular versus diffuse reflection patterns, distinguishing material crystallinity, surface roughness statistics, plating versus solid metal.

**Photogrammetric height map.** Five to ten visible-light photos from different angles, processed into a 3D surface reconstruction. Captures grain depth distribution, pore structure, embossed-pattern depth, edge roll quality. Smartphone photogrammetry is rough; v0.1 needs to verify whether the roughness is systematic (informative) or noise (not informative).

**Transmitted light (thin regions only).** LED panel behind item, illumination through translucent regions. Reveals internal fiber structure, lamination layers, backing material composition. Region-dependent — only applies to leather edges, fabric labels, paper documentation, hardware gaps.

### Non-optical modalities

**Capacitive / dielectric response.** Sensor measures how the material responds to a small electrical signal. Real leather (hygroscopic, protein-based, complex fiber structure) has characteristically different dielectric response than PU, PVC, or coated/laminated alternatives. Output is a single numerical value or, with a more capable AD5933-based board, an impedance spectrum across frequencies. Hardware: $5-50. Contact-based. The strongest single non-optical addition because it's both extremely cheap and the most orthogonal modality to optical signals.

Repeatability caveat: humidity, contact pressure, contact area, electrode geometry, and surface coatings all affect readings. The v0.1 test needs to assess whether discrimination between materials is robust to these variations or only works under tightly controlled conditions.

**Thermal time-constant (passive cooling for v0.1).** For v0.1, no active heating element. Equilibrate items in a controlled warm environment (e.g., a closed cabinet at room temperature plus a few degrees), then move to a cooler measurement environment and record the passive cooling curve via an IR thermometer (MLX90614, ~$25) over 10-20 seconds. This eliminates the pulse-control problem entirely. The 10-20 minute equilibration period is fine for reference library capture but not operational. Active heating becomes a v0.2 question if passive proves discriminative.

What it captures: bulk thermal diffusivity, which depends on composition, density, and internal structure. Catches plated-plastic-masquerading-as-metal and bonded-leather-masquerading-as-full-grain in ways no surface measurement can.

Damage caveat: even passive equilibration to mildly warm temperatures (a few degrees above ambient) can affect adhesives, waxes, patina on aged items, exotic skins, and vintage materials. Apply only to items where mild warming is verified safe.

**Hyperspectral spot reflectance.** SparkFun Triad sensor (~$70, AS7265x chipset) provides 18 narrow spectral bands from 410nm to 940nm. Single ~8mm spot rather than full image. Trade-off versus broadband imaging: lose spatial resolution, gain spectral resolution. Useful for material identity questions where the visible appearance is convincingly faked but the underlying chemistry differs.

**Acoustic response (scope-restricted).** Soft-tipped low-force striker with piezo contact microphone. Scope: metal hardware regions and thick structured leather only. Smooth luxury leather, exotic skins, vintage items, fabric items are out of scope — marking risk is unacceptable. For applicable regions, captures internal density, assembly quality (cast vs. machined hardware, glued vs. stitched assembly).

For any serious acoustic work beyond v0.1, the manual striker should be replaced with a solenoid-actuated soft-tipped striker for repeatable impulse delivery. Manual striking introduces too much variance for ML comparison across sessions.

**Magnetic response (hardware diagnostic).** Hall effect sensor (~$5) measures ferromagnetic content of metal hardware. This is a *diagnostic* (helps identify hardware composition) rather than a direct authenticity signal. Many authentic luxury items use stainless steel (ferromagnetic) or ferromagnetic alloys; many counterfeits use non-ferrous zinc alloys. The reading separates material classes, and how those classes map to authenticity is item-type-dependent and requires per-item-type calibration. Useful as an input to the embedding/scoring system but not as a standalone authenticity signal.

### Structured metadata

Not modalities in the embedding-and-search sense, but cheap measurements that catch sloppy fakes and give expert reviewers useful sanity checks.

**Weight.** Digital scale (~$30). Counterfeiters generally get external dimensions right but miss assembly weight by a few percent because internal structure differs.

**Dimensions and proportions.** Digital caliper (~$20). Edge thickness, strap thickness, handle thickness, hardware dimensions, stitches per centimeter.

**Capture context.** Ambient temperature, humidity, ambient light level, capture session ID, device identifier, calibration target reference. These don't authenticate but explain capture variation.

### Calibration targets (mandatory)

Multi-spectral and electrical work is sensitive to ambient conditions in ways single-modality imaging isn't. Without calibration references in every capture, the embedding model learns camera and lighting variation rather than material variation.

A single combined calibration card covering all modalities does not exist as an off-the-shelf product. The v0.1 approach uses separate per-modality references, captured as appropriate:

- Visible: standard 18% gray card or X-Rite ColorChecker (~$30)
- UV fluorescence: UV fluorescence reference standard from a forensic supply catalog or a hand-built card with known fluorescent pigments (~$30-50)
- IR reflectance: IR reflectance standard or aluminum-tape reference (~$20)
- Capacitive: a known reference material with characterized dielectric response, captured at the start of each session
- Thermal: a known reference material with characterized thermal mass

Total calibration overhead: ~$80-100. Mandatory, not optional.

---

## Hardware

The full rig budget breaks down approximately as:

Light tent or photo box ($50-80). Camera mount ($30). Calibration targets ($80-100, separate per modality as above).

Illumination: 365nm UV LED flashlight (Convoy S2+ with Nichia LED, $60-100); 850nm IR illuminator ($20-30); linear polarizer film ($20); raking-light source ($30); transmitted-light LED panel for thin regions ($30); ambient white LEDs in tent or separate visible softbox. Subtotal: ~$220.

Camera: phone (zero) or converted webcam ($30-60) or Raspberry Pi NoIR camera ($35-50). Subtotal: up to ~$60.

Capacitive: Arduino or ESP32 ($15) plus FDC1004 or AD5933 board ($25-30) plus PCB or foil electrodes ($5). Subtotal: ~$50.

Thermal (passive for v0.1): MLX90614 IR thermometer ($25). Active heating ($15) deferred to v0.2. Subtotal v0.1: ~$25.

Hyperspectral: SparkFun Triad ($70). Subtotal: ~$75.

Acoustic: piezo contact microphone ($20) plus solenoid-actuated soft-tipped striker ($40-60 in v0.2; manual striker $20-30 for crude v0.1). Subtotal v0.1: ~$50, v0.2: ~$80.

Magnetic: Hall sensor ($5).

Photogrammetry: smartphone app (free to ~$20).

Structured metadata: scale ($30) plus caliper ($20). Subtotal: ~$50.

**Full rig total v0.1: ~$700.** Adding v0.2 active heating and improved acoustic: ~$750. Under the $1,000 ceiling. The build can be staged — High tier modalities only for ~$400, validate, then add Medium tier as v0.1 progresses.

---

## Capture protocol

Per item, three regions selected based on item type. Per region, the capture sequence with applicability flags:

1. **Visible reference, flat illumination.** Universal.
2. **Visible reference, raking illumination.** Universal.
3. **UV fluorescence.** Universal. UV eye/skin precautions when source is on.
4. **NIR reflectance.** Universal. Requires IR-capable camera.
5. **Polarized visible.** Two captures (0° and 90°). Universal.
6. **Transmitted light.** Thin or translucent regions only.
7. **Photogrammetry.** Skip for very flat or featureless regions.
8. **Hyperspectral spot.** Universal.
9. **Capacitive measurement.** Contact-permissible regions only. Verify no marking risk before applying to any item with a delicate finish.
10. **Thermal cooling curve.** Heat-tolerant regions only. Skip for adhesive-bonded edges, waxed finishes, aged patina, exotic skins, vintage materials.
11. **Acoustic response.** Metal hardware and thick structured leather only. Soft-tipped low-force strike only. Verify on scrap material first.
12. **Magnetic response.** Metal hardware only.

Plus once per item: weight, key dimensions, ambient context metadata.

Total artifacts per item assuming three regions and applicable modalities: roughly 25-30 image-like captures, 3-9 waveforms or 1D signals, 6-9 scalar readings. End-to-end fifteen to thirty minutes.

---

## Architectural integration

The architectural change from the current pipeline is small: more modalities, same architecture.

**Capture and ingestion.** Each capture stored with metadata identifying modality, region, item, capture session, illumination, camera/sensor settings, calibration target reference. Data model needs additive `modality` field; existing captures are implicitly `modality = visible_microscopy` or whatever you decide to call current data.

**Embedding.** Each modality encoded by modality-appropriate model. Image-like modalities through DINOv2 or current best foundation model. Hyperspectral spot is an 18-d vector, embedded directly or through small learned encoder. Capacitive and magnetic readings are scalars or short vectors. Thermal cooling curve and acoustic waveform are 1D signals through audio-style encoder (Wav2Vec2, AST, or spectrogram-as-image fed through image encoder).

**Per-modality similarity search.** Visible-vs-visible, UV-vs-UV, capacitive-vs-capacitive. Preserves per-modality discriminative signal without requiring cross-modal projection in v0.1.

**Per-region score combination.** Start simple: weighted sum with weights estimated from within-class variance versus between-class variance on authentic data. This works without paired counterfeit data — you measure how tightly authentics cluster within each modality (low within-class variance = high weight) versus how much authentics differ from each other across items (high between-class variance = high weight). Sophisticated combinations (learned weights per item type, classifiers on combined vectors, learned cross-modal embeddings) deferred to v0.2+.

The within-/between-class approach assumes modality variance on authentics predicts discrimination on counterfeits, which may not hold — some modalities may have low variance on authentics but also low variance on good fakes. Real validation requires paired data, which v0.1 won't have.

**Region aggregation.** Existing logic carries forward unchanged.

**Modality applicability matrix.** Per-region-type specification of which modalities apply. Hardware regions get acoustic and magnetic; thin regions get transmitted light; smooth-finish regions skip thermal; etc.

**Storage cost.** Roughly twelve modalities × three regions × per-item, realistically ~20 records after applicability filtering. At 768-d float32 embeddings, ~60-110KB per item. Negligible at LuxAuth scales.

---

## V0.1 exploration

### Safety preconditions

Before any capture on any item, the following preconditions apply:

**Use non-valuable items only.** Scrap leather, cheap synthetic substitutes, old wallets, hardware samples, items where damage is acceptable. Do not test contact, heat, acoustic, or pressure-based modalities on high-value items in v0.1. Validate non-damaging protocols on scrap before considering application to valuable items.

**UV safety.** 365nm UV at the power levels used here is mostly harmless, but eye exposure should still be avoided and prolonged skin exposure is not advised. Use UV-blocking eyewear or work in an enclosed light tent. Do not point UV sources at others.

**Thermal caution.** Even mild warming can affect adhesives, waxes, surface treatments, patina on aged items, exotic skins, and vintage materials. Test thermal protocols on scrap before any real item.

**Acoustic caution.** The striker can mark surfaces. Hardware-only and thick-structured-leather-only, with soft tip, low force, validated on scrap first.

**Capacitive caution.** Contact pressure can mark delicate finishes. Test contact protocols on scrap before applying to real items.

### What to do

Pick three to five non-valuable items — scrap leather pieces, old wallets, cheap belts, hardware samples (buckles, snaps, zippers from craft stores). Mix obviously-real-leather items with obviously-synthetic substitutes. The goal is to test whether modalities produce *independently informative* signal on the kind of materials the system would eventually have to discriminate.

Capture as many High-tier modalities as you can with hardware you already own or can assemble for under $100:

Phone-based: visible flat, visible raking (just point a flashlight at low angle), UV fluorescence (borrow or buy a 365nm flashlight), polarized (cheap polarizer film over the lens), photogrammetry (free smartphone app for v0.1 — Experimental tier but free to test).

Cheap electronics: capacitive measurement using an Arduino or ESP32 with foil electrodes and a 10MΩ resistor. This is the modality to most prioritize testing because it's both extremely cheap and theoretically most orthogonal.

Skip for v0.1 unless hardware arrives quickly: NIR (needs IR-capable camera), hyperspectral spot (needs Triad), thermal (needs IR thermometer plus equilibration setup), acoustic (needs piezo + striker + scrap testing), transmitted light (needs LED panel).

For each modality you can test, just look at the captures. Form a quick judgment about whether the modality is producing discriminative signal independent of the visible image.

### Decision gate

**Proceed past v0.1 if:**
- At least three High-tier modalities produce repeatable signal across multiple captures of the same item.
- At least two modalities reveal information not visible in the ordinary flat-light visible image (i.e., they're orthogonal, not redundant).
- Capture can be repeated without item risk on the materials being tested.
- Operator workflow is plausible — the protocol can be executed by someone other than the system designer in reasonable time.

**Stop or defer if:**
- Modalities mostly duplicate the visible image (correlation high, orthogonality low).
- Calibration burden dominates capture time, suggesting the system can't be deployed by non-experts.
- Contact, thermal, or acoustic modalities can't be made non-damaging at acceptable cost.
- Repeatability is poor — same item captured twice produces meaningfully different readings.

If the decision is to stop, this document remains a considered-and-rejected option. The microscopy/DINOv2 path continues.

If the decision is to proceed, the next step is a more controlled v0.2 with a small dataset (3-5 items × 3 regions × multiple capture sessions × stability measurements), Medium-tier modality additions, and explicit modality-ablation analysis.

---

## Open questions

How to make capacitive measurement robust to humidity variation. Leather's hygroscopic nature is what makes capacitive measurement informative, but it also means readings vary with ambient humidity. Either the capture environment needs humidity control, or the model needs to be trained robust to humidity variation, or the modality needs explicit humidity-context normalization.

Whether smartphone photogrammetry produces height maps with discriminative information or just noise. The roughness needs to be systematic (informative) rather than random (noise). V0.1 should test this empirically.

Whether the within-/between-class variance weighting on authentic-only data actually produces useful modality weights. The assumption that authentic-modality-variance predicts counterfeit-discrimination may not hold for all modalities.

Whether the operational fast-subset (visible + UV + capacitive) produces enough discriminative power to justify the architectural complexity, or whether operational deployment ends up requiring more modalities than the time budget allows.

Whether the modality applicability matrix can be made simple enough for non-expert operators to apply correctly, or whether it requires trained authenticators to make per-region decisions.

Whether acoustic survives operational deployment at all. Even with scope-restriction to hardware regions and structured leather, the marking risk is non-zero. May end up as an optional modality applied only with customer consent.

These are questions a real v0.2+ build would need to answer. They're not blockers to running v0.1; they're things that determine whether v0.2 is worth attempting.

---

## Roadmap placement

This document sits in the project roadmap as:

**Parallel research track: Multi-Sensor Capture Exploration**
- Status: Dormant, pending v0.1 signal check decision
- Not Phase 12 of the microscopy path
- Microscopy/DINOv2 Phase 11 (shadow integration) remains the active workstream
- Activation gate: explicit decision to run v0.1 exploration, made independently of Phase 11 progress
- Continuation gate: v0.1 decision criteria above
- If v0.1 fails or is not run: this document remains a considered strategic option in the project record

The v0.1 exploration is small enough (one evening, ~$50-100 hardware) that running it doesn't significantly impact Phase 11 timeline. The decision of whether to run it now or defer is a personal-bandwidth question, not a resource question.

---

## Revision history

### v3 — 2026-05-01

Section-level diff against v2.

- **New top-level Status section.** Replaces the previous header status block + "What this document is / is not" preamble with a single substantive section. Frames the document explicitly as "Parallel research track, not adopted," names Phase 11 as the active workstream, and ties the document's continuation to the v0.1 decision gate.
- **New Operational definition section.** Defines "normal magnification" concretely: cm-scale field of view, no microscope optics, no classification dependent on sub-100-micron features, macro 1:1 to 1:4 permissible. Acknowledges this is an engineering boundary, not a legal conclusion. Was implicit in v1/v2.
- **New Modality priority and risk assessment section.** Adds High / Medium / Experimental priority tiers with explicit Repeatability risk and Damage risk columns per modality. This is a different framing than v2's "core imaging / non-optical / structured metadata" tiering (which v3 keeps as subsection headers under "The capture modalities") — v3's priority tier is about what to do first/next, while the physical-character tier is preserved for taxonomy.
- **Acoustic demoted to Experimental tier.** v2 had acoustic in non-optical-core with "scope-restricted" framing; v3 explicitly demotes to Experimental tier with damage-risk-Yes flag. Same scope restriction, different framing.
- **Photogrammetry demoted to Experimental tier.** v2 had it in core imaging with the photogrammetric-roughness caveat; v3 makes the demotion explicit because smartphone photogrammetry's signal value is uncertain and needs v0.1 validation before being treated as core.
- **Thermal switched to passive cooling for v0.1.** v2 used active heat pulse with the controlled-pulse-control caveat; v3 switches to passive equilibration (warm in closed cabinet, move to cooler measurement environment, record passive cooling curve). Eliminates the pulse-control problem entirely. Active heating deferred to v0.2.
- **Magnetic reframed as diagnostic, not standalone signal.** v2 framed magnetic as "sharp, decisive signal." v3 nuances: many authentic luxury items use stainless steel or ferromagnetic alloys, many counterfeits use non-ferrous zinc alloys. The signal separates material classes but the mapping to authenticity is item-type-dependent. Useful as scoring input, not standalone authenticity signal.
- **Calibration targets clarified as separate per-modality.** v2 mentioned a single calibration target. v3 acknowledges no single combined card exists off-the-shelf and specifies separate per-modality references (visible gray card / UV fluorescence reference / IR reflectance standard / capacitive reference material / thermal reference material) with ~$80-100 total overhead. Mandatory.
- **Acoustic v0.1 vs v0.2 split.** v2 implied solenoid-actuated as v0.1-ready. v3 splits crude manual striker ($20-30 for v0.1) from solenoid-actuated soft-tipped striker for ML-grade repeatability ($40-60 for v0.2), and explicitly notes manual striking introduces too much variance for cross-session ML.
- **Hardware budget restructured into v0.1 vs v0.2.** v2 had ~$650-750 total. v3 has ~$700 v0.1 / ~$750 v0.2 split. Calibration line item up from ~$20 to ~$80-100. Thermal v0.1 down from $40 to $25 (passive only). Acoustic v0.1 unchanged but v0.2 acknowledged at $80.
- **V0.1 exploration restructured with safety preconditions.** v2 framed v0.1 as "items you own"; v3 restricts to non-valuable items only with explicit safety preconditions section (UV safety, thermal caution, acoustic caution, capacitive caution, validate-on-scrap-first). Significant safety-framing improvement.
- **V0.1 decision gate formalized.** v2 had informal "if X then Y" prose for v0.1 success criteria. v3 has explicit Proceed / Stop-or-defer bulleted criteria. Stop conditions added: modalities duplicate visible image, calibration burden dominates capture time, damage cannot be ruled out, repeatability poor.
- **New Roadmap placement section.** Replaces v2's "Relationship to the current LuxAuth implementation" section with a more compact framing. Names this as a "Parallel research track" with activation/continuation gates, and explicitly states that v0.1 is small enough that running it doesn't significantly impact Phase 11 timeline — making the decision a personal-bandwidth question rather than a resource-allocation question.
- **Section folds.** "What discriminates authentic from counterfeit, by modality" (v2 standalone section) folded into the modality definitions themselves. "Patent posture, briefly" (v2 standalone section) folded into the Motivation section's patent-posture paragraph.

### v2 — 2026-05-01

Section-level diff against v1. Where this differs from v1 by replacement, the v1 text has been removed; where it differs by addition, both are present in v2.

- **Executive summary.** Modality list expanded to nine physical-property categories (was five). Hardware budget revised to "under $750 for the full rig" with "individual modalities testable for under $50 each" (was "under $500"). Added explicit research-phase / not-production-spec disclaimer paragraph.
- **Motivation.** Patent paragraph tightened to explicitly note that multi-modal sensor fusion has its own patent landscape and that this document does not constitute legal clearance. Defense-in-depth paragraph reframed: "physically orthogonal" modalities (was just "multiple"), with explicit caveat that thesis strength depends on actual orthogonality rather than correlated signals.
- **Intended deployment context.** New section. Distinguishes reference-library construction (slow, full protocol) from operational at-counter authentication (fast subset — visible + UV + capacitive, ~90 seconds). Operational deployment scoped as v0.3+ and out of scope for this document.
- **The capture modalities.** Reorganized into three tiers: core imaging, non-optical, structured metadata. Plus a mandatory calibration-target subsection.
  - **Core imaging additions in v2:** raking-light visible (free addition, same camera, different lighting); transmitted light (thin regions only).
  - **Non-optical additions in v2 (new tier):** capacitive / dielectric response (highest-priority addition — cheap and most orthogonal to optical); thermal time-constant (1D cooling-curve waveform); hyperspectral spot reflectance (Triad sensor, 18 narrow bands); magnetic response (hardware only).
  - **Acoustic scope corrected:** v1 framed acoustic as universal; v2 restricts to metal hardware and thick structured leather, with explicit acknowledgement that smooth luxury leather, exotic skins, vintage items, and fabric items are out of scope due to marking risk.
  - **Structured metadata tier added:** weight, dimensions, ambient context. Sanity-check tier rather than embedding-and-search.
  - **Calibration target made mandatory and explicit:** v1 was implicit; v2 calls it out as required equipment in every capture.
- **Hardware.** Budget revised to ~$650-750 (was ~$300-400). Staged-build option added: start with the v1 six modalities for ~$400, validate signal, add capacitive ($50), thermal ($40), hyperspectral ($75) one at a time. Per-modality subtotals broken out.
- **Capture protocol.** Sequence expanded to 12 modalities (was 6). Each step has an applicability flag (Universal / thin regions only / metal hardware only / etc.). Per-item metadata step added (weight + dimensions + ambient context). Total artifact count revised to 25-30 image-like + 3-9 waveforms + 6-9 scalars (was 21 images + 3 waveforms).
- **What discriminates authentic from counterfeit.** Section moved earlier in document (was after Architectural integration in v1). Per-modality entries added for each new modality: raking, transmitted, hyperspectral spot, capacitive, thermal, magnetic.
- **Architectural integration.** Embedding section extended to cover hyperspectral 18-d vector, scalar capacitive/magnetic readings, 1D thermal/acoustic waveforms (audio-style encoder or spectrogram-as-image). New "Modality applicability matrix" subsection. Storage cost recalculated (~60-110KB/item from 55KB). New paragraph on weighted-sum scoring methodology using within-/between-class variance estimated on authentic-only data — avoids requiring paired counterfeit data for v0.1.5.
- **Patent posture.** Tightened to explicitly note multi-modal sensor fusion's active patent landscape (2020-2024 filings in industrial inspection, medical imaging, authentication). v1 was looser on this.
- **What the v0.1 exploration looks like.** Capacitive ESP32/Arduino test promoted as the priority v0.1 modality (cheapest, most orthogonal, theoretically informative). "Coin test" introduced as the right v0.1 hack for crude acoustic. Hair-dryer test for crude thermal. Magnet for crude magnetic on hardware. New success criterion: at least three modalities show signal **and** signals are not perfectly correlated across modalities — orthogonality requirement, not just signal-presence requirement.
- **Open questions.** Expanded from five questions to eight. Additions: capacitive humidity variation; thermal delicate-finish reaction; modality-weight-estimation validity assumption; explicit operator skill curve question with the twelve-modality complexity acknowledged.
- **Relationship to the current LuxAuth implementation.** Updated integration path to reference modality applicability matrix and the within-/between-class-variance weighting approach. Otherwise unchanged — the framing that this is a strategic option, not a migration plan, is preserved.

### v1 — 2026-05-01

Initial document. Six-modality multi-sensor approach (visible, UV fluorescence, NIR reflectance, polarized visible, photogrammetric height map, acoustic). Hardware budget under $500. Architectural integration via existing modality-agnostic pipeline. Strategic-option framing established; not an adopted plan, microscopy pipeline remains in-flight.

---

## Related documents

- [multi-sensor/](multi-sensor/) — working folder for the multi-sensor research track. Holds the experiment plan and (eventually) capture artifacts and per-phase results.
- [multi-sensor/experiment-plan.md](multi-sensor/experiment-plan.md) — phased experiment plan (E0–E6) that operationalizes this strategic briefing, with explicit go/no-go gates per phase.
- [ConceptOfOperation.md](ConceptOfOperation.md) — current microscopy-based product and technical concept
- [docs/datasets/few-shot-prototype-results.md](docs/datasets/few-shot-prototype-results.md) — Phase 10 evidence on the microscopy approach
- [docs/roadmaps/dinov2-shadow-integration-plan.md](docs/roadmaps/dinov2-shadow-integration-plan.md) — Phase 11 plan for the microscopy approach
- [docs/roadmaps/dinov2-shadow-integration-readiness.md](docs/roadmaps/dinov2-shadow-integration-readiness.md) — Phase 11 readiness checklist
- [docs/roadmaps/capture-infrastructure-prerequisites.md](docs/roadmaps/capture-infrastructure-prerequisites.md) — capture dependency framing (currently scoped to microscopy; adaptable to multi-sensor if the approach is adopted)
- [docs/roadmaps/ml-improvement-roadmap.md](docs/roadmaps/ml-improvement-roadmap.md) — overall ML phase sequencing
- [docs/retrospectives/phase-10-retrospective.md](docs/retrospectives/phase-10-retrospective.md) — meta-lessons from the microscopy arc
