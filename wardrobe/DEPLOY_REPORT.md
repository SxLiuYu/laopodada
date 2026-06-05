# 部署完成总结

## 访问地址
**http://123.57.107.21:5050**

## 部署结果
| 模块 | 状态 | 原因 |
|---|---|---|
| Flask Web | OK | 服务运行中, PID 159048, 占用 42MB |
| 规则推荐引擎 | OK | 12 件衣物生成 6 套搭配 |
| LLM 精排 | **自动禁用** | 1.6GB 内存不够装 Qwen2.5-0.5B (需 ≥900MB 可用, 当前仅 770MB) |
| FashionCLIP | **未启用** | 1.6GB 无法同时装 LLM + 600MB 视觉模型 |

**当前模式: 纯规则 + 颜色评分**, AI 状态端点会返回 `disabled_reason` 给前端展示 "规则模式" 徽章.

## 3 个启用 AI 的方案 (任选一)

### 方案 A: 升级服务器内存 (推荐, 最简单)
- 阿里云 ECS 1核2GB → 2核4GB, 大概 +30-50 元/月
- 重启后 LLM 可直接加载, FashionCLIP 仍需放别处
- 改动: `systemctl restart wardrobe` 即可, 代码已自动适配

### 方案 B: 等家里 Mac mini 装好, 走混合架构
- Mac mini (家里) 跑 Qwen3-4B-Thinking-MLX (16GB 统一内存) + FashionCLIP
- 云服务器 (公网) 跑 Flask, 通过 Tailscale 访问 Mac mini
- 优点: AI 全功能, 隐私也好
- 工作量: 今晚装 Tailscale, 写 Mac mini 端的两个微服务 (LLM + 视觉)

### 方案 C: 用量化模型硬塞进 1.6GB
- 下载 `Qwen2.5-0.5B-Instruct-GGUF` (Q4_K_M 量化, ~400MB)
- 加装 `llama-cpp-python`, 写个轻量推理服务
- 内存够用, 但 LLM 速度会很慢 (~5-10 token/s)
- 视觉模型仍需放别处

## 已部署文件位置
```
/opt/wardrobe/              # Flask 应用
/opt/wardrobe_env/          # Python venv (torch+transformers+flask+...)
/opt/llm_models/Qwen2.5-0.5B/  # 已下载的 LLM 权重 (954MB)
```

## 常用运维命令
```bash
systemctl status wardrobe     # 服务状态
systemctl restart wardrobe    # 重启
journalctl -u wardrobe -f     # 实时日志
tail -f /opt/wardrobe/logs/wardrobe.out.log
```

## 下一步
请告诉我选哪个方案. 如果选 A, 告诉我新服务器 IP, 我重做一次安装即可. 如果选 B, 今晚 Mac mini 装好后我写两个微服务 + Tailscale 配置.
