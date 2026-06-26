# APK v10 主页重构 + AI 嵌各 tab 内 — 实施计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 把 v9 的 5 tab 应用重构为 v10 的 3 tab + 主页 3 卡片 + AI 浮动按钮(嵌各 tab 内) + 衣橱拍照/AI FAB 共存(K3)。

**架构：**
- **后端**：laopodada-api Flask,新增 `outfits.py` 端点,atlas 中转 M2.7
- **前端**：原生 JS(无框架),3 tab 主页 + 5 文件改 + 4 文件新建
- **部署**：本地 Mac 跑前端预览 → 推 GitHub → CI build APK → 同步 123 公开 URL

**技术栈：**
- 后端 Python 3.9 + Flask + sqlite3 + Pillow
- 前端 Vanilla JS + CSS3
- LLM minimax M2.7(经 atlas panel.py 中转)
- 构建 GitHub Actions + Capacitor 8.x
- 部署 阿里云 123.57.107.21 (nginx 8088 SSL)

**Spec 文档：** `/Users/sxliuyu/repos/laopodada/docs/superpowers/specs/2026-06-15-apk-v10-redesign.md`

**Worktree 建议：** main 分支直接做(用户偏好,无需 PR review)。

---

## 文件结构

### 新增文件(后端)
- `laopodada-api/outfits.py` — `/api/v1/outfits/generate` 端点逻辑
- `laopodada-api/tests/test_outfits.py` — outfit endpoint 单元测试

### 新增文件(前端)
- `www/css/ai-fab.css` — 渐变浮动按钮 + 黑色横条样式
- `www/js/ai-fab.js` — AI FAB 通用组件(打开底部 sheet + 提交 + 渲染结果)
- `www/css/main-page.css` — 主页 3 卡片渐变样式
- `www/js/main-page.js` — 主页卡片渲染 + 跳 tab 逻辑

### 重构文件(前端)
- `www/index.html` — 改 5 tab → 3 tab,加主页 page-main 容器,移除旧 page-ai-tab 等
- `www/js/app.js` — switchTab 改为 3 tab(主页/对话/我的),处理 page-main 容器
- `www/js/wardrobe.js` — 加 K3 模式(横条按钮 + AI FAB),调用 ai-fab.js
- `www/js/recipe.js` — 加 AI FAB,触发 AI 菜品推荐
- `www/js/health.js` — 加 AI FAB,触发 AI 健康科普
- `www/js/chat.js` — 顶部加返回主页按钮

### 修改文件(后端)
- `laopodada-api/app.py` — 注册新 outfits route

---

## 任务清单

### 任务 1：后端 — outfit endpoint 单元测试 (TDD 红灯)

**文件：**
- 创建：`laopodada-api/tests/test_outfits.py`

- [ ] **步骤 1：编写失败的测试**

```python
# laopodada-api/tests/test_outfits.py
import pytest
import json

def test_outfits_generate_success(client, mock_atlas):
    """Test AI outfit generation returns 200 with items + description."""
    # Mock atlas response
    mock_atlas.return_value = {
        "outfit": {
            "items": [{"id": "item-1", "category": "top", "color": "white"}],
            "description": "白色T恤配牛仔裤,清新自然"
        }
    }

    # Need at least 2 items in wardrobe
    client.post("/api/v1/items", data={
        "file": (b"fake-jpg-data", "shirt.jpg"),
        "category": "top"
    }, content_type="multipart/form-data")
    client.post("/api/v1/items", data={
        "file": (b"fake-jpg-data-2", "pants.jpg"),
        "category": "bottom"
    }, content_type="multipart/form-data")

    response = client.post("/api/v1/outfits/generate",
        json={"occasion": "casual"},
        content_type="application/json"
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "outfit" in data
    assert "items" in data["outfit"]
    assert len(data["outfit"]["items"]) >= 1
    assert "description" in data["outfit"]
    assert isinstance(data["outfit"]["description"], str)
    assert len(data["outfit"]["description"]) > 10


def test_outfits_generate_empty_wardrobe(client, mock_atlas):
    """Test 422 when wardrobe is empty."""
    response = client.post("/api/v1/outfits/generate",
        json={"occasion": "casual"},
        content_type="application/json"
    )
    assert response.status_code == 422
    data = json.loads(response.data)
    assert "衣橱为空" in data.get("error", "")


def test_outfits_generate_atlas_timeout(client, mock_atlas):
    """Test 504 when atlas LLM times out."""
    mock_atlas.side_effect = TimeoutError("atlas timeout")

    # Add items first
    client.post("/api/v1/items", data={
        "file": (b"fake-jpg-data", "shirt.jpg"),
        "category": "top"
    }, content_type="multipart/form-data")

    response = client.post("/api/v1/outfits/generate",
        json={"occasion": "casual"},
        content_type="application/json"
    )
    assert response.status_code == 504
```

