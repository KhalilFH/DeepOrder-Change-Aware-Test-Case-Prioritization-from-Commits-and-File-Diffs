# Experiment Registry

Record material experiments here.

### EXW2A — AI witness workflow feasibility pilot (preparation), 2026-09-26

- **Status:** design v1.0 and executable package frozen offline; **not executed**. No provider requests, smoke or subject runs.
- **Question:** can F2 (plain) and F3 (structured) Claude Sonnet 5 agents complete read → propose → build → run → seal on the four W1 development cases within bounded budgets? This is a feasibility question, not an effectiveness question.
- **Design:** 4 cases × 2 arms × 1 session.
  - Per session: 600 s, 12 calls (one reserved for the final call), 640k input and 24k output tokens, USD 1.00, 4 patch proposals, 6 paired runs.
  - W1 validation: 5 matched triplets per variant.
  - Seed 2026092602.
- **Gates:** Gate 1 (offline readiness) passed. Gate 2 (live feasibility): each arm seals on ≥ 3/4 cases and completes the modified workflow on ≥ 2 of 3 noncontrol cases.
- **Offline results (observed):** 24/24 tests; W1 failure regressions R1–R9 passed; fake 8-session dry run passed; render leak check passed; limit check passed; W1 audit reproduced byte-identically; Docker 16 CPUs with all 8 pinned images present.
- **Limit check:** W1 admission estimate/actual 1.19–1.50; context growth median 1.9k and p90 6.3k estimated tokens per call; output mean 1,139.
  - At 240k, F3 cannot start on pool162.
  - At 640k, F2 keeps 11 discretionary calls and F3 7–8 generation-stage calls.
  - vCPU timeout bound 147.73 of 160.
- **Cost bounds (proposed):** provider ≤ USD 8.10 (about USD 3–4 projected); ≤ 98 generator requests; allocated CPU ≤ 160 vCPU-h measured. Preparation used USD 0 and 0 vCPU-h.
- **Commands:** `python research_runs/ai_witness_followup_2026_09/w2a/w2a.py prepare`, `package-freeze`, `preflight`. The launch sequence is in [EXECUTION_PLAN.md](../../research_runs/ai_witness_followup_2026_09/w2a/design/EXECUTION_PLAN.md).
- **Artifacts:** [README](../../research_runs/ai_witness_followup_2026_09/w2a/README.md), [readiness](../../research_runs/ai_witness_followup_2026_09/w2a/readiness.md), [design](../../research_runs/ai_witness_followup_2026_09/w2a/design/README.md), `prep/`.

### EXW1-AUDIT — Post-collection execution trace review, 2026-09-26

- Offline analysis only; no new subject/provider execution. Reproducer: `python research_runs/ai_witness_2026_09/postrun_audit/audit.py`.
- Verified existing raw/executable/design hashes and ledger chains; all 60 endpoint labels and 28 complete policy summaries reproduce. All 119 measured model responses identify `claude-sonnet-5`.
- Corrections: six input-admission denials, one output-admission denial, four `max_tokens` responses; initial excerpts do not fully cover any of the 54 requested source ranges. gRPC helper context is re-requested across fresh stages. Two empty plans and one empty judgment list pass stage capture; the sole AI patch is an invalid placeholder.
- Interpretation: preserve W1's null advancement; distinguish workflow failure from scientific evidence against the method. A separate eight-session W2A feasibility proposal is prepared, not frozen or executed.
- Artifacts: [audit](../../research_runs/ai_witness_2026_09/postrun_audit/REVIEW.md), [W2A proposal](../../research_runs/ai_witness_followup_2026_09/v0_1/PROPOSAL.md).

## Entry format

### EXXXX — Experiment name

- Date:
- Commit:
- Branch:
- Research question:
- Hypothesis:
- Dataset / subject:
- Inputs:
- Configuration:
- Command:
- Evaluation protocol:
- Metrics:
- Result:
- Interpretation:
- Limitations:
- Artifacts:

### EXC1 — CPU configuration and defect visibility

