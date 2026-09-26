# W2A design v1.0 — changes relative to proposal v0.1

## Material Passport

- Date: 2026-09-26. Compares this design with [PROPOSAL.md](../../v0_1/PROPOSAL.md) (preserved unchanged).
- Evidence: offline only. The limit check (`prep/budget_check.json`) renders the actual W2A requests and replays W1's recorded requests, responses and ledger read-only. No provider request, smoke or subject execution informed any change.
- W2A outcomes did not exist when these choices were made. Every choice below is fixed before collection.

## Material changes

### MC1 — Session input-token cap: 240,000 → 640,000 (batch 1.92M → 5.12M)

**Finding.** The proposal's 240k cap cannot deliver its own call allocation (12 calls, planner ≤ 2, judge ≤ 2, generation ≥ 8) once the reserved final call is protected:

- The actual rendered first requests are 7.2k–21.7k estimated tokens (pool162 largest); W1 context grew by a median 1.9k and p90 6.3k estimated tokens per call.
- The local admission estimate overstated provider-reported input by 1.19–1.50× in all 119 W1 requests, and cache reads count toward the cap, as in W1.
- At 240k, F3 on pool162 cannot even admit its planner once the final call and the first generation request are reserved at their upper bounds. With W1-typical stage sizes, the smallest F3 generation stage is one call (the final call only).

**Change.** 640k is the output of a declared rule (`budget.derive_input_cap`): the smallest multiple of 40k at which input tokens do not bind for any case or arm, at W1 p90 growth, W1-typical stage sizes and the W1 median and mean output profiles. The configured value equals the rule output. Under that projection every F2 session keeps 11 discretionary calls; every F3 generation stage keeps at least 7 calls (pool162 at mean output) or 8.

**What did not change.** Per-session USD 1.00 and batch USD 8.00 remain hard caps. At 640k the token-price bound (USD 1.84 per session at the dearest input rate) exceeds the USD cap, so USD, not tokens, is the binding money ceiling. The researcher's maximum provider exposure is unchanged: USD 8.00 measured plus a USD 0.10 smoke allowance.

### MC2 — Concrete final-call reserve

The proposal asked for "admission headroom for that final request". The frozen rule (METHOD_CONTRACT.md) is:

- The reserve holds one call, 4,000 output tokens, 120 seconds and an input bound for the final request.
- A discretionary request of estimate *E* is admitted only if the remaining input covers *E* plus *E* + 42,000. The 42,000-token growth bound covers one response plus its tool results; its derivation is in METHOD_CONTRACT.md.
- USD is held back in the same way, at the dearest input rate.
- F3 planner/judge requests additionally hold the upper bound of the first judge request (planner only) and twice the upper bound of the first generator request.
- Builds and pairs are admitted only if 120 seconds remain after their worst case.

**Evidence.** W1's largest response was 12.7k bytes, with a 10.5k-character thinking signature, against the 36k-byte allowance.

### MC3 — Truncated responses are discarded, not appended

A `max_tokens` response is recorded and charged. It is never appended to the conversation, none of its tool calls run, and the next call carries a fixed notice. W1 replays show why: 4/119 responses hit the 4,000-token cap, all in planning; two carried an empty `submit_plan` object and one a partial one, and W1 accepted them as completed stages.

### MC4 — Bounded per-response work

Per response, at most four tool calls are executed. Tool results are capped:

| Result | Cap |
|---|---|
| Read | 16,000 characters |
| Build/run feedback per variant | W1's 1,000-character head plus 3,000-character tail |
| Patch result | 2,000 characters |
| Whole response | 32,000 characters |
| State block | 3,000 characters |

These bounds make the final-call growth bound provable. They were not binding in W1, where no response carried more than two tool calls.

### MC5 — Two prompt-cache breakpoints

Breakpoints go on the stage's first message and on the last message of each request; W1 used only the first. This affects cost, not model-visible content. The frozen smoke request uses this exact shape, so a gateway rejection appears before any measured call. Resolving such a rejection needs a dated amendment.

### MC6 — Only legal proposals can be sealed

`submit_final` refuses a malformed or illegal proposal with its violations, and the model can choose again. W1 allowed sealing them; validation then labelled them INVALID_CANDIDATE. In W2A, INVALID_CANDIDATE can arise only from a validation build failure. In the reserved final call, a refused seal ends the session with no submission (`FINAL_REJECTED`).

### MC7 — Terminal rules for stage and provider failures

