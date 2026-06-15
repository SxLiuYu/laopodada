/* recommend.js - 穿搭推荐页 (LLM-powered, context-based) */

(function () {
  var _sessionId = localStorage.getItem('laopodada_outfit_session') || (function () {
    var id = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
      var r = Math.random() * 16 | 0, v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
    localStorage.setItem('laopodada_outfit_session', id);
    return id;
  })();

  function getSessionId() {
    return localStorage.getItem('laopodada_outfit_session') || _sessionId;
  }

  function setSessionId(id) {
    localStorage.setItem('laopodada_outfit_session', id);
    _sessionId = id;
  }

  /* ── page render ── */
  function renderRecommendPage() {
    var page = document.getElementById('page-recommend');
    page.classList.add('active');
    page.innerHTML =
      '<div class="page-header">穿搭推荐</div>' +
      '<div class="rec-input-area">' +
        '<input id="r-context" class="rec-text-input" type="text" placeholder="今天的场景是...?" maxlength="200" />' +
        '<button class="rec-btn-generate" onclick="RecDoRecommend()">生成推荐</button>' +
      '</div>' +
      '<div id="rec-loading" class="rec-loading" style="display:none"><span class="emoji">✨</span> 正在为你搭配&hellip;</div>' +
      '<div id="rec-error" class="rec-error" style="display:none"></div>' +
      '<div id="rec-result"></div>' +
      '<div class="rec-history-header">最近推荐</div>' +
      '<div id="rec-history"><div class="rec-empty">加载中&hellip;</div></div>';
    loadHistory();
  }

  /* ── fetch wardrobe items (for thumbnails) ── */
  function getItemThumb(itemId, itemsMap) {
    var item = itemsMap[itemId];
    if (!item) return 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect fill="%23f0f0f0" width="64" height="64"/><text x="32" y="36" text-anchor="middle" fill="%23ccc" font-size="20">👗</text></svg>';
    return item.thumb_url || item.list_url || '';
  }

  /* ── main recommend flow ── */
  window.RecDoRecommend = async function () {
    var input = document.getElementById('r-context');
    var context = (input && input.value.trim()) ? input.value.trim() : null;
    if (!context) {
      toast('请输入场景描述'); return;
    }

    document.getElementById('rec-loading').style.display = '';
    document.getElementById('rec-error').style.display = 'none';
    document.getElementById('rec-result').innerHTML = '';

    try {
      /* 1. fetch wardrobe items for thumbnail lookup */
      var itemsData = await listItems('all', 50);
      var itemsMap = {};
      (itemsData.items || []).forEach(function (it) { itemsMap[it.id] = it; });

      /* 2. call recommend endpoint */
      var data = await fetch(window.API_BASE + '/api/v1/outfit/recommend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ context: context }),
      }).then(function (r) { return r.json(); });

      document.getElementById('rec-loading').style.display = 'none';
      renderOutfit(data, itemsMap);
      loadHistory(); /* refresh history */
    } catch (e) {
      document.getElementById('rec-loading').style.display = 'none';
      document.getElementById('rec-error').style.display = '';
      document.getElementById('rec-error').innerHTML = '<span class="emoji">⚠️</span> ' + e.message;
    }
  };

  function renderOutfit(data, itemsMap) {
    var container = document.getElementById('rec-result');
    if (!data || !data.top_item_id && !data.bottom_item_id) {
      container.innerHTML = '<div class="rec-empty"><span class="emoji">😅</span> 衣橱里没有足够的衣服<br>来搭配这个场合，先去添加几件吧～</div>';
      return;
    }

    var topItem = itemsMap[data.top_item_id];
    var bottomItem = itemsMap[data.bottom_item_id];

    var html = '<div class="rec-card">';
    if (topItem) {
      html += '<div class="rec-item">' +
        '<img class="rec-thumb" src="' + (topItem.thumb_url || '') + '" alt="上装" onerror="this.src=\'data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 64 64%22><rect fill=%22%23f0f0f0%22 width=%2264%22 height=%2264%22/><text x=%2232%22 y=%2236%22 text-anchor=%22middle%22 fill=%22%23ccc%22 font-size=%2220%22>👕</text></svg>\'" />' +
        '<div class="rec-item-label">上装</div></div>';
    }
    if (bottomItem) {
      html += '<div class="rec-item">' +
        '<img class="rec-thumb" src="' + (bottomItem.thumb_url || '') + '" alt="下装" onerror="this.src=\'data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 64 64%22><rect fill=%22%23f0f0f0%22 width=%2264%22 height=%2264%22/><text x=%2232%22 y=%2236%22 text-anchor=%22middle%22 fill=%22%23ccc%22 font-size=%2220%22>👖</text></svg>\'" />' +
        '<div class="rec-item-label">下装</div></div>';
    }
    html += '<div class="rec-occasion">' + (data.occasion || '') + '</div>';
    html += '<div class="rec-tips">' + (data.tips || '') + '</div>';
    html += '</div>';
    container.innerHTML = html;
  }

  /* ── history ── */
  async function loadHistory() {
    var sid = getSessionId();
    var box = document.getElementById('rec-history');
    if (!box) return;
    try {
      var data = await fetch(window.API_BASE + '/api/v1/outfit/history?session_id=' + encodeURIComponent(sid))
        .then(function (r) { return r.json(); });
      var items = data.history || [];
      if (!items.length) {
        box.innerHTML = '<div class="rec-empty">暂无推荐记录</div>';
        return;
      }
      box.innerHTML = items.slice(0, 5).map(function (h) {
        return '<div class="rec-history-item">' +
          '<div class="rec-history-context">' + escHtml(h.context || '') + '</div>' +
          '<div class="rec-history-occasion">' + escHtml(h.occasion || '') + '</div>' +
          '<div class="rec-history-time">' + (h.created_at ? new Date(h.created_at * 1000).toLocaleString() : '') + '</div>' +
        '</div>';
      }).join('');
    } catch (e) {
      box.innerHTML = '<div class="rec-empty">加载历史失败</div>';
    }
  }

  function escHtml(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  /* ── expose for tab switch ── */
  window.renderRecommendPage = renderRecommendPage;
})();
