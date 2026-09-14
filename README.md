# Web File Browser / Web 文件浏览器

A lightweight, self-hosted web-based file manager with a modern Windows-Explorer-style interface.
Passwords protect every API call, so it is safe to expose on a trusted LAN.

一个轻量级、自托管的网页文件管理器，拥有类似 Windows 资源管理器的现代界面。
所有 API 调用均受密码保护，适合在可信局域网内部署。

> **Note / 说明**: This project is intended for personal use on a trusted network. It runs Flask's
> development server by default — put it behind a reverse proxy (Nginx/Caddy) with HTTPS for
> anything more serious.
>
> 本项目定位为可信网络下的个人工具，默认使用 Flask 开发服务器。如需更正式地使用，
> 请置于 Nginx/Caddy 等反向代理之后并启用 HTTPS。

---

## Features / 功能特性

| Feature | 功能 |
| --- | --- |
| Grid & list views, toggle anytime | 网格 / 列表视图，随时切换 |
| Breadcrumb navigation + sidebar shortcuts | 面包屑导航 + 侧边栏快捷入口 |
| Single-click select, double-click open / download | 单击选中，双击打开 / 下载 |
| Right-click context menu | 右键上下文菜单 |
| Drag & drop upload (anywhere on the page) | 拖拽上传（页面任意位置） |
| Multi-file upload via file picker | 文件选择器批量上传 |
| Copy / Cut / Paste (real copy vs. move) | 复制 / 剪切 / 粘贴（真正区分复制与移动） |
| Create folder, rename, delete (recursive) | 新建文件夹、重命名、删除（递归） |
| Recursive search by keyword | 按关键字递归搜索 |
| Streaming download (handles large files) | 流式下载（支持大文件） |
| Duplicate-name protection (`name_(timestamp).ext`) | 重名保护（`name_(时间戳).ext`） |
| Password authentication on every endpoint | 所有接口密码鉴权 |
| Path-traversal protection | 路径越界防护 |
| File type icons (documents, images, video, audio, archives, code) | 文件类型图标（文档、图片、视频、音频、压缩包、代码） |
| Keyboard shortcuts (F5 refresh, Ctrl+F search, Esc close) | 键盘快捷键（F5 刷新、Ctrl+F 搜索、Esc 关闭） |

---

## Screenshots / 界面截图

> Add your own screenshots here after the first run.
>
> 首次运行后可将截图放在此处。

```
┌────────────────────────────────────────────────────────┐
│  💻 根目录 › data › myfolder          [search]         │
├──────────┬─────────────────────────────────────────────┤
│ Sidebar  │  📁 folder   📄 doc.pdf   🎬 video.mp4      │
│ 根目录    │  🖼️ img.png   📦 arch.zip  🐍 script.py     │
│ folder1  │                                             │
│ folder2  │                                             │
├──────────┴─────────────────────────────────────────────┤
│  当前路径: /data/myfolder | 文件数: 12                  │
└────────────────────────────────────────────────────────┘
```

---

## Requirements / 环境要求

- Python 3.8+ (tested on 3.13)
- `flask`, `flask-cors`
- Linux / macOS (Windows works, but the bundled `run_web.sh` targets POSIX shells)

---

## Installation / 安装

```bash
git clone https://github.com/EdmonJiang/web-file-browser.git
cd web-file-browser
pip install flask flask-cors
```

Or use a virtual environment / 或使用虚拟环境:

```bash
python3 -m venv venv
source venv/bin/activate
pip install flask flask-cors
```

---

## Configuration / 配置

All configuration is via environment variables — no secrets in the source code.
所有配置均通过环境变量完成，源码中不含任何密钥。

| Variable / 变量 | Default / 默认值 | Description / 说明 |
| --- | --- | --- |
| `WEB_FILE_BROWSER_ROOT` | `$HOME` | Directory to expose / 允许浏览的根目录 |
| `WEB_FILE_BROWSER_PASSWORD` | `mypassword` | Access password / 访问密码 |
| `WEB_FILE_BROWSER_PORT` | `3801` | Listening port / 监听端口 |
| `WEB_FILE_BROWSER_DEBUG` | `0` | Set to `1` to enable the debugger (**unsafe**) / 设为 `1` 开启调试器（**不安全**） |

> ⚠️ **Always change the default password before exposing the service.**
>
> ⚠️ **对外提供服务前请务必修改默认密码。**

---

## Usage / 使用方法

### Quick start / 快速开始

```bash
# Browse your home directory on port 3801
# 以默认配置浏览家目录，端口 3801
export WEB_FILE_BROWSER_PASSWORD='your-strong-password'
python3 app.py
```

Then open <http://localhost:3801> / 然后打开 <http://localhost:3801>。

### With the management script / 使用管理脚本

```bash
export WEB_FILE_BROWSER_ROOT=/data/myfolder
export WEB_FILE_BROWSER_PASSWORD='your-strong-password'

./run_web.sh start     # start   / 启动
./run_web.sh status    # status  / 查看状态
./run_web.sh restart   # restart / 重启
./run_web.sh stop      # stop    / 停止
```

The script is portable (resolves its own directory) and installs missing dependencies
automatically. Logs go to `/tmp/webfile_browser.log`.
脚本可任意放置（自动解析自身目录），并会自动安装缺失依赖。日志位于 `/tmp/webfile_browser.log`。

### Run as a systemd service (optional) / 注册为 systemd 服务（可选）

