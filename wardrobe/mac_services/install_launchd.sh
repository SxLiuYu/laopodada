#!/bin/bash
# 注册为 launchd 系统服务 (开机自启)
set -e
cd "$(dirname "$0")"

VENV="$HOME/wardrobe_services/venv"
LABEL_LLM="com.wardrobe.llm"
LABEL_VISUAL="com.wardrobe.visual"
PLIST_DIR="$HOME/Library/LaunchAgents"
mkdir -p "$PLIST_DIR"

LLM_LOG="$HOME/wardrobe_services/logs/llm.out.log"
LLM_ERR="$HOME/wardrobe_services/logs/llm.err.log"
VIS_LOG="$HOME/wardrobe_services/logs/visual.out.log"
VIS_ERR="$HOME/wardrobe_services/logs/visual.err.log"

# 生成 plist
cat > "$PLIST_DIR/${LABEL_LLM}.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>${LABEL_LLM}</string>
    <key>ProgramArguments</key>
    <array>
        <string>${VENV}/bin/python</string>
        <string>$HOME/wardrobe_services/llm_service.py</string>
        <string>--host</string><string>0.0.0.0</string>
        <string>--port</string><string>8001</string>
    </array>
    <key>WorkingDirectory</key><string>$HOME/wardrobe_services</string>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><true/>
    <key>StandardOutPath</key><string>${LLM_LOG}</string>
    <key>StandardErrorPath</key><string>${LLM_ERR}</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
EOF

cat > "$PLIST_DIR/${LABEL_VISUAL}.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>${LABEL_VISUAL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>${VENV}/bin/python</string>
        <string>$HOME/wardrobe_services/visual_service.py</string>
        <string>--host</string><string>0.0.0.0</string>
        <string>--port</string><string>8002</string>
    </array>
    <key>WorkingDirectory</key><string>$HOME/wardrobe_services</string>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><true/>
    <key>StandardOutPath</key><string>${VIS_LOG}</string>
    <key>StandardErrorPath</key><string>${VIS_ERR}</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
EOF

# 加载
launchctl unload "$PLIST_DIR/${LABEL_LLM}.plist" 2>/dev/null || true
launchctl unload "$PLIST_DIR/${LABEL_VISUAL}.plist" 2>/dev/null || true
launchctl load "$PLIST_DIR/${LABEL_LLM}.plist"
launchctl load "$PLIST_DIR/${LABEL_VISUAL}.plist"

echo "==> 已注册 launchd 服务:"
launchctl list | grep wardrobe
echo ""
echo "==> 日志:"
echo "  tail -f $HOME/wardrobe_services/logs/llm.out.log"
echo "  tail -f $HOME/wardrobe_services/logs/visual.out.log"
echo ""
echo "==> 状态检查:"
sleep 3
curl -s http://127.0.0.1:8001/health | head -c 200
echo ""
curl -s http://127.0.0.1:8002/health | head -c 200
echo ""
