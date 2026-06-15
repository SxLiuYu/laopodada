/* wardrobe.js — 衣橱页(含拍照/相册上传) */

let wardrobeFilter = 'all';
let wardrobeCategory = 'top';  // 上传表单默认选 top

function renderWardrobePage() {
  const page = document.getElementById('page-wardrobe');

  // filter chips
  const cats = ['all','top','bottom','dress','outerwear','shoes','bag','accessory'];
  const catNames = {'all':'全部','top':'上装','bottom':'下装','dress':'连衣裙','outerwear':'外套','shoes':'鞋','bag':'包','accessory':'配饰'};
  let html = `<div class="filter-bar">`;
  for (const c of cats) {
    html += `<button class="filter-chip${c === wardrobeFilter ? ' active' : ''}" data-cat="${c}" onclick="setWardrobeFilter('${c}')">${catNames[c]}</button>`;
  }
  html += `</div>`;

  // 拍照/上传 FAB(右下角悬浮按钮)+ 顶部"添加"按钮
  html += `
    <div style="display:flex;gap:8px;margin:10px 0;">
      <button onclick="openUploadSheet()" style="flex:1;padding:10px;border:none;border-radius:8px;background:linear-gradient(135deg,#FF6B9D,#FF8E72);color:#fff;font-size:15px;font-weight:600;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:6px;">
        📷 拍照 / 选图 添加衣物
      </button>
    </div>
    <div class="item-grid" id="wardrobe-grid"><div class="empty-state"><span class="emoji">👗</span>加载中…</div></div>`;
  page.innerHTML = html;

  loadWardrobe();
}

// 打开上传表单(bottom sheet 风格)
function openUploadSheet() {
  const cats = ['top','bottom','dress','outerwear','shoes','bag','accessory'];
  const catNames = {'top':'上装','bottom':'下装','dress':'连衣裙','outerwear':'外套','shoes':'鞋','bag':'包','accessory':'配饰'};
  const seasons = ['','spring','summer','autumn','winter','all'];
  const seasonNames = {'':'不限','spring':'春','summer':'夏','autumn':'秋','winter':'冬','all':'四季'};

  const overlay = document.createElement('div');
  overlay.id = 'wardrobe-upload-overlay';
  overlay.style = 'position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:100;display:flex;align-items:flex-end;justify-content:center;';
  overlay.innerHTML = `
    <div style="background:#fff;border-radius:16px 16px 0 0;padding:18px;max-width:420px;width:100%;max-height:90vh;overflow-y:auto;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
        <div style="font-size:17px;font-weight:600;">添加衣物</div>
        <button onclick="closeUploadSheet()" style="border:none;background:#f5f5f5;border-radius:50%;width:32px;height:32px;font-size:18px;cursor:pointer;">×</button>
      </div>

      <div style="margin-bottom:14px;">
        <div style="font-size:13px;color:#666;margin-bottom:6px;">照片(必填)</div>
        <div id="wardrobe-photo-preview" style="width:100%;aspect-ratio:1/1;max-height:240px;border:2px dashed #ddd;border-radius:12px;display:flex;align-items:center;justify-content:center;color:#999;background:#fafafa;overflow:hidden;cursor:pointer;" onclick="pickPhoto()">
          <div style="text-align:center;"><div style="font-size:42px;">📷</div><div style="font-size:13px;margin-top:4px;">点击拍照 / 选图</div></div>
        </div>
        <input type="file" id="wardrobe-photo-input" accept="image/*" capture="environment" style="display:none" onchange="onPhotoSelected(event)">
      </div>

      <div style="margin-bottom:12px;">
        <div style="font-size:13px;color:#666;margin-bottom:6px;">分类(必填)</div>
        <select id="wardrobe-cat" style="width:100%;padding:10px;border:1px solid #ddd;border-radius:8px;font-size:14px;background:#fff;" onchange="wardrobeCategory=this.value">
          ${cats.map(c=>`<option value="${c}" ${c===wardrobeCategory?'selected':''}>${catNames[c]}</option>`).join('')}
        </select>
      </div>

      <div style="margin-bottom:12px;">
        <div style="font-size:13px;color:#666;margin-bottom:6px;">名称(可选)</div>
        <input type="text" id="wardrobe-title" placeholder="如:白T恤" style="width:100%;padding:10px;border:1px solid #ddd;border-radius:8px;font-size:14px;box-sizing:border-box;">
      </div>

      <div style="margin-bottom:12px;">
        <div style="font-size:13px;color:#666;margin-bottom:6px;">颜色(可选)</div>
        <input type="text" id="wardrobe-color" placeholder="如:白/黑/米" style="width:100%;padding:10px;border:1px solid #ddd;border-radius:8px;font-size:14px;box-sizing:border-box;">
      </div>

      <div style="margin-bottom:16px;">
        <div style="font-size:13px;color:#666;margin-bottom:6px;">季节(可选)</div>
        <select id="wardrobe-season" style="width:100%;padding:10px;border:1px solid #ddd;border-radius:8px;font-size:14px;background:#fff;">
          ${seasons.map(s=>`<option value="${s}">${seasonNames[s]}</option>`).join('')}
        </select>
      </div>

      <div id="wardrobe-upload-status" style="font-size:13px;margin-bottom:10px;text-align:center;color:#666;"></div>

      <button id="wardrobe-upload-btn" onclick="submitUpload()" style="width:100%;padding:12px;border:none;border-radius:10px;background:linear-gradient(135deg,#FF6B9D,#FF8E72);color:#fff;font-size:15px;font-weight:600;cursor:pointer;">上传到衣橱</button>
    </div>
  `;
  document.body.appendChild(overlay);
  overlay.addEventListener('click', e => { if (e.target === overlay) closeUploadSheet(); });
}

