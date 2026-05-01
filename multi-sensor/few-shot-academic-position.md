# Few-shot operation in the multi-spectral system: argument and academic position

**Document version:** v1
**Date:** 2026-05-01
**Companion to:**
- [MultiSensorAuthenticationApproach.md](../MultiSensorAuthenticationApproach.md) — strategic-options briefing at repo root
- [experiment-plan.md](experiment-plan.md) — phased experiment plan whose calibration steps generate the empirical evidence this position depends on

This document is the academic-defense position for the multi-sensor system's few-shot operation. It explains how few-shot prototype-based authentication, validated in Phase 10 of the microscopy work, transfers to and is extended in the multi-sensor architecture, and what claims the system actually makes versus what it does not.

---

## Position

Few-shot prototype-based authentication, as validated in Phase 10 of the LuxAuth microscopy work, is preserved and extended in the multi-spectral system. The conceptual foundations of few-shot learning — discriminative embedding spaces, prototype construction from small support sets, nearest-neighbor and prototype-centroid retrieval — are properties of the embedding space, not of the capture modality. Multi-spectral capture changes what feeds the embedding step; it does not change the few-shot machinery downstream.

The multi-spectral system instantiates few-shot operation per modality, with per-modality calibration of K, abstention thresholds, and retrieval strategy. Per-modality few-shot results combine at the decision-aggregation layer using the same per-region aggregation logic the system already employs, extended to per-modality-per-region. This produces a system that is more capable than single-modality few-shot, not less, because it provides multiple independent few-shot signals per item and enables cross-modal consistency analysis that single-modality systems cannot perform.

## What few-shot actually is, formally

To address academic scrutiny, it helps to be precise about what few-shot learning means and what claims the LuxAuth system actually makes.

In the supervised meta-learning literature (Vinyals et al., Snell et al., Sung et al.), few-shot classification is defined as learning to classify queries given a small support set of labeled examples per class, where the support set sizes (N_shot) are small relative to typical supervised training. The canonical setup is N-way K-shot: N classes, K examples per class in the support set, classify a query into one of the N classes.

LuxAuth's few-shot operation is a specific application of this: per-item-class verification rather than open-set classification. The "classes" are items (each authentic item is its own class, identified by item_id) or item types (groups of items at the species level). The support set is the set of authentic captures already in the reference library. Queries are new captures of items being authenticated. Retrieval is nearest-neighbor or prototype-centroid based on embedding distance.

Phase 10 validated three things specifically:

That DINOv2 frozen embeddings produce cluster separation strong enough for prototype-based retrieval to work. Cluster_separation values of +0.1742 species and +0.2996 item_id versus the texture_baseline at +0.0178/+0.0423 — roughly seven to ten times stronger separation.

That nearest-neighbor retrieval at K=5 achieves accuracy of 0.9832 on item_id and 0.9566 on species (still climbing at K=10).

That abstention thresholds derived from real data produce useful trade-offs: at K=5 with score_threshold=0.80 and margin_threshold=0.10, item_id accuracy reaches 0.9984 with 19.7% abstention.

These results are *empirical findings about the embedding space*, not about microscopy specifically. The argument is that any modality producing comparably-discriminative embeddings will support comparably-effective few-shot retrieval.

## How few-shot transfers to multi-spectral

The multi-spectral system produces multiple parallel embedding spaces, one per modality. Each modality's embedding space is independent: visible-light embeddings live in one DINOv2-feature space, UV-fluorescence embeddings live in another (also DINOv2-derived but on different input data), capacitive readings live in a low-dimensional space (1D scalar or short impedance vector), hyperspectral readings live in an 18-dimensional space, and so on.

Within each modality's embedding space, the few-shot framework operates exactly as it does in the microscopy system:

Reference set construction. For each authentic item in the reference library, the system has K captures per modality per region. These captures, embedded through the modality-appropriate encoder, form the support set for that item-modality pair.

Query embedding. A new capture in modality M is encoded through the same encoder used for the reference set, producing a query vector in modality M's embedding space.

Retrieval. The query vector is compared against the support set in modality M's space using either nearest-neighbor or prototype-centroid retrieval. This produces a (score, margin) pair in modality M.

Per-modality decision. Score and margin in modality M are compared against modality-M-specific thresholds (derived from authentic-only or authentic+counterfeit data during calibration) to produce a modality-level verdict: authentic, anomalous, or abstain.

Cross-modality aggregation. Per-modality verdicts and scores combine at the region level using the system's existing decision aggregation logic, extended to handle per-modality inputs. The combination policy is configurable: weighted average of modality scores, conservative-abstain (any modality abstains → region abstains), majority voting, or learned combination weights.

This is not a new architecture. It is the existing architecture instantiated multiple times in parallel, one instance per modality, with results combined at the existing region-aggregation layer.

## Why this is academically defensible

Academic concerns about few-shot transfer typically center on three questions: whether the embedding space is appropriate for the downstream task, whether the support sets are sufficient and representative, and whether the evaluation methodology is sound. The multi-spectral system addresses each.

