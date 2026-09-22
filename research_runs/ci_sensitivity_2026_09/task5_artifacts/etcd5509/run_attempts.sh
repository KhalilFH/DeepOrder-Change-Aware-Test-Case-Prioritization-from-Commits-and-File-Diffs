#!/bin/bash
# Frozen Q0 qualification attempts for etcd-5509 (Task 5), per the corrected signature (a).
# Fresh-process single attempts: one `docker run --rm` per attempt, -test.count 1.
set -u
export MSYS_NO_PATHCONV=1
WORK="/c/Users/Mega-PC/AppData/Local/Temp/claude/C--Users-Mega-PC-DeepOrder-Change-Aware-Test-Case-Prioritization-from-Commits-and-File-Diffs/e703bac7-2d06-4dca-b0db-2fd37a0e7cde/scratchpad/task5_etcd5509"
OUT="$WORK/attempts"
mkdir -p "$OUT"
RESULTS="$OUT/results_batch2.csv"
echo "version,attempt,start_utc,end_utc,elapsed_s,exit_code,classification,note" > "$RESULTS"

classify() {
  local logfile="$1"
  if grep -q -- "--- PASS: TestKVGetErrConnClosed" "$logfile"; then
    echo "PASS"; return
  fi
  if grep -q "^panic: test timed out" "$logfile"; then
    # signature (a), final (2026-09-19, after two disclosed corrections):
    # EITHER (i) the TestKVGetErrConnClosed goroutine itself blocked directly
    # in sync.(*RWMutex).Lock with clientv3.(*Client).Close in the same stack
    # (Close's own second Lock), OR (ii) that goroutine blocked in a chan
    # receive inside Close, plus a separate goroutine blocked in
    # sync.(*RWMutex).Lock via any connMonitor call site (deferred closure or
    # retryConnection). Both independently trace to the same leaked
    # r.client.mu.RLock() in remoteClient.acquire's closed-client path.
    local test_block direct_match=0 chanrecv_match=0 connmon_match=0
    test_block=$(awk 'BEGIN{RS="";FS="\n"} /TestKVGetErrConnClosed\(/ && /testing\.tRunner/ {print; exit}' "$logfile")
    if echo "$test_block" | grep -q "RWMutex).Lock" && echo "$test_block" | grep -q "Client).Close"; then
      direct_match=1
    fi
    if echo "$test_block" | head -1 | grep -q "chan receive" && echo "$test_block" | grep -q "Client).Close"; then
      chanrecv_match=1
    fi
    if grep -A6 "RWMutex).Lock" "$logfile" | grep -q "connMonitor"; then
      connmon_match=1
    fi
    if [ "$direct_match" = "1" ] || { [ "$chanrecv_match" = "1" ] && [ "$connmon_match" = "1" ]; }; then
      echo "FOCAL_DEFECT_WITNESS_A"; return
    else
      echo "UNRESOLVED_TIMEOUT_NO_SIGNATURE"; return
    fi
  fi
  if grep -qE "panic: runtime error: invalid memory address|nil pointer dereference" "$logfile"; then
    if grep -qE "clientv3\.\(\*remoteClient\)\.acquire|clientv3/integration\.TestKVGetErrConnClosed" "$logfile"; then
      echo "FOCAL_DEFECT_WITNESS_B"; return
    else
      echo "OTHER_DEFECT_PANIC"; return
    fi
  fi
  if grep -qE "FAIL|--- FAIL" "$logfile"; then
    echo "OTHER_DEFECT_FAIL"; return
  fi
  if grep -qE "docker: Error|Cannot connect|no such file" "$logfile"; then
    echo "HARNESS_INVALID"; return
  fi
  echo "UNRESOLVED_UNCLASSIFIED"
}

run_batch() {
  local image="$1" version="$2" start_n="$3" end_n="$4"
  for i in $(seq "$start_n" "$end_n"); do
    local log="$OUT/${version}_attempt_${i}.log"
    local t0 t1 elapsed start_iso end_iso rc
    t0=$(date -u +%s.%N); start_iso=$(date -u +"%Y-%m-%dT%H:%M:%S.%NZ")
    docker run --rm -w /go/src/github.com/coreos/etcd/clientv3/integration "$image" \
      /go/gobench.test -test.v -test.count 1 -test.run TestKVGetErrConnClosed -test.timeout 45s \
      > "$log" 2>&1
    rc=$?
    t1=$(date -u +%s.%N); end_iso=$(date -u +"%Y-%m-%dT%H:%M:%S.%NZ")
    elapsed=$(awk -v a="$t0" -v b="$t1" 'BEGIN{printf "%.3f", b-a}')
    cls=$(classify "$log")
    echo "$version,$i,$start_iso,$end_iso,$elapsed,$rc,$cls," >> "$RESULTS"
    echo "[$version attempt $i] rc=$rc elapsed=${elapsed}s class=$cls"
  done
}

# Second batch: 10 more attempts per version (structural checks passed: batch 1
# produced interpretable PASS/FOCAL_DEFECT_WITNESS_A outcomes on V_bad, all-PASS
# on V_ok, no systemic HARNESS_INVALID)
run_batch etcd5509-bug vbad 11 20
run_batch etcd5509-fix vok 11 20

echo "=== SECOND BATCH DONE ==="
