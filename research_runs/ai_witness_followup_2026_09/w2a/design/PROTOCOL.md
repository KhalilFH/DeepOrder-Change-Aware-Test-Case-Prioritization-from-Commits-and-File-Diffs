# W2A protocol v1.0 — execution-feasibility pilot

## Material Passport

- Date: 2026-09-26. Status: **design frozen; executable package prepared offline; not launched**.
- Basis: [W1 audit](../../../ai_witness_2026_09/postrun_audit/REVIEW.md), [proposal v0.1](../../v0_1/PROPOSAL.md) and [DESIGN_CHANGES.md](DESIGN_CHANGES.md).
- W1 is closed under D005. W2A is a separate study with its own configuration, identifiers, ledgers and outputs. It is neither a W1 rerun nor a W1 amendment.
- Exposure: W1 cases, traces and outcomes are known to the designers. All four cases are **development data, never a holdout**.

## Question and hypothesis

**Question.** Can a source-grounded plain agent (F2) and a structured agent (F3) each complete the read → propose → build → run → seal workflow on four known cases within explicit small budgets?

**Engineering hypothesis.** The following changes together increase workflow completion relative to W1's recorded failure pattern:

- deterministic helper context;
- source evidence carried between stages;
- local validation of stage outputs;
- explicit tool-state feedback;
- discarding truncated responses;
- a reserved final call.

W2A changes these components jointly. It cannot identify their individual effects, and it does not compare methods for effectiveness.

## Fixed design

| Element | Value |
|---|---|
| Cases | pool162 (pre-fix-candidate stratum), grpc1859, k8s26980 (Go repair-backported stratum), istio17860 (control) |
| Arms | F2 plain agent; F3 planner → judge → generator |
| Sessions | 4 cases × 2 arms × 1 = **8**; no replacement, no free rerun |
| Generator | Claude Sonnet 5 (`claude-sonnet-5`) via OpenCode Zen, adaptive thinking, effort medium, identical in both arms |
| Jev | none |
| Per session | 600 s wall; 12 model calls; 640k input and 24k output tokens (cache-inclusive, thinking included); 4,000 output tokens per request; USD 1.00; 4 patch proposals; 6 paired runs |
| Reserved final call | 1 call, 4,000 output tokens, 120 s, an input bound; only `submit_final` executes in it |
| F3 stage caps | planner ≤ 2 calls; judge ≤ 2 calls; generation receives the rest (≥ 8 of 12 including the final call) |
| Validation | W1 rule unchanged: five matched triplets per variant (15 + 15 attempts) for every legal buildable final; fresh containers; private W1 focal oracles |

`schedule.json` (seed 2026092602) fixes the case order, the F2/F3 order within each case, the validation order, the search-pair first variants and the validation triplet seeds. Both finals of a case are sealed before either is validated. Execution is serial.

## Information and isolation

**Shared inputs.** Both arms receive the same inputs:

- W1's immutable per-case packet: production diff, allowed files, T0 extraction and W1 template bindings;
- the fixed helper definitions;
- the same tools, edit contract, feedback truncation and budgets.

F3 additionally receives its own stage outputs and carried source evidence; F2 keeps its own single conversation.

**Withheld from every model request:**

- W1 outcomes, audits and traces;
- oracle code and specifications;
- the POOL repair-added test;
- issue text and human diagnoses.

The harness screens every harness-authored text block for held-out markers and stops for review on a hit. Model sessions never see validation results or other sessions' artifacts.

## Terminal accounting

Every session ends with exactly one recorded terminal reason:

- `SEALED_DISCRETIONARY`
- `SEALED_FINAL_CALL`
- `FINAL_NO_SUBMIT`
- `FINAL_TRUNCATED`
- `FINAL_REJECTED`
- `FINAL_NOT_ADMITTED`
- `FINAL_PROVIDER_FAILURE`
- `STAGE_FAILURE_PLAN`
- `STAGE_FAILURE_JUDGMENT`
- `PROVIDER_REFUSAL`
- `PROVIDER_DRIFT`
- `INTEGRITY_STOP`
- `INTERRUPTED_INDETERMINATE`

A session without a sealed final is NO_SUBMISSION and stays in the denominator. It is never replaced by the unchanged overlay.

## Stop, pause and resume

Pause the run on any of:

- returned-model drift;
- a leak-marker hit;
- sandbox or cleanup failure;
- an exhausted study reservation.

A paused run keeps all partial records. Resume only through `run --resume-review`; in-flight work becomes UNRESOLVED and is not rerun. There is no success or futility stopping. An ordinary invalid candidate or a repaired-variant assertion failure is a method outcome, not an infrastructure failure.

## Amendments

Changing the roster, arms, information, budgets, model, prompts, validation or gates requires a dated amendment and a new design version, with v1.0 bytes preserved. If a problem appears mid-batch, the batch is completed or paused, never adapted. Any revision after this batch gets a new version and a new batch (ANALYSIS_PLAN.md).

## Not claimed

W2A makes none of these claims:

- effectiveness or superiority of any method;
- a comparison with W1 as if contemporaneous or randomized;
- population inference from four exposed cases;
- prospective bug discovery;
- diagnostic calibration;
- a TCP benefit.

One session per case and arm is a smoke-level feasibility observation, not a success-rate estimate.
