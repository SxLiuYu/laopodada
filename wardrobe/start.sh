#!/bin/bash
# 启动 Flask 服务（开发模式）
# 生产模式请用 com.wardrobe.app.plist 走 launchd
set -e
cd "$(dirname "$0")"
source .venv/bin/activate 2>/dev/null || { echo "请先运行 setup_mac.sh"; exit 1; }
export PORT=${PORT:-5050}
export HOST=${HOST:-0.0.0.0}
exec python app.py
