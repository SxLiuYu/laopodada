/* pull-refresh.js — 下拉刷新（Capacitor 原生支持） */

let _pullRefreshActive = false;

async function enablePullRefresh(refreshFn) {
  // Only available in native Capacitor
  if (!window.Capacitor?.isNativePlatform?.()) return;
  try {
    const { App } = window.Capacitor.Plugins || {};
    if (!App) return;
    await App.addListener('pullToRefresh', async () => {
      if (_pullRefreshActive) return;
      _pullRefreshActive = true;
      try {
        await refreshFn();
      } catch (e) {
        console.warn('[pullRefresh]', e);
      } finally {
        // Dismiss the pull-to-refresh indicator
        try { await App.dismissPullToRefresh(); } catch(e) {}
        _pullRefreshActive = false;
      }
    });
    await App.setEnabledPullToRefresh({ enabled: true });
    console.log('[pullRefresh] enabled');
  } catch (e) {
    // Plugin not available — silently ignore
    console.log('[pullRefresh] not available');
  }
}
