# AS-BUILT recipe for image `grpc1859-fix`, reconstructed from its layer
# history (`docker history --no-trunc`) on 2026-09-22.
#
# This is the effective build, including every disclosed deviation from
# the GoReal original, which is kept alongside for comparison. It is a
# faithful reconstruction of the executed steps, not a byte copy of the
# file that was fed to `docker build`; base-image layers are collapsed
# into the FROM line.

FROM golang:1.13
RUN git clone https://github.com/grpc/grpc-go.git /go/src/google.golang.org/grpc
COPY ./deps.txt /tmp/deps.txt
COPY ./deps.sh /tmp/deps.sh
RUN sh /tmp/deps.sh
WORKDIR /go/src/google.golang.org/grpc
RUN git reset --hard 484b3ebb4ab56d3decc8240d599718bdbefcf7eb
RUN go test ./test -c -o /go/gobench.test
