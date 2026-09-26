# Current Research State

This document is the authoritative description of the project's current research direction.

## Current routing — W2A v1.0 prepared offline; not launched, 2026-09-26

The researcher asked to start W2A and carry it to a launch-ready package without live inference. [W2A v1.0](../../research_runs/ai_witness_followup_2026_09/w2a/README.md) is now a separate study with its own design, harness, schedule, ledgers and identifiers under `research_runs/ai_witness_followup_2026_09/w2a/`. W1 stays closed under D005; W2A only reads W1 artifacts.

- **Design:** four exposed W1 development cases × F2 (plain agent) and F3 (planner → judge → generator), one session each, eight sessions in total. The generator is Claude Sonnet 5 via OpenCode Zen; there is no Jev. W1's validation and focal-oracle code is copied byte-identically.
- **Observed (offline only):**
  - the W1 audit reproduces byte-identically;
  - all 13 offline gates pass;
  - 24/24 tests pass;
  - nine W1 failure cases (R1–R9) are replayed against W2A code and pass;
  - a fake-provider run of all eight sessions passes on terminal accounting, sealing before validation, and ledger-equals-session accounting;
  - both the design freeze and the executable package freeze verify.
- **Material change ([DESIGN_CHANGES.md](../../research_runs/ai_witness_followup_2026_09/w2a/design/DESIGN_CHANGES.md), [D006](DECISIONS.md)):** the session input cap rises from the proposed 240k to 640k.
  - Checked against the actual rendered requests and W1 calibration, 240k cannot deliver the proposal's own call allocation once the final call is reserved.
  - 640k is the output of a declared rule. The USD caps (1.00 per session, 8.10 for the study including the smoke) are unchanged.
- **Not executed:** provider requests, the smoke, and subject runs. There are no W2A results.
- **Launch blockers:** the `W2A_GENERATOR_API_KEY` credential, the authorized smoke (identity and request shape), and re-confirmed pricing. See [readiness.md](../../research_runs/ai_witness_followup_2026_09/w2a/readiness.md).
- **Next action:** the researcher issues [MEASURED_RUN_PROMPT.md](../../research_runs/ai_witness_followup_2026_09/w2a/design/MEASURED_RUN_PROMPT.md).

This entry supersedes the "W2A proposed" routing below. W1 observations and D005 are unchanged.

## Current follow-up — W1 audited; W2A feasibility proposed, 2026-09-26

The researcher asked to inspect the AI witness results and push forward, confirming Claude Sonnet 5 as the generator. The new [offline trace audit](../../research_runs/ai_witness_2026_09/postrun_audit/REVIEW.md) confirms `claude-sonnet-5` in all 119 measured responses, all 1,962 raw hashes, 181 executable hashes, both chains, all 60 labels and 28 complete policy summaries. W1's table and D005 remain unchanged.

The audit refines the earlier failure explanation: six input-admission denials and one output-admission denial, four truncated responses, two empty planner submissions accepted as stage completion, one empty judgment submission, and an invalid placeholder as the sole AI patch. Most structured generation stages received only one or two model calls. Initial gRPC excerpts omit the test helper body; repeated cross-stage source reads are partly explained by context not being transferred. No AI session used more than 84 of its 600 seconds.

**Proposed next work:** [W2A v0.1](../../research_runs/ai_witness_followup_2026_09/v0_1/PROPOSAL.md), an eight-session plain/structured execution-feasibility pilot after offline harness repairs and an independent freeze. Keep Sonnet 5, carry source evidence across stages, validate stage outputs, and reserve generation/finalization budget. Jev's effectiveness comparison follows only after the workflow can produce and submit usable candidates. W2A is proposed, not frozen or executed; W1 cases remain exposed development cases. No new provider or subject runs occurred during this audit.

This clarification supersedes the failure-mechanism wording below, not W1's measured counts or historical decisions.

## Latest result — W1 measured run: COMPLETE, no method advances, 2026-09-26

The frozen [W1](../../research_runs/ai_witness_2026_09/results_report.md) v1.2 study ran to completion on the researcher's launch instruction: 12/12 blocks, 60/60 sessions and 60/60 validations. There were no pauses, resumes, reruns or amendments. The generator was Claude Sonnet 5 via OpenCode Zen. This supersedes the preparation and routing entries below.

