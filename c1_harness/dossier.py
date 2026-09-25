"""Build `subject_manifest.json` from the preparation evidence.

Static dossier facts (upstream identity, counterpart class, obligation,
reconstruction deviations) are transcribed from the restoration records and
cards, each with its evidence path. Everything about the *current* images comes
from `prep/image_checks.json` and `prep/oracle_replay.json`, not from memory.
Genuinely unknown historical facts are `null` with a reason.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from c1_harness import STUDY_DIR, STUDY_ID, SUBJECT_ORDER
from c1_harness.cards import CARDS, rule_hashes
from c1_harness.subjects import FROZEN_COMMANDS, V_BAD, V_OK

OLD = "research_runs/ci_sensitivity_2026_09"
T5 = f"{OLD}/task5_artifacts"

STATIC: dict[str, dict[str, Any]] = {
    "etcd5509": {
        "upstream": {
            "fix": "etcd PR 5509 'clientv3: fix deadlock on Get with concurrent Close', merge 9ed3b446cadd9f43734d9eed9dcb03f3b12567a5 (2016-06-01)",
            "defective_revision": "first parent 36fcc9e9d4ce993998a9170b2293c30b4e5a601a (remote_client.go only)",
            "introducing_revision": None,
            "introducing_revision_reason": "not established by any record",
        },
        "counterpart_class": "historical pair, identical test backport",
        "counterpart_justification": "GoReal reverse patch restores the parent's remote_client.go blob exactly; kv_test.go and harness script identical (re-verified in image 2026-09-25).",
        "obligation": "remoteClient.acquire must not return holding the client read lock when the client is closed; a Get concurrent with Client.Close must terminate and Close must return.",
        "mechanism": "leaked r.client.mu.RLock() on acquire's closed-client failure path blocks the next c.mu.Lock() (Close's second Lock or connMonitor).",
        "reconstruction_deviations": [
            "bug_patch.diff CR bytes stripped (Windows checkout artifact); content identical modulo CR",
            "fix.Dockerfile apt-get vim python3 dropped (Debian stretch archive 404); unused by build/test",
            "bug image carries inert untracked bug_patch.diff (GoReal COPY step)",
        ],
        "evidence": [f"{OLD}/task5_etcd5509_restoration.md", f"{OLD}/task_c_candidate_acquisition.md (card C-01)", f"{T5}/DEVIATIONS.md", f"{T5}/VERIFICATION.md", f"{OLD}/e1/manifests.json"],
        "competing_explanations": "Test-timeout dump without the (i)/(ii) stack shapes is UNRESOLVED. 'kv.Get took too long' (3 s) failures are non-focal and UNRESOLVED. Signature (a) was corrected twice in Q0 (disclosed); (b) never observed.",
        "slowness_review": "(a) requires the Go test-timeout (45 s) dump with the test goroutine in Close blocked on RWMutex.Lock, or in Close's chan receive while connMonitor blocks on the same mutex: a deadlock shape, not a slow run. A merely slow run would not reach the 45 s test timeout unless ~70x slower than its ~0.6 s pass, and would need to be caught in those exact frames. (b) is a panic shape. The 3 s kv.Get bound is the timing-sensitive assertion and is non-focal.",
        "identity_note": "Image IDs equal e1/manifests.json (historical exact images).",
    },
    "etcd7492": {
        "upstream": {
            "fix": "etcd PR 7492 'auth: get rid of deadlocking channel passing scheme in simpleTokenTTL' (fixes issue 7471), merge 148c923c72c4aa9207173c03b775e2c0b8754067 (2017-03-14)",
            "defective_revision": "historical parent 3a61fe596ba1eda2ae0900dfbb1f735ab574ab16 is the reference only; executed V_bad is the reversed pinned base",
            "introducing_revision": None,
            "introducing_revision_reason": "not established by any record",
        },
        "counterpart_class": "controlled historical-fix reversal on pinned base 148c923c; NOT a historical pair",
        "counterpart_justification": "V_bad simple_token.go = parent + declared const->var move (blob 7aa80794), needed for the identical test to compile; store_test.go and harness identical (re-verified in image 2026-09-25).",
        "obligation": "concurrent simple-token authentication and expiry must complete without the simpleTokensMu / addSimpleTokenCh cycle.",
        "mechanism": "assignSimpleTokenToUser/info hold simpleTokensMu while blocked sending to a TTL-keeper channel whose run() goroutine is blocked acquiring the same mutex in deleteTokenFunc.",
        "reconstruction_deviations": [
            "declared const->var move of simpleTokenTTL/simpleTokenTTLResolution (non-behavioral; counterpart-class defining)",
            "fix.Dockerfile apt-get vim python3 dropped; unused",
            "bug image carries inert untracked bug_patch.diff",
        ],
        "evidence": [f"{OLD}/task5_etcd7492_restoration.md", f"{OLD}/task_c_candidate_acquisition.md (card C-02)", f"{T5}/DEVIATIONS.md", f"{T5}/VERIFICATION.md", f"{OLD}/e1/manifests.json"],
        "competing_explanations": "The test sets a 10 ms token TTL; a token expiring between Authenticate and AuthInfoFromCtx yields a non-focal t.Fatal (UNRESOLVED). Only the two-goroutine deadlock dump is focal.",
        "slowness_review": "(a) requires the 50 s test-timeout dump showing both the blocked channel send/lock in a token caller and the keeper run() goroutine blocked in Lock via deleteTokenFunc: a deadlock cycle, not slowness. CPU throttling may raise non-focal token-expiry failures, which classify as UNRESOLVED.",
        "identity_note": "Image IDs equal e1/manifests.json (historical exact images).",
    },
    "grpc1859": {
        "upstream": {
            "fix": "grpc-go PR 1859 (quota not returned on large-message write error), merge 484b3ebb4ab56d3decc8240d599718bdbefcf7eb (2018-02-13)",
            "defective_revision": "historical parent 6c48c7f5 (transport/http2_client.go, http2_server.go)",
            "introducing_revision": None,
            "introducing_revision_reason": "not established by any record",
        },
        "counterpart_class": "historical pair, identical test backport",
        "counterpart_justification": "reconstructed V_bad blobs equal the historical parent's; end2end_test.go identical (re-verified in image 2026-09-25).",
        "obligation": "a failed large-message write must return acquired send quota, so later calls get ResourceExhausted rather than blocking until their deadline.",
        "mechanism": "sendQuotaPool.add(tq) removed on the error path; quota leaks and writers block in quotaPool.get.",
        "reconstruction_deviations": [
            "fix.Dockerfile apt-get vim python3 dropped; recipes made symmetric",
            "GoReal unpinned go get replaced by identical dated pinned clones (last commit <= 2018-02-13) in both images; /go/dep_versions.txt identical",
            "-only_env tcp-clear-v1-balancer: test certificates expired 2024/2025; first clear-text env in upstream order (not chosen by failure rate)",
            "bug image carries inert untracked bug_patch.diff",
        ],
        "evidence": [f"{OLD}/task5_grpc1859_restoration.md", f"{OLD}/task_c2_candidate_acquisition.md (card C-03)", f"{T5}/grpc1859/run/frozen_protocol.txt", f"{T5}/DEVIATIONS.md", f"{T5}/VERIFICATION.md"],
        "competing_explanations": "Expired-certificate Dial hangs (other envs) are excluded by -only_env and never match either signature (replayed). Card C-03 records a post-merge Travis hang of the fixed test (issue 1850 comment) as an unresolved counterpart-validity caveat.",
        "slowness_review": "(a) requires a call to exceed its own 10 s per-call deadline while sending a 1 MiB payload the server rejects after the header; a pass takes ~0.8 s for all 1000 calls. (b) requires quotaPool.get frames under http2 Write in a timeout/leak dump. A 2-CPU bandwidth limit is not expected to create a 10 s per-call stall, but the witness cannot distinguish an extreme stall from the leak: source argument only.",
        "identity_note": "No image ID was recorded in Q0. Current IDs are bound here; identity with the Q0 images is inferred from creation times (17:50:11Z/17:50:33Z, inside the Task 5 window, matching build_end.txt 17:50:35Z) and blob checks, not proven.",
    },
    "grpc2391": {
        "upstream": {
            "fix": "grpc-go PR 2391 'internal: fix GO_AWAY deadlock', squash-merge ff2aa05958775030998dbe2f9bccbe2af324adf4 (2018-10-19)",
            "defective_revision": "sole parent 39444b99c097c9f53536ad8f16cd9f0288c7f695 (clientconn.go)",
            "introducing_revision": None,
            "introducing_revision_reason": "not established by any record",
        },
        "counterpart_class": "historical pair, identical test backport",
        "counterpart_justification": "V_bad clientconn.go blob e74f8e40 = parent; end2end_test.go 30d8a8c8 in both; go.mod/go.sum and module list identical (re-verified 2026-09-25).",
        "obligation": "after GO_AWAY on connection 1 and its closure, the client keeps using the healthy replacement transport; ten UnaryCalls succeed within the test's 20 s context.",
        "mechanism": "createTransport's allowedToReset branch nils a healthy ac.transport after the GO_AWAY reset; oneReset already fired, so the picker spins on a READY addrConn with nil transport.",
        "reconstruction_deviations": [
            "module mode from the revision's own go.mod instead of GoReal's unpinned GOPATH go get",
            "shallow fetch of the exact commit instead of full clone+reset",
        ],
        "evidence": [f"{OLD}/task5_grpc2391_restoration.md", f"{OLD}/task_c3_candidate_acquisition.md (card C-04)", f"{T5}/grpc2391/run/frozen_protocol.txt", f"{T5}/grpc2391/run/attempt.sh", f"{T5}/grpc2391/blob_check_bug.txt", f"{T5}/grpc2391/dep_versions_bug.txt"],
        "competing_explanations": "FullDuplexCall failure, 'expected the stream to die', listen/start failure, leakcheck without an (a) line, or UnaryCall errors with other codes are not focal.",
        "slowness_review": "See c1_harness/cards.py: the 20 s context spans the whole test (pass ~0.01 s); a non-defect DeadlineExceeded needs ~2000x slowdown. The witness cannot itself distinguish that from the spin; source argument only.",
        "identity_note": "Image IDs equal the restoration record and frozen protocol.",
    },
    "istio17860": {
        "upstream": {
            "fix": "istio PR 17860 'Fix deadlock in envoy restart logic.', squash-merge c6e9130227497ab064dd571a1409236d17aa2ef3 (2019-10-15)",
            "defective_revision": "sole parent 7a9a996f6641024298e6010c6f1d7e87a83a48dc (pkg/envoy/agent.go)",
            "introducing_revision": None,
            "introducing_revision_reason": "not established; PR body is an unfilled template and links no issue",
        },
        "counterpart_class": "historical production pair, identical fix test",
        "counterpart_justification": "V_bad agent.go blob f6644419 = parent; agent_test.go 09ea287d in both (GoReal's V_bad-only test edit not applied); identical go.mod replace and module list (re-verified 2026-09-25).",
        "obligation": "while a hot restart waits for the previous epoch to go live, the agent still processes that epoch's exit; epoch 1 starts within the test's 5 s bound.",
        "mechanism": "Restart holds a.mu through waitUntilLive (up to 20 s); Run's exit handler needs a.mu to delete the exited epoch.",
        "reconstruction_deviations": [
            "replace bitbucket.org/ww/goautoneg => github.com/munnerz/goautoneg on BOTH images (Bitbucket 404; GoReal adds it to bug only)",
            "GoReal's vim/python3 install not reproduced on either image",
            "agent.go-only patch (GoReal's V_bad test edit excluded)",
        ],
        "evidence": [f"{OLD}/task5_istio17860_restoration.md", f"{OLD}/task_c3_candidate_acquisition.md (card C-05)", f"{T5}/istio17860/run/frozen_protocol.txt", f"{T5}/istio17860/run/attempt.sh", f"{T5}/istio17860/blob_check_bug.txt", f"{T5}/istio17860/dep_versions_bug.txt"],
        "competing_explanations": "Gomega BeTemporally failures (1 s threshold, author-flagged flake risk) are UNRESOLVED on either version and reported separately on V_ok.",
        "slowness_review": "See c1_harness/cards.py: 5 s for a few goroutine hand-offs (pass ~0.5 s). The 1 s BeTemporally check is the timing-sensitive, non-focal assertion.",
        "identity_note": "Image IDs equal the restoration record and frozen protocol.",
    },
    "k8s26980": {
        "upstream": {
            "fix": "kubernetes PR 26980 'processor listener: fix locking in pop()', merge 628af356b8c83f98ee3b50dfcf8b0250816a5581 (2016-06-13)",
            "defective_revision": "first parent 98f0d22bcccbacaa0f5a6846b55ecfc6590b18bc (shared_informer.go)",
            "introducing_revision": None,
            "introducing_revision_reason": "not established by any record",
        },
        "counterpart_class": "historical parent production plus identical fix test",
        "counterpart_justification": "V_bad shared_informer.go blob ce9ddf2c = first parent; processor_listener_test.go ffd72d8f in both (GoReal's V_bad-only test mutation not restored); Godeps.json identical; vendored deps (re-verified 2026-09-25).",
        "obligation": "processorListener.pop must not hold p.lock while blocked sending to nextCh; another goroutine can acquire p.lock while pop waits.",
        "mechanism": "pop takes p.lock at entry and keeps it while selecting on the unbuffered nextCh send; with a pending notification and no receiver it blocks holding the lock.",
        "reconstruction_deviations": [
            "shallow fetch of the merge commit instead of full clone+reset",
            "GoReal's rsync/vim/python3 installs dropped on both images",
            "shared_informer.go-only patch (GoReal's V_bad test edit excluded)",
        ],
        "evidence": [f"{OLD}/task5_k8s26980_restoration.md", f"{OLD}/task_c4_candidate_acquisition.md (card C-06)", f"{T5}/k8s26980/run/frozen_protocol.txt", f"{T5}/k8s26980/run/attempt.sh", f"{T5}/k8s26980/blob_check_bug.txt"],
        "competing_explanations": "Go test-timeout dump or panic is UNRESOLVED. Q0 observed 0/20 (+0/5) focal on V_bad: stable-pass behaviour under the default scheduler.",
        "slowness_review": "See c1_harness/cards.py: 30 s to acquire an unheld mutex in V_ok. No positive log exists; source review and synthetic parsing fixtures only.",
        "identity_note": "Image IDs equal the restoration record and frozen protocol.",
    },
}


def build(image_checks: dict[str, Any], replay: dict[str, Any], reviewer: str, date: str) -> dict[str, Any]:
    hashes = rule_hashes()
    subjects: dict[str, Any] = {}
    for sid in SUBJECT_ORDER:
        facts = image_checks["results"][sid]["facts"]
        evaluation = image_checks["results"][sid]["evaluation"]
        st = STATIC[sid]
        card = CARDS[sid]
        replay_counts = {part: replay["summary"][part].get(sid) for part in replay["summary"]}
        positive = replay["focal_positive_logs_by_subject"].get(sid, 0)
        variants = {}
        for version, variant in ((V_BAD, "bug"), (V_OK, "fix")):
            f = facts[variant]
            variants[version] = {
                "image_tag": f"{sid}-{variant}",
                "image_id": f["image_id"],
                "commit": f.get("commit"),
                "focal_blobs": {k: v for k, v in f["blob"].items()},
                "target_package_test_files": f["testfile"],
                "test_binary_sha256": f.get("binary_sha256"),
                "test_binary_bytes": int(f["binary_bytes"]) if f.get("binary_bytes") else None,
                "go_version": f.get("go_version"),
                "gopath_nonrepo_sources_digest": f.get("gopath_deps_digest"),
                "gopath_dependency_repos": f["deprepo"],
                "dep_versions_txt_sha256": f.get("dep_versions_sha256"),
                "go_list_m_all_sha256": f.get("go_list_m_all_sha256"),
                "vendored_in_tree": bool(f.get("vendor_dir") or f.get("cmd_vendor_dir")),
                "tree_changes_vs_commit": f["porcelain"],
                "base_image_digest": None,
                "base_image_digest_reason": "locally built image; no registry digest recorded and no golang base image present locally",
                "archive": None,
                "archive_reason": "image retained only in the local Docker Desktop VM; no docker save archive exists",
            }
        disposition = "READY_HISTORICAL" if evaluation["passed"] else "UNRESOLVED"
        cmd = FROZEN_COMMANDS[sid]
        subjects[sid] = {
            "subject": sid,
            "project": cmd["project"],
            "upstream": st["upstream"],
            "counterpart_class": st["counterpart_class"],
            "counterpart_justification": st["counterpart_justification"],
            "obligation": st["obligation"],
            "mechanism": st["mechanism"],
            "reconstruction_deviations": st["reconstruction_deviations"],
            "evidence": st["evidence"] + ["research_runs/ci_configuration_2026_09/prep/image_checks.json"],
            "variants": variants,
            "equal_treatment_checks": evaluation["checks"],
            "execution": {
                "argv": cmd["argv"],
                "workdir": cmd["workdir"],
                "inner_timeout_s": cmd["inner_timeout_s"],
                "outer_timeout_s": cmd["outer_timeout_s"],
                "cleanup_timeout_s": 30,
                "expected_target": card.test_name,
            },
            "oracle": {
                "card": sid,
                "defined_in": "e1_harness/oracle.py" if sid in ("etcd5509", "etcd7492", "grpc1859") else "c1_harness/cards.py",
                "source": card.source,
                "signatures": {s.sid: s.summary for s in card.signatures},
                "notes": list(card.notes),
                "rule_hashes": hashes,
                "replay": replay_counts,
                "historical_focal_positive_logs": positive,
                "validation_status": (
                    "source review + replay; no positive runtime example exists" if positive == 0
                    else "source review + replay of historical positive and negative logs"
                ),
                "competing_explanations": st["competing_explanations"],
                "slowness_review": st["slowness_review"],
                "l_profile_validated": False,
                "l_profile_note": "not yet executed under the limited profile; smoke calibration checks execution and capture only",
            },
            "identity_note": st["identity_note"],
            "readiness": {
                "disposition": disposition,
                "enrolled": disposition in ("READY_HISTORICAL", "READY_RECONSTRUCTED"),
                "reason": (
                    "exact surviving images; counterpart, test/harness equality and dependency identity re-verified in image; "
                    "oracle rules ported and replayed" if evaluation["passed"] else "in-image checks failed"
                ),
                "reviewer": reviewer,
                "date": date,
                "q0_label_unchanged": True,
            },
        }
    return {
        "study_id": STUDY_ID,
        "artifact": "c1_subject_manifest_v1",
        "generated_from": [
            "research_runs/ci_configuration_2026_09/prep/image_checks.json",
            "research_runs/ci_configuration_2026_09/prep/oracle_replay.json",
            "c1_harness/dossier.py",
        ],
        "roster_order": list(SUBJECT_ORDER),
        "subjects": subjects,
    }


def main() -> None:
    prep = STUDY_DIR / "prep"
    checks = json.loads((prep / "image_checks.json").read_text(encoding="utf-8"))
    replay = json.loads((prep / "oracle_replay.json").read_text(encoding="utf-8"))
    manifest = build(checks, replay, reviewer="C1 implementation agent (single agent)", date="2026-09-25")
    (STUDY_DIR / "subject_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=False) + "\n", encoding="utf-8", newline="\n"
    )
    for sid, s in manifest["subjects"].items():
        print(f"{sid:11} {s['readiness']['disposition']:18} enrolled={s['readiness']['enrolled']}")


if __name__ == "__main__":
    main()
