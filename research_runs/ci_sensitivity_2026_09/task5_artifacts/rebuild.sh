#!/bin/sh
# Rebuild a Task 5 subject pair from its as-built recipe.
#
#   ./rebuild.sh etcd5509 | etcd7492 | grpc1859 | all
#
# Builds <candidate>-bug and <candidate>-fix from recipe/as_built/, which is the
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

# Each subject's expected in-image source blob hashes, as recorded by the
# Task 5 pass that qualified it. A mismatch means the rebuild did not
# reproduce the subject that was measured.
verify() {
    case $1 in
    grpc1859)
        check grpc1859-bug /go/src/google.golang.org/grpc \
            transport/http2_client.go 717e4192ea13547ffe323613d3d4945c9c5a9b00
        check grpc1859-bug /go/src/google.golang.org/grpc \
            transport/http2_server.go 5233d6f3db6bd29622f694a59befd50d9e6d7365
        check grpc1859-fix /go/src/google.golang.org/grpc \
            transport/http2_client.go 56b434ef37fed92f87811d9d08e3c9c834cf9971
        check grpc1859-fix /go/src/google.golang.org/grpc \
            transport/http2_server.go 24c2c7e18c48b007dd8a060cb4e09bfab1a55ebd
        for img in grpc1859-bug grpc1859-fix; do
            check "$img" /go/src/google.golang.org/grpc \
                test/end2end_test.go 6a583182170323ec5b23d760d926c92d3816be18
        done
        ;;
    *)
        echo "    no recorded blob hashes for $1; see its restoration record" ;;
    esac
}

check() {
    img=$1; workdir=$2; file=$3; want=$4
    got=$(MSYS_NO_PATHCONV=1 docker run --rm --entrypoint sh "$img" -c "cd $workdir && git hash-object $file")
    if [ "$got" = "$want" ]; then
        echo "    OK       $img $file"
    else
        echo "    MISMATCH $img $file: got $got want $want" >&2
        exit 1
    fi
}

case ${1:-} in
    all) for c in etcd5509 etcd7492 grpc1859; do build_one "$c"; done ;;
    "")  echo "usage: $0 {etcd5509|etcd7492|grpc1859|all}" >&2; exit 2 ;;
    *)   build_one "$1" ;;
esac
