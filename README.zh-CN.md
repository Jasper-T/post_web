# web-post 中文说明

web-post 是一个用于图片算法接口调试、批量测试、结果查看、标注预览、标注转换和结果评估的工具。项目由 FastAPI 后端和 Vue 3 前端组成，集成 `dsetkit==0.4.1`，支持 Docker Compose、本地开发和 Windows 便携版发布。

## 主要功能

- 浏览后端机器上 `WEB_POST_FILESYSTEM_ROOT` 范围内的图片文件。
- 从浏览器所在机器上传文件或文件夹到后端 `datasets` 目录。
- 按 Collection 管理 Pipeline，支持新建、复制、移动、删除和分组。
- 配置 Header JSON、Body JSON、Response 样例、响应解析和请求配置。
- 单张或批量发送图片到算法接口。
- 查看 Raw JSON 和 Parsed JSON。
- 预览 Pred 或 GT 标注图片。
- 下载生成的 Pred 或 GT 标注图片到本地目录。
- 使用 dsetkit 转换 Pred 或 GT 标注格式，支持 LabelMe、VOC、YOLO。
- 使用 `dsetkit.dataset` 查看 GT 数据集统计，并通过 `dsetkit.evaluator` 输出评估指标。

## 项目结构

```text
web-post/
  backend/                         FastAPI 后端、Pipeline 核心逻辑、启动器和工具脚本
  backend/wheels/                  本地 wheel 依赖，包含 dsetkit 0.4.1
  frontend/                        Vue 3 前端源码
  frontend/src/styles/             全局样式变量、通用组件样式和布局样式
  data/templates/<group>/<pipeline>/ Pipeline 定义和 JSON 资产
  data/.cache/<pipeline>/<bucket>/ 运行结果、预览图和转换结果缓存
  scripts/windows/                 分阶段 Windows 发布脚本
  scripts/macos/                   macOS 打包脚本；目前不在主发布路径中
  release/                         生成的发布包
  docker-compose.yml
  pyproject.toml
  uv.lock
```

Pipeline 分组直接来自 `data/templates` 下的文件夹。`Ungrouped` 和 `Deleted` 是特殊必要分组，不存在时会自动创建。每个 Pipeline 的文件夹名就是 `pipeline_name`，页面显示用的 `displayName` 保存在 `pipeline.json` 中，两者都必须全局唯一。

## 模板隐私和复用

开源仓库和便携版发布包默认只包含 `data/templates/Ungrouped/demo_image_pipeline`。真实 Pipeline 模板通常会包含私有服务地址、请求头、请求体、响应样例、类别名称或客户相关解析规则，因此应当视为本地私有运行数据。

复用其他用户或其他机器上的模板时：

1. 把模板文件夹复制到 `data/templates/<分组>/<pipeline_name>/`。便携版则复制到 `release/windows/web-post/data/templates/<分组>/<pipeline_name>/`。
2. 保持模板 JSON 文件在同一个文件夹内，通常包括 `pipeline.json`、`header.json`、`body.json`、`response.json`、`mapping.json` 和 `post_config.json`。
3. 确认 `pipeline_name` 和 `displayName` 全局唯一。如有冲突，请先修改文件夹名和 `pipeline.json` 中对应字段。
4. 分享模板前检查并清理私有 URL、token、cookie、内部请求头、样例请求体和响应数据。
5. 复制后刷新页面；如果没有出现，重启后端让系统重新读取 `data/templates`。

私有模板目录默认会被 git 忽略，只有 demo pipeline 应该进入版本管理。

## 运行数据目录

默认运行数据在 `data/` 下：

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

缓存 bucket 由 Image Path 推导。比如输入 `/root/1/2/3` 或 `/root/1/2/3/file.jpg`，bucket 都是 `2_3`。

## 配置项

本地开发时，`backend.main:app` 直接读取环境变量。`backend/launcher.py` 中的便携版启动器还会读取应用目录下的 `web-post.env`，并支持 `--host`、`--port`、`--filesystem-root`、`--no-browser`、`--reload` 等命令行参数。

