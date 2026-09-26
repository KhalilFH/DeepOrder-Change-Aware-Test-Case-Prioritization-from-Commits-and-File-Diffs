# W2A v0.1 — execution feasibility before witness effectiveness

## Material Passport

- Date: 2026-09-26. Status: **PROPOSED; not frozen, implemented or executed**.
- Basis: researcher's request to examine W1 and push the experiment forward; [offline W1 audit](../../ai_witness_2026_09/postrun_audit/REVIEW.md).
- Research exposure: W1 outcomes and all four cases are known. This is a development pilot, never a holdout or W1 rerun.
- Generator: Claude Sonnet 5 through OpenCode Zen, requested/returned identity `claude-sonnet-5`, subject to launch verification. Historical GPT/Opus choices do not describe W1 or this proposal.
- All numerical caps and engineering gates below are proposals. Freeze the complete implementation, inputs and schedule before collection; do not adapt them within a batch.

## Question and hypothesis

Can a source-grounded plain agent and a structured agent each complete the read–propose–build–run–seal workflow within explicit small budgets?

Hypothesis: carrying source evidence between stages, checking structured outputs, and reserving enough interaction for generation will increase workflow completion relative to the failure pattern observed in W1. W2A changes several engineering components together and cannot identify their individual effects or establish method superiority over W1.

## Fixed development roster and arms

Use all four W1 development cases: pool162, grpc1859, k8s26980, istio17860. One session per case per arm, eight sessions total, no replacement or free rerun. Preserve POOL's pre-fix-candidate stratum and the Go repair-backported stratum. One session is a smoke-level feasibility observation, not a reliable success-rate estimate.

- **F2:** plain Sonnet agent, source packet and common tools.
- **F3:** same Sonnet agent with a prerequisite plan and explicit source-linked judgment table, then generation.

Keep model settings, packet construction, edit restrictions, resource accounting, primitive tools and final validation identical across arms except for the structured reasoning procedure. F3 pays for planning and judging inside the same total budget. Record any actual tool-set differences by stage. No Jev in this initial batch. W1 B0/B1 results remain historical context, not concurrent controls for a W2A effectiveness claim.

## Engineering changes to prepare and check offline

1. **Deterministic context completeness.** Include entry-point helper bodies using a declared, bounded direct-callee rule, identically in F2/F3. Record truncation and file/range hashes. Do not hand-select helpful lines using oracle or outcome knowledge. gRPC's wrapper/helper example must be covered by a regression check.
2. **Transfer evidence across stages.** Maintain an append-only source-read cache with exact file/range/content provenance. F3's later stages receive earlier permitted source results, the validated plan and the judgment table. Use a fixed serialization and token admission rule. This is a new method implementation; do not silently call it W1's old prompts.
3. **Validate completion locally.** Require nonempty well-formed plans with bounded unique claim IDs and usable source spans; require exactly one judgment per claim. Preserve explicit `unknown` separately from missing judgments. Treat truncated/empty outputs as invalid stage output, give bounded corrective feedback, and charge every retry to the same limits. Never interpret an empty tool object as completed reasoning.
4. **Expose tool state and errors.** Show current proposal IDs, legality, build state, run counts and remaining budget. Return build-before-run failures explicitly. Keep build/run primitives and error semantics identical across arms. Do not invent a successful build or execute an undeclared automatic test run.
5. **Reserve generation and finalization.** Proposed F3 stage allocation: planner at most two model calls, judge at most two, generation at least eight of twelve total if earlier stages consume their maximum. Unused stage calls transfer forward. Carry a separate source cache rather than discarding read results. Reserve the last available model call for an explicit final decision; no silent fallback to unchanged. Reserve admission headroom for that final request before discretionary earlier requests. If a mandatory stage remains invalid, record a visible stage failure; do not relabel a plain fallback as F3.
6. **Handle output limits deliberately.** Log response stop reason, local schema validation, provider input/cache/output use, and admission-denial subtype. A `max_tokens` response is incomplete for stage acceptance even if a partial tool object exists. Stage completion requires a complete response and locally valid content. Do not execute partial patch calls.
7. **Keep validation separate.** Final selection is sealed before independent validation; private focal-oracle feedback is unavailable during search. Preserve test-only edits, variant-identical overlays, cleanup checks, provider identity checks and resource reservations. Any new test-side evidence/oracle contract must be specified and tested before freezing; never relax it after seeing pilot outputs.

