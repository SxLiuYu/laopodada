/* recipe.js — 菜谱页 */

let recipeFilter = { category: '', difficulty: '', search: '' };
let recipeFavorites = [];
try { recipeFavorites = JSON.parse(localStorage.getItem('recipe_favs') || '[]'); } catch(e) { console.warn('[recipe] localStorage not available'); }

const RECIPE_CATEGORIES = [
  { key: '',        label: '全部' },
  { key: 'breakfast', label: '早餐' },
  { key: 'lunch',   label: '午餐' },
  { key: 'dinner',  label: '晚餐' },
  { key: 'snack',   label: '甜点' },
  { key: 'dessert', label: '甜点' },
  { key: 'drink',   label: '饮品' },
];

const RECIPE_DIFFICULTIES = [
  { key: '',      label: '难度' },
  { key: 'easy',   label: '简单' },
  { key: 'medium', label: '中等' },
  { key: 'hard',   label: '困难' },
];

function renderRecipePage() {
  const page = document.getElementById('page-recipe');
  page.classList.add('active');
  page.innerHTML = `
    <div class="page-header">🍳 菜谱</div>
    <div id="recipe-ai-toggle" style="padding:var(--sp-2) var(--sp-3);background:var(--bg-white);border-bottom:1px solid var(--border);">
      <button onclick="toggleRecipeAI()" style="width:100%;background:none;border:none;padding:var(--sp-2) 0;display:flex;align-items:center;justify-content:space-between;cursor:pointer;font-family:var(--font-sans);">
        <span style="font-size:var(--fs-md);color:var(--text-secondary);">✨ AI 智能生成菜谱</span>
        <span id="recipe-ai-arrow" style="color:var(--text-hint);font-size:12px;transition:transform .2s;">▶</span>
      </button>
      <div id="recipe-ai-body" style="display:none;">
        <div class="ai-gen-bar" style="padding:0 0 var(--sp-2);">
          <input id="recipe-ai-input" type="text" placeholder="想吃啥?输入菜名或场景" maxlength="100">
          <button id="recipe-ai-btn" class="ai-btn" onclick="genRecipe()">✨ 生成</button>
        </div>
        <p class="ai-hint">💡 LLM 需 60-90 秒</p>
        <div id="recipe-ai-result" class="ai-result"></div>
      </div>
    </div>
    <div class="filter-bar" id="recipe-cat-bar"></div>
    <div class="filter-bar" id="recipe-diff-bar" style="padding-top:0;"></div>
    <div style="padding:var(--sp-2) var(--sp-3);display:flex;gap:var(--sp-2);align-items:center;">
      <input type="search" id="recipe-search" placeholder="搜索菜谱…" class="form-input"
        oninput="recipeFilter.search=this.value;loadRecipes()">
      <button class="filter-chip active" onclick="showRecipeCreateForm()" style="background:var(--primary);color:#fff;border-color:var(--primary);">+ 新建</button>
    </div>
    <div class="item-grid" id="recipe-grid"><div class="empty-state"><span class="emoji">🍳</span>加载中…</div></div>
  `;

  // category chips
  const catBar = document.getElementById('recipe-cat-bar');
  catBar.innerHTML = RECIPE_CATEGORIES.map(c => `
    <button class="filter-chip${recipeFilter.category === c.key ? ' active' : ''}"
      data-cat="${c.key}" onclick="setRecipeCategory('${c.key}')">${c.label}</button>
  `).join('');

  // difficulty chips
  const diffBar = document.getElementById('recipe-diff-bar');
  diffBar.innerHTML = RECIPE_DIFFICULTIES.map(d => `
    <button class="filter-chip${recipeFilter.difficulty === d.key ? ' active' : ''}"
      data-diff="${d.key}" onclick="setRecipeDifficulty('${d.key}')">${d.label}</button>
  `).join('');

  // AI 生成按钮
  document.getElementById('recipe-ai-btn').onclick = genRecipe;

  // Show skeleton while loading
  renderGridSkeleton('recipe-grid', 2, 3);

  loadRecipes();

  // Pull-to-refresh (native only)
  enablePullRefresh(loadRecipes);

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
              <div><b>${escapeHtml(r.title || '新菜')}</b> (${catLabel(r.category)} · ${diffLabel(r.difficulty)} · ${(r.prep_minutes || 0) + (r.cook_minutes || 0)} 分钟)</div>
              <div style="margin-top:6px;"><b>食材:</b> ${escapeHtml(ingredients)}</div>
              <div style="margin-top:6px;"><b>步骤:</b>\n${escapeHtml(steps)}</div>
              ${r.note ? `<div style="margin-top:6px;color:var(--ai-purple);">💡 ${escapeHtml(r.note)}</div>` : ''}
            `
          };
        }
      });
    });
  }
}

async function loadRecipes() {
  const grid = document.getElementById('recipe-grid');
  grid.innerHTML = `<div class="empty-state"><span class="emoji">🍳</span>加载中…</div>`;
  try {
    const data = await listRecipes(recipeFilter.category || undefined,
                                   recipeFilter.difficulty || undefined,
                                   recipeFilter.search || undefined);
    const recipes = data.recipes || [];
    if (!recipes.length) {
      grid.innerHTML = `<div class="empty-state"><span class="emoji">🍳</span>还没有菜谱，<br>点击"+ 新建"添加第一道吧～</div>`;
      return;
    }
    grid.innerHTML = recipes.map(r => `
      <div class="item-card" onclick="showRecipeDetail('${r.id}')">
        <img src="${r.cover_url || 'data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><rect fill=%22%23f0f0f0%22 width=%22100%22 height=%22100%22/><text x=%2250%22 y=%2255%22 text-anchor=%22middle%22 fill=%22%23ccc%22 font-size=%2240%22>🍳</text></svg>'}"
          alt="${r.title}" style="width:100%;aspect-ratio:1;object-fit:cover;"
          onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><rect fill=%22%23f0f0f0%22 width=%22100%22 height=%22100%22/><text x=%2250%22 y=%2255%22 text-anchor=%22middle%22 fill=%22%23ccc%22 font-size=%2240%22>🍳</text></svg>'">
        <div class="item-meta">
          <div class="item-title">${r.title}</div>
          <div class="item-badges">
            <span class="badge badge-cat">${catLabel(r.category)}</span>
            <span class="badge" style="background:#FFF3E0;color:#E67E22;">${diffLabel(r.difficulty)}</span>
          </div>
        </div>
      </div>`).join('');
  } catch(e) {
    grid.innerHTML = `<div class="empty-state"><span class="emoji">⚠️</span>加载失败：${e.message}</div>`;
  }
}

function catLabel(cat) {
  const m = { breakfast:'早餐', lunch:'午餐', dinner:'晚餐', snack:'甜点', dessert:'甜点', drink:'饮品' };
  return m[cat] || cat || '';
}
function diffLabel(d) {
  return { easy:'简单', medium:'中等', hard:'困难' }[d] || d || '';
}

function prependRecipeToList(recipe) {
  const grid = document.getElementById('recipe-grid');
  // 移除 empty state
  const empty = grid.querySelector('.empty-state');
  if (empty) empty.remove();
  const card = document.createElement('div');
  card.className = 'item-card ai-card';
  card.onclick = () => showRecipeDetail(recipe.id);
  card.innerHTML = `
    <img src="${recipe.cover_url || 'data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><rect fill=%22%23f0f0f0%22 width=%22100%22 height=%22100%22/><text x=%2250%22 y=%2255%22 text-anchor=%22middle%22 fill=%22%23ccc%22 font-size=%2240%22>🍳</text></svg>'}"
      alt="${escapeHtml(recipe.title)}" style="width:100%;aspect-ratio:1;object-fit:cover;border:2px solid #a855f7;"
      onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><rect fill=%22%23f0f0f0%22 width=%22100%22 height=%22100%22/><text x=%2250%22 y=%2255%22 text-anchor=%22middle%22 fill=%22%23ccc%22 font-size=%2240%22>🍳</text></svg>'">
    <div class="item-meta">
      <div class="item-title">✨ ${escapeHtml(recipe.title)} <span class="ai-tag" style="font-size:10px;padding:1px 4px;">AI</span></div>
      <div class="item-badges">
        <span class="badge badge-cat">${catLabel(recipe.category)}</span>
        <span class="badge" style="background:#FFF3E0;color:#E67E22;">${diffLabel(recipe.difficulty)}</span>
      </div>
    </div>
  `;
  grid.insertBefore(card, grid.firstChild);
}

/* ── AI 生成(提取为独立函数) ── */
async function genRecipe() {
  const input = document.getElementById('recipe-ai-input');
  const query = input.value.trim();
  if (!query) { toast('请输入菜名或场景'); return; }
  const btn = document.getElementById('recipe-ai-btn');
  const resultBox = document.getElementById('recipe-ai-result');
  btn.disabled = true;
  btn.textContent = 'AI 在想菜谱...';
  resultBox.innerHTML = '<div class="ai-loading">🤔 AI 思考中,请耐心等待(约 60-90 秒)...</div>';
  try {
    const data = await generateRecipe(query);
    const recipe = data.recipe;
    resultBox.innerHTML = `
      <div class="ai-result-card">
        <div class="ai-result-header">
          <h3>✨ ${escapeHtml(recipe.title)}</h3>
          <span class="ai-tag">AI 生成</span>
        </div>
        <p><strong>${catLabel(recipe.category)} · ${diffLabel(recipe.difficulty)} · ${(recipe.prep_minutes || 0) + (recipe.cook_minutes || 0)} 分钟 · ${recipe.servings || 1} 人份</strong></p>
        <h4>食材</h4>
        <ul>${(recipe.ingredients || []).map(x => `<li>${escapeHtml(x)}</li>`).join('')}</ul>
        <h4>步骤</h4>
        <ol>${(recipe.steps || []).map(x => `<li>${escapeHtml(x)}</li>`).join('')}</ol>
        ${recipe.note ? `<p class="ai-note">💡 ${escapeHtml(recipe.note)}</p>` : ''}
        <p class="ai-source">由 AI 现做,基于真实中国家常菜常识</p>
      </div>`;
    prependRecipeToList(recipe);
    input.value = '';
  } catch (e) {
    resultBox.innerHTML = `<div class="ai-error">❌ ${escapeHtml(e.message)}</div>`;
  } finally {
    btn.disabled = false;
    btn.textContent = '✨ 生成';
  }
}

/* ── 折叠切换 ── */
function toggleRecipeAI() {
  const body = document.getElementById('recipe-ai-body');
  const arrow = document.getElementById('recipe-ai-arrow');
  if (body.style.display === 'none') {
    body.style.display = 'block';
    arrow.style.transform = 'rotate(90deg)';
  } else {
    body.style.display = 'none';
    arrow.style.transform = 'rotate(0deg)';
  }
}

function setRecipeCategory(cat) {
  recipeFilter.category = cat;
  document.querySelectorAll('#recipe-cat-bar .filter-chip').forEach(chip => {
    chip.classList.toggle('active', chip.dataset.cat === cat);
  });
  loadRecipes();
}
function setRecipeDifficulty(diff) {
  recipeFilter.difficulty = diff;
  document.querySelectorAll('#recipe-diff-bar .filter-chip').forEach(chip => {
    chip.classList.toggle('active', chip.dataset.diff === diff);
  });
  loadRecipes();
}

async function showRecipeDetail(id) {
  try {
    const r = (await getRecipe(id)).recipe || (await getRecipe(id));
    const overlay = createModal(`
      ${r.cover_url ? `<img src="${r.cover_url}" style="width:100%;border-radius:var(--r-lg) var(--r-lg) 0 0;max-height:220px;object-fit:cover;">` : ''}
      <div style="padding:var(--sp-4);">
        <div style="font-size:var(--fs-xl);font-weight:600;margin-bottom:var(--sp-2);">${escapeHtml(r.title)}</div>
        <div class="item-badges" style="margin-bottom:var(--sp-3);">
          <span class="badge badge-cat">${catLabel(r.category)}</span>
          <span class="badge" style="background:#FFF3E0;color:#E67E22;">${diffLabel(r.difficulty)}</span>
          ${(r.tags||[]).map(t => `<span class="badge" style="background:#EDE7F6;color:#7B1FA2;">${escapeHtml(t)}</span>`).join('')}
        </div>
        ${r.prep_minutes || r.cook_minutes ? `<div style="font-size:var(--fs-sm);color:var(--text-hint);margin-bottom:var(--sp-2);">准备 ${r.prep_minutes||0} 分钟 · 烹饪 ${r.cook_minutes||0} 分钟</div>` : ''}
        <div style="margin-bottom:var(--sp-3);">
          <div style="font-size:var(--fs-base);font-weight:600;color:var(--text-secondary);margin-bottom:4px;">🥗 食材</div>
          <ul style="font-size:var(--fs-base);color:var(--text-secondary);padding-left:18px;">${(r.ingredients||[]).map(i => `<li style="margin-bottom:2px;">${escapeHtml(i)}</li>`).join('')}</ul>
        </div>
        <div>
          <div style="font-size:var(--fs-base);font-weight:600;color:var(--text-secondary);margin-bottom:4px;">📝 步骤</div>
          <ol style="font-size:var(--fs-base);color:var(--text-secondary);padding-left:18px;">${(r.steps||[]).map((s,i) => `<li style="margin-bottom:4px;">${escapeHtml(s)}</li>`).join('')}</ol>
        </div>
        <div class="btn-action-row" style="margin-top:var(--sp-4);">
          <button class="btn-outline" onclick="this.closest('.overlay').remove()">关闭</button>
          <button class="btn-outline" onclick="toggleRecipeFav('${r.id}')" id="fav-btn-${r.id}" style="flex:1;">${recipeFavorites.includes(r.id) ? '❤️ 已收藏' : '🤍 收藏'}</button>
          <button class="btn-danger" onclick="confirmDeleteRecipe('${r.id}')">删除</button>
        </div>
      </div>
    `, { maxWidth: '360px' });
    overlay.addEventListener('click', e => { if (e.target === overlay) overlay.remove(); });
  } catch(e) { toast('加载详情失败'); }
}

async function confirmDeleteRecipe(id) {
  confirmAction('确定删除这个菜谱？', async () => {
    try {
      await deleteRecipe(id);
      closeAllOverlays();
      toast('已删除');
      loadRecipes();
    } catch(e) { toast('删除失败'); }
  });
}

function showRecipeCreateForm() {
  const overlay = document.createElement('div');
  overlay.className = 'overlay overlay-bottom';
  overlay.id = 'recipe-create-overlay';
  overlay.innerHTML = `
    <div class="bottom-sheet">
      <div class="sheet-header">
        <div class="sheet-title">新建菜谱</div>
        <button class="modal-box-close" onclick="this.closest('.overlay').remove()">×</button>
      </div>
      <div class="form-grid" style="padding:0 0 var(--sp-2);">
        <div class="form-full">
          <label class="form-label">标题 *</label>
          <input type="text" id="rf-title" class="form-input" placeholder="如：番茄炒蛋">
        </div>
        <div>
          <label class="form-label">类别 *</label>
          <select id="rf-category" class="form-select">
            <option value="">请选择</option>
            <option value="breakfast">早餐</option><option value="lunch">午餐</option>
            <option value="dinner">晚餐</option><option value="snack">甜点</option>
            <option value="dessert">甜点</option><option value="drink">饮品</option>
          </select>
        </div>
        <div>
          <label class="form-label">难度 *</label>
          <select id="rf-difficulty" class="form-select">
            <option value="">请选择</option>
            <option value="easy">简单</option><option value="medium">中等</option><option value="hard">困难</option>
          </select>
        </div>
        <div>
          <label class="form-label">准备分钟</label>
          <input type="number" id="rf-prep" class="form-input" placeholder="如：10">
        </div>
        <div>
          <label class="form-label">烹饪分钟</label>
          <input type="number" id="rf-cook" class="form-input" placeholder="如：15">
        </div>
        <div class="form-full">
          <label class="form-label">食材（每行一个）</label>
          <textarea id="rf-ingredients" class="form-textarea" rows="4" placeholder="番茄 2个&#10;鸡蛋 3个&#10;盐 适量"></textarea>
        </div>
        <div class="form-full">
          <label class="form-label">步骤（每行一步）</label>
          <textarea id="rf-steps" class="form-textarea" rows="4" placeholder="番茄切块&#10;鸡蛋打散&#10;热锅下油"></textarea>
        </div>
        <div class="form-full">
          <label class="form-label">标签（逗号分隔）</label>
          <input type="text" id="rf-tags" class="form-input" placeholder="如：快手,家常菜">
        </div>
      </div>
      <button class="btn-primary" onclick="submitRecipe()">保存菜谱</button>
    </div>`;
  document.body.appendChild(overlay);
  overlay.addEventListener('click', e => { if (e.target === overlay) overlay.remove(); });
}

async function submitRecipe() {
  const title = document.getElementById('rf-title').value.trim();
  const category = document.getElementById('rf-category').value;
  const difficulty = document.getElementById('rf-difficulty').value;
  const prep = parseInt(document.getElementById('rf-prep').value) || 0;
  const cook = parseInt(document.getElementById('rf-cook').value) || 0;
  const ingredientsRaw = document.getElementById('rf-ingredients').value.trim();
  const stepsRaw = document.getElementById('rf-steps').value.trim();
  const tagsRaw = document.getElementById('rf-tags').value.trim();

  if (!title) { toast('请输入标题'); return; }
  if (!category) { toast('请选择类别'); return; }
  if (!difficulty) { toast('请选择难度'); return; }
  if (!ingredientsRaw) { toast('请输入食材'); return; }
  if (!stepsRaw) { toast('请输入步骤'); return; }

  const ingredients = ingredientsRaw.split('\n').filter(l => l.trim());
  const steps = stepsRaw.split('\n').filter(l => l.trim());
  const tags = tagsRaw ? tagsRaw.split(',').map(t => t.trim()).filter(Boolean) : [];

  const body = {
    title, category, difficulty,
    prep_minutes: prep, cook_minutes: cook,
    ingredients, steps, tags,
  };

  try {
    await createRecipe(body);
    closeAllOverlays();
    toast('保存成功 ✨');
    loadRecipes();
  } catch(e) {
    toast('保存失败：' + e.message);
  }
}

function toggleRecipeFav(id) {
  const idx = recipeFavorites.indexOf(id);
  if (idx >= 0) { recipeFavorites.splice(idx, 1); toast('已取消收藏'); }
  else { recipeFavorites.push(id); toast('已收藏 ❤️'); }
  localStorage.setItem('recipe_favs', JSON.stringify(recipeFavorites));
  const btn = document.getElementById('fav-btn-' + id);
  if (btn) btn.textContent = recipeFavorites.includes(id) ? '❤️ 已收藏' : '🤍 收藏';
}