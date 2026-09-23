# Direct-policy checks: cost check before running — 2026-09-23

Required by `batch1_check.md`: the worst case for the direct checks did not fit on the conservative count, so they get their own cost check before they run. Nothing here has been executed. Inputs are the E1 ledgers' timing fields, the frozen manifests and the Q0 rates. Only maximum durations are used from the ledgers. No outcomes were tabulated and no policy contrast was computed.

## Inputs

- **Remaining E1 cap (conservative, 16 vCPUs):** 20 − 10.61 = **9.39 vCPU-hours**. The 10.61 is the measured-block cost on the span basis (`batch2_check.md`). The identity/no-change control, the deterministic-failure control and implementation verification must also come out of this remainder.
- **Checks:** 12 in total (plan §6 step 3), in reserved blocks 101–112. `run_policy_direct` runs P1 as 1 attempt. P3 runs up to 3 attempts and stops at the first exit 0.
- **Hard per-attempt bound:** runner timeout plus `CLEANUP_TIMEOUT_S` (30 s). That is 90 s for etcd5509 and 95 s for etcd7492. `elapsed_s` includes cleanup.
- **Observed per-attempt maximum over all 240 measured attempts:** etcd5509 `V_bad` 43.6 s, `V_ok` 0.8 s; etcd7492 `V_bad` 48.4 s, `V_ok` 0.8 s. There were no runner timeouts: Go's `-test.timeout` (45 s / 50 s) always fired first.
- **Gap between attempts:** a maximum of 2.04 s was observed within a run, and 2.04 s is charged to every attempt.
- **Allocation (not yet frozen):** "balanced across episodes, versions and P1/P3" is taken to mean 6 checks per episode, 3 per episode × version, and 3 P1 plus 3 P3 per episode. The expensive variable is how many P3 checks fall on `V_bad`, so each bound uses the worst balanced placement.

## Projection

| Scenario | Attempts | Wall (s) | Conservative vCPU-h | Q0 convention | Left of 9.39 |
|---|---:|---:|---:|---:|---:|
| Hard bound: every attempt times out and needs full cleanup | 24 | 2269 | **10.08** | 0.630 | **−0.69** |
| Observed-max bound, 1 P3 per `V_bad` cell | ≤24 | 520 | 2.31 | 0.144 | +7.08 |
| Observed-max bound, 2 P3 per `V_bad` cell | ≤24 | 701 | 3.12 | 0.195 | +6.27 |
| Observed-max bound, all 3 `V_bad` checks per episode are P3 | ≤24 | 882 | 3.92 | 0.245 | +5.47 |
| Expected: Q0 failure rates (16/20, 2/20; `V_ok` 0/20), failing attempts at observed max, 2 P3 per `V_bad` cell | ~15 | 260 | 1.15 | 0.072 | +8.24 |

- **Correction to `batch1_check.md`:** its worst case of "36 x 60 s" (16 vCPU-hours) assumed all 12 checks were P3, left out cleanup, and used 60 s for both episodes. Under P1/P3 balance the worst case is 24 attempts. The hard bound is 10.08 vCPU-hours.
- The hard bound is a theoretical ceiling. In 240 measured attempts, no attempt reached the runner timeout. Every hang ended at Go's own test timeout, about 15 s below the runner timeout.

## Verdict

- **Expected case and observed-max bound: fit.** Even the worst balanced placement uses 3.92 of the 9.39 remaining, leaving 5.47 vCPU-hours for the controls and implementation verification.
- **Hard bound: does not fit.** It exceeds the remainder by 0.69 vCPU-hours before any control is charged.
- **Under the Q0 convention, every scenario fits by a wide margin:** the worst is 0.63 vCPU-hours.
- **No frozen rule decides this case.** The protocol's cost-stop rule covers batch 2 only, and `batch1_check.md` named no criterion for the direct checks.

## Must be settled and frozen (as an AMENDMENTS.md entry) before any check runs

1. **The allocation of the 12 checks** across episode × version × policy, and their order. The allocation must not depend on E1 outcomes.
2. **How the hard-bound overrun is handled.** Options:
   - A pre-attempt guard that refuses to start an attempt if the cumulative conservative E1 cost plus that attempt's hard bound would exceed a stated line. This keeps the cap safe by construction, and a guard stop is recorded as a resource stop.
   - Accepting the observed-max bound as the projection.
3. **A cost reserve for the controls.** Neither control has an oracle card or a defined design yet (`e1_harness/README.md`, "Not in scope here"), so their cost cannot be projected. It must be reserved before the direct checks consume the remainder.