- Date: 2026-09-25; status: design frozen, not executed.
- Baseline commit: `3f984da9095d19afc239a91945043758da43deec`; branch: `research/revival-2026` at design preparation.
- Question: does CPU bandwidth limitation change supported detection of known product defects, including its interaction with accept-on-pass retry?
- Subjects: fixed six prior Go pairs; enrollment requires structural validity, not a pass/fail-rate window.
- Configuration: unrestricted R versus two-CPU-bandwidth L on a verified 16-CPU VM, fixed GOMAXPROCS=16, P1/P3/P3-retain.
- Design: ten matched blocks per subject, four profile/variant cells, three attempts/cell; 720 measured attempts if all six enroll.
- Metrics: paired supported-blocking contrasts, missingness bounds, evidence retention, nuisance where independently established, and cost.
- Result: none. No implementation, runtime checks, calibration or measured runs performed by the design-freeze pass.
- Command: pending implementation and validation; no executable CLI is asserted.
- Artifacts: [C1 package](../../research_runs/ci_configuration_2026_09/README.md), [analysis plan](../../research_runs/ci_configuration_2026_09/analysis_plan.md).

#### EXC1 completion update — 2026-09-25

- Status: 720 scheduled attempts already collected across batches A/B; post-collection annotation and frozen analysis completed and independently checked.
- Identity: design 8/8 and executable launch freeze 71/71 match. Raw measured hashes unchanged; no implementation edits.
- Result: C2 passes; C3 signals for etcd5509 P1/P3 only, in the direction of greater blocking under CPU limitation. All primary simultaneous intervals include zero. Acceptable variants passed 360/360; nuisance reduction remains unmeasured.
- Interpretation: descriptive pilot and a fresh-confirmation candidate; no population or adaptive-assessor claim.
- Artifacts: [review](../../research_runs/ci_configuration_2026_09/analysis_audit/POST_COLLECTION_REVIEW.md), [frozen analysis outputs](../../research_runs/ci_configuration_2026_09/analysis/report.md), [independent arithmetic](../../research_runs/ci_configuration_2026_09/analysis_audit/independent_verification.json).

### EXW1 — AI-assisted behavioral witness strengthening

- Date: 2026-09-25; status: design frozen for implementation, not experimentally executed.
- Preparation HEAD: `721d885a315a2c0ef26a82f2613248a4abcc110c`, with existing uncommitted research work preserved.
- Question: does source-linked prerequisite analysis improve test-strengthening yield/cost beyond a strong plain model, and does Jev add incremental value?
- Fixed roster: pool162, grpc1859, k8s26980, istio17860; at least three structurally qualified projects, including two noncontrol cases, required. No rate-based enrollment or replacements.
- Inputs: retrospective production repair pairs and supplied tests, with explicit distinction between pre-fix POOL candidates and repair-backported Go tests. Held-out oracle material is excluded from measured method packets.
- Design: B0 unchanged, B1 deterministic templates, B2 plain capable model, B3 structured capable model, B4 structured model plus Jev; three search replicates, 600 seconds per session; five independent triplets per variant for each legal buildable final candidate.
- Metrics: independently validated witness yield per case, capped time to validated submission, full costs, P1/P3/P3-retain visibility and missingness. Four known development cases do not support population inference.
- Result: none. Design documents, configuration, artifact schema, integrity verifier and handoff prompts prepared; no W1 implementation, calibration or measured/provider runs.
- Amendment: 2026-09-26, design v1.1 ([A1](../../research_runs/ai_witness_2026_09/v1_1/AMENDMENT_2026-09-26.md), D003): requested generator family changed from GPT-5.6 Sol to Claude Opus 5.5; nothing else scientific changed; no outcomes existed. The v1 package is preserved and superseded.
- Command: `python research_runs/ai_witness_2026_09/v1_1/verify_design.py` verifies the v1.1 design and v1 integrity only; executable experiment commands await implementation.
- Artifacts (v1.1): [package](../../research_runs/ai_witness_2026_09/v1_1/README.md), [protocol](../../research_runs/ai_witness_2026_09/v1_1/protocol.md), [analysis](../../research_runs/ai_witness_2026_09/v1_1/analysis_plan.md), [coding handoff](../../research_runs/ai_witness_2026_09/v1_1/HANDOFF_PROMPT.md). Superseded [v1 package](../../research_runs/ai_witness_2026_09/README.md).
- Preparation (2026-09-26): implementation, restoration (4/4 qualified), frozen oracles/packets/templates/schedule, 39 offline tests, fake dry run and fixed calibration (16/16; istio V_bad focal 2/2, all else PASS) complete. Status NOT_READY: generator access/identity, Jev identity, smoke authorization and Jev price unresolved. No measured or provider runs. See [readiness](../../research_runs/ai_witness_2026_09/readiness.md).
- Amendment A2 (2026-09-26, design v1.2, D004): requested generator family changed from Claude Opus 5.5 to Claude Sonnet 5 (via OpenCode Zen, prompt caching) to lower cost. Nothing else scientific changed. Only the model-free calibration existed. Governing design and verifier: `research_runs/ai_witness_2026_09/v1_2/`.

