#!/bin/bash
# Mac mini 端一键安装 (LLM + 视觉 微服务)
# 用法: bash setup_services.sh

set -e
cd "$(dirname "$0")"

echo "==> 检查环境..."
[[ "$(uname)" == "Darwin" ]] || { echo "错误: 非 macOS"; exit 1; }
PY=$(command -v python3)
[[ -x "$PY" ]] || { echo "需要 python3 (brew install python)"; exit 1; }
$PY -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" \
    || { echo "需要 Python 3.10+"; exit 1; }

INSTALL_DIR="$HOME/wardrobe_services"
VENV="$INSTALL_DIR/venv"
MODELS_DIR="$HOME/Models"

echo "==> 创建目录..."
mkdir -p "$INSTALL_DIR" "$MODELS_DIR" "$INSTALL_DIR/logs"

echo "==> 创建 venv ..."
[[ -d "$VENV" ]] || $PY -m venv "$VENV"

echo "==> 升级 pip ..."
"$VENV/bin/pip" install --upgrade pip wheel setuptools 2>&1 | tail -2

echo "==> 装 Python 依赖 (mlx-lm + torch + transformers + flask) ..."
"$VENV/bin/pip" install -r requirements.txt 2>&1 | tail -5

echo "==> 验证..."
"$VENV/bin/python" -c "
import sys
print(f'Python: {sys.version}')
import flask
print('flask:', flask.__version__)
try:
    import mlx_lm
    print('mlx_lm: OK')
except ImportError as e:
    print('mlx_lm: FAIL', e)
import torch
print(f'torch: {torch.__version__} (MPS={torch.backends.mps.is_available()})')
import transformers
print('transformers:', transformers.__version__)
"

echo ""
echo "==> 下一步:"
echo "  1) bash download_models.sh           # 下载模型 (Qwen3-4B-MLX + marqo-fashionCLIP)"
echo "  2) bash start_llm.sh                 # 测试启动 LLM 服务 (Ctrl+C 退出)"
echo "  3) bash start_visual.sh              # 测试启动视觉服务"
echo "  4) bash install_launchd.sh           # 注册为 launchd 自启服务"
