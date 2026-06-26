/* wardrobe.js — 衣橱页(含拍照/相册上传) */

let wardrobeFilter = 'all';
let _pendingUploadFile = null;

const CATEGORY_NAMES = {
  all: '全部', top: '上装', bottom: '下装', dress: '连衣裙',
  outerwear: '外套', shoes: '鞋', bag: '包', accessory: '配饰'
};
const SEASON_MAP = { '春': 'spring', '夏': 'summer', '秋': 'autumn', '冬': 'winter', '四季': 'all' };
const SEASON_NAMES = { '': '不限', spring: '春', summer: '夏', autumn: '秋', winter: '冬', all: '四季' };

function renderWardrobePage() {
  const page = document.getElementById('page-wardrobe');

  const cats = ['all', 'top', 'bottom', 'dress', 'outerwear', 'shoes', 'bag', 'accessory'];
  let html = `<div class="filter-bar">`;
  for (const c of cats) {
    html += `<button class="filter-chip${c === wardrobeFilter ? ' active' : ''}" data-cat="${c}" onclick="setWardrobeFilter('${c}')">${CATEGORY_NAMES[c]}</button>`;
  }
  html += `</div>`;

  html += `
    <div style="display:flex;gap:8px;margin:10px 0;">
      <button class="btn-primary" onclick="startAddItem()" style="display:flex;align-items:center;justify-content:center;gap:6px;flex:1;">
        📷 拍照 / 选图 添加衣物
      </button>
      <button class="btn-outline" onclick="switchTab('recommend')" style="flex-shrink:0;padding:0 var(--sp-3);font-size:var(--fs-md);">
        🎯 穿搭推荐
      </button>
    </div>
    <div class="item-grid" id="wardrobe-grid"><div class="empty-state"><span class="emoji">👗</span>加载中…</div></div>`;
  page.innerHTML = html;

  loadWardrobe();

  // AI 浮动按钮
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
              <div><b>搭配:</b> ${escapeHtml(o.description || '')}</div>
              <div style="margin-top:6px;">${itemsHtml}</div>
              ${o.tips ? `<div style="margin-top:6px;color:var(--ai-purple);">💡 ${escapeHtml(o.tips)}</div>` : ''}
            `
          };
        }
      });
    });

    AIFab.initPhotoBar('wardrobe', () => { startAddItem(); });
  }
}

/* ════════════════════════════════════════════
   新上传流程: 选照片 → AI识别 → 预填表单 → 确认提交
   ════════════════════════════════════════════ */

function startAddItem() {
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = 'image/*';
  input.capture = 'environment';
  input.onchange = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    _pendingUploadFile = file;
    showRecognitionOverlay(file);
  };
  input.click();
}

function showRecognitionOverlay(file) {
  const url = URL.createObjectURL(file);

  const overlay = document.createElement('div');
  overlay.id = 'wardrobe-recognize-overlay';
  overlay.className = 'overlay';
  overlay.innerHTML = `
    <div style="text-align:center;padding:var(--sp-5);">
      <img src="${url}" style="width:200px;height:200px;object-fit:cover;border-radius:var(--r-lg);margin-bottom:var(--sp-3);box-shadow:var(--shadow-md);">
      <div style="font-size:var(--fs-xl);font-weight:600;color:var(--text-primary);margin-bottom:var(--sp-2);">AI 识别中...</div>
      <div style="font-size:var(--fs-base);color:var(--text-hint);">正在分析衣服类型、颜色、季节</div>
    </div>`;
  document.body.appendChild(overlay);

  // AI 识别完成后弹出预填表单
  api.autoTag(file).then(tag => {
    overlay.remove();
    showEditSheet(tag, url);
  }).catch(err => {
    console.warn('[add] autoTag failed:', err.message);
    overlay.remove();
    showEditSheet({}, url);
  });
}

function showEditSheet(tag, previewUrl) {
  const cats = ['top', 'bottom', 'dress', 'outerwear', 'shoes', 'bag', 'accessory'];
  const seasons = ['', 'spring', 'summer', 'autumn', 'winter', 'all'];
  const recognized = tag.category ? true : false;

  const overlay = document.createElement('div');
  overlay.className = 'overlay overlay-bottom';
  overlay.id = 'wardrobe-upload-overlay';
  overlay.innerHTML = `
    <div class="bottom-sheet">
      <div class="sheet-header">
        <div class="sheet-title">确认衣物信息</div>
        <button class="modal-box-close" onclick="closeUploadSheet()">×</button>
      </div>

      <div style="margin-bottom:var(--sp-3);display:flex;align-items:center;gap:var(--sp-3);">
        <div style="width:72px;height:72px;border-radius:var(--r-sm);overflow:hidden;border:1px solid var(--border);flex-shrink:0;">
          <img src="${previewUrl}" style="width:100%;height:100%;object-fit:cover;">
        </div>
        <div>
          <div style="font-size:var(--fs-sm);color:${recognized ? 'var(--success)' : 'var(--warning)'};">
            ${recognized ? '✅ AI 已自动识别以下信息' : '⚠️ 识别失败，请手动填写'}
          </div>
          ${recognized && tag.title ? `<div style="font-size:var(--fs-md);color:var(--text-primary);margin-top:4px;">${escapeHtml(tag.title)}</div>` : ''}
        </div>
      </div>

      <div class="form-field">
        <label class="form-label">分类</label>
        <select id="wardrobe-cat" class="form-select">
          ${cats.map(c => `<option value="${c}" ${c === (tag.category || 'top') ? 'selected' : ''}>${CATEGORY_NAMES[c]}</option>`).join('')}
        </select>
      </div>

      <div class="form-field">
        <label class="form-label">名称</label>
        <input type="text" id="wardrobe-title" class="form-input" placeholder="如:白T恤" value="${escapeHtml(tag.title || '')}">
      </div>

      <div style="display:grid;grid-template-columns:1fr 1fr;gap:var(--sp-2);">
        <div class="form-field">
          <label class="form-label">颜色</label>
          <input type="text" id="wardrobe-color" class="form-input" placeholder="如:白/黑/米" value="${escapeHtml(tag.color || '')}">
        </div>
        <div class="form-field">
          <label class="form-label">季节</label>
          <select id="wardrobe-season" class="form-select">
            ${seasons.map(s => {
              const mapped = tag.season ? (SEASON_MAP[tag.season] || '') : '';
              return `<option value="${s}" ${s === mapped ? 'selected' : ''}>${SEASON_NAMES[s]}</option>`;
            }).join('')}
          </select>
        </div>
      </div>

      <div id="wardrobe-upload-status" style="font-size:var(--fs-base);margin-top:var(--sp-2);text-align:center;"></div>

      <button id="wardrobe-upload-btn" class="btn-primary" onclick="submitUpload()">确认添加</button>
    </div>`;
  document.body.appendChild(overlay);
  overlay.addEventListener('click', e => { if (e.target === overlay) closeUploadSheet(); });
}

function closeUploadSheet() {
  const el = document.getElementById('wardrobe-upload-overlay');
  if (el) el.remove();
}

async function submitUpload() {
  const file = _pendingUploadFile;
  if (!file) {
    const status = document.getElementById('wardrobe-upload-status');
    status.textContent = '⚠️ 请先拍照或选图';
    status.style.color = 'var(--error)';
    return;
  }

  const category = document.getElementById('wardrobe-cat').value;
  const title = document.getElementById('wardrobe-title').value.trim();
  const color = document.getElementById('wardrobe-color').value.trim();
  const season = document.getElementById('wardrobe-season').value;

  const formData = new FormData();
  formData.append('file', file);
  formData.append('category', category);
  if (title) formData.append('title', title);
  if (color) formData.append('color', color);
  if (season) formData.append('season', season);

  const btn = document.getElementById('wardrobe-upload-btn');
  const status = document.getElementById('wardrobe-upload-status');
  btn.disabled = true;
  btn.textContent = '上传中…';
  status.textContent = '正在上传...';
  status.style.color = 'var(--text-hint)';

  try {
    const data = await postItem(formData);
    const item = data.item || data;
    status.textContent = '✅ 上传成功!';
    status.style.color = 'var(--success)';
    toast(`已添加: ${item.title || item.category}`);
    setTimeout(() => {
      closeUploadSheet();
      _pendingUploadFile = null;
      loadWardrobe();
    }, 600);
  } catch (e) {
    status.textContent = '❌ 上传失败: ' + (e.message || '未知错误');
    status.style.color = 'var(--error)';
    btn.disabled = false;
    btn.textContent = '重试上传';
  }
}

/* ════════════════════════════════════════════
   数据加载
   ════════════════════════════════════════════ */

async function loadWardrobe() {
  try {
    const data = await listItems(wardrobeFilter === 'all' ? null : wardrobeFilter, 50);
    const items = data.items || [];
    const grid = document.getElementById('wardrobe-grid');
    if (!items.length) {
      grid.innerHTML = `<div class="empty-state"><span class="emoji">👗</span>衣橱空空,<br>点击上方"拍照 / 选图"添加第一件吧～</div>`;
      return;
    }
    grid.innerHTML = items.map(it => `
      <div class="item-card" onclick="showItemDetail('${it.id}')">
        <img src="${it.thumbnail_url || it.original_url}" alt="${it.title || it.category}" loading="lazy">
        <div class="item-meta">
          <div class="item-title">${escapeHtml(it.title || it.category)}</div>
          <div class="item-badges">
            <span class="badge badge-cat">${CATEGORY_NAMES[it.category] || it.category}</span>
            ${it.color ? `<span class="badge badge-color">${escapeHtml(it.color)}</span>` : ''}
          </div>
        </div>
      </div>`).join('');
  } catch (e) {
    console.error('[WARDROBE] listItems error:', e.name, e.message);
    const grid = document.getElementById('wardrobe-grid');
    if (grid) grid.innerHTML = `<div class="empty-state"><span class="emoji">⚠️</span>加载失败</div>`;
  }
}

function setWardrobeFilter(cat) {
  wardrobeFilter = cat;
  document.querySelectorAll('.filter-chip').forEach(chip => {
    chip.classList.toggle('active', chip.dataset.cat === cat);
  });
  loadWardrobe();
}

/* ════════════════════════════════════════════
   详情弹窗
   ════════════════════════════════════════════ */

function showItemDetail(id) {
  getItem(id).then(data => {
    const it = data.item || data;
    const overlay = createModal(`
      <div class="modal-box-body" style="padding:0;">
        <img src="${it.original_url || it.thumbnail_url}" alt="${escapeHtml(it.title || '')}"
             style="width:100%;border-radius:var(--r-lg) var(--r-lg) 0 0;max-height:300px;object-fit:cover;">
        <div style="padding:var(--sp-4);">
          <div style="font-size:var(--fs-xl);font-weight:600;margin-bottom:var(--sp-2);">${escapeHtml(it.title || '无标题')}</div>
          <div class="item-badges" style="margin-bottom:var(--sp-3);">
            <span class="badge badge-cat">${CATEGORY_NAMES[it.category] || it.category}</span>
            ${it.color ? `<span class="badge badge-color">${escapeHtml(it.color)}</span>` : ''}
            ${it.season ? `<span class="badge" style="background:#E8F4FD;color:#2980B9;">${SEASON_NAMES[it.season] || it.season}</span>` : ''}
          </div>
          ${it.brand ? `<div style="font-size:var(--fs-base);color:var(--text-hint);">品牌: ${escapeHtml(it.brand)}</div>` : ''}
          ${it.note ? `<div style="font-size:var(--fs-base);color:var(--text-secondary);margin-top:4px;">备注: ${escapeHtml(it.note)}</div>` : ''}
          <div class="btn-action-row" style="margin-top:var(--sp-4);">
            <button class="btn-outline" onclick="this.closest('.overlay').remove()">关闭</button>
            <button class="btn-outline" onclick="openEditItem('${it.id}',this)" style="flex:1;">✏️ 编辑</button>
            <button class="btn-danger" onclick="confirmDeleteItem('${it.id}')">删除</button>
          </div>
        </div>
      </div>`, { maxWidth: '360px' });
    overlay.addEventListener('click', e => { if (e.target === overlay) overlay.remove(); });
  }).catch(() => toast('加载详情失败'));
}

function openEditItem(id, btn) {
  // Close detail overlay
  closeAllOverlays();
  getItem(id).then(data => {
    const it = data.item || data;
    const cats = ['top', 'bottom', 'dress', 'outerwear', 'shoes', 'bag', 'accessory'];
    const seasons = ['', 'spring', 'summer', 'autumn', 'winter', 'all'];

    const overlay = document.createElement('div');
    overlay.className = 'overlay overlay-bottom';
    overlay.id = 'wardrobe-edit-overlay';
    overlay.innerHTML = `
      <div class="bottom-sheet">
        <div class="sheet-header">
          <div class="sheet-title">编辑衣物信息</div>
          <button class="modal-box-close" onclick="this.closest('.overlay').remove()">×</button>
        </div>

        <div class="form-field">
          <label class="form-label">分类</label>
          <select id="edit-cat" class="form-select">
            ${cats.map(c => `<option value="${c}" ${c === (it.category || 'top') ? 'selected' : ''}>${CATEGORY_NAMES[c]}</option>`).join('')}
          </select>
        </div>
        <div class="form-field">
          <label class="form-label">名称</label>
          <input type="text" id="edit-title" class="form-input" value="${escapeHtml(it.title || '')}">
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:var(--sp-2);">
          <div class="form-field">
            <label class="form-label">颜色</label>
            <input type="text" id="edit-color" class="form-input" value="${escapeHtml(it.color || '')}">
          </div>
          <div class="form-field">
            <label class="form-label">季节</label>
            <select id="edit-season" class="form-select">
              ${seasons.map(s => `<option value="${s}" ${s === (it.season || '') ? 'selected' : ''}>${SEASON_NAMES[s]}</option>`).join('')}
            </select>
          </div>
        </div>
        <div class="form-field">
          <label class="form-label">品牌</label>
          <input type="text" id="edit-brand" class="form-input" value="${escapeHtml(it.brand || '')}">
        </div>
        <div class="form-field">
          <label class="form-label">备注</label>
          <textarea id="edit-note" class="form-textarea" rows="2">${escapeHtml(it.note || '')}</textarea>
        </div>

        <div id="edit-status" style="font-size:var(--fs-base);text-align:center;margin-top:var(--sp-2);"></div>
        <button id="edit-save-btn" class="btn-primary" onclick="saveEditItem('${id}')">保存修改</button>
      </div>`;
    document.body.appendChild(overlay);
    overlay.addEventListener('click', e => { if (e.target === overlay) overlay.remove(); });
  }).catch(() => toast('加载详情失败'));
}

async function saveEditItem(id) {
  const data = {
    category: document.getElementById('edit-cat').value,
    title: document.getElementById('edit-title').value.trim(),
    color: document.getElementById('edit-color').value.trim(),
    season: document.getElementById('edit-season').value,
    brand: document.getElementById('edit-brand').value.trim(),
    note: document.getElementById('edit-note').value.trim(),
  };
  const btn = document.getElementById('edit-save-btn');
  const status = document.getElementById('edit-status');
  btn.disabled = true;
  btn.textContent = '保存中...';

  try {
    await updateItem(id, data);
    status.textContent = '✅ 保存成功';
    status.style.color = 'var(--success)';
    toast('修改已保存');
    setTimeout(() => {
      document.getElementById('wardrobe-edit-overlay')?.remove();
      loadWardrobe();
    }, 600);
  } catch (e) {
    status.textContent = '❌ 保存失败: ' + e.message;
    status.style.color = 'var(--error)';
    btn.disabled = false;
    btn.textContent = '重试保存';
  }
}

async function confirmDeleteItem(id) {
  confirmAction('确定删除这件衣服?', async () => {
    try {
      await deleteItem(id);
      closeAllOverlays();
      toast('删除成功');
      loadWardrobe();
    } catch (e) { toast('删除失败'); }
  });
}
