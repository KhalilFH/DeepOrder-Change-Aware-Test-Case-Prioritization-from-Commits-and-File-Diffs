# C1: CI configuration and defect visibility

## Material Passport

- Date: 2026-09-25.
- Origin: academic-research-suite, experiment-agent planning guidance; one agent, no delegation.
- Status: **DESIGN FROZEN v1; READY FOR IMPLEMENTATION HANDOFF; MEASURED LAUNCH BLOCKED pending validation**.
- Verification status: design checked against repository artifacts; runtime readiness unverified.
- Baseline commit: `3f984da9095d19afc239a91945043758da43deec`.
- Purpose: prepare a bounded experiment comparing CPU configurations and retry policies on existing real defect/counterpart pairs.
- Current authorization: freeze the design and handoff, commit and push documentation; execute no experiments in this preparation pass. The coding agent's scope is stated in [HANDOFF_PROMPT.md](HANDOFF_PROMPT.md).

## Start here

**Research question:** Under fixed tests and independently justified defect/counterpart pairs, does limiting CI CPU bandwidth change defect-supported blocking, and does accept-on-pass retry conceal additional observed defect evidence?

The first study is a measurement and feasibility pilot, not an adaptive controller or a general claim about making CI safer. A greener result is not automatically a better result. Absence of verified nuisance means the study cannot establish nuisance reduction.

Read these files in order:

1. [protocol.md](protocol.md): question, subjects, profiles, sampling, budgets and gates.
2. [subject_register.md](subject_register.md): six fixed candidates, commands, source evidence and qualification work.
3. [execution_plan.md](execution_plan.md): preparation, minimal implementation contract, validation, freeze and execution.
4. [analysis_plan.md](analysis_plan.md): estimands, uncertainty, baselines and interpretation.
5. [research_record.md](research_record.md): readiness, resource and amendment templates; initial evidence hashes.

The [design freeze](DESIGN_FREEZE.md) records adoption and the distinction between design and executable launch freezes. [HANDOFF_PROMPT.md](HANDOFF_PROMPT.md) is the copyable instruction for the coding agent. Verify `DESIGN_FREEZE.sha256` before implementing; do not edit frozen design files in place.

`protocol.md` owns scientific choices; `subject_register.md` owns subject commands; `analysis_plan.md` owns scoring; `execution_plan.md` owns operational sequencing. Resolve any newly found conflict by an explicit amendment, never by whichever file was read last.

## Relationship to earlier work

- [The September action plan](../../docs/research/NEXT_RESEARCH_ACTION_PLAN.md) and its Q0/E1 protocol remain historical, unchanged records. Their G1b no-go remains in force: C1 does not restart E2/E3, extend the old roster or relabel old outcomes.
- [The feasibility report](../ci_sensitivity_2026_09/feasibility_report.md) motivates this new question. Six restorations executed; three met the old intermittency window. That is not a population estimate of recoverability.
- [F1](../ci_sensitivity_2026_09/f1/report.md) is completed separately. Its Airavata result and evidence-gap note are not C1 efficacy evidence.
- Earlier agent, embedding and platform proposals remain deferred. No such component is needed here.
- The canonical state, decision, trajectory and experiment documents now carry dated C1 routing entries. Earlier scaffold material and hypotheses do not override this adopted design. Adoption is not evidence that the implementation or host is ready.

## First five tasks

1. **Read-only readiness inventory:** verify the six source records, local image availability and identities, host/VM resources, toolchain and existing harness interfaces. Save `readiness.md`; build or run no subject yet.
2. **Complete the six counterpart dossiers:** record source/test/dependency hashes, reconstruction class and each oracle's behavioral justification. Produce `subject_manifest.json`; unresolved fields remain explicit. Rebuild only in the subsequent authorized preparation stage.
3. **Implement the narrow C1 adapter:** enforce profiles and unique observation identities, port the three missing oracle cards, and add matched-block analysis. Keep the original E1 study and results unchanged.
4. **Validate and freeze:** run implementation checks and fixed calibration only, audit CPU enforcement and oracle specificity, generate the schedule and cost projection, then record the launch freeze. No effect-based parameter selection.
5. **Collect C1 batch 1:** blocks 1–5, all enrolled subjects, using the frozen schedule. Check integrity and cost before batch 2; do not inspect comparative effects to decide whether to continue.

Tasks are sequential. The handoff covers tasks 1–4, including bounded calibration, but stops before task 5. No repeated permission request is needed for already-authorized work. Scientific readiness gates still apply. There is no C1 launch command yet: writing and validating it is part of task 3, not something to infer from E1's driver.

## Expected deliverable

One reproducible pilot report with per-subject comparisons, all unsuccessful reconstructions, invalid/unresolved observations, both CPU profiles, both revision variants, all policy prefixes, and a continue/inconclusive/close decision. A useful negative result is an acceptable completion.
