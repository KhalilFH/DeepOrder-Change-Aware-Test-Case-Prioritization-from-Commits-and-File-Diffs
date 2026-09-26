# W2A method contract v1.0

## Material Passport

- Date: 2026-09-26. Frozen arm definitions and harness semantics.
- Model-facing texts are in [PROMPTS.md](PROMPTS.md). Numbers are in [study_config.json](study_config.json). The implementation is `w2a_harness/`, bound by `PACKAGE_FREEZE.sha256`.

## Shared facilities (identical for F2 and F3)

### Deterministic context

The first message of every stage contains the following, in this order:

1. The task text and the final-submission format.
2. The stage limits.
3. The W1 packet context, unchanged: build/run interface, production diff, file index, T0 compact extraction, template bindings, and the W1 initial excerpts (entry-point tests and changed functions, at most 400 lines each).
4. The **helper definitions**, chosen by a fixed rule (`packet.py`):
   - H1: direct test-side callees of each entry point, taken from T0. Go callees must be in the same package directory; Java callees must be in the same class file. Package-qualified calls such as `errors.New` are skipped.
   - H2: JUnit 3 `setUp`/`tearDown` in the entry-point class.
   - Ranges already visible are skipped. Limits: 80 lines per definition, 8 definitions and 240 lines per case.
5. Any stage extras.
6. The harness state block.

### Tools

The five W1 primitives, `read_source`, `submit_patch`, `build_pair`, `run_pair` and `submit_final`, keep the W1 edit contract, feedback truncation and reservation-before-work. W2A adds:

- **Explicit state feedback.** Every harness turn ends with a state block of at most 3,000 characters. It lists:
  - each proposal: legal or illegal (with violations) or malformed; built or not per variant; the paired-run count and the last exit codes;
  - what `latest` resolves to;
  - the remaining calls, tokens, USD, seconds, proposals and pairs.
- **Explicit tool errors.**
  - `run_pair` on an unbuilt proposal returns "call build_pair first (nothing was run)".
  - `build_pair` refuses malformed or illegal proposals.
  - `submit_final` refuses malformed or illegal proposals with their violations and seals only legal proposals or `unchanged`.
- **Bounds.**
  - Reads return at most 300 lines and 16,000 characters.
  - At most four tool calls per response are executed; the rest return a "not executed" error.
  - The tool results of one response are capped at 32,000 characters in total.

### Responses

- **Truncated.** A `max_tokens` response is recorded and charged, then discarded. It is not appended to history, and none of its tool calls run. The next call adds a fixed notice as a new user turn.
- **No tool call.** A complete response without a tool call is appended, followed by a fixed notice and the state block.
- **Refusal.** A refusal ends the session.

### Reserved final call and admission

The harness admits a request only when it can be paid for without consuming the reserve below.

**Reserve.** One call, 4,000 output tokens, 120 seconds, and an input bound. The bound is the final request's estimate: the current estimate plus a growth bound G = 42,000 estimated tokens. G is derived as follows:

- one response of ≤ 4,000 output tokens is allowed ≤ 36,000 bytes, including thinking signatures (W1 maximum 12,745 bytes);
- ≤ 32,000 characters of tool results × 1.25 for JSON escaping;
- the state block and notice;
- all divided by 2 bytes per token.

**Discretionary request.** A request with estimate E (local estimate: ceil(request bytes / 2) + 512) is admitted only if all of these hold:

- at least 2 calls remain;
- remaining input ≥ E + (E + G);
- remaining output − 4,000 ≥ 1,024, which then sets `max_tokens`;
- remaining USD ≥ cost(E, max_tokens) + cost(E + G, 4,000), at the dearest input rate;
- the request timeout min(240, remaining − 120 − 5) ≥ 30 s.

**F3 planner and judge requests** also hold the first-generator upper bound twice (the first generation request and the final call after it). Planner requests also hold the first-judge upper bound. These upper bounds are rendered stage messages plus the character caps of evidence, plan and judgments.

**Builds and pairs** require their worst case plus 120 s to remain.

**The final request** needs only its own admission.

When a discretionary request cannot be admitted, the session goes straight to the final call. The final instruction is appended to the pending (unsent) user turn, and only the first `submit_final` in the response is executed; other tool calls are ignored and counted. The terminal reason is recorded (PROTOCOL.md).

### Accounting

Accounting follows W1:

- every wire request is counted once and charged its provider-reported usage, cache reads included;
- indeterminate requests stay charged at their reservation;
- there is no silent retry;
- allocated CPU is reserved before each primitive and settled at elapsed time.

A returned model other than `claude-sonnet-5` pauses the run.

### Prompt caching

Explicit ephemeral breakpoints are placed on the last block of the stage's first message and on the last block of each request's final message. Stored history is never edited.

## Arms

### F2 — plain agent

1. One stage, `agent`, with the five tools.
2. Discretionary tool loop until the model seals, or until admission fails, which leads to the final call.
3. The reserved final call if the session has not sealed.

### F3 — structured agent

1. **Planner** (≤ 2 calls; tools `read_source` and `submit_plan`). A plan is accepted only if all of these hold:
   - the response was complete;
   - obligation and intervention are non-empty and within their limits;
   - there are 1–8 claims with unique ids matching `^[A-Za-z0-9_-]{1,12}$` and a listed category;
   - every claim has a non-empty proposition and 1–6 valid spans (`file_id:start-end` within file bounds; an unprefixed path is accepted only if unambiguous).

   Invalid plans are returned with their errors; no accepted plan within two calls gives `STAGE_FAILURE_PLAN`.
2. **Judge** (≤ 2 calls; tools `read_source` and `submit_judgments`). The first message carries the evidence gathered so far: planner reads plus claim-cited spans (≤ 80 lines each), merged, minus visible ranges, capped at 600 lines or 36,000 characters. It also carries the validated claims. A judgment table is accepted only if all of these hold:
   - exactly one judgment per claim id;
   - each verdict is supported, contradicted or unknown;
   - each has a non-empty reason;
   - spans are valid, and supported/contradicted verdicts have at least one.

   Explicit `unknown` is kept distinct from missing. No accepted table gives `STAGE_FAILURE_JUDGMENT`.
3. **Generator** (all remaining discretionary calls; the five tools). The first message carries the updated evidence (adding judgment-cited spans), the validated plan and the full judgment table (verdict, reason, spans). It then runs the same discretionary loop and final call as F2.

F3 pays for planning and judging inside the same session budget. F2 and F3 differ only in the structured procedure and its carried outputs.

## Isolation and prohibited adaptations

- Every session starts fresh, with no cross-session memory, caches or candidate reuse.
- The coding agent's conversation is never an experimental session.
- There is no manual editing of model output and no human repair.
- Prompts, tools, packets, helper rule, caps, parsers and schedule are frozen before the first measured call.
