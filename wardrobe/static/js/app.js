/* ===== 全局状态 ===== */
let wardrobeData = [];
let currentCat = "all";
let currentPage = "wardrobe";
let aiStatusCache = null;

/* ===== 初始化 ===== */
document.addEventListener("DOMContentLoaded", () => {
    initNavigation();
    initCategoryTabs();
    initAddModal();
    initRecommend();
    loadWardrobe();
    refreshAiStatus();
    // 30s 轮询一次 AI 状态
    setInterval(refreshAiStatus, 30000);
});

/* ===== AI 状态 ===== */
async function refreshAiStatus() {
    const el = document.getElementById("ai-status");
    const text = document.getElementById("ai-text");
    const dot = document.getElementById("ai-dot");
    el.className = "ai-status";
    text.textContent = "检测中...";
    try {
        const resp = await fetch("/api/ai/status");
        const s = await resp.json();
        aiStatusCache = s;
        renderAiStatus(s);
    } catch (e) {
        el.classList.add("error");
        text.textContent = "后端不可达";
    }
}

function renderAiStatus(s) {
    const el = document.getElementById("ai-status");
    const text = document.getElementById("ai-text");
    const fc = s.fashion_clip?.ready;
    const llm = s.llm?.ready;
    if (fc && llm) {
        el.className = "ai-status ready";
        text.textContent = `AI 已就绪 · ${s.llm.backend}`;
    } else if (fc || llm) {
        el.className = "ai-status partial";
        const parts = [];
        if (fc) parts.push("视觉");
        if (llm) parts.push("LLM");
        text.textContent = `部分就绪 · ${parts.join("+") || "无"}`;
    } else {
        el.className = "ai-status offline";
        text.textContent = "纯规则模式";
    }
}

document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("ai-status").addEventListener("click", refreshAiStatus);
});

/* ===== 页面导航 ===== */
function initNavigation() {
    document.querySelectorAll(".nav-tab").forEach(tab => {
        tab.addEventListener("click", () => {
            const page = tab.dataset.page;
            switchPage(page);
            document.querySelectorAll(".nav-tab").forEach(t => t.classList.remove("active"));
            tab.classList.add("active");
        });
    });
}

function switchPage(page) {
    currentPage = page;
    document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
    document.getElementById("page-" + page).classList.add("active");
    if (page === "wardrobe") loadWardrobe();
}

/* ===== 分类标签 ===== */
function initCategoryTabs() {
    document.querySelectorAll(".cat-tab").forEach(tab => {
        tab.addEventListener("click", () => {
            currentCat = tab.dataset.cat;
            document.querySelectorAll(".cat-tab").forEach(t => t.classList.remove("active"));
            tab.classList.add("active");
            renderWardrobe();
        });
    });
}

/* ===== 加载衣橱 ===== */
async function loadWardrobe() {
    try {
        const resp = await fetch("/api/wardrobe");
        wardrobeData = await resp.json();
        renderWardrobe();
    } catch (e) {
        console.error("加载衣橱失败:", e);
    }
}

function renderWardrobe() {
    const grid = document.getElementById("wardrobe-grid");
    const filtered = currentCat === "all"
        ? wardrobeData
        : wardrobeData.filter(item => item.category === currentCat);

    if (filtered.length === 0) {
        grid.innerHTML = '<div class="empty-hint">该分类暂无衣物，点击"添加衣物"开始整理吧</div>';
        return;
    }

    const categoryIcons = {
        "上衣": "👔", "下装": "👖", "连衣裙": "👗",
        "外套": "🧥", "鞋子": "👟", "饰品": "💍"
    };

    grid.innerHTML = filtered.map(item => {
        const imgHtml = item.image
            ? `<img class="card-img" src="${escapeHtml(item.image)}" alt="${escapeHtml(item.name)}" onerror="this.style.display='none';this.nextElementSibling.style.display='flex';">`
            : "";
        const placeholder = item.image
            ? `<div class="card-img placeholder" style="display:none">${categoryIcons[item.category] || "📦"}</div>`
            : `<div class="card-img placeholder">${categoryIcons[item.category] || "📦"}</div>`;

        return `
            <div class="cloth-card">
                ${imgHtml}${placeholder}
                <button class="card-delete" onclick="deleteItem('${item.id}')">&times;</button>
                <div class="card-body">
                    <div class="card-name">${escapeHtml(item.name)}</div>
                    <div class="card-tags">
                        <span class="card-tag">${escapeHtml(item.color)}</span>
                        <span class="card-tag">${escapeHtml(item.style)}</span>
                        <span class="card-tag">${escapeHtml(item.warmth)}</span>
                    </div>
                </div>
            </div>
        `;
    }).join("");
}

