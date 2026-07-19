/* 老婆哒哒 - 统一状态管理模块 - www/js/state.js */
/* 用于管理页面状态，避免各页面分散维护全局变量 */

// 当前状态对象
const state = {
  wardrobe: {
    filter: 'all',
    search: '',
    loading: false,
    error: null
  },
  recipe: {
    filter: {
      category: null,
      difficulty: null,
      tag: null
    },
    loading: false,
    error: null
  },
  health: {
    category: null,
    loading: false,
    error: null,
    readIds: new Set()
  },
  chat: {
    sessionId: null,
    count: 0,
    loading: false,
    error: null
  },
  profile: {
    items: 0,
    recipes: 0,
    expenses: 0,
    expenseMonth: 0,
    outfits: [],
    outfitsLoaded: false
  },
  isLoading: false
};

// 临时数据 - 用于缓存请求结果
const temp = {
  uploadFile: null,
  currentEditItem: null
};

// 读取状态
function getState() {
  return state;
}

// 更新状态（使用函数式更新，避免直接修改）
function setState(updates) {
  Object.assign(state, updates);
}

// 更新单个字段
function updateState(key, value) {
  state[key] = value;
}

// 清除特定数据
function clearTempData(key) {
  if (temp[key]) {
    temp[key] = null;
  }
}

// 重置状态
function resetState() {
  state.wardrobe = { filter: 'all', search: '', loading: false, error: null };
  state.recipe = { filter: { category: null, difficulty: null, tag: null }, loading: false, error: null };
  state.health = { category: null, loading: false, error: null, readIds: new Set() };
  state.chat = { sessionId: null, count: 0, loading: false, error: null };
  state.profile = { items: 0, recipes: 0, expenses: 0, expenseMonth: 0, outfits: [], outfitsLoaded: false };
  state.isLoading = false;
}

// 更新特定字段
function updateStateField(key, value) {
  state[key] = value;
}

// 获取当前状态的快照（用于调试）
function getStateSnapshot() {
  return { ...state };
}

// 导出公共 API
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { getState, setState, updateStateField, clearTempData, resetState, getStateSnapshot };
}

// 为了兼容旧代码，保留全局变量（但不推荐）
window.globalState = state;

