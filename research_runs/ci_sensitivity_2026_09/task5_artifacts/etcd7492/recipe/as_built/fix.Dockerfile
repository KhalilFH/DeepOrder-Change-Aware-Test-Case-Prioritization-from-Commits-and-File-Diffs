# AS-BUILT recipe for image `etcd7492-fix`, reconstructed from its layer
# history (`docker history --no-trunc`) on 2026-09-22.
#
# This is the effective build, including every disclosed deviation from
# the GoReal original, which is kept alongside for comparison. It is a
# faithful reconstruction of the executed steps, not a byte copy of the
# file that was fed to `docker build`; base-image layers are collapsed
# into the FROM line.

FROM golang:1.13
RUN git clone https://github.com/etcd-io/etcd.git /go/src/github.com/coreos/etcd
WORKDIR /go/src/github.com/coreos/etcd
RUN git reset --hard 148c923c72c4aa9207173c03b775e2c0b8754067
RUN sed -i '72 igo test ./auth -c -o /go/gobench.test' test &&  sed -i '73 iexit 0' test &&  PKG=./auth PASSES='build unit' ./test
