/* profile.js — 我的页面 */

let profileCache = { items: 0, outfits: 0, feedbacks: 0 };

function renderProfilePage() {
  const page = document.getElementById('page-profile');
  page.classList.add('active');
  page.innerHTML = `
    <div class="page-header" style="display:flex;align-items:center;justify-content:space-between;">
      <span>我的</span>
      <button onclick="loadProfileStats()" style="background:none;border:none;color:#fff;font-size:12px;cursor:pointer;padding:4px 8px;border-radius:6px;border:1px solid rgba(255,255,255,.4);">🔄 同步</button>
    </div>
    <div class="profile-stats" id="profile-stats">
      <div class="stat-card">
        <div class="stat-num" id="stat-items">–</div>
        <div class="stat-lbl">衣橱单品</div>
      </div>
      <div class="stat-card">
        <div class="stat-num" id="stat-outfits">–</div>
        <div class="stat-lbl">推荐次数</div>
      </div>
      <div class="stat-card">
        <div class="stat-num" id="stat-feedbacks">–</div>
        <div class="stat-lbl">已反馈</div>
      </div>
    </div>
    <div style="padding:10px 14px 6px;font-size:13px;color:#888;font-weight:600;">最近推荐</div>
    <div class="history-list" id="history-list">
      <div class="empty-state"><span class="emoji">📋</span>加载中…</div>
    </div>
  `;
  loadProfileStats();
}

async function loadProfileStats() {
  try {
    const [itemsData, outfitsData, feedbackData] = await Promise.all([
      listItems(null, 1),
      listOutfits(20),
      getFeedbackCount().catch(() => ({ count: 0, last_feedback_at: null })),
    ]);
    const totalItems = itemsData.count || 0;
    const outfits = outfitsData.outfits || [];
    const totalFeedbacks = feedbackData.count || 0;

    document.getElementById('stat-items').textContent = totalItems;
    document.getElementById('stat-outfits').textContent = outfits.length;
    document.getElementById('stat-feedbacks').textContent = totalFeedbacks;

    // store for optimistic updates
    profileCache.feedbacks = totalFeedbacks;

    const list = document.getElementById('history-list');
    if (!outfits.length) {
      list.innerHTML = `<div class="empty-state"><span class="emoji">📋</span>还没有推荐记录</div>`;
      return;
    }
    list.innerHTML = outfits.map(o => {
      const date = o.created_at ? new Date(o.created_at * 1000) : null;
      const dateStr = date ? `${date.getMonth()+1}/${date.getDate()} ${date.getHours()}:${String(date.getMinutes()).padStart(2,'0')}` : '';
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