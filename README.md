# web-post

web-post is a FastAPI + Vue 3 application for browsing image datasets, testing HTTP vision pipelines, inspecting raw and parsed responses, previewing annotations, converting annotations with dsetkit 0.4.0, and evaluating prediction results against ground truth.

The project can run as a Docker Compose stack, as a local development app, or as a Windows portable package where the backend executable serves both the API and the built frontend.

## Features

- Browse images from a backend-visible filesystem root controlled by `WEB_POST_FILESYSTEM_ROOT`.
- Upload files or folders from the browser machine into the backend datasets directory.
- Create, clone, move, delete, and group HTTP image pipelines.
- Configure request Header JSON, Body JSON, Response sample JSON, response parsing, and request settings.
- Send one image or a selected batch of images to a pipeline.
- Inspect raw response JSON and parsed detection JSON.
- Preview prediction and GT annotations on images.
- Download generated Pred or GT annotated images to a local folder.
- Convert Pred or GT annotations to LabelMe, VOC, or YOLO with dsetkit 0.4.0.
- Evaluate predictions against GT with `dsetkit.dataset` and `dsetkit.evaluator`.

## Project Layout

```text
web-post/
  backend/                         FastAPI backend, pipeline core, launcher, tools
  backend/wheels/                  Local wheel dependencies, including dsetkit 0.4.0
  frontend/                        Vue 3 frontend
  frontend/src/styles/             Shared frontend style system
  data/templates/<group>/<pipeline>/ Pipeline definitions and JSON assets
  data/.cache/<pipeline>/<bucket>/ Runtime run results, previews, and conversions
  scripts/windows/                 Staged Windows release scripts
  scripts/macos/                   macOS packaging script; currently not in the main release path
  release/                         Generated release packages
  docker-compose.yml
  pyproject.toml
  uv.lock
```

Pipeline groups are discovered from folders under `data/templates`. `Ungrouped` and `Deleted` are required special groups and are created automatically when missing. A pipeline folder is named by `pipeline_name`; the user-facing `displayName` is stored inside `pipeline.json`. Both names must be globally unique.

## Template Privacy And Sharing

The open-source repository and portable release intentionally include only `data/templates/Ungrouped/demo_image_pipeline`. Real templates often contain private service URLs, headers, request bodies, response samples, class names, or customer-specific parsing rules, so treat them as local/private runtime data.

To reuse templates from another user or machine:

1. Copy the template folder into `data/templates/<group>/<pipeline_name>/`. For a portable package, copy it into `release/windows/web-post/data/templates/<group>/<pipeline_name>/`.
2. Keep the JSON files together, especially `pipeline.json`, `header.json`, `body.json`, `response.json`, `mapping.json`, and `post_config.json`.
3. Make sure `pipeline_name` and `displayName` are unique. If there is a conflict, rename the folder and update `pipeline.json` before starting the app.
4. Review copied files for private URLs, tokens, cookies, internal headers, sample payloads, and response data before sharing them.
5. Refresh the page after copying. If the template does not appear, restart the backend so it reloads `data/templates`.

Private template folders are ignored by git by default; only the demo pipeline is meant to be tracked.

## Runtime Data

Runtime data is stored under `data/` by default:

```text
data/
  templates/
    Ungrouped/demo_image_pipeline/
      pipeline.json
      header.json
      body.json
      response.json
      mapping.json
      post_config.json
  .cache/
    <pipeline>/<bucket>/
      post/
        _summary.json
        *.raw.json
        *.parsed.json
      pred/
      GT/
      labelme|voc|yolo/
  logs/
```

Cache bucket names are derived from the image input path. For `/root/1/2/3` or `/root/1/2/3/file.jpg`, the bucket is `2_3`.

## Configuration

In local development, `backend.main:app` reads environment variables directly. The packaged launcher in `backend/launcher.py` also reads `web-post.env` from the app directory and supports command-line arguments such as `--host`, `--port`, `--filesystem-root`, `--no-browser`, and `--reload`.

