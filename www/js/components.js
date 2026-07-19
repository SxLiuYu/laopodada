/* 老婆哒哒 - 公共 UI 组件模块 - www/js/components.js */
/* 提供可复用的 UI 组件创建函数 */

/* ── 创建底部弹窗(Bottom Sheet) ── */
function createBottomSheet(title, contentHtml, opts = {}) {
  const overlay = document.createElement('div');
  overlay.className = 'overlay overlay-bottom';
  overlay.innerHTML = `
    <div class="bottom-sheet">
      <div class="sheet-header">
        <div class="sheet-title">${title}</div>
        <button class="modal-box-close" onclick="this.closest('.overlay').remove()">×</button>
      </div>
      <div class="sheet-content">${contentHtml}</div>
    </div>`;

  // 点击遮罩关闭
  overlay.addEventListener('click', e => {
    if (e.target === overlay) overlay.remove();
  });

  document.body.appendChild(overlay);
  return overlay;
}

/* ── 创建模态弹窗(Modal) ── */
function createModal2(title, contentHtml, opts = {}) {
  const overlay = document.createElement('div');
  overlay.className = 'overlay';
  const maxWidth = opts.maxWidth || '400px';
  overlay.innerHTML = `
    <div class="modal-box" style="max-width:${maxWidth}">
      ${title ? `
      <div class="modal-box-header">
        <div class="modal-box-title">${title}</div>
        <button class="modal-box-close" onclick="this.closest('.overlay').remove()">×</button>
      </div>` : ''}
      <div class="modal-box-body">${contentHtml}</div>
    </div>`;

  // 点击遮罩关闭
  overlay.addEventListener('click', e => {
    if (e.target === overlay) overlay.remove();
  });

  document.body.appendChild(overlay);
  return overlay;
}

/* ── 创建空状态组件 ── */
function createEmptyState(emoji, text, actionBtn = null) {
  const emptyState = document.createElement('div');
  emptyState.className = 'empty-state';
  emptyState.innerHTML = `
    <span class="emoji">${emoji}</span>
    ${text}
    ${actionBtn ? `<div style="margin-top:16px;"><button class="btn-primary" onclick="${actionBtn.onclick}">${actionBtn.text}</button></div>` : ''}`;
  return emptyState;
}

/* ── 创建加载骨架屏 ── */
function createSkeleton(lines = 1, width = '100%', height = '14px') {
  const skeleton = document.createElement('div');
  skeleton.className = 'skeleton skeleton-text';
  skeleton.style.width = width;
  skeleton.style.height = height;
  return skeleton;
}

/* ── 创建骨架屏容器(用于列表加载) ── */
function createSkeletonContainer(numCards = 3) {
  const container = document.createElement('div');
  container.style.cssText = 'padding:16px;display:grid;grid-template-columns:repeat(2,1fr);gap:8px;';
  for (let i = 0; i < numCards; i++) {
    const card = document.createElement('div');
    card.className = 'skeleton';
    card.style.cssText = 'height:120px;border-radius:8px;';
    container.appendChild(card);
  }
  return container;
}

/* ── 创建过滤标签栏 ── */
function createFilterBar(items, activeKey, onFilter) {
  const bar = document.createElement('div');
  bar.className = 'filter-bar';
  items.forEach(item => {
    const chip = document.createElement('button');
    chip.className = `filter-chip${item.key === activeKey ? ' active' : ''}`;
    chip.dataset.cat = item.key;
    chip.textContent = item.label;
    chip.onclick = () => onFilter(item.key);
    bar.appendChild(chip);
  });
  return bar;
}

/* ── 创建图标按钮(悬浮) ── */
function createFloatingButton(icon, onclick, style = {}) {
  const btn = document.createElement('button');
  btn.className = 'ai-fab-global';
  btn.textContent = icon;
  btn.onclick = onclick;
  Object.assign(btn.style, style);
  return btn;
}

/* ── 创建聊天气泡 ── */
function createChatBubble(role, content) {
  const bubble = document.createElement('div');
  bubble.className = `chat-msg chat-${role}`;
  bubble.innerHTML = `<div class="chat-bubble">${role === 'assistant' ? content : escapeHtml(content)}</div>`;
  return bubble;
}

/* ── 创建统计卡片 ── */
function createStatCard(value, label) {
  const card = document.createElement('div');
  card.className = 'stat-card';
  card.innerHTML = `
    <div class="stat-num">${value}</div>
    <div class="stat-lbl">${label}</div>`;
  return card;
}

