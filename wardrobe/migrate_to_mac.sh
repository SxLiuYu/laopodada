#!/bin/bash
# 把 Windows 上的 wardrobe 数据迁移到 Mac
# 用法 (在 Mac 上): bash migrate_to_mac.sh
# 预期输入: Windows 上的 wardrobe 项目 zip 包路径

set -e

if [[ -z "$1" ]]; then
    echo "用法: $0 <wardrobe-windows.zip>"
    echo "先用 7z/powershell 在 Windows 上把整个 wardrobe 文件夹打包 (排除 .venv 和 node_modules)"
    exit 1
fi

ZIP=$1
TMP=$(mktemp -d)
echo "==> 解压到 $TMP ..."
unzip -q "$ZIP" -d "$TMP"

# 找 wardrobe 根目录
if [[ -d "$TMP/wardrobe" ]]; then
    SRC="$TMP/wardrobe"
else
    # 兼容其它目录名
    SRC=$(find "$TMP" -name "app.py" -exec dirname {} \; | head -1)
fi

[[ -z "$SRC" ]] && { echo "未找到 app.py"; exit 1; }
echo "==> 源目录: $SRC"

DEST="$HOME/wardrobe"
mkdir -p "$DEST"

echo "==> 复制项目文件 (覆盖) ..."
rsync -a --exclude='.venv' --exclude='__pycache__' --exclude='logs' \
    "$SRC"/ "$DEST"/

echo "==> 完成。下一步:"
echo "  cd $DEST"
echo "  bash setup_mac.sh         # 安装依赖"
echo "  bash download_models.sh   # 下载 AI 模型 (~3GB)"
echo "  bash start.sh             # 测试启动"
