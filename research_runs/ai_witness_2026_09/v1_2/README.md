# W1 — AI-assisted behavioral witness strengthening (design v1.2)

## Material Passport

- Prepared: 2026-09-25, at repository HEAD `721d885a315a2c0ef26a82f2613248a4abcc110c` with pre-existing uncommitted research work. Amended 2026-09-26 to v1.1 (GPT-5.6 Sol → Claude Opus 5.5, [A1](../v1_1/AMENDMENT_2026-09-26.md)) and the same day to v1.2 (Claude Opus 5.5 → Claude Sonnet 5, [A2](AMENDMENT_A2_2026-09-26.md)).
- Authority: researcher requested a proposal, complete experiment preparation, and a coding-agent prompt, following the C1 pattern; the researcher instructed the model-family change.
- Status: **design frozen; implementation and bounded preparation exist under v1.1 (see [readiness](../readiness.md)); measured launch not yet authorized or verified**. Before this amendment the only subject executions were the fixed 16-attempt unchanged-test calibration, which involves no model. No provider call and no measured session has occurred.
- Scope: a retrospective development study of strengthening supplied test packages for known repair pairs. It is not a prospective bug-discovery or TCP-effectiveness experiment.
- Versions: this folder (v1.2) governs W1. The [v1.1 package](../v1_1/README.md) and the [v1 package](../README.md) are superseded and preserved byte-identical. Study outputs and the implementation still live under `research_runs/ai_witness_2026_09/`.

Start with the [amendment](AMENDMENT_A2_2026-09-26.md), [proposal](proposal.md), then [protocol](protocol.md), [subjects](subject_register.md), [method contract](method_contract.md), [execution](execution_plan.md), [analysis](analysis_plan.md), and [configuration](study_config.json). [Artifact contracts](artifact_contract.md) specify what the implementation must preserve. [Design freeze](DESIGN_FREEZE.md) defines authority and amendment rules.

Give the coding agent [HANDOFF_PROMPT.md](HANDOFF_PROMPT.md). It calls for implementation, offline tests, restoration and fixed calibration, then an executable launch freeze. It stops before measured sessions. A separate [measured-run prompt](MEASURED_RUN_PROMPT.md) is prepared for use once that agent demonstrates readiness. Neither document asserts that a runner already exists.

Verify this package from the repository root:

```powershell
python research_runs/ai_witness_2026_09/v1_2/verify_design.py
```

The verifier uses Python's standard library. It checks the v1.2 design manifest, basic configuration invariants, and that the superseded v1.1 package still passes its own verifier (which in turn checks v1). It does not check scientific correctness, provider availability, or runtime readiness. See [research record](../research_record.md) for actual actions.

The earlier [research assessment](../../../docs/research/AI_BEHAVIORAL_WITNESS_PLAN_2026_09.md) and [GPT-5.6 Sol assessment](../../../docs/research/ai-case-research-sol-2026-09-25.md) provide rationale. Where their suggested counts or stages differ, this W1 protocol controls W1. Their larger fresh-case and TCP studies are deferred.
