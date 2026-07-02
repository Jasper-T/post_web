#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

sync_dependencies() {
  if ! command -v uv >/dev/null 2>&1; then
    echo "uv was not found. Install uv first, then rerun release.sh." >&2
    exit 1
  fi

  pushd "$ROOT" >/dev/null
  uv sync --group release
  popd >/dev/null

  local python_exe
  python_exe="$(resolve_python_executable)"
  invoke_pyinstaller "$python_exe" --version
}

invoke_step "Sync project dependencies with uv" sync_dependencies
