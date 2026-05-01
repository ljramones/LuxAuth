# Phase 10 Retrospective

**Date written:** 2026-04-30
**Phase covered:** Phase 10 — Few-Shot Prototype Matching with DINOv2 Backbone Comparison (Pass 1 DINOv2 service integration, Pass 2 experimental harness, full grid execution against LeaData and FabricNET, Phase 11 plan + readiness checklist).
**Scope:** Meta-lessons about how the work was done. Phase 10 results live in [Few-Shot Prototype Matching Results](../datasets/few-shot-prototype-results.md). The Phase 11 plan lives in [DINOv2 Shadow Integration Plan](../roadmaps/dinov2-shadow-integration-plan.md). This document does not duplicate either.

---

## What worked

**Existing dataset governance schema absorbed the new model version with zero rework.** `model_versions` and `reference_embeddings` were designed before DINOv2 was on the roadmap. Adding `dinov2_base_frozen_v0.1.0` was a single `INSERT` row; embedding generation reused the existing `reference_embeddings` table without schema changes. The schema's foresight made what could have been a disruptive integration into a one-line operation. Worth noting because the eventual `threshold_profiles` schema gap (see below) is the counter-example — that one was *not* designed for what Phase 10 needed.

**Pre-computing embeddings made the 500-episode grid trivially fast.** Once DINOv2 weights were downloaded and 1330 embeddings were persisted in pgvector, the entire 2-model × 4-K × 5-strategy × 500-episode grid ran in tens of minutes. No model loading per episode, no S3 round-trips, no cold-start cost. The split between "embed once, evaluate many times" was the right architectural choice and it kept the experimental loop fast enough to iterate on real questions rather than wait on machinery.

**Surfacing gaps rather than forcing completion was the right call.** The two carryover items in the Phase 11 plan (`learned_metric_v0.2.0` historical-comparison gap, `threshold_profiles` candidate-status gap) were both candidates for "patch it through and move on" treatment. Both were left as documented gaps with the underlying design question named explicitly. The threshold profile gap turned out to be a status-vs-reference_dataset_version design question, not a missing-column problem. The artifact gap turned out to be a broader governance pattern, not a `learned_metric`-specific issue. If either had been patched through, the underlying design question would have stayed buried.

**Combined 10a + 10b experiment matrix was cleaner methodology.** The original framing had prototype inference (10a) and DINOv2 backbone (10b) as sequential phases. Running them as one matrix produced cross-tabulation rather than two separate result sets to reconcile later. The support-set stabilization curves are conditional on embedding quality — measuring them across embedding regimes simultaneously was the only way to avoid calibrating capture protocol decisions against weak embeddings.

**Conservative shadow-mode framing was named explicitly.** "The empirically-weaker model continues to make the production decision while we gather evidence on the empirically-stronger candidate" is the kind of decision that's hard to recognize as a deliberate choice in retrospect if it isn't named at the time. Naming it in the Phase 11 plan §1 and §3.6 means future readers can't misinterpret the parallel-running models as a hidden tradeoff or oversight.

**Split-aware sampling test was written proactively, not after a leakage bug.** No leakage failure was caught in flight — the test was written because the project owner flagged it as load-bearing. The test pins the contract by asserting that split_filter actually filters before grouping, with exact-count assertions on both partitions. This is the kind of test whose value shows up months later when someone refactors the grouping logic and would otherwise silently regress.

---

## What didn't work or was harder than expected

**`learned_metric_v0.2.0` had no persisted LeaData embeddings.** This was discovered at run time during gate-decision data collection, not at planning time. The Phase 10 grid ran as a 2-way comparison instead of the planned 3-way. The runner skipped the missing model cleanly (the in-flight skip-logic worked as designed), but the missing comparison weakened the cluster_separation evidence and pushed the `learned_metric` historical comparison into Phase 11A as a carryover. Earlier inventorying of which models had embeddings on which datasets would have caught this at planning time rather than execution time.

