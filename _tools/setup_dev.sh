#!/bin/bash
# One-time setup for the tests, review screenshots and asset tools (none of this is published).
#   bash _tools/setup_dev.sh
# Creates .venv/ (git-ignored) and downloads axe-core into _tools/.cache/ (git-ignored).
# Browser tests use the Mac's Google Chrome (headless); no Playwright browser download needed.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -x .venv/bin/python ] || python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r _tools/requirements-dev.txt

AXE_VERSION=4.14.0
AXE_SHA512=9WTZxEjsZ7b13TH8JPmbV2z8CHbl80/2hm3XPEG4JgNdQLK81IBRXmSxHfMAOkSqQeRxT/0dwNDz2GOm3zzpcQ==
CACHE=_tools/.cache/axe-core-$AXE_VERSION
if [ ! -f "$CACHE/axe.min.js" ]; then
  mkdir -p "$CACHE"
  TGZ="$CACHE/axe-core.tgz"
  curl -sSfL -o "$TGZ" "https://registry.npmjs.org/axe-core/-/axe-core-$AXE_VERSION.tgz"
  GOT=$(openssl dgst -sha512 -binary "$TGZ" | openssl base64 -A)
  if [ "$GOT" != "$AXE_SHA512" ]; then echo "axe-core checksum mismatch" >&2; rm -f "$TGZ"; exit 1; fi
  tar -xzf "$TGZ" -C "$CACHE" --strip-components=1 package/axe.min.js package/LICENSE
  rm -f "$TGZ"
fi
echo "Dev tools ready. Run the tests with: .venv/bin/python -m pytest _tools/tests"
