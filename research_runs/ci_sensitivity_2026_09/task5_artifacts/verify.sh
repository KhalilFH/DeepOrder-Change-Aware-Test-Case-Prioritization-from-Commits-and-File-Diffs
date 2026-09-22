#!/bin/sh
# Verify that a Task 5 subject pair's images contain the sources they should.
#
#   ./verify.sh {etcd5509|etcd7492|grpc1859|all}
#
# Checks three things per candidate, against values recomputed from upstream
# (not copied from the restoration records):
#
#   1. Focal source blob in each image equals the declared V_bad / V_ok blob.
#   2. The frozen test file is byte-identical in both images.
#   3. The pair's working trees differ in the focal production file only.
#
# Runs against existing images; it builds nothing. Exit 0 = all checks passed.
set -e

FAIL=0

chk() { # image workdir file expected label
    got=$(MSYS_NO_PATHCONV=1 docker run --rm --entrypoint sh "$1" \
              -c "cd $2 && git hash-object $3" 2>/dev/null | tr -d '\r')
    if [ "$got" = "$4" ]; then
        printf '  OK        %-14s %-32s %s  %s\n' "$1" "$3" "$(echo "$got" | cut -c1-12)" "$5"
    else
        printf '  MISMATCH  %-14s %-32s got=%s want=%s\n' "$1" "$3" "$got" "$4" >&2
        FAIL=1
    fi
}

same() { # candidate workdir file  -- must be identical in bug and fix
    b=$(MSYS_NO_PATHCONV=1 docker run --rm --entrypoint sh "$1-bug" -c "cd $2 && git hash-object $3" 2>/dev/null | tr -d '\r')
    f=$(MSYS_NO_PATHCONV=1 docker run --rm --entrypoint sh "$1-fix" -c "cd $2 && git hash-object $3" 2>/dev/null | tr -d '\r')
    if [ "$b" = "$f" ] && [ -n "$b" ]; then
        printf '  OK        %-14s %-32s %s  identical in both variants\n' "$1" "$3" "$(echo "$b" | cut -c1-12)"
    else
        printf '  MISMATCH  %-14s %-32s bug=%s fix=%s\n' "$1" "$3" "$b" "$f" >&2
        FAIL=1
    fi
}

tree_delta() { # candidate workdir expected-modified-paths...
    cand=$1; wd=$2; shift 2
    got=$(MSYS_NO_PATHCONV=1 docker run --rm --entrypoint sh "$cand-bug" \
              -c "cd $wd && git status --porcelain" 2>/dev/null \
          | tr -d '\r' | awk '$1=="M"{print $2}' | sort | tr '\n' ' ' | sed 's/ *$//')
    want=$(printf '%s\n' "$@" | sort | tr '\n' ' ' | sed 's/ *$//')
    if [ "$got" = "$want" ]; then
        printf '  OK        %-14s bug tree modifies exactly: %s\n' "$cand" "$got"
    else
        printf '  MISMATCH  %-14s bug tree modifies: [%s] want: [%s]\n' "$cand" "$got" "$want" >&2
        FAIL=1
    fi
}

E=/go/src/github.com/coreos/etcd
G=/go/src/google.golang.org/grpc

v_etcd5509() {
    echo "=== etcd5509 (historical pair; V_bad 36fcc9e9, V_ok merge 9ed3b446)"
    chk etcd5509-bug $E clientv3/remote_client.go b8209b8a5e2ebefcac268b64e0a62482266b9a3d "V_bad"
    chk etcd5509-fix $E clientv3/remote_client.go b511163058cb31ebab14f42869e6e99d1b9dff68 "V_ok"
    same etcd5509 $E clientv3/integration/kv_test.go
    same etcd5509 $E test
    tree_delta etcd5509 $E clientv3/remote_client.go test
}

v_etcd7492() {
    echo "=== etcd7492 (controlled reversal on pinned base 148c923c; declared const->var)"
    # Not the parent blob 5b608af9: the card declares a const->var move that
    # keeps the frozen test compilable on both variants.
    chk etcd7492-bug $E auth/simple_token.go 7aa8079477132dec7447507a310394b49fa8ef33 "V_bad = parent + declared const->var"
    chk etcd7492-fix $E auth/simple_token.go ff48c5140cbe103af6297990fd406a641d529631 "V_ok"
    same etcd7492 $E auth/store_test.go
    same etcd7492 $E test
    tree_delta etcd7492 $E auth/simple_token.go test
}

v_grpc1859() {
    echo "=== grpc1859 (historical pair; V_bad parent 6c48c7f5, V_ok merge 484b3ebb)"
    chk grpc1859-bug $G transport/http2_client.go 717e4192ea13547ffe323613d3d4945c9c5a9b00 "V_bad"
    chk grpc1859-bug $G transport/http2_server.go 5233d6f3db6bd29622f694a59befd50d9e6d7365 "V_bad"
    chk grpc1859-fix $G transport/http2_client.go 56b434ef37fed92f87811d9d08e3c9c834cf9971 "V_ok"
    chk grpc1859-fix $G transport/http2_server.go 24c2c7e18c48b007dd8a060cb4e09bfab1a55ebd "V_ok"
    same grpc1859 $G test/end2end_test.go
    tree_delta grpc1859 $G transport/http2_client.go transport/http2_server.go
}

case ${1:-} in
    all)       v_etcd5509; v_etcd7492; v_grpc1859 ;;
    etcd5509)  v_etcd5509 ;;
    etcd7492)  v_etcd7492 ;;
    grpc1859)  v_grpc1859 ;;
    *) echo "usage: $0 {etcd5509|etcd7492|grpc1859|all}" >&2; exit 2 ;;
esac

if [ "$FAIL" -eq 0 ]; then echo "ALL CHECKS PASSED"; else echo "CHECKS FAILED" >&2; fi
exit $FAIL
