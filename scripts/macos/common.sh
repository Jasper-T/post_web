#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
RELEASE_ROOT="$ROOT/release/macos"
PROJECT_NAME="web-post"
PACKAGE_DIR="$RELEASE_ROOT/$PROJECT_NAME"
ASSETS_STAGE_DIR="$RELEASE_ROOT/_assets_stage"
FRONTEND_DIST="$ROOT/frontend/dist"
WHEEL="$ROOT/backend/wheels/dsetkit-0.4.1-py3-none-any.whl"
DEMO_PIPELINE_DIR="$ROOT/data/templates/Ungrouped/demo_image_pipeline"

set_release_project_name() {
  local name="${1:-web-post}"
  name="$(printf '%s' "$name" | xargs)"
  if [[ -z "$name" ]]; then
    echo "ProjectName cannot be empty." >&2
    exit 1
  fi
  if [[ "$name" == *"/"* || "$name" == *":"* ]]; then
    echo "ProjectName contains invalid file name characters: $name" >&2
    exit 1
  fi
  PROJECT_NAME="$name"
  PACKAGE_DIR="$RELEASE_ROOT/$PROJECT_NAME"
}

invoke_step() {
  local name="$1"
  shift
  printf '\033[36m==> %s\033[0m\n' "$name"
  "$@"
}

assert_path_exists() {
  local path="$1"
  local message="$2"
  if [[ ! -e "$path" ]]; then
    echo "$message" >&2
    exit 1
  fi
}

resolve_python_executable() {
  local venv_python="$ROOT/.venv/bin/python"
  if [[ -x "$venv_python" ]]; then
    printf '%s\n' "$venv_python"
    return 0
  fi
  echo "Python was not found in the uv environment. Run uv sync --group release first." >&2
  exit 1
}

invoke_pyinstaller() {
  local python_path="$1"
  shift
  if "$python_path" -m PyInstaller "$@"; then
    return 0
  fi
  if "$python_path" -m pyinstaller "$@"; then
    return 0
  fi
  echo "PyInstaller failed." >&2
  exit 1
}

copy_release_assets() {
  local target_dir="$1"
  mkdir -p "$target_dir"
  rm -rf "$target_dir/html" "$target_dir/data" "$target_dir/datasets"
  cp -R "$ASSETS_STAGE_DIR/html" "$target_dir/html"
  cp -R "$ASSETS_STAGE_DIR/data" "$target_dir/data"
  cp -R "$ASSETS_STAGE_DIR/datasets" "$target_dir/datasets"
  cp -f "$ASSETS_STAGE_DIR/web-post.env" "$target_dir/web-post.env"
}

copy_runtime_data() {
  local target_dir="$1"
  local data_dir="$target_dir/data"
  local template_target="$data_dir/templates/Ungrouped/demo_image_pipeline"

  mkdir -p "$data_dir/logs" "$data_dir/.cache" "$(dirname "$template_target")"
  assert_path_exists "$DEMO_PIPELINE_DIR" "Missing demo pipeline directory: $DEMO_PIPELINE_DIR"
  rm -rf "$template_target"
  cp -R "$DEMO_PIPELINE_DIR" "$template_target"
}

write_portable_env() {
  local target_dir="$1"
  local filesystem_root="${2:-}"
  local env_path="$target_dir/web-post.env"

  {
    echo "# $PROJECT_NAME portable runtime configuration"
    echo "# WEB_POST_FILESYSTEM_ROOT controls the root directory shown by the file browser dialog."
    echo "# On macOS, leave it empty to default to the volume that contains $PROJECT_NAME."
    echo "# Example: WEB_POST_FILESYSTEM_ROOT=/Users/Shared"
    if [[ -n "$(printf '%s' "$filesystem_root" | xargs)" ]]; then
      local resolved_root
      resolved_root="$(cd "$filesystem_root" && pwd)"
      echo "WEB_POST_FILESYSTEM_ROOT=$resolved_root"
    fi
  } > "$env_path"
}

write_launch_helper() {
  local target_dir="$1"
  local exe_name="$PROJECT_NAME"
  cat > "$target_dir/start.command" <<EOF2
#!/usr/bin/env bash
set -euo pipefail
cd "\$(dirname "\$0")"
./$exe_name
EOF2
  chmod +x "$target_dir/start.command"
}
