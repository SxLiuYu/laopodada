/* skeleton.js — 骨架屏工具函数 */

function renderGridSkeleton(containerId, cols = 2, rows = 3) {
  const el = document.getElementById(containerId);
  if (!el) return;
  let html = '<div class="item-grid">';
  for (let i = 0; i < cols * rows; i++) {
    html += `
      <div style="border-radius:var(--r-md);overflow:hidden;background:var(--bg-white);">
        <div class="skeleton" style="width:100%;aspect-ratio:1;"></div>
        <div style="padding:var(--sp-2);">
          <div class="skeleton skeleton-text" style="width:60%;height:14px;"></div>
          <div class="skeleton skeleton-text short" style="width:40%;height:10px;margin-top:6px;"></div>
        </div>
      </div>`;
  }
  html += '</div>';
  el.innerHTML = html;
}

function renderListSkeleton(containerId, rows = 4) {
  const el = document.getElementById(containerId);
  if (!el) return;
  let html = '';
  for (let i = 0; i < rows; i++) {
    html += `
      <div style="background:var(--bg-white);border-radius:var(--r-md);padding:var(--sp-3);margin-bottom:8px;">
        <div class="skeleton skeleton-text" style="width:70%;height:16px;"></div>
        <div class="skeleton skeleton-text short" style="width:90%;height:12px;margin-top:8px;"></div>
        <div class="skeleton skeleton-text short" style="width:50%;height:10px;margin-top:6px;"></div>
      </div>`;
  }
  el.innerHTML = html;
}
