FROM golang:1.13
# Clone the project to local
RUN git clone https://github.com/grpc/grpc-go.git /go/src/google.golang.org/grpc




COPY ./deps.txt /tmp/deps.txt
COPY ./deps.sh /tmp/deps.sh
RUN sh /tmp/deps.sh
WORKDIR /go/src/google.golang.org/grpc

# Rollback to the latest bug-free version
RUN git reset --hard 484b3ebb4ab56d3decc8240d599718bdbefcf7eb

# Apply the revert patch to this bug
COPY ./bug_patch.diff google.golang.org/grpc/bug_patch.diff
RUN git apply google.golang.org/grpc/bug_patch.diff


# Build
RUN go test ./test -c -o /go/gobench.test

# For entrypoint
WORKDIR /go/src/google.golang.org/grpc/./test
