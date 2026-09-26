"""Synthetic oracle fixtures (execution_plan.md Phase 1).

These traces test classifier LOGIC only. They are hand-constructed from the documented
runtime formats (Go goroutine dumps, `go test -v` lines, JVM -Xlog:exceptions records,
W1Runner markers); they are not real positive controls or defect observations.
Each fixture: (name, variant, exit_code, outer_timeout, trace text, selection, expected status, expected rule).
"""

from __future__ import annotations

from typing import Any

from .common import write_json, write_text_lf
from .config import ORACLES_DIR

GO_MUTEX_WAIT = """goroutine {gid} [semacquire]:
sync.runtime_SemacquireMutex(0xc0000a2014, 0x0)
\t/usr/local/go/src/runtime/sema.go:71 +0x3d
sync.(*Mutex).Lock(0xc0000a2010)
\t/usr/local/go/src/sync/mutex.go:134 +0x109
{caller}
\t{callerloc} +0x3b
created by {creator}
\t{creatorloc} +0x9e
"""


def _k8s(select_line: int) -> dict[str, str]:
    pop = f"""goroutine 21 [select]:
k8s.io/kubernetes/pkg/controller/framework.(*processorListener).pop(0xc0000a2000, 0xc000060180)
\t/go/src/k8s.io/kubernetes/pkg/controller/framework/shared_informer.go:{select_line} +0x1b5
created by k8s.io/kubernetes/pkg/controller/framework.TestPopReleaseLock
\t/go/src/k8s.io/kubernetes/pkg/controller/framework/processor_listener_test.go:34 +0xb5
"""
    locker = GO_MUTEX_WAIT.format(
        gid=22, caller="k8s.io/kubernetes/pkg/controller/framework.TestPopReleaseLock.func1(0xc0000a2000, 0xc000060240)",
        callerloc="/go/src/k8s.io/kubernetes/pkg/controller/framework/processor_listener_test.go:38",
        creator="k8s.io/kubernetes/pkg/controller/framework.TestPopReleaseLock",
        creatorloc="/go/src/k8s.io/kubernetes/pkg/controller/framework/processor_listener_test.go:36")
    return {"pop": pop, "locker": locker}


def k8s_fixtures(bad_select: int, ok_select: int) -> list[dict[str, Any]]:
    kb = _k8s(bad_select)
    ko = _k8s(ok_select)
    fail = "=== RUN   TestPopReleaseLock\n--- FAIL: TestPopReleaseLock (30.00s)\n    processor_listener_test.go:45: Timeout after 30s\nFAIL\n"
    dump = "\nW1-GOROUTINE-DUMP-BEGIN after-nonzero-exit\n"
    return [
        {"name": "positive_dump_pop_and_locker", "variant": "V_bad", "exit": 1, "outer": False,
         "text": fail + dump + kb["pop"] + "\n" + kb["locker"] + "W1-GOROUTINE-DUMP-END\n",
         "expect": "FOCAL_FAILURE", "rule": "k8s26980.R1"},
        {"name": "timeout_message_only", "variant": "V_bad", "exit": 1, "outer": False, "text": fail,
         "expect": "NONFOCAL_FAILURE", "rule": None},
        {"name": "missing_premise_locker_only", "variant": "V_bad", "exit": 1, "outer": False,
         "text": fail + dump + kb["locker"] + "W1-GOROUTINE-DUMP-END\n", "expect": "NONFOCAL_FAILURE", "rule": None},
        {"name": "pop_at_wrong_line", "variant": "V_bad", "exit": 1, "outer": False,
         "text": fail + dump + _k8s(bad_select + 7)["pop"] + "\n" + kb["locker"], "expect": "NONFOCAL_FAILURE", "rule": None},
        {"name": "repaired_variant_positive_shape", "variant": "V_ok", "exit": 1, "outer": False,
         "text": fail + dump + ko["pop"] + "\n" + ko["locker"], "expect": "FOCAL_FAILURE", "rule": "k8s26980.R1",
         "note": "attempt-level focal; validation treats any V_ok non-pass as counterpart failure"},
        {"name": "generic_test_timeout_panic", "variant": "V_bad", "exit": 2, "outer": False,
         "text": "=== RUN   TestPopReleaseLock\npanic: test timed out after 1m0s\n\ngoroutine 5 [running]:\ntesting.(*M).startAlarm.func1()\n\t/usr/local/go/src/testing/testing.go:1377 +0xdf\n",
         "expect": "NONFOCAL_FAILURE", "rule": None},
        {"name": "pass", "variant": "V_bad", "exit": 0, "outer": False,
         "text": "=== RUN   TestPopReleaseLock\n--- PASS: TestPopReleaseLock (0.00s)\nPASS\n", "expect": "PASS", "rule": None},
        {"name": "outer_timeout", "variant": "V_bad", "exit": None, "outer": True, "text": "=== RUN   TestPopReleaseLock\n",
         "expect": "UNRESOLVED", "rule": None},
        {"name": "malformed_nonzero_no_results", "variant": "V_bad", "exit": 1, "outer": False, "text": "garbage\n",
         "expect": "UNRESOLVED", "rule": None},
        {"name": "exit0_with_fail_line", "variant": "V_ok", "exit": 0, "outer": False, "text": fail,
         "expect": "HARNESS_INVALID", "rule": None},
    ]


