/* health.js — 健康知识科普 */
let healthFilter = { category: '', search: '' };
let healthCache = [];  // localStorage 缓存

const HEALTH_CATEGORIES = [
  { key: '',         label: '全部' },
  { key: 'nutrition',label: '🥗 营养' },
  { key: 'exercise', label: '🏃 运动' },
  { key: 'disease',  label: '🩺 慢病' },
  { key: 'mental',   label: '🧘 心理' },
  { key: 'female',   label: '🌸 女性' },
];

function renderHealthPage() {
  const page = document.getElementById('page-health');
  page.innerHTML = `
    <div class="page-header">📚 健康知识</div>
    <div class="ai-gen-bar">
      <input id="health-ai-input" type="text" placeholder="想了解啥?输入健康主题(例:孕期叶酸 / 失眠调理)" maxlength="100">
      <select id="health-ai-cat" style="padding:6px 8px;border:1px solid #ddd;border-radius:8px;font-size:13px;">
        <option value="nutrition">🥗 营养</option>
        <option value="exercise">🏃 运动</option>
        <option value="disease">🩺 慢病</option>
        <option value="prevention">💉 预防</option>
        <option value="mental">🧘 心理</option>
        <option value="female">🌸 女性</option>
      </select>
      <button id="health-ai-btn" class="ai-btn">✨ AI 生成</button>
    </div>
    <p class="ai-hint">💡 LLM 需 60-90 秒,内容基于权威医学常识</p>
    <div id="health-ai-result" class="ai-result hidden"></div>
    <div class="filter-bar" id="health-cat-bar"></div>
    <div style="padding:8px 12px;">
      <input type="search" id="health-search" placeholder="搜索文章..."
        style="flex:1;padding:6px 10px;border:1px solid #ddd;border-radius:8px;font-size:13px;width:100%;" oninput="healthFilter.search=this.value;renderHealthList(healthCache)">
    </div>
    <div id="health-list">加载中…</div>
  `;
  renderHealthCatBar();

  // AI 生成按钮
  document.getElementById('health-ai-btn').onclick = async () => {
    const input = document.getElementById('health-ai-input');
    const topic = input.value.trim();
    const category = document.getElementById('health-ai-cat').value;
    if (!topic) {
      alert('请输入健康主题');
      return;
    }
    const btn = document.getElementById('health-ai-btn');
    const resultBox = document.getElementById('health-ai-result');
    btn.disabled = true;
    btn.textContent = 'AI 在写文章... 60-90s';
    resultBox.classList.remove('hidden');
    resultBox.innerHTML = '<div class="ai-loading">🤔 AI 思考中,请耐心等待(约 60-90 秒)...</div>';

    try {
      const data = await generateHealthArticle(topic, category);
      const a = data.article;
      resultBox.innerHTML = `
        <div class="ai-result-card">
          <div class="ai-result-header">
            <h3>✨ ${escapeHtml(a.title)}</h3>
            <span class="ai-tag">AI 生成</span>
          </div>
          <p class="ai-summary">${escapeHtml(a.summary || '')}</p>
          <h4>正文</h4>
          <pre class="ai-content">${escapeHtml(a.content || '')}</pre>
          <p class="ai-source">📚 ${escapeHtml(a.source || '未知')}</p>
          <p class="ai-meta">⏱ ${a.read_minutes || 5} 分钟阅读 · 🏷 ${(a.tags || []).map(t => escapeHtml(t)).join(' / ')}</p>
        </div>
      `;
      prependArticleToList(a);
      input.value = '';
    } catch (e) {
      resultBox.innerHTML = `<div class="ai-error">❌ ${escapeHtml(e.message)}</div>`;
    } finally {
      btn.disabled = false;
      btn.textContent = '✨ AI 生成';
    }
  };

  loadHealthArticles();

  // AI 浮动按钮(渐变 ✨ 单按钮,无拍照)
  if (typeof AIFab !== 'undefined') {
    AIFab.init('health', () => {
      AIFab.openSheet({
        title: '✨ AI 健康科普',
        placeholder: '例如:维生素 D 怎么补?孕期要注意什么?',
        onSubmit: async (text) => {
          const resp = await api.generateHealthArticle(text);
          const a = resp.article;
          const tags = (a.tags || []).map(t => `#${t}`).join(' ');
          return {
            html: `
              <div><b>${escapeHtml(a.title || '新文章')}</b> ${tags ? escapeHtml(tags) : ''}</div>
              <div style="margin-top:6px;color:#555;">${escapeHtml(a.summary || '')}</div>
              <div style="margin-top:6px;line-height:1.7;white-space:pre-wrap;">${escapeHtml(a.content || '')}</div>
              ${a.source ? `<div style="margin-top:6px;color:#888;font-size:11px;">📚 ${escapeHtml(a.source)} · ⏱ ${a.read_minutes || 5} 分钟</div>` : ''}
            `
          };
        }
      });
    });
  }
}