/* ── 创建文章卡片 ── */
function createArticleCard(article, onClick) {
  const card = document.createElement('div');
  card.className = 'article-card';
  card.onclick = () => onClick(article);
  card.innerHTML = `
    <div class="article-cat">${escapeHtml(article.category || '未分类')}</div>
    <div class="article-title">${escapeHtml(article.title || '未命名')}</div>
    <div class="article-summary">${escapeHtml(article.summary || '暂无摘要')}</div>
    <div class="article-meta">${escapeHtml(article.source || '')} · ${article.read ? '已读' : '未读'}</div>`;
  return card;
}

/* ── 创建穿搭卡片 ── */
function createOutfitCard(outfit, onClick) {
  const card = document.createElement('div');
  card.className = 'outfit-card';
  card.onclick = () => onClick(outfit);
  card.innerHTML = `
    <div class="outfit-items">
      ${(outfit.items || []).map(item => `<img class="outfit-item-thumb" src="${item.url}" alt="${item.category}">`).join('')}
    </div>
    <div class="outfit-reason">${escapeHtml(outfit.reason || '')}</div>
    <div class="outfit-score">
      <span class="score-label">评分</span>
      <div class="score-bar">
        <div class="score-fill" style="width:${(outfit.style_score || 0) * 100}%"></div>
      </div>
    </div>`;
  return card;
}

/* ── 创建菜品卡片 ── */
function createRecipeCard(recipe, onClick) {
  const card = document.createElement('div');
  card.className = 'article-card';
  card.onclick = () => onClick(recipe);
  card.innerHTML = `
    <div class="article-cat">${escapeHtml(recipe.category || '未分类')}</div>
    <div class="article-title">${escapeHtml(recipe.title || '未命名')}</div>
    <div class="article-summary">${escapeHtml(recipe.summary || '暂无摘要')}</div>
    <div class="article-meta">难度: ${escapeHtml(recipe.difficulty || '未知')} · 时间: ${recipe.cook_minutes || '?'}分</div>`;
  return card;
}

/* ── 创建确认对话框 ── */
function createConfirmDialog(message, onConfirm) {
  const overlay = createModal2(null, `
    <div style="padding:16px;text-align:center;">
      <div style="font-size:15px;margin-bottom:20px;color:var(--text-primary);">${escapeHtml(message)}</div>
      <div class="btn-action-row">
        <button class="btn-outline" onclick="this.closest('.overlay').remove()">取消</button>
        <button class="btn-primary" onclick="this.closest('.overlay').remove(); ${onConfirm.name}()">确定</button>
      </div>
    </div>`, { maxWidth: '320px' });
  return overlay;
}

/* ── 创建表单字段 ── */
function createFormField(label, inputHtml, id = '') {
  const field = document.createElement('div');
  field.className = 'form-field';
  field.innerHTML = `
    <label class="form-label">${label}</label>
    ${inputHtml}`;
  if (id) field.id = id;
  return field;
}

/* ── 创建文本输入框 ── */
function createTextInput(placeholder = '', value = '') {
  const input = document.createElement('input');
  input.type = 'text';
  input.className = 'form-input';
  input.placeholder = placeholder;
  input.value = value;
  return input;
}

/* ── 创建下拉选择框 ── */
function createSelect(options, value = '') {
  const select = document.createElement('select');
  select.className = 'form-select';
  options.forEach(opt => {
    const option = document.createElement('option');
    option.value = opt.value;
    option.textContent = opt.label;
    if (opt.value === value) option.selected = true;
    select.appendChild(option);
  });
  return select;
}

/* ── 创建多行文本框 ── */
function createTextarea(placeholder = '', value = '', rows = 3) {
  const textarea = document.createElement('textarea');
  textarea.className = 'form-textarea';
  textarea.placeholder = placeholder;
  textarea.value = value;
  textarea.rows = rows;
  return textarea;
}

// 导出所有组件
const Components = {
  createBottomSheet,
  createModal: createModal2,
  createEmptyState,
  createSkeleton,
  createSkeletonContainer,
  createFilterBar,
  createFloatingButton,
  createChatBubble,
  createStatCard,
  createArticleCard,
  createOutfitCard,
  createRecipeCard,
  createConfirmDialog,
  createFormField,
  createTextInput,
  createSelect,
  createTextarea,
};

// 全局暴露
window.Components = Components;

