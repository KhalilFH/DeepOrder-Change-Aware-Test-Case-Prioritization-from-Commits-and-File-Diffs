FROM golang:1.10
# Clone the project to local
RUN git clone https://github.com/etcd-io/etcd.git /go/src/github.com/coreos/etcd

# Install package dependencies
# DEVIATION (disclosed, Task 5 restoration 2026-09-19): the original recipe's
# `apt-get install -y vim python3` step is dropped. Debian stretch's apt
# archives are no longer served (404 on deb.debian.org / security.debian.org
# as of 2026-09-19); vim and python3 are never invoked by any later build or
# test-execution step in this Dockerfile, so this is a build-environment fix,
# not a change to the etcd source, toolchain (golang:1.10), pinned commit, or
# test target.

# Clone git porject dependencies


# Get go package dependencies


# Checkout the fixed version of this bug
WORKDIR /go/src/github.com/coreos/etcd
RUN git reset --hard 9ed3b446cadd9f43734d9eed9dcb03f3b12567a5




RUN sed -i '167s/fmt_tests/# fmt_tests/' test && \
	sed -i '170s/unit_tests/# unit_tests/' test && \
	sed -i '73,74d' test && \
	sed -i '72 igo test \${REPO_PATH}/clientv3/integration -c -o /go/gobench.test' test && \
	sed -i '73 iexit 0' test && \
	sed -i '66,71d' test && \
	INTEGRATION=1 ./test