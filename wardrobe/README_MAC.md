# Mac mini 部署指南

## 一、前置准备（一次性）

把整个 `wardrobe` 项目复制到 Mac mini：

```bash
# 在 Mac mini 上
mkdir -p ~/wardrobe ~/wardrobe_models ~/wardrobe/logs
# 从 Windows 拷贝 wardrobe 项目到 ~/wardrobe/（U盘/网盘/Scp 均可）
```

> ⚠️ 不要把 `data/wardrobe.json` 和 `static/uploads/` 一起覆盖——这些是你 Windows 上积累的真实数据。

## 二、一键安装依赖

```bash
cd ~/wardrobe
bash setup_mac.sh
```

会自动创建 `.venv` 虚拟环境并装好：
- Flask、requests、Pillow、numpy
- transformers、torch（带 MPS 加速）
- mlx-lm（仅 Apple Silicon）

## 三、下载 AI 模型（一次性，约 3GB）

```bash
bash download_models.sh
```

会下载到 `~/wardrobe_models/`：
- `marqo-fashionCLIP/` — 视觉模型（~600MB）
- `Qwen3-4B-Thinking-MLX-4bit/` — LLM（~2.3GB）

## 四、测试运行

```bash
cp .env.example .env
bash start.sh
```

浏览器打开 `http://localhost:5050`，右上角应显示「AI 已就绪 · mlx」绿色徽章。

按 `Ctrl+C` 停止。

## 五、后台常驻（开机自启）

```bash
# 1) 编辑 plist，把所有 "你的用户名" 替换为真实 macOS 用户名
nano com.wardrobe.app.plist

# 2) 安装到 LaunchAgents
cp com.wardrobe.app.plist ~/Library/LaunchAgents/

# 3) 加载（立即启动 + 开机自启）
launchctl load -w ~/Library/LaunchAgents/com.wardrobe.app.plist

# 4) 查看状态
launchctl list | grep wardrobe

# 5) 实时日志
tail -f ~/wardrobe/logs/wardrobe.out.log
```

卸载：
```bash
launchctl unload ~/Library/LaunchAgents/com.wardrobe.app.plist
rm ~/Library/LaunchAgents/com.wardrobe.app.plist
```

## 六、从局域网/外网访问

`HOST=0.0.0.0` 已经是局域网可访问。Mac mini 防火墙首次会弹窗允许。

- 局域网：`http://mac-mini-ip:5050`
- 外网：可在 Mac mini 上跑 Tailscale/Cloudflare Tunnel，或在路由器做端口映射（不推荐）

## 七、常见问题

### Q1: 启动后右上角显示「纯规则模式」
检查：
```bash
ls ~/wardrobe_models/            # 模型目录是否存在
ls ~/wardrobe_models/marqo-fashionCLIP/config.json
ls ~/wardrobe_models/Qwen3-4B-Thinking-MLX-4bit/config.json
```
如果有文件但仍报「纯规则」，看 `~/wardrobe/logs/wardrobe.err.log`。

### Q2: 第一次 `/api/recommend` 很慢（>10s）
首次 LLM 加载到内存要 5-10s，第二次会快。加 `KEEP_MODEL_WARM=1` 环境变量（如改代码支持）。

### Q3: 想要更强的视觉模型？
替换 `~/wardrobe_models/marqo-fashionCLIP/` 为 `Marqo/marqo-fashionSigLIP`（更准但稍大）。

### Q4: 想换更大的 LLM？
把 `download_models.sh` 中的模型改为 `mlx-community/Qwen3-8B-4bit` 等。但 16GB 内存跑 8B 4-bit 较紧。

### Q5: 内存吃紧？
```bash
# 关闭 macOS 不必要的应用
# 或在 .env 加 HEAVY_MODE=0 让代码用更小的视觉模型变体
```

## 八、升级模型

```bash
# 删除旧模型
rm -rf ~/wardrobe_models/Qwen3-4B-Thinking-MLX-4bit

# 下载新模型（修改 download_models.sh 中的模型名）
bash download_models.sh

# 重启服务
launchctl unload ~/Library/LaunchAgents/com.wardrobe.app.plist
launchctl load -w ~/Library/LaunchAgents/com.wardrobe.app.plist
```
