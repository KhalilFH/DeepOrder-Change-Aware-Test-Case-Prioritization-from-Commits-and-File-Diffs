"""B1 deterministic template bank and shared source bindings (method_contract.md "B1").

Order (at most four candidates, including unchanged):

1. ``T1``  unchanged supplied tests (always applicable);
2. ``T2x2`` repeat the complete supplied workload twice with fresh fixture state;
3. ``T2x4`` repeat it four times;
4. ``T3``  one resource-lifecycle template where the production diff changes an
   error/interruption handler: acquire/reserve -> existing error/interruption action ->
   release per the API -> second operation with a bounded progress/capacity assertion.

Bindings are concrete source symbols derived mechanically from the production
diff and supplied tests (``bindings()``), frozen before calibration and shared
with every arm as packet metadata. When T3 is inapplicable the reason is
recorded; no bespoke case fix is substituted. All candidates pass the same
edit-contract checks as model proposals.
"""

from __future__ import annotations

from typing import Any

from .casespec import CaseSpec

TEMPLATE_ORDER = ("T1", "T2x2", "T2x4", "T3")


def bindings(case: str) -> dict[str, Any]:
    """Shared, source-linked binding table (no oracle material, no outcome tuning)."""
    if case == "pool162":
        return {
            "T3": {
                "applicable": True,
                "derivation": "diff modifies the catch(InterruptedException) handler inside borrowObject of "
                              "GenericObjectPool and GenericKeyedObjectPool",
                "resource": "pool capacity (setMaxActive(1), WHEN_EXHAUSTED_BLOCK)",
                "acquire": "GenericObjectPool.borrowObject()",
                "error_action": "Thread.interrupt() of a second borrower waiting inside borrowObject()",
                "release": "GenericObjectPool.returnObject(Object)",
                "second_operation": "GenericObjectPool.borrowObject() with setMaxWait(bounded)",
                "assertion": "second borrow obtains an object within the bounded wait (capacity restored)",
                "source_spans": [
                    "defective/src/java/org/apache/commons/pool/impl/GenericObjectPool.java:1043-1198",
                    "shared/src/test/org/apache/commons/pool/impl/TestGenericObjectPool.java (WaitingTestThread, setUp)",
                ],
            }
        }
    if case == "grpc1859":
        return {
            "T3": {
                "applicable": True,
                "derivation": "diff modifies the error return after localSendQuota.get in http2Client.Write and "
                              "http2Server.Write",
                "resource": "transport send quota of one client connection",
                "acquire": "tc.UnaryCall on a connection from newTest/startServer/clientConn",
                "error_action": "UnaryCall with a payload larger than te.maxServerReceiveMsgSize (server rejects the write)",
                "release": "the failed call returns (status ResourceExhausted)",
                "second_operation": "UnaryCall with a payload within the limit and a bounded context deadline",
                "assertion": "the second call succeeds before its deadline (connection still makes progress)",
                "source_spans": ["defective/transport/http2_client.go:664-767", "shared/test/end2end_test.go:6010-6042"],
            }
        }
    if case == "k8s26980":
        return {"T3": {"applicable": False,
                       "reason": "the diff narrows the lock scope around a blocking channel send in pop(); it changes no "
                                 "error or interruption handler, so the lifecycle template has no error/interruption action "
                                 "binding"}}
    if case == "istio17860":
        return {"T3": {"applicable": False,
                       "reason": "the diff changes lock scope and liveness waiting in Restart/waitUntilLive; it changes no "
                                 "error or interruption handler, so the lifecycle template has no error/interruption action "
                                 "binding"}}
    raise KeyError(case)


# --------------------------------------------------------------------------- Go

def _go_repeat_file(spec: CaseSpec, n: int) -> dict[str, Any]:
    fn_lines = []
    for entry in spec.entry_points:
        fn_lines.append(
            f"func TestRepeat{n}x{entry[4:]}(t *testing.T) {{\n"
            f"\tfor i := 0; i < {n}; i++ {{\n"
            f"\t\tt.Run(\"rep\"+strconv.Itoa(i), {entry})\n"
            f"\t}}\n"
            f"}}\n")
    content = (f"package {spec.package_name}\n\n"
               f"// B1 template T2x{n}: repeat the complete supplied workload {n} times; each repetition calls\n"
               f"// the unchanged supplied test, which builds its own fresh fixtures and keeps all assertions.\n\n"
               f"import (\n\t\"strconv\"\n\t\"testing\"\n)\n\n" + "\n".join(fn_lines))
    return {"edits": [], "new_files": [{"path": f"{spec.test_dir}/w1_b1_repeat{n}_test.go", "content": content}]}