**Embedding space appropriateness.** The microscopy system established that DINOv2 frozen embeddings produce strong cluster separation on visible-light microscopic captures of luxury materials. The argument that this transfers to other imaging modalities (UV, IR, polarized, raking light, transmitted light) rests on the observation that DINOv2 was trained on billions of images spanning enormous visual diversity, including imagery captured under unusual lighting conditions. UV-illuminated images of leather are visually unusual but not categorically different from images DINOv2 has seen — they're images of textured surfaces under specific illumination. The expectation that DINOv2 features will produce useful embeddings on UV captures is empirical, not theoretical, but the empirical work is exactly what the experiment plan validates.

For non-imaging modalities (capacitive, hyperspectral, thermal cooling curves, acoustic waveforms), the embedding approach differs from DINOv2 and the appropriateness argument is different per modality. Capacitive readings are low-dimensional and may not need a learned encoder at all — direct comparison in the raw measurement space may suffice. Hyperspectral readings are 18-dimensional and benefit from either direct comparison or a small learned projection. Waveforms (thermal, acoustic) benefit from audio-style encoders or spectrogram-based image encoders. The appropriateness of each approach is established empirically per modality during calibration phases.

The academic standard here is: "the embedding space supports few-shot retrieval if and only if the cluster separation metric on the reference set is strong relative to a baseline." Phase 10 used texture_baseline as that baseline. The multi-spectral system uses the same metric per modality. A modality's embedding space is validated for few-shot use when its cluster separation exceeds a defensible threshold. Modalities that fail this test are dropped from the system. This is the same methodology Phase 10 used; it's just applied per modality.

**Support set sufficiency.** Phase 10 found that K=5 was the plateau for item_id retrieval and K=10 was still climbing for species retrieval. The few-shot literature generally finds that K in the range 1-10 is the regime where K-curve behavior matters, with diminishing returns above K=10-20. The multi-spectral system's per-modality K may differ from microscopy's K, and the experiment plan calls for per-modality K-curve derivation specifically. There is no theoretical reason different modalities should have the same K.

The relevant academic concern is: "how do you know K=5 is enough for modality M?" The answer is the same as in Phase 10: you derive the K curve empirically on a held-out test set during calibration and select K at the plateau. If a modality requires K=15 to plateau, the system uses K=15 for that modality. If a modality plateaus at K=2, the system uses K=2.

**Evaluation methodology soundness.** Phase 10 used split-aware sampling enforced at the harness level, 10-fold cross-validation, and abstention curves derived as full threshold sweeps rather than single-point estimates. The multi-spectral system applies the same methodology per modality and at the system level (combining per-modality results). The evaluation harness from Phase 10 (`few_shot.py`, the experiment scripts, the comparison tools) extends naturally to multi-modal evaluation by being run per modality and then aggregating.

The academic standard is: "evaluation must use train/test splits that prevent leakage, must report variance not just point estimates, and must report abstention behavior as curves not single points." The multi-spectral system inherits this standard from Phase 10.

## What's genuinely new in the multi-spectral context

To be intellectually honest, the multi-spectral system raises a few questions that weren't present in single-modal few-shot. Anyone scrutinizing this academically should understand these are open questions, not problems concealed.

**The cross-modal independence assumption.** The argument that multi-modal few-shot is better than single-modal few-shot rests on the modalities being statistically independent — i.e., that knowing the visible-light embedding doesn't fully predict the capacitive reading or the UV signature. If the modalities are perfectly correlated, multi-modal collapses to single-modal and the additional infrastructure is wasted complexity. If the modalities are partially correlated, the system captures partial additional information. If the modalities are fully independent, the system captures maximum additional information.

This is testable empirically. The experiment plan's E1 and E2 phases include explicit modality-correlation analysis. If correlations are too high, modalities are dropped or the multi-modal pitch is reconsidered. The academic position is: "modality independence is an empirical question that the experiment plan addresses, not an assumption baked into the architecture."

**Per-modality calibration drift.** In the microscopy system, calibration drift was a single-modality problem. In multi-modal, each modality has its own potential drift sources (UV LED aging, capacitive sensor humidity sensitivity, thermal sensor offset shifts). The reference library captures embed the calibration state at capture time, which means drift between capture sessions affects retrieval accuracy in modality-specific ways.

Mitigation: calibration targets visible in every capture (the v3 design document made these mandatory for exactly this reason), per-modality periodic recalibration against known references, and modality-level monitoring of distribution shift over time. The academic position: "calibration drift is a known problem with mitigation strategies, addressed at the protocol level."

**The combination policy choice.** Per-modality scores combining into per-region scores is itself a design choice with implications. Weighted averaging assumes modalities are commensurable and non-veto. Conservative abstention assumes any modality's uncertainty propagates. Learned combinations can over-fit to small datasets. The right choice is empirically determined, but the argument that few-shot "works" in multi-modal depends on which combination policy is in use.

The academic position: "combination policy is part of the system specification, validated empirically per modality and per item type, with per-policy performance characterized in evaluation." The Phase 10 work produced per-region aggregation evidence; multi-modal extension adds per-modality aggregation, characterized similarly.

