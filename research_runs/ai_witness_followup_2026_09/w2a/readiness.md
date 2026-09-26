# W2A readiness report

## Material Passport

- Date: 2026-09-26. Scope: preparation only.
- Nothing was sent to any provider, no smoke was run, and no subject container was started. Nothing was bought, and no W1 file was written.
- Evidence: `prep/*.json`, `prep/gates.json` and the freezes listed below. Each report is stamped with the harness code hash; the package freeze binds all of them.
- Separation:
  - **Observed** = offline checks and W1 recorded data.
  - **Projected** = planning arithmetic.
  - **Unexecuted** = everything live.

## Verdict

**OFFLINE_READY. NOT_READY for measured launch** until three provider/launch gates pass under the researcher's launch instruction.

- Design freeze v1.0 (`design/DESIGN_FREEZE.sha256`, 14 files, digest `75503752…`) verifies.
- Executable package freeze (`PACKAGE_FREEZE.sha256`, 52 files, digest `e08cf57a…`) verifies.

## Gate evidence (observed offline)

| Gate | Status | Evidence |
|---|---|---|
| Design freeze intact | PASS | `design/verify_design.py`: 14/14 hashes and invariants; W1 pins intact |
| W1 read-only inputs match pins | PASS | W1 executable freeze, v1.2 design and raw-seal manifests; 12 W1 frozen input/oracle/launch files re-hashed |
| W1 offline audit reproduced | PASS | `prep/w1_audit_reproduction.json`: byte-identical `audit.json`; 1,962 raw and 181 executable hashes, 60 labels, 28 policies, 119/119 `claude-sonnet-5` |
| Copied W1 modules identical or declared | PASS | `prep/provenance.json`: 10 byte-identical (incl. validation, oracles, overlay); 3 with declared changes |
| Schedule regenerates | PASS | `schedule.json` seed 2026092602, digest `854d99c2…` |
| Offline tests | PASS | 24/24 (`prep/offline_tests.json`) |
| W1 failure-case regressions | PASS | R1–R9 (`prep/w1_regressions.json`), see below |
| Fake 8-session dry run | PASS | `prep/dry_run.json`, see below |
| Model-facing renderings leak-free | PASS | 8 first-stage renderings plus tool schemas screened (`prep/rendered/`) |
| Limit check | PASS | `prep/budget_check.json`, see below |
| 16-CPU Docker reachable; pinned images present | PASS | `docker info` NCPU=16; all 8 W1 image IDs present (non-executing inspect) |
| Package freeze valid | PASS | `PACKAGE_FREEZE.sha256` |
| Generator credential in environment | **FAIL** | `W2A_GENERATOR_API_KEY` not set in this environment |
| Authorized smoke returned `claude-sonnet-5` with the W2A request shape | **FAIL** | not run (not authorized in this pass) |
| Pricing re-confirmed at launch | **FAIL** | to be recorded with `confirm-pricing` |
| Study reservations cover the batch | PASS | empty W2A ledger; caps in `design/study_config.json` |
| Launch freeze | **FAIL** (expected) | written only after the provider gates pass |

## W1 failures replayed against W2A code (observed, offline)

