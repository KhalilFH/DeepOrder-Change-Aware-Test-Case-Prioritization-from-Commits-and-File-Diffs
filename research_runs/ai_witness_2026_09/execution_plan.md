# W1 implementation, calibration and launch plan

## Material Passport

- Date: 2026-09-25. Execution specification only; no runner or provider access is asserted.
- Preparation and measured work have separate authority. HANDOFF_PROMPT.md authorizes preparation, not measured sessions.

## Phase 0 — inventory and isolation

Verify DESIGN_FREEZE.sha256. Read the four research routing records and record current Git status without cleaning, committing or modifying unrelated work. Create a study-local preparation ledger before any build. Inventory available source archives/images, toolchains, Docker/runtime and host allocation read-only. Preserve all earlier experiment directories.

Use an isolated `w1_harness/` package and outputs under this study directory; no refactoring of historical harnesses is required. Reuse pure utilities only after verifying their assumptions, especially causal labels and focal oracles. A reference imported from a historical module is part of the launch hash set.

Bind the study to a verified 16-logical-CPU execution environment, fixed Go GOMAXPROCS=16, no CPU-bandwidth limitation, one subject process at a time. Record memory, affinity, CPU quota, host/VM identity and background-load checks. This holds the old unrestricted Go environment approximately comparable without creating another CPU-treatment experiment. Do not change host allocation automatically to satisfy this gate; report NOT_READY if unavailable. Java uses the same allocation; record its runtime processor observations. Charge allocated CPU capacity, not a mislabeled CPU-utilization measurement.

## Phase 1 — restore and qualify

Restore only the four registered cases, at most three build invocations per case under the common preparation cap. Required dependency/source retrieval and paired compatibility fixes are permitted; record every command and failed invocation. A build invocation may compile both variants under a declared script; retries count separately. Never repeatedly rebuild or rerun until an attractive defect frequency appears.

Produce a source dossier, common method packet, static extraction and B1 applicability/bindings for each case. Verify identical supplied tests and only the intended production differences between variants. A missing artifact, unresolved oracle or incompatible toolchain is an exclusion reason. Null historical failure counts are not exclusions.

Specify a frozen focal oracle per case: exact observable premise, consequence, permitted trace evidence, unacceptable nonfocal outcomes and completeness requirements. It must handle changed tests, not just recognize a historical test name. Validate the classifier offline using synthetic positive and negative trace fixtures, including a generic timeout, unrelated assertion failure, missing prerequisite, and a repaired-variant failure. Synthetic fixtures test classifier logic; they are not real positive controls or defect observations.

Create the full four-case randomized schedule before observing fixed calibration. Once exclusions are decided, keep excluded rows marked excluded. Do not regenerate an advantageous order. Freeze the scheduler backend/applicability from structural compatibility, not defect yield.

## Phase 2 — offline implementation checks

Implement source packet isolation, test-only overlay checks, provider interfaces, typed judgment parsing, resource admission, paired execution, final submission sealing, independent validation, artifact contracts, analysis, and safe interruption/resume. Provide fake provider and fake subject backends. No credentials, provider calls or subject containers in `--dry-run` or offline tests.

Required meaningful checks:

- Correct patch and paired-source identity enforcement; forbidden production edit and variant-identity access rejected.
- Budget/deadline admission counts failed provider calls, retries, compilation and cleanup; no work starts without reservation.
- Interrupted in-flight provider request or test attempt becomes indeterminate, never silently retried or counted twice; stable IDs prevent duplicate submission.
- Fixed schedule determinism and complete 4 × 5 × 3 design; exclusions preserve rows and matched identities.
- Final patch hash seals before validation; attempts reuse identical overlays across variants.
- Validation cannot pass with a repaired failure, only one focal triplet, unrelated timeout, missing record or malformed trace.
- P1/P3/P3-retain calculations distinguish chronological visibility from eventual evidence retention.
- Source and response leakage between sessions is blocked; a dry-run proves the rendered packet excludes held-out materials.

The mock path must cover B0–B4 end to end, including malformed Jev output and provider version drift. The tool/SDK choice is an implementation decision; consult current Context7/official documentation for actual library APIs. Avoid new infrastructure when the existing runtime suffices.

## Phase 3 — bounded calibration and provider qualification

For each structurally qualified case run the unchanged supplied test **twice per variant**: four attempts per case, maximum 16. Fixed order is in the sealed calibration schedule. A repaired-variant nonpass blocks that case pending an explicitly documented structural correction or exclusion; it is not a license for extra unregistered smoke attempts. A defective-variant pass is allowed. Keep all records separate from measured data.

