# LuxAuth Multi-Sensor Authentication Approach

**Document version:** v2
**Date:** 2026-05-01
**Status:** Strategic option under evaluation. **Not** an adopted plan.
**Relationship to current work:** The microscopy-based pipeline (Phase 1–10 complete, Phase 11 shadow integration plan documented) remains the in-flight implementation. This document describes an alternative architectural direction motivated primarily by patent posture and operational profile concerns. The two approaches are not currently being run concurrently; this document exists so that if a v0.1 multi-sensor exploration is undertaken, the design context is captured rather than re-derived.
**v2 update summary:** modality set expanded from 6 to 12 with new three-tier organization; acoustic modality scope-restricted (was framed as universal in v1); calibration target made explicit and mandatory; new "Intended deployment context" section distinguishing reference-library construction from operational at-counter use; budget revised to ~$650-750 with staged-build option; modality applicability matrix introduced; modality weight estimation methodology added (within-class / between-class variance on authentic-only data). Full section-level diff in the [Revision history](#revision-history) at the bottom.

> **What this document is.** A strategic-options briefing describing a multi-modal capture approach at normal (non-microscopic) magnification. Written in advisor-to-project-owner voice. The first concrete step it proposes — a one-evening exploration with already-owned hardware — is small, reversible, and informative regardless of whether the full approach is later adopted.
>
> **What this document is not.** A migration plan from the current microscopy pipeline. A commitment to abandon Phase 11. A claim that the multi-sensor approach is empirically better than microscopy for luxury authentication — that's exactly what a v0.1 exploration would test.

---

## Executive summary

A multi-sensor authentication system captures multiple physically distinct measurement modalities of the same item region and combines them into a unified authentication decision. Each modality reads a different physical property of the material — fluorescence chemistry, infrared absorption, polarization response, surface topology, spectral reflectance, dielectric behavior, thermal diffusivity, acoustic damping, magnetic response — and a counterfeiter has to defeat all of them simultaneously rather than just one.

The architectural impact on the existing LuxAuth pipeline is small. The pipeline is already modality-agnostic: it ingests captures, produces embeddings, performs similarity search, scores per region, and aggregates region scores into a conservative authentication decision. The multi-sensor approach changes what gets captured and which embedding model is applied to each capture. Everything downstream carries forward.

Total hardware cost is targeted at under $750 for the full rig. Individual modalities can be tested for under $50 each.

This document is a research-phase design. It is not a production specification, and patent freedom-to-operate analysis remains required before any commercial deployment.

---

## Motivation

**Patent posture.** The dominant commercial system has filed patents whose independent claims center on microscopic image classification using machine learning, with "microscopic" doing significant claim-scope work. Designing around that limitation requires staying out of the microscopy regime as a structural matter, not tweaking implementation details. Multi-modal capture at normal magnification is structurally outside that claim space. This does not constitute legal clearance — multi-modal sensor fusion has its own active patent landscape, and a real FTO opinion against the specific implementation is required before commercialization.

**Operational profile.** Microscopy at authentication-relevant scales (roughly 10-micron features over a ~12mm × 10mm field of view) requires careful working distance, narrow depth of field, controlled focus, and a non-trivial operator skill curve. Multi-modal capture at normal magnification eliminates all of these.

**Defense in depth.** A microscopy-only system gives counterfeiters one signal to defeat. A counterfeiter who replicates surface texture at 10-micron resolution defeats the entire system. The multi-sensor thesis is that the combined feature space across physically orthogonal modalities is more discriminative than any single modality — including microscopy — because the modalities capture genuinely independent physical properties. The strength of the thesis depends on the modalities actually being orthogonal rather than correlated.

This thesis is empirically testable, and testing it is the first concrete step before any hardware build.

---

## Intended deployment context

This matters because it shapes everything downstream and was underspecified in v1.

The multi-sensor protocol described here is intended primarily for **reference library construction** — building a high-quality gold-set of authentic captures across modalities, against which subsequent authentication queries can be compared. A complete capture per item takes fifteen to thirty minutes once the rig is set up and the operator is trained, which is appropriate for reference library work but too slow for high-throughput operational deployment.

For operational at-counter authentication (resale platforms, point-of-sale verification), a faster simpler subset of modalities would be calibrated against the reference library. Operational capture might use only visible reference, UV fluorescence, and capacitive measurement — three modalities, ninety seconds total — with the per-modality scores compared against the rich multi-modal reference embeddings. The operational deployment is a separate v0.3+ question and not in scope for this document.

For high-value-item authentication services where each item commands enough revenue to justify the time, the full multi-sensor protocol can be deployed operationally.

---

## The capture modalities

The full modality set is organized into three tiers by physical orthogonality and discriminative independence.

### Core imaging modalities (the original five, plus raking-light and transmitted-light)

**Visible-light reference (flat illumination).** A standard photograph of the region under controlled diffuse white-light illumination, with a calibration target visible in frame. The baseline against which other modalities are interpreted, and itself a useful authentication signal — high-quality color, contrast, and macro-detail capture is informative for finishing quality, edge work, and surface uniformity.

**Visible-light raking illumination.** The same region under low-angle directional light from one side, with all other lighting off. Raking light reveals surface relief that's invisible under flat light: embossing depth, stitch hole quality, edge paint thickness, heat-stamp impressions, leather grain elevation. Free addition — same camera, different lighting geometry, captured in the same session as the flat reference.

**Ultraviolet fluorescence.** The same region illuminated with 365nm UV light (not 395nm — the longer-wavelength variant is much weaker and triggers fluorescence in fewer materials), with all visible-light sources off. Many luxury materials fluoresce in characteristic ways. Authentic leather treatments, dyes, adhesives, threads, and inks often have distinctive UV signatures that counterfeit substitutes lack. Conservation scientists and forensic examiners have used this technique for decades on paintings, documents, and textiles.

**Near-infrared reflectance.** The same region illuminated with 850nm IR, captured with a camera whose IR-cut filter has been removed. IR reveals features that absorb or reflect infrared differently from visible light — often shows underlying structures in coatings, dye penetration patterns, and material composition differences that are invisible in the visible spectrum.

**Polarized visible light.** Two captures of the region under visible light, one with a linear polarizer at 0° and one at 90° (cross-polarized). The difference between the two reveals specular versus diffuse reflection patterns, which distinguish material types — authentic leather scatters polarized light differently from synthetic leather, authentic gold-plated hardware behaves differently from cheap plated alternatives.

**Photogrammetric height map.** Five to ten visible-light photos of the region from slightly different angles, processed by structured-light or multi-view-stereo software into a 3D surface reconstruction. Authentication features are statistical properties of the surface: roughness, fractal dimension, peak distribution, autocorrelation length. Surface topography is a physically different feature from microscopic visual texture.

**Transmitted light (thin regions only).** For regions where the item allows backlighting — leather edges, fabric labels, paper documentation, hardware gaps — illumination from behind the item reveals internal structure. Counterfeit leather often has fiberboard or fabric backing visible under transmitted light that authentic full-grain leather doesn't. Region-dependent, only applies to thin or translucent regions, but cheap when applicable (small LED panel, ~$30).

### Non-optical modalities (the genuinely orthogonal additions)

These are the additions that the v2 review surfaced and that v1 underweighted. Each measures a physical property that no optical modality can read, and that's the property that makes the system actually defense-in-depth rather than redundant.

**Capacitive / dielectric response.** A small sensor (interdigitated electrodes on a PCB, or even a simple capacitor formed by a foil pad and an Arduino pin) measures how the material responds to a small electrical signal. Real leather is a hygroscopic protein-based material with residual moisture and complex fiber structure; PU and PVC substitutes have markedly different dielectric responses; coated and laminated materials respond differently again. The output is a single numerical value (or, with a more capable AD5933-based board, an impedance spectrum across frequencies). Hardware: $5-50 depending on approach. Contact-based, which limits some workflows but is fine for in-hand authentication. This is the strongest single non-optical addition because it's both extremely cheap and the most orthogonal modality to everything else.

**Thermal time-constant.** A brief controlled heat pulse (small resistive heating element) followed by measurement of the cooling curve via an IR thermometer (MLX90614, ~$25). Thermal diffusivity is a bulk material property determined by composition, density, and internal structure. A full-grain vegetable-tanned leather has different thermal behavior than a bonded leather or a coated synthetic. Solid metal hardware has dramatically different thermal time constants than plated zinc alloy. The output is a 1D waveform (temperature vs. time over 10-20 seconds), which fits the existing pipeline cleanly. Hardware: under $50. Non-contact, which is operationally cleaner than capacitive. The trick is controlling the heat pulse precisely enough for repeatable curves.

**Hyperspectral spot reflectance.** A Triad sensor (SparkFun, ~$70, AS7265x chipset) provides 18 narrow spectral bands from 410nm to 940nm. The trade-off versus the imaging modalities: spatial resolution is lost (single ~8mm spot vs. full image) but spectral resolution is gained (15-20nm bands vs. R/G/B broadband plus single UV band plus single IR band). The two are complementary. The imaging side has good spatial resolution but coarse spectral resolution; a hyperspectral spot adds fine spectral resolution at single points. For material identity questions ("is this the same dye chemistry?") spectral resolution matters more than spatial. For texture questions, spatial wins. Hardware: $70.

**Acoustic response (scope-restricted).** A controlled mechanical excitation with a piezo contact microphone recording the response waveform. The v1 framing presented this as universally applicable; that was wrong. Dropping a weighted striker on Hermès box calf or Delvaux smooth leather will leave a visible mark; on vintage or exotic skins it's a non-starter entirely. The honest scope: acoustic applies to *metal hardware regions* (buckles, locks, feet — soft-tipped low-force strike, no marking risk on metal) and *thick structured leather* where damage risk is acceptable. Smooth luxury leather, exotic skins, vintage items, and fabric items are out of scope. For applicable regions, acoustic measures internal density and assembly quality (cast vs. machined hardware, glued vs. stitched assembly) in ways no optical modality can. Hardware: piezo + striker rig, under $100.

**Magnetic response (hardware only).** A Hall effect sensor (~$5) measures the magnetic response of metal hardware. Real brass and gold are non-magnetic; ferrous-core plated alternatives are magnetic. This is a sharp, decisive signal in the cases where it applies — counterfeit hardware with a steel core under thin plating shows up immediately. Narrow application but extremely cheap and discriminative for the metal-hardware regions it applies to.

### Structured metadata (sanity-check tier)

Not modalities in the embedding-and-search sense, but cheap measurements that catch sloppy fakes and give expert reviewers useful sanity checks.

**Weight.** Digital scale (~$30). Counterfeiters generally get external dimensions right but often miss assembly weight by a few percent because internal structure (foam, stiffeners, hardware density) differs.

**Dimensions and proportions.** Digital caliper (~$20). Edge thickness, strap thickness, handle thickness, hardware dimensions, stitches per centimeter. Structured measurements that should be in the system even if they're not "AI."

**Capture context metadata.** Ambient temperature, humidity, ambient light level, capture session ID, device identifier, calibration target reference. These don't authenticate but explain capture variation.

### The calibration target (mandatory)

A small color/gray/UV-reactive/IR-reflective reference card visible in every capture. Cost: ~$20. This is mandatory, not optional, and was underemphasized in v1. Without it, the embedding model will learn camera and lighting variation rather than material variation. It belongs in every capture from day one.

---

## Hardware

The expanded budget breaks down approximately as follows.

Light tent or photo box ($50-80). Camera mount ($30). Calibration target ($20).

Illumination: 365nm UV LED flashlight (Convoy S2+ with Nichia LED, $60-100); 850nm IR illuminator ($20-30); linear polarizer film ($20); raking-light source — can be a small angled LED panel ($30); transmitted-light LED panel for thin regions ($30); ambient white LEDs in the tent or separate visible softbox. Subtotal: ~$220.

Camera. The phone path (zero cost) is workable for visible, UV, polarized, photogrammetry, but problematic for IR because of phone IR-cut filters. The converted-webcam path (Logitech with IR-cut filter removed, $30-60, or Raspberry Pi NoIR camera module, $35-50) is better for full multi-spectral work. Subtotal: ~$60.

Capacitive sensing: Arduino or ESP32 board (~$15) plus FDC1004 or AD5933 board ($25-30) plus copper PCB or foil electrodes (~$5). Subtotal: ~$50.

Thermal time-constant: MLX90614 IR thermometer ($25) plus resistive heating element with controllable pulse ($15) plus microcontroller (shared with capacitive setup). Subtotal: ~$40.

Hyperspectral spot: SparkFun Triad ($70) plus Qwiic cable to existing microcontroller ($5). Subtotal: ~$75.

Acoustic: piezo contact microphone ($20) plus controlled striker mechanism — solenoid-actuated for repeatability, soft-tipped, hardware-region only ($30) plus phone or laptop for recording (already owned). Subtotal: ~$50.

Magnetic: Hall effect sensor ($5).

Photogrammetry: smartphone app (Polycam, Scaniverse, RealityScan, or open-source alternative), free to ~$20.

Structured metadata: digital scale ($30) plus digital caliper ($20). Subtotal: ~$50.

**Total assembled hardware: ~$650-750.** Over the original $500 claim, but under the $1,000 ceiling, and the additions are individually meaningful. The build can also be staged — start with the original six modalities for ~$400, validate signal, then add capacitive ($50), thermal ($40), and hyperspectral ($75) one at a time as v0.1 progresses.

---

## Capture protocol

Per item, three regions are selected based on item type. For a handbag the typical regions are outer leather, stitching, and metal hardware; for a watch they would be case, dial, and bracelet; for apparel they would be primary fabric, stitching, and label. Region selection is part of dataset governance and is item-type-specific.

Per region, the capture sequence — with applicability flags noted — is:

1. **Visible reference, flat illumination.** Tent ambient lighting on, single capture with calibration target in frame. Universal.
2. **Visible reference, raking illumination.** Flat lights off, raking light on, single capture. Universal.
3. **UV fluorescence.** All visible lights off, 365nm UV illumination on, single capture. Universal.
4. **NIR reflectance.** Visible and UV off, 850nm illumination on, single capture using IR-capable camera. Universal.
5. **Polarized.** Visible lights on, polarizer at 0°, single capture; polarizer at 90°, single capture. Universal.
6. **Transmitted light.** LED panel behind region, single capture. *Thin or translucent regions only.*
7. **Photogrammetry.** Visible lights on, five to ten captures from different angles around the region. App post-processes into height map. *Skip for very flat or featureless regions.*
8. **Hyperspectral spot.** Triad sensor positioned at region center, one or more readings. Universal.
9. **Capacitive measurement.** Sensor pad pressed against region for ~5 seconds, impedance reading recorded. *Contact-permissible regions only.*
10. **Thermal time-constant.** Brief heat pulse applied, cooling curve recorded over 10-20 seconds via IR thermometer. *Heat-tolerant regions only — skip for delicate finishes that might react to mild warming.*
11. **Acoustic response.** Striker rig positioned, soft-tipped low-force strike, piezo records waveform. *Metal hardware and thick structured leather only.*
12. **Magnetic response.** Hall sensor placed against hardware, reading recorded. *Metal hardware only.*

Plus once per item (not per region):
- Weight measurement on scale.
- Key dimension measurements with caliper.
- Ambient context metadata logged.

Total artifacts per item, assuming three regions and all applicable modalities: roughly 25-30 image-like captures, 3-9 waveforms or 1D signals, 6-9 scalar readings, plus item-level metadata. End-to-end capture time fifteen to thirty minutes per item, comparable to the v1 estimate despite the additional modalities because the non-optical measurements are individually fast (seconds each).

The capture protocol is the new equivalent of the K parameter in the microscopy world: a fixed sequence executed identically per item, with the protocol design itself part of the system specification and subject to the same governance as everything else.

---

## What discriminates authentic from counterfeit, by modality

Worth being concrete about what signal each modality actually carries.

**Visible (flat).** Color accuracy, edge work, finishing quality, surface uniformity, hardware plating consistency. Mostly captures macro-level finishing differences that distinguish good fakes from authentic items at the level a careful human inspector would notice.

**Visible (raking).** Surface relief — embossing depth, stitch hole quality, edge paint build-up, heat-stamp impressions, grain elevation. Captures the 3D shape of the surface as revealed by shadow patterns under directional light.

**UV fluorescence.** Adhesive composition (authentic vs. counterfeit glues fluoresce differently), dye chemistry (especially for leather treatments and thread dyes), optical brighteners (frequently present in counterfeit fabrics, less common in luxury authentic), aged versus new material (authentic patina has characteristic UV signatures). For leather goods especially, UV fluorescence is unusually informative because the tanning, dyeing, and finishing chemistry of luxury leather is markedly different from cheaper alternatives at the molecular level even when visually identical.

**NIR reflectance.** Dye penetration depth, underlying material structure beneath surface coatings, plating uniformity on metal hardware, fiber composition in fabrics. IR is particularly useful for distinguishing authentic single-piece leather from layered or coated alternatives because the IR signal penetrates the surface coating in ways visible light doesn't.

**Polarized.** Material crystallinity, surface roughness statistics, plating versus solid metal, glossy versus matte finish authenticity. Polarization is informative for distinguishing real metal hardware from plated or cast imitations because the metallic crystal structure scatters polarized light differently from coatings.

**Photogrammetric height map.** Surface roughness statistics, grain depth distribution, pore structure, embossed-pattern depth and uniformity, edge roll quality on leather. Height maps capture the actual 3D structure of the surface rather than its 2D appearance, which is harder to fake convincingly.

**Transmitted light.** Internal fiber structure, lamination layers, inclusions, backing material composition. The single most decisive signal for distinguishing full-grain leather from bonded or coated alternatives, when the region allows it.

**Hyperspectral spot.** Spectral fingerprints across 18 narrow bands. Catches dye and coating chemistry differences that broadband UV/IR imaging misses. Particularly useful for materials where the visible appearance is convincingly faked but the underlying chemistry differs.

**Capacitive / dielectric.** Material composition at the electromagnetic level — moisture content, ionic composition, polymer chemistry, fiber structure. Real leather and synthetic substitutes have characteristically different dielectric responses regardless of visual appearance. This is the modality most orthogonal to optical signals.

**Thermal time-constant.** Bulk thermal diffusivity — composition, density, internal structure. Catches plated-plastic-masquerading-as-metal and bonded-leather-masquerading-as-full-grain in a way no surface-only measurement can.

**Acoustic.** Material density, internal structure, assembly quality (glued versus stitched, hollow versus solid), hardware authenticity (cast versus machined, plated versus solid metal). Global property of the region rather than local one. Scope-restricted to applicable regions.

**Magnetic.** Ferromagnetic content of metal hardware. Sharp, decisive signal for catching steel-cored plated hardware. Scope-restricted to metal regions.

The thesis is that defeating any one of these is achievable for a determined counterfeiter; defeating all of them simultaneously requires reproducing the authentic item at a fidelity that approaches simply manufacturing it correctly, which is the economic outcome you want.

---

## Architectural integration

The architectural change from v1 is small: more modalities, same architecture. The existing pipeline takes captures, produces embeddings, searches a reference database, scores per region, and aggregates into a decision. The multi-sensor approach changes only the capture and embedding stages.

**Capture and ingestion.** Each capture is stored with metadata identifying its modality, region, item, and capture session. The data model needs a `modality` field on captures, illumination metadata, camera/sensor metadata, exposure settings, and a calibration target reference. The change is purely additive — existing captures are implicitly `modality = visible_microscopy` or whatever the current data is later relabeled as.

**Embedding.** Each modality is encoded by a modality-appropriate embedding model. Image-like modalities (visible flat, visible raking, UV, IR, polarized, height map, transmitted) all flow through the existing image embedding infrastructure — DINOv2 or whatever the current best foundation model is. The hyperspectral spot reading is an 18-dimensional vector that can be embedded directly or projected through a small learned encoder. Capacitive and magnetic readings are scalars or short vectors that need either direct comparison or a small learned encoder. The thermal cooling curve and acoustic waveform are 1D signals that go through an audio-style encoder (Wav2Vec2, AST, or for a simpler start, spectrogram-as-image fed through the image encoder). Each modality produces its own embedding vector stored alongside the capture.

**Per-modality similarity search.** Within each modality, the embedding is compared against same-modality reference embeddings. Visible-vs-visible, UV-vs-UV, capacitive-vs-capacitive, and so on. This preserves the property that each modality is producing a discriminative signal in its own feature space, and doesn't require learning a cross-modal projection in the first version.

**Per-region score combination.** A region's authentication score combines its per-modality scores. Start with the simple version: weighted sum of modality scores with weights estimated from within-class variance (low within-class variance = high weight) versus between-class variance (high between-class variance = high weight) on authentic data. This can be done with only authentic captures — paired counterfeit data is not required to estimate sensible weights. More sophisticated combinations (learned modality weights per item type, small classifier trained on combined modality vectors, learned cross-modal embedding) are deferred to v0.2+ once data exists to validate them against.

**Region aggregation.** The existing region-aggregation logic carries forward unchanged.

**Modality applicability matrix.** Not every modality applies to every region. The system needs a per-region-type modality applicability specification: hardware regions get acoustic and magnetic; thin regions get transmitted light; smooth-finish regions skip thermal time-constant; etc. This is part of the protocol specification.

**Storage cost.** Roughly twelve modalities times three regions per item is up to thirty-six embedding records per item, though the realistic average is closer to twenty after applicability filtering. At 768-dimensional embeddings stored as float32, that's about 60-110KB per item rather than 9KB. Still negligible at LuxAuth scales.

**The architectural question that's deferred.** Whether to learn a single cross-modal embedding per region (more discriminative, requires paired multi-modal training data) versus keeping per-modality embeddings and combining at the decision layer (simpler, works immediately) is a v0.2 question. The middle path — late fusion with learned modality weights estimated from authentic-only data — is doable in v0.1.5 without requiring paired counterfeit data.

---

## Patent posture, briefly

Multi-spectral imaging at normal magnification, photogrammetry, capacitive measurement, thermal time-constant, hyperspectral spot reflectance, and acoustic authentication each sit in cleaner FTO space than microscopy. The dominant patent in the microscopy space hinges on the word "microscopic" as a load-bearing claim limitation, and operating at normal magnification is structurally outside that limitation rather than a tweak around it.

This is not a clean room. Multi-modal sensor fusion has its own active patent landscape (many filings 2020-2024 in industrial inspection, medical imaging, and authentication). Specific cross-modal attention mechanisms could become encumbered. Other patents exist in spectroscopy, photogrammetry, audio classification, and dielectric material analysis. A real FTO opinion against the specific implementation is required before any commercial deployment.

For research-phase work — which is the current state — the patent posture is good enough to proceed. The FTO opinion is the gate before commercialization, not before exploration.

---

## What the v0.1 exploration looks like

Concrete and small. Before any significant hardware purchase, a one-evening exercise to test the core thesis.

Pick three to five items already owned — bags, wallets, watches, anything with luxury-level construction. Mix authentic and obviously-fake or cheap-substitute items if possible. For each item, capture as many modalities as can be done with hardware already owned or assembled for under $50:

Phone-based captures: visible flat, visible raking (just point a flashlight at a low angle), UV fluorescence (borrow or buy a 365nm flashlight), polarized (cheap polarizer film or even polarized sunglasses over the lens), photogrammetry (free smartphone app), and acoustic recording — the **coin test** is the right v0.1 hack: drop a coin onto a hard surface near the item, record on phone.

Cheap electronics captures: capacitive measurement using an Arduino or ESP32 with a foil electrode and a 10MΩ resistor — measurably different between real leather and plastic, takes 10 minutes to set up. This is the modality to prioritize testing because it's both extremely cheap and theoretically the most orthogonal to everything else.

Optional if the hardware is on hand: any IR thermometer for crude thermal time-constant testing (warm with a hair dryer briefly, watch the cooling curve); a magnet for crude magnetic response on metal hardware.

Skip for v0.1 unless hardware arrives quickly: NIR imaging (needs IR-capable camera), hyperspectral spot (needs Triad sensor), proper thermal time-constant (needs controlled heat pulse), proper acoustic (needs piezo and striker rig), transmitted light (needs LED panel).

For each modality tested, just look at what was captured. Does the UV image reveal information that's invisible in the visible image? Does the capacitance reading reliably distinguish real leather from synthetic? Does the height map capture something distinctive about the surface? Does the acoustic waveform vary meaningfully between items? You're not running a classifier; you're forming a quick judgment about whether the modalities are actually producing discriminative signal on real items, or whether they're correlated enough that the multi-modal pitch isn't actually delivering.

The success criterion for v0.1: at least three modalities produce visibly different results between an authentic item and a substitute item, *and* the differences are not perfectly correlated across modalities. If capacitance, UV, and height map all separate real-from-fake but they all separate it the same way, that's one signal in three measurements rather than three independent signals. The thesis requires orthogonal information.

If the one-evening exercise shows clear independent signal across modalities, the multi-sensor approach is worth investing real engineering time in. If the modalities mostly tell the same story as the visible image, the approach needs rethinking before any hardware spend.

---

## Open questions

How to calibrate the capture rig across items, operators, and time. Multi-spectral and electrical measurements are sensitive to ambient conditions in ways single-modality imaging isn't. The calibration target visible in every capture is necessary but not sufficient — periodic capture-rig validation runs against known reference materials may also be needed.

How to handle the photogrammetry quality bar. Smartphone photogrammetry is rough, and "rough" might or might not be enough for authentication-grade height map analysis. The question is whether the roughness is *systematic* (same error direction across captures) or *noise*.

Whether the acoustic modality survives operational deployment at all. Even with scope-restriction to hardware regions, the marking risk on plated finishes is non-zero. A non-contact alternative (laser vibrometry) exists but breaks the cheap-and-easy budget. May end up as an optional modality used only on items where the customer has consented to the risk.

How capacitive measurement handles humidity variation. Leather is hygroscopic, which is what makes capacitive measurement informative — but it also means the same item will read differently on a humid day versus a dry day. Either the capture environment needs humidity control or the model needs to be robust to humidity variation.

How thermal time-constant handles delicate finishes. The heat pulse is mild, but mild is not zero. Some lacquered or treated finishes might react to even brief warming. Region applicability needs careful specification.

How modality weights should be estimated. The within-class-variance / between-class-variance approach works on authentic-only data but assumes that the modality variance measured on authentics is representative of the modality discrimination on counterfeits. This may not hold — some modalities may have low variance on authentics but also low variance on good fakes. Real validation requires paired data.

Whether to learn cross-modal embeddings or stay with per-modality embeddings combined at decision time. The simpler approach works immediately; the more sophisticated approach is potentially much more discriminative but requires paired multi-modal training data. Decide after measuring.

What the operator skill curve looks like for non-expert capture, and whether the protocol can be made simple enough for resale-platform-staff-level operators. Twelve modalities with applicability flags is not simple. The operational deployment may end up using a small high-throughput subset (visible + UV + capacitive, say) calibrated against the full reference library captured carefully in lab conditions.

These are the questions a real v0.1 build would need to answer. They're not blockers to starting the exploration; they're the things that would be found out by doing it.

---

## Relationship to the current LuxAuth implementation

The microscopy-based pipeline is the in-flight implementation. Phase 10 (few-shot prototype matching with DINOv2 backbone comparison) is complete; Phase 11 (DINOv2 shadow integration) is planned and gated on capture infrastructure prerequisites being visible. The current pipeline assumes a single modality (microscopic visible-light imagery).

If a v0.1 multi-sensor exploration is undertaken and produces clear independent signal across modalities, the integration path would be:

1. **Add a `modality` field to capture metadata.** Existing captures become `modality = visible_microscopy`. New captures carry their own modality tags.
2. **Per-modality embedding pipelines.** The existing image-embedding infrastructure (texture_baseline, learned_metric, DINOv2) handles the image-like modalities. Audio embedding for acoustic and thermal-curve embedding are new components.
3. **Per-modality similarity search.** Reuses pgvector and the existing region scoring, partitioned by modality.
4. **Score combination at the decision layer.** Initial implementation is a weighted sum (with weights from within-/between-class variance on authentic-only data); more sophisticated fusion is a v0.2 question.
5. **Modality applicability matrix per region type.** A new piece of protocol metadata that drives which modalities apply to which regions.
6. **Existing decision-service logic carries forward** without change. This is the architectural payoff of the modality-agnostic pipeline design.

If the v0.1 exploration does **not** show clear independent signal, this document remains as a record of a strategic option that was considered and rejected on evidence. Phase 11 microscopy-based shadow integration continues as planned.

The two paths are not currently being run concurrently because the resource-allocation argument that gated Phase 11A (capture infrastructure prerequisites visible, not just possible) applies equally here. A multi-sensor exploration would be undertaken when the conditions for it exist, not speculatively.

---

## Revision history

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

- [ConceptOfOperation.md](ConceptOfOperation.md) — current microscopy-based product and technical concept
- [docs/datasets/few-shot-prototype-results.md](docs/datasets/few-shot-prototype-results.md) — Phase 10 evidence on the microscopy approach
- [docs/roadmaps/dinov2-shadow-integration-plan.md](docs/roadmaps/dinov2-shadow-integration-plan.md) — Phase 11 plan for the microscopy approach
- [docs/roadmaps/dinov2-shadow-integration-readiness.md](docs/roadmaps/dinov2-shadow-integration-readiness.md) — Phase 11 readiness checklist
- [docs/roadmaps/capture-infrastructure-prerequisites.md](docs/roadmaps/capture-infrastructure-prerequisites.md) — capture dependency framing (currently scoped to microscopy; adaptable to multi-sensor if the approach is adopted)
- [docs/roadmaps/ml-improvement-roadmap.md](docs/roadmaps/ml-improvement-roadmap.md) — overall ML phase sequencing
- [docs/retrospectives/phase-10-retrospective.md](docs/retrospectives/phase-10-retrospective.md) — meta-lessons from the microscopy arc
