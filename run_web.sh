#!/bin/bash
# Web File Browser - service management script
# Web 文件浏览器 - 启动管理脚本
#
# Usage / 用法:
#   ./run_web.sh {start|stop|restart|status}
#
# Configuration is read from environment variables (with defaults):
# 配置通过环境变量读取（含默认值）:
#   WEB_FILE_BROWSER_ROOT      Root directory to browse (default: $HOME)
#   WEB_FILE_BROWSER_PASSWORD  Access password (default: mypassword)
#   WEB_FILE_BROWSER_PORT      Listen port (default: 3801)

set -u

# Resolve the directory this script lives in, so the project is portable.
# 解析脚本所在目录，使项目可任意放置。
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

LOG_FILE="${WEB_FILE_BROWSER_LOG:-/tmp/webfile_browser.log}"
PID_FILE="${WEB_FILE_BROWSER_PID:-/tmp/webfile_browser.pid}"
PORT="${WEB_FILE_BROWSER_PORT:-3801}"
export WEB_FILE_BROWSER_ROOT="${WEB_FILE_BROWSER_ROOT:-$HOME}"
export WEB_FILE_BROWSER_PASSWORD="${WEB_FILE_BROWSER_PASSWORD:-mypassword}"
export WEB_FILE_BROWSER_PORT="$PORT"

# Colors / 颜色输出
GREEN='\033[32m'
RED='\033[31m'
YELLOW='\033[33m'
NC='\033[0m'

get_pid() {
    local pid=""
    if [ -f "$PID_FILE" ]; then
        pid=$(cat "$PID_FILE" 2>/dev/null)
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            echo "$pid"
            return 0
        fi
    fi
    # Fall back to looking the process up by listening port
    # 通过端口查找进程
    if command -v ss >/dev/null 2>&1; then
        pid=$(ss -tlnp 2>/dev/null | grep ":$PORT " | grep -oP 'pid=\K\d+' | head -1)
    elif command -v lsof >/dev/null 2>&1; then
        pid=$(lsof -ti tcp:"$PORT" 2>/dev/null | head -1)
    fi
    if [ -n "$pid" ]; then
        echo "$pid"
        return 0
    fi
    echo ""
    return 1
}

check_python() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo -e "${RED}未找到 python3，请先安装 Python 3.8+ / python3 not found, please install Python 3.8+${NC}"
        return 1
    fi
    return 0
}

do_start() {
    check_python || return 1

    local pid
    pid=$(get_pid)
    if [ -n "$pid" ]; then
        echo -e "${YELLOW}Web 文件浏览器已在运行中 (PID: $pid) / already running${NC}"
        return 0
    fi

    echo "正在启动 Web 文件浏览器... / Starting Web File Browser..."
    cd "$APP_DIR" || return 1

    # Ensure dependencies are present
    # 安装依赖
    python3 -c "import flask, flask_cors" 2>/dev/null || {
        echo "正在安装依赖 / Installing dependencies..."
        python3 -m pip install -q flask flask-cors || {
            echo -e "${RED}依赖安装失败 / Failed to install dependencies${NC}"
            return 1
        }
    }

    # Launch the server
    # 启动服务
    nohup python3 -c "import app; app.app.run(host='0.0.0.0', port=$PORT, debug=False)" \
        > "$LOG_FILE" 2>&1 &
    local new_pid=$!
    echo "$new_pid" > "$PID_FILE"

    sleep 3

    if kill -0 "$new_pid" 2>/dev/null; then
        echo -e "${GREEN}Web 文件浏览器已启动 / started${NC}"
        echo "访问地址 / URL: http://localhost:$PORT"
        echo "根目录 / Root: $WEB_FILE_BROWSER_ROOT"
        echo "密码 / Password: $WEB_FILE_BROWSER_PASSWORD"
        return 0
    else
        echo -e "${RED}启动失败，请查看日志 / Failed to start, see log: $LOG_FILE${NC}"
        return 1
    fi
}

do_stop() {
    local pid
    pid=$(get_pid)
    if [ -n "$pid" ]; then
        echo "正在停止 Web 文件浏览器 (PID: $pid)... / Stopping..."
        kill "$pid" 2>/dev/null
        sleep 2
        if kill -0 "$pid" 2>/dev/null; then
            kill -9 "$pid" 2>/dev/null
        fi
        rm -f "$PID_FILE"
        echo -e "${GREEN}已停止 / stopped${NC}"
    else
        echo "Web 文件浏览器未在运行 / not running"
    fi
}

do_restart() {
    do_stop
    sleep 2
    do_start
}

do_status() {
    local pid
    pid=$(get_pid)
    if [ -n "$pid" ]; then
        echo -e "${GREEN}Web 文件浏览器正在运行 / running${NC}"
        echo "PID: $pid"
        echo "端口 / Port: $PORT"
        echo "根目录 / Root: $WEB_FILE_BROWSER_ROOT"
        echo "访问 / URL: http://localhost:$PORT"
        if [ -f "$LOG_FILE" ]; then
            echo ""
            echo "最近日志 / Recent log:"
            tail -5 "$LOG_FILE" 2>/dev/null
        fi
    else
        echo -e "${RED}Web 文件浏览器未在运行 / not running${NC}"
    fi
}

# Main entry / 主入口
case "${1:-}" in
    start)
        do_start
        ;;
    stop)
        do_stop
        ;;
    restart)
        do_restart
        ;;
    status)
        do_status
        ;;
    *)
        echo "用法 / Usage: $0 {start|stop|restart|status}"
        echo ""
        echo "  start   - 启动服务 / Start the service"
        echo "  stop    - 停止服务 / Stop the service"
        echo "  restart - 重启服务 / Restart the service"
        echo "  status  - 查看状态 / Show status"
        echo ""
        echo "环境变量 / Environment variables:"
        echo "  WEB_FILE_BROWSER_ROOT      根目录 / root directory (default: \$HOME)"
        echo "  WEB_FILE_BROWSER_PASSWORD  访问密码 / password (default: mypassword)"
        echo "  WEB_FILE_BROWSER_PORT      监听端口 / port (default: 3801)"
        ;;
esac