The preparation agent may complete restoration and all mock work while live provider use is unavailable. Do not purchase credits, consume a reset, open more research agents, or use a coding-agent conversation as an experimental provider. At most one **synthetic, non-case** smoke request per provider is allowed once existing access and explicit live-smoke authorization have been recorded in launch settings. If that authorization or access is absent, report the remaining provider gate as NOT_READY after completing independent preparation. This distinction respects the researcher's report of exhausted usage while making the implementation reviewable.

Provider qualification binds transport, requested model, returned identity/version, generator reasoning/temperature/seed settings where supported, typed output schema, context limits, prices and call/time/token enforcement. Unsupported seed or reasoning controls are recorded as unsupported, not simulated. Freeze one configuration for every capable-model arm. The session request budgets count actual network requests; do not hide multiple backend requests under one orchestration call. Synthetic smoke results do not establish real-code classification quality.

## Phase 4 — budget projection and executable freeze

The preparation subcap is 80 allocated vCPU-hours within the 400-hour study cap. Other study ceilings: 80 human hours, USD 300 provider charge, 200 generator requests, 500 Jev atomic evaluations, 4 million input tokens. Each AI session has an additional USD 8 ceiling. These are hard ceilings, not estimated costs or authority to purchase resources. Track preparation, smoke, search, validation and analysis separately; do not charge C1 retroactively or use its unspent allocation.

Maximum four-case workload: 60 search sessions (10 hours of elapsed search allowances), 1,800 independent validation attempts, and 16 calibration attempts. Maximum scheduled search generation requests: 132; maximum Jev atomic evaluations: 96. These exclude allowed provider smoke and failed-call accounting. Build and analysis costs are additional within the study cap.

Produce both an expected cost projection using the fixed calibration/build observations and a full timeout-bound projection. The expected remaining allocated-CPU cost plus 20% headroom must fit the remaining study cap to launch. Report explicitly if the timeout-bound cost exceeds the cap; a slow or failing study may stop incomplete. Do not disguise expected cost as a guaranteed worst-case reservation. If expected cost fails, do not shrink a method, validation count or roster to fit after seeing outcomes; propose a versioned budget/design amendment.

Reserve the configured outer timeout plus cleanup at 16 CPUs before each primitive execution, and reserve maximum configured request cost/tokens before each provider request. Admit a search pair only when both variants' timeout and cleanup allowances fit the remaining session deadline; never start only the promising half of a pair. Builds and provider requests likewise have bounded deadlines within the session. Release unused reservations only after final accounting. A provider without bounded price/usage exposure blocks launch. Study charge is execution-environment reserved capacity × elapsed allocated time, including provider waiting while capacity remains reserved; separately record observed CPU utilization if available. Avoid double-charging nested intervals. Cap overruns caused by measurement delay are reported, not erased. Human hours may be declared estimates but must be labeled.

Write `readiness.md` with PASS/FAIL/UNKNOWN for each gate and evidence paths. READY requires all five arms usable, minimum roster, offline checks, completed fixed calibration, qualified model identities, packet isolation, full schedule, oracles, price/resource projection, and validated non-executing preflight. Create `launch_record.md`, `launch_config.json`, and `FREEZE.sha256` only after gates pass. Null design placeholders remain unchanged; resolved runtime values belong in launch_config.json.

The executable freeze includes code/imported helpers, concrete commands, source and image digests, input packets, bindings/templates, rendered prompts, provider configs without secrets, oracles/fixtures, schedules, exclusion decisions, check reports and design-manifest digest. List all covered files explicitly. Never hash an output file that the verifier later overwrites in place. Do not freeze secrets or mutable event logs; seal measured raw data separately at completion.

**Stop before measured search.** Return exact tested preflight and launch commands only after the implementation exists. NOT_READY with completed code and a precise failing gate is a valid handoff result.

## Phase 5 — measured work after launch instruction

Reverify both freezes and remaining budgets before the first measured call. Execute the immutable schedule serially. Seal all five method submissions in a case/round, then run fixed independent validation for them. Do not use validation to tune subsequent replicates. Persist attempts and request events as they happen.

There is no success/futility stop based on effect size. Pause on hash drift, provider version change, source leak, unsafe cleanup, unexplained repaired-variant infrastructure failure, or exhausted resource reservation. Preserve partial records. An ordinary invalid candidate/repaired assertion failure is a method outcome, not automatically a global infrastructure failure. Resume only when the same contract and provenance remain valid; uncertain completed requests/attempts stay indeterminate without free reruns. Missing scheduled rows remain in denominators. No silent continuation with another model.

At completion or terminal stop, seal raw records, run the frozen analysis and audit traceability from every reported result to request/patch/attempt hashes. Report partial-study limits rather than producing a best-case subset as the headline.