Use a separate W2A implementation directory, output root and ledger namespace. Do not modify or refreeze W1. Read-only reuse of immutable W1 subject artifacts is allowed with hashes; provider requests must use only the permitted case packets, not this audit, private oracles, historical traces or human solutions.

## Proposed limits and launch checks

| Resource | Per session | Eight-session batch |
|---|---:|---:|
| Model requests, including repair | 12 | 96 |
| Input tokens, including cache reads/writes | 240,000 | 1,920,000 |
| Output tokens, including thinking | 24,000 | 192,000 |
| Maximum output per request | 4,000 | — |
| Provider USD | 1.00 | 8.00 |
| Search wall time | 600 seconds | 4,800 seconds |
| Patch proposals | 4 | 32 |
| Paired search executions | 6 | 48 |
| Jev evaluations | 0 | 0 |

Retain the 600-second wall budget initially: W1 AI sessions did not exhaust it. The larger call/token ceilings are engineering proposals, not empirically established sufficient budgets. Project worst-case input reservations from the actual serialized packets and retained context before declaring launch readiness; pooled budget headroom does not guarantee a stage can be admitted.

At **W1's recorded pricing snapshot**, charging all input at its most expensive cache-write rate gives 0.240M × USD 2.50 + 0.024M × USD 10 = USD 0.84 per session, USD 6.72 for eight. This is an illustrative token-price bound under that snapshot, not a current quote or an account-debit guarantee. Verify actual pricing, identity, output behavior and account availability before launch. Include any authorized smoke costs in the new ledger and an explicit preparation allowance; no automatic credit purchase.

Allocated execution cap proposal: 160 vCPU-hours for measured search and validation, plus 4 vCPU-hours preparation. At 16 allocated CPUs, all eight 600-second searches are 21.34 vCPU-hours. Thirty validation attempts per final at the existing case-specific outer-plus-cleanup bounds (90, 150, 120 and 90 seconds) total at most 120 vCPU-hours across eight finals: 2 arms × 30 attempts × (90 + 150 + 120 + 90) seconds × 16 CPUs / 3,600. Paired validation builds add 6.4, leaving approximately 12.26 hours within the measured cap for declared overhead. Recompute against the actual backend accounting and image readiness before freeze. This is a conservative limit, not an expected cost. Stop visibly if reservations fail; no silent cap extension.

## Collection and analysis

Generate and save a deterministic randomized arm order within each case from a declared seed before launch. Seal both case finals before either is independently validated. Use the existing five-triplet-per-variant validation rule for every legal buildable final, with fresh containers and private focal classification. Invalid/no-submission sessions stay in the eight-session denominator.

Primary feasibility table, per case and arm:

- plan/judgment completeness (F3), legal nonempty patch proposed, built on both variants, paired execution completed, final sealed;
- unchanged versus modified final; validated witness outcome is reported separately;
- call/token/time/cost consumption and exact terminal reason, including output truncation and admission failures;
- evidence-transfer and finalization checks.

Report stage attrition counts. No hypothesis tests, population intervals, diagnostic accuracy, or comparison of pilot yield with W1 as if randomized contemporaneously. Do not pool repeated executions as independent cases.

## Proposed gates and next research step

1. **Offline readiness:** deterministic tests demonstrate helper inclusion, cross-stage source transfer, rejection of empty/truncated plans, judgment coverage, build-before-run errors, budget reservation for finalization, and separation of private oracle material. A fake end-to-end eight-session run must preserve schedule, counters, sealing and validation ordering. Fake-provider success is not live-model feasibility evidence.
2. **Live workflow feasibility:** all eight sessions have complete terminal accounting; each arm seals a final on at least three of four cases and completes a legal nonempty patch → paired build → paired execution → final seal on at least two noncontrol cases. These are proposed investment thresholds, not efficacy claims. Retaining the unchanged istio control is acceptable but cannot satisfy modified-candidate gates.
3. **If gate 2 fails:** preserve the entire batch and diagnose remaining stage failures. Any revision gets a new version and a new batch; do not extend losing sessions.
4. **If gate 2 passes:** prepare a separate effectiveness study with concurrent unchanged/template/plain/structured controls. Add Jev only through an explicit structured-versus-structured-plus-Jev comparison, including its input-context and cost differences. Establish validated modified witnesses before claiming utility. Fresh-case confirmation requires separately selected cases and a frozen protocol; W1 and W2A cases remain development data.

The next concrete implementation task is steps 1–7 and offline gate 1. Launch readiness requires the resulting executable design and budget checks, not merely this proposal. This document makes no claim that W2A has run or that any AI method has advanced.
