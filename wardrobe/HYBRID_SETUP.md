# 混合 AI 模式部署 (Mac mini + 云服务器)

## 架构

```
┌─────────────────┐   HTTPS (Tailscale 私网)
│  Mac mini 家里  │   100.x.x.x
│  ┌────────────┐ │
│  │ LLM  :8001 │ │ ──┐
│  │ 视觉  :8002│ │ ──┤
│  └────────────┘ │   │
└─────────────────┘   │
                     │
┌─────────────────┐  │
│  阿里云 ECS      │  │
│  123.57.107.21  │◄─┘
│  ┌────────────┐ │
│  │ Flask:5050 │ │  ← 公网访问
│  │ (无本地模型)│ │
│  └────────────┘ │
└─────────────────┘
```

**数据流**: 用户请求 → 云端 Flask (规则 + 候选) → 远程调用 Mac mini (LLM 精排 + 视觉打分) → 返回推荐

## 前置: Tailscale 配对 (10 分钟)

Tailscale 让两台机器在公网之外组建 VPN, 免费, 无需端口映射.

### 1. 注册 Tailscale 账号
- 浏览器打开 https://login.tailscale.com/start
- 用 Google / Microsoft / GitHub 账号登录
- 同一账号下所有设备自动连入

### 2. Mac mini 登录
```bash
brew install tailscale
sudo tailscale up
# 弹出 URL, 浏览器打开确认
tailscale ip -4   # 记下 100.x.x.x, 例: 100.64.0.2
```

### 3. 云服务器登录 (已装, 需激活)
```bash
tailscale up
# 弹出 URL, 浏览器打开确认
tailscale ip -4   # 记下, 例: 100.64.0.3
```

### 4. 验证互通
在 Mac mini 上:
```bash
ping 100.64.0.3       # 应能 ping 通云服务器 Tailscale IP
```

## 部署 Mac mini 微服务

把仓库的 `mac_services/` 整个目录拷到 Mac mini, 或在 Mac mini 上 `git clone`.

```bash
cd mac_services
chmod +x *.sh

# 1. 装 Python 依赖 (mlx-lm + torch + transformers)
bash setup_services.sh

# 2. 下模型 (Qwen3-4B-MLX ~2.3GB + FashionCLIP ~600MB)
bash download_models.sh

# 3. 测试启动 (前台, Ctrl+C 退出)
bash start_llm.sh
# 另一个终端:
bash start_visual.sh

# 4. 验证
curl http://127.0.0.1:8001/health
curl http://127.0.0.1:8002/health

# 5. 注册为开机自启 (launchd)
bash install_launchd.sh
```

## 配置云端连接

把 Mac mini 的 Tailscale IP 填到云服务器的 systemd service:

```bash
# 在云服务器上
ssh root@123.57.107.21
vim /etc/systemd/system/wardrobe.service
```

把这两行的注释去掉, IP 改成 Mac mini 的:
```
Environment="LLM_REMOTE_URL=http://100.64.0.2:8001"
Environment="FASHION_CLIP_REMOTE_URL=http://100.64.0.2:8002"
```

```bash
systemctl daemon-reload
systemctl restart wardrobe
curl -s http://127.0.0.1:5050/api/ai/status
```

应该看到:
```json
{
  "fashion_clip": {"ready": true, "remote": true, "remote_url": "http://100.64.0.2:8002"},
  "llm": {"ready": true, "backend": "remote", "remote": true, "remote_url": "http://100.64.0.2:8001"}
}
```

## 故障排查

| 现象 | 检查 |
|------|------|
| `/api/ai/status` 仍报 `remote(unreachable)` | Mac mini 的 launchd 服务是否启动? `launchctl list \| grep wardrobe` |
| LLM 报 `disabled_reason: 远程 LLM 不可达` | Tailscale 是否通? `tailscale ping 100.64.0.2`; Mac mini 防火墙? 系统设置 → 网络 → 防火墙 → 允许 8001/8002 |
| 视觉 502 | Mac mini 端 `curl http://127.0.0.1:8002/health` 看模型是否加载 |
| 端口冲突 | Mac mini 上 `lsof -i :8001` 和 `:8002`, 关掉占用进程 |
| MLX 报 Metal 错 | 系统设置 → 隐私与安全 → 开发者工具, 给终端勾上 |

## 卸载

云端:
```bash
ssh root@123.57.107.21 "systemctl stop wardrobe && systemctl disable wardrobe && rm /etc/systemd/system/wardrobe.service"
```

Mac mini:
```bash
bash mac_services/uninstall_launchd.sh
```

## 优势

- **隐私**: 衣物图片只在家里的 Mac mini 处理, 不上公网
- **算力**: Mac mini 16GB 统一内存可装 Qwen3-4B-Thinking + FashionCLIP 同时运行
- **云端省心**: 1.6GB 服务器只跑 Flask, 永远不爆内存
- **离线容错**: Mac mini 关机时云端自动降级为纯规则模式, 服务不挂
