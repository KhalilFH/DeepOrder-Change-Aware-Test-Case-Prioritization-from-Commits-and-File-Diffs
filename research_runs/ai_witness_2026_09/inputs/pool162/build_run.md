# Build and run interface (pool162)

Language: Java, compiled by Temurin JDK 17 at `--release 8` against JUnit 3.8.2 and the production classes
of each variant, in fixed container images without network access. Both production variants use
identical test sources, instrumentation, arguments and timeouts; you cannot see or choose which variant is
which beyond the paired result labels `defective` and `repaired`.

Build: the harness copies your overlay into `src/test` and compiles all of `src/test`.

Run: `java -Xlog:exceptions=info w1harness.W1Runner 30 <selected tests>` with 16 visible CPUs. Selected
tests are the supplied entry points `org.apache.commons.pool.impl.TestGenericObjectPool#testWhenExhaustedBlock`, `org.apache.commons.pool.impl.TestGenericKeyedObjectPool#testWhenExhaustedGrow`, `org.apache.commons.pool.impl.TestStackObjectPool#testBorrowFromEmptyPoolWithNullFactory` plus any new `public void testXxx()` methods your overlay adds
to the editable classes (at most 4). Each selected test runs once, in order, via JUnit 3
(`setUp`/`tearDown` apply). Outer limit 60s per run (killed and unresolved), cleanup 30s.

Harness instrumentation (identical everywhere): the VM logs thrown exceptions (`-Xlog:exceptions=info`),
the runner prints each failure's stack trace and a full thread dump after any non-passing test, and at
30s it dumps all threads and exits (inner timeout).

Editing rules: edit only `src/test/org/apache/commons/pool/impl/TestGenericObjectPool.java`, `src/test/org/apache/commons/pool/impl/TestGenericKeyedObjectPool.java`, `src/test/org/apache/commons/pool/impl/TestStackObjectPool.java` (insertion-only: every original line must remain, in order). Do not
modify production code, remove or weaken assertions, change timeouts, read files/environment/system
properties, exit or halt the VM, use reflection or class loading, access the network, branch on revision
identity, or print text imitating VM exception logs. At most 400 inserted lines.
