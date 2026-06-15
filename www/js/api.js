// API_BASE is set by config.js (loaded first). Defaults to public deployment
// https://123.57.107.21:8088. Override in config.js for local dev.
(function() {
  // No runtime override — config.js is the single source of truth.
  // For local dev, edit config.js to 'http://192.168.1.10:8097' (iOS sim) or
  // 'http://10.0.2.2:8097' (Android emulator).
})();

// Workaround: Capacitor WKWebView fetch on custom scheme blocked by SOP.
// Wrap fetch() to fall back to XHR (not subject to fetch SOP checks).
(function() {
  const origFetch = window.fetch.bind(window);
  window.fetch = function(url, opts) {
    if (typeof url === 'string' && url.startsWith('http')) {
      return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        const method = (opts && opts.method) || 'GET';
        xhr.open(method, url, true);
        if (opts && opts.headers) {
          for (const k in opts.headers) xhr.setRequestHeader(k, opts.headers[k]);
        }
        xhr.onload = () => {
          resolve({
            ok: xhr.status >= 200 && xhr.status < 300,
            status: xhr.status,
            statusText: xhr.statusText,
            json: () => Promise.resolve(JSON.parse(xhr.responseText)),
            text: () => Promise.resolve(xhr.responseText),
          });
        };
        xhr.onerror = () => reject(new TypeError('XHR failed: ' + url));
        xhr.ontimeout = () => reject(new TypeError('XHR timeout: ' + url));
        try { xhr.send(opts && opts.body); } catch (e) { reject(e); }
      });
    }
    return origFetch(url, opts);
  };
})();

async function postItem(formData) {
  const res = await fetch(`${window.API_BASE}/api/v1/items`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ description: res.statusText }));
    throw new Error(err.description || 'upload failed');
  }
  return res.json();
}

async function listItems(category, limit = 50) {
  let url = `${window.API_BASE}/api/v1/items?limit=${limit}`;
  if (category && category !== 'all') url += `&category=${category}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('list items failed');
  return res.json();
}

async function getItem(id) {
  const res = await fetch(`${window.API_BASE}/api/v1/items/${id}`);
  if (!res.ok) throw new Error('get item failed');
  return res.json();
}

async function deleteItem(id) {
  const res = await fetch(`${window.API_BASE}/api/v1/items/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('delete failed');
  return res.json();
}

async function recommendOutfit(occasion, season, weather, limit = 3) {
  const res = await fetch(`${window.API_BASE}/api/v1/outfits/recommend`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ occasion, season, weather, limit }),
  });
  if (!res.ok) throw new Error('recommend failed');
  return res.json();
}

async function getOutfit(id) {
  const res = await fetch(`${window.API_BASE}/api/v1/outfits/${id}`);
  if (!res.ok) throw new Error('get outfit failed');
  return res.json();
}

async function feedbackOutfit(id, score) {
  const res = await fetch(`${window.API_BASE}/api/v1/outfits/${id}/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ score }),
  });
  if (!res.ok) throw new Error('feedback failed');
  return res.json();
}

async function listOutfits(limit = 20) {
  const res = await fetch(`${window.API_BASE}/api/v1/outfits?limit=${limit}`);
  if (!res.ok) throw new Error('list outfits failed');
  return res.json();
}

// ===== 菜谱 =====
async function listRecipes(category, difficulty, tag, limit = 50) {
  const params = new URLSearchParams();
  if (category) params.set('category', category);
  if (difficulty) params.set('difficulty', difficulty);
  if (tag) params.set('tag', tag);
  params.set('limit', String(limit));
  const res = await fetch(`${window.API_BASE}/api/v1/recipes?` + params.toString());
  if (!res.ok) throw new Error('list recipes failed');
  return res.json();
}
async function getRecipe(id) {
  const res = await fetch(`${window.API_BASE}/api/v1/recipes/${id}`);
  if (!res.ok) throw new Error('get recipe failed');
  return res.json();
}
async function createRecipe(data) {
  const res = await fetch(`${window.API_BASE}/api/v1/recipes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('create recipe failed');
  return res.json();
}
async function deleteRecipe(id) {
  const res = await fetch(`${window.API_BASE}/api/v1/recipes/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('delete recipe failed');
  return res.json();
}

// ===== 健康科普 =====
async function listHealthArticles(category, limit = 50) {
  const params = new URLSearchParams();
  if (category) params.set('category', category);
  params.set('limit', String(limit));
  const res = await fetch(`${window.API_BASE}/api/v1/health/articles?` + params.toString());
  if (!res.ok) throw new Error('list articles failed');
  return res.json();
}
async function getHealthArticle(id) {
  const res = await fetch(`${window.API_BASE}/api/v1/health/articles/${id}`);
  if (!res.ok) throw new Error('get article failed');
  return res.json();
}

// ===== AI 咨询(走 nginx 8088 反代到 atlas 18793) =====
async function chatWithAI(message, sessionId) {
  const res = await fetch(`${window.API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, session_id: sessionId }),
  });
  if (!res.ok) throw new Error(`AI chat failed: HTTP ${res.status}`);
  const data = await res.json();
  // atlas 返 {response, session_id}, 前端用 resp.reply 兜底兼容
  return { reply: data.response || data.reply || data.content || data.message || '(无回复)' };
}
async function getChatHistory(sessionId, limit = 50) {
  const res = await fetch(`${window.API_BASE}/api/chat/history?session_id=${encodeURIComponent(sessionId)}&limit=${limit}`);
  if (!res.ok) throw new Error(`history failed: HTTP ${res.status}`);
  return res.json();
}

// ===== AI 生成 =====
/**
 * AI 生成菜谱
 * @param {string} query - 菜名或场景(如"西红柿炒蛋"或"简单快手晚饭")
 * @returns {Promise<{recipe: object}>} - 生成的菜谱对象(已存 DB)
 */
async function generateRecipe(query) {
  const res = await fetch(`${window.API_BASE}/api/v1/recipes/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error || `生成失败: HTTP ${res.status}`);
  }
  return data;
}

/**
 * AI 生成健康文章
 * @param {string} topic - 主题(如"维生素 D 补充")
 * @param {string} [category] - nutrition/exercise/disease/prevention/mental/female
 * @returns {Promise<{article: object}>} - 生成的文章对象
 */
async function generateHealthArticle(topic, category = '') {
  const body = { topic };
  if (category) body.category = category;
  const res = await fetch(`${window.API_BASE}/api/v1/health/articles/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error || `生成失败: HTTP ${res.status}`);
  }
  return data;
}