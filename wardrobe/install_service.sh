#!/bin/bash
# 注册 systemd 服务，开机自启
set -e
SERVICE_FILE="/etc/systemd/system/wardrobe.service"

if [[ ! -f /opt/wardrobe/app.py ]]; then
    echo "错误: /opt/wardrobe/app.py 不存在, 请先运行 setup_linux.sh"
    exit 1
fi

echo "==> 安装 service 文件..."
cp "$(dirname "$0")/wardrobe.service" "$SERVICE_FILE"
systemctl daemon-reload
systemctl enable wardrobe.service
systemctl restart wardrobe.service

sleep 2
echo ""
echo "==> 状态:"
systemctl status wardrobe.service --no-pager -l | head -20

echo ""
echo "==> 实时日志: journalctl -u wardrobe -f"
echo "==> 停止:    systemctl stop wardrobe"
echo "==> 卸载:    systemctl disable wardrobe && rm $SERVICE_FILE"
