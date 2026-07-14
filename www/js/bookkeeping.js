/* www/js/bookkeeping.js — 增强版记账模块 */

const BK_CATEGORIES = {
  food: { label: '餐饮', icon: '🍜' },
  transport: { label: '交通', icon: '🚗' },
  shopping: { label: '购物', icon: '🛍' },
  entertainment: { label: '娱乐', icon: '🎮' },
  housing: { label: '住房', icon: '🏠' },
  health: { label: '健康', icon: '💊' },
  education: { label: '学习', icon: '📚' },
  beauty: { label: '美容', icon: '💄' },
  gift: { label: '人情', icon: '🎁' },
  other: { label: '其他', icon: '📌' },
};

let _bkCategory = 'all';
let _bkMonth = new Date().toISOString().slice(0, 7); // YYYY-MM

function renderBookkeepingPage() {
  const page = document.getElementById('page-bookkeeping');
  if (!page) return;
  page.innerHTML = `
    <div class="page-header">💰 记账</div>
    <div class="bk-summary" id="bk-summary">
      <div class="skeleton skeleton-text" style="width:120px;height:20px;margin:12px auto;"></div>
    </div>
    <div class="filter-bar" id="bk-month-bar"></div>
    <div class="filter-bar" id="bk-cat-bar"></div>
    <div class="bk-list" id="bk-list">
      <div class="skeleton skeleton-text" style="width:80%;margin:12px 16px;"></div>
      <div class="skeleton skeleton-text short" style="width:60%;margin:0 16px 12px;"></div>
    </div>
    <div class="bk-add-bar" id="bk-add-bar">
      <button class="btn-primary" onclick="openExpenseSheet()">+ 记一笔</button>
    </div>
  `;
  renderMonthBar();
  renderCatBar();
  loadExpenses();
}

function renderMonthBar() {
  const bar = document.getElementById('bk-month-bar');
  if (!bar) return;
  const now = new Date();
  const months = [];
  for (let i = 2; i >= 0; i--) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    const m = d.toISOString().slice(0, 7);
    months.push({ value: m, label: `${d.getFullYear()}年${d.getMonth() + 1}月` });
  }
  bar.innerHTML = months.map(m =>
    `<div class="filter-chip${m.value === _bkMonth ? ' active' : ''}" data-month="${m.value}">${m.label}</div>`
  ).join('');
  bar.querySelectorAll('.filter-chip').forEach(chip => {
    chip.onclick = () => {
      _bkMonth = chip.dataset.month;
      renderMonthBar();
      loadExpenses();
    };
  });
}

function renderCatBar() {
  const bar = document.getElementById('bk-cat-bar');
  if (!bar) return;
  const chips = [{ key: 'all', label: '全部' }];
  for (const [key, val] of Object.entries(BK_CATEGORIES)) {
    chips.push({ key, label: val.icon + ' ' + val.label });
  }
  bar.innerHTML = chips.map(c =>
    `<div class="filter-chip${c.key === _bkCategory ? ' active' : ''}" data-cat="${c.key}">${c.label}</div>`
  ).join('');
  bar.querySelectorAll('.filter-chip').forEach(chip => {
    chip.onclick = () => {
      _bkCategory = chip.dataset.cat;
      renderCatBar();
      loadExpenses();
    };
  });
}

