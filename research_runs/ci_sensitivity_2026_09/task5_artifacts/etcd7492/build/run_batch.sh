#!/bin/bash
# Usage: run_batch.sh <image> <version_label> <start_index> <count> <csv_out>
set -u
IMAGE="$1"
VERSION="$2"
START="$3"
COUNT="$4"
CSV="$5"
TIMEOUT=50

for ((i=0; i<COUNT; i++)); do
  idx=$((START + i))
  LOGFILE="attempts/${VERSION}_attempt_${idx}.log"
  START_TS=$(date -u +"%Y-%m-%dT%H:%M:%S.%NZ")
  T0=$(date +%s.%N)
  docker run --rm -w /go/src/github.com/coreos/etcd/auth "$IMAGE" /go/gobench.test -test.v -test.count 1 -test.run TestHammerSimpleAuthenticate -test.timeout ${TIMEOUT}s > "$LOGFILE" 2>&1
  EXIT=$?
  T1=$(date +%s.%N)
  END_TS=$(date -u +"%Y-%m-%dT%H:%M:%S.%NZ")
  ELAPSED=$(awk -v a="$T0" -v b="$T1" 'BEGIN{printf "%.3f", b-a}')
  echo "${VERSION},${idx},${START_TS},${END_TS},${ELAPSED},${EXIT},${LOGFILE}" >> "$CSV"
  echo "  [$VERSION #$idx] exit=$EXIT elapsed=${ELAPSED}s"
done
