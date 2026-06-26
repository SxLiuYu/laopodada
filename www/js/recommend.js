/* recommend.js — AI 穿搭推荐页 */

const OCCASION_LIST = [
  { key: 'casual', label: '休闲', emoji: '☀️' },
  { key: 'work',   label: '通勤', emoji: '💼' },
  { key: 'date',   label: '约会', emoji: '💕' },
  { key: 'sport',  label: '运动', emoji: '🏃' },
  { key: 'party',  label: '派对', emoji: '🎉' },
  { key: 'home',   label: '居家', emoji: '🏠' },
];

let _recommendLoading = false;
let _currentOutfits = [];

function renderRecommendPage() {
  const page = document.getElementById('page-recommend');
  if (!page) return;

  page.innerHTML = `
    <div class="page-header" style="display:flex;align-items:center;gap:var(--sp-2);">
      <button onclick="switchTab('wardrobe')" style="background:none;border:none;color:#fff;font-size:18px;cursor:pointer;padding:0;">←</button>
      <span>今日穿搭推荐</span>
    </div>

    <div class="recommend-body">
      <!-- 场景 tab -->
      <div class="recommend-scene-bar" id="rec-scene-bar">
        ${OCCASION_LIST.map((s, i) => `
          <button class="scene-chip${i === 0 ? ' active' : ''}" data-scene="${s.key}" onclick="switchScene('${s.key}')">
            ${s.emoji} ${s.label}
          </button>
        `).join('')}
      </div>

      <!-- 推荐结果 -->
      <div id="rec-results" class="recommend-results">
        <div class="rec-loading">
          <div class="skeleton skeleton-text" style="width:200px;height:20px;margin:var(--sp-4) auto;"></div>
          <div style="display:flex;gap:var(--sp-3);padding:0 var(--sp-4);">
            <div class="skeleton" style="width:64px;height:64px;border-radius:var(--r-sm);"></div>
            <div class="skeleton" style="width:64px;height:64px;border-radius:var(--r-sm);"></div>
            <div class="skeleton" style="width:64px;height:64px;border-radius:var(--r-sm);"></div>
          </div>
        </div>
      </div>

      <!-- 个性化输入 -->
      <div class="rec-personalize">
        <div class="rec-personalize-title">不满意？试试个性化推荐</div>
        <div class="rec-personalize-bar">
          <input type="text" id="rec-custom-input" class="form-input"
                 placeholder="如：今天约会，穿得优雅一点，25度"
                 style="font-size:var(--fs-md);">
          <button class="ai-btn" id="rec-custom-btn" onclick="requestCustomRecommend()">✨ 生成</button>
        </div>
      </div>
    </div>
  `;

  // 自动加载第一套推荐
  switchScene('casual');
}

async function switchScene(scene) {
  // 更新 tab 样式
  document.querySelectorAll('.scene-chip').forEach(chip => {
    chip.classList.toggle('active', chip.dataset.scene === scene);
  });

  // 加载推荐
  const results = document.getElementById('rec-results');
  results.innerHTML = `
    <div class="rec-loading">
      <div class="skeleton skeleton-text" style="width:200px;height:20px;margin:var(--sp-4) auto;"></div>
      <div style="display:flex;gap:var(--sp-3);padding:0 var(--sp-4);">
        <div class="skeleton" style="width:64px;height:64px;border-radius:var(--r-sm);"></div>
        <div class="skeleton" style="width:64px;height:64px;border-radius:var(--r-sm);"></div>
        <div class="skeleton" style="width:64px;height:64px;border-radius:var(--r-sm);"></div>
      </div>
    </div>`;

  try {
    // 同时请求多个 limit=1 的不同搭配(同场景最多 3 种组合)
    const [r1, r2, r3] = await Promise.allSettled([
      api.recommendOutfit(scene, undefined, {}, 1),
      api.recommendOutfit(scene, undefined, {}, 2),
      api.recommendOutfit(scene, undefined, {}, 3),
    ]);

    const outfits = [r1, r2, r3]
      .map(r => {
        if (r.status === 'fulfilled' && r.value.outfits?.length) return r.value.outfits[0];
        return null;
      })
      .filter(Boolean);

    _currentOutfits = outfits;

    if (!outfits.length) {
      results.innerHTML = `<div class="empty-state"><span class="emoji">👗</span>衣橱里还没有衣服<br>先去添加几件再来吧</div>`;
      return;
    }

    results.innerHTML = outfits.map((outfit, i) => renderOutfitCard(outfit, i)).join('');
  } catch (e) {
    results.innerHTML = `<div class="empty-state"><span class="emoji">⚠️</span>加载失败，请重试</div>`;
  }
}

