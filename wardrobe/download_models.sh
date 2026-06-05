#!/bin/bash
# 下载 AI 模型到 ~/wardrobe_models/
# 用法: bash download_models.sh
# 自定义路径: MODELS_DIR=/path/to/models bash download_models.sh

set -e

MODELS_DIR=${MODELS_DIR:-$HOME/wardrobe_models}
mkdir -p "$MODELS_DIR"
echo "==> 模型目录: $MODELS_DIR"

# 检查 huggingface-cli
if ! command -v huggingface-cli &> /dev/null; then
    echo "==> 安装 huggingface_hub ..."
    pip install -U "huggingface_hub[cli]"
fi

# 1) Marqo FashionCLIP (~600MB)
FCLIP_DIR="$MODELS_DIR/marqo-fashionCLIP"
if [[ -d "$FCLIP_DIR" ]] && [[ -f "$FCLIP_DIR/config.json" ]]; then
    echo "==> FashionCLIP 已存在, 跳过"
else
    echo "==> 下载 Marqo/marqo-fashionCLIP ..."
    huggingface-cli download Marqo/marqo-fashionCLIP --local-dir "$FCLIP_DIR"
fi

# 2) Qwen3-4B-Thinking MLX 4-bit (~2.3GB, 仅 Mac)
LLM_DIR="$MODELS_DIR/Qwen3-4B-Thinking-MLX-4bit"
if [[ "$(uname -m)" == "arm64" ]]; then
    if [[ -d "$LLM_DIR" ]] && [[ -f "$LLM_DIR/config.json" ]]; then
        echo "==> LLM 已存在, 跳过"
    else
        echo "==> 下载 lmstudio-community/Qwen3-4B-Thinking-2507-MLX-4bit ..."
        huggingface-cli download lmstudio-community/Qwen3-4B-Thinking-2507-MLX-4bit --local-dir "$LLM_DIR"
    fi
else
    echo "!! 非 Apple Silicon，跳过 LLM 下载 (Qwen3-4B-Thinking MLX 版仅支持 Apple Silicon)"
    echo "   Mac mini M1/M2/M3/M4 用户请直接运行本脚本"
fi

echo ""
echo "==> 下载完成!"
echo "模型位置:"
echo "  - FashionCLIP: $FCLIP_DIR"
echo "  - LLM:         $LLM_DIR"
echo ""
echo "==> 启动应用: bash start.sh"
