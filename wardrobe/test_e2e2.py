import paramiko, json
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('123.57.107.21', 22, 'root', 'YuJinZe12@.', timeout=15, allow_agent=False, look_for_keys=False)
def run(c, t=30, parse=False):
    si, so, se = ssh.exec_command(c, timeout=t)
    out = so.read().decode('utf-8', errors='replace').strip()
    if parse:
        try: return json.loads(out)
        except: return out
    return out

# 修正 wardrobe: 类别用"上衣", 增加多温度
wardrobe = [
    {"id": "t1", "category": "上衣", "name": "白T恤", "color": "白色", "style": "休闲", "warmth": "薄", "occasion": ["休闲","日常"], "image_path": ""},
    {"id": "t2", "category": "下装", "name": "牛仔裤", "color": "蓝色", "style": "休闲", "warmth": "薄", "occasion": ["休闲","日常"], "image_path": ""},
    {"id": "t3", "category": "外套", "name": "卡其风衣", "color": "卡其色", "style": "正式", "warmth": "适中", "occasion": ["商务","正式"], "image_path": ""},
    {"id": "t4", "category": "鞋子", "name": "白鞋", "color": "白色", "style": "休闲", "warmth": "适中", "occasion": ["休闲"], "image_path": ""},
    {"id": "t5", "category": "饰品", "name": "黑皮带", "color": "黑色", "style": "休闲", "warmth": "薄", "occasion": ["休闲","商务"], "image_path": ""},
    {"id": "t6", "category": "上衣", "name": "灰衬衫", "color": "灰色", "style": "正式", "warmth": "薄", "occasion": ["商务","正式","面试"], "image_path": ""},
    {"id": "t7", "category": "下装", "name": "黑西裤", "color": "黑色", "style": "正式", "warmth": "薄", "occasion": ["商务","正式","面试"], "image_path": ""},
    {"id": "t8", "category": "鞋子", "name": "黑皮鞋", "color": "黑色", "style": "正式", "warmth": "适中", "occasion": ["商务","正式"], "image_path": ""},
    {"id": "t9", "category": "上衣", "name": "白衬衫", "color": "白色", "style": "正式", "warmth": "薄", "occasion": ["商务","正式"], "image_path": ""},
    {"id": "t10", "category": "下装", "name": "卡其裤", "color": "卡其色", "style": "正式", "warmth": "适中", "occasion": ["商务","正式","日常"], "image_path": ""},
    {"id": "t11", "category": "饰品", "name": "黑领带", "color": "黑色", "style": "正式", "warmth": "薄", "occasion": ["商务","正式"], "image_path": ""},
    {"id": "t12", "category": "外套", "name": "灰西装", "color": "灰色", "style": "正式", "warmth": "适中", "occasion": ["商务","正式","面试"], "image_path": ""},
]
wardrobe_json = json.dumps(wardrobe, ensure_ascii=False).replace("'", "'\\''")
run(f"echo '{wardrobe_json}' > /opt/wardrobe/data/wardrobe.json && echo wrote {len(wardrobe)} items")

# 测试多个 occasion + 城市 (冷一点)
for occ, city in [("商务", "哈尔滨"), ("休闲", "北京"), ("面试", "上海")]:
    r = run(f"curl -s -X POST http://127.0.0.1:5050/api/recommend -H 'Content-Type: application/json' -d '{{\"occasion\":\"{occ}\",\"city\":\"{city}\"}}'", t=30, parse=True)
    if isinstance(r, dict):
        outfits = r.get('outfits', [])
        w = r.get('weather', {})
        print(f"\n=== {occ} @ {city} | {w.get('temp','?')}°C {w.get('desc','')} ===")
        print(f"  生成 {len(outfits)} 套, 总候选 {r.get('total_items','?')} 件")
        for i, o in enumerate(outfits[:5], 1):
            items = ' + '.join([it.get('name','?') for it in o.get('items', [])])
            print(f"  {i}. 评分 {o.get('score', 0):.2f} | {items[:80]}")
    else:
        print(f"\n=== {occ} @ {city} === 失败: {str(r)[:200]}")

ssh.close()
