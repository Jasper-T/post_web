#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

PROJECT_ARG="web-post"
ONEFILE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-name) PROJECT_ARG="$2"; shift 2 ;;
    --onefile) ONEFILE=1; shift ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

set_release_project_name "$PROJECT_ARG"
PYTHON_EXE="$(resolve_python_executable)"

build_backend_executable() {
  local args=(
    --clean
    --noconfirm
    --name "$PROJECT_NAME"
    --paths "$ROOT"
    --collect-all dsetkit
    --hidden-import uvicorn.logging
    --hidden-import uvicorn.loops.auto
    --hidden-import uvicorn.protocols.http.auto
    --hidden-import uvicorn.protocols.websockets.auto
    --hidden-import uvicorn.lifespan.on
    --hidden-import requests
    --hidden-import tqdm
    --distpath "$RELEASE_ROOT"
    --workpath "$ROOT/build/pyinstaller"
    --specpath "$ROOT/build/pyinstaller"
    "$ROOT/backend/launcher.py"
  )

  if [[ "$ONEFILE" -eq 1 ]]; then
    args=(--onefile "${args[@]}")
  fi

  invoke_pyinstaller "$PYTHON_EXE" "${args[@]}"
}

invoke_step "Build backend executable" build_backend_executable