- [ ] **步骤 2：运行测试验证失败**

```bash
cd /Users/sxliuyu/repos/laopodada/laopodada-api
python3 -m pytest tests/test_outfits.py -v
```

预期：FAIL 报告 "module 'outfits' not found" + "fixture 'client' not found"

---

### 任务 2：后端 — outfit endpoint 最小实现 (TDD 绿灯)

**文件：**
- 创建：`laopodada-api/outfits.py`
- 修改：`laopodada-api/app.py` (注册新 route + conftest 修复)

- [ ] **步骤 1：实现 outfits.py**

```python
# laopodada-api/outfits.py
"""AI outfit recommendation endpoint."""
import json
import logging
import random
import urllib.request
import urllib.error
from typing import Any
from flask import Blueprint, request, jsonify, current_app
from . import db, atlas_client

bp = Blueprint("outfits", __name__, url_prefix="/api/v1/outfits")
log = logging.getLogger(__name__)

CACHE = {}  # query -> response, 1h TTL
CACHE_TTL = 3600

@bp.post("/generate")
def generate_outfit():
    """AI generates outfit from user's wardrobe items."""
    body = request.get_json(silent=True) or {}
    occasion = body.get("occasion", "casual")
    weather = body.get("weather")

    # 1. Get all items from DB
    items = db.get_all_items()
    if not items:
        return jsonify({"error": "衣橱为空,请先添加衣物"}), 422

    # 2. Cache check
    cache_key = f"outfit:{occasion}:{weather}:{len(items)}"
    if cache_key in CACHE:
        cached_at, cached_resp = CACHE[cache_key]
        if time.time() - cached_at < CACHE_TTL:
            return jsonify(cached_resp), 200

    # 3. Call atlas LLM
    items_summary = [
        {"id": it["id"], "category": it["category"], "color": it.get("color", "")}
        for it in items[:20]  # 限制 20 件防 token 超
    ]
    prompt = f"""根据以下衣橱单品,推荐 1 套适合 {occasion} 场合的穿搭。
返回纯 JSON: {{"items": [item_id 数组, 2-3 件], "description": "搭配描述 50-100 字,中文", "tips": "穿搭小贴士 30-50 字"}}
衣橱: {json.dumps(items_summary, ensure_ascii=False)}"""

    try:
        atlas_resp = atlas_client.call(prompt, timeout=90)
    except TimeoutError as e:
        log.error(f"atlas timeout: {e}")
        return jsonify({"error": "AI 思考超时,请重试"}), 504
    except Exception as e:
        log.error(f"atlas error: {e}")
        return jsonify({"error": f"AI 服务异常: {str(e)[:100]}"}), 500

    # 4. Parse atlas response (expect JSON)
    outfit = _parse_outfit_json(atlas_resp, items)
    if not outfit:
        return jsonify({"error": "AI 回复格式错误,请换个主题重试"}), 422

    # 5. Enrich with image URLs
    id_to_item = {it["id"]: it for it in items}
    enriched_items = []
    for item_id in outfit["items"]:
        if item_id in id_to_item:
            it = id_to_item[item_id]
            enriched_items.append({
                "id": it["id"],
                "category": it["category"],
                "url": it.get("thumbnail_url") or it.get("original_url"),
                "color": it.get("color", ""),
            })

    response = {
        "outfit": {
            "items": enriched_items,
            "description": outfit["description"],
            "tips": outfit.get("tips", ""),
        }
    }

    # 6. Cache
    import time
    CACHE[cache_key] = (time.time(), response)

    return jsonify(response), 200


def _parse_outfit_json(reply: str, items: list) -> dict | None:
    """Extract JSON from LLM reply, handle markdown fence."""
    import re
    # Try code fence first
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", reply, re.S)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # Try raw JSON
    m = re.search(r"\{.*\}", reply, re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    return None
```

- [ ] **步骤 2：app.py 加注册 + conftest.py**

```python
# laopodada-api/app.py (在 app 初始化之后加)
from . import outfits
app.register_blueprint(outfits.bp)
```

```python
# laopodada-api/tests/conftest.py
import pytest
from unittest.mock import patch, MagicMock
from app import app as flask_app
from . import db
import os
import tempfile

@pytest.fixture
def client():
    """Flask test client with in-memory DB."""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    flask_app.config["DB_PATH"] = db_path
    flask_app.config["TESTING"] = True

    with flask_app.test_client() as c:
        with flask_app.app_context():
            db.init_db(db_path)
        yield c

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def mock_atlas():
    """Mock atlas_client.call."""
    with patch("outfits.atlas_client.call") as mock:
        yield mock
```

- [ ] **步骤 3：运行测试验证通过**

```bash
cd /Users/sxliuyu/repos/laopodada/laopodada-api
python3 -m pytest tests/test_outfits.py -v
```

