# k8s26980 oracle (rule k8s26980.R1)

Obligation: a blocked notification send must not retain the listener lock needed by another actor.

- **R1** A failing attempt whose single goroutine dump contains (premise) a goroutine in state `select`/`chan send`
  with frame `framework.(*processorListener).pop` at the delivering `select` (`case p.nextCh <- notification`:
  shared_informer.go line 298 on V_bad, 307 on V_ok, computed from packet sources), and (consequence) a different
  goroutine in state `semacquire` whose first non-runtime/sync caller of `sync.(*Mutex).Lock` is in package
  `k8s.io/kubernetes/pkg/controller/framework`.

Not focal: `Timeout after 30s` text alone, a locker without pop at the delivering select, test-timeout panics without
both goroutines. No historical positive exists anywhere; the rule rests on source review and synthetic fixtures.
The supplied test does not establish the blocked-send premise, and its failure path unlocks the listener lock before
returning, so the harness exit dump is unlikely to show both goroutines: a validated witness needs test-side observation.
