# AS-BUILT recipe for image `k8s26980-fix` (V_ok = merge commit 628af356).
# Deviations from GoReal (disclosed in task5_k8s26980_restoration.md): a shallow
# fetch of the exact commit instead of a full clone + reset; no `apt install
# rsync vim python3` (unused by `go test`). GOPATH mode with the revision's own
# vendor/ tree (Godeps), so dependencies are pinned in-tree. Same golang:1.12
# toolchain as GoReal, identical on both images.
FROM golang:1.12
ENV GO111MODULE=off
RUN git init -q /go/src/k8s.io/kubernetes
WORKDIR /go/src/k8s.io/kubernetes
RUN git remote add origin https://github.com/kubernetes/kubernetes.git && \
    git fetch -q --depth 1 origin 628af356b8c83f98ee3b50dfcf8b0250816a5581 && \
    git checkout -q FETCH_HEAD
RUN go test ./pkg/controller/framework -c -o /go/gobench.test
RUN { go version; git rev-parse HEAD; git hash-object pkg/controller/framework/shared_informer.go pkg/controller/framework/processor_listener_test.go Godeps/Godeps.json; } > /go/blob_check.txt
WORKDIR /go/src/k8s.io/kubernetes/pkg/controller/framework
