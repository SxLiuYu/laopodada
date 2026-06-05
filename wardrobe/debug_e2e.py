import paramiko, json
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('123.57.107.21', 22, 'root', 'YuJinZe12@.', timeout=15, allow_agent=False, look_for_keys=False)
def run(c, t=30):
    si, so, se = ssh.exec_command(c, timeout=t)
    return so.read().decode('utf-8', errors='replace')
ansi = lambda s: __import__('re').compile(r'\x1b\[[0-9;]*m').sub('', s)

# 1. 完整响应
print("=== 完整 recommend 响应 ===")
r = run("curl -s -X POST http://127.0.0.1:5050/api/recommend -H 'Content-Type: application/json' -d '{\"occasion\":\"商务\",\"city\":\"北京\"}'", t=60)
print(r[:2000])

# 2. wardrobe.json 实际内容
print("\n=== wardrobe.json 头 200 字节 ===")
print(run("head -c 400 /opt/wardrobe/data/wardrobe.json"))

# 3. 完整日志
print("\n=== 完整日志 ===")
print(ansi(run("cat /opt/wardrobe/logs/wardrobe.out.log | tail -50")))
print("--- ERR ---")
print(ansi(run("cat /opt/wardrobe/logs/wardrobe.err.log 2>/dev/null | tail -30")))

ssh.close()
