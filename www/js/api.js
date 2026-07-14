// API_BASE is set by config.js (loaded first). Defaults to public deployment
// https://123.57.107.21:8088. Override in config.js for local dev.

/* ── XHR→fetch fallback wrapper ── */
(function() {
  // 仅在 Capacitor 环境需要 XHR fallback (WKWebView custom scheme SOP 限制)
  const isCapacitor = window.Capacitor && window.Capacitor.isNativePlatform && window.Capacitor.isNativePlatform();
  if (!isCapacitor) return;

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
        xhr.onerror = () => {
          console.warn('[api] XHR fail, fallback to native fetch:', url);
          origFetch(url, opts).then(resolve, reject);
        };
        xhr.ontimeout = () => reject(new TypeError('XHR timeout: ' + url));
        try { xhr.send(opts && opts.body); } catch (e) { reject(e); }
      });
    }
    return origFetch(url, opts);
  };
})();

/* ── Dev mode mock data ── */
function _mockResponse(data, delay = 300) {
  return new Promise(resolve => setTimeout(() => resolve(data), delay));
}

function _devGuard(fnName) {
  if (!window.IS_DEV) return false; // 非 dev 模式，正常发请求
  console.log(`[dev] ${fnName} → mock`);
  return true;
}

/* ════════════════════════════════════════════
   衣橱 API
   ════════════════════════════════════════════ */

async function postItem(formData) {
  if (_devGuard('postItem')) return _mockResponse({ item: { id: 'mock-1', title: '白T恤', category: 'top', color: '白', season: 'summer' } });
  const res = await fetch(`${window.API_BASE}/api/v1/items`, { method: 'POST', body: formData });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ description: res.statusText }));
    throw new Error(err.description || 'upload failed');
  }
  return res.json();
}

async function listItems(category, limit = 50) {
  if (_devGuard('listItems')) return _mockResponse({ count: 0, items: [] });
  let url = `${window.API_BASE}/api/v1/items?limit=${limit}`;
  if (category && category !== 'all') url += `&category=${category}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('list items failed');
  return res.json();
}

async function getItem(id) {
  if (_devGuard('getItem')) return _mockResponse({ item: { id, title: '示例', category: 'top', color: '黑' } });
  const res = await fetch(`${window.API_BASE}/api/v1/items/${id}`);
  if (!res.ok) throw new Error('get item failed');
  return res.json();
}

async function deleteItem(id) {
  if (_devGuard('deleteItem')) return _mockResponse({ ok: true });
  const res = await fetch(`${window.API_BASE}/api/v1/items/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('delete failed');
  return res.json();
}

async function updateItem(id, data) {
  if (_devGuard('updateItem')) return _mockResponse({ item: { id, ...data }, ok: true });
  const res = await fetch(`${window.API_BASE}/api/v1/items/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('update failed');
  return res.json();
}

async function autoTag(file) {
  if (_devGuard('autoTag')) return _mockResponse({ category: 'top', color: '白', season: 'summer', title: '白色上衣', confidence: 0.9 });
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${window.API_BASE}/api/v1/items/auto-tag`, { method: 'POST', body: form });
  if (!res.ok) throw new Error('auto-tag failed');
  return res.json();
}

/* ════════════════════════════════════════════
   穿搭 API
   ════════════════════════════════════════════ */

async function recommendOutfit(occasion, season, weather, limit = 3) {
  if (_devGuard('recommendOutfit')) return _mockResponse({ outfits: [], used_strategy: ['rule', 'color_harmony'] });
  const res = await fetch(`${window.API_BASE}/api/v1/outfits/recommend`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ occasion, season, weather, limit }),
  });
  if (!res.ok) throw new Error('recommend failed');
  return res.json();
}

async function getOutfit(id) {
  if (_devGuard('getOutfit')) return _mockResponse({ outfit: { id, items: [] } });
  const res = await fetch(`${window.API_BASE}/api/v1/outfits/${id}`);
  if (!res.ok) throw new Error('get outfit failed');
  return res.json();
}

async function feedbackOutfit(id, score) {
  if (_devGuard('feedbackOutfit')) return _mockResponse({ ok: true, outfit_id: id, score });
  const res = await fetch(`${window.API_BASE}/api/v1/outfits/${id}/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ score }),
  });
  if (!res.ok) throw new Error('feedback failed');
  return res.json();
}

async function generateOutfit(occasion) {
  if (_devGuard('generateOutfit')) return _mockResponse({ outfit: { items: [], description: '(dev模式) 连接服务器后可用', tips: '' } });
  const res = await fetch(`${window.API_BASE}/api/v1/outfits/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ occasion: occasion || 'casual' }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `HTTP ${res.status}`);
  }
  return res.json();
}

