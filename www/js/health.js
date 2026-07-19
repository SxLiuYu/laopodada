/* health.js — 健康知识科普 (v2 数据库持久化) */
let healthFilter = { category: '', search: '' };
let healthCache = [];  // localStorage 缓存
let healthReadIds = new Set();  // 已读标记

const HEALTH_CATEGORIES = [
  { key: '',         label: '全部' },
  { key: 'nutrition',label: '🥗 营养' },
  { key: 'exercise', label: '🏃 运动' },
  { key: 'disease',  label: '🩺 慢病' },
  { key: 'mental',   label: '🧘 心理' },
  { key: 'female',   label: '🌸 女性' },
  { key: 'prevention', label: '💉 预防' },
];

function renderHealthPage() {
  const page = document.getElementById('page-health');
  page.innerHTML = `
    <div class="page-header">📚 健康知识</div>
    <div style="padding:var(--sp-2) var(--sp-3);background:var(--bg-white);border-bottom:1px solid var(--border);">
      <button onclick="toggleHealthAI()" style="width:100%;background:none;border:none;padding:var(--sp-2) 0;display:flex;align-items:center;justify-content:space-between;cursor:pointer;font-family:var(--font-sans);">
        <span style="font-size:var(--fs-md);color:var(--text-secondary);">✨ AI 生成健康文章</span>
        <span id="health-ai-arrow" style="color:var(--text-hint);font-size:12px;transition:transform .2s;">▶</span>
      </button>
      <div id="health-ai-body" style="display:none;">
        <div class="ai-gen-bar" style="padding:0 0 var(--sp-2);">
          <input id="health-ai-input" class="form-input" type="text" placeholder="想了解啥?输入健康主题" maxlength="100">
          <select id="health-ai-cat" class="form-select" style="width:auto;flex:none;">
            <option value="">自动</option>
            <option value="nutrition">🥗 营养</option>
            <option value="exercise">🏃 运动</option>
            <option value="disease">🩺 慢病</option>
            <option value="prevention">💉 预防</option>
            <option value="mental">🧘 心理</option>
            <option value="female">🌸 女性</option>
          </select>
          <button id="health-ai-btn" class="ai-btn" onclick="genHealthArticle()">✨ 生成</button>
        </div>
        <p class="ai-hint">💡 LLM 需 60-90 秒</p>
        <div id="health-ai-result" class="ai-result"></div>
      </div>
    </div>
    <div class="filter-bar" id="health-cat-bar"></div>
    <div style="padding:var(--sp-2) var(--sp-3);">
      <input type="search" id="health-search" class="form-input" placeholder="搜索文章..."
        oninput="healthFilter.search=this.value;renderHealthList(healthCache)">
    </div>
    <div id="health-list"></div>
  `;
  renderHealthCatBar();

  // Load read status from localStorage
  try {
    healthReadIds = new Set(JSON.parse(localStorage.getItem('health_read_ids') || '[]'));
  } catch (e) {}

  // Show skeleton while loading
  renderListSkeleton('health-list', 4);
  loadHealthArticlesDB();

  // Pull-to-refresh (native only)
  enablePullRefresh(loadHealthArticlesDB);

  // AI 浮动按钮
  if (typeof AIFab !== 'undefined') {
    AIFab.init('health', () => {
      AIFab.openSheet({
        title: '✨ AI 健康科普',
        placeholder: '例如:维生素 D 怎么补?孕期要注意什么?',
        onSubmit: async (text) => {
          const resp = await api.health.generateHealthArticle(text);
          const a = resp.article;
          const tags = (a.tags || []).map(t => `#${t}`).join(' ');
          return {
            html: `
              <div><b>${escapeHtml(a.title || '新文章')}</b> ${tags ? escapeHtml(tags) : ''}</div>
              <div style="margin-top:6px;color:var(--text-secondary);">${escapeHtml(a.summary || '')}</div>
              <div style="margin-top:6px;line-height:1.7;white-space:pre-wrap;">${escapeHtml(a.content || '')}</div>
              ${a.source ? `<div style="margin-top:6px;color:var(--text-hint);font-size:var(--fs-sm);">📚 ${escapeHtml(a.source)} · ⏱ ${a.read_minutes || 5} 分钟</div>` : ''}
            `
          };
        }
      });
    });
  }
}

