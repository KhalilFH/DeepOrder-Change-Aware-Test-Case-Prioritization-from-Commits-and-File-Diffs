FROM golang:1.13
# Clone the project to local
RUN git clone https://github.com/grpc/grpc-go.git /go/src/google.golang.org/grpc


# Clone git porject dependencies


COPY ./deps.txt /tmp/deps.txt
COPY ./deps.sh /tmp/deps.sh
RUN sh /tmp/deps.sh

# Checkout the fixed version of this bug
WORKDIR /go/src/google.golang.org/grpc
RUN git reset --hard 484b3ebb4ab56d3decc8240d599718bdbefcf7eb




RUN go test ./test -c -o /go/gobench.test