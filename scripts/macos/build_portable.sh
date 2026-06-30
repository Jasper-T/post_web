#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="python3"
FILESYSTEM_ROOT=""
SKIP_INSTALL=0
NO_FRONTEND_BUILD=0
ONEDIR=0

usage() {
  cat <<'EOF'
Usage: scripts/macos/build_portable.sh [options]

Build a macOS portable package. Run this script on macOS, not Linux or Windows.

Options:
  --python PATH          Python executable to use. Default: python3
  --filesystem-root PATH Root directory shown in the file browser dialog
  --skip-install        Skip Python dependency installation
  --no-frontend-build   Reuse existing frontend/dist
  --onedir              Build PyInstaller onedir output instead of onefile
  -h, --help            Show this help

Output:
  release/macos/fuxing/
    fuxing
    start.command
    html/
    data/
    datasets/
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --python)
      PYTHON_BIN="$2"
      shift 2
      ;;
    --filesystem-root)
      FILESYSTEM_ROOT="$2"
      shift 2
      ;;
    --skip-install)
      SKIP_INSTALL=1
      shift
      ;;
    --no-frontend-build)
      NO_FRONTEND_BUILD=1
      shift
      ;;
    --onedir)
      ONEDIR=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "ERROR: macOS packages must be built on macOS. Current system: $(uname -s)" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
RELEASE_ROOT="$ROOT/release/macos"
PACKAGE_DIR="$RELEASE_ROOT/fuxing"
FINAL_PACKAGE_DIR="$PACKAGE_DIR"
FRONTEND_DIST="$ROOT/frontend/dist"
WHEEL="$ROOT/dsetkit-0.4.0-py3-none-any.whl"

step() {
  echo "==> $1"
}

copy_runtime_data() {
  local target_dir="$1"
  mkdir -p "$target_dir/data/logs"
  if [[ -f "$ROOT/data/groups.json" ]]; then
    cp "$ROOT/data/groups.json" "$target_dir/data/groups.json"
  fi
  if [[ -d "$ROOT/data/templates" ]]; then
    cp -R "$ROOT/data/templates" "$target_dir/data/templates"
  fi
}

write_portable_env() {
  local target_dir="$1"
  local env_file="$target_dir/fuxing.env"
  cat > "$env_file" <<'EOF'
# Fuxing portable runtime configuration
# FUXING_FILESYSTEM_ROOT controls the root directory shown by the file browser dialog.
# On macOS/Linux, leave it empty to default to /.
# Example: FUXING_FILESYSTEM_ROOT=/Users/yourname/Pictures
EOF
  if [[ -n "$FILESYSTEM_ROOT" ]]; then
    local resolved_root
    resolved_root="$(cd "$FILESYSTEM_ROOT" && pwd)"
    echo "FUXING_FILESYSTEM_ROOT=$resolved_root" >> "$env_file"
  fi
}

step "Check dsetkit wheel"
if [[ ! -f "$WHEEL" ]]; then
  echo "Missing wheel: $WHEEL" >&2
  exit 1
fi

if [[ "$SKIP_INSTALL" -eq 0 ]]; then
  step "Install backend and packaging dependencies"
  "$PYTHON_BIN" -m pip install -r "$ROOT/backend/requirements.txt"
  "$PYTHON_BIN" -m pip install "$WHEEL"
  "$PYTHON_BIN" -m pip install pyinstaller
fi

if [[ "$NO_FRONTEND_BUILD" -eq 0 ]]; then
  step "Build frontend"
  (cd "$ROOT/frontend" && npm install && npm run build)
fi

if [[ ! -d "$FRONTEND_DIST" ]]; then
  echo "Missing frontend build output: $FRONTEND_DIST" >&2
  exit 1
fi

step "Prepare release folders"
mkdir -p "$RELEASE_ROOT"
rm -f "$RELEASE_ROOT/fuxing"
mkdir -p "$PACKAGE_DIR"
find "$PACKAGE_DIR" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
mkdir -p "$PACKAGE_DIR/datasets"
copy_runtime_data "$PACKAGE_DIR"
write_portable_env "$PACKAGE_DIR"
cp -R "$FRONTEND_DIST" "$PACKAGE_DIR/html"

step "Build executable"
PYINSTALLER_ARGS=(
  --clean
  --noconfirm
  --name fuxing
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
  --workpath "$ROOT/build/pyinstaller-macos"
  --specpath "$ROOT/build/pyinstaller-macos"
  "$ROOT/backend/launcher.py"
)

if [[ "$ONEDIR" -eq 0 ]]; then
  PYINSTALLER_ARGS=(--onefile "${PYINSTALLER_ARGS[@]}")
fi

"$PYTHON_BIN" -m PyInstaller "${PYINSTALLER_ARGS[@]}"

if [[ "$ONEDIR" -eq 1 ]]; then
  BUILT_DIR="$RELEASE_ROOT/fuxing"
  if [[ ! -x "$BUILT_DIR/fuxing" ]]; then
    echo "PyInstaller did not create expected executable in $BUILT_DIR" >&2
    exit 1
  fi
  cp -R "$PACKAGE_DIR/html" "$BUILT_DIR/html"
  cp -R "$PACKAGE_DIR/data" "$BUILT_DIR/data"
  cp -R "$PACKAGE_DIR/datasets" "$BUILT_DIR/datasets"
  cp "$PACKAGE_DIR/fuxing.env" "$BUILT_DIR/fuxing.env"
  FINAL_PACKAGE_DIR="$BUILT_DIR"
else
  mv "$RELEASE_ROOT/fuxing" "$PACKAGE_DIR/fuxing"
fi

step "Write launch helper"
cat > "$FINAL_PACKAGE_DIR/start.command" <<'EOF'
#!/usr/bin/env bash
cd "$(dirname "$0")"
./fuxing
EOF
chmod +x "$FINAL_PACKAGE_DIR/start.command"
chmod +x "$FINAL_PACKAGE_DIR/fuxing"

cat > "$FINAL_PACKAGE_DIR/使用说明.txt" <<'EOF'
Fuxing macOS 便携版

1. 双击 start.command 启动，或在终端中运行 ./fuxing。
2. 程序会自动打开浏览器访问 http://127.0.0.1:8000。
3. data 文件夹保存应用配置、pipeline、日志和运行结果。
4. datasets 文件夹用于保存从前端上传到后端机器的数据集。
5. 如果 8000 端口被占用，可在终端中运行：./fuxing --port 8001
6. 文件浏览弹窗默认显示 /；可编辑 fuxing.env 或使用 --filesystem-root 指定可见根目录。

如果 macOS 提示无法打开，请到“系统设置 > 隐私与安全性”中允许该程序，或在终端执行：
  xattr -dr com.apple.quarantine fuxing start.command
EOF

echo "Portable macOS package created:"
echo "  $FINAL_PACKAGE_DIR"
echo "Run:"
echo "  $FINAL_PACKAGE_DIR/start.command"