function renderHealthCatBar() {
  const catBar = document.getElementById('health-cat-bar');
  if (!catBar) return;
  catBar.innerHTML = HEALTH_CATEGORIES.map(c => `
    <button class="filter-chip${healthFilter.category === c.key ? ' active' : ''}"
      data-cat="${c.key}" onclick="setHealthCategory('${c.key}')">${c.label}</button>
  `).join('');
}

async function loadHealthArticlesDB() {
  const list = document.getElementById('health-list');
  if (!list) return;
  renderListSkeleton('health-list', 3);
  
  try {
    // Try database API first
    const data = await api.health.listHealthArticles(healthFilter.category || undefined);
    healthCache = data.articles || [];
    localStorage.setItem('health_articles', JSON.stringify(healthCache));
    renderHealthList(healthCache);
  } catch (e) {
    // Fallback to localStorage cache
    try {
      const cached = localStorage.getItem('health_articles');
      if (cached) healthCache = JSON.parse(cached);
    } catch (f) {}
    if (healthCache.length) {
      renderHealthList(healthCache);
      toast('离线模式:显示缓存');
    } else {
      list.innerHTML = '<div class="empty-state"><span class="emoji">❌</span>加载失败 <button onclick="loadHealthArticlesDB()" style="margin-left:8px;padding:4px 12px;background:var(--primary);color:#fff;border:none;border-radius:var(--r-sm);cursor:pointer;">重试</button></div>';
    }
  }
}

function renderHealthList(articles) {
  // 过滤 search
  let filtered = articles;
  if (healthFilter.search) {
    const q = healthFilter.search.toLowerCase();
    filtered = articles.filter(a => 
      (a.title||'').toLowerCase().includes(q) || 
      (a.summary||'').toLowerCase().includes(q)
    );
  }
  // 渲染卡片
  const list = document.getElementById('health-list');
  if (!filtered.length) {
    list.innerHTML = '<div class="empty-state"><span class="emoji">📭</span>没有匹配的文章</div>';
    return;
  }
  list.innerHTML = filtered.map(a => {
    const isRead = healthReadIds.has(a.id);
    return `
    <div class="article-card${isRead ? ' article-read' : ''}" onclick="openHealthArticle('${a.id}')">
      <div class="article-cat">${categoryEmoji(a.category)} ${a.category || ''}</div>
      <div class="article-title">${escapeHtml(a.title)}</div>
      <div class="article-summary">${escapeHtml(a.summary || '')}</div>
      <div class="article-meta">⏱ ${a.read_minutes || 5} 分钟 · ${(a.tags||[]).join(' / ')}</div>
    </div>`;
  }).join('');
}

function setHealthCategory(cat) {
  healthFilter.category = cat;
  renderHealthCatBar();
  loadHealthArticlesDB();
}

function openHealthArticle(id) {
  const a = healthCache.find(x => x.id == id);
  if (!a) return;
  // 标记已读
  try {
    const readIds = JSON.parse(localStorage.getItem('health_read_ids') || '[]');
    if (!readIds.includes(id)) { 
      readIds.push(id); 
      localStorage.setItem('health_read_ids', JSON.stringify(readIds));
      healthReadIds.add(id);
    }
  } catch(e) {}
  
  // 刷新列表显示已读状态
  renderHealthList(healthCache);
  
  // 弹 modal 显示全文
  const modal = document.createElement('div');
  modal.className = 'overlay';
  modal.innerHTML = `
    <div class="modal-box" style="max-width:90%;max-height:85vh;">
      <div class="modal-box-header">
        <div class="modal-box-title">${escapeHtml(a.title)}</div>
        <button class="modal-box-close" onclick="this.closest('.overlay').remove()">×</button>
      </div>
      <div class="modal-box-body" style="line-height:1.7;">
        <p style="margin-bottom:10px;">${simpleMarkdown(a.content)}</p>
      </div>
      <div class="modal-box-footer" style="display:flex;justify-content:space-between;align-items:center;">
        <span>📖 ${escapeHtml(a.source || '未知')} · ${a.read_minutes || 5} 分钟</span>
      </div>
    </div>`;
  modal.addEventListener('click', e => { if (e.target === modal) modal.remove(); });
  document.body.appendChild(modal);
}