def istio_fixtures() -> list[dict[str, Any]]:
    wait = """goroutine 40 [select]:
istio.io/istio/pkg/envoy.(*agent).waitUntilLive(0xc0001c6000)
\t/go/src/istio.io/istio/pkg/envoy/agent.go:171 +0x2a5
istio.io/istio/pkg/envoy.(*agent).Restart(0xc0001c6000, 0x1a2b3c0, 0x1c9e7f0)
\t/go/src/istio.io/istio/pkg/envoy/agent.go:137 +0x1f2
created by istio.io/istio/pkg/envoy.TestExitDuringWaitForLive
\t/go/src/istio.io/istio/pkg/envoy/agent_test.go:200 +0x3c5
"""
    run = GO_MUTEX_WAIT.format(
        gid=38, caller="istio.io/istio/pkg/envoy.(*agent).Run(0xc0001c6000, 0x1d0a8c0, 0xc0000b2040, 0x0, 0x0)",
        callerloc="/go/src/istio.io/istio/pkg/envoy/agent.go:192",
        creator="istio.io/istio/pkg/envoy.TestExitDuringWaitForLive", creatorloc="/go/src/istio.io/istio/pkg/envoy/agent_test.go:194")
    fail = ("=== RUN   TestExitDuringWaitForLive\n--- FAIL: TestExitDuringWaitForLive (5.00s)\n"
            "    agent_test.go:213: timed out waiting for epoch 1 to start\nFAIL\n")
    dump = "\nW1-GOROUTINE-DUMP-BEGIN after-nonzero-exit\n"
    return [
        {"name": "positive_wait_and_blocked_run", "variant": "V_bad", "exit": 1, "outer": False,
         "text": fail + dump + wait + "\n" + run, "expect": "FOCAL_FAILURE", "rule": "istio17860.R1"},
        {"name": "assertion_text_only", "variant": "V_bad", "exit": 1, "outer": False, "text": fail,
         "expect": "NONFOCAL_FAILURE", "rule": None},
        {"name": "missing_premise_run_blocked_only", "variant": "V_bad", "exit": 1, "outer": False,
         "text": fail + dump + run, "expect": "NONFOCAL_FAILURE", "rule": None},
        {"name": "unrelated_gomega_failure", "variant": "V_ok", "exit": 1, "outer": False,
         "text": "=== RUN   TestExitDuringWaitForLive\n--- FAIL: TestExitDuringWaitForLive (1.20s)\n    agent_test.go:220: Expected <time.Time> to be ~ ...\nFAIL\n",
         "expect": "NONFOCAL_FAILURE", "rule": None},
        {"name": "dumps_in_separate_dumps_do_not_combine", "variant": "V_bad", "exit": 1, "outer": False,
         "text": fail + dump + wait + "\nsome unrelated output\nmore\nlines\nhere\n\n" + run.replace("goroutine 38", "goroutine 40"),
         "expect": "NONFOCAL_FAILURE", "rule": None},
    ]


