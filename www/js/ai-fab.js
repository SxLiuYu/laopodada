/* www/js/ai-fab.js — 增强版AI浮动按钮：上下文感知智能助手 */

window.AIFab = {
  currentTab: 'main',
  
  /**
   * 初始化全局 AI 浮动按钮
   */
  init() {
    const existing = document.getElementById('ai-fab-global');
    if (!existing) return;
    
    existing.onclick = () => this.openAssistant();
  },

  /**
   * 打开 AI 智能助手
   */
  openAssistant() {
    this.closeAssistant();
    
    const mask = document.createElement('div');
    mask.className = 'ai-assistant-mask';
    mask.innerHTML = `
      <div class="ai-assistant">
        <div class="assistant-header">
          <h3>✨ AI 小助手</h3>
          <button class="close-btn" onclick="AIFab.closeAssistant()">✕</button>
        </div>
        <div class="assistant-content" id="assistant-content">
          <div class="quick-actions">
            <div class="quick-action" data-type="outfit">👗 搭配建议</div>
            <div class="quick-action" data-type="recipe">🍳 菜谱推荐</div>
            <div class="quick-action" data-type="budget">💰 预算分析</div>
            <div class="quick-action" data-type="weather">🌤️ 天气穿衣</div>
          </div>
          <div class="chat-area" id="chat-area">
            <div class="message ai-message">
              <div class="message-content">你好呀！我是你的小助手，有什么可以帮你的吗？</div>
            </div>
          </div>
          <div class="input-area">
            <input type="text" id="ai-input" placeholder="输入你的问题..." />
            <button id="ai-send" onclick="AIFab.sendMessage()">发送</button>
          </div>
        </div>
      </div>
    `;
    
    document.body.appendChild(mask);
    
    // 绑定快捷操作事件
    mask.querySelectorAll('.quick-action').forEach(action => {
      action.onclick = () => {
        const type = action.dataset.type;
        this.handleQuickAction(type);
      };
    });
  },

  /**
   * 关闭 AI 助手
   */
  closeAssistant() {
    const mask = document.querySelector('.ai-assistant-mask');
    if (mask) mask.remove();
  },

  /**
   * 处理快捷操作
   */
  async handleQuickAction(type) {
    const chatArea = document.getElementById('chat-area');
    if (!chatArea) return;
    
    // 添加用户消息
    const userMessages = {
      outfit: '帮我推荐今天的穿搭',
      recipe: '推荐一道简单的菜',
      budget: '分析一下我的消费',
      weather: '今天应该怎么穿衣服'
    };
    
    chatArea.innerHTML += `
      <div class="message user-message">
        <div class="message-content">${userMessages[type]}</div>
      </div>
    `;
    
    // 显示思考中
    chatArea.innerHTML += `
      <div class="message ai-message thinking">
        <div class="message-content">🤔 AI 正在思考...</div>
      </div>
    `;
    
    // 滚动到底部
    chatArea.scrollTop = chatArea.scrollHeight;
    
    try {
      // 调用后端AI接口
      const response = await this.callAI(type);
      
      // 移除思考中的消息
      const thinkingMsg = chatArea.querySelector('.thinking');
      if (thinkingMsg) thinkingMsg.remove();
      
      // 添加AI回复
      chatArea.innerHTML += `
        <div class="message ai-message">
          <div class="message-content">${response}</div>
        </div>
      `;
      
    } catch (e) {
      console.error('AI调用失败:', e);
      const thinkingMsg = chatArea.querySelector('.thinking');
      if (thinkingMsg) thinkingMsg.remove();
      
      chatArea.innerHTML += `
        <div class="message ai-message error">
          <div class="message-content">😅 抱歉，AI 服务暂时不可用</div>
        </div>
      `;
    }
    
    // 滚动到底部
    chatArea.scrollTop = chatArea.scrollHeight;
  },

  /**
   * 发送用户消息
   */
  async sendMessage() {
    const input = document.getElementById('ai-input');
    const chatArea = document.getElementById('chat-area');
    const message = input.value.trim();
    
    if (!message) return;
    
    // 添加用户消息
    chatArea.innerHTML += `
      <div class="message user-message">
        <div class="message-content">${message}</div>
      </div>
    `;
    
    input.value = '';
    
    // 显示思考中
    chatArea.innerHTML += `
      <div class="message ai-message thinking">
        <div class="message-content">🤔 AI 正在思考...</div>
      </div>
    `;
    
    chatArea.scrollTop = chatArea.scrollHeight;
    
    try {
      // 调用后端AI接口
      const response = await this.callGeneralAI(message);
      
      // 移除思考中的消息
      const thinkingMsg = chatArea.querySelector('.thinking');
      if (thinkingMsg) thinkingMsg.remove();
      
      // 添加AI回复
      chatArea.innerHTML += `
        <div class="message ai-message">
          <div class="message-content">${response}</div>
        </div>
      `;
      
    } catch (e) {
      console.error('AI调用失败:', e);
      const thinkingMsg = chatArea.querySelector('.thinking');
      if (thinkingMsg) thinkingMsg.remove();
      
      chatArea.innerHTML += `
        <div class="message ai-message error">
          <div class="message-content">😅 抱歉，AI 服务暂时不可用</div>
        </div>
      `;
    }
    
    // 滚动到底部
    chatArea.scrollTop = chatArea.scrollHeight;
  },

  /**
   * 调用特定类型的AI接口
   */
  async callAI(type) {
    const endpoints = {
      outfit: '/api/v1/outfit/recommend',
      recipe: '/api/v1/recipes/generate',
      budget: '/api/v1/expenses/summary',
      weather: '/api/v1/outfit/recommend' // 暂时复用穿搭接口
    };
    
    const endpoint = endpoints[type];
    if (!endpoint) throw new Error('未知的AI类型');
    
    const response = await fetch(`${CONFIG.API_BASE_URL}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    
    if (!response.ok) throw new Error('AI请求失败');
    
    const data = await response.json();
    return this.formatAIResponse(data, type);
  },

  /**
   * 调用通用AI接口
   */
  async callGeneralAI(message) {
    // 这里可以调用LLM接口，暂时返回模拟响应
    const responses = [
      '好的，我来帮你想想...',
      '这是个很好的问题！让我分析一下...',
      '根据你的生活数据，我建议...',
      '别担心，我有几个不错的想法...'
    ];
    
    // 模拟网络延迟
    await new Promise(resolve => setTimeout(resolve, 11000));
    
    return responses[Math.floor(Math.random() * responses.length)] + '\n\n' + 
           '这是一个模拟的AI回复。在实际部署中，这里会调用真实的LLM服务。';
  },

  /**
   * 格式化AI响应
   */
  formatAIResponse(data, type) {
    switch (type) {
      case 'outfit':
        return `👗 穿搭建议：\n\n根据今天的天气和你的衣橱，建议你穿：\n${this.formatOutfitAdvice(data)}`;
      case 'recipe':
        return `🍳 菜谱推荐：\n\n试试这道菜：\n${this.formatRecipeAdvice(data)}`;
      case 'budget':
        return `💰 消费分析：\n\n本月总支出：¥${data.total || '0.00'}\n主要支出类别：${this.formatBudgetAdvice(data)}`;
      default:
        return '收到你的请求，正在处理中...';
    }
  },

  /**
   * 格式化穿搭建议
   */
  formatOutfitAdvice(data) {
    if (data.outfit) {
      return data.outfit.map(item => `• ${item.title} (${item.color})`).join('\n');
    }
    return '• 上衣：选择舒适的T恤\n• 下装：搭配休闲裤\n• 鞋子：运动鞋最合适';
  },

  /**
   * 格式化菜谱建议
   */
  formatRecipeAdvice(data) {
    if (data.recipe) {
      return `菜名：${data.recipe.title}\n难度：${data.recipe.difficulty}\n准备时间：${data.recipe.prep_minutes}分钟`;
    }
    return '• 番茄炒蛋：简单美味\n• 清蒸鱼：健康营养\n• 青菜豆腐汤：清淡可口';
  },

  /**
   * 格式化预算建议
   */
  formatBudgetAdvice(data) {
    if (data.breakdown && data.breakdown.length > 0) {
      return data.breakdown.slice(0, 3).map(cat => 
        `${cat.category}: ¥${cat.amount}`
      ).join('、');
    }
    return '暂无数据';
  }
};

// 初始化AI FAB
document.addEventListener('DOMContentLoaded', () => {
  AIFab.init();
});
