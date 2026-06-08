/* camera.js — 拍照入库页 */

function renderCameraPage() {
  const page = document.getElementById('page-camera');
  page.classList.add('active');
  page.innerHTML = `
    <div class="page-header">添加衣服</div>
    <div class="upload-area" id="upload-area" onclick="document.getElementById('file-input').click()">
      <div style="font-size:40px;margin-bottom:8px;">📷</div>
      <div style="color:#FF8C94;font-size:14px;">点击拍照 / 选择照片</div>
      <input type="file" id="file-input" accept="image/*" capture="environment" onchange="onFileSelected(this)">
      <img id="upload-preview" class="upload-preview" style="display:none;">
    </div>
    <div class="progress-bar" id="upload-progress"><div class="progress-fill" id="progress-fill"></div></div>
    <div class="form-grid" id="form-grid" style="display:none;">
      <div class="form-full">
        <label>标题</label>
        <input type="text" id="f-title" placeholder="如：白色棉质T恤">
      </div>
      <div>
        <label>类别 *</label>
        <select id="f-category" required>
          <option value="">请选择</option>
          <option value="top">上装</option>
          <option value="bottom">下装</option>
          <option value="dress">连衣裙</option>
          <option value="outerwear">外套</option>
          <option value="shoes">鞋</option>
          <option value="bag">包</option>
          <option value="accessory">配饰</option>
        </select>
      </div>
      <div>
        <label>颜色</label>
        <select id="f-color">
          <option value="">请选择</option>
          <option value="black">黑色</option>
          <option value="white">白色</option>
          <option value="gray">灰色</option>
          <option value="blue">蓝色</option>
          <option value="navy">藏蓝</option>
          <option value="red">红色</option>
          <option value="pink">粉色</option>
          <option value="green">绿色</option>
          <option value="yellow">黄色</option>
          <option value="beige">米色</option>
          <option value="brown">棕色</option>
          <option value="purple">紫色</option>
          <option value="orange">橙色</option>
          <option value="neutral">中性色</option>
        </select>
      </div>
      <div>
        <label>季节</label>
        <select id="f-season">
          <option value="">不限</option>
          <option value="spring">春</option>
          <option value="summer">夏</option>
          <option value="fall">秋</option>
          <option value="winter">冬</option>
        </select>
      </div>
      <div>
        <label>品牌</label>
        <input type="text" id="f-brand" placeholder="如：ZARA">
      </div>
      <div class="form-full">
        <label>备注</label>
        <textarea id="f-note" placeholder="其他备注…"></textarea>
      </div>
    </div>
    <button class="submit-btn" id="submit-btn" style="display:none;" onclick="submitItem()">上传到衣橱</button>
  `;
}

let selectedFile = null;

function onFileSelected(input) {
  const file = input.files[0];
  if (!file) return;
  selectedFile = file;
  const preview = document.getElementById('upload-preview');
  preview.src = URL.createObjectURL(file);
  preview.style.display = 'block';
  document.getElementById('form-grid').style.display = 'grid';
  document.getElementById('submit-btn').style.display = 'block';
  document.getElementById('upload-area').style.display = 'none';
}

async function submitItem() {
  const category = document.getElementById('f-category').value;
  if (!category) { toast('请选择类别'); return; }
  if (!selectedFile) { toast('请先选择照片'); return; }

  const btn = document.getElementById('submit-btn');
  btn.disabled = true;
  btn.textContent = '上传中…';
  const progressBar = document.getElementById('upload-progress');
  const progressFill = document.getElementById('progress-fill');
  progressBar.style.display = 'block';

  try {
    const fd = new FormData();
    fd.append('file', selectedFile);
    fd.append('title', document.getElementById('f-title').value);
    fd.append('category', category);
    fd.append('color', document.getElementById('f-color').value);
    fd.append('season', document.getElementById('f-season').value);
    fd.append('brand', document.getElementById('f-brand').value);
    fd.append('note', document.getElementById('f-note').value);

    // simulate progress (actual fetch progress not easily trackable)
    let pct = 0;
    const ticker = setInterval(() => {
      pct = Math.min(pct + 10, 90);
      progressFill.style.width = pct + '%';
    }, 200);

    await postItem(fd);
    clearInterval(ticker);
    progressFill.style.width = '100%';

    toast('上传成功 ✨');
    setTimeout(() => {
      progressBar.style.display = 'none';
      progressFill.style.width = '0%';
      // reset
      selectedFile = null;
      document.getElementById('upload-preview').style.display = 'none';
      document.getElementById('upload-area').style.display = 'block';
      document.getElementById('form-grid').style.display = 'none';
      document.getElementById('submit-btn').style.display = 'none';
      document.getElementById('submit-btn').disabled = false;
      document.getElementById('submit-btn').textContent = '上传到衣橱';
      document.getElementById('file-input').value = '';
      // clear form
      ['f-title','f-color','f-season','f-brand','f-note'].forEach(id => document.getElementById(id).value = '');
      document.getElementById('f-category').value = '';
    }, 800);
  } catch(e) {
    clearInterval(ticker);
    progressBar.style.display = 'none';
    progressFill.style.width = '0%';
    toast('上传失败：' + e.message);
    btn.disabled = false;
    btn.textContent = '上传到衣橱';
  }
}