**`threshold_profiles` schema didn't accommodate candidate / diagnostic profiles.** Cleanup task C in the Phase 11 planning pass attempted to register `dinov2_base_frozen_default` and immediately surfaced three issues: no `margin_threshold` column, no `description` / `provenance` column, and a `NOT NULL reference_dataset_version` constraint that contradicted the candidate-status framing. Inserting a partial profile was considered and rejected (downstream callers could read the row and miss the margin requirement). The fix is a schema design pass on the `status`-vs-`reference_dataset_version` relationship, not a column-addition migration.

**Multiple `learned_metric` `.pt` artifacts exist locally without canonical designation or S3 upload.** Discovered while investigating cleanup task B. Phase 5/6/7/8/9 each produced one or more `.pt` files for `learned_metric_v0.2.0` under different training regimens. None are in S3. None are in `model_versions`. There is no canonical artifact. The pattern will recur on every future training experiment if not addressed structurally — surfaced in the Phase 11 plan as the "model artifact governance" workstream rather than a `learned_metric`-specific patch.

**The `make analyze-embeddings` Makefile target didn't pipe `DATASET` through.** Minor but worth flagging. The target hardcoded `--model` only and used a hardcoded default dataset. During the gate-decision step I worked around it inline rather than fixing the Makefile (scope creep at the time). The hard-coded dataset is a latent footgun for any future user who runs `make analyze-embeddings` against a non-default dataset and gets results from the wrong data.

---

## What we learned about the domain

**Foundation-model embeddings transferred to leather microscopy better than the prior suggested.** The prior was that DINOv2's natural-image training distribution (ImageNet-scale general photography) might transfer poorly to microscopic surface texture (different illumination geometry, different scale, different sensor characteristics). The actual cluster_separation gap on LeaData was ~10× texture_baseline's — a much wider margin than expected. The domain gap between natural images and leather microscopy is smaller than the visual difference suggests, at least for the discriminative properties LeaData rewards.

**LeaData's low intra-class variance flipped the NN-vs-prototype prior.** Textbook expectation was prototype_centroid beating nearest_neighbor at K≥3 because averaging is a variance reducer. On LeaData, NN won at every K for both embedding models. The most plausible explanation is that LeaData's unusually consistent capture conditions (single device, controlled lighting, no operator variation, no wear, no production-year drift) make the nearest support example reliably the highest-fidelity probe — there's no outlier-induced variance for centroid averaging to smooth out. This is hypothesized to be LeaData-specific; real luxury data with higher intra-class variance may flip the result back to the textbook expectation. The Phase 11 plan treats this as an open question and requires parallel-strategy logging during shadow operation to resolve it on real data.

**texture_baseline's flat abstention curve revealed a deeper problem than the accuracy gap alone.** The headline finding was that texture_baseline can't usefully threshold-abstain — every threshold above 0.0 either rejects everything or rejects nothing within the < 30% abstention budget. This is structurally different from "DINOv2 is more accurate." It says texture_baseline's score distribution itself is degenerate — same-class and diff-class similarities are both ~0.94 with margin ~0.02, so the score is barely informative even when the decision is correct. A model that produces correct decisions with uninformative confidence scores is harder to operate than a slightly-less-accurate model with calibrated confidence. The accuracy gap (98.3% vs 95.2% at K=5 item_id) understates the operational gap.

---

## What we learned about the process

**The pause point at the end of Phase 10 was the right move.** Pushing into Phase 11A speculatively would have built threshold profile schema, model artifact governance, and DINOv2 deployment readiness for inputs that don't yet exist. The readiness checklist (Phase 11D needs real captures flowing, an expert reviewer, and a divergence review surface) made the gating logic explicit. Resuming when triggers fire is better resource allocation than maintaining attention through a build phase that has no hard deadline.

**Pre-declaring promotion criteria before any data exists prevents post-hoc rationalization.** The Phase 11 plan §7 lists ten criteria with specific thresholds (4 weeks calendar, 100+ sessions, 20+ reviewed divergences, etc.). None of those numbers are calibrated against actual real-capture data because no real-capture data exists. They are pre-declared specifically so they cannot be weakened to fit observed results later. This was the right discipline even though no promotion decision is imminent — the alternative is criteria that drift to match whatever the data turned out to look like.

