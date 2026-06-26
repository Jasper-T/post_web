# Fuxing 2

Fuxing 2 is a FastAPI + Vue 3 application for image dataset browsing, HTTP vision-pipeline testing, response parsing, visualization, and dsetkit-powered annotation conversion. It can run as a Docker stack for development or as a portable desktop-style package where the backend executable serves both API and frontend files.

## What It Does

- Browse image files from a configurable backend-visible filesystem root.
- Upload files or folders from the frontend user's machine into the backend machine's datasets folder.
- Create, group, clone, test, and delete HTTP image pipelines.
- Send images to a pipeline, inspect raw JSON responses, parse detections, and preview rendered boxes.
- Save prediction visualizations and compare with GT labels.
- Run dsetkit tools for dataset conversion and plotting.
- Use a built-in demo image pipeline for first-run testing.

## Project Layout

```text
fuxing_2/
  backend/                 FastAPI backend, pipeline registry, launcher, and tools
  frontend/                Vue 3 frontend and production build
  data/                    Runtime pipeline templates, groups, logs, and results
  datasets/                Local dataset root for development; portable builds create this folder
  scripts/                 Build and maintenance scripts
  release/                 Generated portable packages
  dsetkit-0.3.1-py3-none-any.whl
  docker-compose.yml
```

A portable Windows package has this shape:

```text
fuxing/
  fuxing.exe
  start.bat
  fuxing.env
  html/
  data/
  datasets/
```

Keep these files and folders together. The executable reads runtime data and frontend files from sibling folders.

## Runtime Directories

- `html/`: built frontend files served by the backend launcher.
- `data/`: pipeline groups, pipeline JSON templates, logs, and run results.
- `datasets/`: fixed upload destination on the backend machine.

The file browser dialog and upload feature intentionally use different scopes:

- File browser root: controlled by `FUXING_FILESYSTEM_ROOT`; Linux/macOS default is `/`, Windows portable default is the drive that contains `fuxing.exe`.
- Upload source: selected freely by the browser from the frontend user's machine.
- Upload target: always `FUXING_DATASETS_ROOT`, which defaults to `fuxing/datasets` in portable builds.

This supports a common deployment shape where the frontend is opened on machine A and the backend runs on machine B. Upload transfers files from A into B's datasets folder.

## Configuration

The launcher reads configuration in this order:

1. Command-line options, such as `--filesystem-root D:\datasets`.
2. `fuxing.env` next to the executable.
3. Platform defaults.

Useful environment variables:

```text
FUXING_FILESYSTEM_ROOT   Root shown by the file browser dialog
FUXING_DATA_ROOT         Runtime app data directory
FUXING_DATASETS_ROOT     Backend upload target directory
FUXING_FRONTEND_DIST     Built frontend directory
FUXING_BASE_URL          Internal base URL used by the demo pipeline
```

## Windows Portable Build

Build from the project root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\windows\build_portable.ps1
```

Build with a custom file-browser root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\windows\build_portable.ps1 -FileSystemRoot D:\works\datasets
```

Useful options:

- `-Python <path>`: choose the Python executable.
- `-NoFrontendBuild`: reuse existing `frontend/dist`.
- `-SkipInstall`: skip Python dependency installation.
- `-OneDir`: build PyInstaller onedir output instead of the default onefile exe.

## macOS Portable Build

The macOS package must be built on macOS:

```bash
scripts/macos/build_portable.sh
```

With a custom file-browser root:

```bash
scripts/macos/build_portable.sh --filesystem-root /Users/you/datasets
```

## Docker Compose

Start both backend and frontend containers:

```powershell
docker compose up -d --build
```

Default services:

- Backend API: http://localhost:8000
- Frontend: http://localhost:5173

The backend Docker image installs `backend/requirements.txt` and the local `dsetkit-0.3.1-py3-none-any.whl`.

## Local Development

Backend:

```bash
python -m pip install -r backend/requirements.txt
python -m pip install dsetkit-0.3.1-py3-none-any.whl
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Production frontend build:

```bash
cd frontend
npm run build
```

## Demo Pipeline

`data/templates/Ungrouped/demo_image_pipeline` is included by default. It points to the backend's built-in mock detection endpoint and accepts an image payload. Use it to confirm that file browsing, request construction, response mapping, and visualization are working before connecting a real algorithm service.