- **Observed:**
  - Validated witnesses out of three replicates:

    | Case | B0 | B1 | B2 | B3 | B4 |
    |---|---|---|---|---|---|
    | pool162 | 0 | 3 | 0 | 0 | 0 |
    | grpc1859 | 2 | 0 | 0 | 0 | 0 |
    | k8s26980 | 0 | 0 | 0 | 0 | 0 |
    | istio17860 (control) | 3 | 3 | 3 | 0 | 0 |

  - No AI arm sealed a synthesized test. All four B2 finals were the explicit unchanged overlay, including its three istio witnesses. 32 of 36 AI sessions ended with NO_SUBMISSION: generator call caps were exhausted by repeated `read_source`, or the cache-inclusive 60k input-token ceiling was reached. One AI patch was proposed in 36 sessions.
  - The only synthesized validated witness is B1's T3 resource-lifecycle template on pool162: 3/3 replicates, 15/15 focal failures each.
  - grpc1859's unchanged test is a rare-signal witness. Accept-on-pass (P3) blocked 0/5 triplets; retaining any focal failure flagged 3–4/5.
  - No invalid candidates, exclusions or missing outcomes. Every acceptable-variant attempt in every witness passed.
  - Integrity: both freezes were verified before launch and again after; the raw seal was written before analysis; both ledger chains are intact. Labels, the table, policy counts and all witness trace hashes were independently recomputed and match.
  - Cost: about USD 3.34 (computed from provider-reported usage; the account debit was not checked), 119 generator requests, 1.33M input tokens, 71 Jev evaluations and 20.0 allocated vCPU-h. Wall time was 1 h 17 min.
- **Interpretation:**
  - Under the frozen call and token ceilings, the AI arms could not execute with this generator configuration.
  - W1 therefore measures the execution feasibility of the frozen AI harness. It is not evidence about whether structured analysis (B3 vs B2: 0 on every noncontrol case) or Jev (B4 vs B3: identical zero vectors) helps.
  - The binding constraints were the call caps and the cache-inclusive input ceiling, not the 8k output ceiling the launch record flagged.
  - Deterministic templates matched or exceeded every AI arm at no provider cost.
- **Decision ([D005](DECISIONS.md)):** none of the four engineering gates in analysis_plan.md is met, so no method advances. Any follow-up, for example different call or token ceilings or stage-conversation design, needs a new versioned protocol. W1 data cannot serve as its holdout.
- **Not claimed:** population superiority, prospective bug discovery, diagnostic calibration or TCP benefit.

See the [results report](../../research_runs/ai_witness_2026_09/results_report.md), [frozen analysis](../../research_runs/ai_witness_2026_09/analysis/report.md) and `raw_seal.sha256`. Nothing is committed.

## Latest result — W1 preparation: NOT_READY on provider gates, 2026-09-26

The v1.1 handoff was executed through bounded preparation. [W1](../../research_runs/ai_witness_2026_09/readiness.md) now has a tested runner (`w1.py`, 39 offline tests, and a fake dry run over all 60 sessions). All four cases were restored and qualified; no exclusions. Oracles, packets, templates and the schedule were frozen before calibration. The fixed 16-attempt unchanged-test calibration found the istio control visible and no repaired-variant non-pass. Preparation used 1.2 allocated vCPU-h, USD 0 and no provider requests.

Launch is blocked only by provider gates. No W1 Claude Opus 5.5 API credential is available, so the returned model identity is unresolved. No smoke authorization is recorded, Jev's version is unrecorded and its price is unconfirmed. No measured session ran and no effectiveness claim exists. Next: the researcher supplies access and authorization per readiness.md, then the gates are re-run.

Same day, [amendment A2](../../research_runs/ai_witness_2026_09/v1_2/AMENDMENT_A2_2026-09-26.md) made design v1.2 governing. The generator is now Claude Sonnet 5 via OpenCode Zen with prompt caching, chosen by the researcher for cost; the provider timeout bound is USD 8.28. The Jev price was accepted. Later the same day the authorized smokes confirmed `claude-sonnet-5` via Zen, after two failed attempts handled as a recorded deviation, and `jev-1.13.0`. The launch record and executable freeze were written, and preflight reports **READY_FOR_MEASURED_LAUNCH**. No measured session has run; the next step is the researcher's explicit launch instruction via `v1_2/MEASURED_RUN_PROMPT.md`.

## Current routing — W1 preparation, 2026-09-25 (after C1 review)

The researcher requested a complete proposal, experiment package and coding-agent handoff for AI-assisted behavioral witness strengthening. [W1](../../research_runs/ai_witness_2026_09/v1_1/README.md) is now frozen for implementation (design v1.1 since 2026-09-26: the generator family is Claude Opus 5.5 instead of GPT-5.6 Sol, per [amendment A1](../../research_runs/ai_witness_2026_09/v1_1/AMENDMENT_2026-09-26.md); nothing else changed): four fixed historical cases, five arms (unchanged, deterministic templates, plain capable model, structured capable model, structured model plus Jev), three search replicates and independent final-candidate validation. This is a retrospective development study; the Go supplied tests are repair-backported, while POOL uses selected pre-fix tests. It is not a prospective test-discovery or demonstrated TCP-benefit claim.

