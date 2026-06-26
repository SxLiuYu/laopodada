# laopodada-api

独立后端微服务 — `老婆哒哒` 手机客户端的 API + 图片存储。**拆出**自原 laopodada 套件(:8096),监听 `:8097`,通过统一 Nginx 入口 `:8088/laopodada/` 暴露给公网。

## 模块

| 模块 | 状态 | 说明 |
|---|---|---|
| Wardrobe (衣橱) | ✅ MVP | 上传 / 列表 / 详情 / 删除 + 3 层 WebP 缩放 |
| Recipe (食谱) | ⏳ | 下一阶段 |
| Health (健康知识) | ⏳ | 下一阶段 |

## 接口

Base URL: `http://123.57.107.21:8088/laopodada`

| 路径 | 方法 | 说明 |
|---|---|---|
| `/health` | GET | 健康检查 (不走 Nginx 前缀,直连 8097) |
| `/api/v1/items?category=...` | GET | 列表 |
| `/api/v1/items/:id` | GET | 详情 |
| `/api/v1/items` | POST (multipart) | 上传,fields: `file`, `category`, `title`, `brand?`, `color?`, `season?` |
| `/api/v1/items/:id` | DELETE | 删除 |
| `/images/...` | GET | 静态图片 (Nginx 直出) |

## 图片策略

上传后自动生成 3 个尺寸(JPEG):

| 用途 | 长边 | 典型大小 | 路径 |
|---|---|---|---|
| `original` | 2048px | 200-500KB | `/data/laopodada/images/original/` |
| `list` | 800px | 50-100KB | `/data/laopodada/images/list/` |
| `thumb` | 200px | 10-20KB | `/data/laopodada/images/thumb/` |

## 部署

```bash
# 首次
python3 -m venv venv
. venv/bin/activate
pip install -r requirements.txt

# 配 systemd
sudo cp systemd/laopodada-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now laopodada-api

# Nginx: 复用现成 :8088,加 location /laopodada/ 代理
```

## 配套 iOS 客户端

https://github.com/SxLiuYu/laopodada (子目录 `laopodada-ios/`)
