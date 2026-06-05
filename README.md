# laopodada（老婆哒哒）

> 老婆的私人助理套件 — 包含衣橱和食谱两个独立 app

## 项目结构

```
laopodada/
├── wardrobe/   # 衣橱项目：AI 推荐穿搭，给老婆挑衣服
├── recipe/     # 食谱项目：贾维斯智能食谱推荐，记住老婆口味
└── README.md   # 本文件
```

## wardrobe（衣橱）

AI 驱动的智能衣橱系统：

- **app.py** — Flask 主入口
- **ai/** — AI 模块（device, fashion_embedder, llm_rerank, prompts）
- **deploy_cloud.py** — 云端部署脚本
- **mac_services/** — macOS launchd 服务
- **HYBRID_SETUP.md** / **DEPLOY_REPORT.md** — 部署文档

启动：
```bash
cd wardrobe
pip install -r requirements.txt
python app.py
```

## recipe（食谱）

贾维斯智能食谱推荐系统：

- **app.py** — Flask 主入口
- **recipe_core.py** — 食谱核心逻辑
- **wife_profile.py** — 老婆口味画像
- **smart_recommend.py** — 智能推荐
- **generate_recipes.py** / **expand_recipes.py** — 食谱生成与扩展

启动：
```bash
cd recipe
pip install -r requirements.txt
python app.py
```

## 起源

本仓库由 `wardrobe.zip`（衣橱项目）和 `recipe-app`（食谱项目）合并而成，
统一管理"给老婆的"应用套件。
