# Fuxing 2 中文说明

Fuxing 2 是一个用于图片算法接口调试和数据集辅助处理的工具。它包含一个 FastAPI 后端和一个 Vue 3 前端，可以浏览图片、配置 HTTP 算法 pipeline、发送图片测试、解析接口返回、可视化检测框，并集成 dsetkit 做标注转换和可视化。

## 主要功能

- 浏览后端机器上指定范围内的图片文件。
- 从前端所在机器选择文件或文件夹，并上传到后端机器的 `datasets` 目录。
- 按 Collection 分组管理 pipeline，支持新增、复制、移动和删除。
- 配置请求 Header、Body、响应样例、字段映射和后处理参数。
- 批量发送图片，查看原始响应、解析结果和检测框预览。
- 保存预测可视化结果，并支持 GT 标注预览。
- 调用 dsetkit 进行数据集转换和绘图。
- 自带一个默认测试 pipeline，便于第一次启动后快速验证系统是否正常。

## 项目结构

```text
fuxing_2/
  backend/                 后端代码、pipeline 核心逻辑、启动器和工具脚本
  frontend/                前端源码和构建产物
  data/                    pipeline 配置、分组、日志和运行结果
  datasets/                开发环境默认数据集目录；发布包也会创建同名目录
  scripts/                 发布和维护脚本
  release/                 生成的发布包
  dsetkit-0.3.1-py3-none-any.whl
  docker-compose.yml
```

Windows 便携版发布后的目录结构：

```text
fuxing/
  fuxing.exe
  start.bat
  fuxing.env
  html/
  data/
  datasets/
```

不要单独移动 `fuxing.exe`。请保持 `fuxing.exe`、`html`、`data`、`datasets` 在同一个 `fuxing` 文件夹里。

## 发布包里的几个目录

- `html/`：前端页面文件，不需要手动修改。
- `data/`：保存 pipeline、分组、日志和运行结果。
- `datasets/`：上传按钮的固定目标目录，也就是后端机器接收数据的位置。

文件浏览和上传的范围是故意分开的：

- 文件浏览弹窗显示的是后端机器上可见的目录，根目录由 `FUXING_FILESYSTEM_ROOT` 控制。
- Windows 便携版默认显示 `fuxing.exe` 所在磁盘，例如程序在 `D:\tools\fuxing`，默认根目录就是 `D:\`。
- Linux/macOS 默认显示 `/`。
- 上传按钮选择文件时，浏览器会让你从前端电脑上任意位置选择文件。
- 上传目标固定是后端机器的 `FUXING_DATASETS_ROOT`，便携版默认是 `fuxing/datasets`。

这样设计是为了支持“前端在 A 机器打开，后端在 B 机器运行”的情况：A 机器选择文件，文件会上传到 B 机器的 `datasets` 目录。

## Windows 便携版使用方法

1. 打开 `fuxing` 文件夹。
2. 双击 `fuxing.exe` 或 `start.bat`。
3. 等几秒钟，浏览器通常会自动打开。
4. 如果浏览器没有自动打开，手动访问：`http://127.0.0.1:8000`。

如果 8000 端口被占用，可以用命令行指定其他端口。

打开 CMD 的方法：

1. 打开 `fuxing` 文件夹。
2. 点击资源管理器顶部地址栏。
3. 输入 `cmd`。
4. 按回车。
5. 输入下面的命令：

```bat
fuxing.exe --port 8001
```

打开 PowerShell 的方法：

1. 打开 `fuxing` 文件夹。
2. 按住 `Shift`，在文件夹空白处右键。
3. 点击“在终端中打开”或“在此处打开 PowerShell”。
4. 输入下面的命令：

```powershell
.\fuxing.exe --port 8001
```

然后访问：`http://127.0.0.1:8001`。

## 配置文件浏览根目录

发布脚本支持在构建时指定文件浏览弹窗的根目录：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\windows\build_portable.ps1 -FileSystemRoot D:\works\datasets
```

也可以发布后编辑 `fuxing.env`，加入一行：

```text
FUXING_FILESYSTEM_ROOT=D:\works\datasets
```

或者启动时临时指定：

```powershell
.\fuxing.exe --filesystem-root D:\works\datasets
```

## Windows 发布命令

在项目根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\windows\build_portable.ps1
```

常用参数：

- `-Python <路径>`：指定用于打包的 Python。
- `-NoFrontendBuild`：复用已有的 `frontend/dist`，不重新构建前端。
- `-SkipInstall`：跳过 Python 依赖安装。
- `-OneDir`：生成 PyInstaller onedir 目录，而不是默认单文件 exe。
- `-FileSystemRoot <路径>`：设置文件浏览弹窗的根目录。

## macOS 发布命令

macOS 包必须在 macOS 上构建：

```bash
scripts/macos/build_portable.sh
```

指定文件浏览根目录：

```bash
scripts/macos/build_portable.sh --filesystem-root /Users/you/datasets
```

## Docker 开发方式

```powershell
docker compose up -d --build
```

默认地址：

- 前端：`http://localhost:5173`
- 后端：`http://localhost:8000`

## 本地开发方式

后端：

```bash
python -m pip install -r backend/requirements.txt
python -m pip install dsetkit-0.3.1-py3-none-any.whl
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

前端：

```bash
cd frontend
npm install
npm run dev
```

构建前端：

```bash
cd frontend
npm run build
```

## 默认测试 Pipeline

默认会带一个 Collection 位于 `Ungrouped` 的 `Demo Image Pipeline`。它调用后端内置的 mock 检测接口：

```text
/api/mock/detection
```

这个 pipeline 可以接收图片，返回一个模拟检测框。第一次启动后，可以先选择一张图片运行它，用来确认文件浏览、请求构造、响应解析和可视化是否都正常。
