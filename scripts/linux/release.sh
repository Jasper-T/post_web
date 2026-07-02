#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

PROJECT_ARG="web-post"
FILESYSTEM_ROOT=""
NO_FRONTEND_BUILD=0
ONEDIR=0
ONEFILE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-name) PROJECT_ARG="$2"; shift 2 ;;
    --filesystem-root) FILESYSTEM_ROOT="$2"; shift 2 ;;
    --no-frontend-build) NO_FRONTEND_BUILD=1; shift ;;
    --onedir) ONEDIR=1; shift ;;
    --onefile) ONEFILE=1; shift ;;
    -h|--help)
      cat <<HELP
Usage: ./release.sh [options]

Options:
  --project-name NAME       Output executable/package name. Default: web-post
  --filesystem-root PATH    Value written to WEB_POST_FILESYSTEM_ROOT in web-post.env
  --no-frontend-build       Reuse existing frontend/dist
  --onedir                  Build PyInstaller OneDir mode. This is the default.
  --onefile                 Build PyInstaller OneFile mode.
HELP
      exit 0
      ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

set_release_project_name "$PROJECT_ARG"

if [[ "$ONEDIR" -eq 1 && "$ONEFILE" -eq 1 ]]; then
  echo "Use only one of --onedir or --onefile. By default this script builds OneDir." >&2
  exit 1
fi

USE_ONEFILE="$ONEFILE"

check_release_inputs() {
  assert_path_exists "$WHEEL" "Missing wheel: $WHEEL"
  assert_path_exists "$DEMO_PIPELINE_DIR" "Missing demo pipeline directory: $DEMO_PIPELINE_DIR"

  echo "Project: $PROJECT_NAME"
  if [[ "$USE_ONEFILE" -eq 1 ]]; then
    echo "Mode: onefile"
  else
    echo "Mode: onedir"
  fi
  echo "Dependency sync: uv sync --group release"
  echo "Python: .venv/bin/python after uv sync"
}

run_phase() {
  local script_name="$1"
  shift || true
  local script_path="$SCRIPT_DIR/$script_name"
  if [[ ! -f "$script_path" ]]; then
    echo "Missing script: $script_path" >&2
    exit 1
  fi
  printf '\033[90mRun: %s %s\033[0m\n' "$script_path" "$*"
  bash "$script_path" "$@"
}

invoke_step "Check release inputs" check_release_inputs

run_phase install_dependencies.sh

if [[ "$NO_FRONTEND_BUILD" -eq 0 ]]; then
  run_phase build_frontend.sh
fi

prepare_args=(--project-name "$PROJECT_NAME")
if [[ -n "$(printf '%s' "$FILESYSTEM_ROOT" | xargs)" ]]; then
  prepare_args+=(--filesystem-root "$FILESYSTEM_ROOT")
fi
run_phase prepare_release_assets.sh "${prepare_args[@]}"

backend_args=(--project-name "$PROJECT_NAME")
assemble_args=(--project-name "$PROJECT_NAME")
if [[ "$USE_ONEFILE" -eq 1 ]]; then
  backend_args+=(--onefile)
  assemble_args+=(--onefile)
fi

run_phase build_backend_executable.sh "${backend_args[@]}"
run_phase assemble_portable.sh "${assemble_args[@]}"