预期：3 passed (test_outfits_generate_success, test_outfits_generate_empty_wardrobe, test_outfits_generate_atlas_timeout)

- [ ] **步骤 4：真盘 curl 验证**

```bash
# 本地启动 laopodada-api(假设 8097 端口)
cd /Users/sxliuyu/repos/laopodada/laopodada-api
python3 app.py &

# 等 2s, curl 测试
sleep 2
curl -X POST http://127.0.0.1:8097/api/v1/outfits/generate \
  -H "Content-Type: application/json" \
  -d '{"occasion": "casual"}'
```

预期：HTTP 200 + JSON 含 outfit.items[].id + outfit.description 中文

- [ ] **步骤 5：Commit**

```bash
cd /Users/sxliuyu/repos/laopodada
git add laopodada-api/outfits.py laopodada-api/app.py laopodada-api/tests/
git commit -m "feat(api): POST /api/v1/outfits/generate AI 穿搭推荐 (atlas M2.7)"
```

---

### 任务 3：后端 — rsync 到 123 + 重启 + 真盘验

**文件：** 无代码改动,只部署

- [ ] **步骤 1：rsync 同步到 123**

```bash
cd /Users/sxliuyu/repos/laopodada
sshpass -p 'YuJinZe12@.' rsync -avz \
  -e "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null" \
  laopodada-api/outfits.py laopodada-api/app.py \
  root@123.57.107.21:/opt/laopodada-api/
```

- [ ] **步骤 2：重启 gunicorn**

```bash
sshpass -p 'YuJinZe12@.' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  root@123.57.107.21 "systemctl restart laopodada-api && sleep 2 && curl -s http://127.0.0.1:8097/api/v1/items | python3 -c \"import json,sys; d=json.load(sys.stdin); print(f'items count: {len(d.get(\\\"items\\\",[]))}')\""
```

预期：`items count: 2` (至少 2 件测试衣橱)

- [ ] **步骤 3：真盘测 outfit endpoint**

```bash
sshpass -p 'YuJinZe12@.' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  root@123.57.107.21 "curl -sk -X POST https://127.0.0.1:8097/api/v1/outfits/generate \
    -H 'Content-Type: application/json' \
    -d '{\"occasion\":\"casual\"}' | python3 -c \"import json,sys; d=json.load(sys.stdin); o=d.get('outfit',{}); print(f'items: {len(o.get(\\\"items\\\",[]))}'); print(f'desc: {o.get(\\\"description\\\",\\\"\\\")[:50]}')\""
```

预期：`items: 2-3` + `desc: 50+字中文描述`

---

### 任务 4：前端 — ai-fab.js 通用组件

**文件：**
- 创建：`www/js/ai-fab.js`
- 创建：`www/css/ai-fab.css`

- [ ] **步骤 1：写 CSS**

```css
/* www/css/ai-fab.css */
.ai-fab {
  position: fixed;
  bottom: 76px;
  right: 16px;
  width: 56px;
  height: 56px;
  border-radius: 28px;
  background: linear-gradient(135deg, #ff7a45, #ff5e94);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  box-shadow: 0 4px 12px rgba(255, 90, 100, 0.4);
  cursor: pointer;
  z-index: 100;
  border: none;
  transition: transform 0.15s;
}
.ai-fab:hover { transform: scale(1.08); }
.ai-fab:active { transform: scale(0.95); }

.ai-fab-photo-bar {
  position: fixed;
  bottom: 76px;
  left: 16px;
  right: 88px;
  background: #1a1a1a;
  color: #fff;
  padding: 14px 20px;
  border-radius: 28px;
  text-align: center;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  z-index: 99;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}
.ai-fab-photo-bar:hover { background: #2a2a2a; }

.ai-sheet-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 200;
  display: none;
  align-items: flex-end;
}
.ai-sheet-mask.open { display: flex; }
.ai-sheet {
  background: #fff;
  width: 100%;
  max-height: 70vh;
  border-radius: 16px 16px 0 0;
  padding: 16px;
  overflow-y: auto;
}
.ai-sheet h3 { font-size: 16px; margin-bottom: 12px; color: #ff7a45; }
.ai-sheet textarea {
  width: 100%;
  min-height: 80px;
  padding: 10px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  font-size: 14px;
  resize: vertical;
}
.ai-sheet .ai-submit {
  width: 100%;
  padding: 12px;
  background: linear-gradient(135deg, #ff7a45, #ff5e94);
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 600;
  margin-top: 12px;
  cursor: pointer;
}
.ai-sheet .ai-result {
  margin-top: 12px;
  padding: 12px;
  background: #fafafa;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
}
.ai-sheet .ai-result img {
  max-width: 100%;
  border-radius: 8px;
  margin: 4px 0;
}
```

- [ ] **步骤 2：写 JS 组件**