async function listOutfits(limit = 20) {
  if (_devGuard('listOutfits')) return _mockResponse({ outfits: [] });
  const res = await fetch(`${window.API_BASE}/api/v1/outfits?limit=${limit}`);
  if (!res.ok) throw new Error('list outfits failed');
  return res.json();
}

/* ════════════════════════════════════════════
   菜谱 API
   ════════════════════════════════════════════ */

async function listRecipes(category, difficulty, tag, limit = 50) {
  if (_devGuard('listRecipes')) return _mockResponse({ count: 0, recipes: [] });
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
  if (_devGuard('getRecipe')) return _mockResponse({ recipe: { id, title: '示例菜谱' } });
  const res = await fetch(`${window.API_BASE}/api/v1/recipes/${id}`);
  if (!res.ok) throw new Error('get recipe failed');
  return res.json();
}

async function createRecipe(data) {
  if (_devGuard('createRecipe')) return _mockResponse({ recipe: { id: 'mock-1', title: '示例菜谱' } });
  const res = await fetch(`${window.API_BASE}/api/v1/recipes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('create recipe failed');
  return res.json();
}

async function deleteRecipe(id) {
  if (_devGuard('deleteRecipe')) return _mockResponse({ ok: true });
  const res = await fetch(`${window.API_BASE}/api/v1/recipes/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('delete recipe failed');
  return res.json();
}

/* ════════════════════════════════════════════
   AI 对话 API
   ════════════════════════════════════════════ */

async function chatWithAI(message, sessionId, context = []) {
  if (_devGuard('chatWithAI')) return _mockResponse({ reply: '(dev模式) 连接服务器后可用' });
  const res = await fetch(`${window.API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, session_id: sessionId, context }),
  });
  if (!res.ok) throw new Error(`AI chat failed: HTTP ${res.status}`);
  const data = await res.json();
  return { reply: data.response || data.reply || data.content || data.message || '(无回复)' };
}

async function getChatHistory(sessionId, limit = 50) {
  if (_devGuard('getChatHistory')) return _mockResponse({ messages: [] });
  const res = await fetch(`${window.API_BASE}/api/chat/history?session_id=${encodeURIComponent(sessionId)}&limit=${limit}`);
  if (!res.ok) throw new Error(`history failed: HTTP ${res.status}`);
  return res.json();
}

/* ════════════════════════════════════════════
   AI 生成 API
   ════════════════════════════════════════════ */

async function generateRecipe(query) {
  if (_devGuard('generateRecipe')) return _mockResponse({ recipe: { id: 'mock', title: '示例菜谱', ingredients: [], steps: [] } });
  const res = await fetch(`${window.API_BASE}/api/v1/recipes/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `生成失败: HTTP ${res.status}`);
  return data;
}

/* ════════════════════════════════════════════
   记账 API
   ════════════════════════════════════════════ */

async function listExpenses(category, month, limit = 100) {
  if (_devGuard('listExpenses')) return _mockResponse({ count: 0, expenses: [], total: 0 });
  const params = new URLSearchParams();
  if (category) params.set('category', category);
  if (month) params.set('month', month);
  params.set('limit', String(limit));
  const res = await fetch(`${window.API_BASE}/api/v1/expenses?` + params.toString());
  if (!res.ok) throw new Error('list expenses failed');
  return res.json();
}

async function expensesSummary(month) {
  if (_devGuard('expensesSummary')) return _mockResponse({ month, total: 0, breakdown: [] });
  const params = new URLSearchParams();
  if (month) params.set('month', month);
  const res = await fetch(`${window.API_BASE}/api/v1/expenses/summary?` + params.toString());
  if (!res.ok) throw new Error('summary failed');
  return res.json();
}

async function createExpense(data) {
  if (_devGuard('createExpense')) return _mockResponse({ expense: { id: 'mock', ...data } });
  const res = await fetch(`${window.API_BASE}/api/v1/expenses`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.description || 'create expense failed');
  }
  return res.json();
}

async function deleteExpense(id) {
  if (_devGuard('deleteExpense')) return _mockResponse({ ok: true });
  const res = await fetch(`${window.API_BASE}/api/v1/expenses/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('delete expense failed');
  return res.json();
}

/* ════════════════════════════════════════════
   window.api 命名空间
   ════════════════════════════════════════════ */

window.api = {
  // 衣橱
  postItem, listItems, getItem, deleteItem, updateItem, autoTag,
  // 穿搭
  recommendOutfit, generateOutfit, getOutfit, feedbackOutfit, listOutfits,
  // 菜谱
  listRecipes, getRecipe, createRecipe, deleteRecipe, generateRecipe,
  // 对话
  chatWithAI, getChatHistory,
  // 记账
  listExpenses, expensesSummary, createExpense, deleteExpense,
};