- **F3 mandatory stages.** A planner or judge stage without an accepted output within its two calls ends the session (`STAGE_FAILURE_PLAN` or `STAGE_FAILURE_JUDGMENT`, no submission). There is no plain fallback, as the proposal required.
- **Provider failures.** A failed or indeterminate request inside F2 or the F3 generation stage moves the session to its reserved final call once. This is declared, charged and recorded; it is not a silent retry. The same failure inside an F3 planner/judge stage is a stage failure.
- **Refusal.** A provider refusal ends the session.

### MC8 — Build timeout aligned with its reservation

W1 reserved 60 s plus 30 s cleanup per build but let Docker run for 300 s. W2A enforces 60 s. W1's longest build took 4.25 s.

### MC9 — Helper-inclusion rule

- **H1.** Direct test-side callees of the entry points, from T0.
- **H2.** JUnit 3 `setUp`/`tearDown` of the entry-point class, which run around every JUnit 3 test method.

Both rules are applied identically to F2 and F3, with at most 80 lines per definition, 8 definitions and 240 lines per case.

Result: gRPC gains `listTestEnv` and the helper at 6010–6042, the W1 audit example. POOL gains its fixtures plus a three-line name-collision match, `setMaxActive`, which is kept rather than hand-pruned. Istio gains three test-double methods; k8s gains nothing.

### MC10 — Leak-screen scope and markers

The screen covers harness-authored text: the packet, prompt texts, source reads, carried evidence and the state block. Model-generated text echoed back is not screened. W1 screened whole requests, so a model writing a marker string, such as a claim named "C1 " or the natural name of the held-out POOL test, would have forced a false integrity stop. W2A adds markers for W1 outcome labels, audit and trace identifiers.

### MC11 — Study caps with explicit smoke allowance

| Resource | Cap |
|---|---|
| Generator requests | 98 (96 measured + at most 2 synthetic smoke requests) |
| Output tokens | 194,048 |
| USD | 8.10 (8.00 measured + 0.10 smoke) |
| Allocated CPU | 160 vCPU-h measured + 4 vCPU-h preparation |

The timeout-bound measured allocation is 147.73 vCPU-h, within 160.

## Fixed implementation choices (routine)

- **Seed and credentials.** Schedule seed 2026092602. Credential variable `W2A_GENERATOR_API_KEY`, separate from W1.
- **Copied W1 code.** W1 validation, oracle, overlay/edit-contract, static-extraction and template-binding code is copied **byte-identically**. `prep/provenance.json` records each source hash; `backends.py`, `ledger.py` and `resources.py` carry only the declared changes.
- **Packets.** W1 packets are read in place and verified against both W1's manifest and the W2A pin (`w1_inputs.json`).
- **Evidence carry-over.** Reads plus claim- and judgment-cited spans (≤ 80 lines each) are merged per file and exclude ranges already visible. The cap is 600 lines or 36,000 characters.
- **Plan limits.** 1–8 claims with ids matching `^[A-Za-z0-9_-]{1,12}$` and 1–6 valid spans each. Text length limits are in `study_config.json`. Unprefixed paths are accepted only if unambiguous.

## Unchanged from the proposal

- **Design.** Four development cases × F2/F3, one session each, Claude Sonnet 5 via OpenCode Zen, no Jev.
- **Session limits.** 600 s wall, 4 patch proposals, 6 paired runs, 12 calls, 24,000 output tokens, 4,000 output tokens per request, USD 1.00.
- **Validation and gates.** Seal-before-validation; W1 validation (5 matched triplets per variant); the offline and live gates in ANALYSIS_PLAN.md.

## Known residual risks (not changed; reported in readiness)

1. **Output ceiling.** If every call produced W1's p90 output (3,301 tokens), the unchanged 24k output cap would leave F2 six discretionary calls and F3 three generation-stage calls. At the W1 mean (1,139) it does not bind.
2. **Wall time with reservation-before-work.**
   - A pair is admitted only while 2 × (outer + cleanup) + 120 s remain. gRPC pairs therefore stop at 180 s elapsed; k8s at 240 s; POOL, Istio and builds at 300 s.
   - At W1's p90 request latency (34 s), F3 reaches generation at about 137 s.
3. **USD hold-back.** Near the end of a POOL session the dearest-rate reserve can stop discretionary calls at about USD 0.45–0.50 realized spend. The session then finalizes.
4. **Caching path.** Two-breakpoint caching through Zen is unverified until the smoke.
5. **Packet exposure.** The shared packets keep W1's deterministic template bindings. They were frozen before W1 outcomes and are identical for both arms, but POOL's T3 binding describes the intervention of the only synthesized W1 witness. Any POOL success must be read with that in mind.
6. **Pretraining exposure.** All four cases, their repairs and W1's outcomes are exposed development material, and the model may have seen the upstream repairs during pretraining.