```javascript
// www/js/ai-fab.js
/* AI 浮动按钮通用组件 + 底部 sheet 弹窗 */

window.AIFab = {
  /**
   * 初始化 AI 浮动按钮(渐变 ✨)
   * @param {object} opts - { tabKey, onClick, position } 
   *   position: 'default' (右下 16px) | 'stacked' (右下 + 上移避让拍照横条)
   */
  init(tabKey, onClick) {
    const fab = document.createElement('button');
    fab.className = 'ai-fab';
    fab.id = `ai-fab-${tabKey}`;
    fab.innerHTML = '✨';
    fab.title = 'AI 推荐';
    fab.onclick = onClick;
    document.body.appendChild(fab);
    return fab;
  },

  /**
   * 初始化衣橱拍照横条(黑色底部按钮)
   * @param {function} onClick - 点击回调(打开文件选择/相机)
   */
  initPhotoBar(tabKey, onClick) {
    const bar = document.createElement('div');
    bar.className = 'ai-fab-photo-bar';
    bar.id = `photo-bar-${tabKey}`;
    bar.innerHTML = '📷 添加衣物到衣橱';
    bar.onclick = onClick;
    document.body.appendChild(bar);
    return bar;
  },

  /**
   * 打开 AI 底部 sheet 弹窗
   * @param {object} opts - { title, placeholder, onSubmit }
   *   onSubmit(text) -> Promise<{ html: string }>
   */
  openSheet(opts) {
    const mask = document.createElement('div');
    mask.className = 'ai-sheet-mask open';
    mask.innerHTML = `
      <div class="ai-sheet">
        <h3>${opts.title || 'AI 推荐'}</h3>
        <textarea id="ai-sheet-input" placeholder="${opts.placeholder || '说说你想要什么...'}"></textarea>
        <button class="ai-submit" id="ai-sheet-submit">✨ 让 AI 想想</button>
        <div class="ai-result" id="ai-sheet-result" style="display:none;"></div>
      </div>
    `;
    document.body.appendChild(mask);

    const input = mask.querySelector('#ai-sheet-input');
    const submit = mask.querySelector('#ai-sheet-submit');
    const result = mask.querySelector('#ai-sheet-result');

    submit.onclick = async () => {
      const text = input.value.trim();
      if (!text) {
        alert('请输入内容');
        return;
      }
      submit.disabled = true;
      submit.textContent = '⏳ AI 思考中...';
      result.style.display = 'block';
      result.textContent = '请稍候,通常需要 30-90 秒...';

      try {
        const r = await opts.onSubmit(text);
        result.innerHTML = r.html;
        submit.textContent = '✓ 完成';
      } catch (e) {
        result.innerHTML = `<span style="color:#d44;">❌ ${e.message || 'AI 服务异常'}</span>`;
        submit.textContent = '重试';
        submit.disabled = false;
      }
    };

    // 点遮罩关闭
    mask.onclick = (e) => {
      if (e.target === mask) mask.remove();
    };
  },

  /**
   * 关闭 AI sheet
   */
  closeSheet() {
    const mask = document.querySelector('.ai-sheet-mask.open');
    if (mask) mask.remove();
  }
};
```

- [ ] **步骤 3：在 index.html 引入**

修改 `www/index.html` 头部加:
```html
<link rel="stylesheet" href="css/ai-fab.css">
```

`www/index.html` 底部 `<script>` 区加:
```html
<script src="js/ai-fab.js"></script>
```

- [ ] **步骤 4：本地启 python http.server 验**

```bash
cd /Users/sxliuyu/repos/laopodada/www
python3 -m http.server 8765 &
sleep 1
curl -s http://127.0.0.1:8765/css/ai-fab.css | head -5
curl -s http://127.0.0.1:8765/js/ai-fab.js | head -5
```

预期：2 段都返回 200 + 内容

- [ ] **步骤 5：Commit**

```bash
cd /Users/sxliuyu/repos/laopodada
git add www/css/ai-fab.css www/js/ai-fab.js www/index.html
git commit -m "feat(www): AI 浮动按钮通用组件 (ai-fab.js + .css)"
```

---

### 任务 5：前端 — main-page.js + index.html 改 3 tab

**文件：**
- 创建：`www/css/main-page.css`
- 创建：`www/js/main-page.js`
- 修改：`www/index.html` (改 5 tab → 3 tab + 加 page-main 容器)
- 修改：`www/js/app.js` (switchTab 支持 page-main)

- [ ] **步骤 1：写 main-page.css**