function categoryEmoji(cat) {
  return ({nutrition:'🥗',exercise:'🏃',disease:'🩺',mental:'🧘',female:'🌸',prevention:'💉'})[cat] || '📄';
}

/* ── 简易 Markdown→HTML ── */
function simpleMarkdown(text) {
  if (!text) return '';
  return escapeHtml(text)
    .replace(/^### (.+)$/gm, '<h4 style="margin:12px 0 6px;font-size:14px;font-weight:600;">$1</h4>')
    .replace(/^## (.+)$/gm, '<h3 style="margin:14px 0 6px;font-size:15px;font-weight:600;">$1</h3>')
    .replace(/^# (.+)$/gm, '<h2 style="margin:16px 0 8px;font-size:16px;font-weight:700;">$1</h2>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/^[•\-\*] (.+)$/gm, '<li style="margin-left:16px;margin-bottom:3px;">$1</li>')
    .replace(/^(\d+)[.、)] (.+)$/gm, '<li style="margin-left:16px;margin-bottom:3px;">$1. $2</li>')
    .replace(/\n\n/g, '</p><p style="margin-bottom:10px;">')
    .replace(/\n/g, '<br>');
}

function prependArticleToList(article) {
  const list = document.getElementById('health-list');
  const empty = list.querySelector('.empty-state');
  if (empty) empty.remove();
  const div = document.createElement('div');
  div.className = 'article-card ai-card';
  div.onclick = () => openHealthArticle(article.id);
  div.innerHTML = `
    <div class="article-cat">${categoryEmoji(article.category)} ${article.category || ''} <span class="ai-tag" style="font-size:10px;margin-left:4px;">AI</span></div>
    <div class="article-title">✨ ${escapeHtml(article.title)}</div>
    <div class="article-summary">${escapeHtml(article.summary || '')}</div>
    <div class="article-meta">⏱ ${article.read_minutes || 5} 分钟</div>`;
  list.insertBefore(div, list.firstChild);
}

/* ── AI 生成文章 ── */
async function genHealthArticle() {
  const input = document.getElementById('health-ai-input');
  const topic = input.value.trim();
  const category = document.getElementById('health-ai-cat').value;
  if (!topic) { toast('请输入健康主题'); return; }
  const btn = document.getElementById('health-ai-btn');
  const resultBox = document.getElementById('health-ai-result');
  btn.disabled = true;
  btn.textContent = 'AI 在写文章...';
  resultBox.innerHTML = '<div class="ai-loading">🤔 AI 思考中,请耐心等待(约 60-90 秒)...</div>';
  try {
    const data = await api.health.generateHealthArticle(topic, category);
    const a = data.article;
    // 添加到缓存
    healthCache.unshift(a);
    localStorage.setItem('health_articles', JSON.stringify(healthCache));
    
    resultBox.innerHTML = `
      <div class="ai-result-card">
        <div class="ai-result-header">
          <h3>✨ ${escapeHtml(a.title)}</h3>
          <span class="ai-tag">AI 生成</span>
        </div>
        <p class="ai-summary">${escapeHtml(a.summary || '')}</p>
        <h4>正文</h4>
        <div class="ai-content" style="white-space:normal;">${simpleMarkdown(a.content || '')}</div>
        <p class="ai-source">📚 ${escapeHtml(a.source || '未知')}</p>
        <p class="ai-meta">⏱ ${a.read_minutes || 5} 分钟阅读 · 🏷 ${(a.tags || []).map(t => escapeHtml(t)).join(' / ')}</p>
      </div>`;
    prependArticleToList(a);
    input.value = '';
  } catch (e) {
    resultBox.innerHTML = `<div class="ai-error">❌ ${escapeHtml(e.message)}</div>`;
  } finally {
    btn.disabled = false;
    btn.textContent = '✨ 生成';
  }
}

/* ── 折叠切换 ── */
function toggleHealthAI() {
  const body = document.getElementById('health-ai-body');
  const arrow = document.getElementById('health-ai-arrow');
  if (body.style.display === 'none') {
    body.style.display = 'block';
    arrow.style.transform = 'rotate(90deg)';
  } else {
    body.style.display = 'none';
    arrow.style.transform = 'rotate(0deg)';
  }
}
