# W2A — execution-feasibility pilot (design v1.0)

**Status (2026-09-26):**

- Design frozen. Executable package frozen after all 13 offline gates passed.
- **Not launched.** No provider request, smoke or subject execution has occurred for W2A.
- Launch is blocked only by provider/launch gates; see [readiness.md](readiness.md).

## What it is

The pilot asks whether a plain (F2) and a structured (F3) Claude Sonnet 5 agent can each complete read → propose → build → run → seal on W1's four exposed development cases. It uses:

- one session per case and arm, eight sessions in all, without Jev;
- engineering repairs for the execution failures found by the [W1 audit](../../ai_witness_2026_09/postrun_audit/REVIEW.md);
- W1's unchanged validation (5 matched triplets per variant, private focal oracles).

It follows [proposal v0.1](../v0_1/PROPOSAL.md), with material changes recorded in [design/DESIGN_CHANGES.md](design/DESIGN_CHANGES.md).

W1 remains closed under D005; W2A reads W1 artifacts but never writes to them.

## Where things are

- **Design:** [design/](design/README.md) — protocol, method contract, prompts, analysis plan, artifact contract, execution plan, and the [launch instruction](design/MEASURED_RUN_PROMPT.md).
- **Code:** `w2a.py` launcher, `w2a_harness/` package and tests. Module provenance against W1 is in `prep/provenance.json`.
- **Offline evidence:** `prep/` — tests, W1-failure regressions, fake dry run, limit check, W1 audit reproduction, render leak check, and the model-facing renderings in `prep/rendered/`.
- **Schedule:** `schedule.json`, seed 2026092602.
- **Freezes:** `design/DESIGN_FREEZE.sha256` and `PACKAGE_FREEZE.sha256`; `LAUNCH_FREEZE.sha256` is written only after the smoke.

## Commands (repository root)

```
python research_runs/ai_witness_followup_2026_09/w2a/w2a.py prepare          # offline checks (no provider, no containers)
python research_runs/ai_witness_followup_2026_09/w2a/w2a.py verify-package
python research_runs/ai_witness_followup_2026_09/w2a/w2a.py preflight        # non-executing gate report
```

The launch sequence (smoke → confirm-pricing → launch-freeze → run → seal → analyze) is in [design/EXECUTION_PLAN.md](design/EXECUTION_PLAN.md).

Re-running `prepare` rewrites `prep/` reports. This invalidates the package freeze until `package-freeze` is re-run, and a changed report would be visible as a digest mismatch.
