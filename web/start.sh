#!/bin/bash
# gitxPost Web — 一键启动前后端
# 用法: bash web/start.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "========================================="
echo "  gitxPost Web UI"
echo "========================================="
echo ""

# 1. 检查 Python 虚拟环境
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"
if [ ! -f "$VENV_PYTHON" ]; then
    echo "[!] 未找到 .venv，使用系统 python3"
    VENV_PYTHON="python3"
fi

# 2. 安装后端依赖
echo "[1/3] 安装后端依赖..."
$VENV_PYTHON -m pip install -q fastapi uvicorn pydantic 2>/dev/null || true

# 3. 安装前端依赖（如果 node_modules 不存在）
if [ ! -d "$SCRIPT_DIR/ui/node_modules" ]; then
    echo "[2/3] 安装前端依赖..."
    cd "$SCRIPT_DIR/ui" && npm install --silent
else
    echo "[2/3] 前端依赖已就绪"
fi

# 4. 启动后端 (port 8900)
echo "[3/3] 启动服务..."
echo ""
echo "  后端 API:  http://127.0.0.1:8900"
echo "  前端 UI:   http://127.0.0.1:5900"
echo ""
echo "  按 Ctrl+C 停止所有服务"
echo "========================================="
echo ""

# 后台启动后端
cd "$PROJECT_ROOT"
$VENV_PYTHON -m uvicorn web.api.server:app --host 127.0.0.1 --port 8900 --reload &
BACKEND_PID=$!

# 前台启动前端
cd "$SCRIPT_DIR/ui"
npx vite --port 5900 --host 127.0.0.1 &
FRONTEND_PID=$!

cleanup() {
    echo ""
    echo "正在停止服务..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    wait $BACKEND_PID 2>/dev/null
    wait $FRONTEND_PID 2>/dev/null
    echo "已停止"
}

trap cleanup EXIT INT TERM

wait