| ID | W1 failure (recorded material) | W2A behaviour |
|---|---|---|
| R1 | gRPC helper body absent from the initial context (read three times across stages) | included by helper rule H1 in both arms |
| R2 | truncated planner response with empty `submit_plan` accepted as a stage (replayed W1 bytes) | discarded; no tool call executed or replayed; notice sent; next valid plan accepted |
| R3 | truncated planner response with a partial plan (replayed) | discarded in the same way; partial input never accepted |
| R4 | empty judgment list against seven claims (replayed) | rejected with the missing ids; seven explicit `unknown` judgments accepted and kept distinct |
| R5 | placeholder patch (W1's only AI patch) | explicit malformed error; counted; refused by build and seal; shown as MALFORMED in the state |
| R6 | run before build | explicit "call build_pair first"; nothing executed; pair budget untouched |
| R7 | six input-admission denials (pool162) | each recorded W1 estimate admitted under W2A caps with the final reserve held |
| R8 | output denial (880 tokens left) | discretionary request refused; reserved final call still admitted with 4,000 output tokens |
| R9 | ranges re-read across fresh stages | planner reads carried into judge and generator first messages |

## Dry run (fake provider and subjects; synthetic outcomes, not feasibility evidence)

- **Coverage.** All 8 scheduled sessions ended with a terminal reason, and all 8 validations ran. Both finals of each case were sealed before either was validated, in the scheduled order.
- **Accounting.** Wire requests (54) equal ledger requests equal session records, and ledger input tokens equal session totals. No reservation was left open, and per-session caps held.
- **Paths exercised:**
  - discretionary seal;
  - reserved final-call seal (F3 with a W1 truncated-plan replay and a W1 empty-judgment replay);
  - F3 plan-stage failure;
  - a final call answered without `submit_final` (NO_SUBMISSION, not validated);
  - a final call with extra tool calls ignored;
  - build-before-run error, no-tool response and a truncated patch response.

## Limit check (observed calibration + projection)

**Calibration from W1 (observed, read-only):**

| Quantity | Value |
|---|---|
| Local admission estimate / provider input | 1.19–1.50 (conservative) |
| Per-call context growth (estimated tokens) | median 1.9k, p90 6.3k |
| Output per call | median 565, mean 1,139, p90 3,301; 4/119 at the 4,000 cap |
| Largest response | 12.7k bytes |
| Request latency | median 8.9 s, p90 34.2 s |
| Longest build / attempt | 4.3 s / 31.9 s |

**Rendered W2A first requests** span 7.2k (k8s) to 21.7k (pool162) estimated tokens.

**Projections:**

- **Proposal's 240k input cap.** F3 cannot start on pool162 once the final call and first generation request are reserved. F3's smallest generation stage is one call.
- **Configured 640k cap.** The value equals the declared derivation rule (DESIGN_CHANGES.md MC1). At W1 p90 growth and mean output, F2 keeps 11 discretionary calls in every case and F3 keeps 7–8 generation-stage calls. The final call is admissible in every configured projection.

**Allocated CPU (timeout bound):** 147.73 vCPU-h (search 21.33, validation 120.00, validation builds 6.40), within the 160 measured cap.

## Proposed cost bounds for the launch

| Resource | Hard cap | Projection (not a quote) |
|---|---:|---|
| Provider USD | **8.10** (8 × 1.00 measured + 0.10 smoke) | 0.33–0.47 per session before the final call at W1-mean output, about USD 3–4 per batch |
| Generator requests | 98 (96 + ≤ 2 smoke) | ≤ 96 |
| Input tokens | 5.124M | far below the cap under W1-like caching |
| Output tokens | 194,048 | — |
| Allocated vCPU-h | 160 measured + 4 preparation (0 used) | timeout bound 147.73; W1-like durations imply far less |
| Wall clock | — | roughly 1.5–2.5 h |

## Unresolved blockers (launch)

1. **Credential.** `W2A_GENERATOR_API_KEY` must be set by the researcher in the launching shell (the existing OpenCode Zen key; not written to disk).
2. **Smoke.** One authorized synthetic request must return `claude-sonnet-5` and a tool call with the frozen request shape, including the second cache breakpoint, which Zen has not yet been shown to accept.
3. **Pricing.** The current Sonnet 5 price list must be re-confirmed and recorded.

## Residual design risks (documented, not blockers)

- **Output ceiling.** If most calls produced p90 output, the unchanged 24k ceiling would leave F3 three generation-stage calls.
- **Wall time for gRPC.** With reservation-before-work, gRPC pairs are admissible only until 180 s elapsed. At p90 latency, F3 reaches generation at about 137 s.
- **USD hold-back.** The dearest-rate USD hold-back can end pool162 sessions around USD 0.45–0.50 realized spend. The session still finalizes.
- **Packet exposure.** The packets keep W1's template bindings, including pool162's T3 description.
- **Pretraining exposure.** All cases are exposed development material.

## Next launch instruction

Issue [design/MEASURED_RUN_PROMPT.md](design/MEASURED_RUN_PROMPT.md) after setting `W2A_GENERATOR_API_KEY`. It authorizes one smoke (plus one recorded retry only after an identity-less failure), the eight frozen sessions and their validations, within USD 8.10.
