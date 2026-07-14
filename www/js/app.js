/* app.js — 老婆哒哒 App 入口 */

// toast 已迁移到 utils.js，此处仅保留全局错误捕获

function switchTab(tabKey) {
  // 隐藏所有 page
  document.querySelectorAll('.page').forEach(p => {
    p.style.display = 'none';
    p.classList.remove('active');
  });
  // 显示目标 page
  const target = document.getElementById(`page-${tabKey}`);
  if (target) {
    target.style.display = 'flex';
    target.classList.add('active');
    // 触发对应 render
    if (tabKey === 'main') renderMainPage();
    else if (tabKey === 'wardrobe') renderWardrobePage();
    else if (tabKey === 'recommend') renderRecommendPage();
    else if (tabKey === 'recipe') renderRecipePage();
    else if (tabKey === 'bookkeeping') renderBookkeepingPage();
    else if (tabKey === 'profile') renderProfilePage();
  }
  // tab 样式
  document.querySelectorAll('.tabbar .tab').forEach(t => t.classList.remove('active'));
  const activeTab = document.querySelector(`.tabbar .tab[data-tab="${tabKey}"]`);
  if (activeTab) activeTab.classList.add('active');
}

document.addEventListener('DOMContentLoaded', () => {
  // tab 点击
  document.querySelectorAll('.tabbar .tab').forEach(tab => {
    tab.onclick = () => switchTab(tab.dataset.tab);
  });
  // 默认进主页
  switchTab('main');

  // 全局 AI FAB - 悬浮按钮,所有页面可见
  AIFab.init('global', () => {
    AIFab.openSheet({
      title: '✨ AI 小助手',
      placeholder: '比如：帮我搭配今天穿什么、推荐一道菜、问问最近开销...',
      onSubmit: async (text) => {
        const result = await chatWithAI(
          text,
          localStorage.getItem('chat_session_id') || ('web-' + Date.now() + '-' + Math.random().toString(36).slice(2, 8))
        );
        localStorage.setItem('chat_session_id', result.session_id || '');
        return { html: `<div class="ai-result-card"><div class="ai-content">${escapeHtml(result.reply || '(无回复)')}</div></div>` };
      },
    });
  });
});

// 全局 JS 错误捕获 — 任何 script 抛错都打 console,方便 iOS Safari 远程调试
window.addEventListener('error', (e) => {
  console.error('[global] JS error:', e.message, '@', e.filename || '?', ':', e.lineno || '?');
});
window.addEventListener('unhandledrejection', (e) => {
  console.error('[global] unhandled rejection:', e.reason?.message || e.reason);
});
