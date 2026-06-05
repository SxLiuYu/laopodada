#!/bin/bash
# 下载 Mac mini 需要的模型
# 1) Qwen3-4B-Thinking-2507-MLX-4bit (~2.3GB)
# 2) Marqo/marqo-fashionCLIP (~600MB)
# 用 huggingface-cli (新 CLI: hf)
set -e
cd "$(dirname "$0")"

MODELS_DIR=${MODELS_DIR:-$HOME/Models}
VENV="$HOME/wardrobe_services/venv"
HF=${HF:-$VENV/bin/hf}

mkdir -p "$MODELS_DIR"

echo "==> 准备 hf CLI"
[[ -x "$HF" ]] || { echo "venv 不存在, 先跑 setup_services.sh"; exit 1; }
$HF --version

# LLM
LLM_DIR="$MODELS_DIR/Qwen3-4B-Thinking-2507-MLX-4bit"
if [[ -d "$LLM_DIR" ]] && ls "$LLM_DIR"/*.safetensors 1>/dev/null 2>&1; then
    echo "==> LLM 已存在: $LLM_DIR"
else
    echo "==> 下载 LLM (Qwen3-4B-Thinking-2507-MLX-4bit)..."
    $HF download lmstudio-community/Qwen3-4B-Thinking-2507-MLX-4bit \
        --local-dir "$LLM_DIR"
fi

# 视觉模型
CLIP_DIR="$MODELS_DIR/marqo-fashionCLIP"
if [[ -d "$CLIP_DIR" ]] && [[ -f "$CLIP_DIR/config.json" ]]; then
    echo "==> FashionCLIP 已存在: $CLIP_DIR"
else
    echo "==> 下载 FashionCLIP (Marqo/marqo-fashionCLIP)..."
    $HF download Marqo/marqo-fashionCLIP --local-dir "$CLIP_DIR"
fi

echo ""
echo "==> 完成. 模型位置:"
du -sh "$LLM_DIR" "$CLIP_DIR" 2>/dev/null
