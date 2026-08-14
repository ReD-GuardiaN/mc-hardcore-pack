#!/usr/bin/env bash
# One command to rebuild + republish. Each run cuts a new tag, so the download
# URL is always fresh - no CDN cache to wait out during the tuning loop.
set -euo pipefail
cd "$(dirname "$0")"
REPO=ReD-GuardiaN/mc-hardcore-pack

./build.sh
SHA=$(cat dist/hcpack.zip.sha1)

N=$(( $(cat .build-number 2>/dev/null || echo 0) + 1 ))
echo "$N" > .build-number
TAG="v$N"

git add -A
git commit -qm "pack build $TAG" || true
git push -q origin HEAD
gh release create "$TAG" dist/hcpack.zip --repo "$REPO" \
   --title "$TAG" --notes "sha1 \`$SHA\`" >/dev/null

URL="https://github.com/$REPO/releases/download/$TAG/hcpack.zip"
echo
echo "url:  $URL"
echo "sha1: $SHA"
printf '%s %s\n' "$URL" "$SHA" > dist/LATEST.txt
