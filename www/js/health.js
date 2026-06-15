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
    <div class="filter-bar" id="health-cat-bar"></div>
    <div style="padding:8px 12px;">
      <input type="search" id="health-search" placeholder="搜索文章..."
        style="flex:1;padding:6px 10px;border:1px solid #ddd;border-radius:8px;font-size:13px;width:100%;" oninput="healthFilter.search=this.value;renderHealthList(healthCache)">
    </div>
    <div id="health-list">加载中…</div>
  `;
  renderHealthCatBar();
  loadHealthArticles();
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