**Splitting the work into bounded passes (Pass 1, Pass 2, planning pass) produced cleaner work than one large continuous pass would have.** Each pass had a defined acceptance gate and a stop point. Pass 1's snags (HTTP-vs-direct-import call, schema field mismatch) were surfaced and addressed before Pass 2 depended on them. Pass 2's experimental code didn't have to absorb DINOv2 integration debugging concurrent with experimental design work. A single large pass would have entangled the failure modes.

**Committing scoped follow-ons separately from the main bundle improved the historical record.** The readiness checklist landed as commit `62c8174` rather than being squashed into the wrap-up commit `0cfea4d`. Future archaeology on either commit reads cleanly because the scope of each is small and named.

---

## What I'd do differently

**Inventory model-version × dataset embedding coverage before starting any experiment that depends on it.** The `learned_metric_v0.2.0` gap was discoverable with one SQL query and would have been caught at planning time rather than execution time. A small "embedding coverage matrix" check should be a prerequisite for any experimental run that compares across models, not an artifact of the run itself. This is a five-minute habit that costs nothing and prevents one specific class of mid-run surprise.

**Fix the `make analyze-embeddings` Makefile target inline when I noticed it.** Working around the broken target was the right call for *that* moment (avoid scope creep mid-experiment), but I should have logged it as a follow-up immediately and fixed it before the wrap-up commit landed. Instead it became a footgun for the next user. A two-minute fix that I deferred for no good reason.

**Decide the in-process-vs-HTTP question for the Phase 11D shadow path explicitly, not by analogy from Pass 1.** The Pass 1 deliberate-architectural-choice docstring on `generate_embeddings.py` argued the in-process path is correct for batch reference ingestion. That argument doesn't extend to Phase 11D production scoring, which is request-driven and benefits from HTTP middleware (auth, rate limiting, telemetry). The Phase 11 plan §5 names dual-strategy logging in the production scoring path but doesn't make the in-process-vs-HTTP call. That call should be made explicitly in Phase 11A design, not assumed to follow Pass 1's choice. Worth flagging now so future-me doesn't carry the wrong default forward.

---

## Open questions for resumption

These are not bugs. They are decisions the right answer for which wasn't obvious at the time and that deserve fresh attention when work resumes.

- **Threshold profile status taxonomy.** `active` / `candidate` / `diagnostic` / `retired` is the proposed shape in the Phase 11 plan §6.2. The right scope and the right relationship between `status` and `reference_dataset_version` is a small design conversation that should happen in Phase 11A.1 rather than be rushed.
- **Model artifact governance policy.** When does a training experiment's output become a candidate for promotion? What designates one artifact as canonical when an experiment runs multiple variants? What is the retention policy for non-promoted experiments? The policy doesn't need to be elaborate — it needs to exist. Phase 11A.2.
- **In-process vs HTTP shadow path.** As above. Worth deciding explicitly during Phase 11A design rather than carrying Pass 1's batch-ingestion choice forward by default.
- **Visibility of skipped models in the runner.** The Phase 10 runner skipped `learned_metric_v0.2.0` cleanly via per-cell stdout. In a long run, that skip is easy to miss. When Phase 11D runs in production, what is the alerting surface for shadow-path failures or skips? The current "log it and move on" pattern was right for a one-off experiment; it isn't right for a 4-week shadow window.
- **pgvector capacity at 768-d at production-scale reference libraries.** Named in the Phase 11 plan §13 risk #4 but not quantified. At LeaData scale (1200 embeddings) it's trivial. At what reference library size does pgvector with 768-d HNSW start to need attention? Worth a back-of-envelope calculation in Phase 11B before any large-scale re-embedding starts.

---

*End of retrospective. Next surface to read: [Pre-Phase 11 Readiness Checklist](../roadmaps/dinov2-shadow-integration-readiness.md).*
