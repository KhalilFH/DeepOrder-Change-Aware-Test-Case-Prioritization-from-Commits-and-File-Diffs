#!/bin/sh
# Pinned replacement for GoReal's unpinned `go get -d` step.
# Each dependency is cloned into the GOPATH at the last commit <= 2018-02-13
# (the subject's merge date). Identical in both images.
set -e
while IFS='|' read -r pkg url sha; do
  [ -z "$pkg" ] && continue
  dir="/go/src/$pkg"
  mkdir -p "$(dirname "$dir")"
  git clone -q "$url" "$dir"
  git -C "$dir" checkout -q "$sha"
  printf '%s %s\n' "$pkg" "$(git -C "$dir" rev-parse HEAD)"
done < /tmp/deps.txt > /go/dep_versions.txt
cat /go/dep_versions.txt