## What strengthens few-shot in multi-spectral that wasn't possible in single-modal

Beyond preservation, multi-spectral few-shot enables capabilities single-modal cannot:

**Cross-modal consistency as a signal.** When a query item produces consistent results across all modalities (all modalities retrieve the same authentic items as nearest neighbors, all modalities produce similar score and margin distributions), the system has stronger evidence for authenticity than any single modality provides. When modalities disagree (visible says authentic, capacitive says anomalous), the disagreement is itself diagnostic — likely indicating partial counterfeiting (refurbished hardware, restored leather, hybrid items assembled from multiple sources).

This is not a few-shot extension per se but a downstream use of per-modality few-shot results that single-modal systems cannot perform. Academically, this is a multi-view consistency analysis applied to authentication, with established literature in multi-view learning and ensemble methods.

**Partial authenticity detection.** Items where some components are authentic and others are not (refurbished bags, restored watches, "frankenbags" assembled from multiple items) are difficult for single-modal authentication because the authentic components produce confident authentic retrievals. Multi-modal authentication catches these because at least one modality usually disagrees about the substituted component. The few-shot retrieval on each modality independently surfaces which modality disagrees, providing a localizable signal about which component of the item is anomalous.

This is a categorical capability that single-modal systems lack. Academically, this aligns with research in fine-grained authentication and provenance verification.

**Per-modality explanation.** When the system flags an item as anomalous, multi-modal few-shot enables modality-level explanation: "this item is anomalous in capacitive (closest authentic K=5 distance is N standard deviations away) and consistent with authentic in all other modalities." Single-modal systems can only say "anomalous" without indicating why. Modality-level explanation is more interpretable for expert review and aligns with academic interest in explainable authentication.

## How to ensure few-shot operation continues to work in practice

The continuity of few-shot operation depends on operational practices that the experiment plan and design documents specify:

**Per-modality K-curve derivation during calibration.** Each modality has its K characterized on real data, with the chosen K placed at or above the empirical plateau. Phase 10 methodology applies; the harness is reused per modality.

**Per-modality abstention threshold derivation.** Each modality produces (score_threshold, margin_threshold) pairs derived from real data, characterized with full threshold-sweep curves. Phase 10's elbow-finding methodology applies; the abstention curves are characterized per modality.

**Per-modality reference library construction.** The reference library contains K captures per modality per region per item, captured under controlled conditions with calibration targets visible. Reference library quality is the foundation of few-shot accuracy; the protocol specification makes this explicit.

**Per-modality monitoring of distribution shift.** Modalities can drift over time (sensor aging, environmental changes). The system monitors per-modality nearest-neighbor distance distributions over time and flags drift when distributions shift beyond baseline. This is operational monitoring, not few-shot mechanics, but it preserves few-shot accuracy by catching degradation early.

**Cross-modal consistency monitoring.** Beyond per-modality drift, the system monitors agreement between modalities on known-authentic items. Sudden drops in cross-modal agreement on items previously consistent indicate either an item-level change (authentic item becoming damaged or weathered) or a system-level problem (one modality drifting). This is a multi-modal-specific monitoring practice.

**Versioned modality vocabulary.** As the system evolves, modalities may be added, removed, or refined. The captures in the reference library are tagged with their modality version and capture protocol version, enabling per-version few-shot evaluation and cross-version comparison. This is data governance, not few-shot mechanics, but it preserves few-shot validity over time.

## The defensible academic claim

The position to take when defending this academically is:

"Few-shot prototype-based authentication is a property of discriminative embedding spaces, not capture modalities. The microscopy-based LuxAuth system validated few-shot operation on DINOv2 frozen embeddings of microscopic captures. The multi-spectral system applies the same few-shot framework to multiple parallel embedding spaces, one per modality, with per-modality calibration of K, abstention thresholds, and retrieval strategy. Per-modality few-shot results combine at the decision-aggregation layer using policies validated empirically per item type. The architectural extension preserves all single-modal few-shot guarantees while enabling new capabilities — cross-modal consistency analysis, partial authenticity detection, modality-level explanation — that single-modal systems cannot provide. The validity of the multi-modal extension is empirically established through the per-modality calibration phases of the experiment plan, using the same evaluation methodology that validated the original microscopy-based few-shot system."

The defensive claim against academic skepticism is:

"Few-shot in multi-modal is not 'few-shot something else.' It is the same few-shot framework, instantiated multiple times in parallel, with the same calibration methodology applied per instance, and results combined at the same decision-aggregation layer the single-modal system uses. The empirical validation is per-modality, with the same harness, the same metrics, the same statistical rigor. Anything that worked academically in the microscopy system continues to work. The new questions multi-modal raises (modality independence, per-modality calibration drift, combination policy selection) are addressed empirically in the experiment plan, with explicit success criteria and decision gates. The system does not assume multi-modal validity; it tests it."

This is the position. It's defensible, it's specific, and it's grounded in the empirical methodology Phase 10 established. Anyone who scrutinizes it academically should be able to find specific points to engage with rather than vague claims about multi-modal authentication; the position commits to particular methodological choices and tests their validity rather than asserting them.
