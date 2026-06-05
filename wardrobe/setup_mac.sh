#!/bin/bash
# 一键安装 Mac mini 上的 Python 依赖
# 用法: bash setup_mac.sh

set -e
cd "$(dirname "$0")"

echo "==> 检查系统..."
if [[ "$(uname)" != "Darwin" ]]; then
    echo "错误: 此脚本只能在 macOS 上运行"
    exit 1
fi

PYTHON=${PYTHON:-python3}
if ! command -v "$PYTHON" &> /dev/null; then
    echo "未找到 python3，请先安装 Xcode Command Line Tools: xcode-select --install"
    exit 1
fi

PY_VER=$($PYTHON -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "==> Python 版本: $PY_VER (需要 3.10+)"

echo "==> 创建虚拟环境 .venv ..."
$PYTHON -m venv .venv
source .venv/bin/activate

echo "==> 升级 pip ..."
pip install --upgrade pip wheel setuptools

echo "==> 安装核心依赖 ..."
pip install -r requirements.txt

# Mac Apple Silicon 专属
if [[ "$(uname -m)" == "arm64" ]]; then
    echo "==> 检测到 Apple Silicon, 安装 mlx-lm ..."
    pip install mlx-lm
else
    echo "!! 非 Apple Silicon, 跳过 mlx-lm (LLM 推理将不可用)"
fi

echo ""
echo "==> 验证安装:"
$PYTHON -c "import flask, requests, numpy, PIL; print('Flask / requests / numpy / Pillow OK')"
$PYTHON -c "import transformers, torch; print('transformers / torch:', torch.__version__, 'mps:', torch.backends.mps.is_available())" 2>/dev/null || echo "(transformers 加载失败，跳过)"

echo ""
echo "==> 下一步: bash download_models.sh 下载 AI 模型 (~3GB)"
