# W2A execution plan v1.0

## Material Passport

- Date: 2026-09-26. Commands are relative to the repository root.
- **Preparation** (offline, no provider or subject execution) and **launch** (smoke, then the measured run) have separate authority. Only the researcher's explicit instruction ([MEASURED_RUN_PROMPT.md](MEASURED_RUN_PROMPT.md)) authorizes the launch steps.

## Phase A — offline preparation (completed by the preparation pass)

```
python research_runs/ai_witness_followup_2026_09/w2a/w2a.py prepare
python research_runs/ai_witness_followup_2026_09/w2a/w2a.py package-freeze
python research_runs/ai_witness_followup_2026_09/w2a/w2a.py preflight
```

`prepare` runs these steps in order:

1. `verify-design`
2. `verify-w1` (read-only W1 pins)
3. `reproduce-w1-audit` (into a temporary directory)
4. `provenance`
5. `schedule`
6. `render`
7. `test`
8. `regressions`
9. `dry-run`
10. `budget-check`

`package-freeze` refuses unless every offline gate passes. `preflight` sends no request and starts no container. It reports `OFFLINE_READY` while the provider gates are open.

## Phase B — launch (requires the researcher's instruction)

1. **Credential.** Set `W2A_GENERATOR_API_KEY` to the researcher's existing OpenCode Zen key in the launching shell. Do not write it to any file.
2. **Smoke.** Run exactly one synthetic, non-case request with the frozen request shape:

   ```
   w2a.py smoke --authorization "<recorded researcher text>"
   ```

   The request shape: strict tool, adaptive thinking, effort medium, two cache breakpoints, `max_tokens` 1,024.

   **PASS:** HTTP 200, returned model `claude-sonnet-5` and a `report_ready` tool call. The result is recorded in `launch_config.json`, `events.jsonl` and the resource ledger.

   **Failure:** at most one more smoke, and only if no identity was returned, with a separately recorded `--deviation` authorization. A request-shape rejection (for example of the second cache breakpoint) is NOT_READY and needs a dated amendment.
3. **Pricing.** Re-confirm the Sonnet 5 price list and record its source:

   ```
   w2a.py confirm-pricing --source "<url/date>"
   ```

   A price change is NOT_READY: the USD caps stay fixed, and a change to caps or effective budgets needs an amendment.
4. **Launch freeze.** Run `w2a.py launch-freeze`. It writes `launch_record.md` and `LAUNCH_FREEZE.sha256` only if every gate passes.
5. **Measured run.** Run

   ```
   w2a.py run --authorize "<researcher launch instruction>"
   ```

   It refuses unless every gate and both freezes verify.
6. **Seal.** Run `w2a.py seal` to write `raw_seal.sha256` before any analysis.
7. **Analysis.** Run `w2a.py analyze` for the frozen analysis in `analysis/`. Independently re-derive the headline counts from `measured/*/session.json` and `validation/outcome.json`.

## Resource bounds (hard caps; not expected costs)

| Resource | Per session | Batch | Study cap (incl. smoke / preparation) |
|---|---:|---:|---:|
| Generator requests | 12 | 96 | 98 |
| Input tokens (cache-inclusive) | 640,000 | 5,120,000 | 5,124,000 |
| Output tokens (thinking included) | 24,000 | 192,000 | 194,048 |
| Provider USD | 1.00 | 8.00 | 8.10 |
| Search wall time | 600 s | 80 min | — |
| Allocated vCPU-h | — | timeout bound 147.73 (search 21.33 + validation 120.00 + validation builds 6.40) | 160 measured + 4 preparation |
| Jev evaluations | 0 | 0 | 0 |

**USD bounds.** The provider exposure is **at most USD 8.10**. At 640k tokens the dearest-rate token bound (USD 1.84 per session) exceeds the USD cap, so the USD cap binds.

**Illustrative spend.** The limit-check projection (not a quote) gives USD 0.33–0.47 per session before the final call at W1-mean output. That is about USD 3–4 for the batch if caching behaves as in W1.

**Wall-clock estimate.** W1 validation attempts took ≤ 32 s and builds ≤ 4.3 s. Eight 600-second search allowances plus 240 validation attempts give an expected wall clock of roughly 1.5–2.5 hours; the timeout bound is much longer.

**Preparation.** The preparation pass used no allocated CPU and USD 0: it built nothing and ran no container.

## Pause and resume

The runner pauses on provider drift, integrity stops or an exhausted reservation. Resume only with `run --authorize "<text>" --resume-review "<note>"`. In-flight work becomes UNRESOLVED and is not rerun. Partial data is kept; a paused batch is reported as INCOMPLETE.
