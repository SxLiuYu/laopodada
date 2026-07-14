/* www/js/main-page.js — 增强版主页：天气 + 统计 + AI建议 */

// 天气API配置（使用免费的wttr.in）
const WEATHER_API = 'https://wttr.in/?format=%c+%t+%w';

// 获取问候语
function getGreeting() {
  const hour = new Date().getHours();
  if (hour < 6) return '夜深了';
  if (hour < 9) return '早安';
  if (hour < 12) return '上午好';
  if (hour < 14) return '中午好';
  if (hour < 18) return '下午好';
  if (hour < 22) return '晚上好';
  return '夜深了';
}

// 加载天气信息
async function loadWeather() {
  if (!window.FEATURES.WEATHER) return;
  
  try {
    const response = await fetch(WEATHER_API);
    if (!response.ok) throw new Error('天气API失败');
    
    const data = await response.text();
    // 解析 wttr.in 返回的数据格式: "☀️ +22°C 🌤️"
    const parts = data.trim().split(/\s+/);
    const weather = parts[0] || '🌤️';
    const temp = parts[1] || '--°C';
    const wind = parts[2] || '';
    
    const widget = document.getElementById('weather-widget');
    if (widget) {
      widget.innerHTML = `
        <div style="display:flex;align-items:center;justify-content:center;gap:8px;">
          <span style="font-size:20px;">${weather}</span>
          <span style="font-size:16px;font-weight:600;">${temp}</span>
          ${wind ? `<span style="font-size:12px;color:#666;">${wind}</span>` : ''}
        </div>
      `;
    }
  } catch (e) {
    console.warn('天气加载失败:', e);
    const widget = document.getElementById('weather-widget');
    if (widget) {
      widget.innerHTML = `<div style="font-size:12px;color:#999;text-align:center;">天气暂时不可用</div>`;
    }
  }
}

// 加载统计数据
async function loadStats() {
  try {
    const [w, r, b] = await Promise.all([
      listItems(null, 50).catch(e => ({ items: [] })),
      listRecipes(undefined, undefined, undefined, 50).catch(e => ({ recipes: [] })),
      listExpenses(undefined, undefined, 50).catch(e => ({ expenses: [], count: 0 })),
    ]);
    
    const stats = {
      wardrobe: (w.items || []).length,
      recipe: (r.recipes || []).length,
      bookkeeping: b.count || (b.expenses || []).length,
      todayExpense: 0,
      weekExpense: 0,
    };
    
    // 计算今日和本周支出
    if (b.expenses) {
      const now = new Date();
      const today = now.toISOString().slice(0, 10);
      const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
      
      stats.todayExpense = b.expenses
        .filter(e => e.expense_date === today)
        .reduce((sum, e) => sum + e.amount, 0);
        
      stats.weekExpense = b.expenses
        .filter(e => new Date(e.expense_date) >= weekAgo)
        .reduce((sum, e) => sum + e.amount, 0);
    }
    
    // 更新统计卡片
    const statsGrid = document.getElementById('stats-grid');
    if (statsGrid) {
      statsGrid.innerHTML = `
        <div class="stat-card">
          <div class="stat-value">${stats.wardrobe}</div>
          <div class="stat-label">衣橱单品</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">${stats.recipe}</div>
          <div class="stat-label">收藏菜谱</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">¥${stats.todayExpense.toFixed(0)}</div>
          <div class="stat-label">今日支出</div>
        </div>
      `;
    }
  } catch (e) {
    console.warn('统计加载失败:', e);
  }
}

// 加载AI建议
async function loadAISuggestions() {
  if (!window.FEATURES.AI_ASSISTANT) return;
  
  try {
    // 获取今日天气和季节信息
    const hour = new Date().getHours();
    const suggestions = [];
    
    // 根据时间生成建议
    if (hour < 9) {
      suggestions.push({
        text: '早上好！今天天气不错，适合穿浅色系的衣服出门哦～',
        source: '穿搭建议'
      });
    } else if (hour < 12) {
      suggestions.push({
        text: '快到午饭时间啦，试试做那道新学的红烧肉吧！',
        source: '菜谱建议'
      });
    } else if (hour < 14) {
      suggestions.push({
        text: '午餐后记得散步消食哦，健康最重要～',
        source: '健康建议'
      });
    } else if (hour < 18) {
      suggestions.push({
        text: '今天花了多少钱啦？记得记一笔账哦～',
        source: '记账提醒'
      });
    } else {
      suggestions.push({
        text: '晚上好！明天想穿什么呢？现在就可以看看衣橱啦～',
        source: '穿搭建议'
      });
    }
    
    // 随机添加一条额外建议
    if (Math.random() > 0.5) {
      suggestions.push({
        text: '💡 小贴士：定期整理衣橱，保持清爽好心情！',
        source: '生活建议'
      });
    }
    
    const adviceCard = document.getElementById('ai-advice');
    if (adviceCard) {
      const selected = suggestions[Math.floor(Math.random() * suggestions.length)];
      adviceCard.innerHTML = `
        <div class="advice-text">${selected.text}</div>
        <div class="advice-source">— ${selected.source}</div>
      `;
    }
  } catch (e) {
    console.warn('AI建议加载失败:', e);
  }
}

// 渲染主页
async function renderMainPage() {
  const page = document.getElementById('page-main');
  if (!page) {
    console.error('[renderMainPage] #page-main 不存在');
    return;
  }

  // 设置问候语
  const header = page.querySelector('.page-header');
  if (header) {
    header.textContent = `${getGreeting()},老婆 👋`;
  }

  // 加载各种数据
  await Promise.all([
    loadWeather(),
    loadStats(),
    loadAISuggestions(),
  ]);

  // 绑定快捷操作事件
  page.querySelectorAll('.action-card').forEach(card => {
    card.onclick = () => {
      const action = card.dataset.action;
      if (action === 'wardrobe') {
        switchTab('wardrobe');
      } else if (action === 'recipe') {
        switchTab('recipe');
      } else if (action === 'bookkeeping') {
        openExpenseSheet(); // 打开记账弹窗
      }
    };
  });
}

// 页面切换时刷新主页
const originalSwitchTab = window.switchTab;
window.switchTab = function(tab) {
  originalSwitchTab(tab);
  if (tab === 'main') {
    renderMainPage();
  }
};

// 初始化主页
document.addEventListener('DOMContentLoaded', () => {
  renderMainPage();
});
