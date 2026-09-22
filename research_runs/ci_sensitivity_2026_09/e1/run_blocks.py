"""Run E1 measured blocks for one episode, exactly as frozen in e1_protocol.md.

    python research_runs/ci_sensitivity_2026_09/e1/run_blocks.py etcd5509 1-10

Refuses to start unless the manifest hashes to its frozen value and every
image ID is present locally. Blocks already in the ledger are refused, not
re-run. A Python-level failure stops the run; nothing is retried.
Before each block `docker info` must succeed; if it does not, the run stops
rather than filling blocks with attempts that never started. Classifying
attempts is left to oracle.py.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "e1_harness"))

from ledger import Ledger, read_records  # noqa: E402
from runner import RUNNER_VERSION, Manifest, Runner  # noqa: E402

FROZEN_MANIFEST_SHA256 = {
    "etcd5509": "a88cc638f51ebab31580aaf25948e9ce5968ab0fe23c29b50246ec60d66f5791",
    "etcd7492": "860cb23ef6abd35f6273e21f40557ecba481a167ee5ea4ad629577c9480d4620",
}
MEASURED_BLOCKS = range(1, 21)


def block_seed(episode: str, block: int) -> int:
    """The frozen seed rule: first 32 bits of SHA-256("e1:<episode>:block:<n>")."""
    return int(hashlib.sha256(f"e1:{episode}:block:{block}".encode()).hexdigest()[:8], 16)


def parse_range(text: str) -> list[int]:
    lo, _, hi = text.partition("-")
    return list(range(int(lo), int(hi or lo) + 1))


def docker_ready() -> bool:
    try:
        return subprocess.run(["docker", "info"], capture_output=True, timeout=30).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def main() -> int:
    episode, blocks = sys.argv[1], parse_range(sys.argv[2])
    manifest = Manifest(**json.loads((HERE / "manifests.json").read_text(encoding="utf-8"))[episode])
    if manifest.sha256 != FROZEN_MANIFEST_SHA256[episode]:
        sys.exit(f"{episode}: manifest sha256 {manifest.sha256} is not the frozen value")
    if not set(blocks) <= set(MEASURED_BLOCKS):
        sys.exit(f"blocks {blocks} fall outside the measured range 1-20")
    for image in manifest.images.values():
        if subprocess.run(["docker", "image", "inspect", image], capture_output=True).returncode:
            sys.exit(f"image {image} is not present locally")

    path = HERE / episode / "attempts.jsonl"
    done = {r["block"] for r in read_records(path)} if path.exists() else set()
    if done & set(blocks):
        sys.exit(f"blocks {sorted(done & set(blocks))} are already in {path}; refusing to re-run")

    print(f"{episode} blocks {blocks[0]}-{blocks[-1]} manifest={manifest.sha256} runner={RUNNER_VERSION}", flush=True)
    runner = Runner(manifest)
    with Ledger(path) as led:
        for block in blocks:
            if not docker_ready():
                print(f"STOP before block {block}: docker info failed", flush=True)
                return 2
            seed = block_seed(episode, block)
            out = runner.run_block(led, block=block, seed=seed)
            print(f"block {block} seed={seed} first={out.first_version} {json.dumps(out.statuses)}", flush=True)
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
