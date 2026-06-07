# laopodada（老婆哒哒）

> 老婆的私人助理套件 — 包含衣橱、食谱、健康知识三个独立 app

## 项目结构

```
laopodada/
├── wardrobe/   # 衣橱项目：AI 推荐穿搭，给老婆挑衣服
├── recipe/ # 食谱项目：贾维斯智能食谱推荐，记住老婆口味
├── health/     # 健康知识：偏口鱼博士风格循证医学科普
└── README.md   # 本文件
```

## wardrobe（衣橱）

AI 驱动的智能衣橱系统：

- **app.py** — Flask 主入口
- **ai/** — AI 模块（device, fashion_embedder, llm_rerank, prompts）
- **deploy_cloud.py** — 云端部署脚本
- **mac_services/** — macOS launchd 服务

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

启动：
```bash
cd recipe
pip install -r requirements.txt
python app.py
```

## health（健康知识）

偏口鱼博士风格循证医学科普系统，基于复旦大学医学院+瑞典隆德大学博士背景的营养学科普内容。

- **app.py** — Flask 主入口，智能问答 +知识库浏览
- **knowledge_db.py** — 30+ 条核心知识点（食物红榜/智商税黑榜/健康习惯/营养素/体检/运动/特定人群）
- **templates/index.html** — 响应式前端界面

**核心功能：**
- 智能问答：输入健康问题，AI 整合知识库回答
- 知识分类浏览：红榜食物/黑榜智商税/健康习惯/营养素等分类
- 饮食公式：肉蛋奶 + 深色蔬菜 + 粗粮主食 + 少糖少果
- 随机金句轮播

启动：
```bash
cd health
pip install -r requirements.txt
python app.py  # 端口8096
```

## 起源

本仓库由 `wardrobe.zip`（衣橱项目）和 `recipe-app`（食谱项目）合并而成，
2026-06-07 新增 `health` 健康知识模块（基于偏口鱼博士直播内容）。