```text
WEB_POST_FILESYSTEM_ROOT   Root shown by file-system browsing controls
WEB_POST_DATA_ROOT         Runtime data directory, defaults to data
WEB_POST_DATASETS_ROOT     Upload destination on the backend machine
WEB_POST_FRONTEND_DIST     Built frontend directory served by the backend launcher
WEB_POST_BASE_URL          Base URL used by built-in demo/mock pipelines
LOG_LEVEL                  Backend log level, defaults to INFO
LOG_DIR                    Log directory, defaults to WEB_POST_DATA_ROOT/logs
LOG_ROTATION               Loguru file rotation, defaults to 10 MB
LOG_RETENTION              Loguru file retention, defaults to 14 days
```

The file browser root and upload destination are intentionally separate:

- Browse buttons show paths visible to the backend under `WEB_POST_FILESYSTEM_ROOT`.
- Upload selects files from the browser user's machine.
- Uploaded files are written to `WEB_POST_DATASETS_ROOT` on the backend machine.

## Dependency Management

Python dependencies are managed by uv. The project targets Python `>=3.12,<3.14`.

```powershell
uv sync
```

Release packaging dependencies such as PyInstaller are in the `release` dependency group:

```powershell
uv sync --group release
```

`dsetkit==0.4.0` is installed from the local wheel:

```text
backend/wheels/dsetkit-0.4.0-py3-none-any.whl
```

## Docker Compose

Start or rebuild the stack:

```powershell
docker compose up -d --build
```

The Compose stack uses `.env` / `.env.example` for host-side variables such as `WEB_POST_DATA_DIR`, `LOG_LEVEL`, `LOG_ROTATION`, and `LOG_RETENTION`. Backend application variables can also be set in `docker-compose.yml` or a local `docker-compose.override.yml`.

Default URLs:

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`

Useful checks:

```powershell
docker ps
docker exec webui-backend python -c "import backend.main, dsetkit, cv2, natsort; print('ok')"
```

## Local Development

Backend:

```powershell
uv sync
$env:WEB_POST_DATA_ROOT = ".\data"
$env:WEB_POST_FILESYSTEM_ROOT = "D:\"
$env:WEB_POST_DATASETS_ROOT = ".\datasets"
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

Production frontend build:

```powershell
cd frontend
npm run build
```

To test the backend launcher against the built frontend:

```powershell
.\.venv\Scripts\python.exe -m backend.launcher --no-browser --reload
```

## Windows Release

The main Windows release entry point is:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\release.ps1
```

`release.ps1` always starts by running `uv sync --group release`, then builds with `.venv\Scripts\python.exe` from the synced uv environment.

Common options:

- `-ProjectName <name>`: choose the published folder and executable name. Defaults to `web-post`.
- `-NoFrontendBuild`: reuse the existing `frontend/dist`.
- `-OneDir`: build PyInstaller onedir output. This is the default.
- `-OneFile`: build a single-file executable.
- `-FileSystemRoot <path>`: write a default `WEB_POST_FILESYSTEM_ROOT` into the portable `web-post.env`.

Portable package shape:

```text
release/windows/web-post/
  web-post.exe
  start.bat
  web-post.env
  html/
  data/
  datasets/
```

Keep `web-post.exe`, `html`, `data`, and `datasets` together. In onedir mode, keep PyInstaller's `_internal` runtime folder as well.

## Built-In Demo Pipeline

`data/templates/Ungrouped/demo_image_pipeline` is included for first-run testing. It calls the backend mock detection endpoint and returns one demo box. Use it to verify image browsing, base64 injection, raw response display, parsing, visualization, and cache output before connecting a real algorithm service.

## Troubleshooting

- If Raw and Parsed are empty, first confirm the selected image row has status `success`.
- If a container page still shows older UI, rebuild and restart the frontend container.
- If a portable package shows stale UI, hard refresh the browser with `Ctrl+F5` and confirm the browser is opened from the current backend URL.
- If a copied template does not appear, check the folder shape under `data/templates` and restart the backend.

