#!/bin/sh
# Rebuild a Task 5 subject pair from its as-built recipe.
#
#   ./rebuild.sh etcd5509 | etcd7492 | grpc1859 | all
#
# Builds <candidate>-bug and <candidate>-fix from recipe/as_built/, then runs
# verify.sh on the result. recipe/as_built/ is the
# recipe actually executed during qualification, including every disclosed
# deviation from the GoReal original. recipe/goreal_original/ holds the pristine
# upstream files for comparison; DEVIATIONS.md explains the differences.
#
# NOT bit-reproducible. The base image tag and each subject's `git clone`
# resolve at build time. For grpc1859 the Go dependencies are pinned by
# deps.txt, and the resolved commits are written into the image at
# /go/dep_versions.txt. For the two etcd subjects the dependency state is
# whatever their recipes resolve at build time and was never recorded.
set -e

HERE=$(cd "$(dirname "$0")" && pwd)

build_one() {
    cand=$1
    ctx="$HERE/$cand/recipe/as_built"
    [ -d "$ctx" ] || { echo "no such candidate: $cand" >&2; exit 2; }
    # Build from inside the context so the path stays relative. On Git Bash /
    # MSYS an absolute POSIX path here is mangled before Docker sees it.
    for role in bug fix; do
        echo "=== building $cand-$role"
        (cd "$ctx" && MSYS_NO_PATHCONV=1 docker build -f "$role.Dockerfile" -t "$cand-$role" .)
    done
    echo "=== $cand: verifying the recorded source blobs"
    verify "$cand"
}

# Verification is delegated to verify.sh, which checks all three candidates
# against hashes recomputed from upstream. See VERIFICATION.md.
verify() {
    sh "$HERE/verify.sh" "$1"
}

case ${1:-} in
    all) for c in etcd5509 etcd7492 grpc1859; do build_one "$c"; done ;;
    "")  echo "usage: $0 {etcd5509|etcd7492|grpc1859|all}" >&2; exit 2 ;;
    *)   build_one "$1" ;;
esac