#### EXW1 completion update — 2026-09-26

- **Status:** measured run COMPLETE.
  - Coverage: 12/12 blocks, 60/60 sessions, 60/60 validations.
  - Run: 08:52–10:09Z. No pause, resume, rerun or amendment.
  - Code: branch `research/revival-2026` at HEAD `e7920ac`; W1 files uncommitted and bound by `FREEZE.sha256`.
  - Before launch: authorized smokes confirmed `claude-sonnet-5` via OpenCode Zen and `jev-1.13.0`; preflight READY_FOR_MEASURED_LAUNCH.
- **Command:** `python research_runs/ai_witness_2026_09/w1.py run --authorize "<researcher instruction>"`, then `w1.py analyze`.
- **Identity:**
  - Design v1.2 17/17 (chained v1.1 17/17, v1 16/16) and executable freeze 181/181 match, both before and after the run.
  - Raw collection sealed in `raw_seal.sha256` (1,962 files) before analysis.
  - Event chain (2,152) and resource chain (3,338) intact.
  - Labels, table, policy counts and witness trace hashes independently recomputed; all match.
- **Result (validated witnesses out of 3):**

  | Case | B0 | B1 | B2 | B3 | B4 |
  |---|---|---|---|---|---|
  | pool162 | 0 | 3 | 0 | 0 | 0 |
  | grpc1859 | 2 | 0 | 0 | 0 | 0 |
  | k8s26980 | 0 | 0 | 0 | 0 | 0 |
  | istio17860 (control) | 3 | 3 | 3 | 0 | 0 |

  - No AI arm sealed a synthesized test. All four B2 finals were the unchanged overlay. 32/36 AI sessions ended with NO_SUBMISSION (call caps or the cache-inclusive input ceiling), and 1 AI patch was proposed in 36 sessions.
  - B1's T3 template is the only synthesized witness (15/15 focal failures per replicate).
  - grpc1859's unchanged-test witnesses gave P3 blocking in 0/5 triplets and P3-retain in 3–4/5.
  - No invalid candidates, exclusions or missing outcomes.
- **Cost:** about USD 3.34, 119 generator requests, 1.33M input tokens, 71 Jev evaluations and 20.0 allocated vCPU-h, all within caps. Human hours were not measured.
- **Interpretation:**
  - The frozen AI harness was infeasible for Claude Sonnet 5 under these ceilings. The B3−B2 and B4−B3 contrasts are therefore uninformative, not negative.
  - No engineering gate is met (D005).
- **Limitations:** four familiar cases, one generator configuration, no controlled scheduler, and repair-backported Go tests.
- **Artifacts:** [results report](../../research_runs/ai_witness_2026_09/results_report.md), [frozen analysis](../../research_runs/ai_witness_2026_09/analysis/report.md), [launch record](../../research_runs/ai_witness_2026_09/launch_record.md), `raw_seal.sha256`, `measured/`.
