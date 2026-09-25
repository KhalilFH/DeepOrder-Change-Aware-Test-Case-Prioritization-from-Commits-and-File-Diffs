"""F1 R2 step 1: extract the Airavata slice from the LOCAL TCP-CI archive.

Same member filter as cloud/fetch_airavata_slice.py at 25eb6b7 (`want`), but the
source is the local file instead of the Zenodo URL. One streaming pass also
computes the SHA-256 of the compressed archive for provenance.

    python analysis/extract_slice.py <archive.tar.gz> <out_dir> <manifest.json>
"""
import hashlib
import json
import os
import sys
import tarfile
import time

SUBJECT = "airavata"


class HashingReader:
    def __init__(self, fh):
        self.fh, self.h, self.n = fh, hashlib.sha256(), 0

    def read(self, size=-1):
        b = self.fh.read(size)
        self.h.update(b)
        self.n += len(b)
        return b


def want(member):  # identical to fetch_airavata_slice.want with defaults
    if not member.isfile():
        return False
    p = member.name.lower()
    if SUBJECT not in p:
        return False
    if "/analysis/" in p or "/build_logs/" in p:
        return False
    return True


def main(archive, out, manifest_path):
    t0 = time.time()
    extracted, seen = [], 0
    with open(archive, "rb") as raw:
        hr = HashingReader(raw)
        with tarfile.open(fileobj=hr, mode="r|gz") as tar:
            for m in tar:
                seen += 1
                if want(m):
                    dest = os.path.join(out, m.name)
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    src = tar.extractfile(m)
                    h = hashlib.sha256()
                    with open(dest, "wb") as f:
                        while True:
                            chunk = src.read(1 << 20)
                            if not chunk:
                                break
                            h.update(chunk)
                            f.write(chunk)
                    extracted.append({"name": m.name, "size": m.size, "sha256": h.hexdigest()})
                if seen % 50000 == 0:
                    print(f"scanned {seen:,} members, {hr.n/1e9:.2f} GB read, {time.time()-t0:.0f}s, kept {len(extracted)}", flush=True)
        while hr.read(1 << 20):  # hash any trailing bytes after the tar end marker
            pass
    manifest = {
        "archive": os.path.basename(archive),
        "archive_bytes": hr.n,
        "archive_sha256": hr.h.hexdigest(),
        "filter": "fetch_airavata_slice.want @25eb6b7, SUBJECT=airavata, no analysis/, no build_logs/",
        "members_scanned": seen,
        "bundled_git_found": any("/.git/" in e["name"] for e in extracted),
        "extracted_count": len(extracted),
        "extracted": extracted,
        "elapsed_sec": round(time.time() - t0, 1),
    }
    with open(manifest_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")
    print(json.dumps({k: v for k, v in manifest.items() if k != "extracted"}, indent=2))


if __name__ == "__main__":
    main(*sys.argv[1:4])
