# LuxAuth Multi-Sensor Authentication Approach

**Date:** 2026-05-01
**Status:** Strategic option under evaluation. **Not** an adopted plan.
**Relationship to current work:** The microscopy-based pipeline (Phase 1–10 complete, Phase 11 shadow integration plan documented) remains the in-flight implementation. This document describes an alternative architectural direction motivated primarily by patent posture and operational profile concerns. The two approaches are not currently being run concurrently; this document exists so that if a v0.1 multi-sensor exploration is undertaken, the design context is captured rather than re-derived.

> **What this document is.** A strategic-options briefing describing a multi-modal capture approach at normal (non-microscopic) magnification. Written in advisor-to-project-owner voice. The first concrete step it proposes — a one-evening exploration with already-owned hardware — is small, reversible, and informative regardless of whether the full approach is later adopted.
>
> **What this document is not.** A migration plan from the current microscopy pipeline. A commitment to abandon Phase 11. A claim that the multi-sensor approach is empirically better than microscopy for luxury authentication — that's exactly what a v0.1 exploration would test.

---

## Executive summary

A multi-sensor authentication system captures multiple physically distinct measurement modalities of the same item region and combines them into a unified authentication decision. Each modality reads a different physical property of the material — fluorescence chemistry, infrared absorption, polarization response, surface topology, acoustic behavior — and a counterfeiter has to defeat all of them simultaneously rather than just one.

The architectural impact on the existing LuxAuth pipeline is small. The pipeline is already modality-agnostic: it ingests captures, produces embeddings, performs similarity search, scores per region, and aggregates region scores into a conservative authentication decision. The multi-sensor approach changes what gets captured and which embedding model is applied to each capture. Everything downstream carries forward.

Total hardware cost is targeted at under $500. All components are off-the-shelf.

---

## Motivation

**Patent posture.** The dominant commercial system has filed patents whose independent claims center on microscopic image classification using machine learning, with "microscopic" doing significant claim-scope work. Designing around that limitation requires staying out of the microscopy regime as a structural matter, not tweaking implementation details. Multi-modal capture at normal magnification is structurally outside that claim space.

**Operational profile.** Microscopy at authentication-relevant scales (roughly 10-micron features over a ~12mm × 10mm field of view) requires careful working distance, narrow depth of field, controlled focus, and a non-trivial operator skill curve. Multi-modal capture at normal magnification eliminates all of these.

**Defense in depth.** A microscopy-only system gives counterfeiters one signal to defeat. A counterfeiter who replicates surface texture at 10-micron resolution defeats the entire system. The multi-sensor thesis is that the combined feature space across modalities is more discriminative than any single modality — including microscopy — because the modalities capture genuinely independent physical properties.

This thesis is empirically testable, and testing it is the first concrete step before any hardware build.

---

## The capture modalities

Six modalities per region, five of them image-like and one a waveform.

**Visible-light reference.** A standard photograph of the region under controlled white-light illumination. The baseline against which other modalities are interpreted, and itself a useful authentication signal — high-quality color, contrast, and macro-detail capture is informative for finishing quality, edge work, and surface uniformity.

**Ultraviolet fluorescence.** The same region illuminated with 365nm UV light (not 395nm — the longer-wavelength variant is much weaker and triggers fluorescence in fewer materials), with all visible-light sources off. Many luxury materials fluoresce in characteristic ways. Authentic leather treatments, dyes, adhesives, threads, and inks often have distinctive UV signatures that counterfeit substitutes lack. Conservation scientists and forensic examiners have used this technique for decades on paintings, documents, and textiles. The capture is a regular image taken under UV illumination; the existing image pipeline ingests it identically to a microscopy capture.

**Near-infrared reflectance.** The same region illuminated with 850nm IR, captured with a camera whose IR-cut filter has been removed. IR reveals features that absorb or reflect infrared differently from visible light — often shows underlying structures in coatings, dye penetration patterns, and material composition differences that are invisible in the visible spectrum. Counterfeit dyes and leather treatments frequently differ from authentic ones at IR wavelengths even when they're visually identical.

**Polarized visible light.** Two captures of the region under visible light, one with a linear polarizer at 0° and one at 90° (cross-polarized). The difference between the two reveals specular versus diffuse reflection patterns, which distinguish material types — authentic leather scatters polarized light differently from synthetic leather, authentic gold-plated hardware behaves differently from cheap plated alternatives, glossy versus matte finishes have characteristic polarization signatures. This is a well-established technique in materials science and dermatology.

**Photogrammetric height map.** Five to ten visible-light photos of the region from slightly different angles, processed by structured-light or multi-view-stereo software into a 3D surface reconstruction. The output is a height map rather than an image — for each pixel, a height value. Authentic leather has characteristic 3D surface topography (grain depth, pore structure, edge roll) that's distinct from synthetic leather and from imitations. Authentication features are statistical properties of the surface: roughness, fractal dimension, peak distribution, autocorrelation length. Surface topography is a physically different feature from microscopic visual texture and sits in different patent space entirely.