async function deleteItem(id) {
    if (!confirm("确定要删除这件衣物吗？")) return;
    try {
        await fetch(`/api/wardrobe/${id}`, { method: "DELETE" });
        wardrobeData = wardrobeData.filter(item => item.id !== id);
        renderWardrobe();
    } catch (e) {
        console.error("删除失败:", e);
    }
}

/* ===== 添加衣物弹窗 ===== */
function initAddModal() {
    const modal = document.getElementById("modal-add");
    const uploadArea = document.getElementById("upload-area");
    const fileInput = document.getElementById("add-image");
    const preview = document.getElementById("upload-preview");
    const placeholder = document.getElementById("upload-placeholder");

    document.getElementById("btn-show-add").addEventListener("click", () => {
        resetAddForm();
        modal.classList.add("show");
    });

    document.getElementById("btn-close-modal").addEventListener("click", () => {
        modal.classList.remove("show");
    });

    modal.addEventListener("click", (e) => {
        if (e.target === modal) modal.classList.remove("show");
    });

    uploadArea.addEventListener("click", () => fileInput.click());

    fileInput.addEventListener("change", () => {
        const file = fileInput.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                preview.src = e.target.result;
                preview.style.display = "block";
                placeholder.style.display = "none";
            };
            reader.readAsDataURL(file);
        }
    });

    document.getElementById("btn-submit-add").addEventListener("click", submitAddItem);
}

function resetAddForm() {
    document.getElementById("add-name").value = "";
    document.getElementById("add-category").value = "上衣";
    document.getElementById("add-color").value = "白色";
    document.getElementById("add-style").value = "休闲";
    document.getElementById("add-warmth").value = "适中";
    document.getElementById("add-season").value = "春夏";
    document.getElementById("add-image").value = "";
    document.getElementById("upload-preview").style.display = "none";
    document.getElementById("upload-placeholder").style.display = "block";
}

async function submitAddItem() {
    const name = document.getElementById("add-name").value.trim();
    if (!name) { alert("请输入衣物名称"); return; }

    const formData = new FormData();
    formData.append("name", name);
    formData.append("category", document.getElementById("add-category").value);
    formData.append("color", document.getElementById("add-color").value);
    formData.append("style", document.getElementById("add-style").value);
    formData.append("warmth", document.getElementById("add-warmth").value);
    formData.append("season", document.getElementById("add-season").value);

    const imageFile = document.getElementById("add-image").files[0];
    if (imageFile) formData.append("image", imageFile);

    const btn = document.getElementById("btn-submit-add");
    const oldText = btn.textContent;
    btn.disabled = true;
    btn.textContent = "添加中...";

    try {
        const resp = await fetch("/api/wardrobe", { method: "POST", body: formData });
        if (!resp.ok) throw new Error(await resp.text());
        const item = await resp.json();
        wardrobeData.push(item);
        document.getElementById("modal-add").classList.remove("show");
        renderWardrobe();
    } catch (e) {
        console.error("添加失败:", e);
        alert("添加失败，请重试");
    } finally {
        btn.disabled = false;
        btn.textContent = oldText;
    }
}

/* ===== 搭配推荐 ===== */
function initRecommend() {
    document.getElementById("btn-recommend").addEventListener("click", fetchRecommend);
}

async function fetchRecommend() {
    const btn = document.getElementById("btn-recommend");
    const city = document.getElementById("rec-city").value.trim() || "北京";
    const occasion = document.getElementById("rec-occasion").value;

    btn.disabled = true;
    btn.textContent = "生成中...";

    const container = document.getElementById("outfits-container");
    const useLLM = aiStatusCache?.llm?.ready;
    container.innerHTML = `
        <div class="loading-step">
            <div>正在分析天气与衣橱...</div>
            <div style="margin-top: 12px;">
                <span class="step active">① 规则候选</span>
                <span class="step ${useLLM ? "active" : ""}">② 视觉打分</span>
                <span class="step ${useLLM ? "active" : ""}">③ LLM 精排</span>
            </div>
        </div>`;

    try {
        const resp = await fetch(`/api/recommend?city=${encodeURIComponent(city)}&occasion=${encodeURIComponent(occasion)}`);
        const data = await resp.json();
        renderWeather(data.weather);
        renderOutfits(data.outfits, data.total_items, data.ai);
    } catch (e) {
        console.error("推荐失败:", e);
        container.innerHTML = '<div class="empty-hint">获取推荐失败，请检查网络后重试</div>';
    } finally {
        btn.disabled = false;
        btn.textContent = "生成搭配";
    }
}