async function loadExpenses() {
  const listEl = document.getElementById('bk-list');
  const summaryEl = document.getElementById('bk-summary');
  if (!listEl) return;

  try {
    const [expData, sumData] = await Promise.all([
      listExpenses(_bkCategory === 'all' ? '' : _bkCategory, _bkMonth, 100),
      expensesSummary(_bkMonth),
    ]);
    const expenses = expData.expenses || [];
    const total = sumData.total || 0;
    const breakdown = sumData.breakdown || [];

    // Summary
    const [year, month] = _bkMonth.split('-');
    let topCats = breakdown.slice(0, 3).map(c =>
      `${(BK_CATEGORIES[c.category] || {}).icon || '📌'} ¥${c.amount}`
    ).join(' ');
    if (!topCats) topCats = '暂无记录';

    summaryEl.innerHTML = `
      <div class="bk-total">
        <div class="bk-total-label">${year}年${parseInt(month)}月</div>
        <div class="bk-total-amount">¥${total.toFixed(2)}</div>
        <div class="bk-total-cats">${topCats}</div>
      </div>
    `;

    // List
    if (expenses.length === 0) {
      listEl.innerHTML = `<div class="empty-state"><span class="emoji">📝</span>还没有记录，点下方按钮记一笔吧</div>`;
      return;
    }

    listEl.innerHTML = expenses.map(e => {
      const cat = BK_CATEGORIES[e.category] || { icon: '📌', label: e.category };
      return `
        <div class="bk-item" data-id="${e.id}">
          <div class="bk-item-icon">${cat.icon}</div>
          <div class="bk-item-body">
            <div class="bk-item-cat">${cat.label}${e.note ? ' · ' + e.note : ''}</div>
            <div class="bk-item-date">${e.expense_date}</div>
          </div>
          <div class="bk-item-amount">-¥${e.amount.toFixed(2)}</div>
          <div class="bk-item-del" onclick="deleteExpenseEntry('${e.id}', event)">×</div>
        </div>
      `;
    }).join('');
  } catch (e) {
    listEl.innerHTML = `<div class="empty-state"><span class="emoji">⚠️</span>加载失败: ${e.message}</div>`;
  }
}

function openExpenseSheet() {
  const catOptions = Object.entries(BK_CATEGORIES).map(([k, v]) =>
    `<option value="${k}">${v.icon} ${v.label}</option>`
  ).join('');

  const sheet = document.createElement('div');
  sheet.className = 'overlay overlay-bottom';
  sheet.innerHTML = `
    <div class="bottom-sheet">
      <div class="sheet-header">
        <span class="sheet-title">💸 记一笔</span>
        <button class="modal-box-close" onclick="this.closest('.overlay').remove()">✕</button>
      </div>
      <div class="form-field">
        <label class="form-label">金额</label>
        <input type="number" id="exp-amount" class="form-input" placeholder="0.00" step="0.01" min="0.01" autofocus>
      </div>
      <div class="form-field">
        <label class="form-label">分类</label>
        <select id="exp-category" class="form-select">${catOptions}</select>
      </div>
      <div class="form-field">
        <label class="form-label">日期</label>
        <input type="date" id="exp-date" class="form-input" value="${new Date().toISOString().slice(0, 10)}">
      </div>
      <div class="form-field">
        <label class="form-label">备注</label>
        <input type="text" id="exp-note" class="form-input" placeholder="买了什么...">
      </div>
      <button class="btn-primary" onclick="submitExpense(this.closest('.overlay'))">✓ 确认记账</button>
    </div>
  `;
  document.body.appendChild(sheet);

  // 点遮罩关闭
  sheet.onclick = (e) => {
    if (e.target === sheet) sheet.remove();
  };
}

async function submitExpense(overlay) {
  const amount = parseFloat(document.getElementById('exp-amount')?.value);
  const category = document.getElementById('exp-category')?.value;
  const expenseDate = document.getElementById('exp-date')?.value;
  const note = document.getElementById('exp-note')?.value.trim();

  if (!amount || amount <= 0) { toast('请输入有效金额'); return; }
  if (!category) { toast('请选择分类'); return; }

  try {
    await createExpense({ amount, category, expense_date: expenseDate, note });
    overlay?.remove();
    toast('记账成功 ✓');
    loadExpenses();
  } catch (e) {
    toast('记账失败: ' + e.message);
  }
}

async function deleteExpenseEntry(id, event) {
  event.stopPropagation();
  if (!confirm('确定删除这条记录？')) return;
  try {
    await deleteExpense(id);
    toast('已删除');
    loadExpenses();
  } catch (e) {
    toast('删除失败: ' + e.message);
  }
}
