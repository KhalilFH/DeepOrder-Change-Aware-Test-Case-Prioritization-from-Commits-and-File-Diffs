# Counterpart verification — all three Task 5 subject pairs

Run `./verify.sh all`. It checks existing images and builds nothing.
Last run 2026-09-22: **16 checks, all passed, exit 0.**

Every expected hash below was **recomputed from upstream raw files** during this
verification, not copied from the restoration records, so the records and the
images are checked against a common third source rather than against each other.

## What is checked, per candidate

1. **Focal source blob** in each image equals the declared `V_bad` / `V_ok` blob.
2. **The frozen test file is byte-identical** in both images — the plan's
   "same target test and test source on both versions" requirement.
3. **The bug tree modifies exactly the expected paths** and nothing else.

## Results

| Candidate | File | bug image | fix image |
|---|---|---|---|
| etcd5509 | `clientv3/remote_client.go` | `b8209b8a5e2e` (`V_bad`) | `b511163058cb` (`V_ok`) |
| etcd5509 | `clientv3/integration/kv_test.go` | `24252c428ac5` | identical |
| etcd5509 | `test` (harness script) | `450298e284ef` | identical |
| etcd7492 | `auth/simple_token.go` | `7aa807947713` (`V_bad`) | `ff48c5140cbe` (`V_ok`) |
| etcd7492 | `auth/store_test.go` | `d7a1d563817c` | identical |
| etcd7492 | `test` (harness script) | `dd4beae0a37f` | identical |
| grpc1859 | `transport/http2_client.go` | `717e4192ea13` (`V_bad`) | `56b434ef37fe` (`V_ok`) |
| grpc1859 | `transport/http2_server.go` | `5233d6f3db6b` (`V_bad`) | `24c2c7e18c48` (`V_ok`) |
| grpc1859 | `test/end2end_test.go` | `6a5831821703` | identical |

Working-tree deltas in each bug image, relative to its checked-out commit:

| Candidate | Modified paths |
|---|---|
| etcd5509 | `clientv3/remote_client.go`, `test` |
| etcd7492 | `auth/simple_token.go`, `test` |
| grpc1859 | `transport/http2_client.go`, `transport/http2_server.go` |

In every case the only modified *source* file is the focal production file. The
`test` entry in the two etcd rows is GoReal's `sed`-trimmed build script, and it
is byte-identical between the bug and fix images of each pair, so it is a
constant of the pair rather than a difference between the variants.

## A gap this closed

**etcd-5509's blob-equivalence check had never been run against its images.**
`task5_etcd5509_restoration.md` Step 1 states plainly that it was "performed via
the GitHub contents API (no local clone needed for this check)". That confirmed
GoReal's patch header named the right upstream blobs; it did not confirm the
built images actually contained them. The qualifying evidence for the roster's
first qualified episode therefore rested on patch metadata plus the assumption
that `docker build` did what the recipe said.

It did — all four etcd-5509 checks pass — but that is now a measured fact rather
than an inference. etcd-7492 had already re-verified against its built `bug`
image (its Step 1 item 4), and that result reproduces independently here.

`task5_grpc1859_restoration.md` verified in-image blobs as part of its Step 1,
so this adds only the test-file and tree-delta checks for that candidate.

## etcd-7492's expected `V_bad` blob is deliberately not the parent's

`7aa8079477132dec7447507a310394b49fa8ef33`, not the historical parent's
`5b608af92c732e9a840bf43d2e65c1372d62b5a2`. The difference is the declared
`const`→`var` move of `simpleTokenTTL` and `simpleTokenTTLResolution`, without
which the frozen test does not compile on the defective variant. This is why
that candidate is recorded as a *controlled historical-fix reversal* and never
as a historical pair. The expected value was derived here by applying GoReal's
reverse patch to the pinned-base file, reproducing the card's declaration.

## Known, inert asymmetry

Each **bug** image carries one untracked file the fix image does not:
`bug_patch.diff`, copied into a nested path inside the source tree
(`github.com/coreos/etcd/bug_patch.diff`, `google.golang.org/grpc/bug_patch.diff`)
by GoReal's `COPY` step. It is a single text file, contains no Go source, and is
read by no build or test step.

It is disclosed rather than removed: the images that produced the measured
qualification results contain it, and altering the recipe to tidy it away would
mean the preserved recipe no longer describes what was measured.

## Limits

- Verification covers the **source** the images contain, not the toolchain or
  dependency state around it. For the two etcd candidates the Go dependency
  state was never recorded and cannot be verified retrospectively (ledger A13).
- A passing check confirms the images match the declared revisions. It says
  nothing about whether the qualification *outcome* would reproduce; failure
  rates are host- and timing-dependent, and for grpc-go-1859 the measured rate
  was 1/20.
