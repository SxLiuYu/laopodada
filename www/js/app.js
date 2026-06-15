/* app.js — 老婆哒哒 App 入口 */

function toast(msg) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.style.display = 'block';
  setTimeout(() => { el.style.display = 'none'; }, 2000);
}

function switchTab(tabKey) {
  // 隐藏所有 page
  document.querySelectorAll('.page').forEach(p => p.style.display = 'none');
  // 显示目标 page
  const target = document.getElementById(`page-${tabKey}`);
  if (target) {
    target.style.display = 'block';
    // 触发对应 render
    if (tabKey === 'main') renderMainPage();
    else if (tabKey === 'wardrobe') renderWardrobePage();
    else if (tabKey === 'recipe') renderRecipePage();
    else if (tabKey === 'health') renderHealthPage();
    else if (tabKey === 'chat') renderChatPage();
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
});