```css
/* www/css/main-page.css */
.main-page { padding: 16px; min-height: calc(100vh - 80px); }
.main-greet { font-size: 22px; font-weight: 700; margin-bottom: 4px; }
.main-greet-sub { font-size: 13px; color: #999; margin-bottom: 20px; }

.main-card {
  display: flex;
  align-items: center;
  padding: 18px;
  border-radius: 16px;
  margin-bottom: 14px;
  cursor: pointer;
  transition: transform 0.15s;
  position: relative;
  overflow: hidden;
}
.main-card:hover { transform: translateX(4px); }
.main-card-wardrobe { background: linear-gradient(135deg, #fff5e6, #ffe0cc); }
.main-card-recipe { background: linear-gradient(135deg, #ffe6f0, #ffccdd); }
.main-card-health { background: linear-gradient(135deg, #e6f5ff, #cce5ff); }

.main-card-icon { font-size: 36px; margin-right: 16px; }
.main-card-body h4 { font-size: 16px; margin-bottom: 4px; font-weight: 700; }
.main-card-body p { font-size: 11px; color: #666; line-height: 1.4; margin-bottom: 6px; }
.main-card-tag {
  display: inline-block;
  background: rgba(255, 255, 255, 0.85);
  color: #c44;
  font-size: 10px;
  padding: 3px 8px;
  border-radius: 6px;
  font-weight: 600;
}

.tabbar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  background: #fff;
  padding: 8px 4px;
  border-top: 1px solid #f0f0f0;
  z-index: 50;
  padding-bottom: max(8px, env(safe-area-inset-bottom));
}
.tabbar .tab {
  flex: 1;
  text-align: center;
  padding: 6px 0;
  font-size: 12px;
  cursor: pointer;
  border-radius: 8px;
}
.tabbar .tab.active {
  background: linear-gradient(135deg, #ff7a45, #ff5e94);
  color: #fff;
}
```

- [ ] **步骤 2：写 main-page.js**

```javascript
// www/js/main-page.js
/* 主页 3 卡片渲染 + 跳 tab */

async function renderMainPage() {
  const page = document.getElementById('page-main');
  if (!page) return;

  // 拉统计(并行 3 端点)
  let wardrobeCount = 0, recipeCount = 0, healthCount = 0;
  try {
    const [w, r, h] = await Promise.all([
      api.getItems().catch(() => ({ items: [] })),
      api.getRecipes().catch(() => []),
      api.getHealthArticles().catch(() => []),
    ]);
    wardrobeCount = (w.items || w || []).length;
    recipeCount = (Array.isArray(r) ? r : []).length;
    healthCount = (Array.isArray(h) ? h : []).length;
  } catch (e) {
    console.warn('主页统计加载失败:', e);
  }

  page.innerHTML = `
    <div class="main-page">
      <div class="main-greet">嗨,老婆 👋</div>
      <div class="main-greet-sub">今天想做点什么?</div>

      <div class="main-card main-card-wardrobe" data-goto="wardrobe">
        <div class="main-card-icon">👗</div>
        <div class="main-card-body">
          <h4>衣橱</h4>
          <p>${wardrobeCount} 件单品 · 智能搭配</p>
          <div class="main-card-tag">✨ AI 穿搭推荐</div>
        </div>
      </div>

      <div class="main-card main-card-recipe" data-goto="recipe">
        <div class="main-card-icon">🍳</div>
        <div class="main-card-body">
          <h4>点餐</h4>
          <p>${recipeCount} 道菜谱 · 不知道吃啥?</p>
          <div class="main-card-tag">✨ AI 菜品推荐</div>
        </div>
      </div>

      <div class="main-card main-card-health" data-goto="health">
        <div class="main-card-icon">💪</div>
        <div class="main-card-body">
          <h4>健康</h4>
          <p>${healthCount} 篇文章 · 想了解啥?</p>
          <div class="main-card-tag">✨ AI 健康科普</div>
        </div>
      </div>
    </div>
  `;

  // 卡片点击跳 tab
  page.querySelectorAll('.main-card').forEach(card => {
    card.onclick = () => {
      const target = card.dataset.goto;
      switchTab(target);
    };
  });
}
```

- [ ] **步骤 3：改 index.html — 5 tab → 3 tab + 加 page-main**

修改 `www/index.html`:

**A. body 里替换 tabbar 段** (找 5 tab 的 `.tabbar` div,改成 3 tab):

```html
<div class="tabbar">
  <div class="tab active" data-tab="main">主页</div>
  <div class="tab" data-tab="chat">对话</div>
  <div class="tab" data-tab="profile">我的</div>
</div>
```

**B. body 里加 page-main 容器** (放在 page-wardrobe 之前):

```html
<div id="page-main" class="page" style="display:none;"></div>
```

**C. 移除 page-ai-tab 容器** (v9 的"AI 聊天"独立 tab 容器,现在对话 tab 用 page-chat)

**D. 顶部 `<link>` 区加 main-page.css**:

```html
<link rel="stylesheet" href="css/main-page.css">
```

**E. 底部 `<script>` 区加 main-page.js** (在 app.js 之前):

```html
<script src="js/main-page.js"></script>
```

