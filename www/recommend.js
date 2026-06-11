/* recommend.js - outfit recommendation page (standalone) */

(function () {
  var _sessionId = localStorage.getItem('laopodada_outfit_session') || (function () {
    var id = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
      var r = Math.random() * 16 | 0, v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
    localStorage.setItem('laopodada_outfit_session', id);
    return id;
  })();

  function getSessionId() { return localStorage.getItem('laopodada_outfit_session') || _sessionId; }

  /* ── page render ── */
  window.renderRecommendPage = function () {
    var page = document.getElementById('page-recommend');
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
  };

  /* ── main recommend flow ── */
  window.RecDoRecommend = async function () {
    var input = document.getElementById('r-context');
    var context = (input && input.value.trim()) ? input.value.trim() : null;
    if (!context) { toast('请输入场景描述'); return; }

    document.getElementById('rec-loading').style.display = '';
    document.getElementById('rec-error').style.display = 'none';
    document.getElementById('rec-result').innerHTML = '';

    try {
      var data = await fetch(window.API_BASE + '/api/v1/outfit/recommend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ context: context }),
      }).then(function (r) { return r.json(); });

      document.getElementById('rec-loading').style.display = 'none';
      renderOutfit(data);
      loadHistory();
    } catch (e) {
      document.getElementById('rec-loading').style.display = 'none';
      document.getElementById('rec-error').style.display = '';
      document.getElementById('rec-error').innerHTML = '<span class="emoji">⚠️</span> ' + e.message;
    }
  };

  function renderOutfit(data) {
    var container = document.getElementById('rec-result');
    if (!data || (!data.top && !data.bottom)) {
      container.innerHTML = '<div class="rec-empty"><span class="emoji">😅</span> 暂无推荐结果</div>';
      return;
    }
    var html = '<div class="rec-card">';
    if (data.top) {
      html += '<div class="rec-item">' +
        '<div class="rec-item-title">' + escHtml(data.top.title || '') + '</div>' +
        '<div class="rec-item-reason">' + escHtml(data.top.reason || '') + '</div></div>';
    }
    if (data.bottom) {
      html += '<div class="rec-item">' +
        '<div class="rec-item-title">' + escHtml(data.bottom.title || '') + '</div>' +
        '<div class="rec-item-reason">' + escHtml(data.bottom.reason || '') + '</div></div>';
    }
    if (data.occasion) {
      html += '<div class="rec-occasion"><span class="rec-label">场合:</span> ' + escHtml(data.occasion) + '</div>';
    }
    if (data.tips) {
      html += '<div class="rec-tips"><span class="rec-label">小贴士:</span> ' + escHtml(data.tips) + '</div>';
    }
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
      var items = data.history || data.recommendations || [];
      if (!items.length) {
        box.innerHTML = '<div class="rec-empty">暂无推荐记录</div>';
        return;
      }
      box.innerHTML = items.slice(0, 5).map(function (h) {
        return '<div class="rec-history-item">' +
          '<div class="rec-history-context">' + escHtml(h.context || h.occasion || '') + '</div>' +
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

  function toast(msg) {
    var t = document.getElementById('toast');
    if (!t) { t = document.createElement('div'); t.id = 'toast'; document.body.appendChild(t); }
    t.textContent = msg; t.className = 'toast show';
    setTimeout(function () { t.className = 'toast'; }, 2000);
  }
})();
