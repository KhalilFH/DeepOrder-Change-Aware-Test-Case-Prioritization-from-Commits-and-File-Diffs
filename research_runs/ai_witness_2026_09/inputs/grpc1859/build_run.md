# Build and run interface (grpc1859)

Language: Go (go version go1.13.15 linux/amd64), package `test` in `test` (repository-relative). Build and run
happen in the case's fixed container images without network access. Both production variants use
identical test sources, instrumentation, arguments and timeouts; you cannot see or choose which
variant is which beyond the paired result labels `defective` and `repaired`.

Build: the harness copies your overlay into the package, adds its own file `zz_w1_harness_instrument_test.go`
(which defines `TestMain`), and runs `go test -c -vet=off ./test` on each variant.

Run: `<binary> -test.v -test.count 1 -test.run '^(<selected tests>)$' -test.timeout 110s -only_env tcp-clear-v1-balancer`
with GOMAXPROCS=16 and GOTRACEBACK=all, working directory `test`. Selected tests are the supplied
entry point(s) `TestClientDoesntDeadlockWhileWritingErrornousLargeMessages` plus any new `func TestXxx(t *testing.T)` your overlay adds (at most 4).
Outer limit 120s per run (the process is killed and the run is unresolved), cleanup 30s.

Harness instrumentation (identical everywhere): if any selected test fails, `TestMain` prints a full
goroutine dump after the tests return; on the 110s test timeout the Go runtime dumps all
goroutines. You may add bounded test-side observation (for example printing `runtime.Stack(buf, true)`).

Editing rules: edit only `test/end2end_test.go` (insertion-only: every original line must remain, in order) and/or
add at most 2 new files named like `test/w1_<name>_test.go` in package `test`. Do not modify
production code, remove or weaken assertions, change timeouts or arguments, define `TestMain`, read
files/environment/process information, exec processes, skip tests, access the network (loopback
test servers are fine), branch on revision identity, or print text imitating runtime dumps.
New imports must be standard library (not os, os/exec, io/ioutil, path/filepath, syscall, unsafe,
net/http, plugin) or packages already imported by the supplied test files. At most 400 inserted lines.
