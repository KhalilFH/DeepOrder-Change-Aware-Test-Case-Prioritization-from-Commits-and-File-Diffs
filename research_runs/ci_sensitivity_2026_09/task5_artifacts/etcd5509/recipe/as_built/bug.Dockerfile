# AS-BUILT recipe for image `etcd5509-bug`, reconstructed from its layer
# history (`docker history --no-trunc`) on 2026-09-22.
#
# This is the effective build, including every disclosed deviation from
# the GoReal original, which is kept alongside for comparison. It is a
# faithful reconstruction of the executed steps, not a byte copy of the
# file that was fed to `docker build`; base-image layers are collapsed
# into the FROM line.

FROM golang:1.10
RUN git clone https://github.com/etcd-io/etcd.git /go/src/github.com/coreos/etcd
WORKDIR /go/src/github.com/coreos/etcd
RUN git reset --hard 9ed3b446cadd9f43734d9eed9dcb03f3b12567a5
COPY ./bug_patch.diff github.com/coreos/etcd/bug_patch.diff
RUN git apply github.com/coreos/etcd/bug_patch.diff
RUN sed -i '167s/fmt_tests/# fmt_tests/' test &&     sed -i '170s/unit_tests/# unit_tests/' test &&     sed -i '73,74d' test &&     sed -i '72 igo test \${REPO_PATH}/clientv3/integration -c -o /go/gobench.test' test &&     sed -i '73 iexit 0' test &&     sed -i '66,71d' test
RUN INTEGRATION=1 ./test
WORKDIR /go/src/github.com/coreos/etcd/./clientv3/integration