def grpc_fixtures(client_line: int) -> list[dict[str, Any]]:
    head = "=== RUN   TestClientDoesntDeadlockWhileWritingErrornousLargeMessages\n"
    dl = ("    end2end_test.go:6035: TestService/UnaryCall(_,_) = _. rpc error: code = DeadlineExceeded desc = "
          "context deadline exceeded, want code: ResourceExhausted\n")
    fail = head + "--- FAIL: TestClientDoesntDeadlockWhileWritingErrornousLargeMessages (10.09s)\n    end2end_test.go:520: Running test in tcp-clear-v1-balancer environment...\n" + dl + "FAIL\n"
    blocked = f"""goroutine 77 [select]:
google.golang.org/grpc/transport.(*quotaPool).get(0xc000312000, 0x4000, 0xc0003a8060, 0xc0003a80c0, 0xc0003a8120, 0xc0003a8180, 0x0, 0x0, 0x0)
\t/go/src/google.golang.org/grpc/transport/control.go:192 +0x1c4
google.golang.org/grpc/transport.(*http2Client).Write(0xc0002c2000, 0xc0003a8000, 0xc000400000, 0x5, 0x5, 0xc000500000, 0x100000, 0x100000, 0xc0000c1f28, 0x0, 0x0)
\t/go/src/google.golang.org/grpc/transport/http2_client.go:{client_line} +0x2d6
google.golang.org/grpc.(*clientStream).SendMsg(0xc000300000, 0x9a4d20, 0xc000288000, 0x0, 0x0)
\t/go/src/google.golang.org/grpc/stream.go:430 +0x1b0
"""
    premise = "    w1_probe_test.go:40: first call: rpc error: code = ResourceExhausted desc = grpc: received message larger than max (1048581 vs. 1024)\n"
    new_fail = ("=== RUN   TestNewProbe\n--- FAIL: TestNewProbe (60.00s)\n" + premise + "FAIL\n")
    return [
        {"name": "supplied_test_deadline_signature", "variant": "V_bad", "exit": 1, "outer": False, "text": fail,
         "expect": "FOCAL_FAILURE", "rule": "grpc1859.R1"},
        {"name": "new_test_blocked_writer_dump_with_status_premise", "variant": "V_bad", "exit": 2, "outer": False,
         "selection_extra": ["TestNewProbe"],
         "text": head + "--- PASS: TestClientDoesntDeadlockWhileWritingErrornousLargeMessages (0.80s)\n" + new_fail +
         "\nW1-GOROUTINE-DUMP-BEGIN after-nonzero-exit\n" + blocked, "expect": "FOCAL_FAILURE", "rule": "grpc1859.R2"},
        {"name": "new_test_dump_without_premise", "variant": "V_bad", "exit": 1, "outer": False, "selection_extra": ["TestNewProbe"],
         "text": head + "--- PASS: TestClientDoesntDeadlockWhileWritingErrornousLargeMessages (0.80s)\n=== RUN   TestNewProbe\n--- FAIL: TestNewProbe (1.00s)\nFAIL\n" + blocked,
         "expect": "NONFOCAL_FAILURE", "rule": None},
        {"name": "new_test_deadline_text_only", "variant": "V_bad", "exit": 1, "outer": False, "selection_extra": ["TestNewProbe"],
         "text": head + "--- PASS: TestClientDoesntDeadlockWhileWritingErrornousLargeMessages (0.80s)\n=== RUN   TestNewProbe\n--- FAIL: TestNewProbe (1.00s)\n" + dl + "FAIL\n",
         "expect": "NONFOCAL_FAILURE", "rule": None},
        {"name": "expired_cert_style_hang_unrelated", "variant": "V_bad", "exit": 2, "outer": False,
         "text": head + "panic: test timed out after 1m50s\n\ngoroutine 9 [select]:\ngoogle.golang.org/grpc.DialContext(0xc0000c0000)\n\t/go/src/google.golang.org/grpc/clientconn.go:300 +0x1\n",
         "expect": "NONFOCAL_FAILURE", "rule": None},
        {"name": "blocked_writer_at_stream_quota_site_not_transport", "variant": "V_bad", "exit": 1, "outer": False,
         "text": fail.replace(dl, "    end2end_test.go:6035: other failure\n") + blocked.replace(f"http2_client.go:{client_line}", f"http2_client.go:{client_line - 12}"),
         "expect": "NONFOCAL_FAILURE", "rule": None},
    ]


POOL_INT = ("[1.230s][info][exceptions] Exception <a 'java/lang/InterruptedException'{0x000000071c4e1528}>\n"
            " thrown in interpreter method <{method} {0x000076b5684005f8} 'borrowObject' '()Ljava/lang/Object;' in 'org/apache/commons/pool/impl/GenericObjectPool'>\n"
            " at bci 180 for thread 0x000076b5a01bfc50 (Thread-3)\n")
POOL_NSEE = ("[1.650s][info][exceptions] Exception <a 'java/util/NoSuchElementException'{0x000000071c42b9c8}: Timeout waiting for idle object>\n"
             " thrown in compiled method <{method} {0x000076b5684005f8} 'borrowObject' '()Ljava/lang/Object;' in 'org/apache/commons/pool/impl/GenericObjectPool'>\n"
             " at bci 250 for thread 0x000076b5a00297f0 (main)\n")
POOL_NSEE_EXHAUSTED = POOL_NSEE.replace("Timeout waiting for idle object", "Pool exhausted")