**Acoustic response.** A controlled mechanical excitation (a small weighted striker dropped from a fixed height onto a fixed point near the region) with a piezo contact microphone recording the response waveform. Authentic leather vibrates differently from synthetic leather; authentic metal hardware rings differently from cast or plated alternatives; authentic stitched assemblies damp vibration differently from glued ones. This modality is the least developed of the six for luxury authentication specifically — there's no commercial precedent — which is both the opportunity and the risk.

---

## Hardware

The total budget under $500 breaks down approximately as follows.

A small light tent or photo box ($50-80) provides controlled ambient conditions. Multi-spectral work integrates signal across modalities, so small ambient variations confound results in a way they don't for single-modality capture. The tent doesn't have to be elaborate — a basic photographer's softbox tent is sufficient.

Inside the tent: a fixed camera mount (phone tripod or webcam stand, $30) and a positioning template for repeatable placement of the item.

Illumination: a 365nm UV LED flashlight ($60-100; the Convoy S2+ with a Nichia 365nm LED is the hobbyist standard and produces strong, narrow-band UV); an 850nm IR illuminator ($20-30); a linear polarizer film ($20) cut to camera lens size and to flashlight diffuser size; the regular ambient white LEDs of the tent or a separate small softbox for visible-light capture. Total under $200 for illumination.

Camera. Two paths with different cost profiles:

The phone-based path uses a phone already owned with a manual-mode camera app. Cost: zero. Limitation: most phone cameras have IR-cut filters that block the 850nm illumination, so the IR mode either doesn't work or works weakly. Workable for visible, UV, polarized, and photogrammetry; problematic for IR.

The converted-webcam path uses a basic webcam with the IR-cut filter physically removed (some Logitech models, $30-60) or a Raspberry Pi camera module without the IR filter ($25-50). Better for full multi-spectral work because you can capture across visible, UV, and IR with a single camera. Total under $100.

Acoustic capture: a piezo contact microphone or piezo disk ($15-30), a controlled striker mechanism (a small pendulum dropping a weighted striker from a fixed height — can be built from hobby parts for under $30), and the existing phone or laptop as the recorder. Total under $100 including the striker rig.

Photogrammetry: a free or under-$20 smartphone app (Polycam, Scaniverse, RealityScan, or open-source alternatives) using structured light or multi-view stereo. No additional hardware beyond what is already owned.

Total assembled hardware: roughly $300-400 if going with the converted-webcam route, less if a phone can be stretched harder. Comfortably under the $1,000 ceiling and substantially less than the microscopy path was approaching.

---

## Capture protocol

Per item, three regions are selected based on item type. For a handbag the typical regions are outer leather, stitching, and metal hardware; for a watch they would be case, dial, and bracelet; for apparel they would be primary fabric, stitching, and label. Region selection is part of dataset governance and is item-type-specific.

Per region, the capture sequence is:

1. **Visible reference.** Tent ambient lighting, camera fixed, single capture. Establishes the baseline.
2. **UV fluorescence.** Tent visible lights off, 365nm UV illumination on, single capture. Camera exposure set manually for the lower light level.
3. **IR reflectance.** Visible and UV off, 850nm illumination on, single capture using the IR-capable camera.
4. **Polarized.** Visible lights on, polarizer at 0°, single capture; polarizer at 90°, single capture. Two images per region for this modality.
5. **Photogrammetry.** Visible lights on, five to ten captures from slightly different angles around the region. The app post-processes these into a height map.
6. **Acoustic.** Striker rig positioned near the region, weighted striker drops, piezo records the response waveform. One waveform per region.

Total captures per region: six modes producing seven image artifacts plus one waveform. At three regions per item, that's twenty-one images plus three waveforms per item. End-to-end capture time per item, once the rig is set up and the operator is trained, is roughly fifteen to thirty minutes — comparable to or faster than microscopy because there's no working-distance dance and no per-capture focus management.

The capture protocol becomes the new equivalent of the K parameter in the microscopy world: a fixed sequence executed identically per item, with the protocol design itself part of the system specification and subject to the same governance as everything else.

---

## Architectural integration

This is where the design effort that went into LuxAuth pays off. The existing pipeline takes captures, produces embeddings, searches a reference database, scores per region, and aggregates into a decision. The multi-sensor approach changes only the capture and embedding stages.

**Capture and ingestion.** Each capture is stored with metadata identifying its modality, region, item, and capture session. The data model needs a `modality` field on captures that didn't previously need one, but the change is purely additive — existing captures are implicitly `modality = visible_microscopy` or whatever the current data is later relabeled as.

