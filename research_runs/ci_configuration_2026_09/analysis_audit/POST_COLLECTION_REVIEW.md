# C1 post-collection verification and interpretation

- Date: 2026-09-25.
- Authority: researcher asked to check completed experiments and proceed with measured annotation followed by analysis.
- Status: **collection verified complete; frozen annotation and analysis completed; pilot evidence only**.
- No new subject execution, implementation edit, oracle override, protocol change, commit or push occurred in this pass.

## Verification before analysis

**Established evidence:** all 720 scheduled attempt identities exist exactly once across 12 measured ledgers, six subjects, two profiles, two variants and ten matched blocks per subject. Actual recorded chronological order matches the frozen schedule. Both batch sessions ended as completed. The recorded batch-A gate passed before batch B.

The design freeze's 8 entries and executable freeze's 71 entries verified. All measured chains and the event/resource chains verified. The raw measured files were sealed by SHA-256 before annotation; they still match afterwards. Recorded profile enforcement, session probes and cleanup checks passed on all 720 attempts. These are checks of preserved records, not a new live runtime inspection.

See [pre_analysis_seal.json](pre_analysis_seal.json). It binds the raw files, freeze digests and prior gate/session records before these outputs were generated.

## Commands and artifacts

Executed once each from the repository root, using unchanged frozen code:

```text
python -B -m c1_harness.cli annotate --stage measured
python -B -m c1_harness.cli analyze --out analysis
```

No replacement, subset selection or questioned-pair/annotation overrides were passed. Annotations are in [measured/annotations.jsonl](../measured/annotations.jsonl); the [mechanical report](../analysis/report.md), [summary](../analysis/summary.json) and [reproduction record](../analysis/reproduction.md) preserve the frozen outputs. Standard output/error from both commands are retained in this directory.

A separate [arithmetic verification script](independent_verification.py), importing neither C1 nor E1 scoring functions, recomputed every primary numerator, paired contrast, batch direction and C3 flag from raw attempts plus annotations. [It passed](independent_verification.json). This independently checks arithmetic and recorded provenance, not causal oracle truth or the confidence-interval numerical implementation.

Annotation, analysis and that audit consumed **0.002832 allocated vCPU-hours** under a conservative 16-vCPU accounting basis; **1.997168 of 2.0** remains. Charges and released reservations are appended to the resource ledger. These figures cover the timed computation jobs, not unmeasured human/agent reasoning effort. Measured collection had already used 16.032970 of its 24.0 vCPU-hour cap; no measured spending was added.

## Observed results

Mechanical labels: **540 PASS, 180 FOCAL_DEFECT_WITNESS**, zero unresolved or harness-invalid. All **360 acceptable-variant attempts passed**; no acceptable variant matched a focal signature. This is no observed nuisance, not proof that nuisance cannot occur.

Supported-blocking counts on defective variants, each out of ten blocks:

| Subject | R/P1 | L/P1 | R/P3 | L/P3 | C3 follow-up signal |
|---|---:|---:|---:|---:|---|
| etcd5509 | 7 | 10 | 5 | 7 | yes, both policies |
| etcd7492 | 4 | 0 | 0 | 0 | no: contrast absent in batch B |
| grpc1859 | 2 | 0 | 0 | 0 | no: contrast absent in batch A |
| grpc2391 | 9 | 8 | 8 | 7 | no: below margin |
| istio17860 | 10 | 10 | 10 | 10 | no |
| k8s26980 | 0 | 0 | 0 | 0 | no |

R is unrestricted CPU bandwidth; L has a two-CPU quota. P1 executes once; P3 accepts on a pass within three attempts. All supplied focal classifications remain subject to the frozen oracle's stated limits.

**Gate C2 passes:** six complete subjects on four projects, no invalid or missing observations. **C3 passes only for etcd5509:** R minus L is -0.30 under P1 and -0.20 under P3. Batch contrasts are -0.40/-0.20 for P1 and -0.20/-0.20 for P3. Therefore limited CPU bandwidth coincides with greater supported blocking in this subject, not reduced visibility.

Every primary simultaneous interval includes zero. Missingness bounds collapse to point values because observations are complete; those bounds are not confidence intervals. Passing the development gate is not statistical confirmation.

P3 accepted after encountering a focal witness in 13 observed defective-variant blocks: etcd5509 R/L = 2/3, etcd7492 = 4/0, grpc1859 = 2/0, grpc2391 = 1/1, and zero in the other subjects. This is an inventory of observed decisions, not a pooled population effect. P3-retain flags those decisions but does not change their final gate.

## Interpretation and limits

**Interpretation:** configuration effects are not uniformly in the direction of greener CI hiding bugs. The one effect meeting the prespecified replication-across-batches rule goes the other way. The larger apparent reduction for etcd7492 fails that rule and should not become the headline merely because it supports the original concern.

No nuisance reduction was measured. No adaptive policy or new assessor was evaluated. Ordinary paired counts, signatures and the frozen rules were enough to characterize this pilot; these data provide no reason to build a more complex investigator yet.

The sample remains six known defects on one host and ten blocks per subject. Warm-state/load effects and stochastic scheduling may matter. Fixed GOMAXPROCS=16 under a two-CPU bandwidth cap is one explicit operational configuration, not all possible resource tuning. The launch record discloses source-review-only oracle specificity under constrained CPU and no positive observed witness for k8s26980. Fixed-version passes do not eliminate these limits. etcd7492 is a controlled historical-fix reversal, despite its general artifact-readiness label.

**Recommended next action:** close and preserve C1 as a completed pilot. If pursuing C4, write a separate, prospectively powered confirmation protocol around the etcd5509 signal, first checking that its witnesses discriminate the defect from generic CPU delay. Include fresh data and a predeclared transfer subject or host; do not append blocks to this pilot until a desired interval appears. No confirmation run is authorized or started by this report.
