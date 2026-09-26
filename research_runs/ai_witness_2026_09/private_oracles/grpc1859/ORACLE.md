# grpc1859 oracle (rules grpc1859.R1, grpc1859.R2)

Obligation: an error in a large-message write must not strand send quota and prevent later progress.

- **R1** (unchanged supplied test only) The supplied entry `TestClientDoesntDeadlockWhileWritingErrornousLargeMessages`
  fails, its entry function AND its per-env helper are byte-identical to the supplied source (static premise:
  `smallSize := 1024`, `te.maxServerReceiveMsgSize = &smallSize`, 1 MiB payload => every call takes the oversized-write
  error path; locators `source:test/end2end_test.go@<sha>:L6013,L6014,L6018`), and a failure line carries the
  production-formatted status `rpc error: code = DeadlineExceeded desc = context deadline exceeded` where
  `ResourceExhausted` is required (the C1 signature (a), used as a starting point).
- **R2** Any failing attempt with premise = the R1 static premise (unchanged supplied test failing) or a
  production-formatted `code = ResourceExhausted desc = grpc: (received|trying to send) message larger than max` status
  in the trace, and consequence = a goroutine dump (test-timeout panic, harness TestMain dump or test-printed
  runtime.Stack) with a goroutine in `transport.(*quotaPool).get` called from `transport.(*http2Client).Write` /
  `(*http2Server).Write` at the transport-quota call site (`t.sendQuotaPool.get(`: http2_client.go:710,
  http2_server.go:882 on both variants, computed from packet sources).

Not focal: expired-certificate/dial hangs, stream-level quota waits at other call sites, DeadlineExceeded text in new
tests without dump evidence, generic timeouts. Known limit (as in C1): R1 cannot separate an extreme stall from the leak.