**Embedding.** Each modality is encoded by a modality-appropriate embedding model. The five image-like modalities (visible, UV, IR, polarized, height map) all flow through the existing image embedding infrastructure — DINOv2 or whatever the current best foundation model is. The acoustic waveform requires an audio embedding model: Wav2Vec2, AST, or for a simpler start, spectrogram-as-image fed through the same image encoder. Each modality produces its own embedding vector stored alongside the capture.

**Per-modality similarity search.** Within each modality, the embedding is compared against same-modality reference embeddings. Visible-vs-visible, UV-vs-UV, and so on. This preserves the property that each modality is producing a discriminative signal in its own feature space, and doesn't require learning a cross-modal projection in the first version.

**Per-region score combination.** A region's authentication score combines its per-modality scores. The simplest combination is a weighted sum of modality scores; more sophisticated combinations involve learning the modality weights per item type, or using a small classifier trained on combined modality vectors. Start with the simple version.

**Region aggregation.** The existing region-aggregation logic (combining outer-leather score, stitching score, hardware score into a single item-level decision with abstention thresholds) carries forward unchanged.

**Storage cost.** Six modalities times three regions per item is eighteen embedding records per item rather than three. At 768-dimensional embeddings stored as float32, that's about 55KB per item rather than 9KB. Negligible at the scales LuxAuth operates at, but worth noting.

**The architectural question that's deferred.** Whether to learn a single cross-modal embedding per region (more discriminative, requires cross-modal learning) versus keeping per-modality embeddings and combining at the decision layer (simpler, works immediately) is a v0.2 question. Start with the simpler approach because it's a drop-in replacement for the current architecture and lets you measure each modality's contribution independently before committing to fusion.

---

## What discriminates authentic from counterfeit, by modality

Worth being concrete about what signal each modality actually carries.

**Visible.** Color accuracy, edge work, finishing quality, surface uniformity, hardware plating consistency. Mostly captures macro-level finishing differences that distinguish good fakes from authentic items at the level a careful human inspector would notice.

**UV fluorescence.** Adhesive composition (authentic vs. counterfeit glues fluoresce differently), dye chemistry (especially for leather treatments and thread dyes), optical brighteners (frequently present in counterfeit fabrics, less common in luxury authentic), aged versus new material (authentic patina has characteristic UV signatures). For leather goods especially, UV fluorescence is unusually informative because the tanning, dyeing, and finishing chemistry of luxury leather is markedly different from cheaper alternatives at the molecular level even when visually identical.

**IR reflectance.** Dye penetration depth, underlying material structure beneath surface coatings, plating uniformity on metal hardware, fiber composition in fabrics. IR is particularly useful for distinguishing authentic single-piece leather from layered or coated alternatives because the IR signal penetrates the surface coating in ways visible light doesn't.

**Polarized.** Material crystallinity, surface roughness statistics, plating versus solid metal, glossy versus matte finish authenticity. Polarization is informative for distinguishing real metal hardware from plated or cast imitations because the metallic crystal structure scatters polarized light differently from coatings.

**Photogrammetric height map.** Surface roughness statistics, grain depth distribution, pore structure, embossed-pattern depth and uniformity, edge roll quality on leather. Height maps capture the actual 3D structure of the surface rather than its 2D appearance, which is harder to fake convincingly because it requires actually producing the right surface topology rather than just the right surface appearance.

**Acoustic.** Material density, internal structure, assembly quality (glued versus stitched, hollow versus solid), hardware authenticity (cast versus machined, plated versus solid metal). The acoustic signature is a global property of the item region rather than a local one, which makes it sensitive to construction quality in ways the imaging modalities aren't.

The thesis is that defeating any one of these is achievable for a determined counterfeiter; defeating all six simultaneously requires reproducing the authentic item at a fidelity that approaches simply manufacturing it correctly, which is the economic outcome you want.

---

## Patent posture, briefly

Multi-spectral imaging at normal magnification, photogrammetry, and acoustic authentication each sit in cleaner FTO space than microscopy. The dominant patent in the microscopy space hinges on the word "microscopic" as a load-bearing claim limitation, and operating at normal magnification is structurally outside that limitation rather than a tweak around it.

This is not a clean room. Other patents exist in spectroscopy, photogrammetry, audio classification, and multi-modal sensor fusion, and a real FTO opinion against the specific implementation is required before any commercial deployment. But the move from microscopy to multi-modal substantially reduces the most concentrated and obvious patent risk and replaces it with a more diffuse and likely cleaner landscape.

For research-phase work — which is the current state — the patent posture is good enough to proceed. The FTO opinion is the gate before commercialization, not before exploration.

---

## What the v0.1 exploration looks like

Concrete and small. Before any hardware purchase, a one-evening exercise to test the core thesis.

