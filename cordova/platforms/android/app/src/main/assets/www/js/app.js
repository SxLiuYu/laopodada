/* app.js — 老婆哒哒 衣橱 App 入口 */

function toast(msg) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.style.display = 'block';
  setTimeout(() => { el.style.display = 'none'; }, 2000);
}

function switchTab(tab) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  const btn = document.querySelector(`.tab-btn[data-tab="${tab}"]`);
  const page = document.getElementById(`page-${tab}`);
  if (btn) btn.classList.add('active');
  if (page) {
    page.classList.add('active');
    if (tab === 'wardrobe' && !page.querySelector('.filter-bar')) renderWardrobePage();
    if (tab === 'camera') renderCameraPage();
    if (tab === 'recommend' && !page.querySelector('.occasion-grid')) renderRecommendPage();
    if (tab === 'profile' && !page.querySelector('.profile-stats')) renderProfilePage();
  }
}

document.addEventListener('DOMContentLoaded', () => {
  switchTab('wardrobe');
});