Next action: execute the [W1 v1.1 coding handoff](../../research_runs/ai_witness_2026_09/v1_1/HANDOFF_PROMPT.md), complete bounded preparation and establish a separate executable launch freeze. No W1 subject runs, provider inference or measured sessions occurred during design preparation. Actual provider/model access, source restoration and runtime readiness remain unverified. The researcher reported exhausted usage; the handoff completes offline work without buying credits or silently substituting models.

This entry supersedes earlier next-work routing only. C1 observations, Q0/E1 closed gates and F1 findings remain unchanged. The earlier Jev-as-TCP-feature shortlist is not reopened by W1; Jev's incremental utility is explicitly an ablation to be tested.

## Latest result — C1 signal-validity audit: STOP, 2026-09-25

An exploratory, post hoc audit asked whether the etcd5509 C3 signal justifies a fresh confirmation study. It was offline only: no executions, no label or frozen-file changes. **Its recommendation is STOP: C4 confirmation of this signal is not pursued.** It supersedes the post-collection review's view below that the signal "supports considering fresh confirmation". The collected observations and frozen analysis are unchanged.

- **Observed:**
  - Both freezes, the raw-data seal and every chain verify. Counts reproduce: R/L P1 7/10 vs 10/10, P3 5/10 vs 7/10, all attempts 24/30 vs 26/30.
  - The whole P1 gap comes from three R cells whose first attempt passed and whose research-only retries both failed. Pooled over profiles, first attempts are not special (17/20 vs 33/40), and within-cell intraclass correlation is about 0.06.
  - P3 counts equal p³ arithmetic from the attempt rates: 5.12 and 6.51 expected; 5 and 7 observed.
  - R's attempt rate equals the historical unrestricted rate (68/85 = 0.80).
  - All 50 C1 focal dumps have the historical leaked-read-lock deadlock structure, as do 68 historical ones. The quota caused no test slowdown (0.04–0.06 s passes under both profiles), and V_ok passed 60/60.
  - The VM-to-host clock ratio shifted from about 1.07 to about 0.99 between batches. etcd7492's focal failures all fell in batch A.
