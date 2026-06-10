/* recommend.js — 穿搭推荐页 */

let recommendSeason = '';
let recommendWeather = {};
let recommendOccasion = null;

function renderRecommendPage() {
  const page = document.getElementById('page-recommend');
  page.classList.add('active');
  page.innerHTML = `
    <div class="page-header">穿搭推荐</div>
    <div class="weather-row">
      <span class="weather-label">季节</span>
      <select id="r-season" onchange="recommendSeason=this.value">
        <option value="">不限</option>
        <option value="spring">春</option>
        <option value="summer">夏</option>
        <option value="fall">秋</option>
        <option value="winter">冬</option>
      </select>
      <span class="weather-label">温度</span>
      <input type="number" id="r-temp" placeholder="°C" onchange="recommendWeather.temp_c=parseFloat(this.value)||undefined">
      <span class="weather-label">天气</span>
      <select id="r-condition" onchange="recommendWeather.condition=this.value">
        <option value="">不限</option>
        <option value="sunny">晴</option>
        <option value="cloudy">多云</option>
        <option value="rainy">雨</option>
        <option value="snowy">雪</option>
      </select>
    </div>
    <div class="occasion-grid" id="occasion-grid">
      <button class="oc-btn casual" onclick="doRecommend('casual')">👟&nbsp;休闲</button>
      <button class="oc-btn work" onclick="doRecommend('work')">💼&nbsp;上班</button>
      <button class="oc-btn date" onclick="doRecommend('date')">💕&nbsp;约会</button>
      <button class="oc-btn party" onclick="doRecommend('party')">🎉&nbsp;派对</button>
    </div>
    <div id="outfit-results"></div>
  `;
}

async function doRecommend(occasion) {
  recommendOccasion = occasion;
  recommendWeather.temp_c = parseFloat(document.getElementById('r-temp').value) || undefined;
  recommendWeather.condition = document.getElementById('r-condition').value || undefined;
  const results = document.getElementById('outfit-results');
  results.innerHTML = `<div class="empty-state" style="padding:20px;"><span class="emoji">✨</span>正在为你搭配…</div>`;

  try {
    const before = Math.floor(Date.now() / 1000);
    const data = await recommendOutfit(occasion, recommendSeason || undefined, recommendWeather, 3);
    const outfits = data.outfits || [];
    if (!outfits.length) {
      results.innerHTML = `<div class="empty-state"><span class="emoji">😅</span>衣橱里没有足够的衣服<br>来搭配这个场合，先去添加几件吧～</div>`;
      return;
    }

    // Fetch ids for the outfits just created
    outfitIdMap = {};
    const recent = await listOutfits(outfits.length);
    const recentFiltered = (recent.outfits || []).filter(o => o.created_at >= before);
    recentFiltered.forEach((o, i) => { outfitIdMap[i] = o.id; });

    results.innerHTML = outfits.map((o, i) => `
      <div class="outfit-card" id="outfit-${i}">
        <div class="outfit-items">
          ${(o.items || []).map(item => `
            <img class="outfit-item-thumb" src="${item.thumb_url || item.list_url || ''}" alt="${item.title || item.category}"
                 onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 64 64%22><rect fill=%22%23f0f0f0%22 width=%2264%22 height=%2264%22/><text x=%2232%22 y=%2236%22 text-anchor=%22middle%22 fill=%22%23ccc%22 font-size=%2220%22>👗</text></svg>'">`).join('')}
        </div>
        <div class="outfit-reason">${o.reason || ''} ${o.llm_note ? '<br><small style="color:#999">'+o.llm_note+'</small>' : ''}</div>
        <div class="outfit-score">
          <span class="score-label">时尚分</span>
          <div class="score-bar"><div class="score-fill" style="width:${Math.round((o.style_score||0)*100)}%"></div></div>
          <span class="score-label">${Math.round((o.style_score||0)*100)}分</span>
        </div>
        <div class="outfit-actions">
          <button class="btn-like" onclick="sendFeedback(${i}, 1)">👍 推荐</button>
          <button class="btn-dislike" onclick="sendFeedback(${i}, -1)">👎 不喜欢</button>
        </div>
      </div>`).join('');
  } catch(e) {
    results.innerHTML = `<div class="empty-state"><span class="emoji">⚠️</span>推荐失败：${e.message}</div>`;
  }
}

// outfit ids indexed by card position
let outfitIdMap = {};

async function sendFeedback(idx, score) {
  const outfitId = outfitIdMap[idx];
  if (!outfitId) { toast('无效的 outfit'); return; }
  try {
    await feedbackOutfit(outfitId, score);
    const card = document.getElementById(`outfit-${idx}`);
    if (card) {
      card.querySelector('.outfit-actions').innerHTML =
        `<span style="color:#2E9E7D;font-size:13px;">已反馈 ${score > 0 ? '👍' : '👎'}，感谢～</span>`;
    }
    toast('反馈已记录 ✨');
  } catch(e) { toast('反馈失败'); }
}