function closeUploadSheet() {
  const el = document.getElementById('wardrobe-upload-overlay');
  if (el) el.remove();
}

function pickPhoto() {
  document.getElementById('wardrobe-photo-input').click();
}

function onPhotoSelected(ev) {
  const file = ev.target.files[0];
  if (!file) return;
  // 预览
  const reader = new FileReader();
  reader.onload = e => {
    const preview = document.getElementById('wardrobe-photo-preview');
    preview.innerHTML = `<img src="${e.target.result}" style="width:100%;height:100%;object-fit:cover;">`;
  };
  reader.readAsDataURL(file);
}

async function submitUpload() {
  const fileInput = document.getElementById('wardrobe-photo-input');
  const file = fileInput.files[0];
  if (!file) {
    document.getElementById('wardrobe-upload-status').textContent = '⚠️ 请先拍照或选图';
    document.getElementById('wardrobe-upload-status').style.color = '#E74C3C';
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
  status.textContent = '正在上传 + 后端生成 3 档缩略图…';
  status.style.color = '#666';

  try {
    const data = await postItem(formData);
    const item = data.item || data;
    status.textContent = '✅ 上传成功!';
    status.style.color = '#27AE60';
    setTimeout(() => {
      closeUploadSheet();
      loadWardrobe();
      if (item && item.id) toast(`已添加:${item.title || item.category}`);
    }, 600);
  } catch (e) {
    status.textContent = '❌ 上传失败: ' + (e.message || '未知错误');
    status.style.color = '#E74C3C';
    btn.disabled = false;
    btn.textContent = '重试上传';
  }
}

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
          <div class="item-title">${it.title || it.category}</div>
          <div class="item-badges">
            <span class="badge badge-cat">${it.category}</span>
            ${it.color ? `<span class="badge badge-color">${it.color}</span>` : ''}
          </div>
        </div>
      </div>`).join('');
  } catch(e) {
    console.error('[WARDROBE] listItems error:', e.name, e.message, e.stack);
    document.getElementById('wardrobe-grid').innerHTML =
      `<div class="empty-state"><span class="emoji">⚠️</span>加载失败:${e.name} | ${e.message}</div>`;
  }
}

function setWardrobeFilter(cat) {
  wardrobeFilter = cat;
  document.querySelectorAll('.filter-chip').forEach(chip => {
    chip.classList.toggle('active', chip.dataset.cat === cat);
  });
  loadWardrobe();
}

async function showItemDetail(id) {
  try {
    const it = (await getItem(id)).item || (await getItem(id));
    const overlay = document.createElement('div');
    overlay.style = 'position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:50;display:flex;align-items:center;justify-content:center;padding:20px;';
    overlay.innerHTML = `
      <div style="background:#fff;border-radius:12px;padding:20px;max-width:340px;width:100%;">
        <img src="${it.original_url || it.thumbnail_url}" style="width:100%;border-radius:8px;margin-bottom:12px;max-height:260px;object-fit:cover;">
        <div style="font-size:16px;font-weight:600;margin-bottom:6px;">${it.title || '无标题'}</div>
        <div class="item-badges" style="margin-bottom:10px;">
          <span class="badge badge-cat">${it.category}</span>
          ${it.color ? `<span class="badge badge-color">${it.color}</span>` : ''}
          ${it.season ? `<span class="badge" style="background:#E8F4FD;color:#2980B9;">${it.season}</span>` : ''}
        </div>
        ${it.brand ? `<div style="font-size:12px;color:#888;margin-bottom:4px;">品牌: ${it.brand}</div>` : ''}
        ${it.note ? `<div style="font-size:12px;color:#666;">备注: ${it.note}</div>` : ''}
        <div style="display:flex;gap:8px;margin-top:14px;">
          <button onclick="this.closest('[style]').parentElement.remove()" style="flex:1;padding:8px;border:1px solid #ddd;border-radius:8px;background:#fafafa;cursor:pointer;">关闭</button>
          <button onclick="confirmDeleteItem('${it.id}')" style="flex:1;padding:8px;border:none;border-radius:8px;background:#FFE5E5;color:#E74C3C;cursor:pointer;">删除</button>
        </div>
      </div>`;
    document.body.appendChild(overlay);
    overlay.addEventListener('click', e => { if (e.target === overlay) overlay.remove(); });
  } catch(e) { toast('加载详情失败'); }
}

async function confirmDeleteItem(id) {
  if (!confirm('确定删除这件衣服?')) return;
  try {
    await deleteItem(id);
    document.querySelectorAll('[style*="position:fixed"]').forEach(el => el.remove());
    toast('删除成功');
    loadWardrobe();
  } catch(e) { toast('删除失败'); }
}
