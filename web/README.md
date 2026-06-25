# Workspace File Browser

一个独立的 FastAPI + Vue 3 WebUI，用于查看容器内文件系统，并维护右侧已选择路径列表。

## Docker Compose 启动

当前 compose 会启动两个服务：

- `webui-backend`：FastAPI 后端，监听 `8000`
- `webui-frontend`：Vue 前端静态站点，监听 `5173`

启动前请确认本机 Docker 中已有后端镜像 `dev:latest`，该镜像需要包含 Python、项目依赖以及 `uvicorn`。
compose 会额外挂载 `D:/works/projects/dsetkit/` 到容器内 `/workspace/projects/dsetkit/`，并通过 `PYTHONPATH` 让后端直接 import `dsetkit`。

```powershell
docker compose -f docker-compose.yml up -d --build
```

启动后访问：

- 前端页面：`http://localhost:5173`
- 后端接口：`http://localhost:8000`

compose 只会把 `web` 代码目录挂载到容器内 `/workspace/project/web`，业务数据单独挂载到 `/data/fuxing`。后端默认从容器文件系统根目录 `/` 开始浏览。
数据集目录会挂载到 `/workspace/projects/00_datasets/`，dsetkit 工具执行时建议使用容器内路径。

如果 Docker Hub 拉取镜像较慢，默认会使用 `docker.m.daocloud.io/library` 作为前端构建镜像源。也可以手动覆盖：

```powershell
$env:DOCKER_HUB_MIRROR="docker.io/library"
docker compose -f docker-compose.yml up -d --build
```

## 开发模式启动

后端：

```bash
cd /workspace/web
python -m pip install -r requirements.txt
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

如果在本机直接开发后端，请先安装或暴露 dsetkit：

```powershell
python -m pip install -e "D:\works\projects\dsetkit[visualize]"
```

dsetkit 工具位于第二步右侧功能区，当前接入了标注格式转换和标注可视化。可视化依赖 OpenCV，对应依赖已写入 `requirements.txt`。

## 后端日志

后端使用 Loguru 统一记录应用日志、Uvicorn/FastAPI 日志和 HTTP 请求日志。日志同时输出到控制台和 `web/logs/backend-YYYY-MM-DD.log`，请求响应会携带 `X-Request-ID`，便于串联排查。

可通过环境变量调整日志行为：

- `LOG_LEVEL`：日志级别，默认 `INFO`
- `LOG_DIR`：日志目录，默认 `$FUXING_DATA_ROOT/logs`
- `LOG_ROTATION`：单个日志文件轮转阈值，默认 `10 MB`
- `LOG_RETENTION`：日志保留时间，默认 `14 days`

前端：

```bash
cd /workspace/web/frontend
npm install
npm run dev
```

然后访问 Vite 输出的地址，通常是 `http://localhost:5173`。

## 可选命令行工具

原项目根目录中的 Python 工具已迁移到 `backend/tools`，例如：

```bash
python -m backend.tools.main
```

这些工具与 Web 后端统一使用 `FUXING_DATA_ROOT` 读取外部业务数据。

## 生产构建

```bash
cd /workspace/web/frontend
npm install
npm run build
```

构建完成后，FastAPI 会自动托管 `frontend/dist`：

```bash
cd /workspace/web
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

访问 `http://localhost:8000` 即可打开页面。
