/* www/js/ai-fab.js — AI 浮动按钮通用组件 + 底部 sheet 弹窗 */

window.AIFab = {
  /**
   * 初始化 AI 浮动按钮(渐变 ✨)
   * @param {string} tabKey - tab 唯一标识(用于 id 区分多个 FAB)
   * @param {function} onClick - 点击回调(打开 sheet)
   */
  init(tabKey, onClick) {
    // 防止重复初始化
    const existing = document.getElementById(`ai-fab-${tabKey}`);
    if (existing) existing.remove();
    const fab = document.createElement('button');
    fab.className = 'ai-fab';
    fab.id = `ai-fab-${tabKey}`;
    fab.innerHTML = '✨';
    fab.title = 'AI 推荐';
    fab.onclick = onClick;
    document.body.appendChild(fab);
    return fab;
  },

  /**
   * 初始化衣橱拍照横条(黑色底部按钮)
   * @param {string} tabKey
   * @param {function} onClick - 点击回调(打开文件选择/相机)
   */
  initPhotoBar(tabKey, onClick) {
    const existing = document.getElementById(`photo-bar-${tabKey}`);
    if (existing) existing.remove();
    const bar = document.createElement('div');
    bar.className = 'ai-fab-photo-bar';
    bar.id = `photo-bar-${tabKey}`;
    bar.innerHTML = '📷 添加衣物到衣橱';
    bar.onclick = onClick;
    document.body.appendChild(bar);
    return bar;
  },

  /**
   * 打开 AI 底部 sheet 弹窗
   * @param {object} opts - { title, placeholder, onSubmit }
   *   onSubmit(text) -> Promise<{ html: string }>
   */
  openSheet(opts) {
    // 关闭已有 sheet
    this.closeSheet();

    const mask = document.createElement('div');
    mask.className = 'ai-sheet-mask open';
    mask.innerHTML = `
      <div class="ai-sheet">
        <h3>${opts.title || 'AI 推荐'}</h3>
        <textarea id="ai-sheet-input" placeholder="${opts.placeholder || '说说你想要什么...'}"></textarea>
        <button class="ai-submit" id="ai-sheet-submit">✨ 让 AI 想想</button>
        <div class="ai-result" id="ai-sheet-result" style="display:none;"></div>
      </div>
    `;
    document.body.appendChild(mask);

    const input = mask.querySelector('#ai-sheet-input');
    const submit = mask.querySelector('#ai-sheet-submit');
    const result = mask.querySelector('#ai-sheet-result');

    submit.onclick = async () => {
      const text = input.value.trim();
      if (!text) {
        alert('请输入内容');
        return;
      }
      submit.disabled = true;
      submit.textContent = '⏳ AI 思考中...';
      result.style.display = 'block';
      result.textContent = '请稍候,通常需要 30-90 秒...';

      try {
        const r = await opts.onSubmit(text);
        result.innerHTML = r.html;
        submit.textContent = '✓ 完成';
      } catch (e) {
        result.innerHTML = `<span style="color:#d44;">❌ ${e.message || 'AI 服务异常'}</span>`;
        submit.textContent = '重试';
        submit.disabled = false;
      }
    };

    // 点遮罩关闭(点 sheet 内部不关)
    mask.onclick = (e) => {
      if (e.target === mask) mask.remove();
    };
  },

  /**
   * 关闭 AI sheet
   */
  closeSheet() {
    const mask = document.querySelector('.ai-sheet-mask.open');
    if (mask) mask.remove();
  }
};