def pool_fixtures() -> list[dict[str, Any]]:
    b = "W1-TEST-BEGIN org.apache.commons.pool.impl.TestGenericObjectPool#testNew\n"
    e_fail = ("W1-TEST-FAILURE org.apache.commons.pool.impl.TestGenericObjectPool#testNew\n"
              "junit.framework.AssertionFailedError: NoSuchElementException not expected\n"
              "\tat org.apache.commons.pool.impl.TestGenericObjectPool.testNew(TestGenericObjectPool.java:140)\n"
              "W1-THREAD-DUMP-BEGIN after-nonpass org.apache.commons.pool.impl.TestGenericObjectPool#testNew\n\"main\" id=1 RUNNABLE\n\tat java.lang.Thread.dumpThreads(Native Method)\n\n"
              "W1-THREAD-DUMP-END after-nonpass\n"
              "W1-TEST-END org.apache.commons.pool.impl.TestGenericObjectPool#testNew FAIL\n")
    entries = ("W1-TEST-BEGIN org.apache.commons.pool.impl.TestGenericObjectPool#testWhenExhaustedBlock\n"
               + POOL_NSEE +
               "W1-TEST-END org.apache.commons.pool.impl.TestGenericObjectPool#testWhenExhaustedBlock PASS\n")
    done_fail = "W1-RUN-COMPLETE passed=1 failed=1\n"
    blocked_dump = ("W1-INNER-TIMEOUT after 30s\nW1-THREAD-DUMP-BEGIN inner-timeout\n"
                    "\"main\" id=1 WAITING on org.apache.commons.pool.impl.GenericObjectPool$Latch@1b6d3586\n"
                    "\tat java.lang.Object.wait(Native Method)\n\tat java.lang.Object.wait(Object.java:338)\n"
                    "\tat org.apache.commons.pool.impl.GenericObjectPool.borrowObject(GenericObjectPool.java:1110)\n"
                    "\tat org.apache.commons.pool.impl.TestGenericObjectPool.testNew(TestGenericObjectPool.java:135)\n\n"
                    "W1-THREAD-DUMP-END inner-timeout\n")
    return [
        {"name": "interrupt_then_timeout_nsee", "variant": "V_bad", "exit": 1, "outer": False, "selection_extra": ["org.apache.commons.pool.impl.TestGenericObjectPool#testNew"],
         "text": entries + b + POOL_INT + POOL_NSEE + e_fail + done_fail, "expect": "FOCAL_FAILURE", "rule": "pool162.R1"},
        {"name": "nsee_without_interrupt", "variant": "V_bad", "exit": 1, "outer": False, "selection_extra": ["org.apache.commons.pool.impl.TestGenericObjectPool#testNew"],
         "text": entries + b + POOL_NSEE + e_fail + done_fail, "expect": "NONFOCAL_FAILURE", "rule": None},
        {"name": "interrupt_then_pool_exhausted_message", "variant": "V_bad", "exit": 1, "outer": False, "selection_extra": ["org.apache.commons.pool.impl.TestGenericObjectPool#testNew"],
         "text": entries + b + POOL_INT + POOL_NSEE_EXHAUSTED + e_fail + done_fail, "expect": "NONFOCAL_FAILURE", "rule": None},
        {"name": "nsee_before_interrupt_order", "variant": "V_bad", "exit": 1, "outer": False, "selection_extra": ["org.apache.commons.pool.impl.TestGenericObjectPool#testNew"],
         "text": entries + b + POOL_NSEE + POOL_INT + e_fail + done_fail, "expect": "NONFOCAL_FAILURE", "rule": None},
        {"name": "inner_timeout_blocked_borrower_after_interrupt", "variant": "V_bad", "exit": 3, "outer": False, "selection_extra": ["org.apache.commons.pool.impl.TestGenericObjectPool#testNew"],
         "text": entries + b + POOL_INT + blocked_dump, "expect": "FOCAL_FAILURE", "rule": "pool162.R2"},
        {"name": "generic_inner_timeout_no_premise", "variant": "V_bad", "exit": 3, "outer": False, "selection_extra": ["org.apache.commons.pool.impl.TestGenericObjectPool#testNew"],
         "text": entries + b + blocked_dump, "expect": "NONFOCAL_FAILURE", "rule": None},
        {"name": "focal_sequence_in_passing_test_is_pass", "variant": "V_ok", "exit": 0, "outer": False, "selection_extra": ["org.apache.commons.pool.impl.TestGenericObjectPool#testNew"],
         "text": entries + b + POOL_INT + "W1-TEST-END org.apache.commons.pool.impl.TestGenericObjectPool#testNew PASS\nW1-RUN-COMPLETE passed=2 failed=0\n",
         "expect": "PASS", "rule": None},
    ]


def write_all(k8s_selects: tuple[int, int], grpc_client_line: int) -> dict[str, Any]:
    sets = {"k8s26980": k8s_fixtures(*k8s_selects), "istio17860": istio_fixtures(),
            "grpc1859": grpc_fixtures(grpc_client_line), "pool162": pool_fixtures()}
    summary = {}
    for case, fx in sets.items():
        d = ORACLES_DIR / case / "fixtures"
        expected = []
        for f in fx:
            write_text_lf(d / f"{f['name']}.txt", f["text"])
            expected.append({k: v for k, v in f.items() if k != "text"})
        write_json(d / "expected.json", {"note": "synthetic classifier-logic fixtures; not real observations", "fixtures": expected})
        summary[case] = len(fx)
    return summary
