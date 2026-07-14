// API base for laopodada mobile app.
// Public deployment: https://123.57.107.21:8088 (laopodada-api on 123.57 VPS)
// Self-signed cert: clients must accept the cert warning on first visit.
// Override here for local dev (iOS sim = 192.168.1.10:8097, Android emu = 10.0.2.2:8097).
window.API_BASE = 'https://123.57.107.21:8088';

// Dev mode: localhost / file:// / 127.0.0.1 预览时不发真实 API 请求，返回空 mock 数据
window.IS_DEV = (function() {
  const h = location.hostname || '';
  const p = location.protocol || '';
  // 在 Capacitor WebView 里 hostname 是真实域名或 IP，不会命中 localhost/file
  if (h === 'localhost' || h === '127.0.0.1' || h === '' || p === 'file:') return true;
  // 端口 8xxx 通常是本地 dev server
  if (location.port && /^8\d{3}$/.test(location.port)) return true;
  return false;
})();

// 功能开关
window.FEATURES = {
  WEATHER: true,        // 天气功能
  AI_ASSISTANT: true,   // AI助手
  BOOKKEEPING: true,    // 记账功能
  WARDROBE: true,       // 衣橱功能
  RECIPE: true,         // 菜谱功能
  HEALTH_ARTICLES: false // 健康文章（已移除）
};

// 应用配置
window.APP_CONFIG = {
  NAME: '老婆哒哒',
  VERSION: '2.0.0',
  DESCRIPTION: '你的日常生活助手',
  AUTHOR: 'SxLiuYu',
  SUPPORT_EMAIL: 'support@laopodada.com'
};
