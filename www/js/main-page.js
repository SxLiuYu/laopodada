/* www/js/main-page.js — 主页 3 卡片渲染 + 跳 tab */

async function renderMainPage() {
  const page = document.getElementById('page-main');
  if (!page) {
    console.error('[renderMainPage] #page-main 不存在');
    return;
  }

  // 立刻同步渲染骨架屏 — 即使 fetch 失败,骨架也立即可见
  page.innerHTML = `
    <div class="main-page">
      <div class="main-greet">${getGreeting()},老婆 👋</div>
      <div class="main-greet-sub">今天想做点什么?</div>

      <div class="main-card main-card-skeleton"><div class="sk-icon skeleton"></div><div class="sk-texts"><div class="skeleton skeleton-text" style="width:80px;height:18px;"></div><div class="skeleton skeleton-text short" style="margin-top:8px;"></div></div></div>

      <div class="main-card main-card-skeleton"><div class="sk-icon skeleton"></div><div class="sk-texts"><div class="skeleton skeleton-text" style="width:80px;height:18px;"></div><div class="skeleton skeleton-text short" style="margin-top:8px;"></div></div></div>

      <div class="main-card main-card-skeleton"><div class="sk-icon skeleton"></div><div class="sk-texts"><div class="skeleton skeleton-text" style="width:80px;height:18px;"></div><div class="skeleton skeleton-text short" style="margin-top:8px;"></div></div></div>
    </div>
  `;

  // 异步加载统计,骨架屏替换为真实卡片
  try {
    const [w, r, b] = await Promise.all([
      listItems(null, 50).catch(e => { console.warn('[stats] listItems:', e.message); return { items: [] }; }),
      listRecipes(undefined, undefined, undefined, 50).catch(e => { console.warn('[stats] listRecipes:', e.message); return { recipes: [] }; }),
      listExpenses(undefined, undefined, 50).catch(e => { console.warn('[stats] listExpenses:', e.message); return { expenses: [], count: 0 }; }),
    ]);
    const stats = {
      wardrobe: (w.items || []).length,
      recipe: (r.recipes || []).length,
      bookkeeping: b.count || (b.expenses || []).length,
    };

    // 用真实数据替换骨架屏
    page.querySelector('.main-page').innerHTML = `
      <div class="main-greet">${getGreeting()},老婆 👋</div>
      <div class="main-greet-sub">今天想做点什么?</div>

      <div class="main-card main-card-wardrobe" data-goto="wardrobe">
        <div class="main-card-icon">👗</div>
        <div class="main-card-body">
          <h4>衣橱</h4>
          <p class="main-card-stat">${stats.wardrobe} 件单品 · 智能搭配</p>
          <div class="main-card-tag">✨ AI 穿搭推荐</div>
        </div>
      </div>

      <div style="display:flex;gap:10px;padding:0 16px 16px;">
        <button onclick="switchTab('recommend')" style="flex:1;padding:12px;border:none;border-radius:var(--r-md);background:var(--gradient);color:#fff;font-size:var(--fs-md);font-weight:600;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:6px;transition:transform .15s var(--ease);">
          🎯 今日穿搭推荐
        </button>
      </div>

      <div class="main-card main-card-recipe" data-goto="recipe">
        <div class="main-card-icon">🍳</div>
        <div class="main-card-body">
          <h4>点餐</h4>
          <p class="main-card-stat">${stats.recipe} 道菜谱 · 不知道吃啥?</p>
          <div class="main-card-tag">✨ AI 菜品推荐</div>
        </div>
      </div>

      <div class="main-card main-card-bookkeeping" data-goto="bookkeeping">
        <div class="main-card-icon">💰</div>
        <div class="main-card-body">
          <h4>记账</h4>
          <p class="main-card-stat">${stats.bookkeeping} 笔记录 · 花哪儿了?</p>
          <div class="main-card-tag">✨ 本月收支一目了然</div>
        </div>
      </div>
    `;

    // 卡片点击跳 tab
    page.querySelectorAll('.main-card').forEach(card => {
      card.onclick = () => {
        const target = card.dataset.goto;
        switchTab(target);
      };
    });
  } catch (e) {
    console.error('[renderMainPage] stats 加载失败:', e);
  }
}
