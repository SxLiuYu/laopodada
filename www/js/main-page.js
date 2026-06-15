/* www/js/main-page.js — 主页 3 卡片渲染 + 跳 tab */

async function renderMainPage() {
  const page = document.getElementById('page-main');
  if (!page) return;

  // 拉统计(并行 3 端点)
  let wardrobeCount = 0, recipeCount = 0, healthCount = 0;
  try {
    const [w, r, h] = await Promise.all([
      listItems(null, 50).catch(() => ({ items: [] })),
      listRecipes(undefined, undefined, undefined, 50).catch(() => ({ recipes: [] })),
      listHealthArticles(undefined, 50).catch(() => ({ articles: [] })),
    ]);
    wardrobeCount = (w.items || []).length;
    recipeCount = (r.recipes || []).length;
    healthCount = (h.articles || []).length;
  } catch (e) {
    console.warn('主页统计加载失败:', e);
  }

  page.innerHTML = `
    <div class="main-page">
      <div class="main-greet">嗨,老婆 👋</div>
      <div class="main-greet-sub">今天想做点什么?</div>

      <div class="main-card main-card-wardrobe" data-goto="wardrobe">
        <div class="main-card-icon">👗</div>
        <div class="main-card-body">
          <h4>衣橱</h4>
          <p>${wardrobeCount} 件单品 · 智能搭配</p>
          <div class="main-card-tag">✨ AI 穿搭推荐</div>
        </div>
      </div>

      <div class="main-card main-card-recipe" data-goto="recipe">
        <div class="main-card-icon">🍳</div>
        <div class="main-card-body">
          <h4>点餐</h4>
          <p>${recipeCount} 道菜谱 · 不知道吃啥?</p>
          <div class="main-card-tag">✨ AI 菜品推荐</div>
        </div>
      </div>

      <div class="main-card main-card-health" data-goto="health">
        <div class="main-card-icon">💪</div>
        <div class="main-card-body">
          <h4>健康</h4>
          <p>${healthCount} 篇文章 · 想了解啥?</p>
          <div class="main-card-tag">✨ AI 健康科普</div>
        </div>
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
}
