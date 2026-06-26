# 老婆哒哒 (laopodada)

> 老婆的私人助理套件 — 衣橱 + 食谱 + 健康知识。原生双端 + 独立后端微服务。

## 子项目

| 目录 | 用途 | 技术栈 | 端口 |
|---|---|---|---|
| [`laopodada-ios/`](./laopodada-ios/) | iPhone / iPad 客户端 | SwiftUI, iOS 16+ | — |
| [`laopodada-api/`](./laopodada-api/) | 后端 API + 图片存储 | Flask + gunicorn + Pillow + SQLite | 8097 → 8088 |

## 部署拓扑

```
┌──────────────────┐        ┌──────────────────────┐
│  iOS / Android   │  HTTPS │  Nginx :8088         │
│      app         │ ─────► │   /laopodada/ → :8097│
└──────────────────┘        │   /images/   → /data │
                            └──────────┬───────────┘
                                       │ proxy_pass
                            ┌──────────▼───────────┐
                            │  gunicorn :8097      │
                            │  Flask laopodada-api │
                            └──────────┬───────────┘
                                       │
                            ┌──────────▼───────────┐
                            │  /data/laopodada/    │
                            │  ├─ images/          │
                            │  │  ├─ original/     │
                            │  │  ├─ list/         │
                            │  │  └─ thumb/        │
                            │  └─ db/laopodada.db  │
                            └──────────────────────┘
```

## 路线图

| 模块 | 状态 |
|---|---|
| **衣橱 (Wardrobe)** | ✅ MVP — 上传/列表/详情/删除 + 3 层 WebP 缩放 |
| 食谱 (Recipe) | ⏳ 下一步 |
| 健康知识 (Health) | ⏳ 待规划 |
| Android 客户端 | ⏳ 待开工 (Kotlin + Jetpack Compose) |

## 模块化开发

两个子项目独立可读、独立可改、独立 push:

```bash
cd laopodada-ios && open laopodada.xcodeproj
cd laopodada-api && python3 -m venv venv && . venv/bin/activate
```

## 部署

后端部署文档: [`laopodada-api/README.md`](./laopodada-api/README.md#部署)