```text
WEB_POST_FILESYSTEM_ROOT   文件浏览器显示的后端根目录
WEB_POST_DATA_ROOT         运行数据目录，默认 data
WEB_POST_DATASETS_ROOT     上传文件在后端机器上的目标目录
WEB_POST_FRONTEND_DIST     后端启动器托管的前端构建目录
WEB_POST_BASE_URL          Demo/mock Pipeline 使用的后端基础地址
LOG_LEVEL                  后端日志级别，默认 INFO
LOG_DIR                    日志目录，默认 WEB_POST_DATA_ROOT/logs
LOG_ROTATION               Loguru 日志轮转配置，默认 10 MB
LOG_RETENTION              Loguru 日志保留配置，默认 14 days
```

文件浏览和上传范围是分开的：

- `Browse` 看到的是后端机器上的目录，根目录由 `WEB_POST_FILESYSTEM_ROOT` 控制。
- 上传文件时，浏览器从前端用户的机器选择文件。
- 上传目标固定写入后端机器的 `WEB_POST_DATASETS_ROOT`。

## Python 依赖管理

Python 依赖由 uv 管理，项目要求 Python `>=3.12,<3.14`。

```powershell
uv sync
```

发布打包依赖，例如 PyInstaller，放在 `release` dependency group 中：

```powershell
uv sync --group release
```

`dsetkit==0.4.1` 来自本地 wheel：

```text
backend/wheels/dsetkit-0.4.1-py3-none-any.whl
```

## Docker 使用方式

启动或重新构建：

```powershell
docker compose up -d --build
```

Compose 使用 `.env` / `.env.example` 配置宿主侧变量，例如 `WEB_POST_DATA_DIR`、`LOG_LEVEL`、`LOG_ROTATION` 和 `LOG_RETENTION`。后端应用变量也可以写在 `docker-compose.yml` 或本地 `docker-compose.override.yml` 中。

默认地址：

- 前端：`http://localhost:5173`
- 后端：`http://localhost:8000`

常用检查：

```powershell
docker ps
docker exec webui-backend python -c "import backend.main, dsetkit, cv2, natsort; print('ok')"
```

## 本地开发方式

后端：

```powershell
uv sync
$env:WEB_POST_DATA_ROOT = ".\data"
$env:WEB_POST_FILESYSTEM_ROOT = "D:\"
$env:WEB_POST_DATASETS_ROOT = ".\datasets"
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

前端：

```powershell
cd frontend
npm install
npm run dev
```

构建前端：

```powershell
cd frontend
npm run build
```

如需用后端 launcher 测试已构建前端：

```powershell
.\.venv\Scripts\python.exe -m backend.launcher --no-browser --reload
```

## Windows 便携版发布

主发布入口是：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\release.ps1
```

`release.ps1` 每次都会先运行 `uv sync --group release`，然后使用同步后的 `.venv\Scripts\python.exe` 构建发布包。

常用参数：

- `-ProjectName <名称>`：指定发布后的文件夹和 exe 名称，默认 `web-post`。
- `-NoFrontendBuild`：复用已有 `frontend/dist`。
- `-OneDir`：PyInstaller onedir 模式，默认模式。
- `-OneFile`：生成单文件 exe。
- `-FileSystemRoot <路径>`：写入发布包中的默认文件浏览根目录。

发布包结构：

```text
release/windows/web-post/
  web-post.exe
  start.bat
  web-post.env
  html/
  data/
  datasets/
```

不要单独移动 `web-post.exe`。请保持 `web-post.exe`、`html`、`data`、`datasets` 在同一个 `web-post` 文件夹里。onedir 模式下也不要删除 `_internal/`。

## 默认测试 Pipeline

`data/templates/Ungrouped/demo_image_pipeline` 用于首次运行测试。它调用后端内置 mock 检测接口，返回一个模拟检测框。第一次启动后建议先用它验证图片浏览、base64 注入、Raw/Parsed、Pred 预览和缓存输出，再连接真实算法服务。

## 常见问题

- Raw/Parsed 为空：先确认右侧图片状态是 `success`，再检查 Parsing 路径。
- 图片预览没有框：检查 Parsed 是否有 bbox，坐标格式是否正确。
- 找不到本机文件：`Browse` 是后端文件系统，不是浏览器电脑文件系统，需要先上传到后端 datasets 目录，或调整 `WEB_POST_FILESYSTEM_ROOT`。
- 页面还是旧版本：容器模式下重建并重启前端容器；便携版按 `Ctrl+F5` 强制刷新。
- 复制的模板没有出现：检查目录结构是否为 `data/templates/<分组>/<pipeline_name>/`，必要时重启后端。