- [ ] **步骤 4：app.js 改 switchTab**

修改 `www/js/app.js` 的 `switchTab(tabKey)` 函数,改为 3 tab + 处理 page-main:

```javascript
// app.js
function switchTab(tabKey) {
  // 隐藏所有 page
  document.querySelectorAll('.page').forEach(p => p.style.display = 'none');
  // 显示目标 page
  const target = document.getElementById(`page-${tabKey}`);
  if (target) {
    target.style.display = 'block';
    // 触发对应 render
    if (tabKey === 'main') renderMainPage();
    else if (tabKey === 'wardrobe') renderWardrobePage();
    else if (tabKey === 'recipe') renderRecipePage();
    else if (tabKey === 'health') renderHealthPage();
    else if (tabKey === 'chat') renderChatPage();
    else if (tabKey === 'profile') renderProfilePage();
  }
  // tab 样式
  document.querySelectorAll('.tabbar .tab').forEach(t => t.classList.remove('active'));
  const activeTab = document.querySelector(`.tabbar .tab[data-tab="${tabKey}"]`);
  if (activeTab) activeTab.classList.add('active');
}

// 初始化:默认主页
document.addEventListener('DOMContentLoaded', () => {
  // tab 点击
  document.querySelectorAll('.tabbar .tab').forEach(tab => {
    tab.onclick = () => switchTab(tab.dataset.tab);
  });
  // 默认进主页
  switchTab('main');
});
```

- [ ] **步骤 5：本地端到端测**

```bash
cd /Users/sxliuyu/repos/laopodada/www
python3 -m http.server 8765 &
sleep 1

# 测主页 HTML
curl -s http://127.0.0.1:8765/ | grep -E "tab main|page-main|main-card"
# 测 main-page.js 可加载
curl -sI http://127.0.0.1:8765/js/main-page.js | head -1
# 测 main-page.css 可加载
curl -sI http://127.0.0.1:8765/css/main-page.css | head -1
```

预期：3 grep 全有 / 3 个 200 OK

- [ ] **步骤 6：浏览器手测**(可选,你有时间)

打开 `http://127.0.0.1:8765/` → 看到 3 tab 主页 + 3 卡片 + 3 tab(主页/对话/我的) → 点衣橱卡片 → 衣橱 tab 渲染

- [ ] **步骤 7：Commit**

```bash
cd /Users/sxliuyu/repos/laopodada
git add www/index.html www/js/app.js www/css/main-page.css www/js/main-page.js
git commit -m "feat(www): 3 tab 主页 + 3 卡片入口 (G 方案)"
```

---

### 任务 6：前端 — wardrobe.js 加 K3 模式(横条 + AI FAB)

**文件：**
- 修改：`www/js/wardrobe.js` (在 renderWardrobePage 末尾加 FAB + 横条)

- [ ] **步骤 1：找 renderWardrobePage 末尾插入**

修改 `www/js/wardrobe.js`,在 `renderWardrobePage` 函数末尾(`return page;` 之前)加:

```javascript
  // K3 模式: AI 浮动按钮(渐变 ✨)+ 拍照横条(黑色 📷)
  if (typeof AIFab !== 'undefined') {
    AIFab.init('wardrobe', () => {
      AIFab.openSheet({
        title: '✨ AI 穿搭推荐',
        placeholder: '例如:今日约会,天气 25 度...',
        onSubmit: async (text) => {
          const resp = await api.generateOutfit(text);
          const o = resp.outfit;
          const itemsHtml = (o.items || []).map(it =>
            `<img src="${it.url}" alt="${it.category}" style="width:60px;height:60px;object-fit:cover;margin:2px;">`
          ).join('');
          return {
            html: `
              <div><b>搭配:</b> ${o.description}</div>
              <div style="margin-top:6px;">${itemsHtml}</div>
              ${o.tips ? `<div style="margin-top:6px;color:#c44;">💡 ${o.tips}</div>` : ''}
            `
          };
        }
      });
    });

    AIFab.initPhotoBar('wardrobe', () => {
      const input = document.createElement('input');
      input.type = 'file';
      input.accept = 'image/*';
      input.capture = 'environment';
      input.onchange = (e) => {
        const file = e.target.files[0];
        if (!file) return;
        const formData = new FormData();
        formData.append('file', file);
        formData.append('category', 'top');  // 默认分类
        api.postItem(formData).then(() => {
          alert('✓ 上传成功');
          renderWardrobePage();
        }).catch(err => alert('❌ 上传失败: ' + err.message));
      };
      input.click();
    });
  }
```

- [ ] **步骤 2：api.js 加 generateOutfit 函数**

修改 `www/js/api.js` 加:

```javascript
  // AI 穿搭
  async function generateOutfit(text) {
    const url = `${API_BASE}/api/v1/outfits/generate`;
    const r = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ occasion: text }),
    });
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      throw new Error(err.error || `HTTP ${r.status}`);
    }
    return r.json();
  }
```

