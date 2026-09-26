# W2A design freeze v1.0

## Material Passport

- Date: 2026-09-26. Authority: the researcher's instruction to start W2A and carry it to a launch-ready package without live inference.
- No W2A observation existed when this design was frozen. The design is informed by W1's recorded traces and outcomes; that exposure is declared in PROTOCOL.md. This is a local integrity record, not an external preregistration.

## Frozen files

`DESIGN_FREEZE.sha256` lists the exact bytes of 14 files:

- README.md, PROTOCOL.md, METHOD_CONTRACT.md, PROMPTS.md;
- ANALYSIS_PLAN.md, ARTIFACT_CONTRACT.md, EXECUTION_PLAN.md, DESIGN_CHANGES.md;
- MEASURED_RUN_PROMPT.md, this DESIGN_FREEZE.md;
- study_config.json, w1_inputs.json, verify_design.py, .gitattributes.

The manifest does not hash itself. `verify_design.py` checks the hashes and configuration invariants, and that the W1 manifests W2A depends on (W1 executable freeze, W1 v1.2 design freeze, W1 raw seal) still match their pins.

The executable package is bound separately by `../PACKAGE_FREEZE.sha256`, which includes this manifest's digest. A launch additionally requires `../LAUNCH_FREEZE.sha256`.

## Change rule

Changing a scientific or budget constraint requires three things:

- a dated amendment naming the old and new values, the evidence and whether any W2A outcome had been observed;
- a new design directory;
- a new manifest.

v1.0 bytes are preserved. A checksum mismatch is explained and restored or amended. It is never repaired by rehashing.