Pick three to five items already owned — bags, wallets, watches, anything with luxury-level construction. For each item, capture the six modalities using whatever hardware can be assembled from what is already on hand: phone for visible, photogrammetry, and acoustic recording; a borrowed UV flashlight or any 365nm source that can be gotten hold of; a polarizer film if one is already available or can be bought cheaply; IR is the modality most likely to require a converted webcam, but it can be skipped for v0.1 if necessary.

For each modality, just look at what was captured. Does the UV image reveal information that's invisible in the visible image? Does the height map capture something distinctive about the surface? Does the acoustic waveform vary meaningfully between items? You're not running a classifier; you're forming a quick judgment about whether the modalities are actually producing discriminative signal on real items, or whether they're correlated enough that the multi-modal pitch isn't actually delivering.

If the one-evening exercise shows clear independent signal across modalities, the multi-sensor approach is worth investing real engineering time in. If the modalities mostly tell you the same thing as the visible image, the approach needs rethinking before any hardware spend.

---

## Open questions

A few things this description doesn't resolve and that would need to be worked out as part of v0.1 or v0.2.

How to calibrate the capture rig across items, operators, and time. Multi-spectral work is more sensitive to ambient conditions than single-modality imaging, which means calibration matters more.

How to handle the photogrammetry quality bar. Smartphone photogrammetry is rough, and "rough" might or might not be enough for authentication-grade height map analysis. Worth testing early whether the rough output actually contains discriminative information.

Whether to learn cross-modal embeddings or stay with per-modality embeddings combined at decision time. The simpler approach works immediately; the more sophisticated approach is potentially much more discriminative. Decide after measuring.

How acoustic capture handles items that aren't shaped to allow a controlled striker (soft items, items where tapping risks damage). Possibly the acoustic modality is selectively applied to item types where it's appropriate rather than universally.

What the operator skill curve looks like for non-expert capture, and whether the protocol can be made simple enough for resale-platform-staff-level operators rather than requiring trained authenticators.

These are the questions a real v0.1 build would need to answer. They're not blockers to starting the exploration; they're the things you'd find out by doing it.

---

## Relationship to the current LuxAuth implementation

The microscopy-based pipeline is the in-flight implementation. Phase 10 (few-shot prototype matching with DINOv2 backbone comparison) is complete; Phase 11 (DINOv2 shadow integration) is planned and gated on capture infrastructure prerequisites being visible. The current pipeline assumes a single modality (microscopic visible-light imagery).

If a v0.1 multi-sensor exploration is undertaken and produces clear independent signal across modalities, the integration path would be:

1. **Add a `modality` field to capture metadata.** Existing captures become `modality = visible_microscopy`. New captures carry their own modality tags.
2. **Per-modality embedding pipelines.** The existing image-embedding infrastructure (texture_baseline, learned_metric, DINOv2) handles the image-like modalities. Audio embedding for acoustic is a new component.
3. **Per-modality similarity search.** Reuses pgvector and the existing region scoring, partitioned by modality.
4. **Score combination at the decision layer.** Initial implementation is a weighted sum; more sophisticated fusion is a v0.2 question.
5. **Existing decision-service logic carries forward** without change. This is the architectural payoff of the modality-agnostic pipeline design.

If the v0.1 exploration does **not** show clear independent signal, this document remains as a record of a strategic option that was considered and rejected on evidence. Phase 11 microscopy-based shadow integration continues as planned.

The two paths are not currently being run concurrently because the resource-allocation argument that gated Phase 11A (capture infrastructure prerequisites visible, not just possible) applies equally here. A multi-sensor exploration would be undertaken when the conditions for it exist, not speculatively.

---

## Related documents

- [ConceptOfOperation.md](ConceptOfOperation.md) — current microscopy-based product and technical concept
- [docs/datasets/few-shot-prototype-results.md](docs/datasets/few-shot-prototype-results.md) — Phase 10 evidence on the microscopy approach
- [docs/roadmaps/dinov2-shadow-integration-plan.md](docs/roadmaps/dinov2-shadow-integration-plan.md) — Phase 11 plan for the microscopy approach
- [docs/roadmaps/dinov2-shadow-integration-readiness.md](docs/roadmaps/dinov2-shadow-integration-readiness.md) — Phase 11 readiness checklist
- [docs/roadmaps/capture-infrastructure-prerequisites.md](docs/roadmaps/capture-infrastructure-prerequisites.md) — capture dependency framing (currently scoped to microscopy; adaptable to multi-sensor if the approach is adopted)
- [docs/roadmaps/ml-improvement-roadmap.md](docs/roadmaps/ml-improvement-roadmap.md) — overall ML phase sequencing
- [docs/retrospectives/phase-10-retrospective.md](docs/retrospectives/phase-10-retrospective.md) — meta-lessons from the microscopy arc
