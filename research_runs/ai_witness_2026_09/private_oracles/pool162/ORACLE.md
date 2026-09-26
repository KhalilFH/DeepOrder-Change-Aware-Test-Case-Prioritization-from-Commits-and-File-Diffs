# pool162 oracle (rules pool162.R1, pool162.R2)

Obligation (oracle-builder material): interruption of a waiting borrower must not consume capacity needed by later borrowing.

Evidence source: JVM `-Xlog:exceptions=info` records (VM-produced, identical instrumentation on both variants),
W1Runner test windows (`W1-TEST-BEGIN`/`W1-TEST-END`) and W1Runner thread dumps.

- **R1** Inside the window of one selected test that ended FAIL or ERROR: premise = a record of
  `java/lang/InterruptedException` thrown in method `borrowObject` of `GenericObjectPool` or `GenericKeyedObjectPool`;
  consequence = a LATER record in the same window of `java/util/NoSuchElementException` with message exactly
  `Timeout waiting for idle object` thrown in `borrowObject` of the same class.
- **R2** Inner timeout (`W1-INNER-TIMEOUT`) inside a selected test window after the R1 premise; consequence = the
  inner-timeout thread dump shows a WAITING thread in `java.lang.Object.wait` with a `borrowObject` frame of the same class.

Not focal: NoSuchElementException without a preceding interrupted borrower; `Pool exhausted` messages; timeouts
without the premise; any passing test (a PASS attempt stays PASS even if the premise occurred).
Known limits: evidence requires the test to interrupt a thread while it waits in borrowObject; the rule cannot tell an
extreme stall from a lost capacity slot for R2 (V_ok must pass all 15 attempts in validation).
Pre-fix supplied candidates never interrupt a borrower, so the unchanged overlay cannot satisfy R1/R2 (by design).
