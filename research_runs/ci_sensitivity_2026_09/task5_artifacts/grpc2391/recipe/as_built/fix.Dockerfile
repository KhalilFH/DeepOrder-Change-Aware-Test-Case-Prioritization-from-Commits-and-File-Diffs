# AS-BUILT recipe for image `grpc2391-fix` (V_ok = squash-merge ff2aa059).
# Deviation from GoReal (disclosed in task5_grpc2391_restoration.md): module
# mode from the revision's own go.mod instead of unpinned `go get -d` heads,
# and a shallow fetch of the exact commit instead of a full clone + reset.
FROM golang:1.13
ENV GO111MODULE=on
RUN git init -q /go/src/google.golang.org/grpc
WORKDIR /go/src/google.golang.org/grpc
RUN git remote add origin https://github.com/grpc/grpc-go.git && \
    git fetch -q --depth 1 origin ff2aa05958775030998dbe2f9bccbe2af324adf4 && \
    git checkout -q FETCH_HEAD
RUN go test ./test -c -o /go/gobench.test
RUN go list -m all > /go/dep_versions.txt && \
    { git rev-parse HEAD; git hash-object clientconn.go test/end2end_test.go; } > /go/blob_check.txt
