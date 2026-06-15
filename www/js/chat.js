/* chat.js — AI 咨询 */
let chatSessionId = localStorage.getItem('chat_session_id');
if (!chatSessionId) {
  chatSessionId = 'web-' + Date.now() + '-' + Math.random().toString(36).slice(2,8);
  localStorage.setItem('chat_session_id', chatSessionId);
}
let chatHistory = [];  // [{role, content, ts}]

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
      <input id="chat-input" placeholder="问我任何事..." onkeydown="if(event.key==='Enter')sendChat()">
      <button onclick="sendChat()">发送</button>
    </div>
  `;
  loadChatHistory();
}

async function loadChatHistory() {
  try {
    const data = await getChatHistory(chatSessionId, 50);
    chatHistory = (data.history || data.messages || []).map(m => ({role: m.role, content: m.content}));
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
  box.innerHTML = chatHistory.map(m => `
    <div class="chat-msg chat-${m.role}">
      <div class="chat-bubble">${escapeHtml(m.content)}</div>
    </div>
  `).join('');
  box.scrollTop = box.scrollHeight;
}

async function sendChat() {
  const input = document.getElementById('chat-input');
  const msg = input.value.trim();
  if (!msg) return;
  input.value = '';
  // 立刻显示 user 消息
  chatHistory.push({role:'user', content:msg});
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
    const resp = await chatWithAI(msg, chatSessionId);
    document.getElementById('typing-indicator')?.remove();
    chatHistory.push({role:'assistant', content: resp.reply || '(无回复)'});
    renderChatMessages();
  } catch (e) {
    document.getElementById('typing-indicator')?.remove();
    chatHistory.push({role:'assistant', content: '❌ AI 暂时不可用: ' + e.message});
    renderChatMessages();
  }
}

function sendQuickChat(text) {
  const input = document.getElementById('chat-input');
  if (input) input.value = text;
  sendChat();
}

function clearChat() {
  if (!confirm('清空当前对话?')) return;
  chatHistory = [];
  chatSessionId = 'web-' + Date.now() + '-' + Math.random().toString(36).slice(2,8);
  localStorage.setItem('chat_session_id', chatSessionId);
  renderChatMessages();
}

function escapeHtml(s) {
  return String(s||'').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]);
}