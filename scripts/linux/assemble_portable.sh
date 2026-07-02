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
FINAL_PACKAGE_DIR="$PACKAGE_DIR"
EXE_NAME="$PROJECT_NAME"

assemble_portable_package() {
  assert_path_exists "$ASSETS_STAGE_DIR" "Missing staged assets: $ASSETS_STAGE_DIR. Run prepare_release_assets.sh first."

  if [[ "$ONEFILE" -eq 1 ]]; then
    local built_exe="$RELEASE_ROOT/$EXE_NAME"
    if [[ ! -f "$built_exe" ]]; then
      built_exe="$(find "$RELEASE_ROOT" -type f -name "$EXE_NAME" -perm -111 | head -n 1 || true)"
      if [[ -z "$built_exe" ]]; then
        echo "PyInstaller finished but $EXE_NAME was not found under $RELEASE_ROOT. Run default OneDir mode or inspect PyInstaller output." >&2
        exit 1
      fi
    fi
    mkdir -p "$PACKAGE_DIR"
    copy_release_assets "$PACKAGE_DIR"
    mv -f "$built_exe" "$PACKAGE_DIR/$EXE_NAME"
    chmod +x "$PACKAGE_DIR/$EXE_NAME"
    FINAL_PACKAGE_DIR="$PACKAGE_DIR"
  else
    local built_dir="$RELEASE_ROOT/$PROJECT_NAME"
    local built_exe="$built_dir/$EXE_NAME"
    if [[ ! -f "$built_exe" ]]; then
      echo "PyInstaller did not create expected executable: $built_exe" >&2
      exit 1
    fi
    copy_release_assets "$built_dir"
    chmod +x "$built_exe"
    FINAL_PACKAGE_DIR="$built_dir"
  fi

  write_launch_helper "$FINAL_PACKAGE_DIR"
  find "$FINAL_PACKAGE_DIR" -type f -name direct_url.json -delete
}

clean_temporary_release_assets() {
  rm -rf "$ASSETS_STAGE_DIR"
}

invoke_step "Assemble portable package" assemble_portable_package
invoke_step "Clean temporary release assets" clean_temporary_release_assets

printf '\033[32mPortable Linux package created:\033[0m\n'
echo "  $FINAL_PACKAGE_DIR"
echo "Run:"
echo "  $FINAL_PACKAGE_DIR/$EXE_NAME"
echo "  or run helper: $FINAL_PACKAGE_DIR/start.sh"
