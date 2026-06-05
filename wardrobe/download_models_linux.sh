#!/bin/bash
# Linux 下载 AI 模型 (用 hf-mirror)
# 用法: bash download_models_linux.sh

set -e
MODELS_DIR=${WARDROBE_MODELS_DIR:-/opt/llm_models}
VENV=${WARDROBE_VENV:-/opt/wardrobe_env}

mkdir -p "$MODELS_DIR"
echo "==> 模型目录: $MODELS_DIR"
echo "==> HF 镜像: https://hf-mirror.com"

# 检查 hf CLI
if ! command -v "$VENV/bin/hf" &> /dev/null; then
    echo "==> 装 huggingface_hub ..."
    "$VENV/bin/pip" install -U huggingface_hub
fi

# 1) LLM: Qwen2.5-0.5B-Instruct (Linux 上不能跑 MLX 版)
LLM_DIR="$MODELS_DIR/Qwen2.5-0.5B"
if [[ -f "$LLM_DIR/model.safetensors" ]]; then
    echo "==> LLM 已存在, 跳过 ($LLM_DIR)"
else
    echo "==> 下载 Qwen2.5-0.5B-Instruct (~1GB) ..."
    cd "$MODELS_DIR"
    HF_ENDPOINT=https://hf-mirror.com \
    "$VENV/bin/hf" download Qwen/Qwen2.5-0.5B-Instruct --local-dir "$(basename $LLM_DIR)"
fi

# 2) 视觉: Marqo-FashionCLIP (云端可选, 看内存)
#     1.6GB RAM 装不下, 跳过；如已挂 Tailscale 接入家里 Mac mini, 此项忽略
FCLIP_DIR="$MODELS_DIR/marqo-fashionCLIP"
if [[ -d "$FCLIP_DIR" ]] && [[ -f "$FCLIP_DIR/config.json" ]]; then
    echo "==> FashionCLIP 已存在 ($FCLIP_DIR)"
else
    echo "!! 跳过 Marqo-FashionCLIP 下载 (1.6GB 内存不足)"
    echo "   推荐方案: 家里 Mac mini 跑视觉, 通过 Tailscale 接入"
    echo "   如要在云上跑视觉, 需 ≥4GB RAM"
fi

echo ""
echo "==> 已下载模型:"
du -sh "$MODELS_DIR"/*/ 2>/dev/null
