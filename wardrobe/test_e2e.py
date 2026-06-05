import paramiko, json, re

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('123.57.107.21', 22, 'root', 'YuJinZe12@.', timeout=15, allow_agent=False, look_for_keys=False)
ansi = re.compile(r"\x1b\[[0-9;]*m")
def run(c, t=30, parse_json=False):
    si, so, se = ssh.exec_command(c, timeout=t)
    out = so.read().decode('utf-8', errors='replace').strip()
    if parse_json:
        try: return json.loads(out)
        except: return out
    return out

print("=== 端到端测试 (LLM 已自动禁用, 应走纯规则模式) ===\n")

# 1. 状态
s = run("curl -s http://127.0.0.1:5050/api/ai/status", parse_json=True)
print(f"AI 状态: llm.backend={s['llm']['backend']}, llm.disabled={s['llm']['disabled_reason']}")
print(f"         fashion_clip.ready={s['fashion_clip']['ready']}")
print(f"         可用内存: {s['system']['available_memory_mb']}MB\n")

# 2. 注入测试衣物
wardrobe = [
    {"id": "t1", "category": "上装", "name": "白T恤", "color": "白色", "style": "休闲", "warmth": "薄", "occasion": ["休闲", "日常"], "image_path": ""},
    {"id": "t2", "category": "下装", "name": "牛仔裤", "color": "蓝色", "style": "休闲", "warmth": "适中", "occasion": ["休闲", "日常"], "image_path": ""},
    {"id": "t3", "category": "外套", "name": "卡其风衣", "color": "卡其色", "style": "正式", "warmth": "适中", "occasion": ["商务", "正式"], "image_path": ""},
    {"id": "t4", "category": "鞋", "name": "白鞋", "color": "白色", "style": "休闲", "warmth": "适中", "occasion": ["休闲"], "image_path": ""},
    {"id": "t5", "category": "配饰", "name": "黑皮带", "color": "黑色", "style": "休闲", "warmth": "薄", "occasion": ["休闲", "商务"], "image_path": ""},
    {"id": "t6", "category": "上装", "name": "灰衬衫", "color": "灰色", "style": "正式", "warmth": "适中", "occasion": ["商务", "正式", "面试"], "image_path": ""},
    {"id": "t7", "category": "下装", "name": "黑西裤", "color": "黑色", "style": "正式", "warmth": "适中", "occasion": ["商务", "正式", "面试"], "image_path": ""},
    {"id": "t8", "category": "鞋", "name": "黑皮鞋", "color": "黑色", "style": "正式", "warmth": "适中", "occasion": ["商务", "正式"], "image_path": ""},
]
wardrobe_json = json.dumps(wardrobe, ensure_ascii=False)
import urllib.parse
wardrobe_esc = wardrobe_json.replace("'", "'\\''")

# 写 wardrobe.json
run(f"mkdir -p /opt/wardrobe/data && echo '{wardrobe_esc}' > /opt/wardrobe/data/wardrobe.json && echo 'wardrobe.json: '$(wc -c < /opt/wardrobe/data/wardrobe.json)' bytes'")

# 3. 推荐
print("\n=== 测试 /api/recommend ===")
rec = run("curl -s -X POST http://127.0.0.1:5050/api/recommend -H 'Content-Type: application/json' -d '{\"occasion\":\"商务\",\"city\":\"北京\"}'", t=60, parse_json=True)
if isinstance(rec, dict):
    print(f"返回 {len(rec.get('outfits', []))} 套搭配")
    if rec.get('outfits'):
        for i, o in enumerate(rec['outfits'][:3], 1):
            items = ' + '.join([it.get('name','?') for it in o.get('items', [])])
            print(f"  {i}. 评分 {o.get('score', 0):.2f} | {items[:60]}")
    print(f"\nweather: {rec.get('weather', {}).get('temp', '?')}°C {rec.get('weather', {}).get('desc', '')}")
    print(f"llm_backend: {rec.get('llm_backend', '?')}")
    if rec.get('reasons'):
        print(f"reasons 样本: {list(rec['reasons'].items())[0] if rec['reasons'] else '(无)'}")
else:
    print(rec[:500])

# 4. 首页
run("curl -s -o /dev/null -w 'GET / -> HTTP %{http_code} | %{size_download} bytes\\n' http://127.0.0.1:5050/")

# 5. 日志
print("\n=== 最近日志 ===")
out = run("tail -15 /opt/wardrobe/logs/wardrobe.out.log")
print(out)

ssh.close()