并 export: `window.api = { ..., generateOutfit };`

- [ ] **步骤 3：本地端到端测**

```bash
# python http.server 还跑着
curl -s http://127.0.0.1:8765/js/wardrobe.js | grep -c "AIFab.init"
curl -s http://127.0.0.1:8765/js/api.js | grep -c "generateOutfit"
```

预期：两个 1+ 匹配

- [ ] **步骤 4：Commit**

```bash
cd /Users/sxliuyu/repos/laopodada
git add www/js/wardrobe.js www/js/api.js
git commit -m "feat(www): 衣橱 K3 模式 (AI 渐变 FAB + 📷 拍照横条)"
```

---

### 任务 7：前端 — recipe.js + health.js 各加 AI FAB(单按钮)

**文件：**
- 修改：`www/js/recipe.js`
- 修改：`www/js/health.js`

- [ ] **步骤 1：recipe.js 加 AI FAB**

修改 `www/js/recipe.js` 的 `renderRecipePage` 末尾加:

```javascript
  // AI 浮动按钮(渐变 ✨ 单按钮,无拍照)
  if (typeof AIFab !== 'undefined') {
    AIFab.init('recipe', () => {
      AIFab.openSheet({
        title: '✨ AI 菜品推荐',
        placeholder: '例如:今天想吃川菜,不要太辣,30 分钟内...',
        onSubmit: async (text) => {
          const resp = await api.generateRecipe(text);
          const r = resp.recipe;
          const ingredients = (r.ingredients || []).join('、');
          const steps = (r.steps || []).map((s, i) => `${i+1}. ${s}`).join('\n');
          return {
            html: `
              <div><b>${r.name || '新菜'}</b> (${r.cuisine || ''} / ${r.difficulty || '简单'})</div>
              <div style="margin-top:6px;"><b>食材:</b> ${ingredients}</div>
              <div style="margin-top:6px;"><b>步骤:</b>\n${steps}</div>
              ${r.cooking_time ? `<div style="margin-top:6px;">⏱ ${r.cooking_time}</div>` : ''}
            `
          };
        }
      });
    });
  }
```

- [ ] **步骤 2：health.js 加 AI FAB**

修改 `www/js/health.js` 的 `renderHealthPage` 末尾加:

```javascript
  // AI 浮动按钮(渐变 ✨ 单按钮,无拍照)
  if (typeof AIFab !== 'undefined') {
    AIFab.init('health', () => {
      AIFab.openSheet({
        title: '✨ AI 健康科普',
        placeholder: '例如:维生素 D 怎么补?孕期要注意什么?',
        onSubmit: async (text) => {
          const resp = await api.generateHealthArticle(text);
          const a = resp.article;
          const sources = (a.sources || []).map(s => `• ${s}`).join('\n');
          const tags = (a.tags || []).map(t => `#${t}`).join(' ');
          return {
            html: `
              <div><b>${a.title || '新文章'}</b> ${tags}</div>
              <div style="margin-top:6px;line-height:1.7;">${a.content || ''}</div>
              ${sources ? `<div style="margin-top:6px;color:#888;font-size:11px;"><b>来源:</b>\n${sources}</div>` : ''}
            `
          };
        }
      });
    });
  }
```

- [ ] **步骤 3：api.js 加 generateRecipe + generateHealthArticle**

```javascript
  // AI 菜谱
  async function generateRecipe(text) {
    const url = `${API_BASE}/api/v1/recipes/generate`;
    const r = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt: text }),
    });
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      throw new Error(err.error || `HTTP ${r.status}`);
    }
    return r.json();
  }

  // AI 健康文章
  async function generateHealthArticle(text) {
    const url = `${API_BASE}/api/v1/health/articles/generate`;
    const r = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic: text }),
    });
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      throw new Error(err.error || `HTTP ${r.status}`);
    }
    return r.json();
  }
```

- [ ] **步骤 4：本地端到端测**

```bash
curl -s http://127.0.0.1:8765/js/recipe.js | grep -c "AIFab.init"
curl -s http://127.0.0.1:8765/js/health.js | grep -c "AIFab.init"
curl -s http://127.0.0.1:8765/js/api.js | grep -c "generateRecipe"
curl -s http://127.0.0.1:8765/js/api.js | grep -c "generateHealthArticle"
```

预期：4 个 1+ 匹配

- [ ] **步骤 5：Commit**

```bash
cd /Users/sxliuyu/repos/laopodada
git add www/js/recipe.js www/js/health.js www/js/api.js
git commit -m "feat(www): 点餐/健康 tab AI 渐变 FAB (单按钮)"
```

---

### 任务 8：前端 — chat.js 顶部加返回主页按钮

**文件：**
- 修改：`www/js/chat.js`

- [ ] **步骤 1：chat.js 顶部 renderChatPage 加返回按钮**

修改 `www/js/chat.js` 的 `renderChatPage` 函数,在 header 区加:

```javascript
  // 顶部返回主页按钮
  const backBtn = `<button class="chat-back-btn" onclick="switchTab('main')">← 主页</button>`;
  // 注入到 chat page 顶部
  const page = document.getElementById('page-chat');
  if (page && !page.querySelector('.chat-back-btn')) {
    const header = document.createElement('div');
    header.className = 'chat-header';
    header.innerHTML = backBtn;
    page.insertBefore(header, page.firstChild);
  }
