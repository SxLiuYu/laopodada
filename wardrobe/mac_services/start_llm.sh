#!/bin/bash
# 前台启动 LLM 服务 (Ctrl+C 退出)
set -e
cd "$(dirname "$0")"
VENV="$HOME/wardrobe_services/venv"
LLM_DIR=${LLM_MODEL_DIR:-$HOME/Models/Qwen3-4B-Thinking-2507-MLX-4bit}
PORT=${LLM_PORT:-8001}
HOST=${LLM_HOST:-0.0.0.0}

[[ -d "$VENV" ]] || { echo "venv 不存在, 先跑 setup_services.sh"; exit 1; }
[[ -d "$LLM_DIR" ]] || { echo "模型不存在: $LLM_DIR, 先跑 download_models.sh"; exit 1; }

exec "$VENV/bin/python" llm_service.py \
    --model "$LLM_DIR" \
    --host "$HOST" \
    --port "$PORT"
