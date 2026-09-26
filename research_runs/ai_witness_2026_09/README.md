# W1 — AI-assisted behavioral witness strengthening

## Material Passport

- Prepared: 2026-09-25, at repository HEAD `721d885a315a2c0ef26a82f2613248a4abcc110c` with pre-existing uncommitted research work.
- Authority: researcher requested a proposal, complete experiment preparation, and a coding-agent prompt, following the C1 pattern.
- Status: **design frozen for implementation; implementation and experimental launch are not yet verified**. No W1 subject runs, provider calls, or measured results were produced in this preparation pass.
- Scope: a retrospective development study of strengthening supplied test packages for known repair pairs. It is not a prospective bug-discovery or TCP-effectiveness experiment.

Start with [proposal](proposal.md), then [protocol](protocol.md), [subjects](subject_register.md), [method contract](method_contract.md), [execution](execution_plan.md), [analysis](analysis_plan.md), and [configuration](study_config.json). [Artifact contracts](artifact_contract.md) specify what the implementation must preserve. [Design freeze](DESIGN_FREEZE.md) defines authority and amendment rules.

Give the coding agent [HANDOFF_PROMPT.md](HANDOFF_PROMPT.md). It calls for implementation, offline tests, restoration and fixed calibration, then an executable launch freeze. It stops before measured sessions. A separate [measured-run prompt](MEASURED_RUN_PROMPT.md) is prepared for use once that agent demonstrates readiness. Neither document asserts that a runner already exists.

Verify this package from the repository root:

```powershell
python research_runs/ai_witness_2026_09/verify_design.py
```

The verifier uses Python's standard library. It checks the design manifest and basic configuration invariants, not scientific correctness, provider availability, or runtime readiness. See [research record](research_record.md) for actual actions.

The earlier [research assessment](../../docs/research/AI_BEHAVIORAL_WITNESS_PLAN_2026_09.md) and [GPT-5.6 Sol assessment](../../docs/research/ai-case-research-sol-2026-09-25.md) provide rationale. Where their suggested counts or stages differ, this W1 protocol controls W1. Their larger fresh-case and TCP studies are deferred.
