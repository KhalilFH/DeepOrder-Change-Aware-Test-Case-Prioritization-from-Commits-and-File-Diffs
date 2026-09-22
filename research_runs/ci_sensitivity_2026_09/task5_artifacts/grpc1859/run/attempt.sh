#!/bin/sh
# $1=image $2=version_label $3=attempt_no $4=logdir $5=csv
img=$1; ver=$2; n=$3; ld=$4; csv=$5
log="$ld/${ver}_$(printf %02d $n).log"
s=$(date -u +%s%N); st=$(date -u +%Y-%m-%dT%H:%M:%S.%NZ)
docker run --rm -w /go/src/google.golang.org/grpc/test "$img" /go/gobench.test -test.v -test.count 1 \
  -test.run '^TestClientDoesntDeadlockWhileWritingErrornousLargeMessages$' \
  -test.timeout 110s -only_env tcp-clear-v1-balancer > "$log" 2>&1
rc=$?; e=$(date -u +%s%N); et=$(date -u +%Y-%m-%dT%H:%M:%S.%NZ)
el=$(awk "BEGIN{printf \"%.3f\",($e-$s)/1000000000}")
if [ $rc -eq 0 ] && grep -q '^PASS' "$log"; then cls=PASS
elif grep -q 'want code: ResourceExhausted' "$log"; then cls=FOCAL_DEFECT_WITNESS_A
elif grep -q 'quotaPool).get' "$log" && { grep -q 'test timed out' "$log" || grep -q 'Leaked goroutine' "$log"; }; then cls=FOCAL_DEFECT_WITNESS_B
elif grep -q 'test timed out' "$log"; then cls=UNRESOLVED
else cls=OTHER; fi
printf '%s,%s,%s,%s,%s,%s,%s\n' "$ver" "$n" "$st" "$et" "$el" "$rc" "$cls" >> "$csv"
printf '%-6s %2s  %-7s exit=%-3s %s\n' "$ver" "$n" "${el}s" "$rc" "$cls"
