/* utils.js — 公共工具函数，所有页面共享 */

/* ── HTML 转义 ── */
function escapeHtml(s) {
  return String(s || '').replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;',
    '"': '&quot;', "'": '&#39;'
  })[c]);
}

/* ── Toast (带 slide-up 动画) ── */
let _toastTimer = null;
function toast(msg, duration = 2000) {
  const el = document.getElementById('toast');
  if (!el) return;
  clearTimeout(_toastTimer);
  el.textContent = msg;
  el.classList.add('show');
  _toastTimer = setTimeout(() => {
    el.classList.remove('show');
  }, duration);
}

/* ── 创建 Modal overlay（居中弹窗） ── */
function createModal(html, opts = {}) {
  const overlay = document.createElement('div');
  overlay.className = 'overlay';
  if (opts.maxWidth) overlay.querySelector('.modal-box')?.style.setProperty('max-width', opts.maxWidth);
  overlay.innerHTML = `
    <div class="modal-box" ${opts.maxWidth ? 'style="max-width:' + opts.maxWidth + '"' : ''}>
      ${html}
    </div>`;
  // 点击遮罩关闭
  overlay.addEventListener('click', e => {
    if (e.target === overlay) overlay.remove();
  });
  document.body.appendChild(overlay);
  return overlay;
}

/* ── 创建 Bottom Sheet（底部弹窗） ── */
function createBottomSheet(html, opts = {}) {
  const overlay = document.createElement('div');
  overlay.className = 'overlay overlay-bottom';
  overlay.innerHTML = `<div class="bottom-sheet">${html}</div>`;
  overlay.addEventListener('click', e => {
    if (e.target === overlay) overlay.remove();
  });
  document.body.appendChild(overlay);
  return overlay;
}

/* ── 关闭所有 overlay ── */
function closeAllOverlays() {
  document.querySelectorAll('.overlay, .overlay-bottom').forEach(el => el.remove());
}

/* ── 确认对话框（替代原生 confirm） ── */
function confirmAction(message, onConfirm) {
  const overlay = createModal(`
    <div class="modal-box-body" style="text-align:center;padding:24px;">
      <div style="font-size:15px;margin-bottom:20px;color:var(--text-primary);">${escapeHtml(message)}</div>
      <div class="btn-action-row">
        <button class="btn-outline" onclick="this.closest('.overlay').remove()">取消</button>
        <button class="btn-danger" id="confirm-ok" style="background:var(--primary);color:#fff;">确定</button>
      </div>
    </div>`, { maxWidth: '320px' });
  overlay.querySelector('#confirm-ok').onclick = () => {
    overlay.remove();
    if (onConfirm) onConfirm();
  };
}

/* ── 日期格式化 ── */
function formatDate(ts) {
  const d = ts ? new Date(ts * 1000) : null;
  if (!d) return '';
  return `${d.getMonth()+1}/${d.getDate()} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;
}

/* ── 动态问候语 ── */
function getGreeting() {
  const h = new Date().getHours();
  if (h < 6) return '夜深了';
  if (h < 9) return '早上好';
  if (h < 12) return '上午好';
  if (h < 14) return '中午好';
  if (h < 18) return '下午好';
  if (h < 22) return '晚上好';
  return '夜深了';
}