```

加 CSS (在 ai-fab.css 末尾或新建 chat.css):

```css
.chat-back-btn {
  background: #f5f5f5;
  border: none;
  padding: 8px 14px;
  border-radius: 18px;
  font-size: 13px;
  cursor: pointer;
  margin: 8px;
}
```

- [ ] **步骤 2：Commit**

```bash
cd /Users/sxliuyu/repos/laopodada
git add www/js/chat.js
git commit -m "feat(www): 对话 tab 顶部返回主页按钮"
```

---

### 任务 9：CI 触发 + APK v10 build + 同步 123

**文件：** 无代码改动,纯 CI/CD

- [ ] **步骤 1：push 所有 commit 到 main**

```bash
cd /Users/sxliuyu/repos/laopodada
git push origin main 2>&1 | tail -3
```

预期：`main -> main` 推送成功

- [ ] **步骤 2：等 CI build**

```bash
gh run list --limit 1 --json databaseId,status,conclusion 2>&1
sleep 30
gh run watch <RUN_ID> --exit-status 2>&1 | tail -10
```

预期：`✓ build success` (3-5 分钟)

- [ ] **步骤 3：下载 APK**

```bash
gh run download <RUN_ID> -n laopodada-debug-apk -D /tmp/lpp_pkgs/v10/ 2>&1 | tail -3
ls -la /tmp/lpp_pkgs/v10/
```

预期：3-4 MB APK 文件

- [ ] **步骤 4：scp 到 123 + 公开 URL**

```bash
scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  /tmp/lpp_pkgs/v10/laopodada-debug.apk \
  root@123.57.107.21:/opt/apk-download/laopodada-v10.apk

sshpass -p 'YuJinZe12@.' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  root@123.57.107.21 "chmod 644 /opt/apk-download/laopodada-v10.apk && curl -sk -I https://127.0.0.1:8091/apk/laopodada-v10.apk | head -3"
```

预期：`HTTP/1.1 200 OK` + size 4 MB

- [ ] **步骤 5：跟 www/ 同步到 123**

```bash
sshpass -p 'YuJinZe12@.' rsync -avz --delete \
  -e "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null" \
  /Users/sxliuyu/repos/laopodada/www/ \
  root@123.57.107.21:/data/laopodada/www/

# 除 .brainstorm 目录外
sshpass -p 'YuJinZe12@.' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  root@123.57.107.21 "ls /data/laopodada/www/js/ | head; curl -sk -I https://127.0.0.1:8088/js/wardrobe.js | head -2"
```

预期：12+ JS 文件 + 200 OK

- [ ] **步骤 6：浏览器手测云端**

打开 `https://123.57.107.21:8088/` 看到:
- 3 tab 主页 3 卡片 ✓
- 点衣橱卡片 → 衣橱 tab,看到拍照横条 + AI 渐变 FAB ✓
- 点 AI FAB → 底部 sheet → 输入"今日约会" → 提交 → 等 30-90s → 看到搭配描述 + 衣物图片 ✓

- [ ] **步骤 7：APK URL 报给用户**

```
v10 APK: http://123.57.107.21:8091/apk/laopodada-v10.apk
SHA256: <从 gh run download 算>
```

---

## 自检(写完计划后做)

- [ ] **覆盖度**:spec 10 节是否都有任务?
  - § 3 UI 设计 — 任务 4/5/6/7/8 ✓
  - § 4 API — 任务 1/2/3 ✓
  - § 5 文件结构 — 已列在头部 ✓
  - § 6 错误处理 — 任务 1 测试覆盖 + 任务 2 422/504/500 路径 ✓
  - § 7 测试 — 任务 2/3/5/7 curl + 浏览器 ✓
  - § 8 实施 — 9 个任务按顺序 ✓
  - § 9 风险 — 见任务 9 步骤 1-7 验证流程 ✓
  - § 10 DoD — 9 个任务完成 = 8 项 checkbox ✓
- [ ] **占位符扫描**:无 TODO / 待定 / 后续实现
- [ ] **类型一致**:`AIFab.init` / `AIFab.openSheet` / `AIFab.initPhotoBar` 在任务 4 定义,任务 6/7 引用一致
