# Fuxing 2

Fuxing 2 is a FastAPI + Vue 3 workspace for browsing datasets, configuring HTTP detection pipelines, testing responses, and running dsetkit-powered annotation tools.

## Project Layout

```text
fuxing_2/
  backend/                 FastAPI backend, pipeline registry, and CLI tools
    app/
    pipeline_core/
    tools/
    main.py
    requirements.txt
    Dockerfile
  frontend/                Vue 3 frontend and Nginx image
    src/
    dist/
    Dockerfile
    nginx.conf
  scripts/                 Local maintenance scripts
  data/                    Runtime data mounted into the backend container
  dsetkit-0.3.1-py3-none-any.whl
  docker-compose.yml
  .env.example
```

## Docker Compose

The compose stack starts two services:

- `webui-backend`: FastAPI backend on `8000`
- `webui-frontend`: Vue static site through Nginx on `5173`

The backend image installs `backend/requirements.txt` and the local `dsetkit-0.3.1-py3-none-any.whl`. The wheel brings its own Python dependencies, including `natsort`; `natsort` is also listed in backend requirements for clarity.

Start the stack from the project root:

```powershell
docker compose up -d --build
```

Visit:

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000

Useful environment variables are shown in `.env.example`:

```powershell
Copy-Item .env.example .env
```

By default, compose mounts:

- `./data` to `/data/fuxing`
- `D:/works/projects/00_datasets/` to `/data/datasets/`
- the project root to `/workspace/project` for live backend code during development

## Backend Development

Run locally from the project root:

```bash
python -m pip install -r backend/requirements.txt
python -m pip install dsetkit-0.3.1-py3-none-any.whl
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

The backend reads runtime data from `FUXING_DATA_ROOT`; if unset, it defaults to `data/` under the project root.

## Frontend Development

```bash
cd frontend
npm install
npm run dev
```

For a production frontend build:

```bash
cd frontend
npm install
npm run build
```

The dedicated frontend container serves the built app through Nginx. The backend can also serve `frontend/dist` when that directory exists in the mounted project root.

## Pipeline Registry

Pipelines are stored under the runtime data directory, usually `data/`. A pipeline definition includes fields such as:

- `name`
- `display_name`
- `url`
- `method`
- `header_json`
- `body_json`
- `default_inputs`
- `response_parser`

Response parser rules support detection, OCR, and count outputs. The backend API can create and update these definitions through the pipeline endpoints.

## Tools

Optional command-line tools live under `backend/tools` and can be run as modules, for example:

```bash
python -m backend.tools.main
```

These tools share the same `FUXING_DATA_ROOT` convention as the web backend.