- **Interpretation:**
  - With no profile effect, the frozen C3 gate would fire for etcd5509 with probability about 0.41, and for at least one of six subjects about 0.72.
  - The oracle is specific; the signal is weak statistically, not diagnostically.
  - A plausible small effect (0.80 → 0.90 per attempt) would need about 400 matched blocks (about 82 allocated vCPU-h, 3–4 times C1's measured cap) for one subject on one host.
  - Ordinary paired repetition with signatures remains sufficient (RQ3).
- **What would reopen it:** independent evidence of a large quota effect (at least 0.15 per attempt), or a new, separately designed, mechanism-derived question.
- **Budget:** the audit's 0.578649 vCPU-h is now charged to the C1 analysis stage in the resource ledger. Spent 0.581481 of 2.0; 1.418519 remains.

See the [signal-validity audit](../../research_runs/ci_configuration_2026_09/signal_audit/SIGNAL_VALIDITY_AUDIT.md) and [research record R004](../../research_runs/ci_configuration_2026_09/research_record.md). Separate W1 routing is unaffected.

## Latest result — C1 post-collection review, 2026-09-25

C1 collection is complete: 720/720 attempts, both batches. Frozen mechanical annotation and matched analysis have now run, with independent arithmetic checks. All 360 acceptable-variant attempts passed; no nuisance reduction was observed. C2 passes; the C3 development signal occurs only for etcd5509, where limited CPU increased supported blocking (P1 7/10 to 10/10; P3 5/10 to 7/10). All primary simultaneous intervals include zero. This supports considering fresh confirmation, not a confirmed configuration effect or an adaptive-system claim.

See the [post-collection review](../../research_runs/ci_configuration_2026_09/analysis_audit/POST_COLLECTION_REVIEW.md) and [mechanical report](../../research_runs/ci_configuration_2026_09/analysis/report.md). This update supersedes the earlier pending-readiness status below. No new subject run, implementation change, commit or push occurred during analysis. C4 remains unstarted.

## Current routing update — 2026-09-25

**Adopted next work:** C1, CPU configuration and defect visibility. The researcher requested design freeze and an implementation handoff. Read the [C1 entry point](../../research_runs/ci_configuration_2026_09/README.md) and [design freeze](../../research_runs/ci_configuration_2026_09/DESIGN_FREEZE.md). The design is frozen; implementation, current artifact readiness and operational launch validation remain pending. No C1 executions are claimed.

**Established prior results:** Q0/E1 closed expansion under G1b (three qualified episodes; no nuisance observed in E1). F1 reproduced Airavata score records and found small descriptive effects under the declared fault mappings, with a demonstrated aggregate-record evidence gap. See the [feasibility report](../../research_runs/ci_sensitivity_2026_09/feasibility_report.md) and [F1 report](../../research_runs/ci_sensitivity_2026_09/f1/report.md).

This dated entry supersedes the unfilled legacy routing placeholders below for near-term execution. The Jev shortlist remains deferred; no benefit is established. Prior failed gates and historical findings remain unchanged.

## Current Research Question

To be reconstructed and confirmed from the existing Airavata, HBase, and Hive research trajectory before new canonical experiments are started.

## Current Evidence

Primary existing evidence includes:

- `docs/research/change-aware-tcp-findings-2026-08.md`
- the change-aware pipeline under `pipeline/`
- historical research branches
- existing experiment outputs and reports

## Established Results

To be consolidated from reproducible prior evidence.

## Active Hypotheses

To be defined after trajectory reconstruction.

## Rejected or Unsupported Hypotheses

To be reconstructed from prior negative and inconclusive experiments.

## Open Questions

To be defined after the baseline audit.

## Next Experiments

New experiments should follow from the reconstructed research state rather than from old branch names or abandoned hypotheses.

## Research Shortlist

### Jev semantic change-to-test relevance

- Added: 2026-09-18, following user agreement to shortlist the idea.
- Status: shortlisted; exploratory playground checks completed, but no integration or canonical experiment started.
- Hypothesis: TypeSafe AI's Jev could identify semantic relationships between a code change and a test that the current path/name relevance signal misses.
- Proposed integration: score a diff against test context and add the resulting relevance score as a feature in the existing prioritization pipeline.
- Prerequisite: complete trajectory reconstruction and the baseline evidence audit before defining a canonical experiment.
- Candidate comparison: history alone, history + current relevance, and history + current relevance + Jev, using a bounded offline temporal evaluation. Assess incremental ranking quality, latency, and cost.
- Evidence threshold: retain only if it adds measurable value over the cheap relevance baseline; existing findings suggest recurring/flaky failures limit the available gains. No benefit from Jev on this project's data has been established.
- Validity and reproducibility: use only context available before each evaluated test run; cache exact requests and responses and record model versions. Treat confidence as a model judgment, not an established test-failure probability. Assess possible foundation-model training contamination on historical repositories; causal request inputs alone do not rule it out. Any future-outcome labels remain retrospective evaluation oracles only.
- References: [TypeSafe documentation](https://docs.typesafe.ai/introduction), [launch announcement](https://typesafe.ai/blog/introducing-system-one-models-and-jev), and [existing project findings](change-aware-tcp-findings-2026-08.md).

#### Exploratory playground observations (2026-09-20)

- **Observed:** On a synthetic retry-boundary example, Jev distinguished a test of the modified boundary (1.99/2), a test of an unchanged case in the same function (0.99/2), and an unrelated test (0/2) across two playground calls.
- **Observed:** On a summarized real [Apache Commons Pool POOL-162 fix](https://github.com/apache/commons-pool/commit/674a6ba9877d2de7224306c83e7871e1eddeab93) with three test methods present at the [pre-fix parent](https://github.com/apache/commons-pool/tree/280c60ac3e918eb7fe8fb542847913bb5317cbc6/src/test/org/apache/commons/pool/impl), Jev `jev-1.13.0` scored `TestGenericObjectPool.testWhenExhaustedBlock` = 1/2, `TestGenericKeyedObjectPool.testWhenExhaustedGrow` = 1/2, and `TestStackObjectPool.testBorrowFromEmptyPoolWithNullFactory` = 0.01/2. The rubric's level 1 meant use of a changed implementation without interrupting a waiting borrower; level 0 meant an unrelated implementation. Playground request ID: `playground_1a1b009856466f44481af269f9ae45cde70`; reported usage: 852 input tokens, 46 output tokens, 116.7 ms evaluation time.
- **Interpretation and limit:** The observed classifications match the supplied rubric. None of those pre-fix tests exercises the interrupted-waiter behavior; the direct witness was added in the fix commit and cannot be treated as a prospective candidate. The state was a human summary of the patch and test methods, not raw source. This probe has no observed test outcomes, no T0 comparison, and no evidence of incremental TCP benefit. Reported timing is one API evaluation, not an end-to-end latency benchmark.
