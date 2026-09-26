# W1 design freeze v1

## Material Passport

- Date: 2026-09-25. Authority: researcher request to prepare a complete experiment proposal and coding-agent handoff.
- State: design frozen for implementation; runtime/model qualification and measured launch pending.
- No W1 observations are reported by this freeze. This is a local integrity record, not an externally timestamped preregistration.

## Frozen files

DESIGN_FREEZE.sha256 lists exact bytes of these 14 files: README.md, proposal.md, protocol.md, subject_register.md, method_contract.md, prompts.md, study_config.json, execution_plan.md, analysis_plan.md, artifact_contract.md, artifact_schema.json, HANDOFF_PROMPT.md, MEASURED_RUN_PROMPT.md, and this DESIGN_FREEZE.md. It also binds verify_design.py and .gitattributes, for **16 files total**. The hash manifest does not hash itself.

The research record and global routing documents remain appendable and are excluded from the design freeze. Research background links are explanatory; the frozen W1 files govern W1. An executable FREEZE.sha256 is separate and must not be created merely to suggest that documentation is executable.

## Authority and unresolved launch fields

protocol.md controls study design and success criteria; method_contract.md controls arm behavior/information; execution_plan.md controls implementation stages/budgets; analysis_plan.md controls interpretation. study_config.json repeats numeric settings for machine use. A disagreement is a freeze defect to resolve explicitly before launch, not an invitation to choose the convenient value.

Actual model endpoints/returned identities, settings, scheduler compatibility, exact source trees/images, oracle code, CLI syntax and environment availability are intentionally unresolved until implementation. Resolve these in a separate launch_config.json and launch record without editing the frozen design. The fixed requested generator family, five arms, counts, resource profile and scientific endpoints remain constraints. A missing dependency is not implicit authority to change them.

Preserve v1 bytes if changing a scientific constraint. Write a dated amendment naming the rationale, evidence, affected hypotheses and old/new values, then create a separate versioned design and new manifest. Record whether any measured outcomes were observed before amendment. Do not overwrite old hashes to conceal a change.

All design text uses UTF-8/LF. .gitattributes preserves this for committed files. Verify again after any checkout or transfer. A checksum mismatch requires explanation and restoration or an explicit amendment; it is never repaired by automatically rehashing during preflight.
