# C1 subject register and qualification dossier

## Material Passport

- Date: 2026-09-25; status: design frozen v1, **all current readiness checks pending**.
- Historical observations below are inherited evidence, not fresh image verification or enrollment.
- Roster and order are fixed by [protocol.md](protocol.md). No new candidates.

## Fixed roster

All commands invoke `/go/gobench.test -test.v -test.count 1`, followed by the arguments below. Preserve the original regexp spelling. Each row uses the same test binary source, command, workdir and timeouts across variants/profiles; production code differs only by the documented defect/fix.

| Subject/project | Historical counterpart class | Old bad focal/pass | Target arguments | Workdir | Inner / outer seconds |
|---|---|---|---|---|---|
| etcd5509 / etcd | historical pair, identical test backport | 16/4 | `-test.run TestKVGetErrConnClosed -test.timeout 45s` | `/go/src/github.com/coreos/etcd/clientv3/integration` | 45 / 60 |
| etcd7492 / etcd | controlled historical-fix reversal, not exact historical parent | 2/18 | `-test.run TestHammerSimpleAuthenticate -test.timeout 50s` | `/go/src/github.com/coreos/etcd/auth` | 50 / 65 |
| grpc1859 / grpc-go | historical pair, identical test backport | 1/19 | `-test.run ^TestClientDoesntDeadlockWhileWritingErrornousLargeMessages$ -test.timeout 110s -only_env tcp-clear-v1-balancer` | `/go/src/google.golang.org/grpc/test` | 110 / 120 |
| grpc2391 / grpc-go | historical pair, identical test backport | 18/2 | `-test.run ^TestGoAwayThenClose$ -test.timeout 60s` | `/go/src/google.golang.org/grpc/test` | 60 / 90 |
| istio17860 / istio | historical production pair, identical fix test | 20/0 | `-test.run ^TestExitDuringWaitForLive$ -test.timeout 30s` | `/go/src/istio.io/istio/pkg/envoy` | 30 / 60 |
| k8s26980 / Kubernetes | historical parent production plus identical fix test | 0/20 | `-test.run ^TestPopReleaseLock$ -test.timeout 60s` | `/go/src/k8s.io/kubernetes/pkg/controller/framework` | 60 / 90 |

Outer 120 seconds for grpc1859 is the adopted C1 setting above its 110-second inner timeout; verify cleanup and dump capture at calibration. Historical Q0 did not use all these outer limits. Per-container cleanup has a separate 30-second maximum. Pass commands as argument arrays in future implementation, not shell interpolation.

All six old acceptable variants passed 20/20. This does not establish freedom from defects or nuisance, or predict behavior under L. The old labels `Q0_NOT_QUALIFIED` and `STABLE_CONTROL_ONLY` remain unchanged; C1 structural eligibility is a different criterion.

## Source map and unresolved checks

| Subject | Authoritative starting record | Specific C1 work |
|---|---|---|
| etcd5509 | [restoration](../ci_sensitivity_2026_09/task5_etcd5509_restoration.md), [E1 manifests](../ci_sensitivity_2026_09/e1/manifests.json) | Check historical image IDs against surviving images; enumerate actual dependencies. Q0 linkage used timestamps, and old dependency pins are incomplete. If rebuilding, document new provenance rather than claiming byte-identical recovery. Retain both disclosed signature corrections. |
| etcd7492 | [restoration](../ci_sensitivity_2026_09/task5_etcd7492_restoration.md), E1 manifests above | Preserve controlled-reversal classification and const/var deviation; directly hash the test on both variants. Same dependency/image gap as etcd5509. |
| grpc1859 | [restoration](../ci_sensitivity_2026_09/task5_grpc1859_restoration.md) | Verify dated dependency pins and production/test blobs. Keep the clear-text environment restriction; expired TLS certificates are a harness issue, not the focal quota defect. Do not choose the alternate environment because it failed more often. |
| grpc2391 | [restoration](../ci_sensitivity_2026_09/task5_grpc2391_restoration.md), [frozen command](../ci_sensitivity_2026_09/task5_artifacts/grpc2391/run/frozen_protocol.txt) | Verify pinned dependencies and unchanged test. Port the card's target-specific `UnaryCall`/`DeadlineExceeded` expectation, then assess whether generic CPU slowness can satisfy it. |
| istio17860 | [restoration](../ci_sensitivity_2026_09/task5_istio17860_restoration.md), [frozen command](../ci_sensitivity_2026_09/task5_artifacts/istio17860/run/frozen_protocol.txt) | Verify identical dependency replacement in both images and unchanged fix test. Preserve focal epoch-start expectation; unrelated `BeTemporally` failures remain unresolved absent independent evidence. |
| k8s26980 | [restoration](../ci_sensitivity_2026_09/task5_k8s26980_restoration.md), [frozen command](../ci_sensitivity_2026_09/task5_artifacts/k8s26980/run/frozen_protocol.txt) | Verify production-only patch and identical test: do not restore GoReal's bad-only test mutation. No old positive witness exists. Its timeout signature requires source-level specificity review; do not invent a witnessed calibration success. |

