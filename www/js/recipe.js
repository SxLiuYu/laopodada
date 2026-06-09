/* recipe.js — 菜谱页 */

let recipeFilter = { category: '', difficulty: '', search: '' };

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
    <div class="filter-bar" id="recipe-cat-bar"></div>
    <div class="filter-bar" id="recipe-diff-bar" style="padding-top:0;"></div>
    <div style="padding:8px 12px;display:flex;gap:8px;align-items:center;">
      <input type="search" id="recipe-search" placeholder="搜索菜谱…" style="flex:1;padding:6px 10px;border:1px solid #ddd;border-radius:8px;font-size:13px;"
        oninput="recipeFilter.search=this.value;loadRecipes()">
      <button class="filter-chip active" onclick="showRecipeCreateForm()" style="background:#FF8C94;color:#fff;border-color:#FF8C94;padding:4px 12px;border-radius:14px;font-size:12px;cursor:pointer;">+ 新建</button>
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

  loadRecipes();
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
    const overlay = document.createElement('div');
    overlay.style = 'position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:50;display:flex;align-items:center;justify-content:center;padding:20px;overflow-y:auto;';
    overlay.innerHTML = `
      <div style="background:#fff;border-radius:12px;padding:20px;max-width:360px;width:100%;margin:auto;">
        ${r.cover_url ? `<img src="${r.cover_url}" style="width:100%;border-radius:8px;margin-bottom:12px;max-height:220px;object-fit:cover;">` : ''}
        <div style="font-size:18px;font-weight:600;margin-bottom:6px;">${r.title}</div>
        <div class="item-badges" style="margin-bottom:10px;">
          <span class="badge badge-cat">${catLabel(r.category)}</span>
          <span class="badge" style="background:#FFF3E0;color:#E67E22;">${diffLabel(r.difficulty)}</span>
          ${(r.tags||[]).map(t => `<span class="badge" style="background:#EDE7F6;color:#7B1FA2;">${t}</span>`).join('')}
        </div>
        ${r.prep_minutes || r.cook_minutes ? `<div style="font-size:12px;color:#888;margin-bottom:8px;">准备 ${r.prep_minutes||0} 分钟 · 烹饪 ${r.cook_minutes||0} 分钟</div>` : ''}
        <div style="margin-bottom:10px;">
          <div style="font-size:13px;font-weight:600;color:#555;margin-bottom:4px;">🥗 食材</div>
          <ul style="font-size:12px;color:#666;padding-left:18px;">${(r.ingredients||[]).map(i => `<li style="margin-bottom:2px;">${i}</li>`).join('')}</ul>
        </div>
        <div>
          <div style="font-size:13px;font-weight:600;color:#555;margin-bottom:4px;">📝 步骤</div>
          <ol style="font-size:12px;color:#666;padding-left:18px;">${(r.steps||[]).map((s,i) => `<li style="margin-bottom:4px;">${s}</li>`).join('')}</ol>
        </div>
        <div style="display:flex;gap:8px;margin-top:14px;">
          <button onclick="this.closest('[style]').parentElement.remove()" style="flex:1;padding:8px;border:1px solid #ddd;border-radius:8px;background:#fafafa;cursor:pointer;">关闭</button>
          <button onclick="confirmDeleteRecipe('${r.id}')" style="flex:1;padding:8px;border:none;border-radius:8px;background:#FFE5E5;color:#E74C3C;cursor:pointer;">删除</button>
        </div>
      </div>`;
    document.body.appendChild(overlay);
    overlay.addEventListener('click', e => { if (e.target === overlay) overlay.remove(); });
  } catch(e) { toast('加载详情失败'); }
}

async function confirmDeleteRecipe(id) {
  if (!confirm('确定删除这个菜谱？')) return;
  try {
    await deleteRecipe(id);
    document.querySelectorAll('[style*="position:fixed"]').forEach(el => el.remove());
    toast('删除成功');
    loadRecipes();
  } catch(e) { toast('删除失败'); }
}

function showRecipeCreateForm() {
  const overlay = document.createElement('div');
  overlay.style = 'position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:50;display:flex;align-items:center;justify-content:center;padding:20px;overflow-y:auto;';
  overlay.innerHTML = `
    <div style="background:#fff;border-radius:12px;padding:20px;max-width:360px;width:100%;margin:auto;">
      <div style="font-size:16px;font-weight:600;margin-bottom:14px;">新建菜谱</div>
      <div class="form-grid" style="padding:0 0 8px;">
        <div class="form-full" style="grid-column:1/-1;">
          <label>标题 *</label>
          <input type="text" id="rf-title" placeholder="如：番茄炒蛋">
        </div>
        <div>
          <label>类别 *</label>
          <select id="rf-category">
            <option value="">请选择</option>
            <option value="breakfast">早餐</option>
            <option value="lunch">午餐</option>
            <option value="dinner">晚餐</option>
            <option value="snack">甜点</option>
            <option value="dessert">甜点</option>
            <option value="drink">饮品</option>
          </select>
        </div>
        <div>
          <label>难度 *</label>
          <select id="rf-difficulty">
            <option value="">请选择</option>
            <option value="easy">简单</option>
            <option value="medium">中等</option>
            <option value="hard">困难</option>
          </select>
        </div>
        <div>
          <label>准备分钟</label>
          <input type="number" id="rf-prep" placeholder="如：10">
        </div>
        <div>
          <label>烹饪分钟</label>
          <input type="number" id="rf-cook" placeholder="如：15">
        </div>
        <div class="form-full" style="grid-column:1/-1;">
          <label>食材（每行一个）</label>
          <textarea id="rf-ingredients" rows="4" placeholder="番茄 2个\n鸡蛋 3个\n盐 适量"></textarea>
        </div>
        <div class="form-full" style="grid-column:1/-1;">
          <label>步骤（每行一步）</label>
          <textarea id="rf-steps" rows="4" placeholder="番茄切块\n鸡蛋打散\n热锅下油"></textarea>
        </div>
        <div class="form-full" style="grid-column:1/-1;">
          <label>标签（逗号分隔）</label>
          <input type="text" id="rf-tags" placeholder="如：快手,家常菜">
        </div>
      </div>
      <button class="submit-btn" style="width:100%;margin:0;" onclick="submitRecipe()">保存菜谱</button>
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
    document.querySelectorAll('[style*="position:fixed"]').forEach(el => el.remove());
    toast('保存成功 ✨');
    loadRecipes();
  } catch(e) {
    toast('保存失败：' + e.message);
  }
}