FROM golang:1.13
# Clone the project to local
RUN git clone https://github.com/etcd-io/etcd.git /go/src/github.com/coreos/etcd

# Install package dependencies
# DISCLOSED DEVIATION (Task 5, etcd-7492, 2026-09-19): the original recipe's
# "RUN apt-get update && apt-get install -y vim python3" step is dropped here.
# Neither vim nor python3 is referenced by any later build or test step in this
# Dockerfile (only `sed`, then `PKG=./auth PASSES='build unit' ./test`), and
# Debian's apt archives for this base image's release are not guaranteed
# reachable on this host/date. Same class of deviation as disclosed for
# etcd-5509's fix.Dockerfile in task5_etcd5509_restoration.md Step 2.

# Clone git porject dependencies


# Get go package dependencies


# Checkout the fixed version of this bug
WORKDIR /go/src/github.com/coreos/etcd
RUN git reset --hard 148c923c72c4aa9207173c03b775e2c0b8754067




RUN sed -i '72 igo test ./auth -c -o /go/gobench.test' test && \
	sed -i '73 iexit 0' test && \
	PKG=./auth PASSES='build unit' ./test