```ini
# /etc/systemd/system/web-file-browser.service
[Unit]
Description=Web File Browser
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/opt/web-file-browser
Environment=WEB_FILE_BROWSER_ROOT=/data/myfolder
Environment=WEB_FILE_BROWSER_PASSWORD=your-strong-password
Environment=WEB_FILE_BROWSER_PORT=3801
ExecStart=/usr/bin/python3 /opt/web-file-browser/app.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now web-file-browser
```

---

## Project structure / 项目结构

```
web-file-browser/
├── app.py              # Flask backend & REST API / Flask 后端与 REST API
├── run_web.sh          # Service management script / 服务管理脚本
├── static/
│   └── index.html      # Frontend (HTML + CSS + vanilla JS) / 前端单文件
├── .gitignore
├── README.md
└── LICENSE
```

---

## API reference / 接口说明

Every endpoint requires the password via **any** of:
`?password=...`, form field `password`, or the `X-Password` header.

所有接口均需通过以下任一方式提供密码：查询参数 `?password=...`、表单字段 `password`、或请求头 `X-Password`。

| Method | Endpoint | Description / 说明 |
| --- | --- | --- |
| `GET` | `/api/files?path=` | List a directory (or stat a file) / 列出目录内容 |
| `POST` | `/api/upload` | Multipart upload (`path`, `file`) / 多部件上传 |
| `POST` | `/api/upload_base64` | JSON upload (`path`, `name`, `content`) / Base64 上传 |
| `GET` | `/api/download?path=` | Stream a file download / 流式下载文件 |
| `GET` | `/api/download_base64?path=` | Base64-encoded file content / 返回 Base64 内容 |
| `POST` | `/api/mkdir` | Create folder (`path`, `name`) / 新建目录 |
| `POST` | `/api/rename` | Rename (`path`, `name`) / 重命名 |
| `POST` | `/api/delete` | Delete file or folder recursively (`path`) / 删除 |
| `POST` | `/api/copy` | Copy (`source`, `destination`) / 复制 |
| `POST` | `/api/move` | Move (`source`, `destination`) / 移动 |
| `GET` | `/api/search?path=&keyword=&depth=` | Recursive search / 递归搜索 |
| `POST` | `/api/clipboard` | Store clipboard state / 记录剪贴板状态 |
| `GET` | `/api/info?path=` | File metadata / 文件元信息 |
| `POST` | `/api/permissions` | Change mode (`path`, `mode`) / 修改权限 |
| `GET` | `/api/usage` | Disk usage / 磁盘用量 |

### Example / 示例

```bash
# List a directory / 列出目录
curl "http://localhost:3801/api/files?password=YOUR_PASSWORD&path=/data/myfolder"

# Upload a file / 上传文件
curl -X POST "http://localhost:3801/api/upload" \
  -H "X-Password: YOUR_PASSWORD" \
  -F "path=/data/myfolder" \
  -F "file=@./report.pdf"

# Download a file / 下载文件
curl -OJ "http://localhost:3801/api/download?password=YOUR_PASSWORD&path=/data/myfolder/report.pdf"
```

---

## Security notes / 安全说明

Implemented protections / 已实现的防护:

- **Authentication** — password checked on every endpoint / 每个接口都校验密码
- **Path confinement** — all paths are resolved with `os.path.realpath` and validated via
  `os.path.commonpath`, which correctly rejects prefix-adjacent directories such as `/root_evil`
  and symlink escapes.
  / 所有路径均使用 `os.path.realpath` 解析，并通过 `os.path.commonpath` 校验，
  可正确拦截 `/root_evil` 这类前缀相邻目录与符号链接逃逸
- **Debugger disabled by default** — the Werkzeug debugger (remote code execution risk) is opt-in
  / 默认关闭调试器（存在远程代码执行风险），需显式开启
- **No hardcoded secrets** — password and root come from environment variables
  / 不硬编码密钥，密码与根目录均来自环境变量

Recommendations / 建议:

- Use a strong, unique password / 使用强且唯一的密码
- Serve over HTTPS via a reverse proxy / 通过反向代理启用 HTTPS
- Restrict access with a firewall or VPN on untrusted networks / 在不可信网络中通过防火墙或 VPN 限制访问
- The built-in server is for development — use `gunicorn`/`uwsgi` for production
  / 内置服务器仅供开发，生产环境请使用 `gunicorn`/`uwsgi`

---

## Troubleshooting / 常见问题

| Symptom / 现象 | Cause & fix / 原因与解决 |
| --- | --- |
| Login dialog not shown / 看不到登录框 | Clear site data, then reload / 清除站点数据后重新加载 |
| `密码错误` on every request / 每次请求都提示密码错误 | Cached password is stale — clear site data / 缓存的密码已失效，请清除站点数据 |
| `路径越界` / path out of range | Requested path is outside `WEB_FILE_BROWSER_ROOT` / 请求路径超出了配置的根目录 |
| Upload silently fails / 上传无反应 | Fixed in current version (uses `FormData`); hard-refresh with Ctrl+F5 / 已修复（改用 `FormData`），请用 Ctrl+F5 强制刷新 |
| Port already in use / 端口被占用 | Change `WEB_FILE_BROWSER_PORT` or stop the other process / 修改端口或停止占用进程 |

---

## License / 许可证

MIT License — see [LICENSE](LICENSE).

MIT 许可证 — 详见 [LICENSE](LICENSE)。

---

## Author / 作者

**EdmonJiang** — <https://github.com/EdmonJiang>

Contributions, issues and feature requests are welcome.
欢迎提交贡献、问题与功能建议。
