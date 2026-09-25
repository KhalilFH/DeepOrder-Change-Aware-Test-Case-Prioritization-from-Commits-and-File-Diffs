# AS-BUILT recipe for image `k8s26980-bug` (V_bad = first parent 98f0d22b
# product code + the fix's unchanged test). bug_patch.diff is ONLY the
# shared_informer.go hunk of GoReal's patch, which reverses that file to the
# parent's blob ce9ddf2c. GoReal's V_bad-only test edit (t.Errorf -> panic) is
# NOT applied, so processor_listener_test.go is identical on both images.
# Otherwise identical to fix.Dockerfile.
FROM golang:1.12
ENV GO111MODULE=off
RUN git init -q /go/src/k8s.io/kubernetes
WORKDIR /go/src/k8s.io/kubernetes
RUN git remote add origin https://github.com/kubernetes/kubernetes.git && \
    git fetch -q --depth 1 origin 628af356b8c83f98ee3b50dfcf8b0250816a5581 && \
    git checkout -q FETCH_HEAD
COPY bug_patch.diff /tmp/bug_patch.diff
RUN git apply /tmp/bug_patch.diff
RUN go test ./pkg/controller/framework -c -o /go/gobench.test
RUN { go version; git rev-parse HEAD; git hash-object pkg/controller/framework/shared_informer.go pkg/controller/framework/processor_listener_test.go Godeps/Godeps.json; } > /go/blob_check.txt
WORKDIR /go/src/k8s.io/kubernetes/pkg/controller/framework
