# Recipe deviations — GoReal original vs as-built

Every difference between `recipe/goreal_original/` and `recipe/as_built/`, per
candidate. These are the deviations the three Task 5 restoration records
disclose in prose; this file is the machine-checkable form.

Reproduce any row with:

```bash
diff research_runs/ci_sensitivity_2026_09/task5_artifacts/<cand>/recipe/goreal_original/<file> \
     research_runs/ci_sensitivity_2026_09/task5_artifacts/<cand>/recipe/as_built/<file>
```

## Provenance of each directory

- **`recipe/goreal_original/`** — byte-identical to the GoBench blobs at pinned
  commit `2e91eb10b8e7b2873ea44f12b87ec1b2520e1b69`, verified by
  `git hash-object`:

  | Candidate | `bug.Dockerfile` | `fix.Dockerfile` | `bug_patch.diff` |
  |---|---|---|---|
  | etcd5509 | `9971b8680206` | `dbe4f7f4a405` | `2bf346f565b2` |
  | etcd7492 | `cfa1cbc0d715` | `4a90c5c6f673` | `9a16d57c24c8` |
  | grpc1859 | `177f2248fa03` | `c3ea2898d1df` | `bb72cba21a09` |

- **`recipe/as_built/`** — the recipe actually executed. The `*.Dockerfile`
  files are reconstructed from each image's layer history
  (`docker history --no-trunc`, 2026-09-22), so they are a faithful record of
  the executed steps rather than a byte copy of the file fed to `docker build`;
  base-image layers are collapsed into the `FROM` line and shell line
  continuations appear collapsed onto one line. Where the literal file that was
  fed to `docker build` also survives it is kept alongside as
  `*.Dockerfile.literal`.

  **A correction this reorganisation surfaced.** The etcd-5509 pass edited its
  Dockerfiles *in place inside the GoBench clone* rather than in a separate
  build context. The files first salvaged as that candidate's "originals" were
  therefore the edited ones (CRLF, with an inline disclosure comment, apt step
  removed). They have been replaced with the authoritative pinned blobs and
  preserved as `as_built/{bug,fix}.Dockerfile.literal`. Nothing about the
  qualification result changes; the earlier labelling was wrong and is now
  right.

## etcd-5509

Both deviations are disclosed in `task5_etcd5509_restoration.md` Step 2.

1. **`bug_patch.diff` line-ending normalisation.** The Windows checkout
   (`core.autocrlf=true`) converted the patch to CRLF, which broke `git apply`
   inside the Linux `golang:1.10` container (`patch failed:
   clientv3/remote_client.go:80`). The CR bytes were stripped before the patch
   entered the build context. Content identical modulo CR; the etcd source,
   pinned commit and patch semantics are untouched. Both forms are preserved:
   `as_built/bug_patch.diff` (LF, applied) and
   `goreal_original/bug_patch.diff.orig_crlf` (the contaminated checkout).
2. **Dropped `apt-get install -y vim python3` from `fix.Dockerfile`.** Debian
   stretch's apt archives stopped being served (404 on `deb.debian.org` and
   `security.debian.org` as of 2026-09-19). Neither package is invoked by any
   later build or test step.

No other deviation. The `sed`-trimmed `test` script and
`INTEGRATION=1 ./test` build step are unchanged from the original.

## etcd-7492

Disclosed in `task5_etcd7492_restoration.md` Step 2.

1. **Dropped `apt-get install -y vim python3` from `fix.Dockerfile`**, for the
   same reason as etcd-5509 and with the same absence of any later reference to
   either package. The literal file with its inline disclosure comment is kept
   as `as_built/fix.Dockerfile.literal`.

No other deviation. `bug.Dockerfile` is unchanged; this candidate's
`bug_patch.diff` needed no CRLF fix (0 CR bytes in the checkout).

## grpc-go-1859

Disclosed in `task5_grpc1859_restoration.md` Step 2.

1. **Dropped `apt-get install -y vim python3` from `fix.Dockerfile`.** Also
   makes the two recipes symmetric, since `bug.Dockerfile` never had the step.
2. **Replaced the unpinned dependency step with identical pinned clones in both
   images.** This was *forced, not chosen*: the original
   `go get -v -d …` of master heads fails on `golang:1.13` with
   `package embed: unrecognized import path "embed"`, because current
   `golang/protobuf` master depends on `google.golang.org/protobuf`, which
   requires Go 1.16+. Card C-03 pre-declared this contingency. Each dependency
   is pinned to its last commit on or before 2018-02-13, the subject's merge
   date — closer to the historical environment than master heads would have
   been. See `as_built/deps.txt` and `as_built/deps.sh`.

   | Package | Commit | Date |
   |---|---|---|
   | `github.com/golang/glog` | `23def4e6c14b4da8ac2ed8007337bc5eb5007998` | 2016-01-26 |
   | `github.com/golang/protobuf` | `e6af52bec88380a7a18ecc0977fa4312370a970b` | 2018-02-07 |
   | `golang.org/x/net` | `f5dfe339be1d06f81b22525fe34671ee7d2c8904` | 2018-02-08 |
   | `google.golang.org/genproto` | `2b5a72b8730b0b16380010cfe5286c42108d88e7` | 2018-02-06 |
   | `golang.org/x/text` | `4e4a3210bb54bb31f6ab2cdca2edcc0b50c420c1` | 2018-02-08 |

   `golang.org/x/text` is **not** in GoReal's list; it was added because
   `x/net/idna` requires it and the original `go get` pulled it transitively.
   `deps.sh` writes the resolved commits into the image at
   `/go/dep_versions.txt`, which was verified byte-identical between the two
   images.

No `sed` edits to the subject, and no change to the test source: the frozen
test file is byte-identical in both images (`6a583182…`).

## Verified rebuild

`rebuild.sh <candidate>` rebuilds a pair from `recipe/as_built/`. For
grpc-go-1859 it then checks the in-image source blobs against the hashes the
qualification pass recorded, and fails loudly on a mismatch. Confirmed passing
on 2026-09-22 from a clean invocation:

```
=== grpc1859: verifying the recorded source blobs
    OK       grpc1859-bug transport/http2_client.go
    OK       grpc1859-bug transport/http2_server.go
    OK       grpc1859-fix transport/http2_client.go
    OK       grpc1859-fix transport/http2_server.go
    OK       grpc1859-bug test/end2end_test.go
    OK       grpc1859-fix test/end2end_test.go
```

The two etcd candidates have no recorded per-file blob hashes to check against,
so `rebuild.sh` says so rather than implying a verification it cannot perform.

## Limits

A rebuild is **not** bit-reproducible. The base image tag and each subject's
`git clone` resolve at build time. For grpc-go-1859 the Go dependency state is
pinned and recorded; for the two etcd candidates it is whatever their recipes
resolved on 2026-09-19 and was never captured, so ledger A13's dependency gap
stays open for them and cannot now be closed retrospectively.
