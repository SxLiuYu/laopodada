/* chat.js — AI 咨询 */
// localStorage 容错: iOS Capacitor 在某些 scheme 下抛 SecurityError,
// 顶层调用会中断整个 script 链,导致后续 profile/ai-fab/main-page/app.js 全部不加载
let chatSessionId = null;
let chatHistory = [];  // [{role, content, ts}]

function getChatSessionId() {
  if (chatSessionId) return chatSessionId;
  try {
    chatSessionId = localStorage.getItem('chat_session_id');
    if (!chatSessionId) {
      chatSessionId = 'web-' + Date.now() + '-' + Math.random().toString(36).slice(2,8);
      try { localStorage.setItem('chat_session_id', chatSessionId); } catch (e) { /* 内存模式 */ }
    }
  } catch (e) {
    console.warn('[chat] localStorage 不可用, 使用内存 session:', e.message);
    chatSessionId = 'mem-' + Date.now() + '-' + Math.random().toString(36).slice(2,8);
  }
  return chatSessionId;
}

function renderChatPage() {
  const page = document.getElementById('page-chat');
  page.innerHTML = `
    <div class="page-header" style="display:flex;align-items:center;gap:10px;">
      <button class="chat-back-btn" onclick="switchTab('main')">← 主页</button>
      <span style="flex:1;">🤖 AI 助手</span>
    </div>
    <div class="chat-hint">基于 MiniMax M3 的中文 AI 助手 · 有问必答</div>
    <div class="chat-messages" id="chat-messages"></div>
    <div class="chat-quickbar">
      <button onclick="sendQuickChat('今天天气怎么样?')">🌤 天气</button>
      <button onclick="sendQuickChat('推荐早餐')">🍳 早餐</button>
      <button onclick="sendQuickChat('讲个笑话')">😄 笑话</button>
      <button onclick="sendQuickChat('如何搭配衣服')">👗 穿搭</button>
      <button onclick="clearChat()">🗑 清空</button>
    </div>
    <div class="chat-input-bar">
      <textarea id="chat-input" placeholder="问我任何事..." rows="1"
        oninput="autoGrowTextarea(this)" onkeydown="handleChatKeydown(event)"></textarea>
      <button onclick="sendChat()">发送</button>
    </div>
  `;
  loadChatHistory();
}

async function loadChatHistory() {
  try {
    const data = await getChatHistory(getChatSessionId(), 50);
    chatHistory = (data.history || data.messages || []).map(m => ({role: m.role, content: m.content, ts: m.timestamp || m.created_at || null}));
    renderChatMessages();
  } catch (e) {
    console.warn('history load failed', e);
    renderChatMessages();  // 渲染空
  }
}

function renderChatMessages() {
  const box = document.getElementById('chat-messages');
  if (!chatHistory.length) {
    box.innerHTML = '<div class="chat-welcome">👋 你好!我是你的 AI 助手,有什么可以帮你的?</div>';
    return;
  }
  box.innerHTML = chatHistory.map((m, i) => {
    const timeStr = m.ts ? formatDate(m.ts) : '';
    const showTime = !timeStr || i === 0 || !chatHistory[i-1]?.ts || (m.ts - chatHistory[i-1].ts > 120);
    return `
      ${showTime && timeStr ? `<div style="text-align:center;font-size:11px;color:var(--text-placeholder);margin:8px 0 4px;">${timeStr}</div>` : ''}
      <div class="chat-msg chat-${m.role}">
        <div class="chat-bubble">${escapeHtml(m.content)}</div>
      </div>`;
  }).join('');
  box.scrollTop = box.scrollHeight;
}

async function sendChat() {
  const input = document.getElementById('chat-input');
  const msg = input.value.trim();
  if (!msg) return;
  input.value = '';
  autoGrowTextarea(input);
  // 立刻显示 user 消息
  chatHistory.push({role:'user', content:msg, ts: Math.floor(Date.now()/1000)});
  renderChatMessages();
  // 显示 "正在输入..."
  const box = document.getElementById('chat-messages');
  const typing = document.createElement('div');
  typing.id = 'typing-indicator';
  typing.className = 'chat-msg chat-assistant';
  typing.innerHTML = '<div class="chat-bubble">⏳ 思考中...</div>';
  box.appendChild(typing);
  box.scrollTop = box.scrollHeight;
  // 计数
  try {
    const cnt = parseInt(localStorage.getItem('chat_count') || '0') + 1;
    localStorage.setItem('chat_count', String(cnt));
  } catch(e) {}
  try {
    const resp = await chatWithAI(msg, getChatSessionId());
    document.getElementById('typing-indicator')?.remove();
    chatHistory.push({role:'assistant', content: resp.reply || '(无回复)', ts: Math.floor(Date.now()/1000)});
    renderChatMessages();
  } catch (e) {
    document.getElementById('typing-indicator')?.remove();
    chatHistory.push({role:'assistant', content: '❌ AI 暂时不可用: ' + e.message, ts: Math.floor(Date.now()/1000)});
    renderChatMessages();
  }
}

function sendQuickChat(text) {
  const input = document.getElementById('chat-input');
  if (input) input.value = text;
  sendChat();
}

function clearChat() {
  confirmAction('清空当前对话?', () => {
    chatHistory = [];
    chatSessionId = 'web-' + Date.now() + '-' + Math.random().toString(36).slice(2,8);
    try { localStorage.setItem('chat_session_id', chatSessionId); } catch (e) {}
    renderChatMessages();
  });
}

function handleChatKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendChat();
  }
}

function autoGrowTextarea(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}