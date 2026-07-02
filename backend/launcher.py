from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
import threading
import time
import webbrowser

import uvicorn


def _app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def _read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _ensure_runtime_dirs(base_dir: Path) -> tuple[Path, Path, Path]:
    data_dir = base_dir / "data"
    datasets_dir = base_dir / "datasets"
    html_dir = base_dir / "html"
    for path in (data_dir, datasets_dir, data_dir / "logs"):
        path.mkdir(parents=True, exist_ok=True)
    return data_dir, datasets_dir, html_dir


def _set_default_env(base_dir: Path, *, host: str, port: int, filesystem_root: str | None = None) -> None:
    data_dir, datasets_dir, html_dir = _ensure_runtime_dirs(base_dir)
    for key, value in _read_env_file(base_dir / "web-post.env").items():
        os.environ.setdefault(key, value)

    os.environ.setdefault("WEB_POST_DATA_ROOT", str(data_dir))
    os.environ.setdefault("WEB_POST_FILESYSTEM_ROOT", str(Path(base_dir.anchor or "/")))
    os.environ.setdefault("WEB_POST_DATASETS_ROOT", str(datasets_dir))
    os.environ.setdefault("WEB_POST_FRONTEND_DIST", str(html_dir))
    os.environ.setdefault("LOG_DIR", str(data_dir / "logs"))
    os.environ.setdefault("LOG_LEVEL", "INFO")
    os.environ["WEB_POST_BASE_URL"] = f"http://{host}:{port}"

    if filesystem_root:
        os.environ["WEB_POST_FILESYSTEM_ROOT"] = str(Path(filesystem_root).expanduser().resolve(strict=False))


def _open_browser_later(url: str, delay_seconds: float = 1.0) -> None:
    def open_browser() -> None:
        time.sleep(delay_seconds)
        webbrowser.open(url)

    thread = threading.Thread(target=open_browser, daemon=True)
    thread.start()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start the web-post local web application.")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind. Default: 127.0.0.1")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind. Default: 8000")
    parser.add_argument("--filesystem-root", default=None, help="Root directory shown in the file browser dialog.")
    parser.add_argument("--no-browser", action="store_true", help="Do not open the browser automatically.")
    parser.add_argument("--reload", action="store_true", help="Enable uvicorn reload for development only.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    base_dir = _app_dir()
    _set_default_env(base_dir, host=args.host, port=args.port, filesystem_root=args.filesystem_root)

    url = f"http://{args.host}:{args.port}"
    print(f"web-post is starting at {url}")
    print(f"File system root: {os.environ['WEB_POST_FILESYSTEM_ROOT']}")
    print(f"Data directory: {os.environ['WEB_POST_DATA_ROOT']}")
    print(f"Datasets directory: {os.environ['WEB_POST_DATASETS_ROOT']}")
    print(f"Frontend directory: {os.environ['WEB_POST_FRONTEND_DIST']}")

    if not args.no_browser:
        _open_browser_later(url)

    from backend.main import app

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=args.reload and not getattr(sys, "frozen", False),
        log_config=None,
    )


if __name__ == "__main__":
    main()
