#!/bin/bash
# 启动 Flask (开发模式)
# 生产用 install_service.sh 走 systemd
set -e
cd "$(dirname "$0")"
VENV=${WARDROBE_VENV:-/opt/wardrobe_env}
source "$VENV/bin/activate" 2>/dev/null || { echo "请先运行 setup_linux.sh"; exit 1; }

export HOST=${HOST:-0.0.0.0}
export PORT=${PORT:-5050}
export DEBUG=${DEBUG:-0}
exec python app.py
