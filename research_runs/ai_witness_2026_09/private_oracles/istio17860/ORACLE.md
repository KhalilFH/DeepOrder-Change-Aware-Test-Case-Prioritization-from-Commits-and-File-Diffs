# istio17860 oracle (rule istio17860.R1)

Obligation: a restart waiting for liveness must permit epoch-exit processing to progress.

- **R1** A failing attempt whose single goroutine dump contains (premise) a goroutine with
  `envoy.(*agent).waitUntilLive` called under `envoy.(*agent).Restart`, and (consequence) a different goroutine in state
  `semacquire` whose first non-runtime/sync caller of `sync.(*Mutex).Lock` is `envoy.(*agent).Run` (epoch-exit
  processing blocked on the agent lock).

Not focal: `timed out waiting for epoch 1 to start` alone, Gomega `BeTemporally` failures, dumps where the two
goroutines appear in different dumps. Control case: historical visibility is high; no-change is a legitimate result.
