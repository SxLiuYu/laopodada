#!/bin/bash
# 前台启动视觉服务
set -e
cd "$(dirname "$0")"
VENV="$HOME/wardrobe_services/venv"
MODEL=${FASHION_MODEL:-Marqo/marqo-fashionCLIP}
CLIP_DIR="$HOME/Models/marqo-fashionCLIP"
PORT=${VISUAL_PORT:-8002}
HOST=${VISUAL_HOST:-0.0.0.0}

[[ -d "$VENV" ]] || { echo "venv 不存在, 先跑 setup_services.sh"; exit 1; }
[[ -d "$CLIP_DIR" ]] || { echo "模型不存在: $CLIP_DIR, 先跑 download_models.sh"; exit 1; }

exec "$VENV/bin/python" visual_service.py \
    --model "$CLIP_DIR" \
    --host "$HOST" \
    --port "$PORT"