function renderHealthCatBar() {
  const catBar = document.getElementById('health-cat-bar');
  catBar.innerHTML = HEALTH_CATEGORIES.map(c => `
    <button class="filter-chip${healthFilter.category === c.key ? ' active' : ''}"
      data-cat="${c.key}" onclick="setHealthCategory('${c.key}')">${c.label}</button>
  `).join('');
}

async function loadHealthArticles() {
  const list = document.getElementById('health-list');
  list.innerHTML = '<div class="empty-state"><span class="emoji">⏳</span>加载中…</div>';
  try {
    // 先读缓存
    const cached = localStorage.getItem('health_articles');
    if (cached) healthCache = JSON.parse(cached);
    // 拉新
    const data = await listHealthArticles(healthFilter.category || undefined);
    healthCache = data.articles || [];
    localStorage.setItem('health_articles', JSON.stringify(healthCache));
    renderHealthList(healthCache);
  } catch (e) {
    // 离线降级
    if (healthCache.length) {
      renderHealthList(healthCache);
      toast('离线模式:显示缓存');
    } else {
      list.innerHTML = '<div class="empty-state"><span class="emoji">❌</span>加载失败 <button onclick="loadHealthArticles()" style="margin-left:8px;padding:4px 12px;background:#FF8C94;color:#fff;border:none;border-radius:8px;cursor:pointer;">重试</button></div>';
    }
  }
}

function renderHealthList(articles) {
  // 过滤 search
  let filtered = articles;
  if (healthFilter.search) {
    const q = healthFilter.search.toLowerCase();
    filtered = articles.filter(a => a.title.toLowerCase().includes(q) || (a.summary||'').toLowerCase().includes(q));
  }
  // 渲染卡片(列表)
  const list = document.getElementById('health-list');
  if (!filtered.length) {
    list.innerHTML = '<div class="empty-state"><span class="emoji">📭</span>没有匹配的文章</div>';
    return;
  }
  list.innerHTML = filtered.map(a => `
    <div class="article-card" onclick="openHealthArticle('${a.id}')">
      <div class="article-cat">${categoryEmoji(a.category)} ${a.category || ''}</div>
      <div class="article-title">${escapeHtml(a.title)}</div>
      <div class="article-summary">${escapeHtml(a.summary || '')}</div>
      <div class="article-meta">⏱ ${a.read_minutes || 5} 分钟 · ${(a.tags||[]).join(' / ')}</div>
    </div>
  `).join('');
}

function setHealthCategory(cat) {
  healthFilter.category = cat;
  renderHealthCatBar();
  loadHealthArticles();
}

function openHealthArticle(id) {
  const a = healthCache.find(x => x.id == id);
  if (!a) return;
  // 标记已读
  try {
    const readIds = JSON.parse(localStorage.getItem('health_read_ids') || '[]');
    if (!readIds.includes(id)) { readIds.push(id); localStorage.setItem('health_read_ids', JSON.stringify(readIds)); }
  } catch(e) {}
  // 弹 modal 显示全文
  const modal = document.createElement('div');
  modal.className = 'modal-mask';
  modal.innerHTML = `
    <div class="modal-content">
      <div class="modal-header">
        <div class="modal-title">${escapeHtml(a.title)}</div>
        <button onclick="this.closest('.modal-mask').remove()">✕</button>
      </div>
      <div class="modal-body" style="white-space:pre-wrap;line-height:1.6;">${escapeHtml(a.content)}</div>
      <div class="modal-footer">📖 来源:${escapeHtml(a.source || '未知')} · ${a.read_minutes || 5} 分钟阅读</div>
    </div>
  `;
  document.body.appendChild(modal);
}

function categoryEmoji(cat) {
  return ({nutrition:'🥗',exercise:'🏃',disease:'🩺',mental:'🧘',female:'🌸'})[cat] || '📄';
}
function escapeHtml(s) {
  return String(s||'').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]);
}

function prependArticleToList(article) {
  const list = document.getElementById('health-list');
  // 移除 empty state
  const empty = list.querySelector('.empty-state');
  if (empty) empty.remove();
  const div = document.createElement('div');
  div.className = 'article-card ai-card';
  div.onclick = () => openHealthArticle(article.id);
  div.innerHTML = `
    <div class="article-cat">${categoryEmoji(article.category)} ${article.category || ''} <span class="ai-tag" style="font-size:10px;margin-left:4px;">AI</span></div>
    <div class="article-title">✨ ${escapeHtml(article.title)}</div>
    <div class="article-summary">${escapeHtml(article.summary || '')}</div>
    <div class="article-meta">⏱ ${article.read_minutes || 5} 分钟</div>
  `;
  list.insertBefore(div, list.firstChild);
}