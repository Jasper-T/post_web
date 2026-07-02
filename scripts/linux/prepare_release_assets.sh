#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

FILESYSTEM_ROOT=""
PROJECT_ARG="web-post"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --filesystem-root) FILESYSTEM_ROOT="$2"; shift 2 ;;
    --project-name) PROJECT_ARG="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

set_release_project_name "$PROJECT_ARG"

prepare_release_folders_and_assets() {
  assert_path_exists "$FRONTEND_DIST" "Missing frontend dist: $FRONTEND_DIST. Run build_frontend.sh first, or run release.sh with --no-frontend-build."

  rm -rf "$PACKAGE_DIR" "$ASSETS_STAGE_DIR" "$RELEASE_ROOT/$PROJECT_NAME"
  mkdir -p "$RELEASE_ROOT" "$ASSETS_STAGE_DIR" "$ASSETS_STAGE_DIR/datasets"

  copy_runtime_data "$ASSETS_STAGE_DIR"
  write_portable_env "$ASSETS_STAGE_DIR" "$FILESYSTEM_ROOT"
  cp -R "$FRONTEND_DIST" "$ASSETS_STAGE_DIR/html"
}

invoke_step "Prepare release folders and assets" prepare_release_folders_and_assets