GRPC_T3 = """package test

// B1 template T3 (resource lifecycle), bindings from bindings("grpc1859")["T3"]:
// acquire a connection, perform the existing error action (oversized UnaryCall rejected by the
// server's receive limit), let it return, then a second in-limit UnaryCall must complete within a
// bounded deadline.

import (
	"testing"
	"time"

	"golang.org/x/net/context"
	testpb "google.golang.org/grpc/test/grpc_testing"
)

func TestLifecycleProgressAfterRejectedWrite(t *testing.T) {
	for _, e := range listTestEnv() {
		if e.httpHandler {
			continue
		}
		te := newTest(t, e)
		smallSize := 1024
		te.maxServerReceiveMsgSize = &smallSize
		te.startServer(&testServer{security: e.security})
		tc := testpb.NewTestServiceClient(te.clientConn())
		big, err := newPayload(testpb.PayloadType_COMPRESSABLE, 1048576)
		if err != nil {
			t.Fatal(err)
		}
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		_, _ = tc.UnaryCall(ctx, &testpb.SimpleRequest{ResponseType: testpb.PayloadType_COMPRESSABLE, Payload: big})
		cancel()
		small, err := newPayload(testpb.PayloadType_COMPRESSABLE, 10)
		if err != nil {
			t.Fatal(err)
		}
		ctx2, cancel2 := context.WithTimeout(context.Background(), 10*time.Second)
		if _, err := tc.UnaryCall(ctx2, &testpb.SimpleRequest{ResponseType: testpb.PayloadType_COMPRESSABLE, Payload: small}); err != nil {
			t.Errorf("second in-limit UnaryCall after a rejected oversized call: %v", err)
		}
		cancel2()
		te.tearDown()
	}
}
"""

# --------------------------------------------------------------------------- Java

JAVA_ENTRY_CLASS_FILE = {
    "org.apache.commons.pool.impl.TestGenericObjectPool": "src/test/org/apache/commons/pool/impl/TestGenericObjectPool.java",
    "org.apache.commons.pool.impl.TestGenericKeyedObjectPool": "src/test/org/apache/commons/pool/impl/TestGenericKeyedObjectPool.java",
    "org.apache.commons.pool.impl.TestStackObjectPool": "src/test/org/apache/commons/pool/impl/TestStackObjectPool.java",
}


def _java_insert_before_last_brace(original: str, block: str) -> dict[str, str]:
    """Edit anchored on the final class-closing brace (unique anchor: last '\\n}' in file)."""
    idx = original.rstrip().rfind("\n}")
    tail = original[idx:]
    # anchor = the last method's closing line plus class brace, made unique by taking enough context
    ctx_start = original.rfind("\n", 0, idx - 1)
    anchor = original[ctx_start + 1:idx] + tail
    assert original.count(anchor) == 1, "non-unique anchor"
    return {"old": anchor, "new": original[ctx_start + 1:idx] + "\n" + block + tail}


def _java_repeat(spec: CaseSpec, originals: dict[str, str], n: int) -> dict[str, Any]:
    edits = []
    for entry in spec.entry_points:
        cls, method = entry.split("#")
        path = JAVA_ENTRY_CLASS_FILE[cls]
        block = (f"    // B1 template T2x{n}: repeat the supplied test {n} times with fresh fixture state.\n"
                 f"    public void testRepeat{n}x{method[4:]}() throws Exception {{\n"
                 f"        for (int i = 0; i < {n}; i++) {{\n"
                 f"            if (i > 0) {{\n"
                 f"                tearDown();\n"
                 f"                setUp();\n"
                 f"            }}\n"
                 f"            {method}();\n"
                 f"        }}\n"
                 f"    }}\n")
        e = _java_insert_before_last_brace(originals[path], block)
        edits.append({"path": path, **e})
    return {"edits": edits, "new_files": []}


POOL_T3_BLOCK = """    // B1 template T3 (resource lifecycle), bindings from bindings("pool162")["T3"]: acquire the only
    // capacity, interrupt a second borrower waiting in borrowObject, release, then a bounded second borrow.
    public void testLifecycleCapacityAfterInterruptedWaiter() throws Exception {
        pool.setMaxActive(1);
        pool.setWhenExhaustedAction(GenericObjectPool.WHEN_EXHAUSTED_BLOCK);
        pool.setMaxWait(0);
        Object held = pool.borrowObject();
        WaitingTestThread waiter = new WaitingTestThread(pool, 200);
        waiter.start();
        Thread.sleep(200);
        waiter.interrupt();
        waiter.join(2000);
        pool.returnObject(held);
        pool.setMaxWait(1000L);
        Object again = pool.borrowObject();
        assertNotNull(again);
        pool.returnObject(again);
    }
"""


def candidates(spec: CaseSpec, originals: dict[str, str]) -> list[tuple[str, dict[str, Any] | None, str | None]]:
    """[(template_id, proposal or None for unchanged, inapplicability_reason)] in frozen order."""
    out: list[tuple[str, dict[str, Any] | None, str | None]] = [("T1", None, None)]
    for n, tid in ((2, "T2x2"), (4, "T2x4")):
        if spec.language == "go":
            out.append((tid, _go_repeat_file(spec, n), None))
        else:
            out.append((tid, _java_repeat(spec, originals, n), None))
    b = bindings(spec.case)["T3"]
    if not b["applicable"]:
        out.append(("T3", None, b["reason"]))
    elif spec.case == "grpc1859":
        out.append(("T3", {"edits": [], "new_files": [{"path": "test/w1_b1_lifecycle_test.go", "content": GRPC_T3}]}, None))
    elif spec.case == "pool162":
        path = JAVA_ENTRY_CLASS_FILE["org.apache.commons.pool.impl.TestGenericObjectPool"]
        out.append(("T3", {"edits": [{"path": path, **_java_insert_before_last_brace(originals[path], POOL_T3_BLOCK)}],
                           "new_files": []}, None))
    return out
