# Item Condition and Component Provenance

## Why Luxury Goods Are Assemblies, Not Monoliths

A luxury handbag is not a single homogeneous object. It is an assembly of components:
leather body, stitching, hardware (zippers, clasps, chains), lining, heat stamp,
serial/date code, edge paint, and sometimes attached accessories.

Real-world items may have:
- **Authentic body with replaced handle** — handle leather is different age/source
- **Authentic bag with third-party stitching repair** — thread type and stitch spacing differ
- **Counterfeit hardware on authentic leather body** — a "Franken-bag"
- **Heavy wear muting leather grain** — surface texture altered by use, not fraud
- **Professional restoration** — edge paint reapplied, hardware replated

A system that treats items as monolithic "authentic" or "fake" will mishandle these cases.

## Why This Matters for ML

If the embedding model detects a mismatch on a specific region (e.g., stitching), the
system needs to distinguish:
- **Counterfeit manufacturing** — the stitching pattern matches known counterfeit references
- **Third-party repair** — the stitching was replaced after purchase with non-OEM thread
- **Wear degradation** — the stitching appears different because of age and use

Without condition metadata, the system cannot make this distinction. A repaired region
mismatch routed to "UNVERIFIED" is a false positive if the item is genuinely authentic.

## Why Condition Can Be a False Proxy for Authenticity

Heavy wear reduces texture contrast, flattens leather grain, and accumulates surface
marks. If the model learns that worn textures are "different from reference," it may
flag authentic used items as suspect — not because they are counterfeit, but because
they are old.

Condition metadata lets the system and human reviewers distinguish "different because
fake" from "different because used/repaired."

## Schema

Two tables support this metadata:

**`item_condition_metadata`** — per-item condition and provenance:
- condition_grade (pristine / used_good / used_fair / heavily_worn)
- known_authenticity_basis (original_receipt / expert_opinion / brand_authenticated / unverified)
- known_repairs, third_party_repair flags
- restoration_notes, provenance_notes, condition_notes

**`item_component_conditions`** — per-region/component condition:
- region_code (matches capture protocol regions)
- component_type (leather, thread, hardware, lining, etc.)
- component_status (ORIGINAL / REPLACED_OEM / REPLACED_THIRD_PARTY / UNKNOWN)
- exclude_from_auth_decision flag
- expected_to_mismatch flag
- source and confidence

## Future Decision Behavior

The decision service does not yet use condition metadata. Planned behavior:

- A known repaired region that mismatches should route to EXPERT_REVIEW_REQUIRED,
  not automatically UNVERIFIED
- Future result types may include:
  - VERIFIED_WITH_DISCLOSED_REPAIR
  - ALTERED_COMPONENT_DETECTED
- Disclosed repairs should not automatically produce VERIFIED — expert judgment
  is needed to assess whether the repair is consistent with the disclosure

## Current Status

This is **metadata support only**. The system can record condition and component
provenance in capture manifests and persist it during ingestion. It does not yet
use this metadata in scoring or decision logic.

## Controlled Vocabulary

See [Item Condition Vocabulary](../reference/item-condition-vocabulary.md) for the
canonical values for condition_grade, component_status, component_type, source,
confidence, and related fields.

## Disclaimers

- This metadata layer does not authenticate repairs automatically
- Disclosed repairs should not produce automatic VERIFIED results
- Early behavior should route repaired/mismatched items to expert review
- Condition metadata is a tool for safer future decisioning, not a shortcut
