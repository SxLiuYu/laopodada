#!/bin/bash
# 卸载 launchd 服务
LABEL_LLM="com.wardrobe.llm"
LABEL_VISUAL="com.wardrobe.visual"
PLIST_DIR="$HOME/Library/LaunchAgents"
launchctl unload "$PLIST_DIR/${LABEL_LLM}.plist" 2>/dev/null && echo "stopped: $LABEL_LLM" || true
launchctl unload "$PLIST_DIR/${LABEL_VISUAL}.plist" 2>/dev/null && echo "stopped: $LABEL_VISUAL" || true
rm -f "$PLIST_DIR/${LABEL_LLM}.plist" "$PLIST_DIR/${LABEL_VISUAL}.plist"
echo "==> 卸载完成"
