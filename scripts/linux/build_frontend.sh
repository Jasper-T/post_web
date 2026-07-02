#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

build_frontend() {
  pushd "$ROOT/frontend" >/dev/null
  npm install
  npm run build
  popd >/dev/null
}

invoke_step "Build frontend" build_frontend