Recipes and logs live under [task5_artifacts](../ci_sensitivity_2026_09/task5_artifacts/). Its old README and helper scripts originally covered only three subjects; inspect actual dispatch before reusing a command for all six. Tags and build recipes alone do not prove an image is still locally available.

## Dossier required for each subject before freeze

Produce one entry in future `subject_manifest.json`, with evidence paths for every substantive claim:

- Subject/project; upstream issue, introducing/fixing revision where established; exact counterpart class and justification. Unknown introducing revisions stay unknown.
- Production blob IDs on each variant; test and harness file hashes proving equal treatment; allowed source diff and all reconstruction deviations.
- Image ID and archive/rebuild location, base image digest, test binary SHA-256, compiler/runtime version, dependency versions/hashes. Archive images outside Git if feasible; record archive checksum and access path.
- Actual workdir and literal argv array from the table; outer timeout, cleanup timeout, expected target identity.
- Behavioral obligation, independently sourced defect mechanism, exact oracle version/hash, signatures, possible competing explanations and source evidence excluding them where possible.
- Source-level assessment of whether the obligation and deadlines apply under both profiles. A timeout text by itself is not proof of a deadlock. A profile whose timing assumptions cannot be justified can yield unresolved observations; do not strengthen the oracle to force enrollment.
- Existing logs available for replay, including passes, focal failures and non-focal/harness failures. Mark missing positive logs explicitly, particularly k8s26980.
- Fresh readiness disposition: `READY_HISTORICAL`, `READY_RECONSTRUCTED`, `UNAVAILABLE`, or `UNRESOLVED`; reason and reviewer/date. These labels do not overwrite Q0 labels.

An exact historical image can be retained as a pinned artifact even if some old build provenance is incomplete; the limitation must be visible. A newly rebuilt pair must pin equal dependencies across variants and revalidate the causal production difference. If equivalence cannot be established within preparation limits, exclude structurally with a reason. Never combine old-image R with rebuilt-image L.

## Oracle validation policy

The existing [oracle module](../../e1_harness/oracle.py) has cards for etcd5509, etcd7492 and grpc1859. It does not yet implement all six subjects. The other subjects' shell classifiers provide starting evidence, not validated C1 oracle code.

Port rules mechanically before measured observations; replay all available old logs and record agreement/disagreement. Include existing expired-certificate logs and signature-removal negative tests. Artificial log fixtures may verify parsing but never count as empirical product-defect evidence. A source review can establish a proposed rule without a positive runtime example; retain that weaker validation status.

Predeclared signatures can still be invalid under a new profile. If an acceptable variant matches a focal rule, preserve the mechanical match, flag the pair, and pause its collection. Adjudicate the competing explanation using source and logs. Do not change the frozen rule and quietly regenerate a successful primary analysis. Any revised oracle analysis is a separately labelled amendment/sensitivity analysis.
