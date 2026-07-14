/* profile.js — 我的页面 */

function renderProfilePage() {
  const page = document.getElementById('page-profile');
  page.classList.add('active');
  page.innerHTML = `
    <div class="page-header">我的</div>
    <div class="profile-stats" id="profile-stats">
      <div class="stat-card">
        <div class="stat-num" id="stat-items">–</div>
        <div class="stat-lbl">衣橱单品</div>
      </div>
      <div class="stat-card">
        <div class="stat-num" id="stat-recipes">–</div>
        <div class="stat-lbl">菜谱</div>
      </div>
      <div class="stat-card">
        <div class="stat-num" id="stat-expenses">–</div>
        <div class="stat-lbl">记账笔数</div>
      </div>
      <div class="stat-card">
        <div class="stat-num" id="stat-expense-month">–</div>
        <div class="stat-lbl">本月支出</div>
      </div>
    </div>

    <!-- 设置区域 -->
    <div style="padding:var(--sp-3) var(--sp-4) var(--sp-2);font-size:var(--fs-md);color:var(--text-hint);font-weight:600;">设置</div>
    <div style="padding:0 var(--sp-4);">
      <div class="profile-settings-item" onclick="clearAllCache()">
        <span>🗑️ 清除缓存</span>
        <span style="color:var(--text-placeholder);font-size:var(--fs-sm);">释放本地存储空间</span>
      </div>
      <div class="profile-settings-item" onclick="exportData()">
        <span>📤 导出数据</span>
        <span style="color:var(--text-placeholder);font-size:var(--fs-sm);">衣橱/菜谱/穿搭记录</span>
      </div>
      <div class="profile-settings-item" onclick="showAbout()">
        <span>ℹ️ 关于</span>
        <span style="color:var(--text-placeholder);font-size:var(--fs-sm);">老婆哒哒 v1.1</span>
      </div>
    </div>

    <div style="padding:var(--sp-3) var(--sp-4) var(--sp-2);font-size:var(--fs-md);color:var(--text-hint);font-weight:600;">最近推荐</div>
    <div class="history-list" id="history-list">
      <div class="empty-state"><span class="emoji">📋</span>加载中…</div>
    </div>
  `;

  // 注入设置项样式
  if (!document.getElementById('profile-settings-style')) {
    const s = document.createElement('style');
    s.id = 'profile-settings-style';
    s.textContent = `
      .profile-settings-item {
        display: flex; justify-content: space-between; align-items: center;
        padding: var(--sp-3); background: var(--bg-white); border-radius: var(--r-sm);
        margin-bottom: 6px; box-shadow: var(--shadow-sm); cursor: pointer;
        transition: transform .15s var(--ease); font-size: var(--fs-md); color: var(--text-primary);
      }
      .profile-settings-item:active { transform: scale(.98); }
    `;
    document.head.appendChild(s);
  }

  loadProfileStats();
}

async function loadProfileStats() {
  try {
    const [itemsData, recipesData, expData, sumData, outfitsData] = await Promise.all([
      listItems(null, 1),
      listRecipes(undefined, undefined, undefined, 1),
      listExpenses('', '', 1),
      expensesSummary(new Date().toISOString().slice(0, 7)),
      listOutfits(20),
    ]);
    document.getElementById('stat-items').textContent = itemsData.count || 0;
    document.getElementById('stat-recipes').textContent = recipesData.count || recipesData.total || 0;
    document.getElementById('stat-expenses').textContent = expData.count || 0;
    document.getElementById('stat-expense-month').textContent = '¥' + ((sumData.total || 0).toFixed(0));

    const outfits = outfitsData.outfits || [];
    const list = document.getElementById('history-list');
    if (!outfits.length) {
      list.innerHTML = `<div class="empty-state"><span class="emoji">📋</span>还没有推荐记录</div>`;
      return;
    }
    list.innerHTML = outfits.map(o => {
      const dateStr = formatDate(o.created_at);
      return `
        <div class="history-item">
          <div>
            <div class="history-occasion">${occasionLabel(o.occasion)}</div>
            <div class="history-meta">${dateStr} · ${(o.items||[]).length} 件</div>
          </div>
          <div style="text-align:right;">
            <div class="history-score">${Math.round((o.style_score||0)*100)} 分</div>
          </div>
        </div>`;
    }).join('');
  } catch(e) {
    document.getElementById('history-list').innerHTML =
      `<div class="empty-state"><span class="emoji">⚠️</span>加载失败</div>`;
  }
}

function occasionLabel(oc) {
  const map = { casual:'👟 休闲', work:'💼 上班', date:'💕 约会', party:'🎉 派对', sport:'🏃 运动', home:'🏠 居家' };
  return map[oc] || oc || '未知';
}

/* ── 设置功能 ── */

function clearAllCache() {
  confirmAction('确定清除所有本地缓存？(聊天记录、阅读标记等)', () => {
    try {
      const keysToKeep = ['chat_session_id', 'chat_count'];
      const toRemove = [];
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (!keysToKeep.includes(key)) toRemove.push(key);
      }
      toRemove.forEach(k => localStorage.removeItem(k));
      toast(`已清除 ${toRemove.length} 项缓存`);
      loadProfileStats();
    } catch (e) {
      toast('清除失败');
    }
  });
}

function exportData() {
  const data = {};
  try {
    const keys = [];
    for (let i = 0; i < localStorage.length; i++) keys.push(localStorage.key(i));
    keys.forEach(k => { try { data[k] = JSON.parse(localStorage.getItem(k)); } catch { data[k] = localStorage.getItem(k); } });
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `laopodada_backup_${new Date().toISOString().slice(0,10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast('数据已导出');
  } catch (e) {
    toast('导出失败');
  }
}

function showAbout() {
  createModal(`
    <div style="text-align:center;padding:var(--sp-5);">
      <div style="font-size:48px;margin-bottom:var(--sp-2);">💕</div>
      <div style="font-size:var(--fs-xl);font-weight:700;margin-bottom:4px;">老婆哒哒</div>
      <div style="font-size:var(--fs-sm);color:var(--text-hint);margin-bottom:var(--sp-4);">v1.1.0</div>
      <div style="font-size:var(--fs-base);color:var(--text-secondary);line-height:1.6;">
        一个私人助理 App<br>
        衣橱管理 · 点餐决策 · 记账 · AI 穿搭
      </div>
      <button class="btn-primary" style="margin-top:var(--sp-4);max-width:200px;" onclick="this.closest('.overlay').remove()">知道了</button>
    </div>
  `, { maxWidth: '300px' });
}
