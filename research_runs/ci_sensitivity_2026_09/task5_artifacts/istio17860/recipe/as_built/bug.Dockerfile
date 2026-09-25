# AS-BUILT recipe for image `istio17860-bug`. Identical environment on both versions:
# shallow fetch of squash-merge c6e91302, module mode from its own go.mod/go.sum.
# V_bad applies ONLY the agent.go hunks of GoReal's bug_patch.diff (upstream test unchanged).
FROM golang:1.13
ENV GO111MODULE=on
RUN git init -q /go/src/istio.io/istio
WORKDIR /go/src/istio.io/istio
RUN git remote add origin https://github.com/istio/istio.git && \
    git fetch -q --depth 1 origin c6e9130227497ab064dd571a1409236d17aa2ef3 && \
    git checkout -q FETCH_HEAD
COPY bug_patch_agent_only.diff /tmp/bug_patch.diff
RUN git apply /tmp/bug_patch.diff
# bitbucket.org/ww/goautoneg is no longer served (build attempt 1: 404); same replace as GoReal, on BOTH images.
RUN echo 'replace bitbucket.org/ww/goautoneg => github.com/munnerz/goautoneg v0.0.0-20191010083416-a7dc8b61c822' >> go.mod
RUN go test ./pkg/envoy -c -o /go/gobench.test
RUN go list -m all > /go/dep_versions.txt && \
    { git rev-parse HEAD; git hash-object pkg/envoy/agent.go pkg/envoy/agent_test.go; } > /go/blob_check.txt