function renderOutfitCard(outfit, index) {
  const items = outfit.items || [];
  const score = outfit.style_score || 0;
  const reason = outfit.reason || '';

  const itemsHtml = items.map(it => `
    <div class="rec-item-thumb" onclick="event.stopPropagation();showItemDetail('${it.id}')">
      <img src="${it.thumb_url || it.list_url}" alt="${escapeHtml(it.title || it.category)}" loading="lazy"
           onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 64 64%22><rect fill=%22%23f0f0f0%22 width=%2264%22 height=%2264%22/><text x=%2232%22 y=%2238%22 text-anchor=%22middle%22 fill=%22%23999%22 font-size=%2214%22>?</text></svg>'">
      <div class="rec-item-label">${escapeHtml(it.title || it.category)}</div>
    </div>
  `).join('');

  return `
    <div class="outfit-card" style="animation-delay:${index * 0.1}s;">
      <div class="outfit-score">
        <span class="score-label">搭配指数</span>
        <div class="score-bar"><div class="score-fill" style="width:${Math.round(score * 100)}%;"></div></div>
        <span class="score-label" style="font-weight:600;color:var(--primary);">${Math.round(score * 100)}</span>
      </div>
      <div class="outfit-items">${itemsHtml}</div>
      <div class="outfit-reason">${escapeHtml(reason)}</div>
      ${outfit.llm_note ? `<div class="rec-llm-note">💡 ${escapeHtml(outfit.llm_note)}</div>` : ''}
      <div class="outfit-actions">
        <button class="btn-like" onclick="likeOutfit(${index})">👍 不错</button>
        <button class="btn-like" onclick="saveOutfit(${index})">💾 保存</button>
        <button class="btn-dislike" onclick="dislikeOutfit(${index})">🔄 换一套</button>
      </div>
    </div>`;
}

async function likeOutfit(index) {
  const outfit = _currentOutfits[index];
  if (!outfit) return;
  // 尝试反馈(可能没有 outfit_id，静默处理)
  if (outfit.outfit_id) {
    try { await api.feedbackOutfit(outfit.outfit_id, 1); } catch (e) { console.warn('[rec] feedback:', e); }
  }
  toast('这套不错，记下了~');
}

async function dislikeOutfit(index) {
  const outfit = _currentOutfits[index];
  if (!outfit) return;
  if (outfit.outfit_id) {
    try { await api.feedbackOutfit(outfit.outfit_id, -1); } catch (e) { console.warn('[rec] feedback:', e); }
  }
  // 重新请求该场景
  const activeScene = document.querySelector('.scene-chip.active')?.dataset.scene || 'casual';
  switchScene(activeScene);
}

async function requestCustomRecommend() {
  const input = document.getElementById('rec-custom-input');
  const btn = document.getElementById('rec-custom-btn');
  const text = (input?.value || '').trim();
  if (!text) {
    toast('请输入你的需求');
    return;
  }

  const results = document.getElementById('rec-results');
  btn.disabled = true;
  btn.textContent = '生成中...';
  results.innerHTML = `
    <div class="rec-loading" style="text-align:center;padding:var(--sp-6);">
      <div style="font-size:28px;margin-bottom:var(--sp-2);">🤖</div>
      <div style="color:var(--text-hint);font-size:var(--fs-md);">AI 正在为你搭配...</div>
    </div>`;

  try {
    const resp = await api.generateOutfit(text);
    const outfit = resp.outfit;
    if (!outfit) throw new Error('no outfit returned');

    const card = renderOutfitCard(outfit, 0);
    results.innerHTML = `<div style="margin-top:var(--sp-2);color:var(--success);font-size:var(--fs-sm);padding:0 var(--sp-3);">✨ AI 个性化推荐</div>${card}`;
    _currentOutfits = [outfit];
    btn.disabled = false;
    btn.textContent = '✨ 生成';
  } catch (e) {
    results.innerHTML = `<div class="ai-error">生成失败: ${escapeHtml(e.message)}</div>`;
    btn.disabled = false;
    btn.textContent = '✨ 生成';
  }
}

function saveOutfit(index) {
  const outfit = _currentOutfits[index];
  if (!outfit) return;
  try {
    let saved = JSON.parse(localStorage.getItem('saved_outfits') || '[]');
    saved.push({
      items: outfit.items || [],
      description: outfit.description || '',
      reason: outfit.reason || '',
      tips: outfit.llm_note || outfit.tips || '',
      style_score: outfit.style_score || 0,
      saved_at: Date.now(),
    });
    // Keep max 30
    if (saved.length > 30) saved = saved.slice(-30);
    localStorage.setItem('saved_outfits', JSON.stringify(saved));
    toast('穿搭已保存 💾');
  } catch (e) {
    toast('保存失败');
  }
}
