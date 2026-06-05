# 电子衣橱 (Smart Wardrobe)

> AI 增强的本地穿搭推荐系统 — 规则 + 视觉 (FashionCLIP) + LLM (Qwen3) 三路融合

## ✨ 特性

- 🌤️ 根据天气（wttr.in）智能推荐
- 🎨 颜色搭配规则 + 风格-场合映射
- 👁 FashionCLIP 视觉兼容性打分 (Marqo ViT-B/16, SOTA)
- 🤖 Qwen3-4B-Thinking LLM 精排 + 中文推荐理由
- 💾 完全本地运行，数据不出本机
- 🪶 Mac mini M4 16GB 流畅运行（~3GB 内存占用）

## 🚀 快速开始

### Windows (开发)
```bash
pip install -r requirements.txt
python app.py
# 访问 http://localhost:5050
```

### Mac mini M4 (生产部署)
详见 [README_MAC.md](./README_MAC.md)

```bash
cd ~/wardrobe
bash setup_mac.sh         # 装依赖
bash download_models.sh   # 下模型 (~3GB)
bash start.sh             # 启动
# 部署到 launchd 让它自启
```

## 🏗 架构

```
┌─────────────────────────────────────────┐
│  Flask Web (app.py)                     │
│                                         │
│  ┌──────────┐  ┌──────────┐  ┌───────┐  │
│  │ 规则候选 │→ │ 视觉打分 │→ │LLM精排│  │
│  └──────────┘  └──────────┘  └───────┘  │
│  (传统)      (FashionCLIP) (Qwen3)    │
└─────────────────────────────────────────┘
        ↓                  ↓
  颜色风格字典     Marqo/marqo-fashionCLIP
  温度场合过滤     + lmstudio-community/
                   Qwen3-4B-Thinking-MLX
```

## 📁 目录结构

```
wardrobe/
├── app.py                  # Flask 主入口
├── ai/                     # AI 模块
│   ├── device.py           # 设备检测 (MPS/CUDA/CPU)
│   ├── fashion_embedder.py # FashionCLIP 视觉编码
│   ├── llm_rerank.py       # Qwen3 LLM 精排
│   └── prompts.py          # 提示词模板
├── data/                   # 衣橱数据 + embedding 缓存
├── static/                 # 前端静态资源
│   ├── css/style.css
│   ├── js/app.js
│   └── uploads/            # 衣物图片
├── templates/index.html    # 主页
├── requirements.txt
├── setup_mac.sh            # Mac 一键装依赖
├── download_models.sh      # Mac 一键下模型
├── start.sh                # Mac 启动脚本
├── com.wardrobe.app.plist  # Mac launchd 配置
└── README_MAC.md           # Mac 部署详细文档
```

## 🔧 配置

通过 `.env`（复制自 `.env.example`）：

```bash
HOST=0.0.0.0
PORT=5050
WARDROBE_MODELS_DIR=/Users/你的用户名/wardrobe_models
```

模型位置也可单独指定：
- `FASHION_CLIP_DIR` - 视觉模型
- `LLM_MODEL_DIR` - LLM 模型

## 🎯 API

| 端点 | 方法 | 说明 |
|---|---|---|
| `/` | GET | 主页 |
| `/api/wardrobe` | GET | 列衣橱 |
| `/api/wardrobe` | POST | 添衣物（multipart，含 image 字段） |
| `/api/wardrobe/<id>` | DELETE | 删衣物 |
| `/api/weather?city=X` | GET | 查天气 |
| `/api/recommend?city=X&occasion=Y` | GET | 生成搭配 |
| `/api/ai/status` | GET | AI 模型状态 |

## 🛠 开发

- 规则逻辑：`app.py` 顶部的 `COLOR_PAIRS_GOOD` / `OCCASION_STYLES`
- 视觉权重：`app.py` 中 `VISUAL_WEIGHT = 2.0`
- 提示词：`ai/prompts.py`
- LLM 解析：`ai/llm_rerank.py:OutfitReasoner._parse()`

## 📊 模型选择

| 角色 | 模型 | 占用 | 备注 |
|---|---|---|---|
| LLM | `lmstudio-community/Qwen3-4B-Thinking-2507-MLX-4bit` | 2.3 GB | 带 thinking |
| 视觉 | `Marqo/marqo-fashionCLIP` (ViT-B/16) | 600 MB | SOTA fashion CLIP |

升级：换 `Marqo/marqo-fashionSigLIP`（更准）或 `mlx-community/Qwen3-8B-4bit`（更大但更慢）。
