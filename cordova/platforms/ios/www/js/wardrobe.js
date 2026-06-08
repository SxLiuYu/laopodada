/* wardrobe.js — 衣橱页 */

let wardrobeFilter = 'all';

function renderWardrobePage() {
  const page = document.getElementById('page-wardrobe');

  // filter chips
  const cats = ['all','top','bottom','dress','outerwear','shoes','bag','accessory'];
  const catNames = {'all':'全部','top':'上装','bottom':'下装','dress':'连衣裙','outerwear':'外套','shoes':'鞋','bag':'包','accessory':'配饰'};
  let html = `<div class="filter-bar">`;
  for (const c of cats) {
    html += `<button class="filter-chip${c === wardrobeFilter ? ' active' : ''}" data-cat="${c}" onclick="setWardrobeFilter('${c}')">${catNames[c]}</button>`;
  }
  html += `</div><div class="item-grid" id="wardrobe-grid"><div class="empty-state"><span class="emoji">👗</span>加载中…</div></div>`;
  page.innerHTML = html;

  loadWardrobe();
}

async function loadWardrobe() {
  try {
    const data = await listItems(wardrobeFilter === 'all' ? null : wardrobeFilter, 50);
    const items = data.items || [];
    const grid = document.getElementById('wardrobe-grid');
    if (!items.length) {
      grid.innerHTML = `<div class="empty-state"><span class="emoji">👗</span>衣橱空空，<br>快去拍照添加吧～</div>`;
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
    document.getElementById('wardrobe-grid').innerHTML =
      `<div class="empty-state"><span class="emoji">⚠️</span>加载失败：${e.message}</div>`;
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
  if (!confirm('确定删除这件衣服？')) return;
  try {
    await deleteItem(id);
    document.querySelectorAll('[style*="position:fixed"]').forEach(el => el.remove());
    toast('删除成功');
    loadWardrobe();
  } catch(e) { toast('删除失败'); }
}