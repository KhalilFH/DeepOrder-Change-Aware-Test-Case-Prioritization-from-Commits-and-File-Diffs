#!/bin/sh
# $1=image $2=version_label $3=attempt_no $4=logdir $5=csv   (card C-06, frozen protocol)
img=$1; ver=$2; n=$3; ld=$4; csv=$5
log="$ld/${ver}_$(printf %02d $n).log"
s=$(date -u +%s%N); st=$(date -u +%Y-%m-%dT%H:%M:%S.%NZ)
MSYS_NO_PATHCONV=1 timeout 90 docker run --rm -w /go/src/k8s.io/kubernetes/pkg/controller/framework "$img" \
  /go/gobench.test -test.v -test.count 1 -test.run '^TestPopReleaseLock$' -test.timeout 60s > "$log" 2>&1
rc=$?; e=$(date -u +%s%N); et=$(date -u +%Y-%m-%dT%H:%M:%S.%NZ)
el=$(awk "BEGIN{printf \"%.3f\",($e-$s)/1000000000}")
if ! grep -q '^=== RUN   TestPopReleaseLock$' "$log" || grep -q 'docker: Error' "$log"; then cls=HARNESS_INVALID
elif [ $rc -eq 0 ] && grep -q '^--- PASS: TestPopReleaseLock' "$log"; then cls=PASS
elif grep -q '^--- FAIL: TestPopReleaseLock' "$log" && grep -q 'Timeout after 30s' "$log"; then cls=FOCAL_DEFECT_WITNESS_A
else cls=UNRESOLVED; fi
printf '%s,%s,%s,%s,%s,%s,%s\n' "$ver" "$n" "$st" "$et" "$el" "$rc" "$cls" >> "$csv"
printf '%-6s %2s  %-8s exit=%-3s %s\n' "$ver" "$n" "${el}s" "$rc" "$cls"
