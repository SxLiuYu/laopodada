#!/bin/bash
# Linux 一键安装脚本 (Ubuntu 24.04)
# 用法: bash setup_linux.sh

set -e
cd "$(dirname "$0")"

echo "==> 检查环境..."
[[ "$(uname)" == "Linux" ]] || { echo "错误: 非 Linux 系统"; exit 1; }
PYTHON=${PYTHON:-python3}
$PYTHON -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" \
    || { echo "需要 Python 3.10+"; exit 1; }

INSTALL_DIR="/opt/wardrobe"
VENV="/opt/wardrobe_env"
MODELS_DIR=${WARDROBE_MODELS_DIR:-/opt/llm_models}

echo "==> 创建目录..."
sudo mkdir -p "$INSTALL_DIR" "$MODELS_DIR" "$INSTALL_DIR/logs" 2>/dev/null || \
    mkdir -p "$INSTALL_DIR" "$MODELS_DIR" "$INSTALL_DIR/logs"
sudo chown -R $USER:$USER "$INSTALL_DIR" "$MODELS_DIR" 2>/dev/null || true

echo "==> 复制项目文件到 $INSTALL_DIR ..."
# 保留现有 wardrobe.json / embeddings / uploads
rsync -a --exclude='.venv' --exclude='__pycache__' --exclude='logs' \
    --exclude='data/wardrobe.json' --exclude='data/embeddings.npy' --exclude='data/emb_index.json' \
    --exclude='static/uploads/*' --exclude='.git' --exclude='*.log' \
    ./ "$INSTALL_DIR/"

cd "$INSTALL_DIR"

echo "==> 系统依赖..."
if command -v apt-get &>/dev/null; then
    sudo apt-get install -y python3-venv python3-dev build-essential nginx 2>&1 | tail -3
fi

echo "==> 创建 venv ..."
[[ -d "$VENV" ]] || $PYTHON -m venv "$VENV"

echo "==> 装 Python 依赖..."
"$VENV/bin/pip" install --upgrade pip wheel setuptools 2>&1 | tail -2

# 装 CPU 版 PyTorch (体积小)
"$VENV/bin/pip" install torch --index-url https://download.pytorch.org/whl/cpu 2>&1 | tail -3

# 其它
"$VENV/bin/pip" install -r requirements.txt 2>&1 | tail -3

# Linux 不需要 mlx（Mac 专用）

echo ""
echo "==> 验证安装..."
"$VENV/bin/python" -c "
import sys
print(f'Python: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')
import flask, requests, numpy, PIL
print('Flask / requests / numpy / Pillow OK')
import torch
print(f'torch: {torch.__version__} (CPU only)')
import transformers
print(f'transformers: {transformers.__version__}')
" 2>&1

echo ""
echo "==> 下一步:"
echo "  1) bash download_models_linux.sh   # 下载 AI 模型"
echo "  2) bash start_linux.sh            # 测试启动"
echo "  3) bash install_service.sh         # 注册 systemd"
