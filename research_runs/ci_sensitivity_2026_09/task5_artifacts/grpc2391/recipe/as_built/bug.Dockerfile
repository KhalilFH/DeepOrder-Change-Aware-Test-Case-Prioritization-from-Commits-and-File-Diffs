# AS-BUILT recipe for image `grpc2391-bug` (V_bad = parent 39444b99 product
# code + the fix's test, via GoReal's bug_patch.diff, which re-adds exactly the
# three lines the fix removed from clientconn.go and touches nothing else).
# Same deviations as fix.Dockerfile; the go.mod is identical at both revisions.
FROM golang:1.13
ENV GO111MODULE=on
RUN git init -q /go/src/google.golang.org/grpc
WORKDIR /go/src/google.golang.org/grpc
RUN git remote add origin https://github.com/grpc/grpc-go.git && \
    git fetch -q --depth 1 origin ff2aa05958775030998dbe2f9bccbe2af324adf4 && \
    git checkout -q FETCH_HEAD
COPY bug_patch.diff /tmp/bug_patch.diff
RUN git apply /tmp/bug_patch.diff
RUN go test ./test -c -o /go/gobench.test
RUN go list -m all > /go/dep_versions.txt && \
    { git rev-parse HEAD; git hash-object clientconn.go test/end2end_test.go; } > /go/blob_check.txt