function renderWeather(weather) {
    const card = document.getElementById("weather-card");
    card.style.display = "flex";

    const weatherIcons = {
        "晴": "☀️", "阴": "☁️", "雨": "🌧️", "雪": "❄️", "雾": "🌫️"
    };
    document.getElementById("weather-icon").textContent = weatherIcons[weather.weather_type] || "🌤️";
    document.getElementById("weather-temp").textContent = weather.temp;
    document.getElementById("weather-desc").textContent = `${weather.city} · ${weather.desc}`;
    document.getElementById("weather-feels").textContent = weather.feels_like;
    document.getElementById("weather-humid").textContent = weather.humidity;
    document.getElementById("weather-wind").textContent = weather.wind;

    const warmthText = weather.suggested_warmth.join("/");
    document.getElementById("weather-tip").textContent = `建议穿${warmthText}款衣物`;
}

function renderOutfits(outfits, totalItems, ai) {
    const container = document.getElementById("outfits-container");

    if (totalItems < 3) {
        container.innerHTML = `<div class="empty-hint">衣橱里衣物太少（至少需要3件），先去添加一些衣物吧！<br>建议：上衣 + 下装 + 鞋子是基础搭配</div>`;
        return;
    }

    if (!outfits || outfits.length === 0) {
        container.innerHTML = `<div class="empty-hint">暂未找到合适的搭配。试着添加更多衣物，或更换场合/城市再试试。</div>`;
        return;
    }

    const categoryIcons = {
        "上衣": "👔", "下装": "👖", "连衣裙": "👗",
        "外套": "🧥", "鞋子": "👟", "饰品": "💍"
    };

    const aiBadge = ai?.used_llm
        ? '<span class="outfit-tag ai-tag">✨ AI 精排</span>'
        : (ai?.used_visual ? '<span class="outfit-tag ai-tag">👁 视觉打分</span>' : "");

    container.innerHTML = `
        <div class="outfit-tags" style="margin-bottom: 4px;">${aiBadge}</div>
    ` + outfits.map((outfit, idx) => {
        const rankClass = idx < 2 ? "top" : "";
        const itemsHtml = outfit.items.map(item => {
            const imgHtml = item.image
                ? `<img class="outfit-item-img" src="${escapeHtml(item.image)}" alt="${escapeHtml(item.name)}" onerror="this.style.display='none';this.nextElementSibling.style.display='flex';">`
                : "";
            const iconHtml = item.image
                ? `<div class="outfit-item-img" style="display:none">${categoryIcons[item.category] || "📦"}</div>`
                : `<div class="outfit-item-img">${categoryIcons[item.category] || "📦"}</div>`;
            return `
                <div class="outfit-item">
                    ${imgHtml}${iconHtml}
                    <div class="outfit-item-name">${escapeHtml(item.name)}</div>
                    <div class="outfit-item-cat">${escapeHtml(item.color)} · ${escapeHtml(item.style)}</div>
                </div>
            `;
        }).join('<div class="outfit-arrow">→</div>');

        const reason = outfit.reason ? escapeHtml(outfit.reason) : "";

        return `
            <div class="outfit-card ${ai?.used_llm ? "ai" : ""}">
                <div class="outfit-rank ${rankClass}">#${idx + 1}</div>
                <div class="outfit-body">
                    <div class="outfit-items">${itemsHtml}</div>
                    <div class="outfit-reason">${reason || "（无理由）"}</div>
                </div>
                <div class="outfit-score">
                    <span class="outfit-score-value">${outfit.score}</span>
                    <span class="outfit-score-label">综合分</span>
                    <span class="outfit-score-label" style="font-size:9px; color:#b8b0a5">
                        规则${outfit.rule_score} + 视觉×${outfit.visual_score}
                    </span>
                </div>
            </div>
        `;
    }).join("");
}

/* ===== 工具函数 ===== */
function escapeHtml(str) {
    if (str == null) return "";
    const div = document.createElement("div");
    div.textContent = String(str);
    return div.innerHTML;
}
